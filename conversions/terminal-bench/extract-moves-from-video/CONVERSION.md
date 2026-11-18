# extract-moves-from-video

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/extract-moves-from-video

## How the pack grades

The agent must write `/app/solution.txt`, the moves typed in a YouTube video of a Zork game, one per line. Upstream's `tests/test_outputs.py` has two tests:

- `test_solution_file_exists`: `/app/solution.txt` exists.
- `test_solution_content_similarity`: the file, read with `open()` in text mode, has a Levenshtein similarity of at least 90 percent to the `SOLUTION` literal, where similarity is `100.0 * (1 - distance / max(len(actual), len(SOLUTION)))`.

The pack has one protocol check, `solution`, with one case. Its adapter (`evaluation/adapter.py`, standard-library Python on the stock interpreter) reads `/app/solution.txt` in the replayed candidate the way upstream's `open()` does and returns the decoded string as `{"text": ...}`. It reports `unable` when the file cannot be opened (missing, a directory, a dangling symlink), is over 64 KiB, or is not valid UTF-8; each of these ends the attempt `failed` with class `case_error`, as each fails upstream's test. The candidate's files are only read: the stock interpreter runs with `-I`, so nothing in `/app` is on its import path. Even if a candidate did forge the observation, it would gain nothing, since it already controls the whole content of the file the adapter reports.

The Oracle (`hidden/oracle.py`) repeats upstream's computation on the reported string: upstream's own `levenshtein_distance` and upstream's float expression for the similarity, compared with `>= 90.0`. The expected transcript is `hidden/solution.txt`, 1,346 characters and 280 lines, the `SOLUTION` literal byte for byte. It was extracted with:

```bash
python3 -I -c "import ast; [open('hidden/solution.txt','w',newline='').write(n.value.value) for n in ast.parse(open('tests/test_outputs.py').read()).body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', None) == 'SOLUTION']"
```

## Fidelity changes

- **No network for the agent (stricter; needs the coordinator's attention).** Upstream sets `allow_internet = true`, and the instructions tell the agent to download the video from `youtube.com`. The brief allows only the domains the reference needs, and upstream's reference (`solution/solve.sh`, which its own comments call a template) writes the transcript from a hardcoded list without any network. So `allowed_domains` is empty. The baseline is a bare `ubuntu:24.04` with no Python, `curl` or video tools, so under this pack an agent cannot download the video or install tools to process it, and can only pass by recalling the transcript. Allowing the download would take at least the YouTube domains (`youtube.com`, `googlevideo.com`, `ytimg.com`) and, to install tools, the Ubuntu archive, PyPI or `github.com`; `github.com` serves upstream's public repository, whose `solution/solve.sh` and `tests/test_outputs.py` hold the answer, so it would also need the "answer reachable" limitation. We kept to the brief's rule and leave the choice to the coordinator.
- **Two tests become one check (equivalent).** `test_solution_file_exists` passes for any existing path, but upstream's verdict needs both tests, and the similarity test fails on anything that `open()` cannot open and read. The adapter opens the file with the same call, so the single check fails exactly when either test fails.
- **A protocol check instead of an artifact check (equivalent).** An artifact check would be simpler, but SecureBench's text parser rejects a file that starts with a UTF-8 byte order mark and keeps `\r`, while upstream's `open()` keeps the byte order mark as one character and translates newlines. A correct transcript saved by a Windows tool (byte order mark, `\r\n`) passes natively at 99.93 percent and would have failed an artifact check. The adapter avoids the difference by decoding with the same layer `open()` builds for text mode: `io.TextIOWrapper` with `encoding="utf-8"`, strict errors and `newline=None`. `mutant-windows-text` checks this.
- **Decoding (equivalent).** Upstream's `open()` uses the locale encoding, which for the verifier's Python 3.13 in the image's unset (C) locale is UTF-8 with strict errors, through locale coercion and UTF-8 mode. The adapter names UTF-8 explicitly, so its result does not depend on the Evaluation's locale. `mutant-latin1` checks this: a transcript one character off, but with that character saved as a Latin-1 byte, fails both graders, where a lenient decoder would have passed it.
- **Size bound of 64 KiB (equivalent).** The distance is at least the length difference, so natively any file longer than 1,495 characters fails (`1,496` characters give at best `100 * (1 - 150/1496) = 89.97`). A file over 65,536 bytes holds at least 16,384 characters, so the adapter's `too_large` report fails only files that upstream fails.
- **Length bound before the distance loop (equivalent).** The Oracle runs on the host, so before upstream's quadratic loop it computes the similarity that the length difference alone would give. When even that best case is below 90 it fails the file without the loop. The bound is exact: the true distance is at least the length difference, and every step of the similarity expression is monotonic in floating point, so the true similarity is no higher. The loop therefore only runs on files within about ten percent of the expected length, at most about two million steps. `mutant-prompt-prefix` and `attack-oracle-cost` take this path; `mutant-ocr-tie` and `mutant-ocr-below` take the loop.
- **Scope (equivalent, except for symlinks).** The scope is `/app`, the workdir, empty in the baseline. Upstream reads only `/app/solution.txt`, so nothing else under `/app` can change the native verdict. The excludes drop everything inside subdirectories of `/app` (`*/*`) and common media and frame files at its top level (`*.mp4`, `*.png` and the like), so that a correct agent that leaves its downloads, frame dumps or a virtual environment in `/app` is not failed by capture's size bounds or by the symlinks a virtual environment contains. No exclude matches `solution.txt`. The bounds are the largest allowed, 100,000 entries and 2 GiB.
- **Symlinks (stricter, narrowly).** The root allows relative symlinks that stay inside `/app`, and the adapter's `open()` follows them, as upstream's does. So `/app/solution.txt` may be a symlink to another top-level file in `/app`. Two cases differ from native. A symlink to a file outside `/app`, or any absolute or escaping symlink at the top level of `/app` outside the excludes, fails capture. A symlink to a file inside a subdirectory of `/app` dangles after capture, because the excludes drop that file, so the adapter reports `unable`. Upstream's instructions ask the agent to "create a file", and we expect few agents to deliver the transcript as a symlink.
- **Baseline (equivalent).** Upstream's `docker_image`, `alexgshaw/extract-moves-from-video:20251031`, pinned to the digest `docker pull` reported.
- **Verifier installs (equivalent).** Upstream's `test.sh` installs `curl`, `uv`, Python 3.13 and pytest at grading time, which needs network. The adapter needs none of them: it uses the stock interpreter SecureBench mounts in every Evaluation, and only the standard library.

The reference is upstream's `solution/solve.sh` with its first two lines changed and one added. Upstream's script starts with the canary comment, followed by `#!/bin/bash`, which is an ordinary comment there because it is not the first line. The reference starts with `#!/bin/sh`, then a comment that replaces upstream's `#!/bin/bash` line, then `cd /app`, needed because upstream writes the relative path `solution.txt` from the image's working directory. The canary comment and everything after it are unchanged. It needs no drift repair.

## Candidates

| Candidate | What it does | Upstream similarity | Expected |
|---|---|---|---|
| `reference.sh` | Upstream solution | 100.0 | pass |
| `null.sh` | Writes nothing | file missing | fail |
| `mutant-windows-text.sh` | Reference with a UTF-8 byte order mark and `\r\n` line endings | 1 / 1,347 = 99.93 | pass |
| `mutant-ocr-tie.sh` | First 131 `e` read as `c`, plus a stray line `inv` | 135 / 1,350 = exactly 90.0 | pass |
| `mutant-ocr-below.sh` | The same with 132 misreads | 136 / 1,350 = 89.93 | fail |
| `mutant-latin1.sh` | `get egg` read as `gét egg`, saved as Latin-1 | `UnicodeDecodeError` | fail |
| `mutant-prompt-prefix.sh` | Every move keeps Zork's `>` prompt | 82.78 | fail |
| `attack-symlink-out.sh` | `solution.txt` is a symlink out of `/app` | file missing | fail (capture) |
| `attack-verdict-claim.sh` | The file claims a passing verdict | 7.58 | fail |
| `attack-oracle-cost.sh` | 64,800 bytes of moves, to slow a quadratic judge | 1.83 | fail |

The upstream similarities were computed with upstream's own test module on each candidate's output, in a UTF-8 locale.

## Divergences from native

None. All ten candidates got the same verdict from both graders in `qualification.json`: the reference, `mutant-windows-text` and `mutant-ocr-tie` pass both, and every other candidate fails both. `mutant-windows-text` passing natively confirms that upstream keeps a byte order mark as one character, and `mutant-latin1` failing natively confirms that upstream decodes strictly as UTF-8.

## Review

Reviewer: aedbeaed26ce0fb22, 2026-10-27 (second review, after the converter addressed the first one's findings)

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged: one root, `/app`, which is an empty directory in the baseline (`alexgshaw/extract-moves-from-video@sha256:14a9dcca…`) with no symlinks, and the image has no `/.securebench`. Upstream has no test files or convention-loaded files under `/app`. `*/*` excludes everything below a top-level directory but not the directory itself, and no pattern matches `solution.txt`, even with case folding. The adapter now follows a symlink with `open()`, as upstream does. The two cases that remain stricter (a symlink that leaves `/app` fails capture; a symlink into an excluded subdirectory dangles and the adapter reports `unable`) are recorded accurately.
3. No expected value leaks. The only expected value is `hidden/solution.txt`, byte for byte upstream's `SOLUTION` literal (checked with `ast`). `evaluation/` holds the adapter and two schemas, with no expected value. There is no `public/`. The baseline holds no copy of the transcript. `allowed_domains` is empty.
4. Challenges. There is one case, and its challenge is `{}` (schema: an empty object, at most 64 bytes). It carries no hidden material.
5. Cases. Upstream's two tests become one protocol case. No case was added, and the seed is unused.
6. Oracle. The expected value comes from `hidden/`. `oracle.py` holds upstream's `levenshtein_distance`, upstream's similarity expression and its `>= 90.0` threshold, and an exact length pre-check that limits the loop to about 2 million steps. It fails anything but `Observed`, and any observation whose keys are not exactly `{"text"}` or whose `text` is not a string. The adapter decodes with `io.TextIOWrapper(..., encoding="utf-8")`, which is the layer `open()` builds in text mode: strict errors, `newline=None`, and a BOM kept. It reports `unable` on an `OSError`, a non-UTF-8 file or a file over 64 KiB. A candidate gains nothing by forging the observation, because any string it could forge is also reachable by writing that string to the file. I ran the adapter on the host with stock Python and judged its output with the Oracle. I compared that with upstream's test module on every candidate's output from the baseline image, and on edge files: a BOM, `\r` only, `\r\r\n`, a NUL, an encoded surrogate, and 64 KiB of `\x01`. The verdicts agree on every file. The largest observation, 393,245 bytes, is within `max_observation_bytes` (524,288).
7. Candidates. The reference now differs from upstream's `solve.sh` only in the header, which the record and the script describe accurately: a shebang, a comment in place of upstream's inert `#!/bin/bash` line, and `cd /app`. The canary line and everything after it are identical. `mutant-windows-text` (a BOM and CRLF) replaces `mutant-crlf` and targets the adapter's decoding. `mutant-latin1` covers strict decoding, `mutant-ocr-tie` and `mutant-ocr-below` cover rounding at the threshold, and `mutant-prompt-prefix` covers the length pre-check. All of them run real code. The attacks are a symlink out of the scope, a claimed verdict, and a judge-cost attack just under the bound.
8. Divergences. `validate` prints `sha256:468b012131e3f63303091c7589253420f004b22a8d2d8da8b98909f97b9d353a`. All ten SecureBench runs in `qualification.json` record this digest, framework commit 0da677d with a clean tree, and a reproduced rejudge, and `problems` is empty. Every candidate got the same verdict from both graders. In particular, `mutant-windows-text` passes both, which confirms the fix natively. "None" holds.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet; the coordinator adds it. No exclusion reason applies.

Every upstream assertion is accounted for. `test_solution_file_exists` and `test_solution_content_similarity` are both covered by the `solution` case. The adapter reports `unable` whenever `open()` fails, and the Oracle repeats the similarity test.

Findings from the first review:
- BOM rejected by the text parser: fixed by the protocol check. Confirmed by my differential and by `mutant-windows-text` passing both graders.
- Reference header not described accurately: fixed.

Findings:
- None that block approval. For the coordinator, as before: the empty `allowed_domains` follows the brief's rule and is recorded as stricter. But an agent cannot download the video and can pass only by recalling the transcript. Whether to allow the YouTube domains is the coordinator's decision.

Verdict: approved
