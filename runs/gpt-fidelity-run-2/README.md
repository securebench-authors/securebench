# GPT 6.1 Sol fidelity study, run 2

This is the fidelity study with GPT 6.1 Sol through Codex. It is the second of two runs, and it covers all 180 converted tasks in one campaign. The first run is [`gpt-fidelity-run-1`](../gpt-fidelity-run-1/README.md). `python3 runs/fidelity_table.py` computes the paper's fidelity table from both runs. The Sonnet 5.5 campaign ran just before this one on the same worker: [`sonnet-fidelity-run-2`](../sonnet-fidelity-run-2/README.md). The data is in this folder (see "Data" at the end).

## Summary

We ran GPT 6.1 Sol once natively and once under SecureBench on all 180 converted tasks (68 Terminal-Bench, 112 DeepSWE), 360 attempts in all. 358 are valid. The other two are both attempts on `vulnerable-secret`: OpenAI's cyber safeguard refused each at its first request. They are kept as they happened and not rerun. We then graded each attempt's files with the other grader too.

- **Verdict agreement, the paper's measure: 97.9%.** Without the five tasks whose native tests cannot judge a copy of the files, the graders agree in 331 of 338 comparisons.
- **Verdict fidelity: 95.4%.** Given the same files, SecureBench and the original grader agree in 332 of 348 comparisons.
  - 9 of the 16 differences are on the by-design tasks. Without those tasks, agreement is 331 of 338 (97.9%).
  - The other 7 are 5 recorded divergences (4 stricter, 1 more lenient) and 2 native false passes on one task.
  - On Terminal-Bench, without the by-design tasks, agreement is 119 of 119.
  - 10 comparisons have no verdict on one side. None is a SecureBench grading error. 5 come from a capture refusal (2 tasks with an unfixed conversion error).
- **Outcome parity.** Native passed 142 of 179 tasks and SecureBench 134. The two agent runs differ on 26 tasks, 17 one way and 9 the other (exact McNemar test, p = 0.17), so there is no significant difference in difficulty. 9 of the 26 have a cause in the grading or the environment; 7 of those 9 favour native (below).
  - Compared with Sonnet, GPT solved 22 more tasks natively and 9 more under SecureBench (Sonnet: 120 and 125). Sonnet ranks lower than GPT under both graders.
- **Scope fidelity: 169 of 176.** In 169 of 176 native attempts, keeping only the files SecureBench captures leaves the original grader's verdict unchanged. Every difference is recorded in the conversion it comes from.
- **No SecureBench grading error.** Every verdict SecureBench reached matches the evidence.
  - Two SecureBench attempts stopped with a transient host error. Each produced `invalid`, not a wrong verdict, and was rerun.
  - A `.venv` conversion error is unfixed in `cattrs` and `langchain`, and here it turned a native pass into a SecureBench fail.

## Setup

- **Model and harness:** `gpt-6.1-sol` at medium reasoning effort, through Codex 0.160.0 on both sides, with an OpenAI API key.
  - Natively, Pier 0.3.1 installs it with `--agent codex -m openai/gpt-6.1-sol --ak version=0.160.0 --ak reasoning_effort=medium`.
  - Under SecureBench it runs from `overlays/codex-0.160.0` with `--reasoning-effort medium`, with Pier's flags.
- **Tasks:** every converted task in `conversions/inventory.tsv`, with the packs as committed. The `.venv` error in `cattrs` and `langchain` was left unfixed on the maintainer's choice, so that the results stay comparable with our earlier runs.
- **Limits:** each upstream task's CPU, memory, disk and agent time limit, on both sides.
- **Concurrency:** at most 5 attempts at once and 22,528 MiB of upstream memory limits, with no new attempt while the host had less than 8 GiB available.
- **When:**
  - The main run went from 12 November 2026, 13:16, to 13 November, 13:33.
  - Two reruns ran on 13 November, 13:34 to 13:42, and two regrades later that day (the Sonnet campaign's `regrades.sh`).
  - Everything ran from commit `b172a82f`, in a separate clean worktree. No file in `conversions/`, `securebench/`, `overlays/`, `pyproject.toml` or `uv.lock` differs from `c2e80fab`, where the Sonnet campaign started.
  - All on the qualified worker.
- **Commands:**
  - Main run: `python3 conversions/equivalence.py run --harness codex --model gpt-6.1-sol --effort medium --token-file .env --out runs/gpt-fidelity-run-2/raw/attempts --memory-budget-mib 22528 --max-running 5 --min-available-mib 8192 <tasks>` (`raw/scripts/gpt-run.sh`).
  - Reruns: the same command, after moving each replaced attempt to `raw/replaced/`.
  - Regrades: `equivalence.py regrade` on two attempts.
- **Validity:**
  - Every valid attempt ran on `gpt-6.1-sol` only, with no provider error and no agent at its time limit.
  - Every SecureBench run was admitted, ran from a clean tree, and was reproduced by `securebench rejudge`.
  - Codex tried to reach `chatgpt.com` and `ab.chatgpt.com` under SecureBench, and the proxy refused them (25 attempts).

## Method

Each task gets two separate agent runs, and each run's files are graded by both graders:

| Verdict | What it is |
|---|---|
| N | Native (Pier) verdict on the native agent's container, as run |
| N→S | SecureBench verdict on the native agent's scope roots, copied out before the native verifier and restored into a SecureBench run |
| N→s→N | Native verdict on the candidate that N→S captured |
| S | SecureBench verdict on the SecureBench agent's work, as run |
| S→N | Native verdict on the candidate that S captured |

N→S against N→s→N and S against S→N compare the graders on identical files. N against N→s→N shows what the scope loses. N against S, two separate agent runs, compares difficulty.

An attempt counts unless the agent ran on another model, or met a provider error (authentication, usage limit, server error), or SecureBench marked it `invalid` (a host error). An agent stopped by its time or memory limit is a valid fail. A by-design task is one where the original grader cannot judge a copy of the files, for example because its test needs a process the agent left running.

## Results

### Verdict fidelity

| Comparison | Agree | Without the by-design tasks |
|---|---|---|
| N→S against N→s→N | 168/176 | 167/171 |
| S against S→N | 164/172 | 164/167 |
| **Total** | **332/348 (95.4%)** | **331/338 (97.9%)** |
| Terminal-Bench | 120/129 | 119/119 |
| DeepSWE | 212/219 | 212/219 |

Ten comparisons have no verdict on one side:

- `cattrs-partial-structuring-recovery` (S) and `langchain-request-coalescing` (both sides): **a conversion error, not fixed in this release.**
  - The agents ran the projects' own uv commands (`uv run`, `uv sync`), which create a `.venv`. A venv holds symlinks, and the packs' `/app` root permits none, so capture refused the whole candidate (`symlink '/app/.venv/lib64': the scope root /app does not permit symlinks`).
  - Natively the verifier ignores the venv, and langchain's native agent passed (50/50 fail-to-pass, 232/232 pass-to-pass).
  - The fix is to exclude `**/.venv` from both packs' scope.
- `mcmc-sampling-stan` (both sides): the recorded stricter scope.
  - Both agents installed RStan with apt. One of its packages links a library in `/usr/lib/R/site-library` to `/usr/lib/x86_64-linux-gnu`, outside the scope, so capture refuses the candidate.
  - `CONVERSION.md` lists exactly this solution as one that passes upstream and fails here.
- `make-doom-for-mips` (S): capture refused the SecureBench agent's files, because its build script left a folder of links with absolute targets (`/app/mips/build/toolchain/mipsel-none-elf-ar`).
  - The framework rejects every absolute link target, and `CONVERSION.md` records that a link leaving `/app` fails capture. But it describes this only for a link that is part of the solution, not for a leftover build folder.
  - The agent's last run of its build reached the expected output, so the build itself probably worked.
- `build-pmars` (both sides): a limit of the measurement tool. Its restore empties `/usr/lib/x86_64-linux-gnu`, which the scope includes, and tar then cannot load.
- `koota-composite-trait-aspects` and `pwntools-tube-multiplexing` (S→N): **the SecureBench agent's work hangs the tests, under both graders.**
  - SecureBench failed both (case error).
    - In koota, the two `feature` cases ran vitest for 500 s and report `vitest did not finish in time`.
    - In pwntools, two cases timed out after 600 s.
  - The native verifier hit Pier's time limit on the same files twice, in the first grading and in a regrade. It writes no reward then, so S→N has no verdict.
    - In koota it hung in `vitest run tests/aspect.test.ts`, the file with the same new tests.
    - In pwntools the hang moved: the two tests SecureBench timed out on passed natively, and pytest hung later, in `TestFlowControl::test_flow_control_does_not_block_other_channels`. The agent's multiplexer hangs nondeterministically.

The 16 differences:

| Task | Comparisons | SecureBench | Original grader | Why |
|---|---|---|---|---|
| `pypi-server` | 2 | pass | fail on the copy | By design: the original test installs from the server the agent left running; a copy of the files has none. |
| `kv-store-grpc` | 2 | pass | fail on the copy | By design: the same, for a gRPC server. |
| `openssl-selfsigned-cert` | 2 | pass | fail on the copy | By design: the original test checks the key's file mode, which a copy does not keep. |
| `adaptive-rejection-sampler` | 2 | pass | fail on the copy | By design: the original test needs R installed outside the scope (`No such file or directory: 'Rscript'`). |
| `hf-model-inference` | 1 (S) | pass | fail on the copy | By design: the original test calls the Flask service the agent left running. |
| `adaptix-name-mapping-aliases` | 2 | fail | pass | Stricter, recorded. Both agents changed an internal API and edited upstream's `test_provider.py` to match; SecureBench restores upstream's tests. The same case occurred in the Sonnet campaign. |
| `claude-code-by-agents-recursive-delegation` | 2 | fail | pass | A native false pass. Natively vitest's worker runs out of memory (`JavaScript heap out of memory`), its JUnit report still lists all 7 tests with `time="0"` and no failure, and the native grader counts `F2P 7/7`. SecureBench runs the same tests and fails all 7: the delegated result is missing. |
| `fastapi-implicit-head-options` | 1 (native) | fail | pass | Stricter, recorded. The agent registered extra HEAD and OPTIONS routes and edited the pass-to-pass test `test_route_classes` to ignore them. SecureBench runs upstream's test, and it fails. `CONVERSION.md` calls this divergence negligible; it decided a verdict here. |
| `scc-bounded-memory-spilling` | 1 (S) | fail | pass | Stricter, recorded. The agent changed the formatters' signatures and rewrote upstream's `formatters_test.go` to match. Upstream's file then does not compile, so SecureBench's setup (`go vet ./processor`) fails. |
| `etree-xml-diff-patch` | 1 (native) | pass | fail | More lenient, recorded. The agent's untagged `merge_test.go` and `patch_test.go` use a helper defined only in its `diff_test.go`. Natively upstream's tagged file replaces it, the package no longer builds, and all 15 pass-to-pass tests fail. SecureBench never compiles the agent's test files. |

### Outcome parity

| | Tasks |
|---|---|
| Both pass | 125 |
| Both fail | 28 |
| Native only | 17 |
| SecureBench only | 9 |

The exact McNemar test on the 26 discordant tasks gives p = 0.17 (Terminal-Bench 3 against 2, p = 1.00; DeepSWE 14 against 7, p = 0.19). Nine of the 26 have a cause in the grading or the environment.

Seven favour native:

- `cattrs-partial-structuring-recovery` and `langchain-request-coalescing` (native only): the `.venv` conversion error. SecureBench never graded the work.
- `mcmc-sampling-stan` (native only): the recorded stricter scope, above.
- `adaptix-name-mapping-aliases` and `scc-bounded-memory-spilling` (native only): edited upstream tests, recorded as stricter.
- `claude-code-by-agents-recursive-delegation` (native only): the native false pass.
- `extract-moves-from-video` (native only): the pack allows no domains, and the SecureBench agent could not fetch the video. Natively the agent has the whole Internet.

Two favour SecureBench:

- `opa-template-string-reconstruction` (SecureBench only): the native agent staged its work but did not commit it. Native grades `git diff <base> HEAD` and saw an empty patch; SecureBench grades the working tree (recorded, more lenient).
- `pypi-server` (SecureBench only): Codex ended the native agent's server before the verifier ran.
  - A server started with `nohup ... &` did not outlive its Codex command, and one started as a foreground command lived only as long as Codex. Native's fail is correct by upstream's rule.
  - SecureBench starts the server from the agent's files (a recorded instruction change).

The other 17 are runs that went differently: 10 native only against 7 SecureBench only. They include `koota-composite-trait-aspects` and `pwntools-tube-multiplexing`, where the SecureBench agent's code hangs the tests under both graders.

### Scope fidelity

169 of 176 native attempts keep the original grader's verdict when only the captured files are graded. Three have no N→s→N verdict (`langchain-request-coalescing`, `mcmc-sampling-stan` and `build-pmars`, above). The 7 differences:

- The four by-design tasks that need a running process, a file mode or R: `kv-store-grpc`, `openssl-selfsigned-cert`, `hf-model-inference` and `adaptive-rejection-sampler`.
- `make-doom-for-mips`: `/tmp` is not captured, and natively the agent's stale `/tmp/frame.bmp` failed the original test.
- `mashumaro-flattened-dataclass-fields`: an edited pass-to-pass test, which the captured files do not include.
- `opa-template-string-reconstruction`: the uncommitted work above.

## Differences between the two environments

The differences listed in the [Sonnet report](../sonnet-fidelity-run-2/README.md) apply here as well. For Codex, the table names where we first saw each difference, in this or an earlier run of the study.

| Difference | First seen in | Favours |
|---|---|---|
| SecureBench allows only the pack's domains; natively the Terminal-Bench agent has the whole Internet | `extract-moves-from-video` | Native |
| Provider-hosted web search is off under SecureBench; natively Codex can use it, also on DeepSWE, where the container has no network but the search runs at the provider | native attempts | Native |
| Natively, Codex reaches `chatgpt.com` and `ab.chatgpt.com`; under SecureBench the proxy refuses them | SecureBench attempts | none observed |
| Native grades only committed work; SecureBench grades the working tree (recorded per conversion) | `opa-template-string-reconstruction`, `opa-rego-rule-profiling` | SecureBench |
| Native compiles the agent's own test files; SecureBench never does (recorded per conversion) | `onedump-dump-encryption-pipeline`, `arcane-drift-detection-baselines` | SecureBench |
| The native verifier sees leftovers in the agent's container | `make-doom-for-mips` | SecureBench |
| Pier passes the instruction as an argument and keeps Codex's home in `/tmp/codex-home`; SecureBench uses standard input and the image's home | all | none observed |
| Natively the agent's container holds the real key; under SecureBench only the relay does | all | none observed |
| Codex's own shell sessions end the processes an agent starts in them, so natively a server the agent "left running" may be gone when the verifier runs; SecureBench starts the service from the agent's files | `pypi-server` | SecureBench |

The last row concerns only tasks whose test needs a process the agent left running, which are by-design tasks for the cross-grades.

## Issues found during the run and how we handled them

No check, Oracle, expected value or upstream test was touched. Every replaced attempt is listed in `replaced-attempts.tsv` and in its task's `result.json`, with the reason. The worker incidents of the Sonnet campaign (DNS, network, Docker volume) all happened before this run started, and a scan of every native verifier log for network and disk failures found none here.

| Issue | Kind | Fix | Attempts |
|---|---|---|---|
| SecureBench stopped with a host error, `cannot locate the stock interpreter's loader: b''`: replay's 60 s probe of the stock Python image printed nothing (15:51 and 19:16 on 12 November) | SecureBench, transient | Rerun; reported to the maintainer | 2 SecureBench attempts rerun (`mobly-grouped-test-barriers`, `vitest-duration-sharding`); both passed on both graders |
| The native verifier hit Pier's time limit on two SecureBench candidates (S→N) | Agent's work | Regraded once to rule out the worker; it timed out again, and the cause is the agent's code (above) | 2 regraded (`koota-composite-trait-aspects`, `pwntools-tube-multiplexing`) |
| The main tree had an uncommitted edit, so SecureBench refused to start; a first start from the worktree lacked the untracked `overlays/` link, and every SecureBench unit failed with `found 0 records` | Measurement setup | Run from a clean worktree with links to `qualification.json`, `conversions/upstream/` and `overlays/`; both failed starts were stopped and their attempts deleted | none (logs kept as `raw/scripts/run-refused-dirty-tree.log` and `run-missing-overlays.log`) |

## Time and cost

| | Agent time, median | Wall time per attempt, mean | Cost per attempt, mean | Total |
|---|---|---|---|---|
| Terminal-Bench, native | 69 s | 7.1 min | $0.16 | $10.43 |
| Terminal-Bench, SecureBench | 101 s | 5.3 min | $0.14 | $9.11 |
| DeepSWE, native | 365 s | 13.1 min | $0.60 | $67.31 |
| DeepSWE, SecureBench | 382 s | 11.9 min | $0.57 | $64.38 |

- Codex reports tokens, not cost. Cost is computed from the tokens at $2 per million uncached input tokens, $0.10 per million cached input tokens and $10 per million output tokens. The OpenAI invoice is the authority.
- The 358 valid attempts cost about $151, and the two replaced attempts about $1.19 more.
- Cached input is 96% of input tokens (523 of 545 million).
- Wall time includes the cross-grades. The main run took 24 hours.

## Data

```
runs/gpt-fidelity-run-2/
├── README.md                 this report
├── attempts.tsv              the 360 attempts above, one row each (equivalence.py report)
├── replaced-attempts.tsv     the 2 replaced attempts and why, both infrastructure
├── <task>/                   one folder per task, 180 in all
│   ├── result.json           both attempts' verdicts, cross-grades, time and tokens, replaced attempts, notes
│   ├── native/
│   │   ├── securebench-record.json   SecureBench's verdict record of the native agent's files (N→S)
│   │   ├── verifier.json             the native verifier's reward and failing tests, for N and N→s→N
│   │   ├── candidate-manifest.json   every captured file: path, kind, size, hash
│   │   └── candidate.tar.gz          the captured files, when they total 10 MB or less
│   └── securebench/          the same for the SecureBench agent (S, and S→N in verifier.json)
└── raw/                      not part of this release; it stayed on the worker (about 112 GB)
```

- 319 candidates are included as files; 35 larger ones have their manifest only. Six were never captured: `langchain-request-coalescing` and `mcmc-sampling-stan` on both sides, and `cattrs-partial-structuring-recovery` and `make-doom-for-mips` under SecureBench.
- A regraded attempt keeps its earlier grades in `raw/attempts/.../regrade-replaced-1/`; its `result.json` has `regrades_replaced: 1`.
- To rebuild this folder from `raw/` (not released): `python3 conversions/equivalence.py export runs/gpt-fidelity-run-2/raw/attempts --out runs/gpt-fidelity-run-2 --replaced runs/gpt-fidelity-run-2/raw/replaced --notes runs/gpt-fidelity-run-2/raw/scripts/notes.json`.
