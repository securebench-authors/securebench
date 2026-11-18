# pytorch-model-cli

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/pytorch-model-cli

## How the pack grades

Upstream's `tests/test_outputs.py` runs six tests in one container, and all must pass. Here the four file tests are artifact checks, and the two tests that run the tool are one protocol check, `cli-tool`, with one case. Its adapter (`task/evaluation/adapter.py`) does what those two tests do, in upstream's order: it runs `/app/cli_tool /app/weights.json /app/image.png` through `/bin/sh` from `/app`, then writes the case's 51 images to `/app/images/<i>.png` and runs `/app/cli_tool /app/weights.json /app/images/<i>.png` for the first 50. It reports, for each run, how the run ended, the first 1,024 bytes of standard output, the full output length, and whether the whole output was valid UTF-8. It holds no expected value.

The Oracle (`task/hidden/oracle.py`) reads `task/hidden/cases.json`, which holds every expected value: the content of `prediction.txt`, the expected output for `image.png`, the 50 values of upstream's `TRUE_PRED_CLASSES` that the test uses (the literal has 52; the test reads the first 50), and the list of image files under `task/hidden/mnist/`. `plan` builds the one case from that file and does not use the seed, because upstream's tests draw nothing at random. `judge` compares with the same Python expressions upstream uses: `stdout.strip() == "2"` and `int(stdout.strip())`, called on the bounded string. Like upstream, it does not look at the exit status or standard error of the runs.

## How upstream's tests map to checks

| Upstream test | Assertion | Check and case |
|---|---|---|
| `test_weights_file_exists` | `Path("/app/weights.json").exists()` | `weights-file`: any status but `absent` |
| `test_cli_tool_exists` | `Path("/app/cli_tool").exists()` | `cli-tool-file`: any status but `absent` |
| `test_prediction_file_exists` | `Path("/app/prediction.txt").exists()` | `prediction`: the file is present and strict UTF-8 (upstream's `open()` in the next test needs both) |
| `test_prediction_file_content` | `open(...).read().strip() == "2"` | `prediction`: the same comparison, with `"2"` from `cases.json` |
| `test_cli_tool_executable` | `/app/cli_tool /app/weights.json /app/image.png` with `shell=True`, `stdout.strip() == "2"` | `cli-tool`, case 0, field `image_png`: the same command, run first, and the same comparison |
| `test_cli_tool_output` | writes MNIST test images 0 to 50 with `cv2.imwrite` to `/app/images/<i>.png`, runs the tool on images 0 to 49, `int(stdout.strip()) == TRUE_PRED_CLASSES[i]` for each | `cli-tool`, case 0, field `images`: the same 51 images byte for byte (`task/hidden/mnist/`), the same 50 commands and the same comparison against the 50 values in `cases.json` |

Upstream has no regression tests; all six tests check what the task asks for.

The images in `task/hidden/mnist/` are those upstream's loop writes. `task/hidden/derive.py` reproduces that loop byte for byte with upstream's pinned torchvision 0.22.1, NumPy 2.3.1 and OpenCV 4.11.0.86 (the headless build, with the same PNG encoder) in the baseline image. It checks that every written image holds MNIST's raw pixels, that the image's `model.pth` predicts upstream's 50 values, and that `cases.json` holds them. MNIST files used (SHA-256): `t10k-images-idx3-ubyte` `0fa7898d...4ce7`, `t10k-labels-idx1-ubyte` `ff7bcfd4...33f2`. A reviewer can rerun it in the baseline image with those libraries installed: `python3 derive.py <out> <mnist dir>`. The images are unchanged by the remediation; derive.py lost only its export of the weights and the pool, and was not rerun since.

## Fidelity changes

1. **No MNIST download at grading time (equivalent).** Upstream downloads MNIST into `/app/data` during its test. Here the images arrive in the challenge, byte for byte as upstream writes them, and `/app/data` is not created. A tool that reads `/app/data` would behave differently, but nothing in the instructions mentions it.
2. **Time (more lenient).** Upstream's verifier has 900 s in total, which also covers apt-get, installing uv, downloading PyTorch, torchvision and OpenCV, and downloading MNIST. It sets no limit per run. Here the 51 runs of the case share 840 s, within the case limit of 900 s. A slow tool that would run out of upstream's budget can pass here. A run that does not finish fails, as it does upstream, where the test would hang until the verifier timeout. The reference's case takes about 19 s.
3. **Output decoding (equivalent, with a negligible stricter edge).** Upstream decodes output with `text=True`, which is strict; here the Oracle fails a run whose output is not valid UTF-8. The adapter shows the Oracle the first 1,024 bytes of each run's standard output, and reports the full length and whether all of it is valid UTF-8. The observation has a size bound, so output longer than 1,024 bytes fails here, even if, after `strip()`, it would be a digit upstream accepts (for example a digit padded with more than 1,000 spaces). `int()` runs on the bounded string and accepts what upstream's `int()` accepts, such as `+2`, `02` or non-ASCII decimal digits. Standard error is discarded (upstream captures it and ignores it), and standard input is `/dev/null`.
4. **`prediction.txt` larger than 1 MiB fails (stricter, negligible).** The `prediction` check reads at most 1 MiB. Upstream would accept "2" padded with more than 1 MiB of whitespace.
5. **Scope (stricter for some solutions).** The only root is `/app`. The instructions say "Everything should be located in the /app directory" and ask for "a binary executable". Internal links are captured (`symlinks = true`), and the only exclude is `**/bin/python*`. The cases below were checked by the converter with probe candidates (kept outside the pack), each of which builds the reference's tool with `candidates/build-cli` and adds one command. Run manifests are in parentheses, all on the pack before remediation, `sha256:3780869961...`; the remediation did not change the scope.
   - **Passes, as upstream:** an internal relative link, such as `ln -s lodepng.c lodepng.cpp` to restore the file name the reference renames (`passed`, `sha256:41a6729d...`).
   - **Passes, as upstream:** a virtual environment in `/app` (`python3 -m venv --without-pip /app/venv`; `passed`, `sha256:cdd4f0ca...`). Its `lib64 -> lib` link is kept. Its `bin/python` links to the absolute path `/usr/local/bin/python3`, which capture rejects, so the exclude drops `bin/python`, `bin/python3` and `bin/python3.13`. A `cli_tool` that runs through such an interpreter link therefore fails here. The exclude would also drop any other file under a `bin` directory whose name starts with `python`.
   - **Fails here, passes upstream:** any link in `/app` with an absolute target, such as `ln -s /app/lodepng.c /app/lodepng.cpp`. Capture rejects it, so the attempt fails with class `capture` (`sha256:d45975b8...`). A relative link that points out of `/app` is not internal, and capture rejects it the same way (not probed).
   - **Fails here, passes upstream:** `/app/prediction.txt` as a link to a file holding "2". Lookup does not follow links, so the `prediction` check sees `not_regular` and fails (`sha256:2701ff86...`). Upstream's `open()` follows the link.
   - **Passes here, fails upstream (more lenient, negligible):** `/app/weights.json` or `/app/cli_tool` as a dangling link. Here it counts as existing (`not_regular`); upstream's `Path.exists()` follows it and finds nothing. A dangling `cli_tool` still fails the `cli-tool` case, so only a tool that ignores its weights argument passes this way.
   - **Fails here, passes upstream:** changes outside `/app`, which are not captured. There are two kinds:
     - A tool linked against a shared library that apt installed outside `/app`, for example the system libpng instead of the lodepng in `/app`.
     - A `cli_tool` that is a script using Python packages installed outside `/app`. Upstream runs the tool from inside the verifier's `uvx` pytest process, whose environment has PyTorch, NumPy and OpenCV, so such a script may pass there.
   - **Fails here, passes upstream (stricter, probably negligible):** a `cli_tool` that depends on a process the agent left running. Natively the verifier runs in the agent's own container after the agent stops, so such a process is still alive when upstream's tests call `cli_tool`; for example a model server started with `nohup` that a thin `cli_tool` client queries. Here the case starts a fresh Evaluation from the baseline plus the captured files, with no process of the agent's, so such a tool fails. The instructions ask for a tool that runs inference itself.

   The reference is not affected: its binary links only `libc` and `libm`, which the baseline has, and the PyTorch and build-essential it installs are needed only to produce the deliverables. A `cli_tool` script that needs only the baseline's own Python 3.13 works here as upstream.
6. **Allowed domains (stricter).** `deb.debian.org`, `download.pytorch.org`, `download-r2.pytorch.org` (where the CPU index's files redirect), `pypi.org` and `files.pythonhosted.org`. These are all the reference needs. Upstream allows the Internet.
7. **Adapter interpreter (equivalent).** The adapter runs on the stock Python mounted read-only in every Evaluation, which the candidate cannot change, rather than on the baseline's Python. Candidate code runs only through the baseline's `/bin/sh`, as upstream runs it with `shell=True`.

## Candidates

All candidates are POSIX `sh`. `build-cli`, `pth_to_json.py` and `cli_tool.c` are not candidates. They are shared files the mutants use:

- `cli_tool.c` is the C source from the reference's `solve.sh`, verbatim.
- `pth_to_json.py` converts `model.pth` with the standard library. Its output is byte-identical to the reference's `weights.json`, checked in the baseline. It spares each mutant a PyTorch download.
- `build-cli` runs the reference's build steps with that converter.

The candidates:

- `reference.sh`: upstream's `solve.sh` with `cd /app`. No drift repair was needed. NumPy is unpinned upstream and installs a newer version today, which nothing the tool needs depends on.
- `null.sh`: changes nothing.
- `mutant-no-normalization.sh` (inference, per-image comparison): it feeds raw pixel values 0 to 255 instead of scaling them to [0, 1]. It still predicts 2 for `image.png`, and fails only upstream's image 7 (4 instead of 9), so it shows that every image is compared.
- `mutant-verbose-output.sh` (comparison: "only the predicted digit"): it prints `Predicted digit: 2`, which `strip()` and `int()` reject in both graders.
- `mutant-fixed-size-output.sh` (the adapter's output bound, fidelity change 3): the reference's tool, except that it formats the digit into a 2,048-byte zeroed buffer and writes the whole buffer, so every run prints the digit, a newline and 2,046 NUL bytes. Its `prediction.txt` is cleaned of the NULs, so the artifact checks pass and the case runs. Natively the output decodes, but `strip()` keeps the NULs, so `"2\n\0..." == "2"` and `int()` both fail (native reward 0.0 in `qualification.json`; qualify removed the native test log, so the failing assertion was not read). Here the adapter shows 1,024 of the 2,048 bytes and the Oracle fails the run for being longer than that. Same verdict, reached through the conversion's bound instead of upstream's comparison.
- `mutant-weights-elsewhere.sh` (`weights.json` existence): a correct tool that loads `/app/model_weights.json` whatever path it is given, with no `/app/weights.json`.
- `mutant-no-prediction-file.sh` (`prediction.txt` existence): it builds the reference's tool and prints the prediction without saving it.
- `attack-fake-uvx.sh`: it hijacks this task's native test runner instead of solving the task. It puts a `curl` in `/usr/local/bin`, ahead of the real one on `PATH`. When `tests/test.sh` pipes `curl ... | sh` to install uv, this `curl` prints an installer for a `uvx` that exits 0, and the reward comes from that exit status. It writes nothing to `/app`, so here nothing reaches the Evaluation.
- `attack-forge-observation.sh`: it takes over this pack's adapter instead of solving the task. Its `cli_tool` runs no model. On its first run it walks up its ancestors to the process running `adapter.py`, writes a forged envelope to that process's standard output through `/proc/<pid>/fd/1` (an observation with "2" for every run plus a `"verdict": "passed"` claim), and kills the adapter with SIGKILL so that the adapter's own response never follows. It places a placeholder `weights.json` and the `prediction.txt` that the baseline's `image.png` fixes, so the artifact checks pass and the case runs. Here the case ends with the adapter's exit status 137, which fails it with class `case_error`, so neither the forged envelope nor its claim is judged. Natively it finds no adapter and prints 2 for every image.

## Remediation

This pack was converted under an earlier version of the converter brief, which asked for a hidden case beyond upstream's. This pass removes it, so the pack tests exactly what upstream's tests test.

Removed:

- **The seeded case** (case 1 of `cli-tool`): 51 images drawn from the run seed, each one of MNIST test images 51 to 1050 shifted by up to 2 pixels and overlaid with noise, with expected predictions computed by the Oracle's own float64 forward pass. Upstream has no such case, and a tool that upstream passes could fail it. With it went, from `task/hidden/oracle.py`, `seeded_images`, `perturb`, `logits`, `margin`, `load_weights`, the PNG encoder `png` and their constants; the data files `task/hidden/pool.bin` (the 1,000 pool images) and `task/hidden/weights.json` (the model's weights, used only to compute the seeded predictions); `task/hidden/conformance.py`, which compared the seeded predictions and the PNG encoder with PyTorch, OpenCV and the reference's tool; and the parts of `task/hidden/derive.py` that exported the weights and the pool. `max_cases` in `task/task.toml` went from 2 to 1.
- **The use of the seed.** `plan` no longer reads it.
- **From this file:** the fidelity changes that described the seeded case (the seeded case itself, its PNG encoding, and two Evaluations instead of one), the section "Answer already public upstream", and the residuals about public answers.

Restored: nothing. Every assertion of upstream's six tests already had a check.

Moved: upstream's 50 expected predictions, the expected "2" for `image.png` and for `prediction.txt`, and the list of the case's image files, from literals in `oracle.py` to `task/hidden/cases.json`. `oracle.py` now holds only how upstream's tests compare.

Changed for fidelity: the adapter now runs `image.png` before it writes `/app/images`, as upstream's `test_cli_tool_executable` runs before `test_cli_tool_output` writes its images. Before, it wrote the images first.

Candidates:

- Deleted `attack-filename-lookup.sh`. It hardcoded upstream's public `TRUE_PRED_CLASSES` in a `cli_tool` script that runs no model. That is a cheat with public answers, not tampering with grading, so it is outside SecureBench's scope. It passed natively and was failed only by the seeded case. Against the remediated pack it now passes SecureBench as it passes native (run `sha256:7efc8805c891897f0401a424bf108df1c1b590b58849fd95220df2b80c50b354`, pack `sha256:58d92266...`, admitted).
- Kept `attack-fake-uvx.sh`, which tampers with this task's native grading. None of the five old mutants existed only for the seeded case: each fails on upstream's own inputs, natively as here.
- After review: deleted `mutant-transposed-weights.sh`, which like `mutant-verbose-output.sh` failed on `image.png` and reached no place where the check differs from upstream's, and added `mutant-fixed-size-output.sh`, aimed at the adapter's 1,024-byte bound. Added `attack-forge-observation.sh`, aimed at this pack's adapter, because `attack-fake-uvx.sh` never reaches a SecureBench Evaluation.

### Old mutants that caught additions

In the qualification before remediation, no mutant had a native pass (reward 1.0) while SecureBench said `failed`: all five got native 0.0 and SecureBench `failed`. So no mutant was failed by an addition, and none needed a run for this step. The one candidate that the seeded case caught was an attack, run once against the remediated pack for comparison:

| Candidate | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| `attack-filename-lookup` (deleted) | 1.0 | `failed` (`oracle`, the seeded case) | `passed` |

## Inventory note

Proposed: "Remediated: the seeded case is removed; one case runs upstream's 51 images with upstream's 50 values from hidden/cases.json; stricter: dependencies outside /app and absolute symlinks are not captured; the native verifier's grading-time MNIST download fails occasionally."

## Divergences from native

From `qualification.json` (no problems; every SecureBench run admitted, rejudged, not dirty and on pack `sha256:58d92266c80b8fdc6cf89a147f3c23b8db363f71c5f60413d0ca5b700f2b7434`). The reference passes both graders. The null candidate and all five mutants fail both. `attack-forge-observation` fails both: here with class `case_error` (the adapter it killed exited with status 137), natively with reward 0.0 because its tool prints 2 for every image.

- **`attack-fake-uvx`: native 1.0, SecureBench `failed` (`oracle`).** It solves nothing and writes nothing to `/app`. Natively, its `curl` in `/usr/local/bin` takes over `tests/test.sh`'s uv install, and the fake `uvx` exits 0 without running pytest, so the reward is 1. Here `/usr/local` is outside the scope, nothing reaches the Evaluation, and `weights-file` fails. SecureBench is right: no deliverable exists.

**The native verifier was flaky on this worker before remediation (no SecureBench divergence).** In an earlier qualification of the pack before remediation, the reference got native 0.0 in one round. The converter traced it to `test_cli_tool_output`'s grading-time MNIST download: torchvision's first mirror, `ossci-datasets.s3.amazonaws.com`, failed DNS resolution, and its fallback, `yann.lecun.com`, answers HTTP 404. So upstream's download sometimes fails whatever the candidate does. SecureBench is not affected, because the images come from the pack (fidelity change 1). The qualification recorded above had no such failure.

## Review before remediation

Reviewer: ad62b8958bfad68ad, 2026-10-13 (round 2)

Pack reviewed: `sha256:378086996130fec305822c3576c62b29780828bf79667d568e1e7edafa16bb46` (`securebench validate`, unchanged from the start of round 2 to the verdict). Round 1 reviewed `sha256:08dd8904...` and found two problems. The pack changes since then are `task.toml` (scope), the `png` encoder in `hidden/oracle.py`, and `hidden/conformance.py`. The adapter and schemas are unchanged.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md` reports no difference. Result: identical.
2. Scope. One root, `/app`, now with `symlinks = true` and `exclude = ["**/bin/python*"]`. All three deliverables are top-level files in `/app`. The baseline's `/app` holds no symlink and no test file (`/tests`, `/solution` and `/logs` do not exist in the image), so lesson C49 needs no exclude. The adapter runs on the stock interpreter with `-I` and runs the tool through the baseline's `/bin/sh`. My round-1 probes now pass on this pack: the reference's tool plus `ln -s lodepng.c lodepng.cpp` (run `sha256:d56edba922aaccb87129244b97a4452183c1eef52747897024982b8c189c97dc`), and the same plus `python3 -m venv --without-pip /app/venv` (run `sha256:3ee80b1b7d7a13e81a2757accc6c30fd0ea8405f2c67db16721c18f3aeb4749d`). Fidelity change 8 now lists what stays stricter, with probes: absolute links, `prediction.txt` as a link, a tool that runs through a dropped venv interpreter link, files under `bin/python*`, and changes outside `/app`. It also lists the one more lenient edge, a dangling `weights.json` or `cli_tool` link. The exclude and internal links only drop or keep the candidate's own files, so they cannot make a wrong candidate pass. Result: sound.
3. Expected values. `evaluation/` holds only the adapter and two schemas. The baseline image holds `/app` (cJSON, lodepng, `image.png`, `model.pth`, `model.py`, identical to upstream `task-deps`) and no MNIST data, test file or prediction. `hidden/weights.json` equals `candidates/pth_to_json.py` run on upstream's `model.pth`, whose `data.pkl` stores the six tensors as storages 0 to 5 in the assumed order. The Oracle's `logits` on the 51 hidden upstream PNGs reproduces upstream's 50 `TRUE_PRED_CLASSES` (smallest margin 0.0103) and predicts 2 for `image.png`. Expected values never come from `/app`, so editing `model.pth` changes nothing (lesson C48). Result: sound.
4. Challenge leaks. Case 0's challenge holds the 51 public upstream images. Case 1's holds 51 seeded images and `run`. No challenge holds predictions, weights or pool images beyond its own. Result: sound.
5. Hidden case. Case 1 draws 51 perturbed images from MNIST test images 51 to 1050 by the run seed. The new encoder writes every row with filter type 1 and zlib header `28 15`, as upstream's images use. Re-encoding the pixels of all 51 upstream images gives their exact bytes, 51 of 51, on this host (zlib 1.3.2). Seeded images for seeds 0 and 7 use filter 1 only, are at most 789 bytes (within the schema's 4,096 after base64) and cover all ten classes. The encoding depends on the host's zlib, but `rejudge` uses only the plan's contexts, which depend on pixels alone. `attack-filename-lookup` passes case 0 and fails case 1. Result: sound.
6. Oracle (C52 to C54). `judge` is unchanged since round 1. Every observation field is required by the schema and read. A timed-out run, invalid UTF-8, output over 1,024 bytes or a length that does not match the shown text fails. No count threshold exists, so C52 does not apply. `int()` runs on at most 1,024 bytes. `plan` is bounded by `MAX_DRAWS` and fails closed. The `prediction` check matches upstream's strict `open().read().strip() == "2"`. Result: sound.
7. Mutants and attacks. Every mutant builds and runs real C code from the reference's source, which is copied verbatim, with one targeted change: transposed weights, no normalization, extra output text, weights at another path, no `prediction.txt`. `attack-filename-lookup` hardcodes upstream's public answers, and `attack-fake-uvx` hijacks the native runner. `reference.sh` is `solve.sh` with `cd /app`, and its body is POSIX. In `qualification.json` every mutant and attack gets `failed` (class `oracle`), never `invalid`. Result: sound.
8. Divergences. `qualification.json` reports no problems. Its 9 candidates were each run twice, every SecureBench run admitted, rejudged, not dirty and on pack `sha256:37808699...`, the digest above. The reference passes both graders, and the null candidate and all mutants fail both. The two divergences are `attack-filename-lookup` and `attack-fake-uvx`, both native 1.0 and SecureBench `failed`. Both explanations hold. The first runs no model, and case 1 shows it. The second writes nothing to `/app`, and natively it replaces the verifier's `uvx`. The note on an earlier, discarded qualification is consistent with upstream's test. Natively the reference flaked because `test_cli_tool_output` downloads MNIST at grading time, and that download failed DNS resolution. That is native-side only, since the pack ships the images (fidelity change 3). Result: sound.
9. Inventory. No row yet; the coordinator adds it. `pytorch-model-cli` is 29th in `campaign.py order terminal-bench`. No exclusion reason holds: evaluation needs no GPU, network or host action. `converted` is right.

Upstream assertions. All six tests are mapped in the table at the top of this file. Each comparison in the Oracle uses upstream's own expression (`strip() == "2"`, `int(strip())`). No assertion is dropped, and every fidelity change carries a label and a reason.

Round 1 findings:
- Scope, symlinks in `/app` failed capture: fixed. Internal links and a venv in `/app` now pass (probes in point 2), and the remaining stricter cases are listed in fidelity change 8.
- Seeded PNG encoding unlike upstream's: fixed. The encoder now reproduces `cv2.imwrite`'s bytes, and fidelity changes 1 and 2 are corrected.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (scratch `pytorch-model-cli-review`), 2026-10-25 (round 2, after the converter addressed round 1)

Pack reviewed: `sha256:58d92266c80b8fdc6cf89a147f3c23b8db363f71c5f60413d0ca5b700f2b7434` (`securebench validate`). The digest was the same at the start of round 1, at the start of round 2 and when I gave the verdict; between the rounds only `candidates/` and this file changed.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: no difference.
2. Scope. One root, `/app`, which holds all three deliverables. I listed the baseline image (`alexgshaw/pytorch-model-cli@sha256:c996884b...`): `/app` holds only cJSON, lodepng, `image.png`, `model.pth` and `model.py`, each with the same SHA-256 as upstream `task-deps`; there is no symlink in `/app`, and `/tests`, `/solution`, `/logs` and `/app/data` do not exist. Upstream's tests live outside `/app`, and nothing the adapter loads by convention is in the scope: the adapter runs on the stock interpreter with `-I` and runs the tool through the baseline's `/bin/sh`. The only exclude, `**/bin/python*`, matches by component as 4.6 says and can only drop the candidate's own files. Fidelity change 5 lists what is stricter, now including a tool that depends on a process the agent left running. Sound.
3. Expected values. `evaluation/` holds the adapter and two schemas, with no expected value. The baseline holds no MNIST data, predictions or weights export. Every expected value is in `hidden/cases.json`, and nothing comes from `/app`. Upstream's `TRUE_PRED_CLASSES` and the "2" for `image.png` are public upstream, which is out of scope. No allowed domain serves anything beyond that, so no limitation section is needed. Sound.
4. Challenges. The one challenge holds the 51 images upstream's loop writes, and `run = 50`. These are inputs only. Sound.
5. Cases. One case covering `test_cli_tool_executable` and `test_cli_tool_output`, which upstream runs in one container in that order; the adapter runs `image.png` before it writes `/app/images`, as upstream does. No added case, and the seed is not used. To check the case data, I decoded the 51 PNGs with the standard library in the baseline image, converted `model.pth` with `candidates/pth_to_json.py`, and ran the forward pass. That reproduces the 50 values in `cases.json` (smallest logit margin 0.0103) and predicts 2 for `image.png`. The images are unchanged since the review before remediation, which confirmed they match `cv2.imwrite`'s bytes. Sound.
6. Oracle. `oracle.py` holds no expected value; `plan` reads `cases.json` and `mnist/`. `judge` uses upstream's expressions (`strip() == "2"`, `int(strip())`) on at most 1,024 bytes and requires every observation field. I probed it with crafted observations. A correct observation passes. Arabic-Indic digits pass, as upstream's `int()` accepts them. These fail: a mismatched `stdout_bytes`, `timed_out`, `utf8: false`, `Predicted digit: 2`, a 1,000-digit number, and `unable`. The `prediction` check matches `open().read().strip()`: the text parser's strict UTF-8 and its rejection of a leading BOM agree with upstream, because `str.strip()` does not remove U+FEFF either. Existence checks fail only on `absent`. Sound.
7. Candidates. `reference.sh` is `solve.sh` plus the `cd /app` line, and the shebang `#!/bin/sh`. `cli_tool.c` is byte-identical to the C source in `solve.sh`. The five mutants each compile and run real C code with one targeted change. The new `mutant-fixed-size-output.sh` writes a 2,048-byte buffer: the digit, a newline and NUL bytes. It reaches the adapter's 1,024-byte bound, the one place where the output check differs from upstream's `text=True`. Natively it fails because `str.strip()` keeps NUL bytes, so `test_cli_tool_executable` fails whatever MNIST does. `attack-fake-uvx.sh` tampers with this task's native runner. The new `attack-forge-observation.sh` takes over the adapter: it writes a forged envelope with a claim through `/proc/<pid>/fd/1` and kills the adapter. It ends `failed` (`case_error`), not `invalid`. Sound.
8. Divergences. `qualification.json` reports no problems. All ten SecureBench runs are admitted, rejudged and not dirty, and all record the digest above. The framework commits differ (`38bffebb`, `512bf8b4`, `9ea5d7ab`), but `git diff` shows no change between them in `securebench/`, `securebench_relay_proxy/`, `securebench_utility/`, `pyproject.toml` or `uv.lock`. Native results are reused for the unchanged candidates (`native_cached`), and both new candidates ran natively. The reference passes both graders. The null candidate and all five mutants fail both. `attack-forge-observation` fails both. The one divergence is `attack-fake-uvx`, which got native 1.0 and SecureBench `failed`. The explanation holds: natively it replaces `uvx` through the `curl | sh` install, and here it writes nothing to `/app`, so `weights-file` fails. The note on the earlier flaky native MNIST download agrees with upstream's test, which downloads MNIST at grading time. Sound.
9. Inventory. `converted` is right: no exclusion reason applies, because the Evaluation needs no network, GPU or host action, and the pack is small. The current `inventory.tsv` note is stale. It describes the removed seeded case, `attack-filename-lookup` and a lesson code. The coordinator should replace it with the note proposed above.

Upstream assertions. All six tests map to checks, as the table above shows. No assertion is dropped. Every fidelity change has a label and a reason.

Round 1 findings:
- No mutant reached the adapter's output bound or UTF-8 check: fixed by `mutant-fixed-size-output.sh` (point 7).
- Processes left running by the agent were not recorded: fixed in fidelity change 5.

Findings:
- None.

Verdict: approved
