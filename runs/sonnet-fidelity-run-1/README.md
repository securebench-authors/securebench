# Sonnet 5.5 fidelity study, run 1

This is the first of the two runs of the fidelity study with Sonnet 5.5. It covers all 180 converted tasks. The second run is [`sonnet-fidelity-run-2`](../sonnet-fidelity-run-2/README.md), and its report describes the method, the verdict names and the differences between the two environments. This run used the same method and settings.

- **Model and harness:** `claude-sonnet-5-5` at medium reasoning effort, through Claude Code 2.1.289 on both sides.
- **Attempts:** each task has one native attempt and one attempt under SecureBench, 360 in all. Each attempt's files are also graded by the other grader.
- **Batches:** the run was made in three batches (100, 11 and 69 tasks), as the tasks were converted. `attempts.tsv` joins the batches.
- **Replaced attempts:** `replaced-attempts.tsv` lists 34 attempts that were replaced, each with the reason.
- **Packs that changed later:** some packs changed after their attempt. We graded the stored candidates of those attempts again on the changed packs, and no verdict changed. [`fidelity-regrade`](../fidelity-regrade/README.md) lists each regraded attempt.

`python3 runs/fidelity_table.py` computes the paper's fidelity table from this run and the second one, for both agents.

## Data

```
runs/sonnet-fidelity-run-1/
├── README.md
├── attempts.tsv              one row per attempt
├── replaced-attempts.tsv     the replaced attempts and why
└── <task>/                   one folder per task, 180 in all
    ├── result.json           both attempts' verdicts, cross-grades, time and cost, replaced attempts, notes
    ├── native/               the SecureBench record of the native agent's files, the native verifier's result, and the candidate
    └── securebench/          the same for the SecureBench agent
```

The other agent's first run is [`gpt-fidelity-run-1`](../gpt-fidelity-run-1/README.md).
