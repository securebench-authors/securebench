# path-tracing-reverse

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/path-tracing-reverse

## The conversion in short

The baseline holds `/app/mystery`, a static binary built with `gcc -static -O3` from a small ray tracer (upstream `environment/orig.c`, deleted from the image). It takes no input and writes an 800x600 P3 image to `image.ppm` in its working directory. The agent must write `/app/mystery.c`, a C program of under 2 KB compressed that does the same. Upstream's three tests (`tests/test_outputs.py`) check that the file exists, that it compiles and is small enough, and that its image is close enough to the one `/app/mystery` writes when the tests run.

The pack has three checks.

- **`source`** (artifact check). It reads `/app/mystery.c` from the candidate with the `text` parser, at most 16 MiB. `hidden/oracle.py` recomputes upstream's compressed size.
- **`original`** (artifact check). It reads `/app/mystery` from the candidate. The Oracle requires its SHA-256 to be the baseline binary's (`hidden/expected.json`). Upstream renders its reference image with whatever `/app/mystery` holds when the tests run; with the baseline's binary, that image is the one stored in `hidden/original-rgb.zlib`.
- **`render`** (protocol check, one case). `evaluation/adapter.py` (standard-library Python on the stock interpreter) runs in a networkless Evaluation environment and repeats upstream's steps. It reports whether `/app/mystery` is executable, deletes it and any `/app/reverse`, and compiles with upstream's command in `/app`, with every other file the candidate left there present. It then deletes every entry of `/app` except the built binary, which stands in for upstream's empty chroot, and runs the binary with `/` as its working directory. It decodes `/image.ppm` as Pillow's PPM plugin does and returns the values `np.array` would hold, zlib-compressed and base64-encoded. It compares nothing. The Oracle repeats upstream's similarity arithmetic against the original image.

## How upstream's tests map to checks

Upstream has no regression tests; all three tests check what the task asks for. One row per assertion, explicit or implicit (a call that raises fails the test as an assertion does):

| Upstream (`tests/test_outputs.py`) | Check and case | How |
|---|---|---|
| `test_image_c_exists`: `assert image_c_path.exists()` | `source` | the file must be present; a symlinked `mystery.c` fails (fidelity changes) |
| `test_image_compiles`: `os.rename("mystery", "/tmp/mystery")` raises if `/app/mystery` is absent | `original` | `/app/mystery` must be present, and must be the baseline's binary (fidelity changes) |
| `test_image_compiles`: `Path("/app/reverse").unlink(missing_ok=True)` raises on a directory | `render` | the adapter unlinks it the same way; a failure is `unable` (`prepare_failed`), which fails the case |
| `test_image_compiles`: `assert result.returncode == 0` for `gcc -static -o /app/reverse /app/mystery.c -lm` in `/app` | `render` | the adapter runs the same command in `/app` with the baseline's `/usr/bin/gcc`; `judge` requires `compile.ending == "exited"` and `exit_status == 0` |
| `test_image_compiles`: `assert len(zlib.compress(open("/app/mystery.c").read().encode())) < 2100` | `source` | `compressed_size` decodes strict UTF-8, applies Python's universal-newline translation, re-encodes and compresses at zlib's default level; `judge` requires `< 2100` |
| `test_image_similarity`: `subprocess.run("cd /tmp; ...; cp mystery /jail_orig/; chroot /jail_orig /mystery; cp /jail_orig/image.ppm /app/original.ppm", check=True)` | `original`, `render` | with the baseline's binary, which `original` requires, this writes the image in `hidden/original-rgb.zlib`; `cp` keeps the file's mode, so the chroot runs it only if it is executable, which `render` requires (`original_executable`) |
| `test_image_similarity`: `Image.open("/app/original.ppm")` and `np.array(original)` | `render` (context) | the stored values are what Pillow 11.2.1 decodes from that image (differential, `original.ppm`: similarity exactly 1.0) |
| `test_image_similarity`: `subprocess.run("mkdir -p /jail_clean; cp /app/reverse /jail_clean/; chroot /jail_clean /reverse; cp /jail_clean/image.ppm /app/image2.ppm", check=True)` | `render` | the binary runs alone in an emptied `/app`, with `/` as its working directory; its exit status is ignored, as upstream checks only the last `cp`; the run must end within the time budget; `/image.ppm` must exist and be a regular file |
| `test_image_similarity`: `Image.open("/app/image2.ppm")` and `np.array(reconstructed).flatten()` | `render` | the adapter decodes every header Pillow's PPM plugin reads (P1 to P6, Pf, PyP, PyRGBA, PyCMYK, P0CMYK) as Pillow 11.2.1 does, including its errors, and reports the mode, size and array values; other formats fail (fidelity changes) |
| `test_image_similarity`: the division by 255.0, the two norms and `original_norm * reconstructed_norm`, which numpy broadcasts when one array has one value and refuses for any other length mismatch | `render` | `judge` requires the image to have 1 value or as many as the original; `similarity` repeats the arithmetic in numpy's order and precision: float64 for integer and boolean arrays, float32 for a float image, numpy's pairwise summation, IEEE division by zero |
| `test_image_similarity`: `assert similarity >= 0.995` | `render` | `judge` requires `score >= 0.995`; NaN fails and infinity passes, as in numpy |

Every upstream assertion has a check. Where a check differs from upstream, the difference is listed under fidelity changes.

### Expected values

All expected values are in data files under `hidden/`; `oracle.py` holds only upstream's two thresholds and numpy's block size.

- `hidden/original-rgb.zlib` holds the 1,440,000 RGB values of the image the baseline's `/app/mystery` writes, compressed with zlib. `hidden/derive.py` documents how to redo it: run `/app/mystery` in the pinned baseline with no network, then decode its P3 file. The program reads no input, so this image is the only one upstream compares against while `/app/mystery` is the baseline's. The `image.ppm` we used has SHA-256 `0d115b98f899dbfafed4a3e57c62a7182d6639861bb73d6965ec956a27d94ea7`, and we rendered it again for this remediation with the same hash. The reference's image is byte-identical to it.
- `hidden/expected.json` holds the SHA-256 of the baseline's `/app/mystery`, `869eebc7779f565fafcaae5c4c366c8d86bd5d21d9a8d1389d34fc67c09911de` (`docker run --rm --network none <baseline> sha256sum /app/mystery`).

### Differential test

The adapter replaces Pillow's PPM decoder and `np.array`. The Oracle replaces numpy's arithmetic and the verifier interpreter's zlib. `hidden/differential.py` compares both ends, each step in a container with no network and a memory limit:

1. `corpus` builds 116 images (two of them renders of reference variants with no shadow and with the sun's direction negated), 55 sources and 304 float32 arrays.
2. `native` runs upstream's code verbatim on Python 3.13.17 with Pillow 11.2.1 and numpy 2.3.1: `test_image_similarity` from `Image.open` to the assertion, `len(zlib.compress(open(path).read().encode()))`, and `np.sum` of each float32 array.
3. `ours` runs on the stock interpreter (Python 3.12.15, zlib 1.3.1). It opens each image as the adapter does, runs the adapter's `decode`, and calls the Oracle's `judge` on the observation the adapter would send. For each source it runs the registry's `text` parser and `compressed_size`, and for each array `pairwise_sum` with float32 rounding.

Results (every similarity compared as an exact hex float):

| Files | Upstream | SecureBench |
|---|---|---|
| the original; as P6; P3 with CRLF, mixed whitespace, header comments, a comment on every line, a 3 MB comment, a comment that joins a token's halves, no final newline, a final comment, trailing data; tokens `+0159`, `2_55`, 10 characters, `-0`; P3 and P6 with maxval 100, 254, 256, 1000, 65535 | pass, 1.0 to 0.99998883 | same floats |
| the same 1,440,000 values in other shapes and modes: 600x800 P6, 1200x400 P3, 2400x600 P5 and P2 (maxval 255, 100, 1000, 65535), PyP 2400x600, PyRGBA, PyCMYK and P0CMYK 600x600, Pf 800x1800 little- and big-endian, scaled by 1/3.7 and by 1e-20 | pass, 0.99998883 to 1.00000001 | same floats |
| single values numpy broadcasts: P1 `0`, P4, P2, P5 (maxval 255, 100, 1000, 65535), PyP, Pf 1.0 | pass, 1097.24506742 | same floats |
| a 1x1 Pf of 1e-30, whose float32 square underflows to 0, so the image is divided by a zero norm | pass, infinity | pass, infinity |
| reference variants: no shadow 0.99705572 passes, sun direction 0.99376359 fails; 16 images darkened to straddle 0.995, as P6 and as Pf | identical verdicts and floats | identical |
| a 900x1600 bitmap of the original, P1 and P4 (padded rows), 0.96024917; P3 and P6 with maxval 1; a gray image; Pf negated, Pf scaled by 1e18 (float32 overflow, 0.0) | fail | fail, same floats |
| zero norms and NaN: all black, P1 `1`, P2 `0`, Pf 0, Pf infinity, Pf with one NaN | fail, NaN | fail, NaN |
| lengths numpy cannot combine: 1x1 RGB, 640x480 RGB, 2000x1000 gray; 1500x1500 gray (over the adapter's 2,000,000-value bound) | fail (`ValueError`) | fail |
| bad data and headers: truncated P3, P6, P5, P5 maxval 1000, P4, Pf; bad P1 token; over maxval, negative, `0x9f`, 11-character tokens, CR-ended comments; maxval 0 and 65536, width 0, `P3800`, end of file in the header, Pf scale 0, `inf` and `one`; P7, an empty file, a one-byte file | fail (`ValueError`, `OSError`, `UnidentifiedImageError`) | fail |
| **the original as PNG content in `image.ppm`** | **pass, 1.0** | **fail** (`not_ppm`) |
| 53 sources: 10 prefixes of `orig.c` that compress to 2,096 to 2,102 bytes, each also with CRLF, lone CR, `\r\r\n` and a non-ASCII character; the reference, `orig.c`, the reference with a NUL byte | identical sizes | identical |
| invalid UTF-8 | fail (`UnicodeDecodeError`) | fail (unparsable) |
| **a UTF-8 byte-order mark before the reference** | **pass, 1,436** | **fail** (unparsable) |
| 304 float32 arrays (every length from 1 to 300, then 1,000, 4,096, 100,003 and 1,440,000) | `np.sum` | `pairwise_sum(..., float32)`: all 304 bit-identical |

The two verdicts that differ are listed below. The Oracle itself runs on the host's Python 3.12.15 with zlib 1.3.2: its float arithmetic is the same IEEE arithmetic, and `compressed_size` there gives upstream's size for all 54 sources that decode. To redo the test, follow the docstring of `hidden/differential.py`.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **`/app/mystery` must stay the baseline's binary (stricter).** Upstream renders its reference image at grading time with whatever `/app/mystery` holds. A candidate that replaces it with a program writing a plain gray image, and writes that same program as `mystery.c`, gets similarity 1.0 there (`attack-replace-mystery`). Here the `original` check requires the baseline's bytes and `render` the executable bit, and the image comes from `hidden/`. A candidate that deletes, moves or breaks the binary fails both graders (`mutant-delete-mystery`), as upstream's `os.rename` or its chroot run fails. The difference: a candidate that changes the binary without changing what it writes (for example `strip /app/mystery`) passes upstream and fails here. Changing the binary is changing the instrument that grades the candidate, and we know of no reason a solution would do it.
- **No copy of the original at `/tmp/mystery` during the build (stricter).** Upstream moves `/app/mystery` to `/tmp/mystery` before it compiles, so a `mystery.c` can embed the original at compile time (for example with `.incbin "/tmp/mystery"`), write it out inside the chroot and run it, against "must not invoke ./mystery". The adapter deletes `/app/mystery` and keeps no copy, so that program fails here. This closes only that route. Neither grader enforces "must not invoke ./mystery" against a copy the agent made itself: an agent that copies `/app/mystery` to a top-level file such as `/app/.r` and writes a `mystery.c` that embeds it with `.incbin "/app/.r"`, writes it out at run time and executes it passes upstream (the build sees `/app/.r`, and the static copy runs inside the chroot) and passes here (the review ran it: `passed`, similarity 1.0, compressed size 229). Closing it would add a check upstream does not have. `attack-invoke-mystery` fails in both graders only because it executes the copy from `/app` at run time, where the chroot, and here the emptied `/app`, no longer hold it.
- **Upstream's chroot directory is not captured (stricter).** Upstream runs `mkdir -p /jail_clean`, which keeps whatever the agent left there. A candidate that renders the original into `/jail_clean/image.ppm` during the agent phase, with a `mystery.c` that writes nothing, is compared with the stale image and passes upstream with similarity 1.0 (found by the earlier review). A `mystery.c` that reads data files placed in `/jail_clean` passes there too. `/jail_clean` is outside the scope, so here the run sees neither, and both fail.
- **The program's image must be a regular file (stricter).** Upstream copies `image.ppm` out of the chroot with a `cp` that runs outside it and follows symlinks. A program that leaves `image.ppm` as a symlink to `/app/original.ppm`, where the test has just copied the original's image, is compared with that image and passes upstream (`attack-symlink-original`). The adapter opens `/image.ppm` without following symlinks and requires a regular file, so a program whose `image.ppm` is a symlink to an image it wrote itself also fails here. We know of no reason a solution would write one.
- **The run sees the baseline filesystem (more lenient, negligible).** Upstream's chroot holds only the binary (and what the agent left in `/jail_clean`, previous bullets). Here `/app` is emptied before the run, so the program sees none of the agent's files and not the original, but it sees the rest of the baseline (`/bin/sh`, `/etc`, `/proc`, `/dev`). A program that needs one of those passes here and fails upstream; neither the original nor any program that reproduces it needs them. The binary runs as `/app/reverse` instead of `/reverse`, with `/` as its working directory as in the chroot, so `image.ppm` and `/image.ppm` both land at `/image.ppm`.
- **Image formats (stricter).** The adapter reproduces Pillow's PPM plugin, which reads every file a PPM writer produces, and fails any other file. Upstream's `Image.open` identifies the format by content, so it also accepts the original's pixels written as PNG, BMP, GIF, TIFF, JPEG or any of Pillow's other formats under the name `image.ppm` (the PNG case scores 1.0 upstream). The Evaluation has no Pillow, and adapters are standard-library Python, so we could not reproduce Pillow's decoders for these formats, several of which run C libraries bundled with Pillow (libjpeg-turbo, libwebp, OpenJPEG, libtiff). Shipping Pillow and numpy wheels in `evaluation/` would remove this difference. A C program under 2 KB that writes another image format is unlikely.
- **Observation size (stricter, negligible).** One observation is at most 4 MiB. Integer images fit at any content: 1,440,000 values take at most 2,880,000 bytes before base64. A float (Pf) image with 1,440,000 values takes 5,760,000 bytes, so it fits only if zlib compresses it enough; the Pf images of the differential do. A Pf image whose values do not compress fails here with class `case_error` and could pass upstream.
- **Byte-order mark and a symlinked `mystery.c` (stricter, negligible).** The `source` check reads the candidate's file directly, as artifact checks do, and that reading accepts only a regular file, and the `text` parser rejects a file that starts with a UTF-8 byte-order mark. gcc skips the mark and follows a symlink, and upstream's size check counts the mark as one character and reads through the symlink, so both pass there. We know of no reason a solution would do either.
- **Files a `mystery.c` can include (stricter, negligible).** The build sees every top-level file the candidate left in `/app`, as upstream's does (`mutant-include-source`). It does not see files below a directory of `/app`, which the scope excludes, or files outside `/app`, which are not captured. So a `mystery.c` that includes such a file fails here and passes upstream.
- **Similarity, compressed size and image decoding (equivalent).** These are reimplemented, and the differential test above shows identical floats and sizes and identical verdicts, except for the formats and the byte-order mark in the bullets above.
- **Time (equivalent).** Upstream bounds only its whole verifier, at 1,800 s. That budget also covers installing uv, Python and the test libraries, compiling, and rendering the original (about 1 s). Here the compile and the run share 1,740 s, and the case timeout is 1,800 s. The reference compiles and renders in about 2 s.
- **Grading tools (equivalent).** The baseline has no Python. Upstream's verifier installs Python 3.13, pytest, Pillow and numpy from the network at grading time. Here the adapter runs on the stock interpreter. gcc is the baseline's `/usr/bin/gcc` (13.3.0), outside the scope, as upstream uses it.
- **Scope (equivalent, apart from the points above).** One root, `/app`, which holds the deliverable `/app/mystery.c` and the binary `/app/mystery`. The root excludes `*/*`, so everything below the top level of `/app` is dropped. Agents can then keep work trees there (disassembly, virtual environments with absolute symlinks) without failing capture. Internal symlinks are allowed. Upstream keeps no test files in the image, because they are mounted at `/tests` only at grading time, so there is nothing to exclude. Files written outside `/app`, such as a `/conftest.py` that rewrites pytest's reports, are not captured.
- **A symlink that leaves `/app` fails capture (stricter).** Capture never follows symlinks, and a symlink at the top level of `/app` that points outside the scope (for example `/app/venv -> /opt/venv`) fails the candidate with class `capture`. Upstream has no capture step, so such an agent can pass there. This is the platform's capture rule, which no pack setting changes: a symlink that leaves the scope would point the replayed candidate at files outside what was captured. Symlinks below a top-level directory of `/app` are excluded with everything else there, so they never fail capture, and an agent that keeps its work trees in a subdirectory is not affected.
- **Allowed domains (stricter).** None, which is all the reference needs. Upstream allows the Internet, so an agent there can install gdb, Python or a decompiler with apt. Here it has the baseline's tools: gcc, objdump, readelf, nm, strings, od and perl. These are enough to disassemble and reproduce the program.
- **Cases (equivalent).** One case, as upstream's tests build and run the program once. The program reads no input.

## Divergences from native

From `qualification.json`: no problems, every SecureBench run admitted and reproduced by `rejudge`, one pack digest (`sha256:9e64f3fe...3c35`), clean SecureBench code. The runs record two framework commits, `cd0b7a2` and `d7038d6`, because the coordinator committed a ledger note while qualify ran; nothing under `securebench/` changed between them. The reference passes both graders, and the null candidate fails both. `mutant-one-pixel` and `mutant-include-source` pass both (native 1.0); `mutant-sun-direction`, `mutant-readable-source` and `mutant-delete-mystery` fail both (native 0.0). `attack-invoke-mystery` fails both. Two attacks get native 1.0 and SecureBench `failed` (`oracle`):

- **`attack-replace-mystery`: native 1.0, SecureBench `failed`.** Upstream renders its reference image with the agent's `/app/mystery`, which writes the same plain gray image as `mystery.c`, so the two images are equal. Here the `original` check finds a binary that is not the baseline's. SecureBench is right: the program reverses nothing, and the candidate replaced the instrument that grades it.
- **`attack-symlink-original`: native 1.0, SecureBench `failed`.** Upstream's last `cp` runs outside the chroot and follows the symlink the program left, to the original's image at `/app/original.ppm`, so it compares the original with itself. Here `/image.ppm` is not a regular file (`not_regular`). SecureBench is right: the program writes no image.

## Mutants that caught additions

Before remediation, no mutant passed natively and failed in SecureBench: all five got native 0.0 and SecureBench `failed`, so none needed rerunning (`git show HEAD:conversions/terminal-bench/path-tracing-reverse/qualification.json`). Two earlier attacks did: they passed natively and SecureBench failed them because of additions. They are mutants now, and we ran them once against the remediated pack:

| Candidate | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `attack-one-pixel`, now `mutant-one-pixel` | 1.0 | `failed` (`not_rgb`: only P3 and P6 were decoded) | `passed`, similarity 1097.245 |
| `attack-include-source`, now `mutant-include-source` | 1.0 | `failed` (the adapter deleted `render.c` before the build) | `passed`, similarity 1.0 |

## Candidates

- `reference.sh`: upstream `solution/solve.sh`, which writes `mystery.c` in the working directory. It drops upstream's canary comment, a `#!/bin/bash` line that is not on line 1 and so has no effect, and the template's comment lines, and it starts with `#!/bin/sh` and `cd /app`. The heredoc is unchanged.
- `null.sh`: changes nothing.
- `mutant-sun-direction.sh` (similarity arithmetic): the reference with the sun's x component negated, a sign error a decompiled constant invites. Upstream scores it 0.99376, just under the threshold.
- `mutant-one-pixel.sh` (decoder and broadcasting): `mystery.c` writes a 1x1 grayscale PGM, which numpy broadcasts to a similarity of about 1097. Both graders should pass it.
- `mutant-readable-source.sh` (compressed size): upstream's `environment/orig.c`, copied beside the script as `orig.c`. It renders the original exactly but compresses to 2,713 bytes.
- `mutant-include-source.sh` (the build): `mystery.c` is `#include "render.c"`, and `/app/render.c` is `orig.c`. Upstream measures only `mystery.c`, so both graders should pass it.
- `mutant-delete-mystery.sh` (the `original` check): the reference, then `rm /app/mystery`. Upstream's `os.rename` fails.
- `attack-replace-mystery.sh`: replaces `/app/mystery` with a static program that writes a plain gray 800x600 image, and writes the same program as `mystery.c`.
- `attack-invoke-mystery.sh`: copies `/app/mystery` to `/app/.renderer`, and `mystery.c` runs it with `execl`. Aimed at the emptied `/app` that stands in for upstream's chroot.
- `attack-symlink-original.sh`: `mystery.c` leaves `image.ppm` as a symlink to `/app/original.ppm`, which upstream's `cp` follows outside the chroot.

`mutant-sun-direction.sh` runs `reference.sh`, edits one line with `sed`, and deletes `mystery.c` if the edit did not apply, so it can never silently become the reference. Upstream rates some plausible variants as correct, and the differential confirms SecureBench agrees: no shadow scores 0.99706 in both. It is not a mutant, because by upstream's threshold it is correct.

## Remediation

This pass brought the conversion in line with the current converter brief: upstream's assertions only, with the protections against tampering kept.

Removed (additions that failed candidates upstream passes because of what they compute):
- `hidden/oracle.py`: the requirement that the image be 800x600 and RGB. The Oracle now requires what upstream's numpy arithmetic requires: as many values as the original, or one value, which numpy broadcasts.
- `evaluation/adapter.py`: the `not_rgb` problem. The adapter decodes every header Pillow's PPM plugin reads, not only P3 and P6, and reports the values `np.array` holds for each mode.
- `evaluation/adapter.py`: the deletion of every file in `/app` but `mystery.c` before the build. Upstream compiles with the agent's files present; the adapter now deletes only `/app/mystery` (a protection, kept) and `/app/reverse` (as upstream), and empties `/app` after the build, before the run.
- `evaluation/adapter.py`: the 64 MiB bound on the image file and the 800x600-pixel bound. The adapter now reads the file as a stream, as Pillow does, and bounds only the number of values (2,000,000), above which upstream fails anyway.
- The sections "Answer already public upstream" and the fidelity changes that described the removed additions ("The build and the run see only `mystery.c`", "Image format and size", "Reading `image.ppm`", "No hidden cases").

Restored:
- Upstream's use of `/app/mystery` at grading time. The earlier pack ignored the binary's state, which let a candidate that deleted it pass ("The original binary need not survive", more lenient). The new `original` check and the executable bit in `render` require it to be the baseline's binary, which keeps the protection against a replaced reference and makes deletion fail as upstream does.

Kept: the scope and its excludes, the hidden original image, the adapter's isolation of the run (now after the build), the regular-file read of `image.ppm` (now also documented as the protection against `attack-symlink-original`), the Oracle's safety rules and the reimplemented similarity and size.

Moved: the original's 800x600 size left `oracle.py`; the binary's SHA-256 is new in `hidden/expected.json`. `oracle.py` now holds only upstream's thresholds and numpy's block size.

Candidates:
- Deleted `attack-conftest.sh`: it is not aimed at this task, and three attacks that are fill the limit; the scope still drops a planted `/conftest.py`.
- Deleted `attack-stale-image.sh`: its route (`/jail_clean`) is closed by the scope alone, with no code of the pack involved; the other three attacks test code. The fidelity change stays recorded.
- `attack-one-pixel.sh` and `attack-include-source.sh` became `mutant-one-pixel.sh` and `mutant-include-source.sh`: they do not tamper with grading, upstream passes them, and the remediated pack now passes them too. They test the decoder, the broadcasting and the build, where the conversion's check is least like upstream's.
- Deleted `mutant-no-checkerboard.sh`, `mutant-upside-down.sh` and `mutant-wrong-resolution.sh`: their images score far from the threshold (0.976, 0.743) or have a length numpy cannot combine, so they test less than the new mutants within the limit of five. The differential covers those cases.
- Added `mutant-delete-mystery.sh` for the restored `original` check, and `attack-symlink-original.sh`, a route against upstream's grading that the earlier conversion did not record.
- `attack-invoke-mystery.sh` and `attack-replace-mystery.sh` are kept; `reference.sh`, `null.sh`, `mutant-sun-direction.sh` and `mutant-readable-source.sh` are unchanged.

## Fixes after the review

- The Oracle bounded its work only by the image size the observation claims: an observation the schema admits (55,000 x 55,000, mode L) inflated to 3,025,000,000 bytes, which the review's container ran out of memory on. `_values` now rejects any value count other than 1 or the original's before it decodes or inflates anything, so the inflation is bounded by the original's size. The same crafted observation now fails at once, in a container limited to 1 GiB, and the differential's `ours` step gave the same results as before.
- The bullet on the original during the build now says that only the `/tmp/mystery` route is closed, and that neither grader stops an agent from embedding a copy it made itself.
- The capture rule for symlinks that leave `/app` is now its own bullet, labelled stricter, with its reason.

## Inventory

Proposed note: `Remediated: upstream's assertions only. Stricter: /app/mystery must stay the baseline's binary (the reference image comes from hidden/); image files other than PPM fail (no Pillow in the Evaluation).`

## Review before remediation

Reviewer: a7d244e93cd538460 (conversion-reviewer), 2026-10-11 (second round)

Pack digest reviewed: `sha256:4a3e54e282821a2ec7adf30e7ad2be52e260929a49d08c145757c49a56758c45` (`securebench validate`, unchanged since the first round and at the end of this one). The pack did not change between the rounds. The fixes changed `CONVERSION.md` and added `candidates/attack-stale-image.sh`.

The findings of the first round:
- **Finding 1 (the original binary need not survive): fixed.** It now has a table row and a bullet labelled more lenient, with a reason that holds: the binary is the measuring instrument, not a deliverable, and the instructions never ask the agent to keep it. The bullet cites a native probe (0.0, `FileNotFoundError`) and my SecureBench run of `reference.sh` plus `rm /app/mystery` (`passed`). "No upstream assertion is dropped" is replaced with an accurate statement.
- **Finding 2 (`/jail_clean`): fixed.** It now has a table row and a bullet labelled stricter. The claim about the chroot is qualified. `attack-stale-image.sh` is added and is listed with the closed weaknesses. Qualification confirms the native 1.0 that I predicted from upstream's code, and SecureBench `failed`.
- **Finding 3 (`/tmp/mystery` and `.incbin`): fixed** in the bullet on the build seeing only `mystery.c`, labelled stricter.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. One root `/app` that excludes `*/*`, with internal symlinks allowed. Every solution the instructions allow is a single `/app/mystery.c`, which is captured. The stricter cases (an include beside `mystery.c` or outside `/app`, a symlinked `mystery.c`, files left in `/jail_clean`) are listed and labelled. Capture prunes excluded subtrees before counting them (`securebench_utility/utility.py:236`). C has no convention-loaded test files, and upstream mounts its tests only at grading time (lesson C49).
3. Expected values. I inspected the baseline by digest:
   - `/` and `/app` hold only `/app/mystery`.
   - A `find` for `*.ppm`, `*.pgm`, `orig*` and `mystery*` finds nothing else.
   - `orig.c` is removed in a later layer and is absent from the merged filesystem.
   
   The expected image is only in `hidden/original-rgb.zlib` and in the host-side context. I re-derived it in the pinned baseline with no network. The SHA-256 of `image.ppm` matches `0d115b98...4ea7`, and its decoded values equal the stored 1,440,000 bytes. The Evaluation deletes `/app/mystery` before the compile.
4. Challenges. The single challenge is `{}` (at most 16 bytes). The original image is only in the context, on the host.
5. Hidden cases. There is no public example and no input, so there is nothing a case could vary. The public answer is recorded (lesson C58).
6. Oracle. `judge` checks the following, in order:
   - the compile's ending and status;
   - that the run is present and ended;
   - that the image decoded with no problem;
   - the magic, 800x600, exactly 600 rows of 4,800 hex characters, and the decoded length;
   - only then, the similarity.
   
   The source check requires a present text file and a compressed size under 2,100. There are no counted items. The work is bounded and fixed at 1,440,000 values. There are no regular expressions, and no evidence is used as a path or as code. I checked the reimplementations independently with upstream's versions (Python 3.13.9, numpy 2.3.1, Pillow 11.2.1):
   - `numpy_sum` equals `np.sum` on 307 array lengths;
   - `similarity` equals upstream's expression bit for bit on 12 perturbed images;
   - the adapter's `decode` and Pillow agree on all of 40,000 fuzzed P3 and P6 files.
7. Mutants and attacks. Five mutants run real code, each with a guard against an edit that did not apply. Each targets a requirement: the sun's sign near the threshold, the checkerboard, the flip, the resolution, and the size limit. Six attacks each target a real weakness: the broadcasting, the replaced reference binary (lesson C48), an include beside `mystery.c`, invoking the original, a stale `/jail_clean` image, and `conftest.py` (lesson C49). SecureBench gives every mutant and attack `failed` with class `oracle`, never `invalid` (lesson C72).
8. Divergences from native. `qualification.json` has two rounds and `problems: []`. Every SecureBench run is admitted and reproduced by `rejudge`. Every run records pack digest `4a3e54e2...8c45`, worker record `7802f6dc...b9df`, and clean SecureBench code at `9c7e84f`. The reference passes both graders. The null candidate, the five mutants and `attack-invoke-mystery` fail both. Five attacks get native 1.0 and SecureBench `failed`: `one-pixel`, `replace-mystery`, `include-source`, `stale-image` and `conftest`. Each explanation matches the mechanism I verified in upstream's code and in my own runs, and SecureBench is right in each case. The note on a superseded qualification, in which native gave `attack-one-pixel` 0.0, is disclosed openly. The 0.0 is consistent with upstream's `test.sh`, which writes reward 0 when `uvx` cannot fetch its tools. It does not affect the committed record, where both rounds agree.
9. Inventory. There is no row yet, and the coordinator adds it. It should be `converted`. No exclusion reason holds for every conversion: the chroot is only upstream's grading mechanism, nothing needs network at evaluation, there is no speed target, and the task fits 1 CPU and 2 GiB.

Upstream assertions:
- `test_image_c_exists` maps to `source`.
- The compile's return code maps to `render.compile`.
- The compressed size maps to `compressed_size`, with identical sizes in the differential.
- The `cp` of `image.ppm` and the 0.995 cosine map to `render`.
- The two implicit conditions, a surviving `/app/mystery` and a reused `/jail_clean`, are listed as more lenient and stricter, with reasons.

Every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (session bdda55d6), 2026-10-25 (second round)

Pack digest reviewed: `sha256:9e64f3fe6a263714dcaa6a13ae09767c4185e4b1235f2050eca89274d7d03c35` (`securebench validate`, the same at the start and the end of this round). The first round reviewed `sha256:76588de8...6980`. Between the rounds the pack changed in `hidden/oracle.py` only (`_render` and `_values`), and `CONVERSION.md` changed in the bullets the findings named, in "Divergences from native" and in the new "Fixes after the review".

The findings of the first round:
- **Finding 1 (unbounded inflation in `_values`): fixed.** `_values` now receives the original's length from `_render` and rejects any count other than 1 or that length (line 250) before it decodes base64 or inflates, so inflation is bounded by `size + 1` with `size` at most 5,760,000 bytes. I reran my crafted observation (55,000 x 55,000, mode `L`, 3,920,216-byte `values`) in a container limited to 1 GiB: it fails at once with "image and original do not combine". The same bomb payload claimed as 1200 x 1200 (the original's count) fails with "image values do not match its size" in 0.01 s, as `decompress` stops at `size + 1`.
- **Finding 2 (embedding an agent-made copy): fixed.** The bullet is renamed "No copy of the original at `/tmp/mystery` during the build", says that only that route is closed, describes the `.incbin "/app/.r"` route and that it passes both graders, and explains why `attack-invoke-mystery` fails. That is accurate: my run passed here, and by upstream's code the build sees `/app/.r` and the static copy runs inside the chroot.
- **Finding 3 (unlabelled capture difference): fixed.** "A symlink that leaves `/app` fails capture (stricter)" is its own bullet, with its reason, and the scope bullet no longer carries it.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. Unchanged since the first round: one root `/app` excluding `*/*`, so only top-level entries are captured, `/app/mystery.c` among them; no convention-loaded test files exist and upstream mounts its tests at grading time; the baseline's `/app` holds only `mystery`, with no symlinks. The capture rule for outward symlinks is now labelled stricter.
3. Expected values. Unchanged: the baseline has no image, `orig*` file or `/.securebench`, and `/app/mystery` has SHA-256 `869eebc7...11de` as `hidden/expected.json` says. My re-render in the baseline (`image.ppm` `0d115b98...4ea7`) decodes to the 1,440,000 values of `hidden/original-rgb.zlib`. `evaluation/` holds no expected value. Allowed domains are empty.
4. Challenges. The one challenge is `{}`.
5. Cases. One case, as upstream; the seed is unused.
6. Oracle. Expected values come only from `hidden/`; `oracle.py` holds upstream's thresholds and numpy's block size. `judge` checks every field it needs (executable bit, compile ending and status, run ending, image problem, mode, size, encoding, the count numpy can combine, similarity), ignores claims, uses no regular expression and no evidence as a path, and now bounds its work over candidate data before decoding (finding 1). The order change moves the count check before decoding without changing which observations pass.
7. Candidates. Unchanged since the first round. `reference.sh` is upstream's heredoc with `cd /app`; the five mutants run real code and are aimed at the threshold arithmetic, the decoder and broadcasting, the compressed size, the build with other files present, and the `original` check; the three attacks are specific to this task. In `qualification.json` every mutant gets the same verdict from both graders, and every attack gets SecureBench `failed` (`oracle`).
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run is admitted, reproduced by `rejudge`, made with clean SecureBench code, and records pack digest `9e64f3fe...3c35`, the digest I noted, and one worker record (`d9013d84...0453`). The runs record two framework commits, `cd0b7a2` and `d7038d6`; `git log cd0b7a2..d7038d6 -- securebench` is empty, so the SecureBench code is the same, as the record says. The reference passes both graders and the null candidate fails both. `mutant-one-pixel` and `mutant-include-source` pass both; the other three mutants and `attack-invoke-mystery` fail both. Two attacks get native 1.0 and SecureBench `failed`: `attack-replace-mystery` (the agent's replaced `/app/mystery` renders the reference image upstream; here the `original` check fails it) and `attack-symlink-original` (upstream's `cp` follows the symlink to `/app/original.ppm`; here `/image.ppm` is `not_regular`). Both explanations match the code of upstream's test and of the adapter, and SecureBench is right in both. Native results reused from the earlier qualification are marked `native_cached`, for candidates whose scripts did not change.
9. Inventory. `converted` is right; no exclusion reason holds for every conversion. The current row's note describes the pre-remediation pack; the proposed note in "Inventory" is accurate and should replace it.

Upstream assertions: every assertion of `test_image_c_exists`, `test_image_compiles` and `test_image_similarity` has a row in the mapping table and a matching check, and every fidelity change carries a label and a reason.

Findings:
- None.

Verdict: approved
