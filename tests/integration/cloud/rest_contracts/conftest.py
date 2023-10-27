from __future__ import annotations

import enum
import os
import pathlib
import subprocess
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, Final, Iterator, List, Union

import pact
import pytest
from typing_extensions import Annotated, TypeAlias  # noqa: TCH002

from great_expectations.compatibility import pydantic
from great_expectations.core.http import create_session

if TYPE_CHECKING:
    import requests


PACT_MOCK_HOST: Final[str] = "localhost"
PACT_MOCK_PORT: Final[int] = 9292
PACT_DIR: Final[pathlib.Path] = pathlib.Path(pathlib.Path(__file__).parent, "pacts")

PACT_BROKER_BASE_URL: Final[str] = "https://greatexpectations.pactflow.io"

CONSUMER_NAME: Final[str] = "great_expectations"
PROVIDER_NAME: Final[str] = "mercury"


JsonData: TypeAlias = Union[None, int, str, bool, List[Any], Dict[str, Any]]

PactBody: TypeAlias = Union[
    Dict[str, Union[JsonData, pact.matchers.Matcher]], pact.matchers.Matcher
]


EXISTING_ORGANIZATION_ID: Final[str] = os.environ.get("GX_CLOUD_ORGANIZATION_ID") or ""


@pytest.fixture(scope="module")
def gx_cloud_session() -> requests.Session:
    try:
        access_token = os.environ["GX_CLOUD_ACCESS_TOKEN"]
    except KeyError as e:
        raise OSError("GX_CLOUD_ACCESS_TOKEN is not set in this environment.") from e

    return create_session(access_token=access_token)


class RequestMethods(str, enum.Enum):
    DELETE = "DELETE"
    GET = "GET"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"


class ContractInteraction(pydantic.BaseModel):
    """Represents a Python API (Consumer) request and expected minimal response,
       given a state in the Cloud backend (Provider).

    The given state is something you know to be true about the Cloud backend data requested.

    Args:
        method: A string (e.g. "GET" or "POST") or attribute of the RequestMethods class representing a request method.
        request_path: A pathlib.Path to the endpoint relative to the base url
              e.g. pathlib.Path("/", "organizations", organization_id, "data-context-configuration"))
        upon_receiving: A string description of the type of request being made.
        given: A string description of the state of the Cloud backend data requested.
        response_status: The status code associated with the response. An integer between 100 and 599.
        response_body: A dictionary or Pact Matcher object representing the response body.
        request_body (Optional): A dictionary or Pact Matcher object representing the request body.
        request_headers (Optional): A dictionary representing the request headers.

    Returns:
        ContractInteraction
    """

    class Config:
        arbitrary_types_allowed = True

    method: Union[RequestMethods, pydantic.StrictStr]
    request_path: pathlib.Path
    upon_receiving: pydantic.StrictStr
    given: pydantic.StrictStr
    response_status: Annotated[int, pydantic.Field(strict=True, ge=100, lt=600)]
    response_body: PactBody
    request_body: Union[PactBody, None] = None
    request_headers: Union[dict, None] = None

    def run(self, gx_cloud_session: requests.Session) -> None:
        """Produces a Pact contract json file in the following directory:
             - tests/integration/cloud/rest_contracts/pacts
           and verifies the contract against Mercury.

        Returns:
            None
        """

        request: dict[str, str | PactBody] = {
            "method": self.method,
            "path": str(self.request_path),
        }
        if self.request_body is not None:
            request["body"] = self.request_body

        request["headers"] = dict(gx_cloud_session.headers)

        response: dict[str, int | PactBody] = {
            "status": self.response_status,
            "body": self.response_body,
        }

        pact_test: pact.Pact = next(ContractInteraction._get_pact_test())

        (
            pact_test.given(provider_state=self.given)
            .upon_receiving(scenario=self.upon_receiving)
            .with_request(**request)
            .will_respond_with(**response)
        )

        request_url = f"http://{PACT_MOCK_HOST}:{PACT_MOCK_PORT}{self.request_path}"

        with pact_test:
            gx_cloud_session.request(method=self.method, url=request_url)

    @staticmethod
    def _get_git_commit_hash() -> str:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip()
        )

    @staticmethod
    def _get_pact_test() -> Iterator[pact.Pact]:
        broker_token: str
        publish_to_broker: bool
        if os.environ.get("PACT_BROKER_READ_WRITE_TOKEN"):
            broker_token = os.environ.get("PACT_BROKER_READ_WRITE_TOKEN", "")
            publish_to_broker = True
        elif os.environ.get("PACT_BROKER_READ_ONLY_TOKEN"):
            broker_token = os.environ.get("PACT_BROKER_READ_ONLY_TOKEN", "")
            publish_to_broker = False
        else:
            pytest.skip(
                "no pact credentials: set PACT_BROKER_READ_ONLY_TOKEN from greatexpectations.pactflow.io"
            )

        # Adding random id to the commit hash allows us to run the build
        # and publish the contract more than once for a given commit.
        # We need this because we have the ability to trigger re-run of tests
        # in GH, and we run the release build process on the tagged commit.
        version = (
            f"{ContractInteraction._get_git_commit_hash()}_{str(uuid.uuid4())[:5]}"
        )

        pact_test: pact.Pact = pact.Consumer(
            name=CONSUMER_NAME,
            version=version,
            tag_with_git_branch=True,
            auto_detect_version_properties=True,
        ).has_pact_with(
            pact.Provider(name=PROVIDER_NAME),
            broker_base_url=PACT_BROKER_BASE_URL,
            broker_token=broker_token,
            host_name=PACT_MOCK_HOST,
            port=PACT_MOCK_PORT,
            pact_dir=str(PACT_DIR.resolve()),
            publish_to_broker=publish_to_broker,
        )

        pact_test.start_service()
        yield pact_test
        pact_test.stop_service()

        try:
            ContractInteraction._verify_pact()
        except AssertionError as e:
            raise AssertionError("Pact verification failed") from e

    @staticmethod
    def _verify_pact() -> None:
        try:
            provider_base_url: str = os.environ["GX_CLOUD_BASE_URL"]
        except KeyError as e:
            raise OSError("GX_CLOUD_BASE_URL is not set in this environment.") from e

        verifier = pact.Verifier(
            provider=PROVIDER_NAME,
            provider_base_url=provider_base_url,
        )

        pacts: tuple[str, ...] = tuple(
            str(file.resolve()) for file in PACT_DIR.glob("*.json")
        )

        success, logs = verifier.verify_pacts(
            *pacts,
            verbose=False,
        )
        assert success == 0


@pytest.fixture
def run_pact_test(gx_cloud_session: requests.Session) -> Callable:
    def _run_pact_test(contract_interaction: ContractInteraction) -> None:
        """Runs a contract test and produces a Pact contract json file in directory:
            - tests/integration/cloud/rest_contracts/pacts
        Args:
            contract_interaction: A ContractInteraction object which represents a Python API (Consumer) request
                                  and expected minimal response, given a state in the Cloud backend (Provider).
        Returns:
            None
        """
        contract_interaction.run(gx_cloud_session=gx_cloud_session)

    return _run_pact_test
