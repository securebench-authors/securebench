# mteb-retrieve

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/mteb-retrieve

## How the pack grades

The task has one deliverable, `/app/result.txt`, and one artifact check,
`result`, reads it with the `text` parser. Upstream's two tests map to it as
follows:

| Upstream assertion (`tests/test_outputs.py`) | Where it is checked |
|---|---|
| `test_result_exists`: `os.path.exists("/app/result.txt")` | the file's status must be `present`; `absent` fails |
| `test_data_matches`: `len(f.readlines()) == 1` | `readlines` in `hidden/oracle.py` recounts the lines from the full text as Python's universal-newline mode does (a line ends at `\r\n`, `\r` or `\n`) |
| `test_data_matches`: `lines[0].strip() == expected` | `lines[0].strip()` compared with `hidden/expected.json` |

The expected line, `MTEB: Massive Text Embedding Benchmark`, is upstream's
literal and lives only in `hidden/expected.json`. Upstream's two tests are
merged into one check because the second subsumes the first.

The SecureBench text parser splits lines only on `\n` and keeps `\r`, so the
Oracle does not use its `lines` field. Its own `readlines` was compared with
Python's `open(..., encoding="utf-8").readlines()` on 20,000 random strings
over `a`, `MTEB`, space, `\r`, `\n`, `\x0b`, `\x0c`, `\x85` and ` `.
Line counts and stripped lines were identical on every one. The comparison
script is not part of the pack; it ran the Oracle's `readlines` against a file
written with `newline=""` and read back in text mode.

## Fidelity changes

- Scope: root `/app` with the exclude pattern `*/*`, which drops everything
  inside any subdirectory of `/app` (top-level files are captured). Equivalent
  for grading: the only file upstream's tests read is `/app/result.txt`. The
  exclusion keeps a virtual environment (whose absolute symlinks would fail
  capture) or a downloaded model copy under `/app/<dir>/` from failing the
  candidate. Symlinks are permitted so that internal relative links at the top
  level do not fail capture either. Capture still fails, where upstream would
  not care because it reads only `/app/result.txt`, in these cases:
  - a top-level symlink with an absolute or escaping target;
  - a device, socket or named pipe at the top level of `/app`;
  - a top-level file, or a direct subdirectory of `/app`, that cannot be read
    (for example mode 000). Capture runs without `CAP_DAC_OVERRIDE`, and the
    walker lists every direct subdirectory before the exclude pattern drops
    its entries;
  - a file name with a backslash or invalid UTF-8 at the top level or directly
    inside a top-level subdirectory, because names are checked before the
    exclude pattern applies;
  - a mount of another filesystem at the top level of `/app`.

  Each is stricter. No solution needs such a layout: the task only asks for
  one line written to one file.
- `/app/result.txt` must be a regular file. Upstream follows a symlink; here a
  symlink is `not_regular` (or, if absolute, fails capture). Stricter; the
  instructions ask to write the line to the file.
- `/app/result.txt` is read up to 16 MiB; a larger file fails as `too_large`.
  Upstream has no bound, so a file over 16 MiB that is one padded line of the
  answer would pass upstream only. Stricter, for files no solution writes.
- Encoding: upstream reads the file as UTF-8 (the image sets `LANG=C.UTF-8`)
  and fails on invalid UTF-8 with a decode error. The `text` parser rejects
  invalid UTF-8 too, and also rejects a leading byte-order mark. Upstream
  keeps a BOM as `﻿` in the line, which `strip()` does not remove, so it
  fails too. Equivalent (see `mutant-bom`).
- Allowed domains: `huggingface.co` and `hf.co`. The reference downloads the
  model from `huggingface.co`, and with `hf-xet` installed the file content
  comes from `us.aws.cdn.hf.co` and `cas-server.xethub.hf.co` (from the
  reference run's proxy log). Upstream allows all internet access; this is the
  least the reference needs. More strict for agents that would use other
  sources, such as a mirror.
- Instructions, baseline and the single case are upstream's, unchanged. The
  baseline is `alexgshaw/mteb-retrieve:20251031` pinned by the digest
  `docker pull` reported.
- `reference.sh` is upstream's `solution/solve.sh` unchanged, preceded by
  `#!/bin/sh` and `cd /app`. No drift repair was needed.

## Limitation: answer reachable through an allowed domain

`huggingface.co` hosts the dataset `harborframework/terminal-bench-2.0`, which
publishes upstream's test file at
`https://huggingface.co/datasets/harborframework/terminal-bench-2.0/blob/main/mteb-retrieve/tests/test_outputs.py`.
That file contains the expected line. The domain is kept because the reference
needs it to download the embedding model.

## Candidates

- `reference.sh`: upstream's solution.
- `null.sh`: writes nothing.
- `mutant-crlf.sh`: the right line ending in `\r\n`. Aimed at the Oracle's
  universal-newline line count and `strip`; upstream passes it.
- `mutant-print-newline.sh`: `print(docs[i], file=f)` with the unstripped line,
  leaving a second, empty line. Aimed at the line count; upstream fails it.
- `mutant-bom.sh`: the right line written with `utf-8-sig`. Aimed at the
  parser's BOM rejection; upstream fails it.
- `mutant-sixth.sh`: off by one in the ranking (sixth highest). Upstream fails
  it.
- `attack-shotgun-cr.sh`: all 30 documents on one `\n`-free "line" separated by
  `\r`, aimed at a grader that splits only on `\n` and looks for the answer in
  it. The Oracle counts 30 lines and fails it.
- `attack-symlink.sh`: `/app/result.txt` as a relative symlink to the input
  (`data.txt`). Capture keeps the link because symlinks are permitted; the
  Oracle receives `not_regular` and fails it. Native follows the link and
  fails it on the line count.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-crlf` pass both; `null`, `mutant-print-newline`,
`mutant-bom`, `mutant-sixth`, `attack-shotgun-cr` and `attack-symlink` fail
both (SecureBench class `oracle` for all of them).

## Review

Reviewer: conversion-reviewer (scratch `mteb-retrieve-review`), 2026-10-26, second review. Pack digest reviewed: `sha256:7b8aebbbf3ff4fe6e8d53bcbb698efcd8d102e3aec8022cddd5124ad1a77141a`, the same as in the first review. `task/` did not change. Since the first review, `CONVERSION.md` and `candidates/attack-symlink.sh` have changed.

1. Instructions: `cmp task/instructions.md` against upstream `instruction.md` reports no difference.
2. Scope: one root `/app` with `exclude = ["*/*"]`. Following `securebench/core/patterns.py`, this excludes everything below each direct subdirectory of `/app` and keeps top-level files, including `/app/result.txt`, the only deliverable. Upstream has no test files or convention-loaded files, and nothing in the candidate runs. The baseline `/app` holds only `data.txt` and no symlinks. The baseline repo digest matches the upstream tag `alexgshaw/mteb-retrieve:20251031`. The scope bullet now lists every capture failure upstream would not have, each labelled stricter with a reason. I checked the list against `securebench_utility/utility.py`: special files (lines 291-292), unreadable top-level files or direct subdirectories (capture keeps no capabilities, `isolation/docker.py`), names checked before the exclude test (lines 234-237), and another filesystem at the top level (line 247). The first review's first finding is fixed.
3. Expected value leaks: the expected line is only in `hidden/expected.json`. There is no `public/` and no `evaluation/`. In the baseline image, `/app` holds only the input `data.txt`, and there is no model cache, `/tests` or `/logs`. The image's other matches for the line are the `mteb` package naming its own paper. The allowed-domain limitation is recorded, and I confirmed with curl that the dataset file on huggingface.co holds the literal.
4. Challenges: there are none (artifact check only).
5. Cases: one artifact check covers upstream's two tests. Nothing was added, and the seed is unused, as upstream draws nothing at random.
6. Oracle: the Oracle is unchanged. The expected value comes from `hidden/`, and the code holds comparison logic only. It requires `present`, recounts lines with universal newlines, requires one line and compares `strip()`. Its work is bounded by the 16 MiB file limit, and it fails closed. My differential from the first review still applies: 30,000 strings through the real text parser and `judge`, compared with Python's `readlines` plus upstream's assertions, gave 0 mismatches.
7. Candidates: `attack-symlink.sh` now creates a relative link, `result.txt -> data.txt`. The link stays inside the scope, and `symlinks = true` lets capture keep it, so the attack now reaches the Oracle, which fails it as `not_regular` (class `oracle` in `qualification.json`). Its comment matches what it does. The first review's second finding is fixed. The other candidates are unchanged and remain as assessed: the reference is upstream's `solve.sh` with only a shebang, a comment and `cd /app` added; the mutants run the real model and target the newline recount, the BOM rejection and the ranking; `attack-shotgun-cr` targets a `\n`-only split.
8. Divergences: `qualification.json` reports `"problems": []`, and every SecureBench run records the digest above. Every run was admitted and rejudged, with `dirty: false`. The runs used three framework commits (`402bbb9`, `3b0b868` and `f9693c5`), but `git diff` between them shows no change under `securebench/`, `securebench_utility/`, `securebench_relay_proxy/`, `pyproject.toml` or `uv.lock`, so they ran the same SecureBench code. The two graders agree on every candidate: `reference` and `mutant-crlf` pass both, and every other candidate fails both. "Divergences from native" says "None", which matches.
9. Inventory: `conversions/inventory.tsv` has no `mteb-retrieve` row yet. No Section 11 reason applies, so the row should read `converted`.

Every upstream assertion is accounted for: `os.path.exists` maps to status `present`, `len(lines) == 1` to the Oracle's `readlines` count, and `lines[0].strip() == expected` to the final comparison.

Findings:
- None. Both findings from the first review are fixed, as described in points 2 and 7.

Verdict: approved
