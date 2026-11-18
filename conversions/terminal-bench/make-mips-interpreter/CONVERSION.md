# make-mips-interpreter

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/make-mips-interpreter

## The conversion in short

The agent must write `/app/vm.js`, a MIPS interpreter in JavaScript that runs the provided ELF `/app/doomgeneric_mips` under `node vm.js`. The ELF is doomgeneric built with the `doomgeneric_img.c` frontend: it reads `doom.wad` from the working directory and writes every tenth frame to `/tmp/frame.bmp`, so the interpreter must handle the program's file system calls. Upstream's three tests start `node /app/vm.js` from `/app`, wait up to 30 s for `/tmp/frame.bmp`, wait 1 s more, stop vm.js, and then assert on its output and on the frame. They run vm.js once, on the baseline's files, so upstream has one case.

The pack has one protocol check, `doom`, with that one case. It runs `task/evaluation/adapter.py` (standard-library Python on the stock interpreter) in a fresh networkless Evaluation environment. The challenge is empty. The adapter reproduces upstream's process handling: stderr merged into stdout, working directory `/app`, a 30 s wait for the frame with 0.1 s polling, 1 s more, `terminate`, and `kill` after 5 s. The one difference is vm.js's standard input ("Fidelity changes"). It then decodes the frame with `task/evaluation/frame.py`, which runs on the baseline's own `/usr/local/bin/python3` (3.13) with the baseline's Pillow 11.2.1, the versions upstream's verifier installs, and does exactly what upstream's test does: `Image.open(frame).convert("RGB")`. The adapter writes the first 12 MiB of vm.js's output, in base64, to the check's Output Artifact `/srv/vm-output.json` (JSON, at most 16 MiB). Its observation says whether the frame appeared and gives the frame's size and RGB bytes in base64, or a problem (`absent`, `empty`, `too_large`, `undecodable`). It compares nothing. The output goes to an Output Artifact because the observation is bounded at 4 MiB, and an interpreter that traces its system calls can print megabytes before the line upstream looks for (`mutant-verbose-read`).

`task/hidden/cases.json` holds the case: its empty challenge, the expected `I_InitGraphics` line, the reference size (640x400) and the name of the file with the reference pixels, `task/hidden/reference-rgb.zlib` (upstream's `tests/reference.jpg` as Pillow 11.2.1 decodes it). `task/hidden/oracle.py` reads them in `plan` and holds only the comparisons in `judge`; its one constant is upstream's threshold, 0.95.

## How upstream's tests map to checks

Upstream's tests are the three functions of `tests/test_outputs.py`. All of them check what the task asks for; there are no regression tests. Every assertion is carried by check `doom`, case 0.

| Upstream test | Assertion | Check and case | How |
|---|---|---|---|
| `test_vm_execution` | `frame.bmp` exists within 30 s, else `TimeoutError` | `doom`, case 0 | the adapter waits as upstream does and reports `frame_appeared`; `judge` requires `true` |
| `test_vm_execution` | `b"I_InitGraphics: DOOM screen size: w x h: 320 x 200" in stdout_content` (stdout and stderr merged) | `doom`, case 0 | the adapter writes the first 12 MiB of the merged output to the Output Artifact; `judge` requires `expected_text` from `cases.json` in it (12 MiB bound: "Fidelity changes") |
| `test_frame_bmp_exists` | `frame_path.exists()` | `doom`, case 0 | the adapter reports `frame_problem: absent`; `judge` requires a decoded frame |
| `test_frame_bmp_exists` | `frame_path.stat().st_size > 0` | `doom`, case 0 | the adapter reports `frame_problem: empty`; `judge` requires a decoded frame |
| `test_frame_bmp_similar_to_reference` | `reference_path.exists()` | none (grader side) | the reference is hidden data here; `plan` reads `reference-rgb.zlib` and stops if it is missing or does not match the size in `cases.json`. It checks the grader, not the candidate |
| `test_frame_bmp_similar_to_reference` | `Image.open(frame_path).convert("RGB")` succeeds (an exception fails the test) | `doom`, case 0 | `frame.py` makes that call; if Pillow raises, the adapter reports `undecodable` and the case fails |
| `test_frame_bmp_similar_to_reference` | `frame_img.size == ref_img.size` | `doom`, case 0 | `judge` requires the width and height from `cases.json` (640x400, the size of `reference.jpg`) and exactly 640 x 400 x 3 RGB bytes |
| `test_frame_bmp_similar_to_reference` | `similarity >= 0.95`, with similarity `1 - (sum of absolute channel differences / (pixels * 3)) / 255` | `doom`, case 0 | `judge` computes the same value with the same arithmetic against `reference-rgb.zlib`, and the same threshold |

Nothing in the pack is outside this table.

## Differential test of the frame reading and the score

Pillow decodes the frame in both graders, at the same version, so the frame decoding is not reimplemented. The Oracle reimplements the test's similarity loop, and the adapter, `frame.py` and the Oracle add bounds and a path of their own between the frame and the score. We compared the whole path with upstream's test code. `hidden/differential.py` runs in the baseline image. For each file, it runs `test_frame_bmp_exists` and `test_frame_bmp_similar_to_reference` verbatim (Pillow decoding, the same loops), next to the adapter's `read_frame` (which runs `frame.py`) followed by the Oracle's `judge` on case 0 of its plan. We re-ran it on the remediated pack (2026-10-25), with a frame written by the upstream reference `vm.js` in the pinned baseline. The 22 files and their results:

| File | Upstream | SecureBench |
|---|---|---|
| reference `vm.js`'s frame (32-bit, top-down, as `doomgeneric_img.c` writes) | pass, 0.957128497753268 | pass, 0.957128497753268 |
| same frame, 24-bit bottom-up BMP saved by Pillow | pass, same score | pass, same score |
| same frame as PNG content in `frame.bmp` | pass, same score | pass, same score |
| same frame as an 8-bit palette BMP saved by Pillow | pass, same score | pass, same score |
| 11 frames perturbed to total channel differences of 9,792,000 + d for d = -1000, -100, -10, -2, -1, 0, 1, 2, 10, 100, 1000 (9,792,000 is a similarity of exactly 0.95) | pass for d <= 0, fail for d > 0 (0.95 itself passes) | identical verdicts and identical floats |
| 3 frames perturbed further (0.9561, 0.9469, 0.9163) | identical verdicts and floats | identical verdicts and floats |
| frame truncated by 1,000 bytes | fail (`OSError`) | fail (`undecodable`) |
| empty file | fail (empty) | fail (`empty`) |
| 320x200 frame | fail (size) | fail (size) |
| `BM` followed by 100 zero bytes | fail (`OSError`) | fail (`undecodable`) |

No verdict differs. The reference's frame scores 0.9571 against `reference.jpg`, only 0.007 above the threshold, so the exact agreement of the scores matters. Upstream's verdict depends on Pillow's JPEG decoding, and `reference-rgb.zlib` was produced by the same Pillow version. To redo it, run the command in the docstring of `hidden/differential.py` with a frame from the reference `vm.js`. To redo `reference-rgb.zlib`, run the command in the docstring of `hidden/derive.py`; we re-ran it on 2026-10-25 in the pinned baseline, and it reproduced the file byte for byte and printed the size 640x400 that `cases.json` records.

## Fidelity changes

- **Scope (stricter).** One root, `/app`, holding the deliverable `vm.js` and anything it loads (the reference adds `memory.js` and `make_json.js`, about 2 MB). The bounds are the largest the format allows (100,000 entries, 2 GiB).
  - `doomgeneric_mips` and `doom.wad` are excluded, so edits to `/app/doomgeneric_mips` and `/app/doom.wad` are dropped. A `vm.js` that loads these files when it runs gets the baseline's ELF and WAD. A `vm.js` that snapshots a program into another file in `/app` when the candidate is built, as the reference does with `memory.js`, runs that snapshot, and the grader cannot tell which ELF was snapshotted. They are excluded because they are what is measured: the instructions say "I have provided /app/doomgeneric_mips ... implement a MIPS interpreter ... this should run the MIPS file", so the interpreter is graded on the file provided, not on one the agent made; and `reference.jpg` is the title screen the program draws from the baseline's `doom.wad`. No correct interpreter needs to change either file.
  - So the `doomgeneric_mips` exclusion stops exactly two things, and nothing more. First, one delivery path of a public-answer cheat: a `vm.js` that runs a title renderer put in place of `/app/doomgeneric_mips` (`attack-replace-elf`, native 1.0). The same renderer at any other path in `/app`, started by `vm.js`, passes both graders; it produces only the public title screen, which is outside SecureBench's scope (see "Public answer"). Second, one way of running a rebuilt ELF: a `vm.js` that loads a rebuilt `/app/doomgeneric_mips` when it runs (next bullet).
  - The exclusion has a cost (stricter). The baseline ships the doomgeneric source and the MIPS toolchain, and its Makefile compiles through `llc -march=mipsel -mcpu=mips32r2 ... -O3` and assembles for `mips32r2` (`mips.patch`, lines 40 and 41). An agent could rebuild `/app/doomgeneric_mips`, for example for plain `mips32` to avoid `ext`, `seb` and `seh`, and write a `vm.js` that loads that ELF when it runs. Upstream grades its own ELF and can pass it. Here the rebuilt ELF is dropped, `vm.js` meets the baseline's `mips32r2` ELF, and the candidate fails unless it also interprets the instructions it avoided. We accept this cost because the instructions name the provided file as the program to run. The cost applies only to a `vm.js` that loads the ELF when it runs: one that snapshots a rebuilt ELF into another file when the candidate is built passes here, as it does upstream.
  - `doomgeneric/` stays in scope. The instructions provide it as the corresponding source, and nothing graded reads it except what a candidate's `vm.js` chooses to read.
  - Nothing outside `/app` is captured: not `/tmp` (a framework-protected path), and not packages installed under `/usr`. The baseline has `node` 18.20.4 and no `npm`; a `vm.js` that loads modules the agent installed outside `/app` would not find them here. The instructions name `node vm.js` and nothing else.
  - A frame the agent left in `/tmp/frame.bmp` does not reach the Evaluation. Upstream, it is still there when the tests run, and the test then waits only for the existing file (`attack-stale-frame`).
  - Internal symlinks are allowed (`symlinks = true`). A symlink that leaves `/app` fails the attempt with class `capture`, where upstream would follow it. Allowing links does not reach the measured files: a link put in place of `doomgeneric_mips` or `doom.wad` is dropped with the exclusion.
  - The baseline has no symlinks under `/app` and no test material. Upstream mounts its tests and `reference.jpg` only at grading time, in `/tests`.
- **Image formats (equivalent).** `frame.py` decodes with the baseline's Pillow 11.2.1, the version upstream's verifier installs, by the same call, so every format Pillow reads is read here too (differential test above). The baseline's Python and Pillow are outside the scope, so a candidate's delta cannot change them.
- **Output bounds (stricter, only for extremely verbose interpreters).** The adapter reports the first 12 MiB of vm.js's output (12 MiB less 48 bytes, the most whose base64 fits the 16 MiB Output Artifact bound), so the `I_InitGraphics` line must appear within it; upstream reads its whole output. The reference prints the line after about 2 KB. `mutant-verbose-read`, the reference with its commented-out `read` debug line turned on and printing the bytes read in hex, prints it after 3,394,651 bytes and saves its first frame 3 s after start, in our probe in the baseline with 1 CPU; it passes here. Under the earlier 1 MiB bound it would have failed here and passed upstream. An interpreter that prints more than 12 MiB before the line within 30 s, for example one that traces every instruction, passes upstream and fails here. A frame of more than 262,144 pixels, or over 4,096 on a side, is reported as `too_large` without being converted. Every such frame also fails upstream's size check, which needs 640x400 = 256,000 pixels.
- **Standard input (equivalent).** The adapter starts vm.js with standard input from `/dev/null`. Upstream's `Popen` passes no `stdin`, so vm.js inherits the verifier's standard input, whatever Harbor gives the test script. The difference cannot matter to a correct interpreter: the program never reads standard input (`doomgeneric_img.c` takes no input; `DG_GetKey` reads only an internal key queue), and the reference's `read` for fd 0 returns a fixed string without touching the real standard input. A `vm.js` that read its own standard input for something gets end of file here.
- **Allowed domains (stricter).** None, which is all the reference needs: `solve.sh` writes two files and runs `node`. Upstream allows the Internet. An agent here cannot install packages (there is no `npm` in the image anyway), and can still run `node` and the image's MIPS cross toolchain and Python to test its interpreter.
- **Grading tools (equivalent).** Upstream's verifier installs Python 3.13, pytest and Pillow 11.2.1 from the network at grading time. Here the adapter runs on the stock Python, the frame is decoded by the baseline's Python 3.13 and Pillow 11.2.1, the reference picture is pre-decoded by the same Pillow version, and `node` is the baseline's `/usr/bin/node`.
- **Timing (equivalent when the case gets a full core, stricter on a loaded worker).** The case runs in its own Evaluation environment with the upstream limits (1 CPU, 2 GiB, 10 GiB disk). The 30 s wait for the frame is wall-clock time, and `--cpus 1` caps the case's CPU but does not reserve it. On a worker with a free core, `vm.js` gets the single CPU upstream's run gets. On a worker loaded by other runs, it gets less, and an interpreter whose first frame takes, say, 20 s upstream can pass upstream and fail here. The reference's first frame appears 3.4 to 5.5 s after vm.js starts in our runs, far within the 30 s wait, and the per-case timeout is 180 s. An interpreter that needs more than 30 s for the first frame fails both graders.
- **Frame read race (equivalent).** The reference `vm.js` creates `/tmp/frame.bmp` when the program opens it and fills it when the program closes it. Stopping vm.js between the two leaves an empty frame, which fails here as upstream. Both graders run vm.js once, with the same waits, so the race is equally likely. It did not occur in any of our runs.
- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.

## Public answer

The whole solution is in upstream's `solution/solve.sh`, and the frame compared is upstream's `tests/reference.jpg`. A `vm.js` that writes that picture, or one that draws the title screen from `doom.wad` without interpreting MIPS, passes both graders, as upstream's tests allow. These cheats use public answers and do not tamper with grading, so they are outside SecureBench's scope; the pack does not try to stop them.

## Divergences from native

From `qualification.json` of 2026-10-25 (pack `sha256:5f7d0585...`, no problems; every SecureBench run admitted, reproduced by `rejudge` and not dirty). The reference and `mutant-verbose-read` pass both graders; the null candidate and the other four mutants fail both. Two candidates diverge, both attacks:

- **`attack-stale-frame`: native 1.0, SecureBench `failed` (`oracle`, frame did not appear within 30 s).** Upstream grades in the agent's own container, where the candidate left the converted `reference.jpg` in `/tmp/frame.bmp`, so the test finds the frame at once while `vm.js` only prints the expected line. Here `/tmp` is not captured, `vm.js` writes no frame, and none appears. SecureBench is right: running `node vm.js` does not produce a frame.
- **`attack-replace-elf`: native 1.0, SecureBench `failed` (`oracle`, frame did not appear within 30 s).** Upstream runs the title renderer put in place of `/app/doomgeneric_mips`, which `vm.js` executes natively. Here the replacement is dropped by the exclusion, and the baseline ELF cannot be executed natively, so no line is printed and no frame appears. SecureBench is right by the instructions, which ask for an interpreter that runs the provided MIPS file: this `vm.js` interprets nothing. The exclusion closes only this path ("Scope").

## Candidates

- `reference.sh`: runs upstream `solve.sh`, kept byte for byte in `candidates/upstream/solve.sh`, with `bash` from `/app`. No drift repair: the solution needs no network and no packages.
- `null.sh`: changes nothing. There is no `/app/vm.js`, so `node` exits with `Cannot find module '/app/vm.js'` and no frame appears.
- `mutant-silent-stdout.sh` (aimed at the substring check on the output): `write` for the standard streams reports success but prints nothing. DOOM boots and its frames are correct, but its start-up text never reaches vm.js's output; only vm.js's own `console.log` lines (`Open!`, `Unhandled syscall: 83`) do.
- `mutant-no-writeback.sh` (aimed at the frame-exists and non-empty checks, which the adapter reports as problems): `close` forgets to write a file's buffered contents back. `open` still creates `/tmp/frame.bmp`, so the frame appears, but it stays empty.
- `mutant-srlv-dispatch.sh` (aimed at the reimplemented similarity score): the R-type dispatch runs the SRL handler for SRLV, so the shift uses the instruction's `sa` field (0) instead of the register. DOOM boots and prints the `I_InitGraphics` line and frames are saved, but `cmap_to_fb`'s `pix >> (j*8)` stores the blue byte in every channel. Similarity 0.807 to `reference.jpg` (SecureBench run of 2026-10-25).
- `mutant-verbose-read.sh` (aimed at the 12 MiB output bound): the reference with the debug line its author left commented out in `read` (`//console.log(this.fileCache, fd)`) turned on and extended to print the bytes each read returns, in hex. DOOM reads about 1.7 MB of `doom.wad` before `I_InitGraphics`, so the line comes after 3,394,651 bytes of output; the frames are correct. It should pass both graders. With 1 MiB, the bound of the earlier pack, it would have failed here only.
- `mutant-lbu-sign-extend.sh` (aimed at the 30 s wait for the frame): LBU sign-extends like LB. The program runs but goes wrong during `R_Init`, never reaches `I_InitGraphics`, and saves no frame.
- `attack-stale-frame.sh`: tampers with the grading environment. It interprets nothing and writes no frame when it runs. The candidate leaves the converted `reference.jpg` in `/tmp/frame.bmp`, where upstream's grader, which runs in the agent's container, finds it at once; `vm.js` only prints the `I_InitGraphics` line and waits.
- `attack-replace-elf.sh`: tampers with the measured program. It is the public-answer title renderer, `render_title.py`, delivered through the measured input file: it replaces `/app/doomgeneric_mips` with the renderer, and `vm.js` executes `/app/doomgeneric_mips` natively. With the exclusion, the Evaluation's `doomgeneric_mips` is the baseline ELF, which cannot be executed natively (`/bin/sh` reports a syntax error), so no line is printed and no frame appears. The exclusion closes only this path: the same renderer at another path in `/app` passes both graders, as a public-answer cheat outside SecureBench's scope ("Scope", "Public answer").
- `render_title.py` and `reference.jpg` (a copy of upstream `tests/reference.jpg`) are used by the attacks.

Each mutant runs upstream `solve.sh` and then edits one line of `vm.js` with `sed`. If its edit does not apply, it deletes `vm.js`, so a mutant can never silently become the reference. The probes that chose these mutants also tried SRA, SRAV and SRLV as logical or arithmetic shifts, SLTU and SLTIU as signed comparisons, a MULT that loses precision, a signed DIVU and a sign-extending LHU. The first six of those leave the first frame unchanged (similarity 0.9571, so they pass upstream too), and the last two stop DOOM before its first frame, like `mutant-lbu-sign-extend`.

## Remediation

Done on 2026-10-25 under the current converter brief. The earlier conversion added two seeded cases that upstream does not have; everything else it built is kept.

Removed:
- Cases 1 and 2 of check `doom`. In each, `plan` drew a permutation of DOOM's first palette from the run seed (redrawing until the expected frame was far from the known frames), the challenge carried it, and the adapter wrote it into the `PLAYPAL` lump of `/app/doom.wad` before starting vm.js. The expected frame was a model of the title screen under that palette. Upstream runs vm.js once on the baseline's WAD, so these cases, their randomness and their exact-frame comparison were additions. They could fail a candidate that upstream passes, for example a `vm.js` that embeds the WAD when the candidate is built.
- From `task/hidden/oracle.py`: the palette draw, the title model (`_model_frame`), `Random`, and the constants `SEEDED`, `MAX_SIMILARITY_TO_KNOWN` and `MAX_DRAWS`.
- From `task/evaluation/adapter.py`: `patch_palette` and its WAD bounds. The adapter now requires an empty challenge.
- `task/evaluation/challenge.schema.json`: the optional `palette` field; the schema is now the empty object.
- `task/hidden/title-indices.bin`, `playpal0.bin` and `gamma0.bin`, which served only the title model, and the parts of `task/hidden/derive.py` that extracted them and checked the model. `derive.py` now writes only `reference-rgb.zlib`.
- `max_cases` in `task.toml` from 8 to 1.
- From `CONVERSION.md`: the sections on the seeded cases, the two fidelity changes that described them, and "Answer already public upstream", with the residual it recorded. The timing and frame read race fidelity changes are rewritten for one case.

Restored: nothing. Every upstream assertion already had a check (map above), and upstream has no regression tests.

Moved:
- The expected `I_InitGraphics` line and the reference size 640x400 left `oracle.py` for `task/hidden/cases.json`, together with the case's challenge and the name of the reference pixel file. `oracle.py` keeps only upstream's threshold, 0.95, and the comparisons. `hidden/differential.py` now gives the Oracle a `read_json` to read `cases.json`.

Changed after the review of the remediation:
- The output limit (finding 1). The earlier pack reported the first 1 MiB of vm.js's output in the observation. A plausible verbose interpreter, `mutant-verbose-read`, prints the `I_InitGraphics` line after 3.4 MB and passes upstream, so that bound would have made SecureBench fail it. The output now goes to an Output Artifact, `/srv/vm-output.json`, with the first 12 MiB (`adapter.py`, `task.toml`, `oracle.py`, `observation.schema.json`, `differential.py`), and `mutant-verbose-read.sh` was added.
- The standard input difference is now listed under "Fidelity changes" and in the adapter's docstring (finding 2).
- What the `doomgeneric_mips` exclusion enforces is now stated exactly, in "Scope", in the `attack-replace-elf` entry and in the `task.toml` comment (finding 3).

Kept unchanged: the scope and both excludes (with the reason for `doom.wad` rewritten, since it no longer serves a palette patch), the adapter's process handling, `frame.py`, the frame fields of the observation schema, `reference-rgb.zlib`, the Oracle's checks of every field, the similarity arithmetic, and the differential test (re-run after each change, 22 files, 0 disagreements).

Candidates:
- Deleted `attack-hardcode-frame.sh`. It writes upstream's public `reference.jpg` to `/tmp/frame.bmp` and does not tamper with grading. Without the seeded cases it passes both graders, and such cheats are outside SecureBench's scope.
- Kept `attack-stale-frame.sh` and `attack-replace-elf.sh`, both aimed at this task: one leaves output in the grader's path, the other replaces the measured program.
- Kept the four mutants. None existed for the seeded cases; each is aimed at a place where the check is carried by the adapter or a reimplementation (see "Candidates"). Added `mutant-verbose-read.sh` for the output bound (finding 1 of the review of the remediation), making five.
- `reference.sh` and `null.sh` unchanged.

Old mutants that caught additions. In the earlier `qualification.json` no mutant had a native reward of 1.0 with SecureBench `failed`: all four mutants had native 0.0. So no mutant was failed by an addition, and there was none to re-run for this step.

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| (none) | | | |

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: one case as upstream, seeded palette cases removed; frame opened with the baseline's Pillow 11.2.1. Stricter, recorded: a rebuilt ELF that vm.js loads from /app/doomgeneric_mips at run time is dropped; output beyond 12 MiB is not read."

## Review before remediation

Reviewer: a5f7d5e1d4687ddb6, 2026-10-12 (review 2)

Pack digest checked: `sha256:f359e4689e6d0d9b005d3f3b6459967f17c6ff0d81852879abde7b3418c5cafc` (`uv run securebench validate`, valid). It is unchanged since review 1: the fixes touch only `CONVERSION.md`, and no file in `task/` or `candidates/` is newer than `qualification.json`. No file in the conversion is ignored by git.

1. **Instructions.** `cmp` of upstream `instruction.md` and `task/instructions.md`: identical. `candidates/upstream/solve.sh` and `candidates/reference.jpg` are also byte-identical to upstream's `solution/solve.sh` and `tests/reference.jpg`.
2. **Scope.** One root, `/app`, with the format's largest bounds. It holds `vm.js` and anything it loads, which covers the reference (`vm.js`, `make_json.js`, `memory.js`). The baseline has no symlinks under `/app` and no test files, and `/app/doomgeneric/.git` is excluded by the implicit `**/.git`. With no network, an agent cannot install modules outside `/app`, and the baseline has no `npm`. Excluding `doom.wad` makes the adapter always patch the baseline WAD. The `doomgeneric_mips` exclusion is now fully explained (Finding 1 of review 1, fixed below).
3. **Leaking expected values.** No expected value is in `evaluation/` or the challenges. I inspected the baseline image (`alexgshaw/make-mips-interpreter@sha256:082fc882...`, the pinned digest). It has no `/tests`, no `reference.jpg` or any other JPEG or BMP, and nothing but `mips.patch` in `/tmp`. Its `doom.wad` and `doomgeneric/doomgeneric/tables.c` determine the seeded frames once the palette is known. That is the documented render-the-title residual. I re-ran `hidden/derive.py` in the pinned baseline (`--network none --memory 2g`): all four hidden files were reproduced byte for byte. They are also byte-identical to `make-doom-for-mips`'s.
4. **Challenges.** Case 0's challenge is `{}`. Each seeded challenge carries only its own 768-byte palette, which is a permutation of the public palette. No challenge holds another case's palette or any expected frame.
5. **Hidden cases.** `reference.jpg` is public, so two seeded palette cases are added. In the converter's runs, `attack-hardcode-frame` scores 1.0 on case 0 and 0.62 and 0.67 on the seeded cases. The reference scores 0.957128 and then 1.0 and 1.0. The title-renderer probe passes all three cases. That residual is documented under lesson C58 in the same terms as the approved `make-doom-for-mips`, and I agree that no WAD change visible in the first frame can stop it.
6. **Oracle (C52 to C54).**
   - It checks every field: `output_b64` (strict base64), `frame_appeared is True`, no `frame_problem`, a `frame` object, width and height equal to the context's, and the pixel count. An observation with only `frame_appeared`, or with both `frame` and `frame_problem`, fails.
   - Nothing is counted, so deduplication does not apply.
   - Its work is bounded by the schema: at most 1 MiB of output and 768,000 pixel bytes. The zlib data it decompresses comes from its own context.
   - It uses no regular expressions and never uses evidence as a path.
   - The similarity uses upstream's arithmetic. The converter's differential (22 files, with 11 at the 0.95 boundary down to one unit of difference) agrees with upstream in every verdict and every float.
7. **Mutants and attacks.**
   - All four mutants run the real reference with a one-line `sed` edit. I checked that each edit's target occurs exactly once in `solve.sh`, and the guard deletes `vm.js` if an edit does not apply.
   - In the converter's runs each mutant fails for its intended reason. `silent-stdout` and `lbu-sign-extend` fail on "expected text not in output". `no-writeback` fails on `empty`. `srlv-dispatch` fails on similarity.
   - The three attacks target the public frame, the stale `/tmp` frame and the replaced ELF. The `attack-replace-elf` entry now says that the exclusion closes only that one path.
8. **Divergences from native.** `qualification.json` reports `problems: []` over 2 rounds. Every SecureBench run is admitted, rejudged and not dirty, and records the pack digest above.
   - Two framework commits appear: `adbbdbc4` for `reference` and `null`, `d8ff7bfe` for the rest. Their `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical (`git rev-parse <commit>:<dir>`), and also identical to `HEAD`.
   - Verdicts:
     - The reference passes both graders.
     - The null candidate and all four mutants fail both.
     - The three attacks get native 1.0 and SecureBench `failed`/`oracle`. Each divergence is explained, and the explanations hold:
       - `hardcode-frame` writes the same picture whatever `doom.wad` holds.
       - `stale-frame` depends on a `/tmp` file that `node vm.js` does not produce.
       - `replace-elf` interprets nothing and depends on replacing the provided ELF. The explanation correctly adds that only this path is closed.
9. **Inventory.** There is no row yet, as expected. It should read `terminal-bench make-mips-interpreter converted -`, with a note that names the accepted residual: a WAD-reading title renderer that interprets no MIPS passes, as it does upstream. In `campaign.py order terminal-bench` the task comes after `build-pov-ray`, and every task before it has a row, so the selection is consistent. No exclusion reason applies.

Upstream assertions:
- `test_vm_execution` timeout: maps to `frame_appeared`.
- `expected_text in stdout_content`: checked by `judge` on the first 1 MiB of output (fidelity change listed).
- `test_frame_bmp_exists`: maps to the `absent` and `empty` problems.
- `Image.open(...).convert("RGB")`: run by `frame.py` with the baseline's Pillow 11.2.1. Failures map to `undecodable`.
- Size equality and `similarity >= 0.95`: checked by `judge`.
- `reference_path.exists()`: explained.

None is dropped.

Findings of review 1:
- **`doomgeneric_mips` exclusion: fixed.** The Scope bullet now gives the reason as the instructions ("this should run the MIPS file" provided). It says the exclusion closes only the `attack-replace-elf` path and not its class, which the title-renderer probe passes from another path. It states the cost, labelled stricter: an agent that rebuilds the ELF from the shipped source for plain `mips32` and loads it at run time passes upstream and fails here. It also notes that a snapshotting `vm.js` of the provided ELF is unaffected. The `mips.patch` line numbers cited (40 and 41) are correct. The `attack-replace-elf` entry in "Candidates" and in "Divergences from native" says the same.
- **Timing label: fixed.** The label is now "equivalent when each case gets a full core, stricter on a loaded worker". The text explains that wall-clock time and the `--cpus` cap are the cause, and gives an example.
- **Frame read race label: fixed.** The label is now "stricter, rarely", because the verdict is per attempt.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer bdda55d6-3805-4704-aca7-50b6d04d93e5, 2026-10-25 (second review of the remediation, completed after qualification)

Pack digest checked: `sha256:5f7d05858247e524c974f1eb50136bf68afe5b3e17cf4d79deeee8a9cd56cb1b` (`uv run securebench validate`, valid; I checked it again at the end and it had not changed). No file in the conversion is ignored by git. `qualification.json` is still the one from 2026-10-12, for pack digest `sha256:f359e468...`, so it does not cover this pack.

1. **Instructions.** I ran `cmp` on `task/instructions.md` and upstream `instruction.md`: identical. `candidates/upstream/solve.sh` and `candidates/reference.jpg` are byte-identical to upstream's.
2. **Scope.** Unchanged: `/app`, excluding the top-level `doomgeneric_mips` and `doom.wad` (anchored single-component patterns). The pinned baseline has no symlinks under `/app` and no test material, and `node` on `PATH` is `/usr/bin/node`. The text on what the `doomgeneric_mips` exclusion enforces is now exact, in "Scope" and in the `task.toml` comment: a `vm.js` that loads the file when it runs gets the baseline's ELF, and a build-time snapshot runs whatever was snapshotted. The stricter cost is limited to the load-at-run-time variant.
3. **No expected value leaks.** `evaluation/` holds the adapter, `frame.py` and the schemas, with no expected value. The new Output Artifact `/srv/vm-output.json` is written by the adapter in the Evaluation and holds only vm.js's output. It is evidence, not a source of expected values. The expected frame is public (upstream's `reference.jpg`), and "Public answer" records that. No domain is allowed.
4. **Challenges.** One challenge, `{}`.
5. **Cases.** One case, as upstream. The seed is unused.
6. **Oracle.** Expected values come only from `cases.json` and `reference-rgb.zlib`, and the only constant is upstream's threshold. `judge` still requires `frame_appeared is True`, a decoded frame of the reference size, exactly `w*h*3` pixel bytes, and similarity `>= 0.95` with upstream's arithmetic. The output check now reads exactly one Output Artifact, which must be `present`, a JSON object, and strict base64, and must contain the expected line. If any of that fails, the case fails. The bound arithmetic holds: base64 of 12 MiB less 48 bytes is 16,777,152 bytes, plus 18 bytes of wrapper, under the 16 MiB artifact bound. A larger artifact is `too_large`, and the case fails. `/srv` exists in the baseline and is outside the protected paths. After the change I re-ran `hidden/differential.py` in the pinned baseline on a frame from the upstream reference: 22 files, 0 disagreements, identical floats at the 0.95 boundary.
7. **Candidates.** `mutant-verbose-read.sh` is new. Its `sed` target, the tab-indented `//console.log(this.fileCache, fd)`, occurs once in `solve.sh` (line 808), and the guard deletes `vm.js` when the edit does not apply. It runs real code. I probed it in the pinned baseline with 1 CPU and 2 GiB, with standard input from `/dev/null`:
   - the `I_InitGraphics` line starts at byte offset 3,394,651 of 3,553,934 bytes of output;
   - the frame appeared 2.8 s after start;
   - the frame is byte-identical to the reference's.
   So it lies between the old 1 MiB bound and the new 12 MiB one, and should pass both graders. I also ran it through SecureBench (`securebench run`, scripted harness, 1 CPU, 2048 MiB, 10240 MiB): `passed`, admitted, not dirty, the Output Artifact `present`, and similarity 0.957128497753268. That confirms the new Output Artifact path end to end. `mutant-silent-stdout` is now described as aimed at the substring check, which is what it tests. The other candidates are unchanged and remain as checked in my first review. There are five mutants and two attacks, within the limits.
8. **Divergences from native.** `qualification.json` (2026-10-25) reports `problems: []`. Every SecureBench run is admitted, rejudged and not dirty, and records pack digest `sha256:5f7d0585...b1b`, the digest I noted, and one worker record. The runs come from two framework commits, `1fbb0baa` (`reference`, `null`) and `84120d22` (the rest). Their `securebench`, `securebench_utility` and `securebench_relay_proxy` trees are identical to each other and to `HEAD` (`git rev-parse <commit>:<dir>`).
   - Verdicts: the reference and `mutant-verbose-read` pass both graders. The null candidate and the other four mutants fail both, so no mutant diverges. `mutant-verbose-read` agrees with my own probe and run.
   - The two divergences are both attacks: native 1.0, SecureBench `failed`/`oracle`. Both explanations hold:
     - `attack-stale-frame` depends on a `/tmp/frame.bmp` left in the agent's container, which `node vm.js` never writes.
     - `attack-replace-elf` interprets nothing and depends on the replaced input file. Its entry correctly says that only this path is closed.
   - Native results for unchanged scripts are marked `native_cached`. `mutant-verbose-read` ran natively this time.
9. **Inventory.** The note proposed under "Inventory note" matches the pack (one case, a 12 MiB output bound, the run-time-load cost of the ELF exclusion). The row now in `conversions/inventory.tsv` (line 18) still describes the removed seeded cases. The coordinator has to replace it. No exclusion reason applies.

Upstream assertions: all are mapped, as in my first review. The `I_InitGraphics` substring assertion now reads the Output Artifact, with the 12 MiB bound listed as stricter. None is dropped.

Findings of the previous review:
- **1. No mutant at the output bound: fixed.** The output moved to an Output Artifact with a 12 MiB bound, and `mutant-verbose-read` exercises the region the old bound would have cut off. My probe and SecureBench run confirm its claims. The remaining stricter case, more than 12 MiB before the line within 30 s, is listed under "Output bounds".
- **2. Standard input not listed: fixed.** It is now under "Fidelity changes" as "Standard input (equivalent)", with a reason, and in the adapter's docstring. I checked the claim about the reference: `read` on fd 0 writes a fixed `"Test input\n"` and never touches the real standard input.
- **3. Wording on the ELF exclusion: fixed.** "Scope", the `attack-replace-elf` entry and the `task.toml` comment now say exactly what is closed (one delivery path of the public-answer renderer, and a rebuilt ELF loaded at run time) and what is not.
- **4. Inventory row:** still out of date, for the coordinator (point 9).

Findings:
- None in the conversion. The inventory row is for the coordinator (point 9).

Verdict: approved
