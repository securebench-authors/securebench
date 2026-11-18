# Brief: review one conversion

Every review agent receives this text verbatim, followed by one line naming the conversion: `Conversion: conversions/<source>/<task>`. The reviewer never wrote or helped write that conversion. Nothing else is added except answers to questions the agent asks.

A reviewer reads two documents of this repository: this brief, which says how to review, and the converter's brief, `conversions/brief-convert.md`, which is the standard a conversion is checked against. Neither refers to any other document.

---

You are reviewing one conversion of an upstream benchmark task into a SecureBench task pack. You did not write it. The repository is `/home/user/securebench`. Your job is to find what is wrong, not to confirm that it is right. Assume that the candidate code the task will grade is adversarial.

## 1. Read first

1. This brief, in full.
2. `conversions/brief-convert.md`, in full. It is what the converter followed: how SecureBench grades, the pack format, the conversion rules, the candidates, `CONVERSION.md` and qualification. Every rule in it is something you check.
3. The whole upstream task under `conversions/upstream/<source>/` (for DeepSWE, `tasks/<task>`), every test that checks what the task asks for included. Regression tests that run by outcome (converter brief, Section 5, "Never trust a test report") need reading only as far as choosing how to run them.
4. The whole conversion: pack, candidates, `CONVERSION.md` and `qualification.json`.

Other conversions in `conversions/` follow earlier versions of these briefs and may contradict them. Do not use them as examples.

## 2. What to check

Check each of these nine points explicitly. Section numbers refer to `conversions/brief-convert.md`.

1. **Instructions.** Compare `instructions.md` with upstream `instruction.md` byte for byte (`cmp`). Any difference must be listed as a fidelity change.
2. **Scope.** The scope covers every solution the instructions allow, and excludes test files wherever the language keeps them, including files beside the sources (Go's `_test.go`) and convention-loaded files (`conftest.py`, package initializers), so a candidate cannot rewrite the specification. Check exclude patterns against their real matching rules (4.6), and look for baseline symlinks that lead out of a scope root.
3. **No expected value or test input leaks.** No expected value is in `public/`, in `evaluation/`, in the baseline image inside the scope, or in anything the candidate's changes can alter. Nothing in `evaluation/` decides an expected value (Section 5, "Test inputs"): no test bodies, no classes or literals from a test file, and no upstream test file except a stand-in without test bodies. For each test, check that an agent that knows `evaluation/`, `hidden/oracle.py` and the instructions could not work out its expected values. Inspect the baseline image itself, not only the pack. When an allowed domain makes the answer reachable, `CONVERSION.md` records it under "## Limitation: answer reachable through an allowed domain" (Section 4.7).
4. **Challenges.** No challenge leaks hidden material beyond what its own case needs.
5. **Cases.** Every case comes from an upstream test, and none was added (Section 5, "Cases"). The seed is used only where upstream's tests draw random values themselves.
6. **Oracle.** Every expected value comes from a data file under `hidden/`, and `oracle.py` holds only judging logic (Section 5, "Expected values"), except where `CONVERSION.md` records upstream tests that draw random inputs. It checks every required field, counts the way upstream's test counts, bounds its work over candidate data, ignores the candidate's claims, and follows the rules in Section 5, "Oracle". Where regression tests run by outcome (Section 5, "Never trust a test report"), the feature tests still return values, the test files and every convention-loaded file come from the baseline, and `CONVERSION.md` records the limitation.
7. **Candidates.** Each mutant runs real code, is aimed where the conversion's check is least like upstream's assertion, and gets the same verdict from both graders. Each attack tampers with grading in a way this task allows. A forged record or report that carries only values a candidate could hardcode (upstream's public expected values) is outside SecureBench's scope and is not a finding; one that passes a check whose expected value is hidden, or makes the Oracle accept a value it never sees, is. The reference is the upstream solution with only the additions Section 6 allows.
8. **Divergences.** Every divergence from native is explained, and the explanation holds up.
9. **Inventory.** The inventory row is correct, and any exclusion reason (Section 11) holds for every possible conversion.

In addition, for each upstream test assertion, find where the conversion checks it or where `CONVERSION.md` says why it does not. An assertion that is silently dropped is a finding. So is any fidelity change listed without a stricter, more lenient or equivalent label and a reason.

## 3. Order of work

The converting agent may still be running `campaign.py qualify` when you start, and its "Divergences from native" may not be written yet.

1. Run `uv run securebench validate conversions/<source>/<task>/task` and note the pack digest it prints.
2. Check points 1 to 7, 9 and the upstream assertions.
3. If they already need changes, write the review now with verdict `changes needed`, and write "not yet checked: qualification still running" for point 8.
4. Otherwise, unless `qualification.json` exists and every SecureBench run in it records the digest you noted, end with the one line `Waiting for qualification`. You will be resumed when the converter has reported.
5. Check point 8, then write the review. `approved` requires that `qualification.json` reports no problems and that every SecureBench run in it records the digest you noted. If the digest changed while you reviewed, re-check what changed before you decide.

You may run commands to confirm a finding, such as `securebench validate`, single `securebench run`s, or a new attack script written in your scratch subdirectory `<task>-review`. Use the run command of Section 9 and follow the rules of Section 10, "Shared machine".

## 4. Where you may write

Only the `## Review` section at the end of `CONVERSION.md`. Do not change the pack, the candidates or anything else; the converting agent fixes findings.

## 5. The review section

```markdown
## Review

Reviewer: <agent id>, <date>

1. <point 1: what you checked, how, and the result>
...
9. <point 9>

Findings:
- <each problem: file and line, what is wrong, why it matters>

Verdict: approved | changes needed
```

`approved` means you found nothing that would let a candidate tamper with grading, make a SecureBench verdict differ from the native one without a reason, or leave a difference from upstream unexplained.

Write plainly and directly.
