# cobol-modernization

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/cobol-modernization

The agent rewrites `/app/src/program.cbl`, a small book-marketplace program in
COBOL, as `/app/program.py`. Upstream's verifier (`tests/test_outputs.py`)
checks that `program.py` and the four data files exist, then writes known
initial data files, runs `python /app/program.py` three times with three
transactions in `INPUT.DAT`, and compares the final `ACCOUNTS.DAT`,
`BOOKS.DAT` and `TRANSACTIONS.DAT` with literals.

## How the pack grades

One protocol check, `program-output`, with one case. Upstream's three tests
run in order in one container and share its state, so they become one case:

| Upstream assertion | SecureBench |
|---|---|
| `test_required_files_exist`: `Path("/app/program.py").exists()` | The adapter records `Path.exists()` for it before touching anything; the Oracle requires `true`. |
| `test_data_files_exist`: `exists()` of the three `.DAT` files in `/app/data` and of `/app/src/INPUT.DAT` | The same, for the four files. |
| `test_program_output`: writes the initial `ACCOUNTS.DAT`, `BOOKS.DAT`, empty `TRANSACTIONS.DAT` | The adapter writes the same contents, which arrive in the challenge. A failed write is reported as `unable` (the case fails with class `case_error`); upstream's test fails there too. |
| three times: write `INPUT.DAT`, `subprocess.run(["python", "/app/program.py"], capture_output=True, text=True)` from `/app` (which raises if standard output or error is not UTF-8), `assert result.returncode == 0` | The adapter does the same and records, for each run, the exit status and whether each stream decodes as strict UTF-8, stopping after the first run that fails either way as the test does; the Oracle requires three runs, each with both streams UTF-8 and status 0. |
| `read_text()` of the three data files `==` expected literals | The three files are Output Artifacts parsed as UTF-8 text; the Oracle requires each to be present and its text equal to the literal. |

The challenge (initial files and the three inputs) and the expected file
contents are in `task/hidden/cases.json`, copied from upstream's test. The
Oracle holds no expected value. We also checked the literals against the COBOL
program itself: compiled with the baseline's `cobc -x` and run on the same
three inputs, it leaves exactly these three files.

Scope: all of `/app`, with internal symlinks allowed. Upstream has no test
files in `/app` and runs nothing there by convention; the data and input files
stay in scope because upstream checks that they exist.

## Fidelity changes

- **Interpreter (equivalent).** Upstream's test runs `python` from the `PATH`
  of the uv tool environment that runs pytest: a virtual environment whose
  base interpreter is the baseline's `/usr/local/bin/python` (3.13.7) and
  which does not see the system site-packages. We confirmed this by running
  upstream's `uvx` command in the baseline with a test that printed
  `shutil.which("python")`, `sys.prefix` and `sys.base_prefix`. The adapter
  runs `/usr/local/bin/python` directly. The one difference is which
  third-party packages `program.py` could import: upstream's venv has pytest
  and its dependencies, the baseline interpreter has pip. Packages an agent
  installs into the system site-packages are invisible to upstream's venv and
  are not captured by our scope (`/usr/local` is outside it), so both graders
  fail a program that needs them (`mutant-sitewide-module`).
- **Standard streams (equivalent).** Upstream runs the program with
  `capture_output=True, text=True`: once the program exits, subprocess
  decodes its standard output and error with the locale encoding (UTF-8 in the
  baseline) and strict errors, and a decode error fails the test. The adapter
  captures both streams and feeds them to Python's incremental strict UTF-8
  decoder as they arrive, so it reports the same answer without holding the
  output in memory; the Oracle requires both to decode
  (`mutant-latin1-output`). We compared this check with
  `subprocess.run(..., text=True)` on 13 outputs, among them a multi-byte
  character split across the adapter's 64 KiB reads, a truncated final
  sequence, an encoded surrogate, an overlong encoding, a code point above
  U+10FFFF and a bad byte after 300,000 good ones, on both the baseline's
  Python 3.13.7 and the stock Python 3.12.15 that runs the adapter: no
  differences. Standard input differs: upstream's program inherits pytest's,
  the adapter gives it `/dev/null`. The task reads no standard input.
- **Reading the data files (equivalent, except symlinks: stricter).** Upstream
  compares `Path.read_text()`, which decodes as UTF-8 (the baseline has no
  `LANG`, so Python's C-locale coercion selects UTF-8) and translates `\r\n`
  and `\r` to `\n`. SecureBench's text parser decodes strict UTF-8 without
  translating newlines and rejects a leading byte-order mark. Because the
  expected literals contain no `\r`, `\n` or U+FEFF, a file matches upstream's
  literal after `read_text()` exactly when its bytes are the UTF-8 encoding of
  the literal, which is what the Oracle requires; a byte-order mark fails both
  (`mutant-byte-order-mark`). One difference remains: `read_text()` follows a
  symlink, while an Output Artifact that is a symlink is not a regular file
  and fails. A `program.py` that leaves a data file as a symlink to a file
  with the right content would pass upstream and fail here; we know of no
  plausible implementation that does this.
- **Timeout (equivalent).** Upstream has no per-run timeout; its verifier as
  a whole has 900 seconds, including installing uv and pytest. The case has
  900 seconds.
- **Allowed domains (equivalent for grading, stricter for the agent).**
  None, where upstream's agent has full internet. Grading is unchanged: the
  verdict depends only on what the candidate leaves in `/app`. The agent,
  however, cannot download anything (packages, documentation) while it works.
  The reference solution runs `apt-get update && apt-get install -y
  gnucobol3`; without network `apt-get update` fails, the install is skipped,
  and the already-installed `gnucobol3` is used, so the reference needs no
  domain. Its `program.py` uses only the standard library.
- **Scope (stricter).** Upstream grades in the agent's own container, so
  everything the agent leaves anywhere counts: a helper module in `/opt`, a
  binary in `/usr/local/bin`, a background process. SecureBench keeps only
  `/app`, and every case starts from the baseline with the candidate's
  changes under `/app` replayed. We keep `/app` because the instructions name
  `/app/program.py` as the deliverable and the data files it modifies are in
  `/app` too; a `program.py` that depends on files elsewhere fails here and
  could pass upstream. `mutant-sitewide-module` is one such case that also
  fails upstream, because upstream's virtual environment does not see the
  system site-packages.
- **Capture (stricter, framework).** An agent that creates a virtual
  environment under `/app` leaves symlinks that point out of the scope (for
  example `bin/python -> /usr/local/bin/python3`), and capture fails the
  candidate. Upstream would grade such a candidate normally. The task needs
  only the standard library, so we did not exclude guessed venv names.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` unchanged, after `cd /app`.
- `null.sh`: changes nothing; `/app/program.py` does not exist.
- `mutant-latin1-output.sh`: correct files, prints a confirmation in Latin-1
  (UTF-8 record of standard output).
- `mutant-byte-order-mark.sh`: writes the data files with a UTF-8 byte-order
  mark (text parser, decoding).
- `mutant-exit-status.sh`: correct files, exit status 1 (exit status record).
- `mutant-consumes-input.sh`: deletes `src/INPUT.DAT` after processing and is
  run once at agent time (existence record).
- `mutant-sitewide-module.sh`: the logic lives in a module in the system
  site-packages (interpreter and scope).
- `attack-forge-observation.sh`: `program.py` writes a forged all-success
  observation to the adapter's standard output through `/proc` and kills the
  adapter.
- `attack-special-outputs.sh`: `program.py` turns the data files into a
  symlink to `/dev/zero`, a FIFO and a directory, aiming to hang or crash the
  Output Artifact collection.
- `attack-kill-everything.sh`: `program.py` sends SIGKILL to every process it
  can reach, aiming for an infrastructure error.

## Limitation: answer in the baseline

The baseline image ships the expected final files. `/app/data/ACCOUNTS.DAT`,
`BOOKS.DAT` and `TRANSACTIONS.DAT` in the image (upstream's
`environment/data/`) are byte for byte the three expected contents in
`task/hidden/cases.json`: upstream left its data directory in the state its
own test produces. A candidate that copies these files at agent time and whose
`program.py` writes the copies back over `/app/data/` passes both graders; the
reviewer ran such a candidate through SecureBench and it passed. The pack
cannot hide the files without changing the baseline, which would change what
the agent sees. Since native passes the same candidate, this is not a
divergence; it is a weakness of the upstream task that the conversion keeps.

## Divergences from native

No mutant diverges: every mutant fails both graders, the reference passes
both and the null candidate fails both. One attack does not end in a native
fail:

- `attack-kill-everything`: native ends in an error,
  `RewardFileNotFoundError`, with no reward. Its SIGKILL reaches upstream's
  `test.sh` as well as pytest, so `test.sh` never writes `reward.txt`. The
  native grader lets a wrong candidate turn its failure into an
  infrastructure error. SecureBench is right: it says `failed`
  (`case_error`, the adapter exited with status 137), and the candidate does
  nothing towards the task.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-24 (second review, after
the converter addressed the first one)

Pack digest from `securebench validate`:
`sha256:cb8de73e515fb1b9e60561f0d8d5e6f36db8d81343c4577ef6f409e6cfb1f539`.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`:
   identical.
2. Scope. One root, `/app`, no excludes, internal symlinks allowed. In the
   baseline image `/app` holds only `data/` (the three `.DAT` files) and
   `src/` (`INPUT.DAT`, `program.cbl`): no symlinks, no test files, no
   convention-loaded files. The deliverables are all under `/app`. The scope
   is now a labelled fidelity change (stricter, with its reason), and the
   venv-symlink case is recorded under "Capture".
3. Expected values. None in `evaluation/` or the challenge, and there is no
   `public/`. The baseline ships the three expected files at `/app/data/`
   (byte for byte the literals in `hidden/cases.json`); the pack cannot hide
   them without changing the baseline, and this is now recorded under
   "Limitation: answer in the baseline", including that a copy-back candidate
   passes both graders. No allowed domains.
4. Challenges. The single challenge carries only the initial files and three
   inputs that upstream's test writes.
5. Cases. One case, from upstream's `test_program_output`, with the two
   existence tests folded in because they share its state. No seed. None
   added.
6. Oracle. Expected contents come from `hidden/cases.json`; `oracle.py` only
   compares. It checks exact field sets for the observation, `existed` and
   each run record, requires both streams UTF-8 and status 0 for every run
   (in upstream's order: decode, then return code), requires exactly three
   runs, then the Output Artifacts' order, status and exact text. Bounded by
   the schemas (16 runs, 4 KiB observation) and 1 MiB artifacts. No regex, no
   evidence used as a path. No regression tests run by outcome.
7. Candidates. The reference is upstream `solve.sh` plus `cd /app`. The five
   mutants run real code and are aimed at the adapter's records (existence,
   exit status, the new UTF-8 record of the streams), the text parser (byte
   order mark) and the interpreter and scope (site-packages). The three
   attacks forge the observation through `/proc` (updated to the new
   observation format), turn the Output Artifacts into special files, and
   kill every process. I checked the adapter's incremental UTF-8 check
   against upstream's `subprocess.run(..., capture_output=True, text=True)`
   in the baseline on 12 outputs (empty, multi-byte characters split across
   the 64 KiB reads, truncated sequence, encoded surrogate, overlong
   encoding, code point above U+10FFFF, a bad byte after 300,000 good ones,
   a byte-order mark, CR and CRLF): they agree on all of them.
8. Divergences. `qualification.json`: every SecureBench run is admitted,
   clean (`dirty: false`), rejudged, and records the digest above;
   `problems` is empty. Reference passes both graders, null fails both,
   every mutant fails both (`mutant-latin1-output` included, native 0.0).
   The only difference is `attack-kill-everything`: native ends in
   `RewardFileNotFoundError`, SecureBench in `failed`/`case_error`. The
   explanation holds: `kill(-1)` reaches upstream's `test.sh`, so no reward
   is written natively, and SecureBench correctly fails a candidate that
   does nothing towards the task. Seven native results are `native_cached`
   from the earlier qualification; the upstream task and those scripts are
   unchanged, and `reference.sh`, which the mutants read, is unchanged.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet (the
   coordinator adds it). It should be `converted`; no Section 11 exclusion
   reason applies.

Upstream assertions: `test_required_files_exist` and `test_data_files_exist`
map to the `existed` record; the implicit strict UTF-8 decoding of
`capture_output=True, text=True` and the three `returncode == 0` assertions
map to the per-run records; the three `read_text() ==` assertions map to the
Output Artifacts. Each fidelity change is labelled with a reason.

Findings from the first review, re-checked:
- Output not decoded as UTF-8: fixed in the adapter, schema and Oracle, with
  `mutant-latin1-output` aimed at it; the bullet now describes the check and
  its comparison with upstream's decoding.
- Answer in the baseline: recorded under "Limitation: answer in the
  baseline".
- Scope not a labelled fidelity change: added, stricter.
- Allowed domains: the bullet now says the agent loses internet access.

Findings:
- None.

Verdict: approved
