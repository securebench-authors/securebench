# extract-elf

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/extract-elf

## How the pack grades

The agent writes `/app/extract.js`, a Node.js program that prints the memory
map of an ELF binary as JSON (address to 32-bit word). Upstream's
`tests/test_outputs.py` has two tests, which become the one case of the
protocol check `extract`:

- `test_extract_js_exists`: `/app/extract.js` exists and is a file
  (`Path.exists()` and `Path.is_file()`, both following symlinks). The adapter
  reports `os.path.exists` and `os.path.isfile` on that path before any
  candidate code runs; the Oracle requires both to be true.
- `test_output_matches_reference`: upstream writes `/app/new.c` (a small
  program printing its arguments, never shown to the agent), compiles it to
  `/app/new.o`, runs `node /app/extract.js /app/new.o` with standard output in
  `/app/out.json`, and runs its own reference script (`REF` in the test file)
  on the same binary. Then it asserts: the candidate exited 0; every address in
  `out.json` that is also in the reference output has the reference's value
  (Python `!=` on what `json.load` returned); and at least 75% of the
  reference's addresses appear in `out.json`, computed as
  `(found_keys / len(reference_json)) * 100 >= 75`.

  The adapter (`evaluation/adapter.py`) takes `new.c` and `new.o` from the
  case's challenge (see "Test inputs in hidden data"), writes them to the same
  paths, runs the same command with the same redirections, parses `out.json`
  with Python's `json` module exactly as upstream does, and reports the exit
  status and every key of the parsed object with its value and the value's
  JSON type (`integer`, `number`, `boolean`, `string`, ...). The Oracle
  (`hidden/oracle.py`) applies upstream's comparison to that report: Python's
  `int == value` for the reported type (so `1784774249.0` and `true` for 1
  count as equal, as they do upstream), and upstream's coverage expression,
  counting distinct keys.

The reference output (108 addresses, from `.text`, `.rodata` and `.data`) is
in `hidden/cases.json`. `hidden/derive.sh` rebuilds it: inside the pinned
baseline image it compiles `hidden/new.c` with the image's gcc, checks the
result is byte for byte `hidden/new.o`, and runs `hidden/ref.js` (upstream's
`REF` string, stripped as the test strips it) on it. The test binary has
sha256 `fa54084cf7f184506ebcb340875cd6fd55870cadd5ff2417c7fe2b53ab8348d4`.

## Test inputs in hidden data

Form: values. Upstream's only test input that decides an expected value is
data, not code: the test program `new.c` and the binary compiled from it,
`new.o`. The reference memory map is upstream's reference script run on
`new.o`, so whoever holds `new.o` (or `new.c` and the baseline's gcc) can work
out every expected value. Both files used to sit in `evaluation/`; they are now
`hidden/new.c` and `hidden/new.o`. `hidden/cases.json` names them for the one
case (`"program": "new.c"`, `"binary": "new.o"`), and `plan` puts them into
the challenge: `program` as text (211 bytes) and `binary_base64` as the
binary in base64 (21,280 bytes). The adapter decodes them and writes them to
`/app/new.c` and `/app/new.o` as before. `hidden/derive.sh` now compiles
`hidden/new.c` and compares with `hidden/new.o`; rerun on 2026-11-04, it
reproduced the binary and the 108 reference values unchanged. The challenge
was `{}` and is now about 21.5 KB, so `max_challenge_bytes` went from 1,024 to
21,539, the canonical size of this challenge.

We did not send the test steps as code. The steps (write the two files, run
`node /app/extract.js /app/new.o` into `/app/out.json`, parse it) are the same
for every possible test binary and decide no value: the map depends only on
the binary's bytes. They stay in the adapter.

Test by test, what is left in `evaluation/`:

- `test_extract_js_exists`: the adapter names `/app/extract.js` and reports
  `os.path.exists` and `os.path.isfile`. The expected values (both true) are
  decided by the instructions, which name the deliverable, and by the test's
  name. They are listed below.
- `test_output_matches_reference`: the adapter names the paths `/app/new.c`,
  `/app/new.o` and `/app/out.json` and the command `node`. These are fixed by
  upstream's test and say nothing about the binary's contents, so they decide
  no reference value. `challenge.schema.json` bounds `program` at 211 bytes
  and `binary_base64` at 21,280 bytes, the exact sizes this challenge needs,
  so it gives the lengths of the two files. A length decides no address or
  word of the map. The observation schema and the adapter's type names
  (`kind_of`) describe how a value is reported and are the same for every
  binary.

Expected values decided by the instructions or a test's name, not by hidden
data: `extract_js_exists` and `extract_js_is_file` true; `exit_status` 0
(upstream asserts the run succeeded); `stderr_is_utf8` true and
`output_kind` `object` (any run that upstream's test can parse at all). The
reference map and the 75% threshold over it are the only values that need
hidden data.

`new.c` is also printed verbatim in upstream's public
`tests/test_outputs.py`, so an agent that knows the upstream benchmark can
compile it itself. That is a public answer, which is out of scope here.

No attack changed. `attack-fake-gcc` shadows `gcc`, which the adapter never
runs before or after the move; the other two attacks do not touch the moved
files.

## Fidelity changes

- **Test binary compiled ahead of time (equivalent).** Upstream compiles
  `new.c` at grading time with `gcc` from `PATH`; we keep the compiled binary
  in `hidden/new.o`, `plan` sends it in the challenge, and the adapter writes
  it to `/app/new.o`. The binary
  is identical to what upstream's test produces: compiling twice in fresh
  baseline containers, and once after upstream's `test.sh` steps
  (`apt-get update`, `apt-get install -y curl gcc`, which leaves gcc at
  13.3.0-6ubuntu2~24.04), all give the sha256 above. Shipping it keeps
  candidate files in the scope (`/usr/local/bin/gcc`, `as` or `ld` ahead of
  `/usr/bin` on `PATH`, headers in `/usr/local/include`) from changing the
  program under test; `attack-fake-gcc` shows that this matters natively.
- **Reference output kept on the host (stricter against tampering, equivalent
  otherwise).** Upstream runs its reference script with `node` in the graded
  container after the candidate, so a candidate that shadows `node` controls
  both outputs (`attack-fake-node`). The Oracle compares with the stored
  reference output instead. For any candidate that does not tamper with the
  test, the verdicts are the same.
- **Upstream assertions about its own reference dropped (equivalent).** The
  test also asserts that `gcc` and the reference script exit 0 and that
  `out.json` and `reference.json` exist. These concern trusted steps that we
  perform ahead of time, and `out.json` always exists once the adapter has
  opened it.
- **Undecodable standard error fails the case (equivalent).** Upstream runs
  the candidate with `stderr=subprocess.PIPE, text=True`, so standard error
  that is not valid UTF-8 raises inside `subprocess.run` and fails the test.
  The adapter reports `stderr_is_utf8` and the Oracle requires it.
- **Scope `/app`, `/usr/local` and `/opt` (stricter).** The deliverable is
  `/app/extract.js`; the scope also captures helpers next to it
  (`node_modules`, scripts) and packages installed with pip or npm under
  `/usr/local` or into `/opt`. Nothing is excluded: Node loads no test file by
  convention, and `/app/package.json` (for example `"type": "module"`) is part
  of a legitimate solution. Natively the agent's whole container is graded,
  so a solution whose `extract.js` relies on something the agent installed
  elsewhere, such as an apt package under `/usr`, passes natively and fails
  here. The baseline already has `python3`, `readelf` and `objdump`, so
  solutions that shell out to those still work (`mutant-python-floats` uses
  `python3`).
- **No allowed domains (stricter).** Upstream sets `allow_internet = true`.
  The reference needs no network, so the agent here cannot download npm or pip
  packages.
- **Output bounds (stricter).** The observation is at most 4 MiB and lists at
  most 100,000 keys, so an `out.json` with more than roughly 70,000 addresses
  fails here even if it would pass upstream. The reference prints 108 and a
  dump of every allocated section 214; a byte-granular dump of the whole
  test binary (about 16,000 addresses) still fits.
- **Time limit (more lenient).** Upstream's 900 s verifier timeout covers
  installing curl, uv and Python as well as running the candidate; here the
  case alone has 900 s.
- **Python 3.12 instead of 3.13 for parsing `out.json` (equivalent).** The
  adapter runs on the stock interpreter (3.12); upstream's test runs on
  3.13 under `uvx`. `json.loads` behaves the same in both on the inputs we
  tried, including the 4,300-digit integer limit.
- **Keys that are not valid Unicode are left out of the report
  (equivalent).** A key with a lone surrogate (`"\ud800"`) cannot be sent as
  strict JSON; no reference key contains one, so upstream ignores such keys
  too.

## Checking the comparison against upstream's

We ran upstream's comparison (`json.loads`, then the two assertions) and the
adapter's description followed by the strict decoder and the Oracle on 24
crafted `out.json` texts (in a `python:3.13-slim` container). They agreed on
every one: exact output; values written as floats (`4196274163.0`), with an
exponent, or as `true`/`false` for 1/0; values as strings; `NaN` or a
30-digit integer at a reference address; `NaN`, `Infinity` or a 30-digit
integer at an extra address; duplicate keys with the right value last and
with it first; keys with lone surrogates; `-0.0` for 0; a list, an empty
object, truncated JSON, two concatenated objects, a byte-order mark and
trailing whitespace; and the first 81 and 80 of the 108 reference addresses
(75.0% and 74.1%).

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with `cd /app` added.
- `null.sh`: changes nothing.
- `mutant-text-only.sh`: loads only `.text` (88 of 108 words, 81.5%). Probes
  the coverage count; passes both graders.
- `mutant-signed.sh`: reads words as signed integers. Probes the integer
  comparison of reported values; fails both.
- `mutant-all-alloc-sections.sh`: loads every allocated `PROGBITS` section, a
  superset of the reference. Probes extra keys; passes both.
- `mutant-directory.sh`: `/app/extract.js` is a directory with `index.js`,
  which `node` runs correctly. Probes the file check; fails both.
- `mutant-python-floats.sh`: `extract.js` runs a Python ELF parser
  (`python-floats-helper.py`) that writes values as floats. Probes the
  adapter's parsing and the float comparison; passes both.
- `attack-fake-node.sh`: shadows `node` so the candidate and the reference
  print the same map. Passes natively; must fail here.
- `attack-fake-gcc.sh`: shadows `gcc` so the test binary becomes the public
  `a.out`, and `extract.js` replays a map of `a.out` prepared in advance.
  Passes natively; must fail here.
- `attack-adapter-stdout.sh`: `extract.js` writes a forged report to the
  adapter's standard output, repeating one address 200 times, and kills the
  adapter. Must fail here.

## Divergences from native

- `attack-fake-node`: native passes (reward 1.0), SecureBench fails (oracle,
  0 of 108 reference addresses). SecureBench is right. The candidate parses
  nothing: its `/usr/local/bin/node` prints `{"0": 0}` for every script, so
  upstream's test compares the fake's output with itself. SecureBench compares
  with the reference output kept on the host.
- `attack-fake-gcc`: native passes (reward 1.0), SecureBench fails (oracle,
  inconsistent values from address 4432 onward). SecureBench is right. The
  candidate's `/usr/local/bin/gcc` turns upstream's hidden test program into
  the public `a.out`, and its `extract.js` replays a map of `a.out` without
  reading the binary it is given. SecureBench gives the candidate the real
  test binary.

Every other candidate gets the same verdict from both graders.

## Review

Reviewer: a0e561144237e2e5b, 2026-10-27

Pack digest reviewed: `sha256:e856a4288c8ff485f37a85327f7e97ba7b8c2da29d6088b50ef2f3f35c101ee3` (`securebench validate`, unchanged at the end of the review).

1. Instructions: `cmp` of upstream `instruction.md` and `task/instructions.md` finds no difference.
2. Scope: roots `/app`, `/usr/local` and `/opt`, nothing excluded. Upstream's tests live in `/tests` and the adapter does not use pytest, so no test file or convention-loaded file sits in the scope. The adapter runs on the stock interpreter with `-I`, so nothing in `/usr/local/lib/python3.12` reaches it. In the baseline image, the only symlink under the three roots is `/usr/local/man -> share/man`, which stays inside the root. `/app` holds only `a.out` and `hi.c`. Helpers the agent leaves outside the roots are lost. This is recorded as stricter, and without allowed domains the agent cannot install apt packages anyway.
3. Expected values: the reference map is only in `hidden/cases.json`. `evaluation/` holds `new.c` and `new.o`, which are the inputs upstream's test also writes into `/app`, plus the adapter and schemas. I found nothing in the baseline image (`find` for test files, `ref.js`, `new.c`, `new.o`, `reference.json` and `solve.sh`). The expected map is a deterministic function of `new.o`, which the candidate is given, so any forged report that passes has to contain values that solve the task. No allowed domains, so Section 4.7 does not apply.
4. Challenges: the one challenge is `{}`.
5. Cases: one case, covering upstream's two tests in upstream's order. Nothing was added, and the seed is unused.
6. Oracle: it holds only the comparison and the 75% threshold, and reads the reference from `hidden/cases.json`. `hidden/ref.js` is byte for byte upstream's `REF.strip()`, and `evaluation/new.c` is byte for byte the program the test writes (checked by parsing `test_outputs.py`). `new.o` has the sha256 that `CONVERSION.md` states. Every observation field is required by the schema and checked by the Oracle. `exit_status` rejects `False`. Coverage counts distinct keys as upstream does, and repeated keys fail. The work is bounded by the 100,000-entry schema. I ran `judge` on crafted observations and got the expected verdicts: 200 copies of one key fail; 81 exact keys pass and 80 fail; floats pass; `false` for 0 passes, as `0 != False` is false upstream; a kind/field mismatch fails; a missing `stderr_is_utf8` fails. I confirmed the stderr rule natively: in `python:3.13-slim`, with `LANG` unset and with `C.UTF-8`, `subprocess.run(..., stderr=PIPE, text=True)` raises `UnicodeDecodeError` on a 0xff byte. No regression tests run by outcome.
7. Candidates: `reference.sh` is `solve.sh` with only `cd /app` and a `sh` shebang (diffed). The mutants run real code and target the places where the conversion's check differs from upstream: float and bool values, extra keys, the file test, signed values and coverage. All five agree with native. The three attacks are specific to this task (shadowed `node` and `gcc`, a forged adapter report) and all fail in SecureBench. One observation: `attack-adapter-stdout` fails as `case_error` because it kills the adapter, so it never reaches the duplicate-key check that `CONVERSION.md` says it targets. The judge run above shows that the Oracle rejects that forged report anyway, so this is not a finding.
8. Divergences: `qualification.json` reports no problems. Every SecureBench run records the digest above, and no SecureBench code changed between the two framework commits it lists (ff5433c and dd3182b differ only under `conversions/` and `docs/`). The two divergences, `attack-fake-node` and `attack-fake-gcc` (native 1.0, SecureBench failed with class `oracle`), are explained correctly: both defeat upstream's in-container compilation or reference run, and the host-side reference and precompiled binary stop them.
9. Inventory: `conversions/inventory.tsv` has no row for this task yet. The coordinator adds it, and none of the Section 11 exclusion reasons applies.

Upstream assertions: `extract_path.exists()` and `is_file()` map to `extract_js_exists` and `extract_js_is_file`; the candidate's return code to `exit_status`; the inconsistent-values and 75% assertions to the Oracle. The assertions about gcc and the reference script exiting 0, and about `out.json` and `reference.json` existing, are listed as dropped (equivalent) with reasons. The implicit failures (UTF-8 stderr, `json.load` errors, a non-object passed to `.items()`) are reproduced.

Findings:
- None.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "`evaluation/` holds `new.c` and `new.o`" (line 218) → they are `task/hidden/new.c` and `task/hidden/new.o`; `evaluation/` holds only the adapter and schemas.
- "Challenges: the one challenge is `{}`" (line 219) → the challenge carries `program` (the text of `new.c`) and `binary_base64` (`new.o`).
- "`evaluation/new.c` is byte for byte the program the test writes" (line 221) → that file is now `task/hidden/new.c`.
