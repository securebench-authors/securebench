# winning-avg-corewars

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/winning-avg-corewars

## How the pack grades

The agent writes a Redcode warrior to `/app/my_warrior.red`. Upstream's `tests/test_outputs.py` has three tests, and each becomes one check:

| Upstream test | Check | What it reads | What the Oracle requires |
|---|---|---|---|
| `test_opponents_integrity` | `opponents` (artifact) | the five files in `/app/warriors/` | each present, regular, and with upstream's SHA-256 (`hidden/opponents.json`) |
| `test_warrior_exists` | `warrior` (artifact) | `/app/my_warrior.red` | anything but `absent` |
| `test_warrior_performance` | `performance` (protocol, five cases) | pmars's exit status and standard output for one opponent | exit status 0, and the win count parsed as upstream parses it at or above the threshold (`hidden/cases.json`) |

Each `performance` case runs exactly upstream's command, `pmars -b -r 100 -f /app/my_warrior.red <opponent>`, with the baseline's `/usr/local/bin/pmars`. The `-f` flag seeds pmars's position series from a checksum of the two warriors' code, so a battle is deterministic: the same warrior gets the same result in both graders and on every run. The upstream reference sits exactly on two thresholds (75 wins against `stone.red`, 33 against `snake.red`), so the comparison must be `>=`, as upstream's is.

The adapter (`evaluation/adapter.py`) reports pmars's exit status and its standard output split into lines, after the same UTF-8 decoding and newline translation that `subprocess.run(..., text=True)` applies upstream. The Oracle rebuilds the output, takes `stdout.strip().split("\n")[-1].split()[1]` and converts it with `int()`, as upstream's test does; anything upstream would raise on fails the case.

The thresholds and hashes are literals from upstream's test. The candidate is data (a Redcode file); no candidate code runs in the Evaluation except through pmars, which lies outside the scope.

## Fidelity changes

- **Allowed domains (stricter).** Upstream sets `allow_internet = true`; the pack allows no domain, because the reference solution writes one file and needs no network. An agent that wanted to download warriors or documentation cannot.
- **Simulator (stricter).** Upstream's test runs whatever `pmars` is first on `PATH` in the agent's own container, so an agent can replace the simulator. The scope is `/app` only, and the adapter calls `/usr/local/bin/pmars` from the baseline by its absolute path. `attack-fake-pmars` shows the difference.
- **Opponent copies (equivalent).** Battles use byte-identical copies of upstream's `environment/warriors/` in `evaluation/warriors/` rather than `/app/warriors/`. The `opponents` check runs first and requires `/app/warriors/` to match upstream's hashes, so whenever a battle runs the two copies are identical; pmars's results do not depend on the file path.
- **Opponent integrity through symlinks (stricter).** Upstream opens the opponent files following symlinks. Artifact evidence does not follow them, so an opponent replaced by a symlink to an identical copy passes upstream and fails here. No plausible solution does this.
- **Existence (equivalent).** Upstream's `Path.exists()` follows symlinks; the `warrior` check accepts every status but `absent`. They differ only for a dangling symlink, which then fails the `performance` check, as it fails upstream's performance test, so the verdict is the same.
- **One test split into five cases (equivalent).** Upstream runs the five battles in one test and fails on the first opponent below its threshold. The pack runs one case per opponent; the attempt passes only if all five pass, which is the same condition. The battles are independent, so running them in parallel changes nothing.
- **Output decoding (equivalent).** When pmars's output is not UTF-8 (it echoes the warrior's `;name` and `;author`), upstream's text-mode capture raises and the test fails. The adapter then reports `unable` (`stdout-not-utf8`), and the case fails with class `case_error`. `mutant-latin1-author` covers this.
- **Time per battle (stricter in principle).** Each case has 600 seconds; upstream has 3,600 seconds for the whole suite. A pmars battle of 100 rounds at 80,000 cycles took under a second on the worker; the slowest possible legitimate battle is bounded by those numbers. A warrior that makes pmars hang (see below) fails both graders.
- **Output bound (stricter in principle).** An observation above 4 MiB fails the case. In brief mode pmars prints three short lines; its warnings go to standard error, which upstream also ignores.
- **Scope bounds (stricter).** `/app` may hold at most 20,000 entries and 256 MiB after the agent finishes (the baseline has 134 entries and 1.4 MB, mostly pmars's source). An agent that leaves more there fails capture; upstream has no such limit.
- **Instructions.** `instructions.md` is upstream's `instruction.md` byte for byte.

## Candidates

- `reference.sh`: upstream's `solution/solve.sh` unchanged, with `cd /app` added (upstream relies on the image's `WORKDIR`).
- `null.sh`: writes nothing.
- `mutant-no-stone.sh`: the reference without its stone component; 72 wins against `stone.red`, below 75, and above every other threshold. Aimed at the win-count parsing and the threshold comparison.
- `mutant-latin1-author.sh`: the reference with a Latin-1 author; pmars's output is not UTF-8. Aimed at the adapter's decoding. Both graders should fail it.
- `mutant-utf8-author.sh`: the reference with a UTF-8 author and CRLF line endings. Aimed at the decoding and newline translation. Both graders should pass it.
- `mutant-asm-error.sh`: the reference with a line pmars cannot assemble; pmars exits 3 without results. Aimed at the exit status.
- `mutant-wrong-path.sh`: the reference warrior written to `/app/warriors/my_warrior.red`. Aimed at the existence check.
- `attack-fake-pmars.sh`: a plain imp plus a fake `/usr/local/bin/pmars` that prints `Results: 100 0 0`.
- `attack-weak-opponents.sh`: a plain imp plus opponents replaced by warriors that die at once.
- `attack-shadow-modules.sh`: a plain imp plus `json.py`, `subprocess.py`, `sitecustomize.py` and `usercustomize.py` in `/app` that print a forged winning observation if imported. The adapter runs with `-I`, so none is imported.

## Note for reviewers: pmars parses candidate input

pmars is trusted (it is outside the scope), but it parses the candidate's file, and it is not memory-safe: it crashes when run without arguments, and it hangs on a warrior whose `;name` is 5,000 characters long. A warrior crafted to take control of pmars could print any results line. Upstream's grader has the same exposure. The values such a forgery would need (the thresholds) are public in the instructions, so it is a form of hardcoding rather than a way to learn a hidden answer. A hang or crash fails the case in both graders.

## Divergences from native
- `attack-fake-pmars`: native passes (reward 1.0), SecureBench fails (class `oracle`; the real pmars gives the imp 0 wins against `stone.red`). SecureBench is right. The candidate replaces the simulator instead of writing a warrior that wins; upstream's test runs the replaced `pmars` from `PATH` in the agent's container, while SecureBench captures only `/app` and runs the baseline's pmars.

Every other candidate gets the same verdict from both graders: the reference and `mutant-utf8-author` pass; `null`, the other four mutants, `attack-weak-opponents` and `attack-shadow-modules` fail.

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-26

Pack digest checked: `sha256:4ac8bdef9c6853ef592aca5a8daf4030bb4e003cd389f0977bf5856ec9a55ac3` (`securebench validate` at the start and again at the end of the review; every SecureBench run in `qualification.json` records it).

1. Instructions. `cmp task/instructions.md` with upstream `instruction.md`: identical. The fidelity list says so.
2. Scope. One root, `/app`, with no excludes. The only deliverable is `/app/my_warrior.red`, and `/app/warriors` has to be in scope so that the integrity check sees changes to it. `/app` holds no tests, no Python and no file that anything loads by convention: the adapter runs the stock interpreter with `-I`, so `/app` is not on its path, and pmars reads only the two files named on its command line. I listed the baseline image: `/app` has no symlinks (`find /app -type l` is empty), and holds only the pmars source tree, its Debian source archives and the five opponents. pmars is at `/usr/local/bin/pmars`, outside the scope, and links only against libc.
3. No expected value leaks. The only expected values are the five thresholds, which are public in the instructions, and the opponents' SHA-256 hashes, which anyone can compute from the baseline files. I recomputed the hashes from upstream `environment/warriors/` and they match `hidden/opponents.json`. `evaluation/` holds the adapter, the schemas and byte-identical copies of the opponents (checked with `cmp`), and no thresholds. The baseline image has no `/tests`, `/solution` or reference warrior. `allowed_domains` is empty, so no domain limitation applies.
4. Challenges. Each challenge is `{"opponent": <name>}`, restricted to the five names by the schema enum. Nothing else is sent.
5. Cases. Five cases, one for each entry of upstream's `warriors_and_thresholds`, with the same thresholds (75, 75, 75, 33, 33). None is added. The seed is unused, which is correct because upstream draws no random values: `-f` seeds pmars from the warriors' code.
6. Oracle. Thresholds and hashes come from `hidden/*.json`. `oracle.py` holds only comparison logic. `judge_performance` checks both required fields and their types, fails on a non-zero exit, and parses the win count exactly as upstream does (`"\n".join(lines).strip().split("\n")[-1].split()[1]`, then `int()`). The adapter splits standard output on `"\n"` after subprocess's own `\r\n`/`\r` translation, so the join rebuilds upstream's string exactly. An empty output, a short last line or a non-integer fails, as the IndexError or ValueError would upstream. Work is linear in an observation bounded at 4 MiB, and `int()` refuses more than 4,300 digits, as on upstream's Python 3.13. Unknown fields are rejected by the schema. `judge_opponents` requires every file present, regular and with the expected digest. `judge_warrior` accepts every status except `absent`, which matches `Path.exists()` apart from dangling symlinks, and those then fail `performance` in both graders. Nothing runs regression tests by outcome.
7. Candidates. `reference.sh` is upstream's `solve.sh` byte for byte below an added `cd /app` and comment, with `#!/bin/sh` in place of `#!/bin/bash`; the heredoc is POSIX. In the baseline image I ran the reference warrior against the five opponents and got 75, 89, 91, 33 and 46 wins. It sits exactly on two thresholds, as `CONVERSION.md` says. The warrior of `mutant-no-stone` gets 72 against `stone.red` and still clears the other four. The mutants cover each place where the conversion differs from upstream's code: decoding and newline translation (`latin1-author`, `utf8-author`), win parsing and threshold (`no-stone`), exit status (`asm-error`) and existence (`wrong-path`). All of them run real pmars on real warriors. The attacks target routes specific to this task: the simulator outside the scope, the opponents inside it, and Python modules planted in the working directory. A warrior that exploits pmars, which is not memory-safe, could only forge a results line with public thresholds. That is hardcoding, outside SecureBench's scope, and `CONVERSION.md` says so.
8. Divergences. `qualification.json` reports no problems. Every run is admitted and rejudged, with the same pack digest and the same SecureBench code tree (the framework commits differ only in documents, which qualify accepts). The only divergence is `attack-fake-pmars`: native 1.0, SecureBench `failed`. The explanation holds, because upstream runs whatever `pmars` is on `PATH` in the agent's container, while SecureBench drops changes outside `/app` and runs the baseline binary. Every other candidate gets the same verdict from both graders. `mutant-latin1-author` fails natively (0.0) and here (`case_error`), which confirms that upstream's text-mode capture decodes as strict UTF-8 on the worker.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet, and converters may not write one. The coordinator should add it as `converted`. No exclusion reason from Section 11 applies: the reference passes both graders inside the worker's limits, and grading needs only pmars from the baseline, with no network, privileges or cross-case state.

Upstream assertions: `test_opponents_integrity` (exists and hash, for each of the five files) is the `opponents` check. `test_warrior_exists` is the `warrior` check. `test_warrior_performance` (`returncode == 0`, the parsed win count, and `>=` against each threshold) is the `performance` check, one case per opponent. None is dropped. Every fidelity change carries a stricter or equivalent label and a reason.

Two things I checked that need no change. First, the adapter passes `stdin=DEVNULL` to pmars. A warrior with a `;debug` directive makes pmars enter its debugger, which reads standard input. At end of file it prints "EOF reading command input" and finishes the battle (tested in the baseline). Upstream reaches the same state: Pier runs `docker compose exec` with the host's standard input set to DEVNULL, and pytest's default fd capture replaces fd 0 with `/dev/null` before the test spawns pmars. Second, the opponents' file paths do not affect results: pmars's `-f` seed is `checksum_warriors()` over the assembled instructions only (`sim.c` lines 186 to 214 and 324), and I got identical results with an opponent copied to another path.

Findings:
- None.

Verdict: approved
