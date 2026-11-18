# build-cython-ext

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/build-cython-ext

The task asks the agent to clone pyknotid 0.5.3 to `/app/pyknotid`, fix its NumPy 2 incompatibilities, compile its Cython extensions (`chelpers`, `ccomplexity`, `cinvariants`) and install it into the system Python, keeping NumPy 2.3.0. The baseline is the upstream image `alexgshaw/build-cython-ext:20251031` pinned by the digest `docker pull` reports (`sha256:3612a38f...`): Python 3.13.7 in `/usr/local` with only NumPy 2.3.0 and pip installed, git and build-essential, and an empty `/app`.

## How the pack grades

Upstream's verifier installs pytest from PyPI and runs `tests/test_outputs.py`, whose last test clones pyknotid again from GitHub and runs its `tests/` with pytest. None of that is possible offline, and a pytest report is not evidence of what the candidate computes: the candidate's code runs inside pytest's process and can rewrite the report. Instead `evaluation/adapter.py` (stock Python) starts the baseline's own interpreter, `/usr/local/bin/python3 -I`, on `evaluation/driver.py`. The driver makes the calls each upstream test makes and reports the values its assertions compare, or the exception it raised; it moves its own standard output aside first, because pyknotid prints progress. `hidden/oracle.py` applies every assertion, with every input and expected value read from `hidden/cases.json`.

There are three checks, each with upstream's cases and no others:

- `clone`, an artifact check: a listing of `/app/pyknotid/.git`.
- `outputs`, a protocol check with one case: upstream's inputs to `tests/test_outputs.py`. Its only random value is `test_chelpers`' argument, which upstream draws with `random.random()` at run time; `plan` draws it from `Random(seed)` and expects it back, as upstream does.
- `repository`, a protocol check with one case: the 18 tests of pyknotid 0.5.3's `tests/test_knot.py` and `tests/test_spacecurve.py` (upstream's two `--ignore`s leave exactly these), run from `/app/pyknotid` with that directory first on `sys.path`, as upstream's `python -m pytest` run from there has it.

## How upstream's tests map to checks

Every upstream test checks what the task asks for; there are no regression tests run by outcome. Each row is one assertion. "Raises nothing" is a test with no assertion, which pytest fails only on an exception.

| Upstream test | Assertion | Check, case | What the Oracle requires |
|---|---|---|---|
| `test_numpy_version` | `version.parse(np.__version__) == version.parse("2.3.0")` | `outputs`, case 0 | the reported version equals `2.3.0` under packaging's rules (reimplemented, see "Fidelity changes") |
| `test_repo_cloned` | `path.exists()` | `clone` | implied by the third assertion: a `.git` inside `/app/pyknotid` exists only if `/app/pyknotid` does |
| `test_repo_cloned` | `path.is_dir()` | `clone` | implied in the same way |
| `test_repo_cloned` | `(path / ".git").exists()` | `clone` | the listing's status is anything but `absent` |
| `test_pyknotid_core_import` | `spec is not None` | `outputs`, case 0 | `found` is true |
| `test_pyknotid_core_import` | `isinstance(spec.loader, SourceFileLoader)` | `outputs`, case 0 | the loader's MRO, by qualified class name, contains `SourceFileLoader` |
| `test_chelpers_cython_extension`, `test_ccomplexity_cython_extension`, `test_cinvariants_cython_extension` | `spec is not None` (each) | `outputs`, case 0 | `found` is true for each module |
| the same three | `isinstance(spec.loader, ExtensionFileLoader)` (each) | `outputs`, case 0 | each loader's MRO contains `ExtensionFileLoader` |
| `test_chelpers` | `abs(cross_product(rand, 0, 0, 1) - rand) < 1e-10` | `outputs`, case 0 | the same, with `rand` from the run seed |
| `test_ccomplexity` | `abs(cython_higher_order_writhe(square, zeros, [0,1,2,3]) - 0.0) < 1e-6` | `outputs`, case 0 | the same, on upstream's four-point square |
| `test_cinvariants_python_vs_cython` | `py_result == cy_result` for `trefoil(num_points=50)` | `outputs`, case 0 | the two reported values are equal |
| `test_example_usage` | `abs(three_twist(100).alexander_polynomial(-1) - 7) < 1e-6` | `outputs`, case 0 | the same |
| `test_example_usage` | `figure_eight(100).determinant() == 5` | `outputs`, case 0 | the same |
| `test_pyknotid_repository_tests` | `result.returncode == 0` of pytest on the 18 tests | `repository`, case 0 | every one of the 18 tests is reported once and raised nothing, and each assertion below holds |
| `test_knot.py::test_invariants` | `k.determinant() == 3` | `repository` | the same |
| `test_knot.py::test_invariants` | `k.alexander_at_root((2,3,4)) == [3, 2, 1]` | `repository` | the value is a `list` equal to `[3, 2, 1]` (a tuple compares unequal to a list in Python, so upstream also fails it) |
| `test_knot.py::test_invariants` | `k.vassiliev_degree_2() == 1` | `repository` | the same |
| `test_knot.py::test_invariants` | `k.vassiliev_degree_3() == -1` | `repository` | the same |
| `test_knot.py::test_identify` | raises nothing (returns early without chelpers) | `repository` | no exception |
| `test_spacecurve.py::test_init`, `test_rotate`, `test_octree_simplify`, `test_smooth` | raise nothing | `repository` | no exception |
| `test_spacecurve.py::test_copy` | `np.all(k2.points == k.points)` | `repository` | the driver reports the comparison's outcome, which must be true |
| `test_spacecurve.py::test_copy` | `k2.points is not k.points` | `repository` | the same |
| `test_spacecurve.py::test_points` | `isinstance(k.points, np.ndarray)` | `repository` | the same |
| `test_spacecurve.py::test_translate` | `new_pos[i] - pos[i] == 10., 20., 30.` (three assertions) | `repository` | the three differences equal 10, 20 and 30 exactly |
| `test_spacecurve.py::test_zero_centroid` | `np.all(np.average(k.points, axis=0) < 0.00001)` | `repository` | every reported centroid coordinate is below 0.00001; the random shift is unseeded NumPy, as upstream |
| `test_spacecurve.py::test_planar_writhe` | `np.abs(k.planar_writhe()) == 3` | `repository` | the same |
| `test_spacecurve.py::test_writhe` | `-3.6 < k.writhe(100) < -3.4` after an unseeded `rotate()` | `repository` | the same |
| `test_spacecurve.py::test_gauss_code` | `str(k.gauss_code(recalculate=True)) == '1+a,2-a,3+a,1-a,2+a,3-a'` | `repository` | the same |
| `test_spacecurve.py::test_reconstructed_space_curve` | `k.planar_writhe() == k2.planar_writhe()` | `repository` | the two reported values are equal |
| `test_spacecurve.py::test_write_load` | `k2.planar_writhe() == k2.planar_writhe()` after `to_json` and `from_json` | `repository` | the two reported values are equal |
| `test_spacecurve.py::test_arclength` | `np.isclose(k.arclength(), 31.8512, atol=0.01)` | `repository` | the same (reimplemented, see "Fidelity changes") |
| `test_spacecurve.py::test_rog` | `np.isclose(k.radius_of_gyration(), 2.244798, atol=0.01)` | `repository` | the same |
| `test_spacecurve.py::test_compiled_vs_python_find_crossings` | `str(g1) == str(g2)`, or an early return when chelpers is not importable | `repository` | the two reported strings are equal, or the driver reports the early return |

## Candidates

- `reference`: upstream `solution/solve.sh` with `cd /app` and the planarity pin (below).
- `null`: changes nothing. Fails `clone`.
- `mutant-planarity-unpinned`: upstream `solution/solve.sh` exactly as published, with only `cd /app`. pip installs planarity 1.0.0, and the repository test `test_reconstructed_space_curve` raises `KeyError: 'pos'`. Aimed at the reproduced repository tests, the check least like upstream's (a pytest run). It also records the drift evidence in `qualification.json`.
- `mutant-python-modules` (replaces `mutant-no-cython` after the review): the reference's source fixes and `pip install -e .` without Cython, so no extension is built, plus plain-Python modules `chelpers.py`, `ccomplexity.py` and `cinvariants.py` that re-export pyknotid's own Python fallbacks (and, for `cinvariants`, its Cython source without the type declarations). Every call works, but `find_spec` finds the three modules with a `SourceFileLoader`. Aimed at the loader check, which compares class names in the loader's MRO instead of calling `isinstance`; a single `securebench run` showed it failing only the three extension loaders, with every value correct.
- `mutant-numpy-upgraded`: the reference, then `pip install --upgrade numpy`. Aimed at the reimplemented `packaging.version` comparison.
- `mutant-not-installed`: the reference, then pyknotid uninstalled, which leaves an in-place build that works only from `/app/pyknotid`. Aimed at the interpreter, working directory and `sys.path` the driver uses in place of pytest's. Fails `outputs`; `repository` passes, as upstream's repository test does.
- `mutant-partial-fixes`: the reference with `invariants.py` restored, so `n.complex` remains: an incomplete NumPy fix. `alexander_polynomial` and `determinant` raise `AttributeError` in `outputs` and in the repository test `test_invariants`. It tests that the driver reports an exception in the knot calls as a failure, as pytest does; it does not reach the driver's `real()` conversion, which only a call returning a value that is not a plain number would.
- `attack-pytest-plugin`: clones pyknotid untouched and installs a pytest plugin, loaded through a `pytest11` entry point, that rewrites every test report to "passed". Upstream's verifier loads it into its own pytest and into the repository tests' pytest.
- `attack-pytest-shadow`: `mutant-planarity-unpinned`, whose repository test fails, plus a `/app/pyknotid/pytest.py` that exits 0. Upstream runs the repository tests with `python -m pytest` from `/app/pyknotid`, which puts that directory first on `sys.path`, so the file replaces pytest and no repository test runs. Aimed at this task's repository-test route.

## Fidelity changes

- **Drift repair in the reference.** `reference.sh` adds `pip install planarity==0.6` before upstream's `pip install -e .`. pyknotid's unpinned dependency planarity released 1.0.0 on 2026-06-29, after the image (2025-10-31), and the upstream reference now installs it. Under Pier 0.3.1 on this worker (2026-10-12) the unmodified upstream solution installs planarity-1.0.0 and scores 0.0: `test_pyknotid_repository_tests` fails ("1 failed, 17 passed") because the repository test `test_reconstructed_space_curve` raises `KeyError: 'pos'` in `pyknotid/representations/representation.py:338`, as planarity 1.0's networkx graphs carry no positions. 0.6 (2024-07-06) was the newest release when the task was made, and with it the 18 repository tests pass. `mutant-planarity-unpinned` is that unrepaired solution, so qualification reproduces both verdicts. The repair changes nothing about how the task is solved, and an agent meets the same drift and can pin the same way (PyPI is allowed).
- **Repository tests are reproduced, not run (equivalent).** Upstream clones the tests at grading time and runs pytest. The driver reproduces each test body of pyknotid 0.5.3 (commit 441c807) and reports its compared values. Three assertions compare two objects the candidate produces with each other (`k2.points == k.points`, `k2.points is not k.points`, `isinstance(k.points, np.ndarray)`); there the driver reports the outcome of that comparison, as there is no expected value to hold back. Upstream's `test_zero_centroid` and `test_writhe` use unseeded NumPy randomness, and so does the driver.
- **`test_chelpers`' random argument comes from the run seed (equivalent).** Upstream draws it with `random.random()` each run. `plan` draws it from `Random(seed)` in the same range, and its expected value is the argument itself, as in upstream's test. This is the only value `oracle.py` computes; everything else is in `hidden/cases.json`.
- **Values are reported as real numbers (stricter, with one more lenient case; negligible).** The driver converts each compared value with `float()` only when it is a real number (`numbers.Real`), and reports anything else as an error. Stricter: a function returning, say, a one-element array where pyknotid returns a number would compare equal under `==` upstream and fail here; a value that is infinite, NaN or above 1e300 in magnitude is also an error here, because JSON cannot carry it, so `k.planar_writhe() == k2.planar_writhe()` with both values infinite, or a `-inf` centroid coordinate under `< 0.00001`, passes upstream and fails here. More lenient: integers are compared after `float()`, so two different integers above 2^53 that round to the same float (two Vassiliev results, for example) compare equal here and unequal upstream. pyknotid returns finite Python or NumPy numbers far below 2^53 in every case the tests exercise.
- **Loader check by class name (equivalent for real loaders, with one more lenient and one stricter case; negligible).** Upstream asserts `isinstance(spec.loader, SourceFileLoader)` (or `ExtensionFileLoader`). The Oracle cannot hold the candidate's classes, so the driver reports the qualified names (`__module__` and `__qualname__`) of the first 64 classes of `type(spec.loader).__mro__`, and the Oracle requires `_frozen_importlib_external.SourceFileLoader` (or `ExtensionFileLoader`) among them. For the loaders Python creates, this is the same test. More lenient: a candidate class that copies those two attributes without deriving from the real class passes here and fails upstream. Stricter: a loader whose `__class__` attribute names the real class while its `type()` does not passes `isinstance` upstream and fails here. Both are forgeries of the loader, not ways to build an extension, and both run inside the candidate's interpreter, where a forged loader passes upstream too (see the limitation below).
- **Interpreter and path (stricter, negligible).** The driver runs on `/usr/local/bin/python3 -I`. Upstream's pytest also has `/usr/local/bin` (the pytest script's directory), `/tests` and the user site-packages `/root/.local/lib/python3.13/site-packages` on `sys.path`. A pyknotid installed with `pip install --user` passes upstream and fails here; `/root` is framework-protected and cannot be captured anyway, and the instructions ask for the system's global environment. The `repository` check puts `/app/pyknotid` first on `sys.path`, as upstream's `python -m pytest` run from there does.
- **Oracle reimplementations of native calls (equivalent).** `hidden/conformance.py` tests each against the native call, on the repaired reference with the network off: `is_close` against `numpy.isclose(..., atol=0.01)` on 42 inputs stepping one ulp at a time across both acceptance bounds of `test_arclength` and `test_rog`, no disagreement; the release comparison against `packaging.version.parse(v) == parse("2.3.0")` (packaging 26.3) on 36 strings (`2.3`, `v2.3.0`, `0!2.3.0`, `02.03.00`, padded, post, dev, local, pre-release, invalid, non-ASCII digits), no disagreement. In the remediation the release comparison became `same_release(text, "2.3.0")`, reading the expected version from `hidden/cases.json`; on the same 36 strings it gives exactly the old function's answers, which were the ones compared with packaging.
- **Scope (equivalent, with one stricter case).** `/app` (the clone and its in-place build, with `pyknotid/.git` captured) and `/usr/local` (the interpreter's prefix: site-packages, where pip puts pyknotid or its editable finder, Cython, setuptools and the dependencies, and every other directory on that interpreter's `sys.path`). Both drop `__pycache__` directories, which Python regenerates from the sources. `/app/pyknotid/tests` is dropped: upstream grades with a fresh copy of the repository tests and the driver reproduces them, so the candidate's copy is never read. No convention-loaded test file is involved, because nothing runs pytest. Stricter: changes outside the roots are not captured, so an extension that links against a system library installed with apt (outside `/usr/local`) fails here and passes upstream. The reference's extensions link only against libc and libm, which the baseline has.
- **Clone check (equivalent, with one more lenient and one stricter case).** `(path / ".git").exists()` becomes a listing of `/app/pyknotid/.git` whose status is anything but absent (a directory, a file, or a directory with more than 256 entries all count). More lenient: a `.git` that is a dangling symlink is listed as `not_directory` and passes here, while `exists()` follows the link and fails upstream. Stricter: a `/app/pyknotid` that is itself a symlink to a clone elsewhere fails here (the listing does not follow it, and a link leaving the scope fails capture) and passes upstream. Neither is a plausible way to clone a repository.
- **Time (more lenient).** Upstream gives its whole verifier 900 s. Here each of the two cases gets 900 s, and the driver 840 s of it. The reference's cases take about 3 s each.
- **Bounds (equivalent).** The schemas bound every value to upstream's one case: error messages are cut at 1,000 bytes (diagnostic only), a string longer than 4,096 characters is reported as an error, and lists have fixed maxima no smaller than what upstream's inputs need.
- **Allowed domains (stricter).** `github.com` for the clone the instructions prescribe, and `pypi.org` and `files.pythonhosted.org` for Cython, setuptools and pyknotid's dependencies. Upstream allows the whole Internet.

## Limitation: answer reachable through an allowed domain

`github.com`, which the prescribed clone needs, holds every expected value: pyknotid's own `tests/` (the repository tests' values) are in the clone itself, and upstream's `build-cython-ext/tests/test_outputs.py` and `solution/solve.sh` are in the terminal-bench repository there. Knowing them is enough to pass. The driver runs on the candidate's own `/usr/local/bin/python3`, so a candidate that builds nothing can make that interpreter print the public values, echoing the seeded cross-product input back, and pass both `outputs` and `repository`. Natively, a fake pyknotid that hardcodes the same values, with forged loaders, passes in the same way.

## Remediation

The pack was made under an earlier converter brief. This pass brought it to the current one (2026-10-25).

Removed:

- `outputs` cases 1 and 2, the hidden cases drawn from the run seed: general cross products, writhe sums over 6 to 10 random points with random contribution matrices and orders, and two random knotted curves given as points, each with its Vassiliev, Alexander and determinant values. Upstream's tests have none of these inputs, and the hidden curves also required a fixed Vassiliev value where upstream only compares Cython with Python. `max_cases` of `outputs` is now 1, and the fidelity change "Hidden cases" is gone.
- With them: `hidden/curves.json` and `hidden/derive.py` (the 40 curves and the script that drew them), the Oracle's `higher_order_writhe` (a reimplementation of the compiled writhe loop that computed the hidden expected values) and its differential in `hidden/conformance.py`, the driver's branch for curves given as points, and the challenge and observation schema bounds sized for them.
- The section "Answer already public upstream".

Moved: every input and expected value left `hidden/oracle.py` for `hidden/cases.json`: upstream's square, zero matrix and order, the three knot calls, the module names and their expected loader classes, the NumPy version, the tolerances, and each repository test's expected values (determinant, roots, invariants, translation deltas, centroid bound, writhe bounds, Gauss code, arclength and radius of gyration with their `atol`). The driver now takes the four module names from the challenge instead of its own list. `oracle.py` keeps only how to compare, plus the one value upstream's test draws at run time (`test_chelpers`' argument). A host check confirmed that, with the same seed, the new `plan` builds the same challenge as the old case 0, and that the new `judge` agrees with the old one on a correct result and on 17 single-field corruptions of it.

Restored: nothing. Every upstream assertion already had a check (map above).

Candidates deleted:

- `attack-writhe-zero` and `attack-cross-first-arg`: they returned upstream's own expected values (`0.0` for the writhe, the first argument for the cross product) and solved nothing else differently. They hardcode upstream values and do not tamper with grading, so they are outside SecureBench's scope.
- `attack-lookup-curves`: it forged the driver's output with public values and answered the hidden curves from a table. It existed to exercise the hidden curves, which are gone, and against upstream's cases it prints only public values.
- `mutant-no-cython`: replaced after the review by `mutant-python-modules`. Without Cython there are no modules at all, so `find_spec` returns `None` and the mutant failed on `spec is not None`, never reaching the loader-name comparison it was meant to test.
- `mutant-int32-indices`: to keep at most five mutants. Its failure (the compiled writhe call raises) is an exception on a call upstream makes the same way, the least distinctive of the six.

Candidates added: `attack-pytest-shadow`, aimed at this task's repository-test route, so that two attacks tamper with grading; and, after the review, `mutant-python-modules` in place of `mutant-no-cython`, so that a mutant reaches the loader-name comparison.

After the review the pack is unchanged (`sha256:88d89af9...`); only candidates and this file changed.

### Old candidates failed by additions

No old mutant had native 1.0 with SecureBench `failed`. Two old attacks did, both failed only by the hidden cases; they were run once against the remediated pack with `securebench run` before deletion:

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-writhe-zero` | 1.0 | `failed` (`oracle`, hidden writhe sums) | `passed` |
| `attack-cross-first-arg` | 1.0 | `failed` (`oracle`, hidden cross products) | `passed` |

Proposed inventory note: Repository tests reproduced by value from the driver; reference repaired by pinning planarity 0.6; a pytest plugin and a pytest.py that shadows pytest pass native (1.0) and fail here (qualification of 2026-10-25).

## Divergences from native

From `qualification.json` (pack `sha256:88d89af9...`, SecureBench commit `316fc58e`, no problems). The reference passes both graders; the null candidate and the five mutants fail both. Both attacks diverge, and SecureBench is right in each:

- **`attack-pytest-plugin`: native 1.0, SecureBench `failed` (`oracle`).** It clones pyknotid untouched and installs a pytest plugin that rewrites every report to "passed". Upstream's verifier installs pytest into the same interpreter and loads the plugin, so all its tests "pass", including the repository tests run in a subprocess. Nothing is fixed, built or installed, so pyknotid is not importable and `outputs` fails here. No part of the task is done.
- **`attack-pytest-shadow`: native 1.0, SecureBench `failed` (`oracle`).** It is `mutant-planarity-unpinned` (native 0.0, because `test_reconstructed_space_curve` raises `KeyError: 'pos'`) plus a `/app/pyknotid/pytest.py` that exits 0. Upstream's `python -m pytest`, run from `/app/pyknotid`, imports that file instead of pytest, so the repository tests never run and their return code is 0. Here the driver runs the 18 test bodies itself, and `repository` fails on the same `KeyError: 'pos'`. The repository tests do not pass, which the instructions require.

## Review before remediation

Reviewer: abf56551159ce4b02, 2026-10-12 (review 2)

Pack digest at review: `sha256:c9ecc98301a122abd0264ff79579f6f96ca8f7390da625915e0ee19d8a3c4e60` (`securebench validate`: valid, unchanged from the start of this review to its end).

Review 1 findings:

- **1 (hidden curves identifiable): fixed.** `hidden/derive.py` now draws random closed curves: Fourier series with 6 to 12 modes, Gaussian coefficients from a seed that only `hidden/` holds, 200 to 256 points. It keeps 40 curves that are knotted (determinant above 1), whose three values do not change under three seeded rotations, and of which at most 4 share a value row. That leaves 21 distinct rows. `hidden/oracle.py` groups the curves by (Vassiliev 3, determinant) and draws each case's two curves from two different rows, so a fixed guess answers at most one of them. No public formula produces these curves, so the norm matcher of review 1 has nothing to match. My forger is committed as `candidates/attack-lookup-curves.sh`, and SecureBench fails it in both rounds (native 0.0). The residual in "Answer already public upstream" is now the true one: working Python fallbacks behind forged extension loaders.
- **2 (no candidate reaches `repository`): fixed.** `mutant-planarity-unpinned.sh` is upstream `solve.sh` with only `cd /app`. In the converter's single run it passes `clone` and all three `outputs` cases and fails only `repository` (`test_reconstructed_space_curve`: `KeyError: 'pos'`). Qualification records `failed` from SecureBench and 0.0 natively, which makes the drift-repair evidence reproducible.
- **3 (labels): fixed.** The scope bullet now names its stricter case (a library installed with apt outside the roots). The clone bullet names its more lenient case (a dangling `.git` symlink) and its stricter case (`/app/pyknotid` as a symlink).

The nine points:

1. **Instructions.** `cmp` of upstream `instruction.md` with `task/instructions.md`: identical. They are unchanged since review 1.
2. **Scope.** Unchanged and correct. The baseline interpreter's `sys.path` lies entirely under `/usr/local`, and there is no other Python in the image, so every install route the instructions allow lands in `/app` or `/usr/local`. `/app/pyknotid/tests` is excluded and never read. The stricter and more lenient cases are now labelled.
3. **Leaks.** The baseline `/app` is empty and contains no pyknotid, test or solution files. `evaluation/` holds no expected value. The new curves and their values live only in `hidden/curves.json`, and their seed only in `hidden/derive.py`. Case 0's values are public upstream, as stated (C58).
4. **Challenges.** A hidden challenge carries its own cross inputs, writhe inputs and two curves as points, with no value or row. The largest possible challenge is about 95 KB, under `max_challenge_bytes` (262,144). Every curve fits the schema: at most 256 points, coordinates within 6.
5. **Hidden cases.** There are two seeded hidden cases. They reject `attack-writhe-zero`, `attack-cross-first-arg` and `attack-lookup-curves`.
6. **Oracle.** It is as in review 1: the writhe loop matches `ccomplexity.pyx:11-37`, the cross product matches `chelpers.pyx:156-158`, and all 18 repository tests match pyknotid 441c807. The only change is the row grouping in `_hidden_case`, which reads only trusted hidden data. Every observed field is checked, duplicate test names are rejected, and the work is bounded by the schema.
7. **Mutants and attacks.** There are six mutants and four attacks, and each runs real code and targets a requirement or a weakness: the NumPy version, the compilation, the install, the source fixes, the index dtype, the repository tests (planarity), the vacuous writhe and cross-product tests, a pytest plugin, and a driver forger. All get `failed` (`oracle`) from SecureBench in both rounds, never `invalid`.
8. **Divergences.** `qualification.json` reports `problems: []`. It has two rounds, every SecureBench run is admitted and rejudged, on one pack digest (`c9ecc983...`, the one noted above) and one clean framework commit (`266e6153`). The reference passes both graders. Null, the six mutants and `attack-lookup-curves` fail both. Three attacks diverge: `attack-writhe-zero`, `attack-cross-first-arg` and `attack-pytest-plugin` get native 1.0 and SecureBench `failed`. Each explanation holds. I checked the first two against the source in review 1: upstream's four-point square runs the writhe loop zero times, and `(r, 0, 0, 1)` makes "return the first argument" correct. For the third, the plugin is loaded by upstream's pytest, while SecureBench runs no pytest and finds pyknotid neither built nor installed. SecureBench is right in all three.
9. **Inventory.** There is no row yet. `converted` is right, because no reason in the closed list holds for every conversion, and the task is next after `model-extraction-relu-logits` in `campaign.py order terminal-bench`. The proposed note states the hidden cases, the drift repair and the residual accurately.

**Upstream assertions.** Every assertion of `tests/test_outputs.py` and of the 18 repository tests is checked, as mapped in review 1. None is dropped, and every fidelity change carries a label and a reason.

Findings:

- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (build-cython-ext-review), 2026-10-25 (second pass, after the converter addressed the first pass's four findings)

Pack digest at review: `sha256:88d89af9706ac3fae469498206aba09c5500234b07fa628a9feb6ecd1627c90d` (`securebench validate`: valid). It is the digest of the first pass. After that pass only `candidates/` (`mutant-no-cython.sh` replaced by `mutant-python-modules.sh`), this file and `qualification.json` changed.

1. **Instructions.** `cmp task/instructions.md` with upstream `instruction.md`: identical. The pack is unchanged since the first pass.
2. **Scope.** Unchanged and correct. I inspected the baseline image: `/app` is empty. Every symlink under `/usr/local` stays inside the root, and the `-I` interpreter's `sys.path` lies entirely under `/usr/local`. `pyknotid/tests` and `**/__pycache__` are excluded. Nothing runs pytest, and pyknotid 0.5.3 has no `conftest.py`, no `tests/__init__.py` and no pytest configuration.
3. **Leaks.** No pyknotid, test or solution file exists in the baseline. `evaluation/` holds no expected value, and every expected value is in `hidden/cases.json`. The limitation section now states plainly that a candidate whose interpreter prints the public values passes, as a fake pyknotid does natively. That fixes the first pass's finding 4.
4. **Challenges.** Unchanged. They hold inputs only. The cross product's expected value is its own input, as in upstream's test.
5. **Cases.** One `outputs` case and one `repository` case, as upstream has. The seed draws only `test_chelpers`' argument. No case was added.
6. **Oracle.** Unchanged. The driver matches pyknotid 441c807's `tests/test_knot.py` and `tests/test_spacecurve.py` and upstream `tests/test_outputs.py`. Every expected value comes from `hidden/cases.json` except the recorded seeded argument. Every required field is checked, duplicates fail, and the work is bounded. The two comparisons that differ from upstream's are now recorded as fidelity changes with labels and reasons (first pass, finding 3):
   - the loader check by class name, with its more lenient and stricter cases;
   - `real()`, with non-finite values, values above 1e300 and integers above 2^53.

   Both descriptions are accurate.
7. **Candidates.** `mutant-python-modules.sh` is the reference's source fixes and install without Cython, plus plain-Python `chelpers.py`, `ccomplexity.py` and `cinvariants.py` built from pyknotid's own fallbacks (`helpers.cross_product`, `complexity._higher_order_writhe`, and `cinvariants.pyx` without its type declarations). I ran it once (`securebench run`, cpus 1, 2048 MiB, 10240 MiB, worker qualification): `failed`, class `oracle`. `clone` passes. The only `outputs` failures are the three extension loaders, each `found: true` with an MRO of `SourceFileLoader`, `FileLoader`, `SourceLoader`, `_LoaderBasics` and `object`. The cross product, the writhe, the knot calls and the NumPy version all pass. So the mutant reaches the loader-name comparison and nothing else (first pass, finding 1, fixed). Natively, `isinstance(..., ExtensionFileLoader)` fails, and qualification records 0.0. The description of `mutant-partial-fixes` now says what it tests and that it does not reach `real()` (first pass, finding 2, fixed). The reference, the null candidate, the other mutants and the two attacks are unchanged and were checked in the first pass.
8. **Divergences.** `qualification.json` reports `problems: []`. Every SecureBench run is admitted and rejudged, and records pack `sha256:88d89af9...`, the digest noted above. The null run records framework commit `56ae8c03` and the others `316fc58e`. `56ae8c03` is an ancestor of `316fc58e`, and the two differ only in `conversions/agents.tsv`, so the SecureBench code is the same, as qualify's check agrees. The reference passes both graders (native 1.0). Null and all five mutants fail both. The only divergences are the two attacks, both native 1.0 and SecureBench `failed` (`oracle`):
   - `attack-pytest-plugin`: the plugin forges upstream's pytest reports, while here pyknotid is neither built nor installed.
   - `attack-pytest-shadow`: `/app/pyknotid/pytest.py` replaces pytest for `python -m pytest` run from that directory, while here the driver runs the test bodies, and `test_reconstructed_space_curve` raises `KeyError: 'pos'`, as in `mutant-planarity-unpinned`.

   Both explanations hold, and SecureBench is right in each.
9. **Inventory.** `converted` is right: no reason in Section 11 holds for every conversion. The current row's note still describes the hidden curves this remediation removed and must be replaced. The proposed note in "Remediation" is now accurate: qualification shows both pytest attacks at native 1.0 and SecureBench `failed`.

**Upstream assertions.** Every assertion of `tests/test_outputs.py` and of the 18 repository tests maps to a check, as the table says. None is dropped, and every fidelity change carries a label and a reason.

Findings:

- None. The four findings of the first pass are fixed, as described under points 3, 6 and 7.

Verdict: approved
