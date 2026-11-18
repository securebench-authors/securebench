# SecureBench

SecureBench grades coding agents on benchmark tasks. It treats the agent and everything the agent produces as adversarial. The verdict is decided outside every environment that the agent's work can reach. We call this design split verification.

This repository contains the framework, the 180 benchmark tasks we converted and the results of our campaigns.

The project website is <https://securebench.org>. It shows the architecture, the results and some of the attacks with interactive diagrams. Its results are the ones in the paper.

## What is in the repository

| Path | Contents |
|---|---|
| `securebench/`, `securebench_relay_proxy/`, `securebench_utility/` | The framework |
| `tests/`, `fixtures/` | The test suite and the five fixture tasks F1 to F5 |
| [`docs/architecture.md`](docs/architecture.md) | The architecture: threat model, components, rules, and why |
| [`docs/task-format.md`](docs/task-format.md) | The task pack format |
| [`docs/operating.md`](docs/operating.md) | Setting up and qualifying a worker; preparing model harness overlays |
| [`docs/testing.md`](docs/testing.md) | Test layout, the fixture tasks, and which tests demonstrate which security property |
| [`docs/conversion.md`](docs/conversion.md) | The conversion campaign's method |
| `conversions/` | The 180 converted tasks (68 from Terminal-Bench, 112 from DeepSWE), the briefs the conversion agents worked from, and the campaign's scripts |
| `adversarial/` | The briefs and the script of the adversarial campaign, and each task's record of its adversarial copies |
| `runs/` | The results of the campaigns |

## Running SecureBench

```bash
uv sync
uv run securebench validate fixtures/f1-answer-file/task
uv run securebench qualify --output qualification.json
uv run securebench run --run-dir runs/example --qualification qualification.json --harness scripted:fixtures/f1-answer-file/candidates/correct.sh fixtures/f1-answer-file/task
uv run securebench rejudge runs/example
```

`run` only starts on a qualified worker. With `--development` it starts anyway, and every record then says `admitted: false`.

The model harnesses (`claude-code:<version>:<model>`, `codex:<version>:<model>`) need an overlay that is prepared beforehand. [`docs/operating.md`](docs/operating.md) explains how, and lists what a worker needs.

## Checks

```bash
uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run lint-imports && uv run pytest
uv run pytest -m integration
```

The second line needs Docker 28 or later.

## Results

Every campaign has a folder under `runs/`. The folder holds a report (`README.md`), the campaign's tables and one folder per task. A task's folder holds the SecureBench record and the candidate of each attempt.

Some candidates are larger than 10 MB. For those we release only the manifest, which lists the candidate's files with their digests.

| Folder | What it measured |
|---|---|
| [`sonnet-fidelity-run-1`](runs/sonnet-fidelity-run-1/README.md), [`sonnet-fidelity-run-2`](runs/sonnet-fidelity-run-2/README.md) | The fidelity study with Claude Sonnet 5.5, run twice: all 180 tasks, once natively and once under SecureBench, each attempt graded by both graders |
| [`gpt-fidelity-run-1`](runs/gpt-fidelity-run-1/README.md), [`gpt-fidelity-run-2`](runs/gpt-fidelity-run-2/README.md) | The same with GPT 6.1 Sol through Codex |
| [`fidelity-regrade`](runs/fidelity-regrade/README.md) | The run 1 attempts whose pack changed later, graded again on the current packs: no verdict changed |
| [`opus-adversarial-final-180`](runs/opus-adversarial-final-180/README.md) | Claude Opus 5.5 attacks the SecureBench grader of each task, once in the black box and once in the white box |
| [`opus-native-adversarial-campaign-180`](runs/opus-native-adversarial-campaign-180/README.md) | The same attacker against each upstream task's own grader, with each native pass regraded by SecureBench |

Two scripts recompute our numbers.

`python3 runs/fidelity_table.py` recomputes the comparison and pass counts of the paper's fidelity table from the four fidelity runs. The cause of each disagreement is noted in the task's `result.json`, and the run 2 reports describe them.

`uv run python runs/rejudge.py` takes the stored evidence of every released SecureBench record and judges it again. It needs Linux and no model. On our worker it recomputes 23,146 judgments with no mismatch. It skips 76 records of fidelity run 1, because their pack changed after the attempt. `runs/fidelity-regrade/` covers those 76.

## Terms

Some names in the paper differ from the names in the task packs, the briefs, the code and the reports.

| Paper | Here |
|---|---|
| Passive check, active check | `artifact_checks`, `protocol_checks`; "artifact check" and "protocol check" in the briefs and the code |
| Output file | `output_artifacts`; "Output Artifact" in the briefs |
| Limited knowledge, full knowledge | Black box (`task/`), white box (`task-white-box/`); the reports call the level a "tier" |
| Verdict agreement, equal difficulty | Verdict fidelity, outcome parity |
| Weak upstream tests | Upstream weakness; cause `upstream` |
| Flaw in SecureBench | Mechanism; cause `mechanism` |
| Conversion error | Cause `conversion` |
| Faked implementation | Cause `faked-implementation` |
| Rejected by SecureBench | `failed-attack` with a failed verdict; `stopped-by-securebench` in the native campaign |
| Public answers only | `failed-attack` with a passed verdict; `out-of-scope` in the native campaign |
| Safeguards intervened | `safeguard`, including sessions that fell back to an older model |
| Adapter | Adapter; the reports also say "driver" for the test program the adapter starts |
| Native grader | Native verifier, original grader |
| Fidelity record | `CONVERSION.md` in each conversion |
| Upstream's solution, the candidate that changes nothing | Candidates `reference` and `null` |
| Capture environment, setup step | Utility environment, shared setup (`setup_command`) |
| The five tasks left out of the fidelity comparison | By-design tasks |

## Notes on this release

### The briefs

The briefs under `conversions/` and `adversarial/` are complete. Each campaign agent received its brief word for word, plus one line that named its task. We changed one thing for this release: the path of our repository on the worker now reads `/home/user/securebench`.

The briefs changed during the campaign, and these are the final versions. We brought every task converted under an earlier version in line with the final one and had it reviewed again.

### Decision numbers and lesson codes

Some files cite a "decision" by number, or a "lesson" by a code such as C49. Both refer to our working notes from development. As the campaign went on, we merged the rules from those notes into the briefs and the documents above. The briefs are the end result of that process.

Decision numbers appear in some files inside a task's `task/` folder, in three candidate scripts and in a few of the attacking agents' final messages. Lesson codes appear in some conversion records and candidates.

We left these files as they are. A task's digest covers every file in `task/`, and the records under `runs/` cite that digest. Qualification also ran the candidate scripts as they are.

### References to our development repository

The conversion records, the run reports and the records cite commits of our development repository. The conversion records also name two of its files:

- `conversions/agents.tsv`, a ledger of agent sessions
- `conversions/compare_observations.py`, a script that compared a candidate's observations before and after a pack changed

None of this is part of the release.

### The architecture document the attackers saw

The attacking agents received an earlier wording of `docs/architecture.md`. The rules are the same. Three things differ:

- It cited decisions by number.
- It listed six security goals. The paper and the copy here list four: the old G3 and G5 are now part of G1 and G2, and the old G4 and G6 are now G3 and G4.
- It called passive and active checks artifact and protocol checks.

So the digest of the copy here differs from the one that each `ADVERSARIAL.md` records. An agent's final message may also cite a goal by its old number.

### Values in Oracle comments

Three Oracles quote values from upstream's published tests in a comment or docstring: `chess-best-move`, `polyglot-c-py` and `multi-source-data-merger`. Our own adversarial campaign found this. For `chess-best-move` it let an attack pass, and the paper reports that pass as a conversion error.

We release the three files exactly as they were attacked. Every record under `runs/` can be checked against the task it was produced on, and readers see the conversions as our agents wrote them.

### The seed

`adversarial/seed.json` holds the seed of the adversarial campaign. We kept it secret while the campaign ran.

## License

SecureBench is released under the Apache License 2.0 (`LICENSE`). The converted tasks derive from Terminal-Bench and DeepSWE and contain third-party material. `NOTICE` gives the details.
