from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from great_expectations.expectations.expectation import (
    MulticolumnMapExpectation,
    render_evaluation_parameter_string,
)
from great_expectations.render import LegacyRendererType, RenderedStringTemplateContent
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.renderer_configuration import (
    RendererConfiguration,
    RendererValueType,
)
from great_expectations.render.util import (
    num_to_str,
    parse_row_condition_string_pandas_engine,
    substitute_none_for_missing,
)

if TYPE_CHECKING:
    from great_expectations.core import (
        ExpectationValidationResult,
    )
    from great_expectations.expectations.expectation_configuration import (
        ExpectationConfiguration,
    )
    from great_expectations.render.renderer_configuration import AddParamArgs


class ExpectSelectColumnValuesToBeUniqueWithinRecord(MulticolumnMapExpectation):
    """Expect the values for each record to be unique across the columns listed. Note that records can be duplicated.

    expect_select_column_values_to_be_unique_within_record is a \
    [Multicolumn Map Expectation](https://docs.greatexpectations.io/docs/guides/expectations/creating_custom_expectations/how_to_create_custom_multicolumn_map_expectations).

    Multicolumn Map Expectations are evaluated for a set of columns and ask a yes/no question about the row-wise relationship between those columns.
    Based on the result, they then calculate the percentage of rows that gave a positive answer.
    If the percentage is high enough, the Expectation considers that data valid.

    Args:
        column_list (tuple or list): The column names to evaluate

    Other Parameters:
        ignore_row_if (str): \
            "all_values_are_missing", "any_value_is_missing", "never" \
            If specified, sets the condition on which a given row is to be ignored. Default "never".
        mostly (None or a float between 0 and 1): \
            Successful if at least `mostly` fraction of values match the expectation. \
            For more detail, see [mostly](https://docs.greatexpectations.io/docs/reference/expectations/standard_arguments/#mostly). Default 1.
        result_format (str or None): \
            Which output mode to use: BOOLEAN_ONLY, BASIC, COMPLETE, or SUMMARY. \
            For more detail, see [result_format](https://docs.greatexpectations.io/docs/reference/expectations/result_format).
        catch_exceptions (boolean or None): \
            If True, then catch exceptions and include them as part of the result object. \
            For more detail, see [catch_exceptions](https://docs.greatexpectations.io/docs/reference/expectations/standard_arguments/#catch_exceptions).
        meta (dict or None): \
            A JSON-serializable dictionary (nesting allowed) that will be included in the output without \
            modification. For more detail, see [meta](https://docs.greatexpectations.io/docs/reference/expectations/standard_arguments/#meta).

    Returns:
        An [ExpectationSuiteValidationResult](https://docs.greatexpectations.io/docs/terms/validation_result)

        Exact fields vary depending on the values passed to result_format, catch_exceptions, and meta.

    Supported Datasources:
        [Snowflake](https://docs.greatexpectations.io/docs/application_integration_support/)
        [PostgreSQL](https://docs.greatexpectations.io/docs/application_integration_support/)

    Data Quality Category:
        Cardinality

    For example:
    ::

        A B C
        1 1 2 Fail
        1 2 3 Pass
        8 2 7 Pass
        1 2 3 Pass
        4 4 4 Fail
    Example Data:
                test 	test2   test3
            0 	1       1       2
            1 	1       2       3
            2 	8       2       7

    Code Examples:
        Passing Case:
            Input:
                ExpectSelectColumnValuesToBeUniqueWithinRecord(
                    column_list=["test", "test3"],
            )

            Output:
                {
                  "exception_info": {
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  },
                  "result": {
                    "element_count": 3,
                    "unexpected_count": 0,
                    "unexpected_percent": 0.0,
                    "partial_unexpected_list": [],
                    "missing_count": 0,
                    "missing_percent": 0.0,
                    "unexpected_percent_total": 0.0,
                    "unexpected_percent_nonmissing": 0.0
                  },
                  "meta": {},
                  "success": true
                }

        Failing Case:
            Input:
                ExpectSelectColumnValuesToBeUniqueWithinRecord(
                    column_list=["test", "test2, "test3"],
            )

            Output:
                {
                  "exception_info": {
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  },
                  "result": {
                    "element_count": 3,
                    "unexpected_count": 1,
                    "unexpected_percent": 33.33333333333333,
                    "partial_unexpected_list": [
                        {
                            "test": 1,
                            "test2": 1,
                            "test3": 2
                        }
                    ],
                    "missing_count": 0,
                    "missing_percent": 0.0,
                    "unexpected_percent_total": 33.33333333333333,
                    "unexpected_percent_nonmissing": 33.33333333333333
                  },
                  "meta": {},
                  "success": false
                }
    """  # noqa: E501

    column_list: Union[tuple, list]
    ignore_row_if: str = "all_values_are_missing"

    library_metadata = {
        "maturity": "production",
        "tags": [
            "core expectation",
            "multi-column expectation",
        ],
        "contributors": [
            "@great_expectations",
        ],
        "requirements": [],
        "has_full_test_suite": True,
        "manually_reviewed_code": True,
    }

    map_metric = "select_column_values.unique.within_record"
    args_keys = ("column_list",)

    @classmethod
    def _prescriptive_template(
        cls,
        renderer_configuration: RendererConfiguration,
    ) -> RendererConfiguration:
        add_param_args: AddParamArgs = (
            ("column_list", RendererValueType.ARRAY),
            ("mostly", RendererValueType.NUMBER),
            ("ignore_row_if", RendererValueType.STRING),
        )
        for name, param_type in add_param_args:
            renderer_configuration.add_param(name=name, param_type=param_type)

        params = renderer_configuration.params

        if params.mostly and params.mostly.value < 1.0:
            renderer_configuration = cls._add_mostly_pct_param(
                renderer_configuration=renderer_configuration
            )
            template_str = (
                "Values must be unique across columns, at least $mostly_pct % of the time: "
            )
        else:
            template_str = "Values must always be unique across columns: "

        if params.column_list:
            array_param_name = "column_list"
            param_prefix = "column_list_"
            renderer_configuration = cls._add_array_params(
                array_param_name=array_param_name,
                param_prefix=param_prefix,
                renderer_configuration=renderer_configuration,
            )
            template_str += cls._get_array_string(
                array_param_name=array_param_name,
                param_prefix=param_prefix,
                renderer_configuration=renderer_configuration,
            )

        renderer_configuration.template_str = template_str

        return renderer_configuration

    @classmethod
    @renderer(renderer_type=LegacyRendererType.PRESCRIPTIVE)
    @render_evaluation_parameter_string
    def _prescriptive_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        runtime_configuration = runtime_configuration or {}
        _ = False if runtime_configuration.get("include_column_name") is False else True  # noqa: SIM211
        styling = runtime_configuration.get("styling")

        params = substitute_none_for_missing(
            configuration.kwargs,
            [
                "column_list",
                "ignore_row_if",
                "row_condition",
                "condition_parser",
                "mostly",
            ],
        )

        if params["mostly"] is not None and params["mostly"] < 1.0:
            params["mostly_pct"] = num_to_str(params["mostly"] * 100, no_scientific=True)
            template_str = (
                "Values must be unique across columns, at least $mostly_pct % of the time: "
            )
        else:
            template_str = "Values must always be unique across columns: "

        for idx in range(len(params["column_list"]) - 1):
            template_str += f"$column_list_{idx!s}, "
            params[f"column_list_{idx!s}"] = params["column_list"][idx]

        last_idx = len(params["column_list"]) - 1
        template_str += f"$column_list_{last_idx!s}"
        params[f"column_list_{last_idx!s}"] = params["column_list"][last_idx]

        if params["row_condition"] is not None:
            (
                conditional_template_str,
                conditional_params,
            ) = parse_row_condition_string_pandas_engine(params["row_condition"])
            template_str = (
                conditional_template_str + ", then " + template_str[0].lower() + template_str[1:]
            )
            params.update(conditional_params)
        return [
            RenderedStringTemplateContent(
                **{
                    "content_block_type": "string_template",
                    "string_template": {
                        "template": template_str,
                        "params": params,
                        "styling": styling,
                    },
                }
            )
        ]
