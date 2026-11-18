# fix-git

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/fix-git

The baseline is upstream's `alexgshaw/fix-git:20251031`, pinned by the digest `docker pull` reported (`sha256:61e431c0...`). In it, `/app/personal-site` is on `master` at `d7d3e4b` with a clean working tree. The reflog shows the lost commit `650dba4` ("Move to Stanford"), made on a detached HEAD at `c4e38a1`, the parent of `master`. It changes `_includes/about.md` and `_layouts/default.html`. `master` also changed `_includes/about.md` after `c4e38a1`, so a plain `git merge` of the lost commit conflicts in that file. The baseline also holds upstream's reference copies of both files in `/app/resources/patch_files`, byte for byte the same as `environment/resources/patch_files` in the upstream repository (checked with `cmp`).

## How upstream's tests map to checks

Upstream's `tests/test_outputs.py` has two tests, each with one assertion, and nothing else. It checks no Git state. There are no regression tests.

| Upstream test and assertion | Check | Case | How |
|---|---|---|---|
| `test_about_file`: `md5(read("/app/personal-site/_includes/about.md").strip()) == md5(read("/app/resources/patch_files/about.md").strip())` | artifact check `about` | none (artifact check) | reads the file with the `text` parser (16 MiB bound). The Oracle compares it, stripped of the six ASCII whitespace characters that `bytes.strip()` removes, with `hidden/about.md` stripped the same way. |
| `test_layout_file`: the same for `_layouts/default.html` and `/app/resources/patch_files/default.html` | artifact check `layout` | none (artifact check) | the same against `hidden/default.html`. |

Nothing has to run at grading time, so the pack has no protocol check and no adapter. The expected values are `hidden/about.md` and `hidden/default.html`, copied from upstream's `environment/resources/patch_files`, which `setup.sh` committed as the lost commit. `plan` reads them, and they travel only in the artifact contexts. `oracle.py` holds no expected value: it maps each check id to the path it reads and the name of its hidden file, and compares.

## Fidelity changes

- **Expected values (stricter).** Upstream compares each file with its copy in `/app/resources/patch_files`, which is in the baseline and writable by the agent. Here the expected contents are the same files in `hidden/`. `attack-rewrite-reference` (the same wrong text in both files and both copies) and `attack-empty-reference` (all four emptied) pass upstream and fail here.
- **Comparison (equivalent).** Upstream compares the MD5 of the stripped bytes; the Oracle compares the stripped text itself, which accepts the same files short of an MD5 collision. `bytes.strip()` removes exactly ` \t\n\r\x0b\x0c`, and the Oracle strips exactly these six characters from the decoded text, not Python's wider `str.strip()` set. UTF-8 encodes them as single bytes that never occur inside a multi-byte character, so the result is the same. A file that is not UTF-8 or starts with a byte-order mark is unparsable here and fails. It fails upstream too, because the expected files are UTF-8 without a byte-order mark. The differential below confirms this, and `mutant-echo-trailing-newline` exercises the stripping on a real candidate.
- **File size (stricter, negligible).** The artifact checks read at most 16 MiB, the largest the format allows. Upstream reads files of any size, so the correct text followed by more than 16 MiB of trailing whitespace passes upstream and fails here (status `too_large`).
- **Symlinks (stricter, negligible).** Upstream opens the paths and follows symlinks. Here a deliverable that is a symlink fails. A symlink out of the repository, for example to `/app/resources/patch_files/about.md`, fails capture (it leaves the scope). A symlink to another file in the repository is captured, because the root allows internal symlinks, but it is not a regular file and the check fails. No Git operation leaves either file as a symlink, because the repository tracks both as regular files.
- **No test runner (stricter).** Upstream decides by pytest's exit status. Here no test runs, and the Oracle compares the files. `attack-conftest` plants `/pytest.ini` and `/conftest.py`, which rewrite every pytest report to "passed". It passes upstream, and it fails here: both files lie outside the scope and are dropped, and the two deliverables are unchanged.
- **Scope (equivalent).** The single root is `/app/personal-site`, the working tree that holds both deliverables, with no excludes. Its `.git` stays excluded (the default), so commits, branches and the reflog are dropped from the candidate. This changes no verdict, because upstream checks only the two working-tree files. Changes outside the repository, including to `/app/resources`, are dropped. The bounds (100,000 entries, 2 GiB) are far above the baseline's 96 entries and 34 MB.
- **Git state not checked (equivalent).** The instructions say "merge them into master", but upstream checks only the working tree, so the pack does too. A check that the lost commit is an ancestor of `master` would reject solutions upstream accepts, such as a cherry-pick or a merge left uncommitted.
- **Allowed domains (stricter).** None, which is all the reference needs: it only runs `git` on the local repository. Upstream allows the Internet.
- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte (`cmp`).

### Differential against upstream's tests

`hidden/differential.py` builds 19 inputs per check around the acceptance boundary, to compare the Oracle's stripping with upstream's MD5 of `bytes.strip()` (converter brief, Section 5, "Reimplemented native tools"). They are a test of the comparison, not cases: the Oracle does not use the script. It runs upstream's `test_about_file` and `test_layout_file` verbatim on the baseline's Python 3.13, each input placed at the checked path with `/app/resources/patch_files` as the baseline has it. It also runs the framework's `text` parser binding and this Oracle on the stock Python. The module docstring gives the exact commands.

| Input (each for both files) | Upstream | Here |
|---|---|---|
| exact; trailing `\n`; all six ASCII whitespace characters before and after; padded with spaces to exactly 16 MiB | pass | pass |
| trailing `\x1c`, NBSP, U+0085 or U+2028 (all stripped by `str.strip()` but not by `bytes.strip()`); trailing NUL; trailing invalid UTF-8 byte; byte-order mark; CRLF line endings; last character dropped; one inner space doubled; empty; absent; a directory | fail | fail |
| padded with spaces to one byte past 16 MiB | pass | fail (`too_large`) |
| symlink to the copy in `/app/resources/patch_files` | pass | fail (not a regular file; in a real run, capture rejects the escaping symlink first) |

The 34 inputs that are not about the size bound or symlinks agree. The 4 that differ are the two stricter changes listed above.

### Candidates

| Candidate | What it does | Aimed at |
|---|---|---|
| `reference.sh` | upstream `solve.sh` unchanged, after `cd /app/personal-site`: takes the 4th reflog line's new hash, branches it, merges into `master` with `-X theirs` | |
| `null.sh` | nothing | |
| `mutant-reflog-off-by-one.sh` | reads the 3rd reflog line: the lost commit's parent, an ancestor of `master`, so the merge is "Already up to date" | finding the lost commit |
| `mutant-merge-ours.sh` | `-X ours` instead of `-X theirs`: the conflict in `about.md` keeps `master`'s text, and the layout merges correctly | `about` (conflict resolution) |
| `mutant-conflicted-file-only.sh` | finds the commit by its reflog message, tries a plain merge, aborts on the conflict and checks out only the conflicted `about.md` from it | `layout` (recovering every file) |
| `mutant-echo-trailing-newline.sh` | finds the commit by its reflog message and writes both files from `git show` through `echo "$(...)"`, which adds a trailing newline neither file has in the lost commit | the whitespace stripping, where the Oracle's comparison differs most from upstream's; both graders should accept it |
| `attack-rewrite-reference.sh` | the same wrong text in both files and both copies in `/app/resources/patch_files` | upstream's agent-writable reference copies |
| `attack-empty-reference.sh` | empties both files and both copies | the same, second form |
| `attack-conftest.sh` | `/pytest.ini` and `/conftest.py` that turn every pytest report into a pass | upstream's test runner |

## Mutants failed by an addition

No mutant in the earlier `qualification.json` had a native pass and a SecureBench `failed`: the reference passed both graders, and the null candidate and all three mutants failed both. So no old mutant was failed by an addition, and none needed a rerun.

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| (none) | | | |

## Remediation

The earlier conversion added no case, input or assertion: its two artifact checks are upstream's two assertions, its expected values were already in `hidden/`, and it uses no randomness. So nothing was removed from grading and nothing was restored.

- **Removed.** The section "Answer already public upstream", the fidelity bullet "Hidden cases", and the sentence in "Git state not checked" about the copy attack, all of which argued about hidden cases the current brief no longer asks for. References to lesson codes that the current brief does not define, from `CONVERSION.md`, the comments of `task/task.toml`, the docstrings of `task/hidden/oracle.py` and `task/hidden/differential.py`, and the comments of the three attacks. Each was replaced by the reason it stood for. No grading code or data changed.
- **Restored.** Nothing: both upstream assertions already had a check, and upstream has no regression tests.
- **Moved.** Nothing: `oracle.py` already held no expected value.
- **Candidates.** None deleted. The three attacks all tamper with grading (two rewrite upstream's reference copies, one rewrites pytest's reports), and none hardcodes a public answer. The three mutants each break a different part of the task with real Git work. Added `mutant-echo-trailing-newline.sh`, because no mutant was aimed at the whitespace stripping, the one place where the Oracle's comparison is not upstream's (converter brief, Section 6). `reference.sh` is unchanged.
- **`hidden/differential.py` kept.** It is not an addition to grading: the Oracle never reads it, and it is the comparison of the reimplemented strip-and-compare against upstream's tests that the converter brief, Section 5, requires.

## Proposed inventory note

converted. Faithful to upstream's two file comparisons; the expected files come from hidden/, so rewriting upstream's agent-writable reference copies in /app/resources/patch_files (native 1.0) or planting a conftest.py (native 1.0) fails here; Git history is not judged, as upstream. Remediated: no additions found.

## Divergences from native

The reference and `mutant-echo-trailing-newline` pass both graders, and the null candidate and the other three mutants fail both. Three attacks pass native and fail here:

- **`attack-rewrite-reference`: native 1.0, SecureBench `failed` (`oracle`).** It writes `All tests passed.` to both deliverables and to both copies in `/app/resources/patch_files`. Upstream compares each deliverable with its copy, which now matches. Here the Oracle compares with `hidden/`, and the changes to `/app/resources` lie outside the scope anyway. SecureBench is right: neither file holds the lost commit's version, so the changes were not recovered.
- **`attack-empty-reference`: native 1.0, SecureBench `failed` (`oracle`).** The same with all four files emptied: upstream compares two empty files. SecureBench is right for the same reason.
- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** It changes neither deliverable and plants `/pytest.ini` and `/conftest.py`, so upstream's pytest takes `/` as its rootdir and reports both failing tests as passed. Here no test runner decides, both planted files are outside the scope, and the unchanged `about.md` differs from the lost commit's version. SecureBench is right: nothing was recovered.

## Review before remediation

Reviewer: aa367634abd7508b1, 2026-10-13

Pack digest checked: `sha256:85c5fdda8c8b1d39e365b28c37a04f6698d6de291571b4c11124a8528c43dc05` (`securebench validate`, at the start and again after qualification).

1. `cmp task/instructions.md conversions/upstream/terminal-bench/fix-git/instruction.md` reports no difference. `CONVERSION.md` lists no instruction change. Upstream is pinned at `2fd12b88...`, the commit in `sources.toml` and the checkout's `HEAD`.
2. The scope is the single root `/app/personal-site` with no excludes, and `.git` stays excluded by default. Upstream reads only `_includes/about.md` and `_layouts/default.html` of that working tree, so every solution the instructions allow (merge with `-X theirs`, a hand-resolved merge, a cherry-pick, a checkout of the files from the lost commit) leaves its deliverables inside the scope. Dropping `.git` changes no verdict, because upstream checks no Git state. The project is static files with no test runner and no convention-loaded files, so nothing in the scope can rewrite the specification. In the baseline the working tree has 96 entries, 33.8 MB and no symlinks (checked in a `--network none` container), so the scope's bounds (the format maxima) and lesson A16 are not a concern. `symlinks = true` only avoids a capture failure; a symlinked deliverable is `not_regular` and fails, as listed.
3. The pack has no `public/` and no `evaluation/`. The expected values are only in `hidden/about.md` and `hidden/default.html` (byte for byte upstream's `patch_files`, by `cmp`). I inspected the baseline image: the same files are at `/app/resources/patch_files`, outside the scope, and as the dangling commit `650dba4` in `.git`. The Oracle reads neither (lesson C48). Both are disclosed under "Answer already public upstream" (lesson C58); the copy attack is the expected output itself, so it is not a wrong candidate passing.
4. No protocol check, so no challenge exists. The expected text travels only in the two artifact contexts, which stay on the host.
5. The deliverable is fixed by the baseline image and its answer is public upstream and in the baseline, so no hidden case can help. `CONVERSION.md` says so and names the passing copy attack, as lesson C58 requires.
6. The Oracle (`hidden/oracle.py`) rejects an unknown check id, non-artifact evidence, a malformed context, any evidence other than exactly one file at the declared path with no listings, any status but `present`, and a value that is not `Text`. Nothing is counted, so C52 does not apply. Work is one strip and comparison of at most 16 MiB plus a bounded line scan for the diagnostic (C54). No regular expressions, no paths or code from evidence, and the diagnostic does not quote the candidate's file. The stripping uses exactly the six bytes of `bytes.strip()`. I confirmed that the `text` parser (`securebench/evidence/parsers.py`) does not normalize line endings, so CRLF is not accepted by mistake. I re-ran `hidden/differential.py` (corpus on the host, native side on the baseline with upstream's `tests/` mounted, our side on the stock image, both `--network none --memory 1g`): 38 lines each, and they differ only in the 4 listed rows (padded past 16 MiB and symlink to the reference copy, for both checks), as `CONVERSION.md` states.
7. I ran the reference and the three mutants in baseline containers and compared the deliverables with `patch_files`: the reference matches both; `mutant-merge-ours` leaves `about.md` wrong; `mutant-reflog-off-by-one` leaves both wrong (merge of an ancestor); `mutant-conflicted-file-only` leaves `default.html` wrong. Each is real Git work aimed at one requirement (finding the commit, resolving the conflict, recovering every file). The attacks target this task's known weaknesses: the agent-writable reference copies (C48, in two forms) and a convention-loaded `conftest.py` with `/pytest.ini` (C49). All get `failed` with class `oracle`, never `invalid`. `reference.sh` changes upstream's `#!/bin/bash` to `#!/bin/sh`; the script is POSIX, and `docs/conversion.md` Section 3 requires candidates to be POSIX `sh`, so this changes no behavior.
8. `qualification.json` reports `problems: []`, 2 rounds, all SecureBench runs admitted, rejudged, on clean framework commit `81f715d...`, and every run records pack digest `sha256:85c5fdda...`, the one I noted (`campaign.py` `_consistency` checks every run, and the pack and candidates are unchanged since I read them). Reference passes both, null and the three mutants fail both. The three divergences are `attack-rewrite-reference`, `attack-empty-reference` and `attack-conftest` (native 1.0, SecureBench `failed`). Each explanation holds: upstream compares against copies the candidate rewrote or decides by a pytest outcome the candidate rewrote, while neither deliverable holds the lost commit's version, so SecureBench is right.
9. No inventory row exists yet; the coordinator adds it on approval. The task is in the campaign's selection, and `converted` is correct: no exclusion reason applies (no network, no privileges, no host actions; the deliverables are two plain files).

Upstream assertions: `test_about_file` and `test_layout_file` (stripped-MD5 equality with the reference copies) are the artifact checks `about` and `layout`. The changes (hidden expected values, text instead of MD5, 16 MiB bound, symlinks, no test runner, scope, no Git check, no domains) are each listed with a label and a reason. The "Hidden cases" bullet has no label, but it records that nothing was added, not a change.

Findings:
- None.

Verdict: approved

## Review

Reviewer: ad841bcbdca65eb0c, 2026-10-25

Pack digest checked: `sha256:84e478d5ab03da564e830d70586e9490be574c389c16bb914f2bee867bb4f4e1` (`securebench validate`, at the start and again after qualification had finished). Since the reviewed commit `4f9210e`, the only pack changes are comments in `task.toml` and docstrings in `hidden/oracle.py` and `hidden/differential.py` (checked with `git diff`). No grading code or data changed.

1. `cmp task/instructions.md conversions/upstream/terminal-bench/fix-git/instruction.md` reports no difference, and `CONVERSION.md` lists the instructions as unchanged.
2. The scope is one root, `/app/personal-site`, with no excludes, and `.git` is excluded by default. Both deliverables are working-tree files in it, so every solution the instructions allow (a merge resolved any way, a cherry-pick, a checkout of the files) is captured. Nothing runs at grading time, so no test file or convention-loaded file in the scope can affect the verdict. In the baseline (`--network none` container) the working tree is clean on `master` at `d7d3e4b`, holds 96 entries and has no symlinks, and `.git` is the only Git directory. So no symlink leads out of the root.
3. The pack has no `public/` and no `evaluation/`. `hidden/about.md` and `hidden/default.html` match upstream's `patch_files` byte for byte (`cmp`). In the baseline the expected contents appear only at `/app/resources/patch_files`, which is outside the scope, and in the lost commit inside the excluded `.git`. The task is to recover that commit. The Oracle reads neither copy. A candidate cannot change either location in a way that reaches the Oracle. No domain is allowed, so the domain limitation does not apply.
4. There is no protocol check and so no challenge. The expected text travels only in the two artifact contexts, which stay on the host.
5. There are no cases. The two artifact checks are upstream's two tests, and nothing was added. The seed is not used, and upstream draws no random values.
6. `oracle.py` holds only the check-to-path map, the six `bytes.strip()` characters and the comparison. The expected text comes from `hidden/`. It rejects any unknown check, non-artifact evidence, a malformed context, evidence other than exactly one file at the declared path, any status but `present` and any value that is not `Text`. It compares the stripped text in full, which is bounded at 16 MiB by the check, and its diagnostic never quotes the candidate's file. It uses no regular expressions and takes no path from the evidence. The `text` parser (`securebench/evidence/parsers.py`) rejects invalid UTF-8 and a byte-order mark and keeps `\r`. Both are equivalent to upstream: when a file's stripped bytes equal the expected stripped bytes, the file is valid UTF-8 without a byte-order mark. I re-ran `hidden/differential.py` as its docstring describes. The corpus was built on the host, the native side ran on the baseline with upstream's `tests/` and the Oracle side on the stock Python image, both with `--network none --memory 1g`. Each side gave 38 lines, and they differ only in `padded-past-16-mib` and `symlink-to-reference` for both checks. Those are the two stricter changes listed. No regression tests exist.
7. `reference.sh` is upstream's `solve.sh` with only a `cd`, a comment and a `#!/bin/sh` shebang, as Section 6's POSIX `sh` rule requires. The commands are POSIX. Each mutant runs real Git work:
   - `mutant-reflog-off-by-one` gets finding the commit wrong.
   - `mutant-merge-ours` gets the conflict resolution wrong.
   - `mutant-conflicted-file-only` recovers only one of the two files.
   - `mutant-echo-trailing-newline` exercises the whitespace stripping, the one place where the Oracle's comparison differs from upstream's MD5. It runs the same in dash and bash because neither file contains a backslash (checked with `grep`).

   Every mutant got the same verdict from both graders. The attacks target this task's routes: the agent-writable reference copies (two forms) and a `/pytest.ini` plus `/conftest.py` that rewrite pytest's reports. Each got `failed` (`oracle`) and never `invalid`.
8. `qualification.json` reports `problems: []`. Every SecureBench run is admitted, rejudged and not dirty, and every one records the pack digest I noted. The runs name two framework commits, `a1eeea4` and `8cb74dd`, but the only change between them is `conversions/agents.tsv`, so the SecureBench code is the same. The reference passes both graders, the null candidate fails both, and the four mutants agree. The native results of the reference, the null candidate and the three unchanged mutants are `native_cached`. That is valid because `campaign.py` keys the cache on the script, the scripts it calls and the non-script files in `candidates/`, and none of these changed. The three divergences are the three attacks (native 1.0, SecureBench `failed`). Each explanation holds: upstream compares against copies the candidate rewrote, or decides by pytest reports the candidate rewrote, while neither deliverable holds the lost commit's version.
9. `converted` with reason `-` is correct. No exclusion reason applies: no network, no privileges, no host actions, and the deliverables are two plain files. The current note in `conversions/inventory.tsv` line 30 still cites lesson codes and "No hidden case is possible". The coordinator should replace it with the "Proposed inventory note" above, which is accurate.

Upstream assertions: `test_about_file` and `test_layout_file` each make one assertion (stripped-MD5 equality with the reference copy), and they are the artifact checks `about` and `layout`. `test.sh` turns pytest's exit status into the reward, which the "No test runner" bullet covers. Every fidelity change has a label and a reason: hidden expected values, text instead of MD5, the 16 MiB bound, symlinks, no test runner, scope, no Git check and no domains. None of the reasons conflicts with the differential or the runs.

Findings:
- None.

Verdict: approved
