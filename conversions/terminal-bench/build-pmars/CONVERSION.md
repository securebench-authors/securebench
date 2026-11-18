# build-pmars

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/build-pmars

## How the pack grades

The agent builds pMARS from the Debian source package without X11, with the
source extracted under `/app` and the binary at `/usr/local/bin/pmars`.
Upstream's verifier (`tests/test_outputs.py`) has four test functions. The pack
has one protocol check, `upstream-tests`, with one case per test function. The
adapter (`evaluation/adapter.py`, standard-library Python on the stock
interpreter) performs the operations of one test as the test does and returns
the raw results: whether a path exists, each shell command's exit status and
standard output as bytes (base64), and the entries a glob under `/app` finds
with the probes the test makes on them. `hidden/oracle.py` applies the test's
assertions to those results; the literals it compares with (the address
threshold, the `Results:` label, the X11 library names) are in
`hidden/cases.json` with the challenges.

| Upstream test | Case | What the Oracle requires |
|---|---|---|
| `test_pmars_works` | 0 | `/usr/local/bin/pmars` exists; `echo -e 's\ns\ns\nq' \| pmars -e rave.red` and the same for `flashpaper.red` each give at least 2 matches of `\b(\d{5})\s+\w+\.\w+`; `pmars -b -r 50 -f flashpaper.red rave.red \| tail -n 1` matches `Results: \d+ \d+ \d+` at its start |
| `test_headless_no_x11` | 1 | `ldd /usr/local/bin/pmars` contains none of `libX11`, `libXt`, `libXext`, `libXaw` |
| `test_debian_source_used` | 2 | `/app` has an entry matching `pmars-*`, and the first one has a `debian` entry |
| `test_built_from_source` | 3 | the first `pmars-*` entry has a `src` entry, and `src/*.c` matches at least one entry |

Each command runs as upstream's `run_shell_command` runs it: `/bin/sh -c`
(dash in this image, so `echo -e` prints `-e` and the debugger's first command
is `-e s`, which it rejects before the two steps), in `/app`, with standard
input at `/dev/null` (pytest's fd capture) and only standard output captured.
The Oracle then does what `run_shell_command` does with the result: decode
strictly as UTF-8, translate `\r\n` and `\r` to `\n`, strip; on a non-zero
exit, keep the output if there is any and otherwise fail. The reference's
debugger commands exit with status 4 and pass through that branch, as they do
natively.

## Fidelity changes

- **Scope (stricter).** The roots are `/app` (the source tree and the
  warriors), `/usr/local` (the binary) and `/usr/lib/x86_64-linux-gnu` (shared
  libraries a build may link against that the baseline lacks, such as
  `libncurses.so.6`, and the C library that installing `build-essential`
  upgrades). Changes anywhere else are not captured. The rest of `/usr` is left
  out because apt creates absolute symlinks there that capture rejects: the
  reference alone creates 17 (`/usr/bin/cc -> /etc/alternatives/cc`,
  `/usr/lib/cpp -> /etc/alternatives/cpp`, ...), so a `/usr` root would fail
  every solution that installs a compiler. `/etc` cannot be a root (it holds
  protected paths). So a solution passes natively but fails here when its
  binary needs, at run time, something outside these roots: a library installed
  outside the default search directories and found only through
  `/etc/ld.so.cache`, or a symlink `/usr/local/bin/pmars` pointing into `/app`
  (capture rejects symlinks that are absolute or leave their root). The
  instructions ask to install the binary to `/usr/local/bin/pmars`, and the
  binary built as they describe needs only `libc.so.6`.
- **`tail` and `ldd` by absolute path (equivalent for every solution; stricter
  against `PATH` shadowing only).** Upstream runs `tail -n 1` and `ldd` through
  `PATH`, where `/usr/local/bin` comes before `/usr/bin`, so a candidate could
  shadow them with its own files there. The challenges run `/usr/bin/tail` and
  `/usr/bin/ldd`, the baseline's files, because `/usr/bin` is outside the
  scope. That is the only protection this gives. `/usr/bin/ldd` is a bash
  script, and bash, the dynamic loader `ldd` calls, and the libraries both of
  them load (`libtinfo.so.6`, `libc.so.6`, `ld-linux-x86-64.so.2`) come from
  `/usr/lib/x86_64-linux-gnu`, which is a scope root and has to be: the C
  library the reference upgrades lives there. A candidate can therefore change
  what `ldd` prints through those libraries, as it can natively; the reviewer
  showed it with a constructor library added to `libtinfo.so.6`. The X11 check,
  like upstream's, judges only what the candidate's environment reports. Its
  expected value (no X11 library names) is public, and a candidate can pass it
  on both graders without tampering anyway, for example with a small non-X11
  `/usr/local/bin/pmars` that execs an X11-linked binary. `pmars` is still
  resolved through `PATH`, as upstream does.
- **`PATH` (equivalent).** The adapter uses the image's `PATH`
  (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`) and
  `HOME=/root`. Natively the verifier also puts `/root/.local/bin` (where
  test.sh installs uv) and the uvx environment first; `/root` is a protected
  path that no scope can cover, and neither directory holds a `pmars`.
- **Each test in a fresh environment (stricter for some candidates, more
  lenient for others).** Natively the four tests run in file order in one
  container, so whatever `pmars` changes on the filesystem when
  `test_pmars_works` runs it is what the later tests see. Here each test is its
  own case in a fresh Evaluation environment, so those changes are lost. That
  is stricter for a `pmars` that, when it runs, repairs something a later test
  checks: it could replace `/usr/bin/ldd` to hide an X11 link
  (`attack-pmars-plants-ldd.sh`), which passes natively and fails here. It is
  more lenient for a `pmars` that breaks something a later test checks: one
  that deletes `/app/pmars-*/debian` or the `*.c` files when it runs fails
  `test_debian_source_used` or `test_built_from_source` natively, and passes
  them here. Neither is behavior the instructions ask for. Per-case isolation is
  what SecureBench requires (cases run in parallel and are judged alone), so
  the native order cannot be kept.
- **Regular expressions reimplemented (equivalent).** The Oracle may not use
  `re`, so the two patterns are matched by hand with the classes Python's `re`
  uses for str patterns (`\d` is `str.isdecimal`, `\s` is `str.isspace`, `\w`
  is `str.isalnum` or `_`), the address count follows `re.findall`
  (non-overlapping, left to right) and the results match is anchored at the
  start only, like `re.match`. We checked these against `re` (Python 3.12):
  the three classes agree on every code point; whitespace and word characters
  are disjoint, which the no-backtracking argument in the code relies on; and
  `findall` counts and `match` results agree on 300,000 random strings built
  from digits, ASCII and Unicode spaces, Unicode digits, letters, `.`, `_` and
  pieces of real debugger output, and on the reference's debugger output. The
  only possible difference is in characters assigned after the Unicode version
  of the Oracle's Python (native uses Python 3.13).
- **`run_shell_command` reimplemented (equivalent).** As described above. The
  adapter returns standard output as base64 so that non-UTF-8 output reaches
  the Oracle, which fails it as `check_output(text=True)` does natively.
- **First glob match (equivalent up to an unspecified order).** Upstream
  checks `source_dirs[0]`, the first entry `Path("/app").glob("pmars-*")`
  yields in directory order, which is not fixed. The Oracle takes the first in
  byte order of the name. Both agree whenever there is one match, as there is
  for the reference. The glob runs with the stock interpreter's `pathlib`
  (Python 3.12) instead of 3.13's; for `pmars-*` and `*.c` both match hidden
  and non-hidden entries of any type, case-sensitively. Names that are not
  UTF-8 are reported with backslash escapes, which changes only their sort
  position.
- **Output bounds (stricter).** Each command's standard output may be at most
  975,000 bytes and the whole observation 4 MiB; upstream has no bound. The
  reference prints about 5 KB for a debugger run. At most 1,000 `pmars-*`
  entries in `/app` are reported.
- **Timeout (equivalent).** Each case has 600 seconds; upstream has 900 for the
  whole verifier. The reference's cases take about 8 seconds.
- **Allowed domains (stricter).** Upstream allows the whole internet. The pack
  allows `deb.debian.org`, the only host the reference uses (the image's apt
  sources, the security suite and the `deb-src` line the instructions call
  for are all on it).
- **Drift repair in `reference.sh`.** Upstream's `solve.sh` pins
  `dpkg-dev=1.22.21`, and the Debian mirror now serves only 1.22.22
  (`apt-cache madison dpkg-dev` in the baseline: `1.22.22 |
  http://deb.debian.org/debian trixie/main amd64 Packages`). Native evidence
  that the unrepaired reference fails: on 2026-11-03 (19:00:30 to 19:01:35
  UTC) we ran the unmodified upstream task, `solution/solve.sh` included, with
  Pier 0.3.1 and its oracle agent (`pier run -p build-pmars --agent oracle -n 1
  --no-delete`) on the campaign worker. `solve.sh` exited at the
  `apt-get install` with

  ```
  Package dpkg-dev is not available, but is referred to by another package.
  E: Version '1.22.21' for 'dpkg-dev' was not found
  ```

  in the agent log (`agent/oracle.txt` of the trial), nothing was built, and
  the verifier gave reward 0.0. The same error appeared when we ran `solve.sh`
  by hand in a container from the baseline image. That run directory was in
  the converter's scratch space and is not kept; the lines above are the
  evidence. `reference.sh` drops that one pin; everything else is upstream's
  script verbatim. The other pins still resolve, and the repaired reference
  passes both graders (`qualification.json`).

## Candidates

- `reference.sh`: upstream's solution with the drift repair.
- `null.sh`: changes nothing.
- `mutant-static-link.sh`: links pmars statically; `ldd` exits 1 with nothing
  on standard output, which `run_shell_command` turns into a failure. Aimed at
  the emulation of `check_output`.
- `mutant-x11-linked.sh`: a headless build that still links `libX11`. Aimed at
  the X11 check, which runs on libraries captured from
  `/usr/lib/x86_64-linux-gnu`.
- `mutant-orig-source.sh`: builds from the upstream tarball alone, so there is
  no `debian/`. Aimed at the glob and existence probes.
- `mutant-debugger-aborts.sh`: the debugger quits on a command it cannot
  parse, so with dash's `echo` it prints one address. Aimed at the standard
  input the adapter gives pmars and at the address count at its threshold.
- `mutant-crlf-results.sh`: ends the results line with CRLF, which passes
  natively. Aimed at decoding, newline translation and the results match.
- `attack-shadow-ldd.sh`: links `libX11` and shadows `ldd` with a filter in
  `/usr/local/bin`.
- `attack-replace-ldd.sh`: links `libX11` and replaces `/usr/bin/ldd` with a
  filter.
- `attack-pmars-plants-ldd.sh`: links `libX11`, and pmars replaces
  `/usr/bin/ldd` with a filter the first time it runs (`plant-ldd.c`).

## Divergences from native

Qualification (`qualification.json`, no problems): the reference passes both
graders, the null candidate and the mutants static-link, x11-linked,
orig-source and debugger-aborts fail both, and crlf-results passes both. The
only divergences are the three attacks, which pass natively (reward 1.0) and
fail here (class `oracle`, case 1, "pmars links against an X11 library").
SecureBench is right in each: all three ship a pmars that links `libX11`,
which `test_headless_no_x11` exists to reject, and pass natively only by
hiding that from `ldd`.

- `attack-shadow-ldd.sh`: natively, `ldd` resolves through `PATH` to the
  candidate's filter in `/usr/local/bin`; here the challenge runs
  `/usr/bin/ldd`.
- `attack-replace-ldd.sh`: natively, the candidate's filter replaces
  `/usr/bin/ldd`; here `/usr/bin` is outside the scope, so the replacement is
  not captured.
- `attack-pmars-plants-ldd.sh`: natively, pmars replaces `/usr/bin/ldd` when
  `test_pmars_works` runs it, before `test_headless_no_x11` runs in the same
  container; here the X11 case starts in a fresh Evaluation environment in
  which pmars has not run.

## Review

Reviewer: conversion-reviewer (build-pmars-review), 2026-11-03 (second review)

Pack digest checked: `sha256:3372990655ea59fcbb5c9fd4ae043af35a3613e52e63c992c86142707ba9091c` (`securebench validate`). It is unchanged since the first review. Only `CONVERSION.md` changed, and the files in `task/` and `candidates/` have the same modification times as in the first review. Every SecureBench run in `qualification.json` records this digest, was made at SecureBench commit `1f18eddc` with `dirty: false`, was admitted and was rejudged. `problems` is empty, and no pack file is ignored by git.

1. Instructions. `cmp task/instructions.md` with upstream `instruction.md`: identical, no fidelity change.
2. Scope. Unchanged and still correct. The roots are `/app`, `/usr/local` and `/usr/lib/x86_64-linux-gnu`. Upstream's tests are not in the image, and the conversion runs no test runner, so there are no test files or convention-loaded files to exclude. The only symlink in the baseline under the roots is `/usr/local/man -> share/man`, which stays inside its root. The stricter losses are recorded with reasons that hold.
3. No expected value leaks. Upstream has no hidden expected value: every assertion is a format or property check with public literals. The baseline holds only the two public warriors in the scope. `deb.debian.org` publishes no answer.
4. Challenges. Each holds only its own test's commands, paths and glob patterns, all upstream literals.
5. Cases. Four cases, one per upstream test function, none added. The seed is unused, correctly.
6. Oracle. Unchanged. The literals are in `hidden/cases.json`, and `oracle.py` has only the hand-written regex matching and `run_shell_command` semantics, which I checked against upstream in the first review (strict UTF-8, universal newlines, strip, non-zero exit with output, `findall` counting, `match` anchoring). It shape-checks each observation and bounds its work. No regression tests run by outcome.
7. Candidates. `qualification.json`: the reference passes both graders (native 1.0). The null candidate fails both. The mutants static-link, x11-linked, orig-source and debugger-aborts fail both, and crlf-results passes both, so every mutant gets the same verdict from both graders. The three attacks get `failed` (class `oracle`) from SecureBench. The reference differs from upstream `solve.sh` only by the dropped `dpkg-dev` pin.
8. Divergences. The only divergences are the three attacks, which pass natively (1.0) and fail here. Each explanation holds: `attack-shadow-ldd` is blocked because the challenge runs `/usr/bin/ldd` by absolute path. `attack-replace-ldd`'s change to `/usr/bin` is outside the scope and not captured. `attack-pmars-plants-ldd` plants its filter only when pmars runs, and the X11 case starts fresh without running it. In all three, SecureBench is right, because the shipped pmars links libX11.
9. Inventory. `conversions/inventory.tsv` has no `build-pmars` row yet; the coordinator adds it. No exclusion reason applies.

Upstream assertions: as in the first review, every assertion of the four tests maps to the Oracle, and the implicit `CalledProcessError` and `UnicodeDecodeError` failures map to `shell_result` returning `None`. None is dropped.

First-review findings, re-checked:
- Fresh environment per test: fixed. The bullet is now labelled stricter for some candidates and more lenient for others. It names the lenient case (a pmars that deletes `debian/` or the `*.c` files when run) and the reason, which holds: SecureBench runs cases in parallel and judges each alone.
- `ldd` by absolute path: fixed. The claim now covers only `PATH` shadowing. It says that `ldd`'s loader and libraries are in a scope root, that a candidate can change what `ldd` prints as it can natively, and that the X11 check has only public expected values and can be passed without tampering. One wording point remains, which does not block approval: "bash, the dynamic loader `ldd` calls, and the libraries ... come from `/usr/lib/x86_64-linux-gnu`" reads as if the bash binary were there. `/usr/bin/bash` is outside the scope, and only its libraries and the loader are inside.
- Drift-repair evidence: fixed. The bullet now gives the native Pier run of the unmodified task (Pier 0.3.1, oracle agent, 2026-11-03) with the error lines and reward 0.0, and says that the run directory is not kept.

Findings:
- None that block. The wording point under the second re-checked finding is optional.

Verdict: approved
