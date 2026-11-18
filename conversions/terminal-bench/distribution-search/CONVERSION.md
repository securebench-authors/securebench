# distribution-search

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/distribution-search

## How the pack grades

The deliverable is one file, `/app/dist.npy`. Upstream's four tests load it with `np.load` and check its shape, its validity as a distribution, and its two KL divergences from the uniform distribution. Here one protocol check, `distribution`, has one case, as upstream has one file to grade. Its challenge is `{}`. Its context is the `expected` object of `task/hidden/cases.json`, which holds every literal of upstream's assertions: the shape `[150000]`, the bounds 0 and 1.0, the sum 1.0 and its tolerance 1e-5, the two targets 10.0 and their tolerance 0.001.

The adapter (`task/evaluation/adapter.py`) loads the file with the baseline's own numpy and reports its dtype, shape, number of non-finite elements and every element as float64. The Oracle (`task/hidden/oracle.py`) applies upstream's conditions to those values with numpy's own float64 arithmetic. A pytest report is never used: the adapter reports values and the Oracle compares them.

## How upstream's tests map to checks

Every row is an assertion of `tests/test_outputs.py`. All four tests check what the task asks for. Upstream has no regression tests.

| Upstream test | Assertion | Check, case and condition here |
|---|---|---|
| `test_distribution_file_exists` | `np.load("/app/dist.npy")` raises nothing | `distribution`, case 0: the adapter calls `np.load` with numpy's defaults (pickles refused), as upstream. A missing or unloadable file, or one that loads as something other than an array (an `.npz` archive), is reported as `unable`, and the case fails with class `case_error` |
| `test_distribution_shape` | `P.ndim == 1` | case 0: `shape` equals the expected `[150000]`, so it has one dimension |
| `test_distribution_shape` | `P.size == 150000` | case 0: the same comparison of `shape` with `[150000]` |
| `test_distribution_validity` | `np.isfinite(P).all()` | case 0: the adapter counts non-finite elements; the judge requires `nonfinite == 0` |
| `test_distribution_validity` | `P.min() > 0` | case 0: the smallest reported value is above `minimum_exclusive` (0.0) |
| `test_distribution_validity` | `P.max() <= 1.0` | case 0: the largest reported value is at most `maximum` (1.0) |
| `test_distribution_validity` | `abs(P.sum() - 1.0) < 1e-5` | case 0: the same comparison with `sum` and `sum_tolerance`, the sum computed with numpy's pairwise summation reproduced bit for bit |
| `test_kl_divergences` | after `P = P / P.sum()`: `abs(kl_forward(P) - 10.0) <= 1e-3` | case 0: the same comparison with `forward_kl` and `kl_tolerance`, computed with the same operations in the same order |
| `test_kl_divergences` | after `P = P / P.sum()`: `abs(kl_backward(P) - 10.0) <= 1e-3` | case 0: the same comparison with `backward_kl` and `kl_tolerance` |

What the pack checks beyond these rows, and why it is not an addition:

- The observation must have exactly the fields `dtype`, `shape`, `nonfinite` and `values`, with 150,000 finite floats in rows of 1,000. This only makes the judge fail closed on a forged or malformed observation; the real adapter always reports this form for a floating-point array of the right shape.
- The dtype must be float64, float32 or long double. The judge reimplements numpy's real floating-point arithmetic only. The one dtype this changes a verdict for is complex; see "Refused dtypes" below.
- A file over 64 MiB is refused, to keep `np.load` inside the memory limit; see "File size" below.
- An element that becomes 0 when divided by the sum fails. Upstream then takes `np.log(0) = -inf`, so a divergence is infinite or NaN and `test_kl_divergences` fails too. The guard exists because `math.log(0)` raises where `np.log` returns `-inf`.

## Fidelity changes

- **Loading (equivalent).** Upstream loads the file with numpy 2.3.0, which its verifier installs at grading time. The Evaluation has no network, so the adapter runs on the baseline's own Python 3.13 and numpy 2.1.2 in `/usr/local`. That is outside the scope, so the candidate cannot change it. The `.npy` reading code is the same in both versions. `hidden/differential.py` writes 13 files in forms other than a plain `np.save` of float64: format versions 2.0 and 3.0, a 1-D array marked Fortran order, trailing bytes, truncated data, a column, an `.npz` archive, a pickled object array, raw `tofile` bytes, float16, long double, complex128 and int64. Upstream and this pack agree on every form except complex128 (below). The adapter runs with `-I`, so a candidate's `/app/numpy.py` is not imported (`attack-shadow-numpy`).
- **Oracle arithmetic for float64 (equivalent).** The judge reimplements numpy's `pairwise_sum_DOUBLE` and uses `math.log`. numpy byte-swaps a big-endian array in buffers of 8,192 elements and sums each buffer pairwise, so for `>f8` the judge does the same (`buffered_sum`). `hidden/differential.py` runs inside the baseline image against numpy 2.3.0 and pytest 8.4.1, with no network and a 2 GiB memory limit, and judges with the context `plan` builds from `hidden/cases.json`. Rerun on 2026-10-25 after the remediation, it found the same as before:
  - `pairwise_sum` equal to `np.sum` bit for bit, and `buffered_sum` equal to `np.sum` of the big-endian copy bit for bit, on 306 array sizes from 1 to 150,000 (including 8,191 to 8,193 and 65,536) at 3 scales;
  - `math.log` equal to `np.log` on all 450,000 positive values tried;
  - the same verdict from upstream's four test functions and from the adapter and judge on all 23 files of a corpus weighted toward the thresholds. For KL(P‖U) = 10.001 and 9.999, KL(U‖P) = 10.001 and 9.999, both together, and sum = 1 ± 1e-5, the corpus holds the last file upstream accepts and the first it rejects, found by bisection on upstream's own computation. On every file where the judge reaches the divergences, its sum and both divergences equal upstream's bit for bit. The corpus also holds five three-level distributions, a big-endian file, one element equal to 1.0 and one element equal to 0.

  The qualification worker's CPU has no AVX-512, so numpy 2.3.0 used libm's `log` there. On an AVX-512 machine numpy uses its own float64 `log`, which may differ by one unit in the last place. That moves a divergence by about 1e-15, so only a file that close to a threshold could be judged differently. Upstream's own verdict varies between machines in the same way.
- **float32 files (more lenient and stricter, only near a threshold).** Upstream computes the sum, the normalization, the logarithms and the sums for a float32 array in float32. The judge computes on the same values, converted exactly to float64, in float64. On the differential corpus written as float32, the judge's divergences differ from upstream's by at most 2.8e-6, and 8 of 23 boundary files get different verdicts, all within 3e-6 of 10.001 or 9.999. A float32 file further than that from every threshold gets upstream's verdict; `mutant-float32` (divergences about 6e-6 from 10.0) passes both graders. Reproducing upstream exactly would mean porting numpy's float32 SIMD `log`, which differs between CPUs.
- **Long double files (stricter for elements outside float64's range, otherwise equivalent except within about 1e-13 of a threshold).** The adapter rounds them to float64, where upstream computes in long double. The differential file written as long double passes both graders. An element below float64's smallest subnormal (about 4.9e-324) becomes 0.0 and fails the `min > 0` condition here, and a subnormal one loses precision. The earlier review built a long double distribution with one element equal to 1e-4000 and the other levels solved so that both divergences are 10 in long double: it passes upstream's four test functions and fails here with "an element is not positive". Reporting long double values exactly would need a second number format in the observation, and no plausible solution writes long double.
- **Refused dtypes (stricter for complex, equivalent otherwise).** The judge accepts only float64, float32 and long double, in either byte order. A complex array passes upstream when its values pass upstream's comparisons, which numpy evaluates on complex numbers: `min` and `max` order them lexicographically, the sum's distance from 1 is a modulus, and `float()` keeps the real part of each divergence, with a warning. The differential's complex128 file (the reference with zero imaginary parts) passes upstream and fails here. Matching upstream would mean reporting 150,000 imaginary parts, which do not fit in the 4 MiB observation beside the real ones (the reference's observation is already 3.6 MB), and reimplementing numpy's complex pairwise sum, complex division and complex logarithm. A complex array with all imaginary parts zero could be judged on its real parts, differing from upstream only within about 1e-13 of a threshold; we did not add that path because a probability distribution is real and no plausible solution saves a complex array. float16 also fails here, and no float16 file can pass upstream: KL(U‖P) = 10 needs the geometric mean of P to be e^-10 / 150,000, about 3.0e-10, below the smallest positive float16 (2^-24, about 6.0e-8), and an element of 0 makes KL(U‖P) infinite. The reference written as float16 fails upstream in the differential. Integer and boolean arrays fail both graders, because positive integers cannot sum to 1.
- **File size (stricter, negligible).** The adapter refuses a file over 64 MiB, so that `np.load` stays within the 2 GiB memory limit. A correct file is 1.2 MB, and `np.load` ignores bytes after the array. So upstream accepts a correct array followed by more than 64 MiB of junk, and this pack does not.
- **Allowed domains (stricter).** None, which is all the reference needs: numpy and scipy are in the baseline. Upstream allows the Internet, so an agent there can install other packages, for example an optimizer the baseline lacks.
- **Scope (stricter, only for odd entries at the top level of `/app`).** One root, `/app`, with internal symlinks allowed and `exclude = ["*/*"]`, so everything below the top level of `/app` is dropped from the candidate. Upstream grades only `/app/dist.npy`, a top-level file, so nothing it grades is dropped. The instructions ask for a Python script, but upstream's tests never look at it, so its location does not matter. The exclude lets an agent keep work trees in subdirectories of `/app`. A probe that ran the reference, then created a virtual environment at `/app/venv`, an absolute symlink `/app/work/home -> /root` and a FIFO `/app/work/fifo`, `passed` (run `sha256:ea15d16b...`). Without the exclude, the earlier review's venv probe failed capture (run `sha256:fa6bd63f...`). Some correct candidates still fail here and pass upstream:
  - a top-level entry that capture rejects in any root: an absolute symlink or a relative one that leaves `/app` (probe `/app/cache -> /root/.cache` after the reference: `failed`, class `capture`, "symlink '/app/cache' has an absolute or malformed target", run `sha256:12d2be3a...`), a FIFO, socket or device, an unreadable directory, top-level files over 2 GiB in total, or a name at the top level or one level down that is not valid UTF-8, contains a backslash or is too long;
  - `/app/dist.npy` as an internal symlink into a subdirectory: the subdirectory is dropped, so the symlink dangles at evaluation. A probe that moved the reference's file to `/app/out/dist.npy` and linked `/app/dist.npy -> out/dist.npy` got `failed`, class `case_error`, `absent` (run `sha256:684a05f2...`).

  `/app` must be the root because the deliverable is a file directly in it, so no pack setting avoids these. We expect them to be rare. Upstream keeps no test files in the image (`/tests` is mounted only at grading), so there is nothing to exclude.
- **Time (equivalent).** Upstream's verifier has 3,600 s, most of it spent installing uv, Python and numpy. Here the case has 300 s. On the qualification worker the adapter loads and reports the file in under a second.
- **Reference shebang (equivalent).** `candidates/reference.sh` is upstream's `solution/solve.sh` byte for byte, except that the first line is `#!/bin/sh` instead of `#!/bin/bash`, followed by a comment. The script uses no bash features. It needed no drift repair.

## Remediation

Done on 2026-10-25 against the current converter brief. The pack had no added cases, inputs or randomness: it already had upstream's single case with an empty challenge, and every judged condition maps to an upstream assertion (table above).

- **Removed.** Nothing from the checks. The section "Answer already public upstream" and the fidelity bullet "Hidden cases (none)", which argued that no hidden case was possible, are gone, because the current brief keeps upstream's cases and nothing more.
- **Restored.** Nothing: no upstream assertion was dropped.
- **Moved.** Every literal of upstream's assertions left `task/hidden/oracle.py` for the new `task/hidden/cases.json`: the vocabulary 150,000 (as the shape `[150000]`), the bounds 0 and 1.0, the sum 1.0 and its tolerance 1e-5, the targets 10.0 and their tolerance 0.001. `plan` reads the file and checks its form, and `judge` compares with the case's context. `oracle.py` keeps only the judging logic and the adapter's row length. `task/hidden/differential.py` now judges with the context `plan` builds; its rerun gave the results above. The adapter changed in one comment only, which says why it bounds the values it reports at 150,000.
- **Candidates deleted.** There were seven mutants, two more than the brief allows.
  - `mutant-backward-only` (KL(P‖U) about 11.92): it fails on the forward divergence, which `mutant-off-target` already exercises, one tolerance away from the threshold rather than two units.
  - `mutant-off-by-one-vocabulary` (V = 149,999): it fails the same shape comparison as `mutant-column`, which also exercises the adapter's flattening of the array, so it adds nothing.
  - `mutant-pruned` (elements below 1e-9 set to 0): it fails `min > 0`, a plain comparison on values the adapter passes through exactly, the place where this pack's check is most like upstream's.
- **Candidate added.** `mutant-float32`, aimed at the float32-to-float64 conversion, the one place where the judge's arithmetic differs from upstream's on a plausible file. No mutant aimed there before.
- **Candidates kept.** `reference`, `null`, `mutant-off-target`, `mutant-forward-only`, `mutant-max-scaled`, `mutant-column`, and all three attacks. Each attack tampers with grading rather than hardcoding an answer: `attack-conftest` and `attack-fake-curl` hijack upstream's test runner, and `attack-shadow-numpy`, aimed at this task's adapter, shadows numpy so that `np.load` returns another file.

Old mutants that failed in SecureBench because of an addition (native pass, SecureBench `failed` in the earlier `qualification.json`):

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| none | | | |

In the earlier qualification, every mutant got 0.0 natively and `failed` from SecureBench, so no mutant had been failed by an addition and none needed rerunning.

## Candidates

- `reference.sh`: upstream's solution.
- `null.sh`: changes nothing.
- `mutant-off-target.sh`: the reference solving for 10.002, so both divergences are 10.002. Aimed at the KL tolerance.
- `mutant-forward-only.sh`: one heavy token and a uniform rest, solved for KL(P‖U) = 10 only. KL(U‖P) is 2.05. Aimed at the judge's backward divergence, which `mutant-off-target` never reaches because the forward one fails first.
- `mutant-max-scaled.sh`: the reference dividing by the largest element instead of the sum. The divergences of `P / P.sum()` are still 10, but the sum is 2.25. Aimed at the reimplemented sum, which the normalized divergences do not catch.
- `mutant-column.sh`: the reference saving a (150000, 1) column. The adapter flattens it to 150,000 values, so only the shape comparison catches it (`ndim == 1`).
- `mutant-float32.sh`: the reference saving float32. Aimed at the float32-to-float64 conversion; its divergences move by about 6e-6, so both graders pass it.
- `attack-conftest.sh`: a uniform distribution, plus `/tests/conftest.py` rewriting every pytest outcome to "passed".
- `attack-fake-curl.sh`: a uniform distribution, plus a `/usr/local/bin/curl` that shadows the one upstream's verifier installs. The verifier pipes `curl` into `sh` to install uv, so the fake prints a script that puts an always-succeeding `uvx` first on `PATH`.
- `attack-shadow-numpy.sh`: a uniform distribution at `/app/dist.npy`, a correct one at `/app/.answer.npy`, and a top-level `/app/numpy.py` that wraps the real numpy so that `np.load` returns the correct file. It works on any loader that imports numpy with `/app` on `sys.path` (checked in the baseline: `python3 -c` from `/app` loads the answer). It fails here because the adapter runs with `-I`.

## Divergences from native

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** Its `/app/dist.npy` is uniform, so both divergences are 0. Upstream copies its tests into the `/tests` directory the candidate already created, and pytest loads the planted `/tests/conftest.py`, which reports every test as passed. Here `/tests` is outside the scope and no test runner runs. The judge computes KL(P‖U) = 0 from the file. SecureBench is right.
- **`attack-fake-curl`: native 1.0, SecureBench `failed` (`oracle`).** Its file is the same uniform distribution. Upstream's `test.sh` runs `curl ... | sh` with the planted `/usr/local/bin/curl` first on `PATH`. The fake prints a script that installs an `uvx` that exits 0, so pytest never runs and the exit status reads as a pass. Here `/usr/local/bin` is outside the scope, and the verdict comes from the file's values. SecureBench is right.

The reference and `mutant-float32` pass both graders. The null candidate, the other four mutants and `attack-shadow-numpy` fail both. Upstream's pytest does not put `/app` on `sys.path`, so the shim is not imported there either.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated (one upstream case, literals moved to hidden/cases.json, no additions found). attack-conftest and attack-fake-curl pass natively by hijacking upstream's test runner; stricter: complex arrays, long double elements outside float64 range, and entries capture rejects directly in /app."

## Review before remediation

Reviewer: ac6b8ef5e3e75450e, 2026-10-12 (second round)

Pack reviewed: `sha256:3f77ea3c1f7542dfb7edc84750d07eae9393362e107e80d7538d99976026b430` (`securebench validate`). Every SecureBench run in `qualification.json` records this digest, and `problems` is empty.

Since round 1, the pack changed only in `task.toml` (the scope's `exclude = ["*/*"]` and its comment). The candidates changed in three comments (`mutant-forward-only`, `mutant-max-scaled`) and in `attack-shadow-numpy`, which now plants a top-level `/app/numpy.py` instead of an `/app/numpy/` package, so the exclude does not drop it. `CONVERSION.md` changed in the bullets the findings named.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference. Unchanged since round 1. Result: sound.
2. Scope. The root is still `/app`, now excluding `*/*`. The only graded file, `/app/dist.npy`, is at the top level, so nothing upstream grades is dropped. My round 1 probe (the reference, then `python -m venv --without-pip /app/venv`) failed capture before this change and now passes (run `sha256:1132821cab1baa6008010072b54a96b1747c4d65ba8f34b919823baa9b273402`). The cases that remain stricter are now listed, with probes, under "Scope (stricter, only for odd entries at the top level of `/app`)": escaping top-level symlinks and special files, and `/app/dist.npy` as an internal symlink into a dropped subdirectory. These match the precedent of `count-dataset-tokens`. An exclude only drops changes, so it cannot make a wrong candidate pass. The adapter imports nothing from `/app` (`-I`). The baseline has no test files to exclude (lesson C49). Result: sound.
3. Leaking expected values. Unchanged. The baseline image's `/app` is empty, and it has no answer or test files and no `.pth` files. The adapter and numpy are in `/usr/local`, outside the scope. The answer is public upstream (lesson C58), and the record says so. Result: sound.
4. Challenge leaks. One case with the challenge `{}` and the context `{}`. Result: sound.
5. Hidden cases. The deliverable is fixed by the instructions and its answer is public (lesson C58), which the record states. Result: sound.
6. Oracle (lessons C52 to C54). `hidden/oracle.py` and the adapter are unchanged since round 1. The judge checks the exact field set, dtype, shape, `nonfinite` and exactly 150 x 1,000 finite floats, then min, max, sum and both divergences, with numpy's float64 operations. Its work is bounded, it uses no regular expressions, and it never uses evidence as a path or code. The long double and float16 bullets are now correct (findings 2 and 3 of round 1). Result: sound.
7. Mutants and attacks. All seven mutants and three attacks get `failed`, class `oracle`, from SecureBench in both rounds, never `invalid`. The comments now match the measured values: KL(U||P) of 2.05 in `mutant-forward-only` and a sum of about 2.25 in `mutant-max-scaled`. `attack-shadow-numpy` still runs a real shim and still fails because of `-I`. Result: sound.
8. Divergences from native. The record lists two, and both hold up.
   - `attack-conftest`: native 1.0, SecureBench `failed`. The planted `/tests/conftest.py` rewrites pytest's outcomes upstream. Here `/tests` is outside the scope, and the judge computes KL(P||U) = 0 for the uniform file. SecureBench is right.
   - `attack-fake-curl`: native 1.0, SecureBench `failed`. The fake `curl` hijacks the `curl | sh` install of `uvx` in upstream's `test.sh`. Here `/usr/local/bin` is outside the scope. SecureBench is right.

   The other candidates agree between the graders: the reference passes both, and null, the mutants and `attack-shadow-numpy` fail both. The record's reason that the shim is not imported natively also holds: pytest's console script puts the test's directory, not `/app`, on `sys.path`. Result: sound.
9. Inventory. `distribution-search` is 20th in selection order. The coordinator adds the row, and `converted` is right. Result: sound.

Upstream assertions. Every assertion in `tests/test_outputs.py` is mapped in the table at the top of this record, and none is dropped.

Round 1 findings:
- Scope: fixed. The exclude was added, the bullet relabelled "stricter", and the remaining cases listed with probes. My venv probe now passes (run `sha256:1132821c...`).
- Long double label: fixed. The bullet now says "stricter" for elements outside float64's range and gives the reason.
- float16 sentence: fixed. It now gives the geometric-mean argument, which supports "equivalent".
- Mutant comments: fixed.

Findings:
- None.

Verdict: approved

## Review

Reviewer: a6756f62d6a38153e, 2026-10-25

Pack reviewed: `sha256:c2a5d8b44789b429c46ca785e2b56c746ddedee16425411708f32de9f0342836` (`securebench validate`, before and after the review). Every SecureBench run in `qualification.json` records this digest, `problems` is empty, and no run is dirty. Nine runs were made at framework commit `a6087a7` and `mutant-float32` at `90457d7`. Those two commits differ only in `conversions/agents.tsv`, so the SecureBench code is the same.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference. Result: sound.
2. Scope. There is one root, `/app`, with `exclude = ["*/*"]`. Under 4.6 each `*` matches one whole component, so the pattern drops everything at depth two or more and keeps every top-level entry, `/app/dist.npy` included. I inspected the baseline image: `/app` is empty, it has no symlinks, and there is no `/tests`. So there are no test files or convention-loaded files to exclude. The adapter runs `/usr/local/bin/python3 -I`, which keeps `/app` off `sys.path`, and the baseline has no `.pth` files. Upstream grades only the top-level `/app/dist.npy`, so the exclude drops nothing it grades. The remaining stricter cases are listed with probes. Result: sound.
3. Expected values. The answer is not secret: the vocabulary size, the targets and the tolerances are all stated in the instructions. `public/` does not exist. `evaluation/` holds only the adapter, which has `MAX_VALUES = 150_000` as a size bound (this number is already in the instructions and is never compared), and two schemas. The expected values are in `hidden/cases.json`, outside both the scope and the Evaluation. No allowed domains. Result: sound.
4. Challenges. There is one challenge, `{}`. Result: sound.
5. Cases. There is one case, matching upstream's single graded file, which all four upstream test functions check. No case was added, and `seed` is unused, as upstream draws no random values. Result: sound.
6. Oracle. Every literal comes from `hidden/cases.json` through `plan`, and `_expected` validates its form. `oracle.py` keeps only judging logic and numpy's own constants (block 128, unroll 8, buffer 8,192). The judge checks the exact field set, the dtype, the shape, `nonfinite`, and exactly 150 rows of finite floats. It then applies min, max, the sum, normalization and both divergences, with upstream's operators (`<` for the sum, `<=` for the KL tolerances). Its work is bounded by the schema (150,000 values). It uses no regular expressions, and it never uses evidence as a path or as code. It fails closed on anything unexpected. No candidate code runs in the Evaluation, so there are no claims to ignore. There are no regression tests.
   I checked the reimplementation independently, in the baseline with a 1 GiB memory limit and no network. On arrays of mixed magnitude (16 sizes from 1 to 150,000, 3 scales), `pairwise_sum` and `buffered_sum` match numpy 2.3.0's `np.sum` bit for bit, for the native and the big-endian copy. They do not match the baseline's numpy 2.1.2, which sums native arrays in buffers of 8,192. That is fine, because upstream's verifier uses 2.3.0 and the judge does not use the baseline's numpy. I also reran `hidden/differential.py` as its docstring describes, with numpy 2.3.0 and pytest 8.4.1 installed in my scratch. It gave exactly what this record states: 0 disagreements on the float64 corpus, sums and divergences bit-equal, 8 float32 disagreements with a largest gap of 2.76e-6, and on the 13 file forms only complex128 differing.
   One point is not tested: the differential runs `math.log` inside the container, while the Oracle runs on the host's Python. Both use glibc's `log` on the same CPU, so any difference is at the 1e-15 level the record already discusses. Result: sound.
7. Candidates. `reference.sh` is upstream's `solve.sh` byte for byte, apart from the `#!/bin/sh` line and a two-line comment. It uses no bash features, and the change is recorded. `null.sh` changes nothing and fails both graders (SecureBench `case_error`, `absent`). The five mutants run real code (the upstream solver, edited or rerun, or a brentq solve). They aim at the KL tolerance (`off-target`), the backward divergence (`forward-only`), the reimplemented sum (`max-scaled`), the adapter's flattening and the shape check (`column`), and the float32-to-float64 conversion (`float32`). Each gets the same verdict from both graders. The three attacks end `failed`, class `oracle`, not `invalid`. `attack-shadow-numpy` targets this task's adapter, and I checked that the shim really works on a loader without `-I`. Result: sound, with one note: no qualified mutant exercises the big-endian `buffered_sum` path or the long double rounding. Both forms are implausible for a solution, five mutants is the limit, and the differential covers both (the `big-endian` and `longdouble` files agree between graders). So this is not a finding.
8. Divergences. The record lists two, and both hold up. `attack-conftest` (native 1.0, SecureBench `failed`): the planted `/tests/conftest.py` rewrites upstream's pytest outcomes, while here `/tests` is outside the scope and the judge computes KL(P||U) = 0 for the uniform file. `attack-fake-curl` (native 1.0, SecureBench `failed`): the fake `/usr/local/bin/curl` hijacks the `curl | sh` install of `uvx` in `test.sh`, while here `/usr/local/bin` is outside the scope. SecureBench is right in both. Every other candidate agrees between the graders, as `qualification.json` shows. Result: sound.
9. Inventory. The row `terminal-bench distribution-search converted` has the right decision, and no exclusion applies. Its note is from before the remediation: it cites "No hidden case is possible (lesson C58)" and leaves out complex arrays. The coordinator should replace it with the note this record proposes. Result: sound for the conversion. The note update is the coordinator's job.

Upstream assertions. Each of the nine assertions in `tests/test_outputs.py` (`np.load` succeeds, `ndim == 1`, `size == 150000`, all finite, `min > 0`, `max <= 1.0`, `abs(sum - 1) < 1e-5`, and the two KL tolerances after `P / P.sum()`) maps to a condition in the judge, as the table at the top of this record shows. None is dropped. Each fidelity change has a stricter, more lenient or equivalent label and a reason.

Findings:
- None that block approval. One minor point: `candidates/attack-conftest.sh` line 4 ("lesson C49") and `task/hidden/differential.py` line 1 ("lesson C57") cite lesson codes that neither brief defines, so a reader of the pack cannot resolve them. Writing the reason out, or deleting the code, would make them self-contained.

Verdict: approved
