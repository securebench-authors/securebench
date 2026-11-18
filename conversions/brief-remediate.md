# Brief: remediate one conversion

Every remediation agent receives this text verbatim, followed by one line naming the conversion: `Conversion: conversions/<source>/<task>`. Nothing else is added except answers to questions the agent asks. The agent never wrote or reviewed that conversion.

A remediation agent reads two documents of this repository: this brief, which says what to change, and the converter's brief, `conversions/brief-convert.md`, which is the standard the result must meet. Neither refers to any other document.

---

You are bringing one existing conversion of an upstream benchmark task into line with the current converter brief. The repository is `/home/user/securebench`. Another agent will review the result in full, and human reviewers at a research venue may read it, so every change must be visible and justified in the files you write.

## 1. Why this pass exists

The conversion was made under earlier versions of the converter brief. Those versions asked converters to add cases and inputs that upstream's tests do not have (hidden or seeded cases, generated scenarios, randomized names), to make some checks stricter than upstream's assertions, and to write attacks that hardcode public or upstream answers. The current brief forbids all of this: a conversion keeps upstream's cases and assertions exactly, and only moves them into SecureBench's architecture with its security guarantees. It also keeps every expected value and challenge in data files under `hidden/`, never in `oracle.py`.

Your job is to make this pack test exactly what upstream's tests test, and to keep everything else the converter built: the scope and its excludes, the adapter and driver, the protections against tampering with grading, and the fixes for differences the platform forces. That work was reviewed and is the purpose of the conversion.

## 2. Read first

1. This brief, in full.
2. `conversions/brief-convert.md`, in full. It is the standard: everything in the remediated conversion must follow it.
3. The whole upstream task under `conversions/upstream/<source>/` (for DeepSWE, `tasks/<task>`), every test that checks what the task asks for included. Regression tests that run by outcome (converter brief, Section 5, "Never trust a test report") need reading only as far as choosing how to run them.
4. The whole conversion: pack, candidates, `CONVERSION.md` and `qualification.json`. The existing `qualification.json` records each candidate's native verdict; you need it in Section 4, step 5. It is also in git: `git show HEAD:conversions/<source>/<task>/qualification.json`.

Other conversions in `conversions/` follow earlier versions of the briefs and may contradict them. Do not use them as examples.

## 3. Where you may write

Only inside `conversions/<source>/<task>/`. Do not edit anything else, do not commit, and do not change `conversions/inventory.tsv`. If something outside your folder prevents a correct remediation, or a rule cannot be met, stop and describe it in your report; the coordinator decides.

`CONVERSION.md` ends with the earlier `## Review` section. Rename its heading to `## Review before remediation` and leave its text unchanged; the new reviewer appends a fresh `## Review`.

## 4. What to do

1. **Map every check to upstream.** For each check, case and assertion in the pack, find the upstream test and assertion it comes from. Write the map in `CONVERSION.md` under "How upstream's tests map to checks": one row per assertion of the tests that check what the task asks for, with the check and case that carry it, and for regression tests that run by outcome one line with how they run and how many there are. Everything in the pack that no upstream test accounts for is an addition.
2. **Remove the additions.** Remove every case, input, check and assertion that upstream's tests do not have, with the Oracle code, data files and derivation scripts that served only them. Remove every use of randomness that upstream's tests do not have, such as seeded scenarios, randomized names or inserted blank lines, and use upstream's fixed values instead; the seed is used only where upstream's tests draw random values themselves. Keep what protects grading from tampering: the scope and its excludes, adapters that never trust a test report, the Oracle's safety rules. The test: an addition can fail a candidate that upstream's tests pass because of what the candidate computes; a protection only stops a candidate from tampering with how it is graded.
3. **Restore anything dropped.** An upstream assertion with no check and no recorded reason gets its check back, or a fidelity change in `CONVERSION.md` that says why it cannot be checked. Effort is never a reason. Upstream's regression tests (for DeepSWE, the pass-to-pass tests) count too. Keep those the pack already checks by value; run the rest with upstream's own runner, as the converter brief, Section 5, "Never trust a test report", allows, instead of transliterating them.
4. **Move expected values and challenges into data files.** Every expected value and every challenge leaves `oracle.py` for data files under `hidden/` (converter brief, Section 5, "Expected values"). `oracle.py` keeps only judging logic. The only exception is an upstream test that draws random inputs at run time, which `CONVERSION.md` then records.
5. **Check the old mutants that caught additions, before you change any candidate.** In the existing `qualification.json`, find the mutants whose native result is a pass (a reward of 1.0) while SecureBench said `failed`: those were failed by an addition. Run each of them once against the remediated pack with `securebench run` (converter brief, Section 9, step 2), in parallel where memory allows. Each must now pass. One that still fails means an addition is still in the pack: fix the pack, never the mutant. Do not run the other old mutants for this step; the ones you keep run in `qualify` against native anyway. Record the table (mutant, native verdict, SecureBench verdict before and after remediation) in `CONVERSION.md`.
6. **Bring the candidates in line with the converter brief, Section 6.** Delete every attack that does not tamper with grading, such as one that hardcodes public or upstream values; such cheats are outside SecureBench's scope. Keep the attacks that tamper with grading, and make sure at least one is aimed at this task. Keep the mutants aimed where the conversion's check is least like upstream's assertion; delete the mutants that existed only to exercise removed additions. Keep at most five mutants and three attacks (converter brief, Section 6), choosing the ones that test the most; a candidate added for a review finding replaces a weaker one. Change `reference.sh` only if it no longer meets Section 6.
7. **Update `CONVERSION.md`** to the template of the converter brief, Section 7. Remove fidelity changes that described removed additions and the section "Answer already public upstream", and keep the map from step 1 and the table from step 5. Add a section "Remediation" listing what you removed, restored and moved, and which candidates you deleted and why. Update the inventory note `CONVERSION.md` proposes.
8. **Qualify and hand over** with the converter brief's working loop, Section 9, steps 4 to 6: start `campaign.py qualify` in the background, send `Ready for review: conversions/<source>/<task>` to `main`, change nothing in `task/` or `candidates/` while it runs, and explain every divergence from native.

If the additions cannot be removed without rewriting most of the pack, for example because the adapter or driver exists only to serve generated cases, stop before changing anything and report `Needs reconversion: <reason, with file and line>`. The coordinator decides.

## 5. Shared machine

Follow the converter brief, Section 10, exactly. Your scratch subdirectory is `<task>-remediate`.

## 6. Report

End with a short report:

- what you removed, restored and moved, by file;
- the candidates you deleted and kept;
- the table from step 5;
- the final `qualify` output;
- anything you are unsure about or that the reviewer should look at first.

Write plainly and directly.
