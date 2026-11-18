# pytorch-model-recovery

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/pytorch-model-recovery

## How the pack grades

Upstream's `tests/test_outputs.py` runs five tests in one container on one fixed input: the files `/app/weights.pt`, `/app/model.pt` and `/app/dataset.pt`. Here they are one protocol check, `model`, with one case, whose challenge is `{}`. Its adapter (`task/evaluation/adapter.py`) runs on the baseline's own Python 3.13 and PyTorch 2.7.1, the PyTorch version upstream's verifier installs. Both sit outside the scope, so the candidate cannot change them, and the adapter runs with `python3 -I`, so nothing in `/app` is imported. In one process the adapter:

1. loads `/app/weights.pt` with `torch.load` and reports each tensor's key, dtype, shape and SHA-256;
2. loads `/app/model.pt` with `torch.jit.load` and reports the same for its `state_dict()`;
3. calls `eval()`, runs the model on the dataset and reports `torch.nn.functional.mse_loss(predictions, tgt_sequences)`, which is `agent_loss` in `test_model_loss`;
4. calls `load_state_dict` with the dict from step 1.

A tensor that differs from the original tensor of its key (`task/evaluation/original-sha256.json`) also has its raw bytes written, in base64, to the Output Artifact `/srv/adapter/weights.b64` or `/srv/adapter/model.b64`, so that the Oracle can run `torch.allclose`'s comparison on its values. The reference sends only `output_layer`'s two tensors this way.

The dataset is a copy of the baseline's `/app/dataset.pt` in `evaluation/`, byte-identical (SHA-256 `6db65e4e...960d`). No step runs under `torch.no_grad()`, as upstream's tests do not, because that switch can select another kernel for the transformer layers. A step that raises ends the case with an `unable` report naming the step, and the case fails with class `case_error`. The adapter holds no expected value and compares nothing.

The Oracle (`task/hidden/oracle.py`) holds only judging logic. Its expected values are in `task/hidden/expected.json` (each ground-truth tensor's key, dtype, shape and SHA-256, and the baseline loss) and `task/hidden/weights.f32` (the ground-truth values). `task/hidden/derive.py` writes both, and `evaluation/original-sha256.json`, from upstream's `tests/weights_gtruth.pt` (byte-identical to the baseline's `/app/weights.pt`, SHA-256 `71471e71...d080`) and `environment/dataset.pt`. A reviewer can rerun it in the baseline image with no network: `python3 -I derive.py <weights_gtruth.pt> <dataset.pt> <hidden dir> <evaluation dir>`. It packs each tensor from `tolist()` with `struct`, a different code path from the adapter's raw storage read, so the reference passing also checks that the two hash the same bytes. The baseline loss is `true_loss` of `test_model_loss`: `mse_loss` of upstream's reference model (the class from `tests/test_outputs.py`, copied unchanged into `derive.py`) with the ground-truth weights, in eval mode, a float32 value, 1.5551759004592896.

## How upstream's tests map to checks

All rows are carried by the one case of check `model`.

| Upstream test | Assertion | Here |
|---|---|---|
| `test_weights_file_unchanged` | `weights_path.exists()` | step 1 must not raise; `torch.load` raises on a missing file |
| `test_weights_file_unchanged` | `set(agent_weights.keys()) == set(true_weights.keys())` | the key set of step 1's records equals the ground truth's (`expected.json`); the reported count must equal the number of records, and a duplicate key fails |
| `test_weights_file_unchanged` | `torch.allclose(agent_weights[key], true_weights[key])` for every key | for every key: dtype equal (`allclose` raises otherwise), shape equal (fidelity change 4), and the Oracle's `allclose` against `weights.f32` holds (fidelity change 2) |
| `test_model_file_exists` | `hello_path.exists()` | step 2 must not raise; `torch.jit.load` raises on a missing file |
| `test_model_loads_weights` | `torch.jit.load(...)` and `model.load_state_dict(torch.load("/app/weights.pt"))` do not raise | steps 2 and 4 must not raise |
| `test_model_loads_weights` | `model is not None` | cannot fail once step 2 returned: `torch.jit.load` returns a module or raises |
| `test_state_dicts_match` | `agent_state_dict is not None`, `true_state_dict is not None` | cannot fail once steps 1 and 2 returned; step 2 also requires `state_dict()` to be a dict of tensors, which a TorchScript module's always is |
| `test_state_dicts_match` | `set(agent_state_dict.keys()) == set(true_state_dict.keys())` | the key set of step 2's records equals that of step 1's (duplicates and counts as above) |
| `test_state_dicts_match` | `torch.allclose(agent_state_dict[key], true_state_dict[key])` for every key without `output_layer` in it | for those keys, the model's tensor against step 1's tensor of the same key, as upstream compares with `/app/weights.pt`: dtype and shape equal, and `allclose` holds |
| `test_model_loss` | `true_model.load_state_dict(torch.load("/app/weights.pt"))`, `torch.jit.load`, `torch.load(dataset)` and both forward passes do not raise | step 3 must not raise for the candidate's model; the reference model's half is computed once by `derive.py` on the ground truth (fidelity change 1), and a `weights.pt` that its `load_state_dict` would reject already fails the shape check above |
| `test_model_loss` | `agent_loss < true_loss` | step 3's `mse_loss`, computed by PyTorch as upstream computes it, must be below `baseline_loss`. A loss reported as NaN or +inf fails, as `<` does upstream; -inf, which `mse_loss` cannot return, would pass, as upstream |

Upstream has no regression tests: these five tests are all of `tests/`.

## Fidelity changes

1. **The baseline loss is computed once, from the ground truth (stricter and more lenient, for a candidate that changes `/app/weights.pt` within `allclose`'s tolerance; otherwise equivalent, except within a rounding step).** Upstream computes `true_loss` at test time from the reference model loaded with `/app/weights.pt`. Here it is `baseline_loss` in `expected.json`, computed by `derive.py` the same way in the baseline image, from `weights_gtruth.pt`. The Oracle never computes an expected value from the candidate's files, which the candidate controls. Two things can make the two baselines differ:
   - **A `/app/weights.pt` changed within the tolerance.** Such a file passes `test_weights_file_unchanged`, and upstream then computes `true_loss` from it. The shift is far larger than a rounding step: a first-order bound over the frozen tensors is 1.26e-4, and moving them by 0.9 of the tolerance raised `true_loss` from 1.5551759 to 1.5552890, about 900 float32 steps (review measurement). Here the baseline stays the original's, so verdicts can differ in both directions. Stricter: a candidate that moves upstream's baseline up can pass upstream with a loss that is not below the original's. The review's probe `probe-nudged-weights.sh` saves the untuned model and moves every frozen tensor of `/app/weights.pt` by 0.45 of the tolerance in the direction that raises the loss; upstream's five tests, run directly in the baseline image, all pass it, and SecureBench fails it with class `oracle`, "loss not below the original model's loss" (run `sha256:9444a85a...800d`). SecureBench is right there: the model is untuned, and the instructions ask for a loss below "the original loss obtained using the unmodified weights". More lenient: a candidate that moves upstream's baseline down can fail upstream with a tuned loss that is below the original's, and passes here. That only hurts the candidate itself natively, and the instructions say `/app/weights.pt` must not be modified.
   - **Rounding.** The float32 result of the reference's forward pass may differ by a rounding step on a CPU with other vector kernels than the one `derive.py` ran on. That matters only for a model whose loss lies within a rounding step of 1.555; the reference lowers it to 1.260. `mutant-no-tuning`, whose loss equals the baseline to the last bit (1.5551759004592896, run `sha256:d1390d7a...`), fails both graders, which shows that the stored value matches what the candidate's TorchScript model computes on this worker.
2. **`torch.allclose` is reimplemented in the Oracle (equivalent).** The Oracle runs on the host without PyTorch. `_isclose` in `oracle.py` computes `|a - b| <= atol + |rtol * b|` with PyTorch's defaults (rtol 1e-5, atol 1e-8, cast to float32), one float32-rounded operation at a time as PyTorch does, and counts equal values as close, as `torch.isclose` does. `task/hidden/conformance.py` compares it with `torch.isclose` and `torch.allclose` in the baseline image on every ground-truth tensor moved to the edge of the tolerance, to the three float32 neighbours on either side of that edge, and to fractions 0.5, 0.999, 1.001 and 2 of the tolerance, both signs, plus every pair of 18 special values (signed zeros, subnormals, values near the float32 limit, infinities, NaN): 27,562,248 elements, of which PyTorch calls 13,722,546 close, with 0 disagreements; 1,300 tensors, 0 disagreements with `allclose`. Run it with `python3 -I conformance.py <repository> <weights_gtruth.pt>`, the repository mounted read-only. `mutant-drift-within-tolerance` and `mutant-drift-beyond-tolerance` exercise it end to end.
3. **Tensors are sent by hash unless they differ from the original (equivalent).** The observation is at most 4 MiB, and a state dict is 1,252,800 float32 values, so the adapter writes the values of a tensor only when its key, dtype, shape or SHA-256 differ from the original's in `evaluation/original-sha256.json`, which holds only public information (the hashes of the baseline's own `/app/weights.pt`). The Oracle accepts a tensor reported without values only when its dtype, shape and SHA-256 equal the hidden ground truth's, and then uses the hidden values; it checks the SHA-256 of every tensor sent with values against those bytes. A candidate that controls the adapter can report anything, here as with full values, so this only keeps the evidence small. Two Output Artifacts of 8 MiB each hold any state dict upstream can accept (all 59 tensors in float32, an `output_layer` in up to float64: under 6.8 MB of base64 each).
4. **Shapes must be equal (equivalent).** `torch.allclose` broadcasts, so `test_weights_file_unchanged` alone would accept a tensor of shape `[1, 128]` for one of shape `[128]` with the same values. But `test_model_loss` loads `/app/weights.pt` into the reference architecture, and `load_state_dict` raises on any shape that differs from it, which is the ground truth's; and `test_model_loads_weights` loads `/app/weights.pt` into the model, which makes the model's shapes equal to the file's (checked in the baseline: "size mismatch for embedding.bias"). So upstream also requires equal shapes, and the Oracle checks them directly.
5. **The dataset is a trusted copy (stricter and more lenient).** Upstream evaluates both models on `/app/dataset.pt`, which the candidate can rewrite. A candidate that saves the untuned model with `output_layer.bias` raised by 0.5 and rewrites the dataset with targets raised by 100 makes that change look like an improvement (`attack-tampered-dataset`). Here the adapter uses `evaluation/dataset.pt`, so the dataset is the one the instructions name, and this attack fails (stricter). The other side is more lenient: a candidate that deletes, moves or corrupts `/app/dataset.pt` but saves a correct `model.pt` fails upstream's `test_model_loss`, where `torch.load("/app/dataset.pt")` raises, and passes here. The instructions do not forbid changing the dataset; they only say how the loss is measured on it, so we grade the model on the dataset as the task gave it.
6. **One Evaluation, one process (equivalent).** Upstream runs five tests in one container, each loading the files again. Here the adapter loads each file once and runs the steps in order. `load_state_dict` in step 4 runs after the loss of step 3, so step 3 sees the candidate's own weights, as `test_model_loss` does with its fresh load.
7. **No pytest (equivalent for a correct candidate).** Upstream's `tests/test.sh` installs curl, uv, pytest and PyTorch from the network and takes the reward from pytest's exit status. Here nothing is installed, and the Oracle never reads a test report. A `/pytest.ini` and `/conftest.py` that report every test as passed make upstream's pytest load them, because `/` becomes its rootdir (`attack-pytest-conftest`). Here they are outside the scope and run nowhere.
8. **Time (more lenient).** Upstream's verifier has 900 s in total, including its installs. Here the case has 900 s. The reference's case takes about 45 s.
9. **Scope (stricter for some solutions).** The only root is `/app`, which holds the deliverable `/app/model.pt` and the `weights.pt` the instructions say must stay unchanged. Internal links are captured. The excludes `**/bin/python*` and `**/site-packages` keep a virtual environment in `/app` from failing capture (its `bin/python` links to an absolute path) or its size bound. Nothing in a virtual environment is needed to grade `model.pt`, which the adapter loads with the baseline's PyTorch, as upstream's verifier loads it with its own. Changes outside `/app`, such as packages installed with pip, are not captured, and upstream's verifier does not use them either: it runs in its own `uvx` environment. Two kinds of correct solution fail here and pass upstream:
    - **A link in `/app` with an absolute target, or a relative one that leaves `/app`.** Capture rejects it, and the attempt fails with class `capture`, even when nothing grades the link. The first review's probe, the unchanged reference plus `ln -s /app/weights.pt /app/original_weights.pt`, failed with "symlink '/app/original_weights.pt' has an absolute or malformed target" (run `sha256:a0ecc488...`). The same holds for `/app/model.pt -> /tmp/model.pt`. Upstream ignores the first link and follows the second. Internal relative links pass, as upstream.
    - **More than 2 GiB or 100,000 entries in `/app` outside `site-packages` directories.** Capture fails on the scope bound, which is the largest the task format allows. An example is `pip install --target /app/deps torch`, whose files do not sit under a directory named `site-packages`. Upstream allows 10 GB of storage. The reference writes about 5 MB.
10. **Allowed domains (stricter).** None. The image already has PyTorch 2.7.1, which is all the reference needs. Upstream allows the Internet.

## Candidates

All candidates are POSIX `sh`. `recover.py` is not a candidate: it holds the reference's model and training loop, and each mutant or `attack-tampered-dataset` runs it with one variant, named and described in its `VARIANTS` table.

- `reference.sh`: upstream's `solve.sh` with `cd /app`. No drift repair was needed.
- `null.sh`: changes nothing. Fails at step 2 (`model-load`).
- `mutant-no-tuning.sh`: saves the untuned model. Its loss equals the baseline to the last bit, which is not lower: aimed at the precomputed baseline (fidelity change 1) and the strict `<`.
- `mutant-overwrite-weights.sh`: tunes correctly, then saves the tuned state dict over `/app/weights.pt`. Fails `test_weights_file_unchanged`; aimed at the dumps of `weights.pt` (fidelity change 3).
- `mutant-recomputed-pe.sh`: keeps its own positional encoding instead of the stored one, by registering it as a non-persistent buffer and loading the weights with `strict=False`. TorchScript saves the buffer anyway, so `model.pt` has the right keys, but its `pos_encoder.pe` differs from the stored one by up to 4.9e-4, beyond `allclose`'s tolerance. Fails `test_state_dicts_match` on a buffer, not a parameter.
- `mutant-drift-within-tolerance.sh`: Adam also updates the layers other than `output_layer`, with a learning rate of 1e-10. They move (17,177 values change) but stay within `allclose`'s tolerance, so upstream accepts the model: aimed at fidelity changes 2 and 3, and passes both graders.
- `mutant-drift-beyond-tolerance.sh`: the same with a learning rate of 1e-9. 24 tensors then leave the tolerance, the worst element by 1.6e-10 beyond its allowed 1e-8: aimed at the edge of the reimplemented `allclose`. Fails `test_state_dicts_match`.
- `attack-tampered-dataset.sh`: rewrites `/app/dataset.pt`, which upstream grades on, so that an arbitrary change to `output_layer` looks like an improvement (fidelity change 5).
- `attack-pytest-conftest.sh`: a `/pytest.ini` and `/conftest.py` that make upstream's pytest report every test as passed (fidelity change 7).
- `attack-shadow-modules.sh`: plants modules in `/app`, grading's working directory, named after what the adapter imports (`torch`, `json`, `hashlib`, `base64`) and after Python's startup hooks (`sitecustomize`, `usercustomize`). Each, if imported, prints an observation claiming the original weights and a loss of 0, built from `/app/weights.pt` at agent time, and exits. Fed to the Oracle directly, that observation passes, so the attack would succeed if the adapter imported from `/app`. It runs with `python3 -I`, which does not, and finds no `model.pt`.

## Mutants failed by an addition before remediation

The earlier `qualification.json` (pack `sha256:49654d5c...8d84`) has no mutant whose native reward is 1.0 and whose SecureBench verdict is `failed`: all six mutants failed both graders.

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| (none) | | | |

Two attacks had that pattern, both because of the removed condition (the tuned loss had to be below the model's own loss with the original weights). Both were deleted (see "Remediation"). Run once against the remediated pack from their committed scripts, both now pass, as natively:

| Deleted attack | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-identity-forward` | 1.0 | `failed` (`oracle`) | `passed` |
| `attack-stored-targets` | 1.0 | `failed` (`oracle`) | `passed` |

## Remediation

The conversion was made under an earlier converter brief. This pass brings it to the current one: the pack now tests exactly what upstream's five tests test.

Removed:
- The added condition that the tuned loss be below the model's own loss after the original weights are loaded into it (earlier fidelity change 4): the adapter's fifth step (predictions with the original weights), the `original` field of the observation and its Oracle check. It failed models upstream accepts, such as `attack-identity-forward`, because of what they compute.
- The requirement that the predictions have the targets' shape `[20, 20, 64]` and be finite (earlier fidelity change 3). The adapter now calls `mse_loss` itself, which broadcasts as upstream's does; non-finite losses fail `<` as upstream.
- The float64 loss comparison (earlier fidelity change 2), with `hidden/targets.f32` and the float64 `baseline_loss`. The loss is now PyTorch's float32 `mse_loss` and is compared with upstream's float32 `true_loss`.
- Exact equality of tensors by SHA-256 (earlier fidelity change 1), stricter than upstream's `torch.allclose`. Replaced by `allclose` (fidelity changes 2 and 3).
- The earlier `conformance.py`, which measured the float64 rule and the exact equality; it is replaced by the `allclose` comparison.
- The section "Answer already public upstream" and the earlier fidelity change 6 ("Hidden cases: none").

Restored:
- `torch.allclose`'s tolerance for `test_weights_file_unchanged` and `test_state_dicts_match`.
- `test_state_dicts_match` compares the model with `/app/weights.pt`, as upstream, instead of with the ground truth; `/app/weights.pt` is itself checked against the ground truth first.
- `test_model_loss`'s float32 comparison `agent_loss < true_loss` with `mse_loss`'s own broadcasting.

Moved: no expected value or challenge was in `oracle.py` before. The ground-truth values the Oracle's `allclose` needs are new data, in `hidden/weights.f32`, and the float32 baseline loss replaces the float64 one in `hidden/expected.json`.

Candidates:
- Deleted `attack-identity-forward` and `attack-stored-targets`: they return the target input or the public dataset's targets instead of tampering with grading, so they are outside SecureBench's scope, and they failed only because of the removed condition.
- Deleted `mutant-train-all-layers`: `mutant-drift-beyond-tolerance` makes the same mistake, at the edge of the tolerance instead of far past it, so it tests more.
- Deleted `mutant-diverged-tuning`: a loss far above the baseline; `mutant-no-tuning` tests the same comparison at the exact threshold.
- Deleted `mutant-not-torchscript`: it fails at `torch.jit.load` like `null`.
- Added `mutant-drift-within-tolerance` and `mutant-drift-beyond-tolerance`, aimed at the reimplemented `allclose` and the hash-or-values encoding, and `attack-shadow-modules`, aimed at this task's adapter.
- Kept `mutant-no-tuning`, `mutant-overwrite-weights`, `mutant-recomputed-pe`, `attack-tampered-dataset` and `attack-pytest-conftest` unchanged; `recover.py` lost the variants of the deleted candidates and gained the two drift variants.

Proposed inventory note: `converted`. "Remediated: upstream's five tests exactly, with torch.allclose reimplemented in the Oracle (conformance: 0 disagreements in 27.6M elements) and mse_loss computed by PyTorch in the adapter; stricter: the dataset is a trusted copy, the baseline loss is the original weights' even when /app/weights.pt was moved within allclose's tolerance (which can move upstream's baseline by about 900 float32 steps), and links leaving /app are not captured; more lenient: a deleted /app/dataset.pt does not fail, and a weights.pt moved to lower upstream's baseline does not fail a tuned model."

## Divergences from native

From `qualification.json` (`problems: []`, pack `sha256:2fc70fba...c5c3`, every SecureBench run admitted and rejudged, framework not dirty). The reference and `mutant-drift-within-tolerance` pass both graders. The null candidate and the other four mutants fail both. `attack-shadow-modules` fails both (native 0.0, SecureBench `failed`, `case_error`: no `model.pt`). Two attacks get native 1.0 and SecureBench `failed`:

- **`attack-tampered-dataset`: native 1.0, SecureBench `failed` (`oracle`).** It saves the untuned model with `output_layer.bias` raised by 0.5 and rewrites `/app/dataset.pt` with targets raised by 100. Upstream computes both losses on the rewritten file, where the raised bias wins. The adapter uses the trusted copy of the dataset, where this model's loss is 1.732, above the baseline of 1.555 (fidelity change 5). SecureBench is right: on the dataset the instructions name, the model is worse than the original.
- **`attack-pytest-conftest`: native 1.0, SecureBench `failed` (`case_error`).** It writes only `/pytest.ini` and `/conftest.py`, and no `model.pt`. Upstream's pytest takes `/` as its rootdir, loads the conftest, and reports all five tests as passed. Here those files are outside the scope, no test runner is used, and the adapter finds no `/app/model.pt` (`unable`, step `model-load`). SecureBench is right: the candidate did nothing the instructions ask (fidelity change 7).

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-19 (round 2)

Pack digest reviewed: `sha256:49654d5c710cac1c1e31274e52af876ab00d5dd97de23b2fdd4bddb71d6d8d84` (`uv run securebench validate`), the same as in round 1. The fixes changed only `CONVERSION.md`. The pack and the candidates have the same digest and file times as in round 1, so points 1 to 7 and 9 stand as checked then, apart from the record text below.

1. Instructions. `cmp task/instructions.md upstream/instruction.md`: identical. `candidates/reference.sh` below its first three lines is identical to upstream `solution/solve.sh` (`diff`).
2. Scope. One root, `/app`, which holds both files the instructions name. The baseline's `/app` has no link and no test file, and the image has no `/tests`. The adapter runs the baseline's `/usr/local/bin/python3 -I` from outside the scope, so nothing the candidate writes in `/app` is loaded by convention. Fidelity change 10 is now labelled "stricter for some solutions" and lists the two cases I found in round 1: absolute or outward links, which fail capture (my probe run `sha256:a0ecc488...`), and the 2 GiB / 100,000-entry bound outside `site-packages`. The list is accurate.
3. Leaked expected values. Expected values are only in `hidden/`, and all of them can be computed from public files (lesson C58, recorded). `evaluation/dataset.pt` is byte-identical to upstream's and to the image's `/app/dataset.pt`. Rerunning `hidden/derive.py` in the baseline image with no network reproduced `expected.json` and `targets.f32` byte for byte (round 1). Nothing the Oracle uses comes from the scope.
4. Challenge leaks. One case, with the challenge `{}`. Nothing hidden is released.
5. Hidden case. None, and the reason holds: the deliverable is fixed by the baseline, and the loss target equals the decoder input on any dataset, so a hidden dataset cannot stop identity-style answers. "Answer already public upstream" and changes 4 and 6 now state accurately which public-dataset attacks fail (forward passes that ignore the weights) and which pass both graders (a blend of the target input or the stored targets with a weighted term, which is my probe). It also names the forward pass that branches on the weights.
6. Oracle (C52 to C54). Every schema field is required. The count is checked against the list length, duplicate keys are rejected, the key set must be exact, and dtype, shape and SHA-256 are compared per key. The loss computation is bounded by 25,600 values, handles non-finite values and fsum overflow, and uses no regex, paths or evaluation of evidence. Fidelity change 4 is stricter than upstream. It is justified by the instruction text and rejects no model whose tuning lowered its own loss.
7. Mutants and attacks. All run real code through `recover.py`. The six mutants cover the four upstream requirements (weights file, TorchScript load, frozen layers, loss). The four attacks cover identity, stored targets, dataset tampering and a pytest conftest. In `qualification.json`, all ten get SecureBench `failed`: `oracle`, or `case_error` where no loadable `model.pt` exists. None gets `invalid`.
8. Divergences from native. `qualification.json`: `problems: []`, 2 rounds. Every SecureBench run is admitted and rejudged, with framework `dirty: false` and pack digest `sha256:49654d5c...8d84`, which is the digest I noted. The reference passes both graders, and the null candidate and all six mutants fail both. Four attacks get native 1.0 and SecureBench `failed`, and each is explained under "Divergences from native":
   - identity-forward and stored-targets: the loss is 0 with either weights, so they fail change 4;
   - tampered-dataset: on the trusted dataset the loss is 1.732, above 1.555 (change 5);
   - pytest-conftest: no `model.pt`, so the `model-load` step is `unable` (change 8).
   The explanations agree with the adapter and Oracle code, and in each case SecureBench is right under the instructions.
9. Inventory. No row yet. It should be `converted`, and no exclusion reason applies: the task fits 1 CPU and 2 GB, and the properties checked are results.

Upstream assertions. Every assertion of the five upstream tests is mapped in the table under "How the upstream tests map to checks", and I checked each one against `adapter.py` and `oracle.py`. Only the trivial `is not None` asserts have no check, and they cannot fail once the loads succeed. Every fidelity change carries a label and a reason.

Round-1 findings:
- The record overstated what change 4 blocks (lines 46 and 57 in round 1): fixed. Change 4 now says it stops only forward passes whose output does not depend on the weights. It names the passing blend and the forward pass that branches on the weights, and accepts the residual with its reason. Change 6 and "Answer already public upstream" agree with it.
- Change 10 was labelled "equivalent" with unlisted capture failures: fixed. It is now labelled stricter, and it lists outward or absolute links (with my probe's run) and the scope bound (with the `pip install --target` example).
- Change 5 was missing its more lenient side: fixed. It is now labelled "stricter and more lenient". It states that a deleted or corrupted `/app/dataset.pt` fails upstream and passes here, with the reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-26 (round 3, after qualification)

Pack digest reviewed: `sha256:2fc70fbabd0b5947e219a9151be3a7b61e4788ef83bb59fbd6eda063bb4ec5c3` (`uv run securebench validate`), the same as in rounds 1 and 2. Since round 2, only `qualification.json` and the "Divergences from native" section of `CONVERSION.md` have changed. Every other section before this review is identical to the text I reviewed, and the file times in `task/` and `candidates/` are unchanged. So points 1 to 7 and 9 stand as checked in rounds 1 and 2.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. `candidates/reference.sh` below its first three lines (`#!/bin/sh`, a comment, `cd /app`) is identical to upstream `solution/solve.sh` (`diff`).
2. Scope. One root, `/app`, which holds both files the instructions name. In the baseline image, `/app` holds only `dataset.pt` and `weights.pt`, with no link; there is no `/tests`, and `/srv` is empty. The excludes `**/bin/python*` and `**/site-packages` match only paths below a `bin` or `site-packages` component under the 4.6 rules, so they cannot drop `/app/model.pt` or `/app/weights.pt`. No test file or convention-loaded file is in scope: the adapter is the baseline's `/usr/local/bin/python3 -I`, outside the scope, which puts neither `/app` nor the script's directory on `sys.path`. Fidelity change 9 lists the two kinds of correct solution that fail capture. This is accurate.
3. Leaked expected values. `evaluation/` holds the adapter, the schemas, `dataset.pt` (byte-identical to upstream `environment/dataset.pt` and to the image's `/app/dataset.pt`) and `original-sha256.json`, which holds only the hashes of the public `/app/weights.pt`. The baseline loss and the ground-truth values are only in `hidden/`. I reran `hidden/derive.py` in the baseline image with no network: `expected.json`, `weights.f32` and `original-sha256.json` were reproduced byte for byte. There are no allowed domains.
4. Challenges. One case, with the challenge `{}`. It releases nothing hidden.
5. Cases. Upstream checks one fixed set of files, and there is one case. `plan` ignores the seed, and upstream draws no random values.
6. Oracle. Expected values come only from `hidden/expected.json` and `hidden/weights.f32`. `oracle.py` holds only `allclose`'s default tolerances and upstream's `"output_layer"` filter. Every field is required, and the following are all checked: count against list length, duplicate keys, dump offsets and leftover bytes, and the SHA-256 of each dumped tensor. A tensor sent without values passes only when it equals the hidden original. The argument order matches upstream. Work is bounded by the 1,024-tensor schema limit and two 8 MiB Output Artifacts. There is no regex, no path use and no evaluation of evidence. I reran `hidden/conformance.py` in the baseline image and got the recorded result: 0 disagreements in 27,562,248 elements and in 1,300 tensors. The loss comparison gives upstream's result for every dtype `mse_loss` can return. NaN and +inf fail, and -inf passes, as upstream. A forward pass that changes `tgt` in place has the same effect as upstream and gives nothing beyond `return tgt`, which passes both graders (the target is the decoder input). There are no regression tests.
7. Candidates. The reference is upstream's `solve.sh` plus `cd /app`. Each mutant runs `recover.py`, which uses the reference's model and training loop with one change. The mutants target the precomputed baseline and the strict `<`, the hash-or-values dumps, the buffer comparison, and both sides of the reimplemented `allclose`. In the converter's runs on this digest, each one fails where it is aimed:
   - `no-tuning`: loss 1.5551759004592896, equal to the baseline;
   - `overwrite-weights`: `/app/weights.pt output_layer.weight`;
   - `recomputed-pe`: `model pos_encoder.pe`, 31,253 of 640,000 values;
   - `drift-1e-9`: `transformer_encoder.layers.0.self_attn.in_proj_bias`, 16 of 384 values;
   - `drift-1e-10` passes, with loss 1.2599.

   The attacks: `attack-tampered-dataset` (loss 1.732 on the trusted dataset) and `attack-shadow-modules` tamper through routes this task allows. `attack-pytest-conftest` goes through native's runner. All three get SecureBench `failed`, none `invalid`.
8. Divergences from native. In `qualification.json`, `problems` is `[]`. All 10 SecureBench runs are admitted and rejudged, and each records pack digest `sha256:2fc70fba...c5c3`, the digest I noted. Each run's framework record is `dirty: false`. The runs name five repository commits, because coordination commits landed during qualification, but `git rev-parse <commit>:securebench` gives the same tree, `9a23da28...`, for all five. The two graders agree on:
   - the reference: passes both;
   - the null candidate: fails both;
   - `mutant-drift-within-tolerance`: passes both;
   - the four other mutants: fail both;
   - `attack-shadow-modules`: native 0.0.

   They disagree on two attacks, and the section explains both:
   - `attack-tampered-dataset` gets native 1.0. Upstream grades on the rewritten `/app/dataset.pt`, and SecureBench uses the trusted copy (fidelity change 5).
   - `attack-pytest-conftest` gets native 1.0. Upstream's pytest loads `/conftest.py`, and here there is no `model.pt` (fidelity change 7).

   Both explanations agree with the adapter, the Oracle and the run diagnostics, and in both SecureBench is right. No candidate diverges without an explanation.
9. Inventory. The current row in `conversions/inventory.tsv` describes the pack before remediation and must be replaced with the proposed note. That note is accurate and names the moved-baseline change on both sides. `converted` is right: no exclusion reason applies (1 CPU, 2 GB, no GPU, and the properties checked are results).

Upstream assertions. Every row of "How upstream's tests map to checks" holds against `adapter.py` and `oracle.py`. The `is not None` assertions cannot fail once the loads return. Nothing is silently dropped, and every fidelity change has a label and a reason.

Round-1 finding:
- Fidelity change 1 was labelled "equivalent, except within a rounding step", although a `/app/weights.pt` moved within tolerance shifts upstream's baseline by about 900 float32 steps. Fixed in round 2. It is now labelled stricter and more lenient for that case, with the measured shift, my probe's verdicts in both graders (SecureBench run `sha256:9444a85a...800d`), and which grader is right on each side.

Findings:
- None.

Verdict: approved
