# Conversion campaign

A conversion turns one upstream benchmark task into a SecureBench task pack. Agents do the conversions, so the act of converting cannot be replayed byte for byte. We make it auditable instead, and make everything around it re-runnable.

| Layer | What a reviewer can redo | Needs |
|---|---|---|
| Selection | The same task list and the same reason for every exclusion, from pinned upstream commits | Git |
| Qualification | Every scripted candidate through SecureBench and the native harness, with the verdicts the converter brief requires | Docker, Pier, no model |
| Experiments | Every judgment from stored evidence (`securebench rejudge`, or `runs/rejudge.py` on the released records) | SecureBench on Linux, no Docker, no model |

Agents are Claude Opus 5.5 (`claude-opus-5-5`) at high reasoning effort. A coordinator, itself an agent session, starts them and passes messages. The maintainer is one of the authors. They work from the briefs, given verbatim with only the task or conversion name added: [`conversions/brief-convert.md`](../conversions/brief-convert.md) for the converting agent, [`conversions/brief-review.md`](../conversions/brief-review.md) for the reviewer and [`conversions/brief-remediate.md`](../conversions/brief-remediate.md) for the remediation agent. The briefs changed during the campaign. Every task converted under an earlier version was brought in line with the final one and reviewed again (Section 5). Beyond answers to an agent's own questions, the coordinator sends only the messages of the review loop, listed verbatim in Section 5, and an identical notice to every running agent when shared infrastructure changes under them (the SecureBench code or the worker record).

The coordinator checks the models in every running agent's transcript whenever it hears from the agent, and before every commit. An agent that has run a turn on any model other than its pinned one is stopped, its task goes on standby without an inventory row, and the coordinator moves to the next task in selection order.

## 1. Inputs

[`conversions/sources.toml`](../conversions/sources.toml) pins each upstream repository by commit, the selection seed, the quota per source and the Pier version. Both upstreams use the Harbor task format, and Pier runs both, so Pier is the one native harness.

```bash
uv tool install datacurve-pier==0.3.1
python3 conversions/campaign.py fetch
```

`fetch` clones each source into `conversions/upstream/` (not committed) and checks it is at the pinned commit with no local changes.

The upstream images are amd64, and qualification needs a qualified amd64 Linux worker.

## 2. Selection

```bash
python3 conversions/campaign.py order terminal-bench
```

prints every task of a source sorted by SHA-256 of `<seed>:<task>`. We triage tasks in that order until the quota is converted. Every task we look at gets one row in [`conversions/inventory.tsv`](../conversions/inventory.tsv): `converted`, or `excluded` with one reason from `conversions/brief-convert.md` Section 11 (or `model-safeguards`, for the one task where the provider's safeguards stopped the converter), and the row's `note` says why in one sentence.

## 3. One conversion

A conversion is one folder, `conversions/<source>/<task>/`, holding the pack (`task/`), the scripted candidates (`candidates/`), the fidelity record (`CONVERSION.md`) and `qualification.json`. What each contains, and every rule a conversion follows, is in [`conversions/brief-convert.md`](../conversions/brief-convert.md), Sections 3 to 8. The briefs are the single source of those rules; this document does not repeat them.

## 4. Qualification

```bash
python3 conversions/campaign.py qualify conversions/<source>/<task>
```

grades every candidate with SecureBench and the native harness and writes `qualification.json`; `conversions/brief-convert.md` Section 8 says what it checks. Only one qualification runs at a time on a worker, and its SecureBench runs are admitted against the worker's qualification record, `qualification.json` at the repository root (`docs/operating.md`).

A task is qualified when the command reports no problems and the review below passes. Re-running the command and diffing `qualification.json` shows whether a reviewer reproduced it.

## 5. Review

A second agent, which did not write the conversion, reviews it under [`conversions/brief-review.md`](../conversions/brief-review.md). It writes its findings as a `## Review` section at the end of `CONVERSION.md`, ending with `Verdict: approved` or `Verdict: changes needed`.

### The review loop

The review overlaps the converter's qualification.

1. The converter sends `Ready for review: conversions/<source>/<task>` when it starts `campaign.py qualify`. The coordinator starts a reviewer with `conversions/brief-review.md`, or, in later rounds, sends the same reviewer message R.
2. The reviewer checks points 1 to 7 and 9 at once. If they need changes, it writes the review with `changes needed` and point 8 marked as not yet checked. Otherwise it reports `Waiting for qualification`, and the coordinator sends it message Q once the converter has reported.
3. On `changes needed`, the coordinator sends the converter message F, and the loop starts again at step 1.
4. On `approved`, the coordinator checks that `qualification.json` reports no problems and that its runs record the pack digest the reviewer noted, adds the inventory row and commits. It then runs `python3 conversions/campaign.py committed conversions/<source>/<task>`, which checks that the pack as committed has the digest the qualification records. Run without arguments, it checks every conversion.

When the maintainer reopens an approved conversion, the coordinator sends its converter message O and, on `Ready for review`, its reviewer message P, both with the same `<change>`; the loop then continues from step 2.

A converter that sends `Pack changed` during a review has changed what the reviewer is reading; the reviewer's digest check catches it. The messages, verbatim, with `<source>/<task>` filled in:

- **F** (to the converter): "The independent review of your conversion is done, with verdict "changes needed". The findings are in the `## Review` section at the end of `conversions/<source>/<task>/CONVERSION.md`. Fix every finding in your pack, candidates and `CONVERSION.md`. Do not edit the `## Review` section, and leave the inventory row to the coordinator. Follow the same brief as before, including its working loop and the "Shared machine" rules. If your fixes change only `CONVERSION.md`, which is outside the pack, keep the existing qualification: send `Ready for review` without running `qualify` again. End with a short report: what you changed for each finding, and the final `qualify` output. Report only changes you have actually made and checked in the files."
- **R** (to the reviewer): "The converting agent reports that it has addressed your findings on `conversions/<source>/<task>`. Review the conversion again under the same brief. Check that each finding is really fixed, and re-check the nine points wherever the changes reach. Replace your `## Review` section with the new review, dated today, and give a new verdict."
- **Q** (to a reviewer waiting for qualification): "The converter of `conversions/<source>/<task>` has reported and its qualification has finished. Complete your review under the same brief: point 8, the digest check and the verdict."
- **O** (to the converter of an approved conversion that the maintainer reopens to make a stated change): "The maintainer has reopened your approved conversion `conversions/<source>/<task>` with this change: <change>. Read `conversions/brief-convert.md` again in full: it may have changed since your conversion, and the current version applies. Make the change in your pack, candidates and `CONVERSION.md`, so that the whole conversion follows the current brief, and update the inventory note `CONVERSION.md` proposes. Do not edit the `## Review` section, and leave the inventory row to the coordinator. Follow the brief's working loop and its "Shared machine" rules. Run `qualify` again and send `Ready for review` when it starts. End with a short report: what you changed, and the final `qualify` output. Report only changes you have actually made and checked in the files."
- **P** (to the reviewer of that conversion, after the converter's `Ready for review`): "The maintainer reopened `conversions/<source>/<task>` after your approval, with this change: <change>. The converting agent reports that it has made the change. Read `conversions/brief-review.md` and `conversions/brief-convert.md` again in full: they may have changed since your review, and the current versions apply. Review the conversion again under them. Check that the change does what it states, and re-check the nine points wherever the change reaches. Replace your `## Review` section with the new review, dated today, and give a new verdict."
- **B** (to an agent whose brief changed while it worked, before any other message it is due): "`<brief>` has changed since you started. Read it again in full; the current version applies to all of your remaining work."
- **U** (to any agent after an interruption, such as an account usage limit): "Your session was cut off and can now continue. Anything you started in the background may have stopped. Check what finished before relying on it, then continue where you left off and end with the report your brief asks for."

### Remediation

Packs converted under earlier briefs are brought in line with the current briefs by a fresh agent each, never the one that converted the task. Its first message is [`conversions/brief-remediate.md`](../conversions/brief-remediate.md) verbatim, followed by `Conversion: conversions/<source>/<task>`. When it sends `Ready for review`, the coordinator starts a fresh reviewer with `conversions/brief-review.md`, which reviews the whole conversion. The review loop then runs as above, with message F going to the remediation agent. An agent that reports `Needs reconversion` is stopped, and the maintainer decides. On approval the coordinator commits the pack and updates its inventory note.

### Moving test inputs into hidden data

Packs whose test inputs sat in code under `evaluation/` were changed so that whatever decides an expected value reaches the Evaluation only in its case's challenge (converter brief, Section 5, "Test inputs"). A fresh agent that never converted, reviewed or remediated the pack made the change. The coordinator then checked that every expected value in `hidden/` was unchanged, that every candidate kept its SecureBench verdict, and that the reference candidate's observations were the same on the old and the new pack. A second fresh agent audited the changed pack. Where a check failed or the change went further, a fresh reviewer reviewed the whole conversion under `conversions/brief-review.md`.

### Known limitations of converted tasks

These hold for some converted tasks by design, and the paper discusses them. Each affected conversion records its limitation in a section of `CONVERSION.md` with a fixed heading, so the rows can be listed with `grep -l` over `conversions/*/*/CONVERSION.md`:

- **Regression tests graded by outcome**, heading `## Limitation: regression test outcomes`. The tests upstream runs only to check that existing behavior still works (DeepSWE's pass-to-pass tests) run with upstream's own runner, and the Oracle accepts each test's outcome. The candidate's code runs inside the runner and could forge these outcomes, as it can natively. The feature tests are still graded by value, so a forger must still produce the right values there.
- **Answer reachable through an allowed domain**, heading `## Limitation: answer reachable through an allowed domain`. The reference needs a domain that also serves the answer, for example upstream's hidden test data in its public repository on `github.com`. The pack keeps the domain, as native allows the whole Internet, so an agent that looks there can read the expected values during its run.
