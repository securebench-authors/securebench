# circuit-fibsqrt

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/circuit-fibsqrt

## How the pack grades

The agent writes `/app/gates.txt`, a circuit for the simulator in `/app/sim.c`. Upstream's `tests/test_outputs.py` has three tests; they map to two checks.

| Upstream test | Check | What the Oracle requires |
|---|---|---|
| `test_gates_file_exists` | artifact check `gates-file` | `/app/gates.txt` is present |
| `test_gates_file_size` | artifact check `gates-file` | fewer than 32,000 lines, counted as Python counts lines of a text-mode file |
| `test_sqrt_fib` | protocol check `sqrt-fib`, 28 cases | for each upstream input `n`, the simulator exits 0 and prints `fib(isqrt(n)) % 2**32` |

`sqrt-fib` works as upstream's test does. Its setup command runs `gcc -O3 /.securebench/evaluation/sim.c -o sim` in `/app`, where upstream runs `gcc -O3 /tests/sim.c -o sim`; `evaluation/sim.c` is byte-identical to upstream's `tests/sim.c`. A failed compile fails the attempt with class `setup`, as upstream's `assert False` fails the test. Each case then runs `/app/sim <n>` in `/app`, and the adapter reports the exit status and the printed lines. The simulator is trusted code compiled from our copy and overwrites any `/app/sim` the candidate left; the candidate supplies only data, the circuit that the simulator reads from `gates.txt`.

The 28 inputs and their expected values are in `hidden/cases.json`. `hidden/derive_cases.py` holds upstream's `fibonacci`, `isqrt` and input list verbatim and computes each value as the test does (`python3 -B derive_cases.py > cases.json`). We checked the values against `math.isqrt` and an independent Fibonacci loop, and against the two examples in the instructions (208 gives 377, 20000 gives 1407432322) by running the simulator on the reference circuit.

## Fidelity changes

- **Line count reimplemented (equivalent).** Upstream counts with `sum(1 for line in f)` on a file opened in text mode, which uses universal newlines: `\r\n` and a lone `\r` each end a line, and an unterminated last line counts. SecureBench's text parser splits on `\n` only, so the Oracle counts from the full text instead: it translates `\r\n` and `\r` to `\n` and counts. We compared it with Python's own count (the baseline's Python 3.13.7, same `io` implementation as the uv-managed 3.13 upstream's verifier uses) on 20,000 texts built from `\n`, `\r`, `\r\n`, ` `, `\x85`, `\v`, `\f` and ordinary characters, including 100,000-character texts that cross the 8 KiB read buffer: no mismatch. Upstream's threshold, `< 32000`, is kept. The mutants `cr-padding`, `unterminated-32000` and `crlf-31999` sit on this reimplementation.
- **`gates.txt` over 16 MiB (stricter).** The artifact check reads at most 16 MiB, the framework's limit for one file; a larger file fails as `too_large`. Upstream has no size limit. A circuit under 32,000 lines over 16 MiB needs lines averaging more than 500 bytes, which the simulator reads in 255-byte pieces; no reasonable solution writes one.
- **`gates.txt` starting with a UTF-8 byte-order mark (stricter).** SecureBench's text parser rejects a BOM, so the file is `unparsable` and fails. Upstream's Python reads it, and the simulator then fails to parse the first line. Such a file passes upstream only if its first line is not needed. Files that are not valid UTF-8 fail both graders: upstream's `open()` decodes strictly as UTF-8.
- **`gates.txt` as a symlink (stricter).** The scope permits relative symlinks inside `/app`, but the artifact check reports a symlinked `gates.txt` as `not_regular` and fails it, while upstream's `Path.exists()` and `open()` follow the link. A directory named `gates.txt` fails both.
- **Scope (equivalent for the content captured; stricter at capture in the edge cases listed).** The scope is `/app`, with everything below a subdirectory of `/app` excluded (`*/*`). Upstream reads only `/app/gates.txt` and compiles `/app/sim`, so nothing below a subdirectory affects its verdict. Dropping that content therefore changes no verdict. It also keeps a virtual environment or build directory with absolute symlinks from failing capture: a candidate that leaves `/app/venv` and an absolute symlink in `/app/a/b` is captured and judged. Capture still fails in these cases, where upstream would grade the circuit normally (stricter):
  - a top-level entry of `/app` that is an absolute or escaping symlink;
  - a top-level entry of `/app` that is a device, socket or named pipe;
  - a file name with a backslash, invalid UTF-8 or more bytes than the framework's name limit, either at the top level of `/app` or directly inside a top-level directory. The capture walker checks each name it lists before it applies the exclude patterns, so `*/*` does not shield names one level down. The reviewer confirmed this case: the reference plus an empty file `/app/build/a\b` ends `failed capture`.

  These are rare by-products of an agent's work and none touches the deliverable. Scope bounds are the framework's maxima, 100,000 entries and 2 GiB.
- **Per-case timeout (approximately equivalent).** Upstream's verifier has 3,600 s for installing uv and pytest, compiling, and running the simulator 28 times in sequence. Each SecureBench case has 128 s (3,600 / 28, rounded down) for one run. A circuit whose runs take very different times on different inputs could pass upstream and time out here (stricter); a circuit whose 28 runs together exceed upstream's budget minus its installation time, but each stay under 128 s, passes here (more lenient). The reference circuit takes about 1.7 s per run.
- **Output parsing (equivalent).** Upstream applies `int(result.stdout.strip())`. The Oracle strips the printed text and requires ASCII decimal digits before comparing. The simulator prints only `printf("%u\n", ...)` or nothing, and both rules accept and reject the same outputs of it. Upstream's non-zero exit check is kept.
- **No network (equivalent).** Upstream's `test.sh` downloads uv and pytest; the conversion needs neither. The reference needs no network, so `allowed_domains` is empty.
- **Test order (equivalent).** Upstream runs all three tests; SecureBench skips the cases when the artifact check fails. Upstream fails the task if any test fails, so the verdict is the same.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` byte for byte, after a `cd /app`.
- `null.sh`: changes nothing; the example circuit prints N/2.
- `mutant-cr-padding.sh`: the reference circuit plus 11,896 lone `\r`; the simulator still answers correctly, but upstream counts 32,000 lines. Both fail.
- `mutant-unterminated-32000.sh`: the reference circuit padded to exactly 32,000 lines, the last without a newline. Both fail.
- `mutant-crlf-31999.sh`: the reference circuit padded with CRLF blank lines to 31,999 lines. Both pass.
- `mutant-31-bit-output.sh`: the reference circuit with the most significant output bit tied to 0; four inputs have answers of 2^31 or more. Both fail.
- `attack-fake-sim.sh`: installs `/app/sim` as a program that prints the right answers. The setup command compiles over it.
- `attack-patched-simc.sh`: replaces `/app/sim.c`, which is inside the scope, with a program that prints the right answers. The setup command compiles its own copy.
- `attack-toolchain-shadow.sh`: plants `cc1`, `as`, `collect2`, `ld` and `ld.bfd` in `/app`, gcc's working directory during setup, each replacing `/app/sim` with the fake. gcc does not search its working directory, so the real simulator is built.
- `fake-sim.py` is used by two attacks and is not a candidate.

## Divergences from native

None. Every candidate gets the same verdict from both graders: the reference and `mutant-crlf-31999` pass both; the null candidate, the other three mutants and the three attacks fail both (native reward 0.0).

## Review

Reviewer: a51451b9e9b2eb026, 2026-10-26 (second review)

The first review had one finding, the incomplete Scope bullet. The converter changed only `CONVERSION.md`. `validate` prints the same pack digest, `sha256:b07deedd110b9010ac225a81bff0114b53b83fd03aaaa34f79ddd2f0e1ddd35a`. `reference.sh` is byte-identical to the copy I took in the first review, and `null.sh` has the same content as before. So points 1 to 7 and 9 stand as I checked them, and only the Scope record needed a second look.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. The root is `/app` with `*/*` excluded. That leaves top-level entries, and directories as empty shells, which covers the only deliverable, `/app/gates.txt`. `/tests` is not in the baseline. `/app` holds only `gates.txt` and `sim.c`, with no symlinks, and grading uses the pack's own `sim.c`. The baseline has no convention-loaded files. I checked in the baseline that a candidate's relative `/app/sim` symlink cannot survive `gcc -o sim`: gcc either unlinks it or writes the trusted build through it. The Scope bullet now records every capture failure I found in the walker (`securebench_utility/utility.py`): escaping or absolute top-level symlinks, top-level devices, sockets and named pipes, and bad names (backslash, invalid UTF-8, over-long) at the top level or one level down. Each is labelled stricter, with the reason.
3. No expected value leaks. Expected values exist only in `hidden/cases.json`. `evaluation/` holds the adapter, the schemas and `sim.c`, which is byte-identical to upstream `tests/sim.c`. The baseline has no `/tests`, no copies of upstream's tests or solution, and its `/app` files match upstream's by sha256. `allowed_domains` is empty. The answers are a public function of each challenge's `n`, which is outside SecureBench's scope.
4. Challenges. Each one is `{"n": n}` for its own case only.
5. Cases. There are 28 cases, which is upstream's list with nothing added. `python3 -I -B derive_cases.py` reproduces `cases.json` byte for byte. The seed is unused, which is correct because upstream draws no random values.
6. Oracle. All values come from `hidden/`, and `oracle.py` holds only judging logic. It requires the adapter to return normally with exit 0, an `Observed` outcome, both fields, simulator exit status 0, and a stripped, bounded, all-digit output equal to the expected value. Upstream's `int(stdout.strip())` gives the same verdicts on the only things the simulator prints. For the line count, I reran a differential in the baseline's Python 3.13 on 5,000 mixed texts, including texts that cross the 8 KiB buffer: no mismatch. The baseline's Python is in UTF-8 mode, and its `open()` rejects invalid UTF-8 and encoded surrogates, as the text parser does. The work is bounded, the schema has no claim fields, and each case is judged alone.
7. Candidates. `reference.sh` is upstream `solve.sh` with only a shebang, a comment and `cd /app` added. Its circuit has 20,104 lines and ends at the top signal (`out20103`), so `mutant-31-bit-output` does zero the most significant bit. The padding arithmetic of the three line-count mutants is correct. All mutants run the real generator and aim at the reimplemented line count and at the value comparison. The three attacks target replacing the simulator, and all fail with class `oracle`.
8. Divergences. `qualification.json` reports no problems. All nine SecureBench runs record the digest above, and none is dirty. The null run is on commit b7825ff and the others on 460f58a, but the two commits have the same framework code. Every verdict matches native, so "None" is correct. The changes since qualification touch only `CONVERSION.md`, which is not part of the pack.
9. Inventory. There is no row yet. The task converts, so no exclusion reason applies.

Upstream assertions: `test_gates_file_exists` and `test_gates_file_size` map to `gates-file`. In `test_sqrt_fib`, the compile assertion maps to the setup command, and the per-input exit status, integer parse and equality map to `sqrt-fib`. None is dropped. Every fidelity bullet has a label and a reason.

Findings:
- None. The first review's finding (Scope bullet incomplete) is fixed.

Verdict: approved
