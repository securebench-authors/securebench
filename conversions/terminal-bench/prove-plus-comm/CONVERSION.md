# prove-plus-comm

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/prove-plus-comm

## How the pack grades

The baseline is upstream's `alexgshaw/prove-plus-comm:20251031`, pinned by digest. The agent works in `/workspace`, which holds the partial proof `plus_comm.v`. The scope is `/workspace` alone: both deliverables (`plus_comm.v` and `plus_comm.vo`) live there, and nothing under it is loaded by a test runner (upstream's tests live in `/tests`, and `coqc` reads no configuration from its working directory). The baseline has no symlinks under `/workspace`.

Upstream's `tests/test_outputs.py` has four tests, run in file order in the same container, all of which must pass. They map to three checks:

| Upstream test | Check | What is compared |
|---|---|---|
| `test_proof_file_exists`, `test_proof_contents` | artifact `proof-source` | `/workspace/plus_comm.v` read from the candidate as UTF-8 text; it must contain `n + m = m + n`, `Proof.` and `Qed.`, and must not contain `admit`, compared with Python's `in` exactly as upstream does (case-sensitive, comments included, no whitespace normalization) |
| `test_compiled_proof_exists` | artifact `compiled-proof` | `/workspace/plus_comm.vo` must exist in the candidate; its content is not judged, as upstream only calls `os.path.exists` |
| `test_compiled_proof_content` | protocol `compile`, one case | the adapter runs the baseline's `/usr/bin/coqc plus_comm.v` in `/workspace` and reports its exit status and whether its output is strict UTF-8; the Oracle requires exit status 0 and UTF-8 output |

The substrings and the expected exit status are in `task/hidden/expected.json`; `task/hidden/oracle.py` holds only the comparisons.

The `compiled-proof` check reads the candidate's own `plus_comm.vo`, because upstream checks its existence before compiling. Checking it after the Evaluation's `coqc` run would always succeed, since that run creates the file.

### What the candidate controls in the compile check

`/usr/bin/coqc` is in the baseline image, outside the scope, so the candidate cannot replace the binary (`attack-fake-coqc` does so in the Agent environment; the change is not captured). The adapter is standard-library Python started with `-I`, so modules planted in `/workspace` are not imported (`attack-shadow-adapter`), and it calls `coqc` by absolute path with a fixed environment, so a `coqc` planted in `/workspace` is never run.

The candidate can still run arbitrary native code inside `coqc`, and so inside the Evaluation, exactly as it can under the native grader. `Declare ML Module` in its legacy `"file:plugin"` form dynlinks a `.cmxs` from `/workspace` without any `-I` flag, and the baseline ships `ocamlfind` and `ocamlopt` to build one. We checked this in the baseline: a `plus_comm.v` holding `Declare ML Module "evil:evil".` and a wrong proof, with `evil.cmxs` built from `let () = exit 0`, makes `coqc` exit 0. (`coqc` also loads `.vo` files from `/workspace` with OCaml's unchecked unmarshalling, a second route to the same place.)

This gains nothing beyond public values. The only things the candidate can forge this way are `coqc`'s exit status and its output, and what the Oracle requires of them (exit status 0, UTF-8 output) is public in upstream's test. A non-proof already reaches the same verdict without native code (see the limitation below), and the Evaluation holds no hidden material: the challenge is the file name and `evaluation/` holds only the adapter and schemas. The text checks read the candidate's files directly, so no code the candidate runs can change them. Under the brief, forging only publicly known values is out of SecureBench's scope, like hardcoding, so there is no attack candidate for this route.

## Fidelity changes

- **Allowed domains (stricter).** Upstream sets `allow_internet = true`; the pack allows no domain. The agent cannot install anything from the network. The task needs nothing beyond the `coqc` in the image, and the reference uses no network.
- **Scope (stricter).** Natively, `coqc` runs in the agent's own container, so every change the agent made anywhere (to `/usr/bin/coqc`, Coq's standard library under `/usr/lib/ocaml/coq`, installed packages) takes part in grading. SecureBench keeps only `/workspace` and compiles against the baseline's tools and library. A candidate that only works because of changes outside `/workspace` passes natively and fails here; `attack-fake-coqc` is the example. Both deliverables are in `/workspace`, so every honest solution is covered.
- **Candidate script shell (equivalent).** `reference.sh` is upstream `solution/solve.sh` with `#!/bin/sh` instead of `#!/bin/bash` and a `cd /workspace` added. The script uses no bash feature, and both graders run it with `sh`.
- **Reading `plus_comm.v` (stricter, edge cases only).** Upstream reads the file with Python's `open(..., "r")`, which decodes UTF-8 in the test container (Python 3.13 under the C locale runs in UTF-8 mode) and translates newlines. The artifact check uses SecureBench's text parser, which also requires strict UTF-8 and keeps `\r`; the substrings contain no line breaks, so newline handling cannot change a verdict. Two differences remain: a file that starts with a UTF-8 byte-order mark is rejected here but accepted upstream (Python keeps the mark as a character, and `coqc` accepts it), and a file above 16 MiB is rejected here. Neither occurs in a plausible solution: the agent edits a 277-byte file in a container whose editors do not write byte-order marks.
- **Existence of `plus_comm.vo` (equivalent).** Upstream's `os.path.exists` accepts a regular file or a directory. The Oracle accepts every file status except `absent` (`present`, `unparsable` for the binary `.vo`, `too_large`, `not_regular` for a directory).
- **Symlinks (stricter, edge case only).** The scope does not permit symlinks, so a candidate that creates one under `/workspace` fails capture, while upstream follows symlinks. No plausible solution creates a symlink to complete a proof.
- **coqc output decoding (equivalent).** Upstream runs `coqc` with `subprocess.run(..., capture_output=True, text=True)`, which raises, failing the test, when `coqc`'s output is not valid UTF-8. The adapter reports this as `output_utf8`, and the Oracle requires it (`mutant-nonutf8-output` covers it). The adapter also returns the last 64 lines of output, each cut to 1,024 UTF-8 bytes, for diagnostics only. `max_observation_bytes` is 524,288 so that this tail can never exceed the bound: JSON escapes a control character as six bytes, so the tail is at most 64 × 1,024 × 6 = 393,216 bytes plus quotes, commas and the envelope. A correct proof whose output is long or full of control characters therefore passes, as it does upstream.
- **coqc environment (equivalent).** The adapter runs `coqc` with the baseline image's `PATH` and `HOME=/root` and no standard input. Upstream inherits the test runner's environment; `coqc` reads no variable that the runner sets.
- **Timeout (equivalent).** The `compile` case has 900 seconds, upstream's whole verifier timeout. The reference compiles in about one second.

## Limitation: upstream's tests accept proofs that are not proofs

We convert upstream's assertions exactly, so we keep their weaknesses. The text checks are substring tests over the whole file, comments included, and the compile check only needs `coqc` to succeed. So both graders accept, for example:

- a proof that ends in `Abort.` followed by `(* Qed. *)` (we ran this through SecureBench: `passed`);
- a proof that uses an `Axiom` stating the theorem;
- a proof that ends in `Admitted.` with `Qed.` in a comment (`Admitted` does not contain the lowercase `admit`).

None of these tamper with grading; they are wrong solutions that upstream's specification accepts. Adding a check such as `Print Assumptions` would be stricter than upstream.

## Candidates

- `reference.sh`: upstream's solution.
- `null.sh`: changes nothing.
- `mutant-admit-comment.sh`: correct compiled proof with "admit" in a comment; aimed at the substring check (comments included).
- `mutant-no-vo.sh`: correct proof never compiled; aimed at the existence check reading the candidate rather than the Evaluation after its own compile.
- `mutant-stale-vo.sh`: an incomplete proof compiled with `Admitted.`, then switched to `Qed.`; the text checks pass and a `.vo` exists, so only the `compile` check rejects it.
- `mutant-latin1-comment.sh`: correct compiled proof with a Latin-1 byte in a comment; `coqc` accepts it, upstream's UTF-8 read rejects it; aimed at the text decoding.
- `mutant-nonutf8-output.sh`: correct compiled proof in a UTF-8 `plus_comm.v` that `Load`s a helper `notes.v` with a Latin-1 byte in a warning name; `coqc` exits 0 but prints the raw byte, so upstream's `text=True` raises; aimed at the adapter's `output_utf8` report.
- `attack-fake-coqc.sh`: a wrong proof, an empty `plus_comm.vo`, and `/usr/bin/coqc` replaced by a script that exits 0.
- `attack-shadow-adapter.sh`: a wrong proof plus Python modules (`sitecustomize`, `json`, `subprocess`, `encodings`, ...) and a `coqc` in `/workspace` that print a forged successful observation.

## Divergences from native
- `attack-fake-coqc`: native reward 1.0, SecureBench `failed` (class `oracle`, `coqc` exit status 1). Natively the agent and the tests share one container, so the agent's replacement `/usr/bin/coqc` answers upstream's `test_compiled_proof_content` with exit 0, and the empty `plus_comm.vo` and admit-free text pass the other tests. In SecureBench `/usr/bin` is outside the scope, the replacement is not captured, and the baseline's real `coqc` rejects the proof. SecureBench is right: the proof does not compile.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-26 (second review, after the converter addressed the first review's five findings)

1. Instructions: `cmp` of upstream `instruction.md` and `task/instructions.md` again finds no difference.
2. Scope: unchanged. One root, `/workspace`, `symlinks = false`. In the baseline, `/workspace` holds only `plus_comm.v` and has no symlinks, and no file in it is convention-loaded. The difference from native grading (native uses the whole container) is now listed as "Scope (stricter)", with a correct reason.
3. Expected values: `public/`, `evaluation/` and `hidden/` are unchanged apart from `task.toml`. The baseline's `/workspace` holds only upstream's partial proof. The expected values are upstream test literals. `allowed_domains` is empty, and the change from upstream's `allow_internet = true` is now listed as "Allowed domains (stricter)". No leak.
4. Challenges: unchanged. The only challenge is `{"source": "plus_comm.v"}`, fixed by an enum.
5. Cases: unchanged. One `compile` case for upstream's one compile test, no added cases, seed unused.
6. Oracle: `oracle.py`, `expected.json`, the adapter and the schemas are unchanged since the first review. `judge` holds only comparisons, checks both required fields with exact types, fails closed, ignores `output_tail`, and matches upstream's UTF-8 read and `in` tests. `max_observation_bytes` is now 524,288. The adapter's worst case is 64 lines × 1,024 bytes × 6 bytes per escaped byte = 393,216 bytes plus overhead, so the bound holds. (U+FFFD from the `replace` decode is 3 UTF-8 bytes escaped to 6, so it stays under the 6× worst case.) I reran my control-character candidate, upstream's correct proof preceded by a `Set Warnings` name made of 70 lines of `\x01`, against the new pack. It now `passed`, as upstream does. The section "What the candidate controls in the compile check" now states correctly that Coq source can dynlink a `.cmxs` from `/workspace` (`Declare ML Module "file:plugin"`) and run native code inside `coqc`, as natively, and explains why this forges only public values: exit status 0 and UTF-8 output, which the `Abort.` limitation already reaches legitimately. It also notes that the Evaluation holds no hidden material and that the artifact checks read the candidate's files directly. I agree with this argument. No regression tests run by outcome.
7. Candidates: `reference.sh` is upstream's `solve.sh` plus `cd /workspace` and a `sh` shebang, and its comment now says so. `null.sh` changes nothing. There are five mutants. `mutant-no-spaces` was replaced by `mutant-nonutf8-output`, which keeps `plus_comm.v` UTF-8 and `Load`s a helper whose warning name holds byte 0xE9. Every text check passes for it and `.vo` exists, so its SecureBench `failed` (class `oracle`) can only come from `output_utf8` on the `compile` case. Native gives 0.0, so this mutant covers the adapter-derived value. The plain substring test remains covered by `mutant-admit-comment`. The other mutants are unchanged and agree between the graders. Both attacks are unchanged and get `failed`.
8. Divergences: the only divergence remains `attack-fake-coqc` (native 1.0, SecureBench `failed`), explained correctly: native grading shares the agent's container, where `/usr/bin/coqc` was replaced, and SecureBench is right. The new `qualification.json` reports no problems. Every SecureBench run records the pack digest `sha256:b5b73820ffb3ee1ea6dce56ca678fc09cd4483df7ad59efa94a893f4a739b233`, which matches `securebench validate`, with a clean framework commit and rejudged verdicts. The reference and the new mutant ran natively again. The other native results are cached on unchanged scripts.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. The row should be `terminal-bench	prove-plus-comm	converted	-`. No exclusion reason applies.

Upstream assertions: `test_proof_file_exists` maps to `proof-source` (status `present`). `test_compiled_proof_exists` maps to `compiled-proof`. The four assertions of `test_proof_contents` map to `proof-source`. `returncode == 0` in `test_compiled_proof_content` maps to `compile`, with the strict decode of `text=True` as `output_utf8`. None is dropped.

First review's findings, rechecked:
- Response bound: fixed (`task/task.toml:58`, 524288; confirmed by rerun).
- False claim about native code in `coqc`: fixed (section rewritten, argument holds).
- Missing fidelity bullets for domains and scope: fixed, both labelled stricter with reasons.
- No mutant for `output_utf8`: fixed (`mutant-nonutf8-output`).
- `reference.sh` comment: fixed.

Findings:
- None.

Verdict: approved
