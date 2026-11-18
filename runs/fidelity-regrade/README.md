# Fidelity run 1, regraded on the current packs

Some packs changed after the first fidelity run: test inputs moved into hidden data, and a few Oracles and adapters were corrected. The run 1 attempts on those packs were graded on the earlier version of the pack.

We therefore graded their stored candidates again on the current packs. No model ran: the files each attempt left were graded again by SecureBench.

- **What was regraded:** every run 1 attempt whose SecureBench grade was given on a pack that later changed. That is 96 attempts on 24 tasks: 48 from `sonnet-fidelity-run-1` and 48 from `gpt-fidelity-run-1`. For an attempt under SecureBench this is its own grade. For a native attempt it is SecureBench's grade of the native agent's files (N->S). Native grades were not redone, because they depend only on the upstream task.
- **Result:** no verdict changed. 67 attempts pass and 29 fail, as before, with the same failure classes. `securebench rejudge` reproduced every regraded verdict.
- **Records:** `results.tsv` has one row per attempt: the run, the task, the side, the earlier verdict, the verdict on the current pack, that pack's digest, the framework commit and whether `rejudge` reproduced it. The digest in each row is the digest of the pack in `conversions/`. The regrade's own run folders stayed on the worker.

One further pack changed after run 1 and was not regraded: `helm-unified-manifest-stream`. Its scope now excludes `.gocache`, and its plan of checks and cases is unchanged. Its four run 1 attempts passed under both graders, as they did in run 2. `runs/rejudge.py` recomputes their judgments.

`runs/rejudge.py` skips the run 1 records whose plan changed, because their stored evidence belongs to the earlier pack. This table is the check for them.
