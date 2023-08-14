---
title: Levels  of Maturity
---

Features and code within Great Expectations are separated into three levels of maturity: Experimental, Beta, and Production.

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer" />
<div>
    <ul style={{
        "list-style-type": "none"
    }}>
        <li><i class="fas fa-circle" style={{color: "#dc3545"}}></i> &nbsp; Experimental: Try, but do not rely</li>
        <li><i class="fas fa-circle" style={{color: "#ffc107"}}></i> &nbsp; Beta: Ready for early adopters</li>
        <li><i class="fas fa-check-circle" style={{color: "#28a745"}}></i> &nbsp; Production: Ready for general use</li>
    </ul>
</div>

Being explicit about these levels allows us to enable experimentation, without creating unnecessary thrash when features and APIs evolve. It also helps streamline development, by giving contributors a clear, incremental path to create and improve the Great Expectations code base.

For users of Great Expectations, our goal is to enable informed decisions about when to adopt which features.

For contributors to Great Expectations, our goal is to channel creativity by always making the next step as clear as possible.

This grid provides guidelines for how the maintainers of Great Expectations evaluate levels of maturity. Maintainers will always exercise some discretion in determining when any given feature is ready to graduate to the next level. If you have ideas or suggestions for leveling up a specific feature, please raise them in Github issues, and we’ll work with you to get there.


| Criteria                                 | <i class="fas fa-circle" style={{color: "#dc3545"}}></i> Experimental <br/>Try, but do not rely | <i class="fas fa-circle" style={{color: "#ffc107"}}></i> Beta <br/>Ready for early adopters | <i class="fas fa-check-circle" style={{color: "#28a745"}}></i> Production <br/>Ready for general use |
|------------------------------------------|--------------------------------------|----------------------------------|-------------------------------------|
| API stability                            | Unstable*                            | Mostly Stable                    | Stable                              |
| Implementation completeness              | Minimal                              | Partial                          | Complete                            |
| Unit test coverage                       | Minimal                              | Partial                          | Complete                            |
| Integration/Infrastructure test coverage | Minimal                              | Partial                          | Complete                            |
| Documentation completeness               | Minimal                              | Partial                          | Complete                            |
| Bug risk                                 | High                                 | Moderate                         | Low                                 |


:::note
Experimental classes log warning-level messages when initialized: 

`Warning: great_expectations.some_module.SomeClass is experimental. Methods, APIs, and core behavior may change in the future.`
:::

## Contributing Expectations

The workflow detailed in our initial guides on [Creating Custom Expectations](../guides/expectations/creating_custom_expectations/overview.md) will leave you with an Expectation ready for contribution at an Experimental level. The checklist generated by the `print_diagnostic_checklist()` method will help you walk through the requirements for Beta & Production levels of contribution;
the first four checks are required for Experimental acceptance, the following three are additionally required for Beta acceptance, and the final three (a full checklist!) are required for Production acceptance. Supplemental guides are available to help you satisfy each of these requirements.

| Criteria                                 | <i class="fas fa-circle" style={{color: "#dc3545"}}></i> Experimental <br/>Try, but do not rely | <i class="fas fa-circle" style={{color: "#ffc107"}}></i> Beta <br/>Ready for early adopters | <i class="fas fa-check-circle" style={{color: "#28a745"}}></i> Production <br/>Ready for general use |
|------------------------------------------|:------------------------------------:|:--------------------------------:|:-----------------------------------:|
| Has a valid library_metadata object            | &#10004; | &#10004; | &#10004; |
| Has a docstring, including a one-line short description | &#10004; | &#10004; | &#10004; |
| Has at least one positive and negative example case, and all test cases pass | &#10004; | &#10004; | &#10004; |
| Has core logic and passes tests on at least one Execution Engine | &#10004; | &#10004; | &#10004; |
| Has basic input validation and type checking | &#8213; | &#10004; | &#10004; |
| Has both Statement Renderers: prescriptive and diagnostic | &#8213; | &#10004; | &#10004; |
| Has core logic that passes tests for all applicable Execution Engines | &#8213; | &#10004; | &#10004; |
| Passes all linting checks | &#8213; | &#8213; | &#10004; |
| Has a robust suite of tests, as determined by a code owner | &#8213; | &#8213; | &#10004; |
| Has passed a manual review by a code owner for code standards and style guides | &#8213; | &#8213; | &#10004; |