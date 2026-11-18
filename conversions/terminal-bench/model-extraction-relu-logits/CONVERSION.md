# model-extraction-relu-logits

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/model-extraction-relu-logits

## How the pack grades

Upstream's `tests/test_outputs.py` has one test, and the pack has one protocol check, `steal`, with one case: upstream's network of 30 hidden neurons built from seed 5. The case's challenge (`{"seed": 5, "hidden": 30}`) and the expected A1 are in `task/hidden/cases.json`, written by `task/hidden/derive.py`. The adapter (`task/evaluation/adapter.py`) does what the test does and reports the array `steal.py` saved, element by element. The Oracle (`task/hidden/oracle.py`) applies upstream's condition to that array and decides.

## How upstream's tests map to checks

Upstream's one test checks what the task asks for. There are no regression tests.

| Upstream (`tests/test_outputs.py`) | Check `steal`, case `upstream` |
|---|---|
| At import, writes its own `forward.py` into the working directory, `/app`. Its `forward()` rebuilds a network of 30 hidden neurons from `np.random.seed(5)` on every call | The adapter writes the same text to `/app/forward.py`, with the challenge's seed and width (5 and 30) in its placeholders. The result is upstream's string byte for byte |
| `os.popen("python3 /app/steal.py").read()` from `/app`, with the exit status ignored | The adapter runs `python3 /app/steal.py` from `/app`, with `python3` found on `PATH`. It reads the script's standard output until every process holding it has closed it, and discards it, as `read()` does. The exit status is reported and not judged. The run must end within 880 s (fidelity change 4) |
| `assert stolen_path.exists()` for `/app/stolen_A1.npy` | The Oracle fails a file the adapter reports `absent` |
| `b = np.load("/app/stolen_A1.npy")`. An exception fails the test | The adapter calls the same `np.load` with numpy's defaults, on the baseline's numpy. The Oracle fails a file reported `unloadable` (np.load raised), `not_array` (np.load returned an `.npz` archive, which upstream's loop cannot divide) or `not_regular` (a directory or device, which np.load cannot read as an array) |
| `a = np.random.randn(30, 10) * 0.3` after `np.random.seed(5)` | `a1` in `task/hidden/cases.json`, computed exactly so by `task/hidden/derive.py` on the baseline |
| `for stolen_row in b:`: iterate over b's first axis | The adapter reports `shape`, every element in C order, and the layout numpy gives the ratio array of an entry (`ratio_strides`, fidelity change 3). The Oracle splits the elements into the entries of the first axis. A 0-d array fails, as iterating over one raises `TypeError` |
| `stolen_row / original_row - np.mean(stolen_row / original_row)`, with numpy's broadcasting and type promotion | The Oracle broadcasts each entry against a row of 10 as numpy does. A scalar entry (1-D `b`) and an entry whose last axis is 1 repeat across the row, and an entry whose last axis is 10 divides element by element. Any other last axis fails, as numpy raises `ValueError`. Elements arrive as float64 or complex128, the types numpy promotes them to against A1's float64 (fidelity change 2). The mean uses numpy's own summation order (fidelity change 3) |
| `if np.all(ratio_diff < 1e-4)`: a match | The Oracle checks that every deviation is below 1e-4, computed as numpy computes it. An entry with no elements matches every row, as `np.all` over nothing is `True`. An entry holding inf or NaN never matches, as its ratios or mean are non-finite and no comparison with them is below 1e-4 |
| `assert all_matched`: every row of A1 has a matching entry | The case passes only if every row of A1 has a matching entry. Entries that match nothing are allowed, as upstream allows them |

Strings, dates and times fail in upstream's division (`TypeError`, `UFuncTypeError`), and object arrays do not load without `allow_pickle`. The Oracle fails every kind other than booleans, integers, floating-point and complex numbers.

## Fidelity changes

1. **Bounds (stricter, negligible).** The file may hold at most 64 MiB, and the array at most 40,960 elements (4,096 rows of 10). An array with no elements is read from its shape alone, however long its other axes. Upstream sets no bound. The element bound keeps the observation, in strict JSON and doubled for complex arrays, under the check's 4 MiB limit. It also bounds the Oracle's work: at the bound, the slowest array measured, 40,960 complex scalars that match nothing, takes 7.4 s to judge on the qualification worker. The reviewer measured 11.5 s for a complex (1, 40960, 1) array. Both are inside the Oracle's 60 s limit. A file over 64 MiB holds either more elements than that or bytes after the array, which np.load ignores. The reference saves 30 rows (300 elements, 2.5 KB).

2. **Element types (equivalent, except long double: stricter or more lenient).** The adapter converts every element to float64, and complex elements to a float64 real and imaginary part. Upstream's division promotes booleans, integers, float16, float32 and complex64 to the same types against A1's float64, with the same conversion. The `rows-float16`, `rows-float32` and `rows-complex64` layouts of the differential (change 3) cover this.

   `longdouble` and `clongdouble` arrays (x87 80-bit extended precision on this baseline) differ. Upstream computes their ratios in long double; here the adapter converts them to double and the Oracle computes in double. This has three consequences:
   - A decision can change, in either direction, when a deviation lies within double rounding of 1e-4.
   - Values above double's range (about 1.8e308) become infinite here, and their entry never matches. Upstream keeps long double's wider range, so an array that is exactly A1 times a large power of two passes upstream and fails here, for example `a1.astype(np.longdouble) * np.longdouble(2) ** 1400`. The differential's `longdouble-beyond-double` sample is this array, and it is the one array on which the verdicts differ.
   - Values below double's smallest subnormal become 0 here. That changes a ratio by less than 1e-300, so a decision changes only at the threshold itself.

   The reason: the observation carries strict-JSON numbers, which are doubles, and the Oracle reproduces numpy's float64 and complex128 operations. To do the same for long double, the adapter would have to send each element's 80-bit encoding, and the Oracle would have to reproduce x87 extended arithmetic, and for `clongdouble` numpy's long double complex absolute value. We record the difference instead: no extraction produces a long double array, let alone one beyond double's range. Strict JSON cannot carry inf or NaN, so the adapter lists the entries holding one in `nonfinite` and sends their values as zeros. The Oracle never matches those entries, as upstream never does.

3. **Oracle arithmetic (equivalent).** The judge runs on the host without numpy. It reproduces the operations of upstream's expression:
   - IEEE division, and for complex entries numpy's complex division by a real row, which multiplies by a reciprocal.
   - `np.mean` as numpy computes it, in the memory order of the ratio array `entry / row`. The sum starts from 0 and adds each buffer of 8,192 elements in order. Each buffer is summed with numpy's pairwise summation (eight running sums per block of 128, halves above that), interleaved for complex values. The total is then divided by the count, as a complex scalar division for complex values.
   - numpy's vectorized complex absolute value, `larger * sqrt(fma(ratio, ratio, 1))`, with the fused multiply-add computed exactly.

   The 8,192-element buffers matter only for entries of more than 8,192 elements. A sum over a whole entry without them differs from numpy's in the last bit from 8,200 elements on; with them it matches on every size tried up to 40,960.

   The memory order matters only for files saved in Fortran order with three or more dimensions. numpy allocates `entry / row` in the entry's own layout, so for such a file the ratios lie in Fortran order and `np.mean` sums them in that order, not in C order. The adapter reports the layout as `ratio_strides`: the element strides of `b[0] / np.ones(10)`, a float64 row of 10, as upstream's rows are. The layout depends on shapes and strides only, never on values. The Oracle sums each entry's ratios in that memory order, and it fails closed on strides that do not lay the array out contiguously. A probe in the baseline (numpy 2.2.5) compared this with `np.mean` on 1,211 entries: arrays of 1, 3 and 4 dimensions (a two-dimensional file has one-dimensional entries, which have only one order), C and Fortran order, real and complex, last axis 1 or 10. Every mean was identical in every bit, and the strides of `b[0] / np.ones(10)` were those of `b[i] / row` in every case.

   `task/hidden/differential.py` compares whole-file verdicts. Inside a container it saves arrays near the threshold with numpy, judges each with upstream's own loop (copied from the test), and records what the adapter's own `load()` reports for the file. On the host it judges those observations with the Oracle. The arrays cover:
   - (n, 10) rows of six element types, one row placed within a relative 1e-16 to 1e-3 of the tolerance;
   - 1-D and (n, 1) arrays and (n, p, 1) entries of small values;
   - (30, p, 10) stacks;
   - 200 single entries of 800 to 4,096 elements broadcast to 8,000 to 40,960 ratios;
   - entries with inf or NaN;
   - half of every three-dimensional layout saved in Fortran order (2,032 and 2,007 arrays in the two runs);
   - `fortran-flip`: Fortran-ordered (30, 50, 10) arrays built so that upstream's verdict on the file differs from its verdict on the C-ordered copy (2 and 3 found);
   - 29 fixed arrays of degenerate shapes and types, among them `np.zeros((1, 50000, 0, 10))`, which upstream passes;
   - the long double array of fidelity change 2, the one known difference.

   The Oracle's verdict equals upstream's on every array except the known long double one. With numpy 2.2.5 (the baseline; seed 2), 20,231 other arrays were judged, 9,411 of them accepted by upstream. With numpy 2.3.1 (upstream's verifier; installed with pip into `python:3.13-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962`; seed 3), 20,232 other arrays were judged, 9,533 of them accepted. In both runs every layout had arrays on both sides of the threshold, except float16 rows, whose rounding always exceeds 1e-4 at the scales used.

   One caveat: numpy's complex absolute value uses a fused multiply-add only on a CPU that has one (the qualification worker does). On a CPU without it, numpy's own result differs in the last bit. That can change a complex entry's decision only when its deviation is within that bit of 1e-4.

4. **Time (stricter, negligible).** Upstream's verifier has 900 s for its own setup and the test. Its setup installs curl and uv and builds the test environment, which took 7.6 s in a native probe, so `steal.py` can run for about 890 s. Here `steal.py`, and every process that keeps its standard output open, may run 880 s inside the case's 900 s. A run past that fails, as it would upstream. The reference takes about 10 s. Once `steal.py` has exited and its standard output is closed, the adapter kills what is left in its process group and loads the file. A process that has closed its standard output and writes the file later can be killed here before it writes, or can lose the race upstream, so the two graders may differ for it. Under `probe-sleep`, `steal.py` forks a child that keeps standard output open and sleeps for 2,000 s; it ran once through SecureBench on the final pack and failed with class `oracle` and "steal.py did not finish in time" (ending `timed_out`), with the attempt done in 15 minutes. The probe is not a candidate: the candidate kinds have no slot for it.

5. **Interpreter and numpy for `steal.py` (equivalent).** Natively, `steal.py` runs under the virtual environment `uvx` builds for pytest: Python 3.13.7 (the baseline's own build) with numpy 2.3.1, plus pytest and its dependencies, and without the baseline's `/usr/local` site-packages. A native probe confirmed this by printing `sys.executable`, `sys.path` and numpy's version from inside `steal.py`. Here `python3` is the baseline's `/usr/local/bin/python3`: the same Python 3.13.7 with numpy 2.2.5, the version the agent develops against. The Evaluation has no network, so the native environment cannot be rebuilt in it. A `steal.py` that needs an API added in numpy 2.3, or imports pytest, passes upstream and fails here; neither is plausible for this task.

6. **Adapter interpreter (equivalent).** The adapter runs on the baseline's `/usr/local/bin/python3` with `-I`, not on the stock interpreter (the converter brief, Section 4.3, makes that optional), so that numpy itself loads the file. `-I` keeps `/app`, which the candidate controls, off the adapter's import path (`attack-numpy-shadow`). The adapter loads the file with numpy 2.2.5, where upstream's verifier uses numpy 2.3.1, and `np.load` has the same signature and defaults in both (`allow_pickle=False`, no memory map, `max_header_size=10000`). I compared the source of `np.load` and of the `.npy` reader (`numpy.lib.format` in 2.2.5, `numpy.lib._format_impl` in 2.3.1) with docstrings removed. Apart from string formatting and module decorators, there is one change. 2.3.1 raises a `ValueError` naming the shortfall when a file holds fewer elements than its header declares, where 2.2.5 raises a `ValueError` from the reshape that follows. Either way the load fails, so the outcome is the same. `/usr/local` is outside the scope, so the adapter starts from the baseline's Python and numpy, and it imports numpy before `steal.py` runs.

7. **Writing `forward.py` (more lenient, corner case).** Upstream's `open("forward.py", "w")` writes through whatever `/app/forward.py` is. When the candidate has made it a directory or a dangling symlink into a missing directory, upstream's test fails at import. The adapter removes whatever is at `/app/forward.py` first and then writes the file, so that the graded network is always installed and a symlink cannot redirect the adapter's write. A candidate that breaks `/app/forward.py` in this way and has a working `steal.py` passes here and fails upstream. A `forward/` package beside it is left alone, as upstream leaves it (`attack-shadow-forward`).

8. **Scope (stricter for some solutions).** The scope is `/app`, which holds the deliverable and anything `steal.py` imports from beside it. Natively the whole agent container is graded, so a `steal.py` that reads files the agent left elsewhere (for example in `/opt`) passes upstream and fails here. `/usr/local` is not captured. Natively `steal.py` runs in a virtual environment that does not see it (change 5), so packages installed there do not help `steal.py` upstream either.

9. **Allowed domains (stricter).** None, which is all the reference needs. Upstream allows the Internet. Packages the agent installs do not reach `steal.py` natively (change 5), so the Internet gives the agent nothing there that grading uses.

## Remediation

The conversion was made under an earlier converter brief. This pass brings it in line with the current one.

Removed:
- **The hidden case** (seed 734395237, 30 hidden neurons), from `task/hidden/cases.json` and its seed search from `task/hidden/derive.py`. Upstream tests only its own network. `max_cases` is now 1. Regenerating `cases.json` with the simplified `derive.py` gives exactly the old upstream case.
- **The relative tolerance**, which also required every deviation to be below 1 % of the mean ratio, from `task/hidden/oracle.py`. The Oracle now applies upstream's absolute tolerance alone, so a row of zeros or of tiny values passes, as it passes upstream.
- **Deleting `/app/stolen_A1.npy` before the run**, from `task/evaluation/adapter.py`. Upstream judges whatever file exists after `steal.py` ran, so this pass does too.
- **The shape requirement**, which accepted only a two-dimensional array with 10 columns and at most 4,096 rows. The Oracle now reads any shape as upstream's loop and numpy's broadcasting do (map above). The adapter reports every element in C order, and the layout of the ratio array. The observation schema changed with it: `re` and `im` are flat, `nonfinite` lists entries instead of flagging rows, and `ratio_strides` is new.
- **The process-group kill as soon as `steal.py` exits.** The adapter now waits, as `os.popen(...).read()` does, until every process holding `steal.py`'s standard output has closed it (`mutant-forked-writer`).
- The old fidelity changes for the hidden case, the relative tolerance, the deleted file and the shape requirement; the residuals "reading the network instead of querying it" and "extra rows" (the second is now part of the map); the section "Answer already public upstream"; and the probes `probe-whitebox`, `probe-orphan`, `probe-complex` and `probe-nan-float32`, which documented removed behaviour.

Restored: nothing was dropped. Every upstream assertion already had a check. The ones the shape requirement narrowed (iterating over any first axis, broadcasting) are now checked in full.

Moved: no expected value or challenge was in `oracle.py`. The expected A1 and the challenge were, and are, in `task/hidden/cases.json`. The 8,192-element buffer and the pairwise block size in `oracle.py` are numpy's summation order, part of how the Oracle compares.

Rewritten: `task/hidden/differential.py` now compares whole-file verdicts against upstream's loop (fidelity change 3), not single rows.

### Changes after the first review

- **An empty array with a long inner axis.** `oracle.py` now treats an entry as empty whenever an inner axis is 0, before it applies the element bound. `np.zeros((1, 50000, 0, 10))` now passes, as upstream passes it (fidelity change 1; it is a fixed sample of the differential).
- **Long double beyond double's range.** Fidelity change 2 now records that an exactly scaled long double array beyond double's range passes upstream and fails here, with the reason.
- **Fortran-ordered files.** The adapter reports `ratio_strides`, and the Oracle sums each entry's ratios in that memory order (fidelity change 3). The differential now saves half of its three-dimensional arrays in Fortran order, and adds Fortran arrays whose verdict upstream depends on the order.
- **No mutant reached the complex path.** `mutant-complex-phase` replaces `mutant-transposed`.
- `attack-forge-observation`'s forged observation gained `ratio_strides`, so that it would still pass the Oracle if it were trusted.

Candidates deleted:
- `attack-hardcode-upstream` (saves upstream's public A1), `attack-stale-output` (leaves upstream's public A1 in the file) and `attack-zero-row` (saves a zero row, which upstream's tolerance accepts). None tampers with grading; each uses a public answer or upstream's own assertion.
- `attack-module-global`, which imports `A1` from the agent's own `forward.py`. It is a wrong solution, not tampering with grading.
- `mutant-unsigned` and `mutant-assume-20`. They test the matching of rows, where the Oracle's check is upstream's assertion itself. The five-mutant limit goes to the places where the check is least like upstream's.

Candidates kept: `reference` and `null`. `mutant-transposed` (an entry of 30 elements, which numpy cannot broadcast against a row of 10) was kept at first, then replaced after the first review by `mutant-complex-phase`: `mutant-flat` already aims at broadcasting, and no mutant reached the complex path.

Candidates added:
- `mutant-flat`: 1-D scalar entries broadcast across a row.
- `mutant-float16`: the adapter's conversion to float64.
- `mutant-normalize-min`: the absolute tolerance and numpy's mean on correct rows at a large scale.
- `mutant-forked-writer`: the wait for every process holding `steal.py`'s output.
- `mutant-complex-phase`, added after the first review: the complex path (complex division by a real row, the interleaved complex pairwise sum, the complex absolute value) and the conversion of complex64.
- `attack-forge-observation`, `attack-numpy-shadow` and `attack-shadow-forward`: three ways of tampering with this task's grading.

### Old mutants failed by an addition

None. In the qualification before remediation (`git show HEAD:conversions/terminal-bench/model-extraction-relu-logits/qualification.json`), every mutant had native reward 0.0, so no mutant was failed by an addition and step 5 had nothing to run. The three attacks that native passed were failed by additions, and they are deleted above.

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-unsigned` | 0.0 | `failed` (`oracle`) | deleted |
| `mutant-assume-20` | 0.0 | `failed` (`oracle`) | deleted |
| `mutant-transposed` | 0.0 | `failed` (`oracle`) | `failed` (`oracle`) in the first remediated qualification; then replaced by `mutant-complex-phase` |

## Candidates

All are POSIX `sh`. The mutants run `reference.sh` first and then change one line of its `steal.py` with `sed`, checking that the change applied. The upstream verdict for each mutant comes from a run of upstream's loop on the reference's output in the baseline.

- `reference.sh`: upstream's `solve.sh`, unchanged after a `cd /app` (and `#!/bin/sh` for the `#!/bin/bash` line; the script uses only POSIX features). No drift repair: it needs nothing from the network. Its rows are small (largest entry 0.03), and their largest deviation is 1.6e-8.
- `null.sh`: changes nothing; there is no `steal.py`.
- `mutant-flat.sh`: saves the 300 numbers as a 1-D array. Each scalar entry broadcasts across a row. Tiny values match some rows of A1 under the absolute tolerance, but not all 30.
- `mutant-float16.sh`: saves the matrix as float16. The reference's rows are small enough that float16 rounding stays below 1e-4, so it passes upstream.
- `mutant-normalize-min.sh`: divides each row by its smallest entry in magnitude. The rows are still A1 up to scaling, but at that scale the reference's errors exceed 1e-4 (largest deviation 3.2e-4) for 4 rows of A1, so it fails upstream.
- `mutant-forked-writer.sh`: `steal.py` forks first. The parent exits at once and the child extracts and saves, so it passes only if the grader waits for the child.
- `mutant-complex-phase.sh`: saves the rows times the unit phase 0.6 + 0.8j as complex64, which is A1 up to a complex scale. Its largest deviation is 1.6e-8, so it passes upstream.
- `attack-forge-observation.sh`: `steal.py` writes a forged observation (a zero row) to its parent's standard output through `/proc` and kills the parent, the adapter. Its target is the adapter's output channel. Judged directly, the forged observation passes the Oracle, so only the exit status of the killed adapter stops it.
- `attack-numpy-shadow.sh`: puts a `numpy` package in `/app`, the adapter's working directory. The package loads the real numpy and replaces `load` with one that returns a zero row. `steal.py` writes bytes that are not an array. Its target is the adapter's own numpy, which `-I` keeps from `/app`. A check in the baseline confirmed the package works: with `/app` on the path, `np.load` returns the zero row.
- `attack-shadow-forward.sh`: adds a `forward/` package holding the agent's own network (seed 0, 20 neurons), which Python's import prefers to the `forward.py` the grader writes. The reference's `steal.py` then extracts the wrong network. Its target is the black box the grader installs; the Oracle's expected A1 does not come from the Evaluation.

## Inventory note

Proposed note: "Remediated: upstream's one case, judged with upstream's absolute tolerance and numpy's broadcasting and summation reproduced; no hidden case, no added condition. Public answer out of scope."

## Divergences from native

None. `qualification.json` reports no problems, and every SecureBench run is admitted, rejudged and made on pack `sha256:29ceaaf0b6b298332effa6c758c6abe301ebdc5566523faaeca49d66af449d59`, after the fixes for the first review.

| Candidate | Native | SecureBench |
|---|---|---|
| `reference` | 1.0 | `passed` |
| `null` | 0.0 | `failed` (`oracle`) |
| `mutant-complex-phase` | 1.0 | `passed` |
| `mutant-flat` | 0.0 | `failed` (`oracle`) |
| `mutant-float16` | 1.0 | `passed` |
| `mutant-normalize-min` | 0.0 | `failed` (`oracle`) |
| `mutant-forked-writer` | 1.0 | `passed` |
| `attack-forge-observation` | 0.0 | `failed` (`case_error`: the adapter was killed) |
| `attack-numpy-shadow` | 0.0 | `failed` (`oracle`: the file does not load) |
| `attack-shadow-forward` | 0.0 | `failed` (`oracle`: no row of A1 matched) |

The three attacks fail natively too, so they show nothing about native grading. Natively, `attack-forge-observation`'s parent is the shell `os.popen` starts, so it writes into a pipe that is discarded. The test appends `/app` to the end of `sys.path`, after numpy is found. And upstream's import also prefers the `forward/` package.

## Review before remediation

Reviewer: a1348bc64c659d4a2, 2026-10-12 (second round)

Pack digest reviewed: `sha256:f311772ab9ddfb9eba0df3966ca9f4abaae1ab40e2efda2e2b6522d960e6ef5f` (`securebench validate`). The first round reviewed `sha256:35b90c13...21bd79`. The only change to the pack since then is the comment in `task/evaluation/adapter.py` before the `killpg` call: putting the old comment back gives the original file byte for byte in size, and the code around it is unchanged. So points 2 to 7 and 9 carry over from the first round. Point 8 is checked again on the new qualification.

First-round findings:
- **Fidelity change 9 and the adapter comment on the process-group kill: fixed.** Both now say that `killpg` reaches only `steal.py`'s process group. A process that leaves it (`os.setsid()`) survives and may write the file before it is loaded, depending on timing, and whatever file is loaded is judged against the case's A1. This matches the behaviour I demonstrated.
- **Fidelity change 12 without a label: fixed.** It is now labelled "equivalent", and the reason states the numpy version difference (2.2.5 here, 2.3.1 upstream), the identical `np.load` defaults, and the one difference in the reader, which ends in a failed load in both versions.

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical. No fidelity change touches them.
2. **Scope.** `/app`, the root holding the deliverable `/app/steal.py`, the file it writes and any module it imports from beside it. In the baseline `/app` holds only `forward.py`, which the adapter replaces.
   - The delta cannot change `python3` on `PATH` or the adapter's interpreter and numpy, all under `/usr/local` outside the scope.
   - `-I` keeps `/app` off the adapter's `sys.path`. Convention-loaded files in `/app` (`numpy/`, `sitecustomize.py`, `.pth`) therefore reach only `steal.py`, which is candidate code anyway.
   - A shadowing `forward/` package or an unchecked-hash `forward.pyc` only changes which network the candidate's own code queries.
   - There are no test files to protect. Fidelity change 10 covers solutions that read files outside `/app`.

   Result: the scope covers every solution the instructions allow.
3. **Leaked expected values.**
   - `public/` is absent.
   - `evaluation/` holds the adapter (the `forward.py` template with placeholders, no seed) and the schemas.
   - I inspected the baseline image itself with `docker run --network none`. `/app` holds only upstream's `forward.py` (md5 identical to `environment/forward.py`), and the image has no `/tests`, `/solution` or `/logs`.
   - The upstream case's A1 is public upstream, as stated.
   - Re-running `hidden/derive.py` on the baseline reproduces `hidden/cases.json` byte for byte, with hidden seed 734395237.
4. **Challenges.** Each challenge is `{seed, hidden}` for its own network only, bounded by the schema and by the adapter. The hidden seed reaches only the hidden case's Evaluation, where `forward()` has to be built from it. That A1 can then be read there is the documented residual, unavoidable because `forward()` must run beside the candidate.
5. **Hidden case.** Present: seed 734395237, width 30. `attack-hardcode-upstream` passes upstream and fails here.
6. **Oracle (C52 to C54).**
   - `judge` requires exactly the schema's field set, `ending == "exited"`, `file == "loaded"`, a numeric kind, and shape `(n, 10)` with `n <= 4096`. The row, imaginary and `finite` counts must agree with the shape. Anything else fails.
   - Repeating rows cannot inflate coverage of A1's rows: one stolen row could match two rows of A1 only if those rows were proportional.
   - Work is bounded. The judge uses no files and no regular expressions, and it never evaluates evidence.
   - Non-finite and overflowing ratios fail closed.
   - The adapter's template matches upstream's `forward.py` string byte for byte for seed 5 and width 30.
   - Re-running `differential.py` with a fresh seed (20,000 rows, 5,028 complex, numpy 2.2.5) gives 0 differences from numpy in mean, largest deviation and decision.
7. **Mutants and attacks.** All run real code and get `failed` with class `oracle`, never `invalid`.
   - Each mutant targets a requirement: `mutant-unsigned` the sign recovery, `mutant-assume-20` the unknown width, `mutant-transposed` the output format.
   - Each attack targets a weakness of this task: the public test network, a stale output file, upstream's absolute tolerance, and the module global in the agent's own `forward.py`.
8. **Divergences.** `qualification.json` (written 03:35, after the last pack change) reports no problems over 2 rounds.
   - Every SecureBench run is admitted, rejudged, made from a clean framework tree at one commit, and records pack digest `sha256:f311772...6ef5f`, the one I noted.
   - The reference passes both graders. The null candidate and the three mutants fail both.
   - `attack-hardcode-upstream`, `attack-stale-output` and `attack-zero-row` each get native 1.0 and SecureBench `failed`. "Divergences from native" explains them by fidelity changes 1, 3 and 2, and in each SecureBench is right: the hidden network is not recovered, `steal.py` writes no file, and a zero row is not A1 up to scaling.
   - `attack-module-global` fails both graders.
9. **Inventory row.** No row exists yet; the coordinator adds it. `converted` is correct. No exclusion reason holds: the result can be checked from the saved matrix. Only how it was obtained (queries versus reading `forward.py`) is an execution property, and upstream does not check that either.

Upstream assertions: all are reproduced (mapping table), none is dropped:
- the rewrite of `forward.py`;
- the run of `steal.py`, with its exit status ignored;
- `stolen_path.exists()`;
- `np.load` succeeding;
- the per-row match condition.

Every fidelity change is labelled and has a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (scratch `model-extraction-relu-logits-review`), 2026-10-25 (second round)

Pack digest reviewed: `sha256:29ceaaf0b6b298332effa6c758c6abe301ebdc5566523faaeca49d66af449d59` (`securebench validate`). The first round reviewed `sha256:978335c8…3a35`. Since then:
- `adapter.py` adds `ratio_strides` (the only diff to the adapter);
- the observation schema adds that field;
- `oracle.py` changes its size check and sums in memory order;
- `differential.py` adds Fortran layouts;
- `mutant-complex-phase` replaces `mutant-transposed`;
- `attack-forge-observation` forges the new field;
- the text of fidelity changes 1 to 3 is updated.

First-round findings:
- **Empty arrays with a long inner axis: fixed.** `oracle.py` now sets the size to 0 when any inner axis is 0, before the bound. `np.zeros((1, 50000, 0, 10))` now passes through the adapter's `load()` and the Oracle, as upstream passes it.
- **Long double explanation: fixed.** Fidelity change 2 now says that an array exactly scaled by a large power of two passes upstream and fails here, gives the example, and says why the conversion records the difference instead of reproducing x87 arithmetic. The label is now "stricter or more lenient". I re-ran `a1.astype(np.longdouble) * 2**1400`: it still passes upstream and fails here, as recorded.
- **Fortran-order summation: fixed.**
  - The adapter reports the element strides of `b[0] / np.ones(10)`.
  - The Oracle maps them to a memory order. It fails closed unless the strides lay out a contiguous array, and it sums in that order.
  - My `fortflip.py` array (30, 50, 10, Fortran order) now passes both graders.
  - I also checked new Fortran arrays against upstream's loop on the baseline: 1-D scalars, (30, 7, 1), (30, 3, 4, 10) and a complex64 (30, 5, 10) stack. Every verdict agrees.
  - The candidate can forge `ratio_strides`, but that changes only the summation order of its own values. Building the order is bounded by the shape bound, at most 409,600 offsets, computed once.
  - Re-timed worst cases: 11.0 s at most, inside the 60 s judge limit.
- **No complex mutant: fixed.** `mutant-complex-phase` saves the rows times 0.6 + 0.8j as complex64. That exercises complex division, the interleaved pairwise sum, the complex absolute value and the complex64 conversion. It passes both graders.
- **Stale inventory note: still open, for the coordinator** (point 9).

1. **Instructions.** Unchanged: `cmp` against upstream `instruction.md` is identical.
2. **Scope.** Unchanged: one root, `/app`. The baseline `/app` holds only `forward.py`, with no symlinks. The adapter runs with `-I`, and numpy comes from `/usr/local`, outside the scope. The new adapter code divides by `np.ones(10)` with that numpy and adds no import path.
3. **Expected value leaks.** Unchanged. `cases.json` is reproduced byte for byte by `derive.py` on the baseline. `ratio_strides` carries layout only.
4. **Challenges.** Unchanged: `{"seed": 5, "hidden": 30}`.
5. **Cases.** Unchanged: one upstream case, no seed use.
6. **Oracle.**
   - Expected values come only from `cases.json`.
   - `FIELDS` includes `ratio_strides`. The new `_memory_order` checks its type and length and requires every offset to be distinct and in range, so a malformed value fails with "malformed ratio layout".
   - The judge still uses no files, no regular expressions and no evaluation of evidence.
   - Findings 1 and 3 are fixed as described above.
7. **Candidates.**
   - `reference.sh` is still upstream `solve.sh` with only `#!/bin/sh` and `cd /app`.
   - Five mutants (`complex-phase`, `flat`, `float16`, `normalize-min`, `forked-writer`) each run the reference and change one line. Each aims at a place where the check is reimplemented.
   - Three attacks target the adapter's output channel, the adapter's numpy and the black box the grader installs.
8. **Divergences.** `qualification.json` reports no problems. Every SecureBench run:
   - is admitted and rejudged;
   - was made from a clean framework tree at `a209c015`;
   - records pack digest `sha256:29ceaaf0…9d59`, the one I noted.

   The reference passes both graders and the null candidate fails both. Each mutant gets the same verdict from both graders:
   - `complex-phase`, `float16` and `forked-writer` pass both;
   - `flat` and `normalize-min` fail both.

   Each attack is `failed` here (`attack-forge-observation` with `case_error`, the others with `oracle`), and each fails natively too. "Divergences from native" says "None" and explains why the attacks also fail natively. That matches the file. The known long double difference (change 2) has no candidate and is recorded.
9. **Inventory.** `converted` is right, and no exclusion reason applies. The note in row 21 of `conversions/inventory.tsv` still describes the removed hidden network and the removed 1 % relative condition. The coordinator should replace it with the note proposed in "Inventory note", which is accurate. Converters may not edit the inventory, so this does not hold up the conversion.

Upstream assertions:
- the rewrite of `forward.py`;
- the run of `steal.py`, with its exit status ignored;
- `stolen_path.exists()`;
- `np.load`;
- iteration over the first axis;
- the broadcast division and mean (now also in numpy's memory order);
- `np.all(ratio_diff < 1e-4)`;
- `assert all_matched`.

Each has a check in the map. None is dropped. Every fidelity change has a label and a reason that holds up on the cases I probed.

Findings:
- None in the conversion. For the coordinator: replace the stale note in `conversions/inventory.tsv` row 21 with the one proposed in "Inventory note".

Verdict: approved
