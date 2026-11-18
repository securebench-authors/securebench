# raman-fitting

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/raman-fitting

## How the pack grades

The agent fits Lorentzians to the G and 2D peaks of `/app/graphene.dat` and writes the
eight parameters to `/app/results.json`. Upstream's `tests/test_outputs.py` has three
tests, all reading that one file:

| Upstream test | Case challenge | What the Oracle requires |
|---|---|---|
| `test_result_file_exists` | `{}` | `Path("/app/results.json").exists()` is true |
| `test_G_Peak` | `{"peak": "G"}` | the file loads, `data["G"]` has `x0`, `gamma`, `amplitude`, `offset` within upstream's tolerances |
| `test_2D_Peak` | `{"peak": "2D"}` | the same for `data["2D"]` |

The single protocol check `results` has these three cases. Its adapter,
`evaluation/adapter.py`, runs the calls upstream's test makes (`Path.exists`,
`json.load(open(...))`, `data[peak]`, `section[name]`) with the baseline's own Python 3.13
(`/usr/local/bin/python3 -I`, outside the scope, so the candidate cannot change it) and
reports, for each field, its Python type and the float that upstream's arithmetic would
use. The Oracle applies upstream's comparisons verbatim: `abs(value - expected) < tol`
for the absolute tolerances and `abs(1 - value / expected) < tol` for the relative ones.
The expected values, tolerances and comparison forms are copied from the test into
`hidden/cases.json`; the reference solution reproduces them (G: 1580.297, 9.061, 8382.692,
5561.035; 2D: 2670.082, 17.520, 12314.417, 1239.092).

A protocol check is used rather than an artifact check so that the file is parsed by
Python's `json` module, as upstream parses it, and not by SecureBench's strict JSON
parser (see "Parsing" below).

### How each value maps to upstream's arithmetic

- An `int` or `bool` value is reported as `float(value)`. Upstream's `x0 - expected` and
  `A / expected` perform exactly this conversion (and raise `OverflowError` for an int
  beyond the float range, which the adapter reports as an int without a value).
- A float is reported as itself; JSON numbers round-trip exactly between the adapter's
  `json.dumps` and SecureBench's parser.
- NaN and infinities are reported without a value, and the Oracle fails a field without
  a value. Upstream's comparisons are all false for NaN and for infinities (for example
  `abs(inf - 1580.3) < 5`), so these always fail upstream too.
- Strings, null, lists, objects and missing keys are reported without a value. Upstream
  raises `TypeError` or `KeyError` on them.

### Differential against upstream's test

`hidden/differential/gen.py` writes 331 crafted `results.json` files in the baseline
image and records, for each, upstream's verdict on the three test functions and the
adapter's three observations; `hidden/differential/judge.py` runs the pack's Oracle on
those observations. The inputs concentrate on the thresholds: for each of the eight
fields, the boundary value and its three nearest floats on each side, ±1e-12 relative,
and the rounded integers around the boundary; plus every non-numeric type, NaN,
`Infinity`, `1e999`, 400-digit and 5000-digit integers, missing keys, non-object
documents and peaks, duplicate keys, a leading BOM, trailing garbage, NaN in extra
fields, Latin-1 bytes, deep nesting, an empty file, a missing file and a directory.
Result: 993 test verdicts, 541 passing and 452 failing upstream, 0 disagreements.

To rerun: copy `gen.py`, upstream's `tests/test_outputs.py` and `evaluation/adapter.py`
into one directory, run `docker run --rm --network none -v <dir>:/d <baseline image>
python /d/gen.py`, then on the host
`uv run python -B <dir>/judge.py <dir>/out.json task/hidden/oracle.py task/hidden`.

## Fidelity changes

- **Scope: `/app` with every path below a subdirectory excluded (`*/*`)** — equivalent.
  Upstream grades only `/app/results.json`. Excluding the contents of subdirectories keeps
  virtual environments, caches and downloads an agent leaves in `/app` from pushing the
  capture past its bounds; none of them is read by grading. Top-level files of `/app`
  remain in scope, with the maximum bounds (100,000 entries, 2 GiB).
- **Capture failures on unusual top-level files** — stricter. A candidate that leaves
  more than 2 GiB or a device, socket or named pipe directly in `/app`, or makes
  `/app/results.json` a symlink pointing outside `/app`, fails at capture. Upstream would
  ignore the extra files, and would follow such a symlink. Symlinks inside `/app` are
  allowed (`symlinks = true`), but one whose target lies below an excluded subdirectory
  resolves to the baseline's empty directory and fails.
- **Python patch version** — equivalent. Upstream runs the test with uv's Python 3.13
  build; the adapter uses the baseline's Python 3.13.7. The `json` module and the
  int-to-float conversion behave the same across 3.13 patch releases. Both run in UTF-8
  mode with no `LANG` set, so `open()` decodes UTF-8 strictly in both; the adapter states
  `encoding="utf-8"` explicitly.
- **Parsing** — equivalent. Because the adapter uses Python's `json.load`, the leniencies
  upstream accepts are kept: duplicate keys (last wins), `NaN` and `Infinity` in fields
  the test does not read. An artifact check would have rejected those files.
- **Cases** — equivalent. Three cases, one per upstream test, each judged alone.
- **Allowed domains: `pypi.org`, `files.pythonhosted.org`** — equivalent. Upstream allows
  all internet; the reference needs only pip's index to install scipy and numpy.
- **Timeouts and output bounds** — stricter only in theory. Each case has 120 seconds and
  a 4 KiB observation; the adapter reads one file and writes eight numbers. A
  `results.json` large enough to exhaust the case's memory fails as `case_error`, where
  upstream's test, with more memory, might parse it.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `#!/bin/sh` and `cd /app` added; the
  body is byte for byte upstream's.
- `null.sh`: changes nothing.
- `mutant-linear-background.sh`: Lorentzian plus a linear background. Lands the 2D offset
  8.75% from upstream's value, near the 10% relative tolerance the Oracle reimplements.
  Passes both.
- `mutant-fwhm.sh`: reports gamma as the full width (twice the half width). Fails the
  absolute gamma tolerance in both.
- `mutant-int-values.sh`: rounds every value to a JSON integer, exercising the
  int-to-float conversion in the adapter. Passes both.
- `mutant-string-values.sh`: serializes numpy float32 values with `default=str`, so
  every value is a string. Fails both.
- `mutant-nonfinite-extra.sh`: correct fields plus uncertainty fields holding `NaN` and
  `Infinity`, which Python's `json` writes and reads but strict JSON rejects. Passes both.
- `fit_variants.py`: the fitting code the mutants share; each mode changes only the model
  or how the results are written.
- `attack-shadow-modules.sh`: plants `json.py`, `pathlib.py`, `math.py`,
  `sitecustomize.py` and `usercustomize.py` in the adapter's working directory to forge an
  observation without values, and writes a wrong `results.json` with verdict claims.
- `attack-nonfinite-overflow.sh`: NaN, infinities, `1e999` and 400-digit integers, aimed
  at crashing the adapter or the Oracle or slipping a NaN past an inverted comparison.
- `attack-fifo.sh`: makes `/app/results.json` a named pipe so that opening it would hang
  the adapter.

## Divergences from native

Every mutant, the reference and the null candidate get the same verdict from both graders
(reference and `mutant-int-values`, `mutant-linear-background`, `mutant-nonfinite-extra`
pass; null, `mutant-fwhm`, `mutant-string-values` fail). The attacks
`attack-shadow-modules` and `attack-nonfinite-overflow` fail in both.

- `attack-fifo`: SecureBench `failed` (class `capture`: a named pipe in the scope is
  rejected); native ended in `error: VerifierTimeoutError` after 30 minutes, because
  upstream's `open("/app/results.json")` blocks forever on the pipe. SecureBench is right:
  the candidate delivers no results, so it must fail. Natively the hang turns a wrong
  candidate into a verifier error instead of a reward of 0, which is the escape hatch
  SecureBench closes.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-26

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: one root, `/app`, with `exclude = ["*/*"]`. Under the 4.6 rules this matches every two-component path and everything below it, so top-level files and directory entries of `/app` are captured and the contents of subdirectories are not. The only deliverable, `/app/results.json`, is top-level. The adapter loads no files from the scope: it runs the baseline's `/usr/local/bin/python3 -I`, which is outside the scope, keeps the working directory off `sys.path` and reads no `pyvenv.cfg` or `._pth` from `/app`. So no candidate code runs in the Evaluation, and there are no test or convention-loaded files to exclude. The baseline's `/app` holds only `graphene.dat` and has no symlinks (checked in the image). Two stricter cases are recorded as fidelity changes: a `results.json` symlink into an excluded subdirectory, and one that points out of `/app`.
3. Leaks: the expected values are only in `hidden/cases.json` and `hidden/differential/gen.py`. `evaluation/` holds an adapter and schemas with no values. In the baseline image, I found no `test_outputs*`, `solve.sh`, `results.json` or `*raman*` file, and grep found no expected value (1580.3, 8382.69, 12314.42, 5561.03, 1239.09, 2670.08, 17.52) anywhere in the filesystem. The allowed domains are `pypi.org` and `files.pythonhosted.org`. The latest `terminal-bench` (0.2.18), `harbor` (0.25.0) and `inspect-evals` (0.26.0) wheels contain neither this task nor its expected values. No limitation section is needed.
4. Challenges: `{}` or `{"peak": "G"|"2D"}`. They carry no hidden material.
5. Cases: three cases, one per upstream test (`test_result_file_exists`, `test_G_Peak`, `test_2D_Peak`). None was added, and the seed is not used.
6. Oracle: every expected value, tolerance and comparison form is in `hidden/cases.json`, and all eight match `tests/test_outputs.py` (absolute for G x0 and both gammas, relative for the rest). `oracle.py` holds only `abs(v - e) < t` and `abs(1 - v / e) < t`. It requires a finite value for all four fields of the peak and fails closed on a missing value, a non-object observation or a malformed context. It ignores extra fields and claims. Its work is constant-size. The adapter's `float()` on int and bool reproduces upstream's implicit conversion, including `OverflowError`. I reran the differential (`gen.py` in the baseline with `--network none`, then `judge.py`) and got 993 verdicts with 0 disagreements. No regression tests run by outcome.
7. Candidates: `reference.sh` is upstream `solve.sh` with only `#!/bin/sh`, a comment and `cd /app` added (checked with diff). The mutants run real fits through `fit_variants.py` and aim at the places where this conversion differs from upstream's assertion: int-to-float conversion (int-values), `NaN`/`Infinity` that strict JSON would reject (nonfinite-extra), the reimplemented relative tolerance near its edge (linear-background), the absolute tolerance (fwhm) and non-numeric types (string-values). The attacks aim at this task's adapter: shadow stdlib modules in its working directory, non-finite and overflowing values, and a FIFO deliverable. No candidate code runs in the Evaluation, so a forged observation is not possible here. There is no mutant for a symlink into an excluded subdirectory. That is a capture-level stricter case recorded under fidelity changes, not a check comparison.
8. Divergences: `qualification.json` reports `"problems": []`. Every SecureBench run records pack digest `sha256:57e09842d319cf36dc9d7cc60cf27dc109255ecc99854c04174e8ae328f1be60`, the digest I noted at the start and again at the end. The runs record three framework commits (40574fe, 50cfacc, 402bbb9), but `git diff` shows no change outside `conversions/` and `docs/` between them, and none is dirty. Reference and mutants agree with native. The only divergence is `attack-fifo`: SecureBench gives `failed`/`capture`, native gives `VerifierTimeoutError`. The explanation holds: upstream's `open()` blocks on the pipe, and a candidate with no results must fail.
9. Inventory: there is no row for this task yet (the coordinator adds it after review). There is no exclusion reason to check.

Upstream assertions: `assert result_path.exists()` maps to case 0 (`exists is True`). In each peak test, `json.load`, `data[peak]`, the four key lookups and the four combined comparisons map to cases 1 and 2 (`loaded`, `fields`, one value per field, the tolerance from `cases.json`). `test.sh` gives reward 1 only when all tests pass, which matches SecureBench's every-case rule. No assertion is dropped.

Findings (non-blocking; they correct the record and do not touch the pack digest):
- `CONVERSION.md` line 56: "541 passing and 452 failing upstream" is wrong. Rerunning the committed `gen.py` gives 750 passing and 243 failing (exists 330/1, G 210/121, 2D 210/121). A venue reviewer who reruns the differential will see a different count.
- `CONVERSION.md` line 76: "Upstream runs the test with uv's Python 3.13 build" is probably inaccurate. uv 0.9.5 prefers a Python already on the system over downloading one, so `uvx -p 3.13` most likely uses the baseline's own `/usr/local/bin/python3.13` (3.13.7). The conclusion ("equivalent") holds either way.
- `CONVERSION.md` line 90: "upstream's test, with more memory" has no support. Both graders run with the upstream `memory_mb = 2048`. The point to make is that the per-case timeout (120 s, against upstream's 900 s verifier timeout) is the stricter bound.

Verdict: approved
