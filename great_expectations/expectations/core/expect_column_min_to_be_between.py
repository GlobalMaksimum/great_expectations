from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Union

from great_expectations.compatibility.typing_extensions import override
from great_expectations.core.evaluation_parameters import (
    EvaluationParameterDict,  # noqa: TCH001
)
from great_expectations.expectations.expectation import (
    ColumnAggregateExpectation,
    render_evaluation_parameter_string,
)
from great_expectations.render import (
    LegacyDescriptiveRendererType,
    LegacyRendererType,
    RenderedStringTemplateContent,
)
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.renderer_configuration import (
    RendererConfiguration,
    RendererValueType,
)
from great_expectations.render.util import (
    handle_strict_min_max,
    parse_row_condition_string_pandas_engine,
    substitute_none_for_missing,
)

if TYPE_CHECKING:
    from great_expectations.core import (
        ExpectationValidationResult,
    )
    from great_expectations.execution_engine import ExecutionEngine
    from great_expectations.expectations.expectation_configuration import (
        ExpectationConfiguration,
    )
    from great_expectations.render.renderer_configuration import AddParamArgs


class ExpectColumnMinToBeBetween(ColumnAggregateExpectation):
    """Expect the column minimum to be between a minimum value and a maximum value.

    expect_column_min_to_be_between is a \
    [Column Aggregate Expectation](https://docs.greatexpectations.io/docs/guides/expectations/creating_custom_expectations/how_to_create_custom_column_aggregate_expectations).

    Column Aggregate Expectations are one of the most common types of Expectation.
    They are evaluated for a single column, and produce an aggregate Metric, such as a mean, standard deviation, number of unique values, column type, etc.
    If that Metric meets the conditions you set, the Expectation considers that data valid.

    Args:
        column (str): \
            The column name
        min_value (comparable type or None): \
            The minimal column minimum allowed.
        max_value (comparable type or None): \
            The maximal column minimum allowed.
        strict_min (boolean): \
            If True, the minimal column minimum must be strictly larger than min_value, default=False
        strict_max (boolean): \
            If True, the maximal column minimum must be strictly smaller than max_value, default=False

    Other Parameters:
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

    Notes:
        * min_value and max_value are both inclusive unless strict_min or strict_max are set to True.
        * If min_value is None, then max_value is treated as an upper bound
        * If max_value is None, then min_value is treated as a lower bound
        * observed_value field in the result object is customized for this expectation to be a list \
            representing the actual column min

    See Also:
        [expect_column_max_to_be_between](https://greatexpectations.io/expectations/expect_column_max_to_be_between)

    Supported Datasources:
        [Snowflake](https://docs.greatexpectations.io/docs/application_integration_support/)
        [PostgreSQL](https://docs.greatexpectations.io/docs/application_integration_support/)

    Data Quality Category:
        Numerical Data

    Example Data:
                test 	test2
            0 	1       1
            1 	1.3     7
            2 	.8      2.5
            3   2       3

    Code Examples:
        Passing Case:
            Input:
                ExpectColumnMinToBeBetween(
                    column="test",
                    min_value=.5,
                    max_value=1
            )

            Output:
                {
                  "exception_info": {
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  },
                  "result": {
                    "observed_value": .8
                  },
                  "meta": {},
                  "success": true
                }

        Failing Case:
            Input:
                ExpectColumnMedianToBeBetween(
                    column="test2",
                    min_value=1,
                    max_value=3,
                    strict_min=True,
                    strict_max=True
            )

            Output:
                {
                  "exception_info": {
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  },
                  "result": {
                    "observed_value": 1
                  },
                  "meta": {},
                  "success": false
                }
    """  # noqa: E501

    min_value: Union[float, EvaluationParameterDict, datetime, None] = None
    max_value: Union[float, EvaluationParameterDict, datetime, None] = None
    strict_min: bool = False
    strict_max: bool = False

    # This dictionary contains metadata for display in the public gallery
    library_metadata = {
        "maturity": "production",
        "tags": ["core expectation", "column aggregate expectation"],
        "contributors": ["@great_expectations"],
        "requirements": [],
        "has_full_test_suite": True,
        "manually_reviewed_code": True,
    }

    # Setting necessary computation metric dependencies and defining kwargs, as well as assigning kwargs default values\  # noqa: E501
    metric_dependencies = ("column.min",)
    success_keys = (
        "min_value",
        "strict_min",
        "max_value",
        "strict_max",
    )

    args_keys = (
        "column",
        "min_value",
        "max_value",
        "strict_min",
        "strict_max",
    )

    @classmethod
    @override
    def _prescriptive_template(  # noqa: C901 - too complex
        cls,
        renderer_configuration: RendererConfiguration,
    ) -> RendererConfiguration:
        add_param_args: AddParamArgs = (
            ("column", RendererValueType.STRING),
            ("min_value", [RendererValueType.NUMBER, RendererValueType.DATETIME]),
            ("max_value", [RendererValueType.NUMBER, RendererValueType.DATETIME]),
            ("strict_min", RendererValueType.BOOLEAN),
            ("strict_max", RendererValueType.BOOLEAN),
        )
        for name, param_type in add_param_args:
            renderer_configuration.add_param(name=name, param_type=param_type)

        params = renderer_configuration.params

        if not params.min_value and not params.max_value:
            template_str = "minimum value may have any numerical value."
        else:
            at_least_str = "greater than or equal to"
            if params.strict_min:
                at_least_str = cls._get_strict_min_string(
                    renderer_configuration=renderer_configuration
                )
            at_most_str = "less than or equal to"
            if params.strict_max:
                at_most_str = cls._get_strict_max_string(
                    renderer_configuration=renderer_configuration
                )

            if params.min_value and params.max_value:
                if params.min_value == params.max_value:
                    template_str = "minimum value must be $min_value"
                else:
                    template_str = f"minimum value must be {at_least_str} $min_value and {at_most_str} $max_value."  # noqa: E501
            elif not params.min_value:
                template_str = f"minimum value must be {at_most_str} $max_value."
            else:
                template_str = f"minimum value must be {at_least_str} $min_value."

        if renderer_configuration.include_column_name:
            template_str = f"$column {template_str}"

        renderer_configuration.template_str = template_str

        return renderer_configuration

    @classmethod
    @override
    @renderer(renderer_type=LegacyRendererType.PRESCRIPTIVE)
    @render_evaluation_parameter_string
    def _prescriptive_renderer(  # type: ignore[override] # TODO: Fix this type ignore
        cls,
        configuration: ExpectationConfiguration,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        runtime_configuration = runtime_configuration or {}
        include_column_name = (
            False if runtime_configuration.get("include_column_name") is False else True  # noqa: SIM211
        )
        styling = runtime_configuration.get("styling")
        params = substitute_none_for_missing(
            configuration.kwargs,
            [
                "column",
                "min_value",
                "max_value",
                "row_condition",
                "condition_parser",
                "strict_min",
                "strict_max",
            ],
        )

        if (params["min_value"] is None) and (params["max_value"] is None):
            template_str = "minimum value may have any numerical value."
        else:
            at_least_str, at_most_str = handle_strict_min_max(params)

            if params["min_value"] is not None and params["max_value"] is not None:
                template_str = (
                    f"minimum value must be {at_least_str} $min_value and {at_most_str} $max_value."
                )
            elif params["min_value"] is None:
                template_str = f"minimum value must be {at_most_str} $max_value."
            elif params["max_value"] is None:
                template_str = f"minimum value must be {at_least_str} $min_value."
            else:
                template_str = ""

        if include_column_name:
            template_str = f"$column {template_str}"

        if params["row_condition"] is not None:
            (
                conditional_template_str,
                conditional_params,
            ) = parse_row_condition_string_pandas_engine(params["row_condition"])
            template_str = f"{conditional_template_str}, then {template_str}"
            params.update(conditional_params)

        return [
            RenderedStringTemplateContent(
                content_block_type="string_template",
                string_template={
                    "template": template_str,
                    "params": params,
                    "styling": styling,
                },
            )
        ]

    @classmethod
    @renderer(renderer_type=LegacyDescriptiveRendererType.STATS_TABLE_MIN_ROW)
    def _descriptive_stats_table_min_row_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        assert result, "Must pass in result."
        return [
            {
                "content_block_type": "string_template",
                "string_template": {
                    "template": "Minimum",
                    "tooltip": {"content": "expect_column_min_to_be_between"},
                },
            },
            f"{result.result['observed_value']:.2f}",
        ]

    @override
    def _validate(
        self,
        metrics: Dict,
        runtime_configuration: Optional[dict] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        return self._validate_metric_value_between(
            metric_name="column.min",
            metrics=metrics,
            runtime_configuration=runtime_configuration,
            execution_engine=execution_engine,
        )
