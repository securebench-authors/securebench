# Sonnet 5.5 fidelity study, run 2

This is the fidelity study with Sonnet 5.5. It is the second of two runs, and it covers all 180 converted tasks in one campaign. The first run is [`sonnet-fidelity-run-1`](../sonnet-fidelity-run-1/README.md). `python3 runs/fidelity_table.py` computes the paper's fidelity table from both runs. The GPT 6.1 Sol campaign ran alongside on the same worker: [`gpt-fidelity-run-2`](../gpt-fidelity-run-2/README.md). The data is in this folder (see "Data" at the end).

## Summary

We ran Sonnet 5.5 once natively and once under SecureBench on all 180 converted tasks (68 Terminal-Bench, 112 DeepSWE). That made 360 attempts, all valid in the end. We then graded each attempt's files with the other grader too.

- **Verdict agreement, the paper's measure: 99.4%.** Without the five tasks whose native tests cannot judge a copy of the files, the graders agree in 345 of 347 comparisons.
- **Verdict fidelity: 97.5%.** Given the same files, SecureBench and the original grader agree in 347 of 356 comparisons.
  - 7 of the 9 differences are on the by-design tasks, where the original grader cannot judge a copy of the files.
  - Without those tasks, agreement is 345 of 347 (99.4%). The other 2 differences:
    - `adaptix-name-mapping-aliases`: a recorded stricter divergence.
    - `kcp-go-multiplexed-kcp-streams`: a race in the agent's code. The same patch passed once and failed once.
  - On Terminal-Bench, without the by-design tasks, agreement is 123 of 123.
  - 4 comparisons have no verdict on one side; see "Verdict fidelity" below.
- **Outcome parity.** Native passed 120 of 180 tasks and SecureBench 125. The two agent runs differ on 41 tasks, 18 one way and 23 the other (exact McNemar test, p = 0.53). There is no measurable difference in difficulty.
- **Scope fidelity: 168 of 177.** In 168 of 177 native attempts, keeping only the files SecureBench captures leaves the original grader's verdict unchanged. Every difference has a known cause. One more stricter case is not recorded in its conversion: `pytorch-model-cli`, where capture refused the files.
- **No SecureBench grading error.** Every verdict SecureBench reached matches the evidence. The one SecureBench defect in this campaign was a transient host error (`tengo-callable-instance-isolation`, N→S). It produced `invalid`, not a wrong verdict, and was regraded.

## Setup

- **Model and harness:** `claude-sonnet-5-5` at medium reasoning effort, through Claude Code 2.1.289 on both sides.
  - Natively, Pier 0.3.1 installs it with `--ak version=2.1.289 --ak reasoning_effort=medium`.
  - Under SecureBench it runs from `overlays/claude-code-2.1.289` as `claude-code-oauth` with `--reasoning-effort medium`.
- **Tasks:** every converted task in `conversions/inventory.tsv`, with the packs as committed.
  - The `cattrs` and `langchain` packs still refuse a candidate that holds a `.venv` (a conversion error; see the GPT report). The maintainer chose to run them unfixed, so that the results stay comparable with our earlier runs. Sonnet's agents did not create a `.venv` in either task.
- **Limits:** each upstream task's CPU, memory, disk and agent time limit, on both sides.
- **Credential:** a Claude subscription token. The run paused once, until 01:30 on 12 November.
- **Concurrency:** at most 5 attempts at once and 22,528 MiB of upstream memory limits, with no new attempt while the host had less than 8 GiB available.
- **When:**
  - The main run went from 11 November 2026, 17:04, to 12 November, 12:38, from commit `c2e80fab`.
  - The GPT campaign then held the worker until 13 November, 13:33.
  - The reruns and regrades ran on 13 November, 13:42 to 18:15, from commit `b172a82f` in a separate clean worktree. Between the two commits no file changes in `conversions/`, `securebench/`, `overlays/`, `pyproject.toml` or `uv.lock`.
  - Everything ran on the qualified worker.
- **Commands:**
  - Main run: `python3 conversions/equivalence.py run --model claude-sonnet-5-5 --effort medium --token-file <oauth token file> --out runs/sonnet-fidelity-run-2/raw/attempts --usage-limit 80 --memory-budget-mib 22528 --max-running 5 --min-available-mib 8192 <tasks>`.
  - Reruns: the same command, after moving each replaced attempt to `raw/replaced/`.
  - Regrades: `equivalence.py regrade` on six attempts.
  - The scripts are in `raw/scripts/`: `chain.sh`, `reruns.sh`, `rerun2.sh`, `regrades.sh` and `rerun3.sh`.
- **Validity:**
  - Every final attempt ran on `claude-sonnet-5-5` only, with no subagent model.
  - Every SecureBench run was admitted, ran from a clean tree, and was reproduced by `securebench rejudge`.
  - One final attempt logged a provider error: `mteb-leaderboard` under SecureBench, where the relay refused the provider-hosted web search tool (`403 provider-hosted tools are disabled`). This refusal is by design, and the attempt counts as valid.
  - Five agents hit their time limit, as they can in any run: `extract-moves-from-video` and `feal-linear-cryptanalysis` natively, and `regex-chess`, `rstan-to-pystan` and `schemelike-metacircular-eval` under SecureBench.

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
| N→S against N→s→N | 172/177 | 171/173 |
| S against S→N | 175/179 | 174/174 |
| **Total** | **347/356 (97.5%)** | **345/347 (99.4%)** |
| Terminal-Bench | 125/132 | 123/123 |
| DeepSWE | 222/224 | 222/224 |

Four comparisons have no verdict on one side, and none is a SecureBench error:

- `build-pmars`, both sides: a limit of the measurement tool. The pack's scope includes `/usr/lib/x86_64-linux-gnu`, and the tool's restore empties a scope root before unpacking with tar, which then cannot load (`tar: not found`). The native verifier then writes no reward.
- `hf-model-inference`, native: also a limit of the measurement tool.
  - The native agent pip-installed PyTorch into `/usr/local`. The tool's restore, which runs as the scripted agent under the task's 2 GiB memory limit, was killed for memory after 75.9 s while unpacking 5.7 GB.
  - Neither N→S nor N→s→N measured the agent's work.
- `pytorch-model-cli`, native: capture refused the candidate, so N→S and N→s→N have no verdict.
  - The agent ran `pip download torch` and left about 3.0 GB of wheels in `/app`, over the pack's 2 GiB bound for that root (`scope root /app holds more bytes than its bound`).
  - This is a stricter case that the conversion's record does not list.

The 9 differences:

| Task | Comparisons | SecureBench | Original grader | Why |
|---|---|---|---|---|
| `pypi-server` | 2 | pass | fail on the copy | By design: the original test calls the server the agent left running; a copy of the files has none. |
| `kv-store-grpc` | 2 | pass | fail on the copy | By design: the same, for a gRPC server (`Port 5328 is not listening`). |
| `openssl-selfsigned-cert` | 2 | pass | fail on the copy | By design: the original test checks the key's file mode, which a copy does not keep (`Key permissions too open: 644`). |
| `hf-model-inference` | 1 (S) | pass | fail on the copy | By design: the original test calls the Flask service the agent left running. |
| `adaptix-name-mapping-aliases` | 1 (native) | fail | pass | Stricter, recorded. The agent changed an internal API and edited upstream's `test_provider.py` to match. SecureBench restores upstream's tests, and 34 of them fail. The same case occurred in the GPT campaign. |
| `kcp-go-multiplexed-kcp-streams` | 1 (native) | pass | fail | A race in the agent's code. Upstream's `TestMuxConcurrentStreams` passed in N and failed in N→s→N on the identical patch (`io: read/write on closed pipe`): OPEN frames can be queued out of id order, and the server then closes the session. N→S passed. |

### Outcome parity

| | Tasks |
|---|---|
| Both pass | 102 |
| Both fail | 37 |
| Native only | 18 |
| SecureBench only | 23 |

The exact McNemar test on the 41 discordant tasks gives p = 0.53 (Terminal-Bench 4 against 3, p = 1.00; DeepSWE 14 against 20, p = 0.39). The graders agree on each discordant attempt's files except where the table above says otherwise, so these are two different agent runs, not two graders. Six of the 41 have a cause in the environment or the grading:

- `adaptix-name-mapping-aliases`, `query-persist-restored-query-state` and `vulture-persistent-analysis-cache` (native only): the native agent edited an existing upstream test to match its change, and native graded the edited test.
  - On the same files SecureBench restores upstream's test and fails (N→S). This is recorded as stricter in each conversion.
  - The SecureBench agents' work failed on both graders.
- `cliffy-config-file-parsing` (native only): both agents exported a new file through `internal/deno.json`, which the scope leaves out (recorded, stricter). It cost N→S, and the SecureBench agent's own attempt too (`Unknown export './runtime/read-text-file'`).
- `feal-linear-cryptanalysis` (SecureBench only) and `rstan-to-pystan` (native only): the failing agent hit its time limit.

The other 35 are runs that went differently.

### Scope fidelity

168 of 177 native attempts keep the original grader's verdict when only the captured files are graded. Three have no N→s→N verdict (`build-pmars`, `hf-model-inference` and `pytorch-model-cli`, above). The 9 differences:

- The three by-design tasks that need a running process or a file mode: `pypi-server`, `kv-store-grpc` and `openssl-selfsigned-cert`.
- `make-doom-for-mips`: `/tmp` is not captured, and natively the agent's stale `/tmp/frame.bmp` failed the original test.
- `cliffy-config-file-parsing`: the `deno.json` exclusion above.
- Edited upstream tests in `mashumaro-flattened-dataclass-fields`, `query-persist-restored-query-state` and `vulture-persistent-analysis-cache`: the captured files do not include the agent's edits to upstream's test files, so the copy is graded with upstream's tests.
- `kcp-go-multiplexed-kcp-streams`: the race above.

## Differences between the two environments

The two environments differ by design in the ways below. The table names the task where we first saw each difference, in this or an earlier run of the study.

| Difference | First seen in | Favours |
|---|---|---|
| SecureBench allows only the pack's domains; natively the Terminal-Bench agent has the whole Internet | `train-fasttext` (pypi.org refused) | Native |
| Provider-hosted web search is off under SecureBench | `mteb-leaderboard` | Native |
| Packages installed with apt cannot be captured | `mcmc-sampling-stan` | Native |
| Pier's background-task setting let the agent end its session before its sampling run finished | `rstan-to-pystan` | SecureBench |
| The native verifier sees leftovers in the agent's container | `make-doom-for-mips`, `make-mips-interpreter` | SecureBench |
| Pier passes the instruction as an argument; SecureBench on standard input | all | none observed |
| Natively the agent's container holds the real token; under SecureBench only the relay does | all | none observed |

One recorded difference decided four native verdicts here: agents editing existing upstream tests to fit their change (`adaptix`, `mashumaro`, `query-persist`, `vulture`). All four are recorded as stricter in their conversions.

## Issues found during the run and how we handled them

No check, Oracle, expected value or upstream test was touched. Every attempt an issue could affect was rerun or regraded, whatever its result. Every replaced attempt is listed in `replaced-attempts.tsv` and in its task's `result.json`, with the reason.

| Issue | Kind | Fix | Attempts |
|---|---|---|---|
| The worker's resolver list had regained 1.1.1.1, which failed about 2 lookups in 3. The relay answered `502 OSError` on about 1% of model requests (11 November, 17:19 to 18:18) | Worker | The maintainer set the resolver to 8.8.8.8 only, at about 21:58 | 7 SecureBench attempts rerun |
| The worker's network failed intermittently from 17:16 to 17:31 on 11 November. Native verifiers that download uv (`Failed to connect to releases.astral.sh`) ran no test and wrote reward 0 | Worker | Rerun or regraded | 1 rerun (`video-processing` native, whose own N was affected); 2 regraded (`bn-fit-modify` N→s→N, `train-fasttext` S→N) |
| Docker's volume (100 GB) filled from 21:08 to 21:58 on 11 November. The cleanup loop removed a task's base images only once both campaigns had finished it, and GPT had not started | Measurement setup | The loop removes base images for the running campaign only | 29 rerun, of which 12 had crashed before writing a record, and 3 were valid but had logged `no space left on device` (`arcane-drift-detection-baselines` native, `termenv-preserve-ansi-resets` and `vitest-duration-sharding` under SecureBench); 3 regraded (`db-wal-recovery` S→N, both `vulnerable-secret` cross-grades) |
| A failed name lookup stopped one native agent (`EAI_AGAIN`, 21:26) | Worker | Rerun | 1 (`etree-xml-diff-patch` native) |
| SecureBench stopped with a host error, `cannot locate the stock interpreter's loader: b''`: replay's 60 s probe of the stock Python image printed nothing | SecureBench, transient | Regraded; reported to the maintainer | 1 regraded (`tengo-callable-instance-isolation` N→S) |
| Anthropic's API answered 503 on several requests, 13 November, 14:10 to 14:47 | Provider | Rerun | 4 SecureBench attempts rerun |
| Pier's build of `financial-document-processor`'s native agent image hung three times (`apt-get` failing with `no space left on device`, 600 s start limit, one retry each). | Worker | We stopped the hung builds; the same build then finished in 55 s, and the fourth start ran normally | 3 replaced, then 1 rerun |
| `equivalence.py` judges an attempt's validity from its agent run only, so a cross-grade that ran no test counts as a fail | Measurement tool | We searched every verifier log for network and disk failures; the hits are the regrades above | — |

More on the `financial-document-processor` row:

- The first start hung during the disk-full window. Pier gave up after its limit but left the hung build processes running.
- The later builds failed the same way while those were still running, although the volume had space.
- After we stopped all of them, the same uncached compose build finished in 55 s. We did not find the exact mechanism.

In every regrade and rerun the two graders agree on the attempt's files. On the redone cross-grades:

- `bn-fit-modify`, `db-wal-recovery`, `tengo-callable-instance-isolation`, `vulnerable-secret` and `video-processing` now pass on all five verdicts.
- `train-fasttext`'s S→N fails because the agent left no `/app/model.bin`, which agrees with S.

The earlier grades are kept in `raw/attempts/.../regrade-replaced-1/`.

## Time and cost

| | Agent time, median | Wall time per attempt, mean | Cost per attempt, mean | Total |
|---|---|---|---|---|
| Terminal-Bench, native | 46 s | 8.1 min | $0.13 | $8.94 |
| Terminal-Bench, SecureBench | 39 s | 6.3 min | $0.13 | $8.82 |
| DeepSWE, native | 203 s | 10.3 min | $0.60 | $67.28 |
| DeepSWE, SecureBench | 218 s | 8.3 min | $0.68 | $76.31 |

- Cost is Claude Code's list-price figure. The 360 final attempts cost about $161, and the replaced attempts that reached the model about $9.71 more.
- The five attempts stopped at their time limit wrote neither cost nor token counts, so they are not counted.
- Cache reads are 96% of input tokens (284 of 297 million).
- Wall time includes the cross-grades.

## Data

```
runs/sonnet-fidelity-run-2/
├── README.md                 this report
├── attempts.tsv              the 360 attempts above, one row each (equivalence.py report)
├── replaced-attempts.tsv     the 45 replaced attempts and why, all infrastructure
├── <task>/                   one folder per task, 180 in all
│   ├── result.json           both attempts' verdicts, cross-grades, time and cost, replaced attempts, notes
│   ├── native/
│   │   ├── securebench-record.json   SecureBench's verdict record of the native agent's files (N→S)
│   │   ├── verifier.json             the native verifier's reward and failing tests, for N and N→s→N
│   │   ├── candidate-manifest.json   every captured file: path, kind, size, hash
│   │   └── candidate.tar.gz          the captured files, when they total 10 MB or less
│   └── securebench/          the same for the SecureBench agent (S, and S→N in verifier.json)
└── raw/                      not part of this release; it stayed on the worker (about 112 GB)
```

- 336 candidates are included as files; 23 larger ones have their manifest only. `pytorch-model-cli`'s native candidate was never captured.
- A regraded attempt keeps its earlier grades in `raw/attempts/.../regrade-replaced-1/`; its `result.json` has `regrades_replaced: 1`.
- To rebuild this folder from `raw/` (not released): `python3 conversions/equivalence.py export runs/sonnet-fidelity-run-2/raw/attempts --out runs/sonnet-fidelity-run-2 --replaced runs/sonnet-fidelity-run-2/raw/replaced --notes runs/sonnet-fidelity-run-2/raw/scripts/notes.json`.
