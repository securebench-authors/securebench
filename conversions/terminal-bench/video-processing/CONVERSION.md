# video-processing

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/video-processing

## How the pack grades

The agent writes `/app/jump_analyzer.py`, which reads an MP4 of a hurdle jump and
writes the takeoff and landing frame numbers to `/app/output.toml`. Upstream's
`tests/test_outputs.py` has five tests; each becomes one case of a protocol check.
All adapters run on the baseline's own Python 3.13.7 (`/usr/local/bin/python3 -I`),
the same interpreter version the native verifier uses.

| Upstream test | Check, case | What the adapter reports | What the Oracle requires |
|---|---|---|---|
| `test_example_video_exists` | `video-exists` #0 | `Path("/app/example_video.mp4").exists()` | true |
| `test_test_video_exists` | `video-exists` #1 | `Path(...).exists()` for the pack's copy of the hidden video | true |
| `test_jump_analyzer_example_video` | `jump-analyzer` #0 | the steps of `_test_jump_analyzer_video` on `/app/example_video.mp4` | the assertions below, ranges [50, 54] and [62, 64] |
| `test_jump_analyzer_test_video` | `jump-analyzer` #1 | after an unjudged run on the example video, the same on `/tests/test_video.mp4` | ranges [219, 223] and [231, 234] |
| `test_jump_analyzer_imports` | `imports` #0 | after unjudged runs on both videos, the top-level module names the AST of `/app/jump_analyzer.py` imports, by upstream's own walk | every name is in Python 3.13's `sys.stdlib_module_names` or in {cv2, numpy, toml} |

Natively the five tests run in file order in one container, so each test sees
every file the script runs of the tests before it left: `output.toml`, caches,
even a rewritten `jump_analyzer.py`. SecureBench starts every case from the
captured candidate, so `evaluation/native_runs.py` first replays those earlier
runs in the case, unjudged, exactly as upstream's helper runs the script (and
only when that test's video exists, as the helper asserts before running). It
also places the hidden video at `/tests/test_video.mp4` in every case, where it
sits natively from the start.

`evaluation/run_analyzer.py` follows `_test_jump_analyzer_video` step by step and
reports one fact per assertion: whether the video exists; the exit status of
`python /app/jump_analyzer.py <video>` run in `/app`; whether its captured standard
output and error decode as UTF-8 (upstream's `subprocess.run(..., text=True)`
raises when they do not); whether `/app/output.toml` exists and loads with
toml 0.10.2; and, for each of the two fields, whether it is present, its kind
(integer, float, boolean or other) and its numeric value. The Oracle checks these
in upstream's order and compares each value with the inclusive range from
`hidden/cases.json`. Upstream's `low <= value <= high` accepts any int, float or
bool in range and raises `TypeError` for every other TOML type, so the Oracle
accepts exactly the integer, float and boolean kinds.

Expected values live in `hidden/`: the frame ranges and the allowed third-party
modules are literals from `tests/test_outputs.py` (`hidden/cases.json`), and
`hidden/stdlib_module_names.json` is `sorted(sys.stdlib_module_names)` printed by
the baseline's Python 3.13.7:

```
docker run --rm --network none alexgshaw/video-processing@sha256:a2c0f39e3ab04e67ac6e49cad9167bb0d987babe32511768c01aa0c6905a875f \
  python3 -c "import sys,json;print(json.dumps(sorted(sys.stdlib_module_names), indent=0))"
```

## Fidelity changes

- **Python stack that runs the candidate's script (equivalent, measured).** The
  native verifier runs the script with `sys.executable` of a `uvx` environment
  holding `opencv-contrib-python==4.11.0.86`, `toml==0.10.2`, pytest and the
  newest numpy at grading time (2.5.4 when we checked). The Evaluation has no
  network, so the script runs on the baseline's own Python 3.13.7, which has
  `opencv-contrib-python` 4.12.0.88 and numpy 2.2.6. We compared the two stacks
  on both videos, in the baseline image with and without a venv holding the
  native versions: the decoded frames, the masks of the MOG, MOG2, KNN and GMG
  background subtractors on blurred grey frames, the bounding boxes of contours
  of the MOG2 masks, `absdiff` against the first frame and Farneback optical
  flow are byte-identical (SHA-256 of every frame's output), and the reference
  writes the same frame numbers under both (54/63 and 222/232). Other OpenCV or
  numpy functions could still differ between the versions; we found none that a
  solution to this task plausibly uses. pytest and its dependencies are not
  importable here, but a script that imports them fails the imports test anyway.
- **toml 0.10.2 shipped in the pack (equivalent).** The baseline image has no
  `toml`, which the native verifier installs at grading time and the
  instructions promise. `evaluation/pylib/` holds the unmodified contents of
  `toml-0.10.2-py2.py3-none-any.whl` (pure Python; wheel SHA-256
  `806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b`, as
  published on PyPI). The adapter puts it on the script's `PYTHONPATH` and loads
  `output.toml` with it, opening the file as `toml.load` does (`io.open` with
  UTF-8 and universal newlines).
- **No allowed domains (stricter).** Upstream allows the agent full internet
  access; the reference needs none, so the pack allows no domain. An agent here
  cannot `pip install` anything, including `toml`, which the instructions say is
  available but the image lacks. A solution can still import `toml` (the
  Evaluation provides it, as natively); the agent just cannot run that import
  while developing.
- **Hidden video path (equivalent).** The pack's copy of `tests/test_video.mp4`
  is on the read-only evaluation mount. Every case that runs the script first
  copies it to `/tests/test_video.mp4`, the path upstream passes, so a script that writes next
  to its input or keys on the path sees what it sees natively.
  `test_test_video_exists` checks the pack's copy, which no candidate can remove,
  as natively no agent can remove `/tests`.
- **Earlier test runs replayed inside each case (equivalent).** Cases must be
  independent, while upstream's tests share one container. `jump-analyzer` #1
  replays the example-video run before the test-video run, and `imports` #0
  replays both runs before it parses the script, so each starts from the state
  the native session has at that test: `output.toml` and every other file the
  earlier runs wrote or rewrote. The scope does not exclude `output.toml`, so
  case #0 starts, as natively, from whatever `output.toml` the agent left.
  `mutant-append-output.sh` (a writer that appends) checks this. What is not
  replayed: the existence tests and the earlier tests' reading of
  `output.toml`, none of which changes a file. Background processes an earlier
  run leaves behind keep running within the case, as natively.
- **Timeout (more lenient).** Natively one 3,600 s budget covers installing the
  verifier's tools (uv, Python packages) and every test. Here each case that
  runs the script has 3,600 s for all the runs it replays, the longest being
  `imports` #0 with both runs. A script whose runs fit in 3,600 s but not once
  the native install time (tens of seconds) is added passes here and fails
  natively. The reference takes 2 to 4 s per video.
- **Bounded `output.toml` (stricter).** The adapter reads `output.toml` only if it
  is a regular file of at most 4 MiB. Natively a larger file is parsed, and a
  FIFO or device hangs or fails the test.
- **Bounded import list (equivalent).** The `imports` adapter truncates module
  names to 256 bytes and reports at most 4,096 distinct names with their count.
  Every allowed name is far shorter than 256 bytes, so truncation never makes a
  forbidden name allowed, and more than 4,096 distinct names cannot all be
  standard library or allowed (the list holds 290), so the Oracle fails a
  truncated list. The file is read as UTF-8, which is what `read_text()` uses in
  the verifier (no `LANG`, so Python's UTF-8 mode).
- **Numbers outside JSON's range (equivalent).** Integers beyond ±(2^63 − 1) and
  non-finite floats are reported as `out_of_bounds` and fail; natively they lie
  outside every range or (NaN) compare false, and fail.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `cd /app` added.
- `null.sh`: changes nothing.
- `mutant-forbidden-import.sh`: a guarded `import tomli_w`; targets the imports
  check and the Oracle's standard library list.
- `mutant-stdlib-writer.sh`: writes float frame numbers by hand with CRLF line
  endings and checks them with `tomllib`; correct per upstream, so it should pass
  both graders. Targets the adapter's value conversion and the standard library
  list.
- `mutant-append-output.sh`: opens `output.toml` in append mode; the first run
  writes a correct file, the replayed second run adds duplicate keys, which
  toml 0.10.2 rejects. Targets the replay of earlier runs.
- `mutant-output-beside-video.sh`: writes `output.toml` next to the input video;
  the test-video case then reads the example run's `/app/output.toml`, as
  natively. Targets the replayed state and the placed video path.
- `mutant-latin1-stdout.sh`: prints a raw Latin-1 byte; targets the adapter's
  reimplementation of `text=True` decoding.
- `attack-stale-output.sh`: leaves an `output.toml` with the example video's
  values behind and ships a script that writes nothing. It passes the
  example-video case, as natively, and fails the hidden one.
- `attack-forged-observation.sh`: the script writes a forged response envelope to
  the adapter's standard output (numeric kinds with no values) and kills the
  adapter.
- `attack-wrapped-values.sh`: writes 2^64 + 222 and 2^64 + 232 (which wrap to
  the hidden video's answers in 64-bit arithmetic), NaN, and verdict claims.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-stdlib-writer` pass both; the null
candidate, the other four mutants and the three attacks fail both (native
reward 0.0). In SecureBench `attack-forged-observation` ends `failed`, class
`case_error`, and every other failure has class `oracle`.


## Review

Reviewer: ab3e6f06fa03ed08b, 2026-10-27 (second review, after the converter addressed the first review's findings)

Pack reviewed: `securebench validate` reports it valid, digest `sha256:7e7b100d27b7604aa1d03722d8a261b6b7b7d1e2c1049293c14cb1af67b2564a`.

1. Instructions. `cmp task/instructions.md` with upstream `instruction.md`: identical.
2. Scope. One root, `/app`, with no exclude patterns now. The `output.toml` exclusion was dropped, so the agent's leftover file is replayed, as it is present natively. Upstream has no test or convention-loaded files under `/app`. The tests live in `/tests`, outside the scope. The adapters run `/usr/local/bin/python3 -I`, also outside the scope, and nothing in `/app` loads into them. The baseline's `/app` holds only `example_video.mp4` (same SHA-256 as upstream's) and no symlinks. Every solution the instructions allow fits in `/app`.
3. Expected values. The ranges and the allowlist are in `hidden/cases.json` and match `tests/test_outputs.py`. `hidden/stdlib_module_names.json` equals the baseline Python 3.13.7's `sys.stdlib_module_names`: I regenerated it and got the same 290 names. `evaluation/` holds the test video, the adapters, the schemas and toml 0.10.2. The test video is an input, byte-identical to upstream's. The toml files match the wheel's `RECORD` hashes. The new `native_runs.py` holds no expected value. The baseline image has no `/tests`, no test video, no `output.toml` and no `jump_analyzer.py`. There are no allowed domains, so no limitation section is needed.
4. Challenges. Each carries paths only: the video to place, the earlier runs to replay, and the video or file to check. No range reaches the Evaluation.
5. Cases. Five cases for upstream's five tests, none added. The replayed runs are unjudged state setup that reproduces the native session order, not new cases. The seed is unused, correctly.
6. Oracle. It is unchanged since the first review. It holds no expected value. It checks, in upstream's order, video existence, UTF-8 decoding of the captured output, exit status, presence and parse of `output.toml`, both fields and the inclusive ranges. It requires a numeric `value` for every numeric kind, and it treats bool, int and float as Python's `low <= v <= high` does. The imports judge fails a truncated list and checks every name against the stdlib list plus the allowlist. Work over candidate data is bounded by the schemas, and claims are ignored. No regression tests are run by outcome.
   With the replay, candidate code now also runs in the `imports` case before the AST walk. Everything the adapter needs afterwards is imported first, and the evaluation mount is read-only. A candidate could still forge an empty import list there. The values that check compares against (the standard library and cv2, numpy, toml) are public, and natively the script can rewrite its own imports before the imports test reads the file. So this is outside scope, not a finding.
7. Candidates. The reference is upstream's `solve.sh` with only `cd /app` added. There are five mutants, all running real code: forbidden import, stdlib writer, append writer, output beside the video, and Latin-1 output. They target the stdlib list, the bundled toml and the value kinds, the replayed state, the placed video path and the reimplemented `text=True` decode. The new `mutant-append-output.sh` is the one the first review asked for: native gives 0.0 and SecureBench gives `failed`. The three attacks (forged observation, stale output, wrapped values) target this task's adapter takeover, leftover output and number conversion, and all end `failed`.
8. Divergences. `qualification.json` reports `problems: []`. All ten SecureBench runs are admitted, rejudged, made with a clean framework (`d65a335`) and record the digest above. The reference and `mutant-stdlib-writer` pass both graders. Every other candidate fails both, with native reward 0.0 and no cached native result. "None" in "Divergences from native" is correct.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet, and no exclusion is claimed.

Upstream assertions: `test_example_video_exists` and `test_test_video_exists` map to `video-exists` #0 and #1. Every assertion of `_test_jump_analyzer_video` maps to `jump-analyzer`: video exists, exit 0, the implicit `text=True` decode, `output.toml` exists, it parses, both fields are present, and both ranges hold. `test_jump_analyzer_imports` (the file exists, the implicit `ast.parse`, no forbidden imports) maps to `imports`, now run on the state the native session has at that test. None is dropped.

First review's findings:
- Fixed: the test-video case started without the example run's state, and the change was mislabelled. `native_runs.py` now places the hidden video at `/tests/test_video.mp4` in every case. It replays the example-video run before the test-video case and both runs before the imports case, each only when its video exists, as upstream's helper asserts before running. The scope no longer excludes `output.toml`. CONVERSION.md describes this as "Earlier test runs replayed inside each case (equivalent)". The append-mode mutant now fails both graders.
- Fixed: the timeout label. It is now "more lenient", which is correct. Each case that runs the script has 3,600 s for all its replayed runs, and natively the same 3,600 s also covers the tool install.

Findings: none.

Verdict: approved
