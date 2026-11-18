# sanitize-git-repo

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/sanitize-git-repo

## How the pack grades

The agent works in the Git repository `/app/dclm` (HEAD `8df3c81f`, checked
clean before the agent starts). Upstream's `tests/test_outputs.py` has three
tests; they map to three checks:

| Upstream test | Check | What it compares |
|---|---|---|
| `test_removal_of_secret_information` | artifact check `sanitized-files` | none of the five secrets occurs, case-insensitively, in the three contaminated files |
| `test_correct_replacement_of_secret_information` | artifact check `sanitized-files` | each contaminated file equals upstream's sanitized copy (`hidden/expected/`, copied byte for byte from upstream `tests/`) |
| `test_no_other_files_changed` | artifact check `other-files-unchanged` | every other path of commit `d6987af0` still holds the baseline's bytes and executable bit, from SecureBench's own hashes of the candidate |
| `test_no_other_files_changed` | protocol check `git-diff`, one case | commit `d6987af0` exists and `git diff d6987af0` names no path but the three contaminated ones |

`sanitized-files` reads the three files with the `text` parser. The Oracle
applies Python's universal-newline translation (`\r\n` and lone `\r` become
`\n`) to both sides before comparing, because the upstream test reads both with
`open(path, "r")`. The secrets and the expected files are in
`hidden/cases.json` and `hidden/expected/`.

`other-files-unchanged` lists `/app/dclm` and compares it with
`hidden/manifest.json`: the 535 paths of the upstream test's reference commit
`d6987af0` other than the three contaminated files, each with the SHA-256 and
executable bit the baseline holds. `hidden/derive_manifest.py` rebuilds it from
the baseline image (command in its docstring); it first checks that the
baseline's working tree differs from `d6987af0` only in the contaminated files
(it differs in `ray_processing/process.py`, which the two later commits
`849c29a9` and `8df3c81f` reformatted),
so the baseline's bytes are exactly what upstream's Git diff accepts. Paths that
are not in the manifest, such as new untracked files, are ignored, as Git's diff
ignores untracked files.

`git-diff` runs `evaluation/git_diff.py` in the Evaluation. It repeats the Git
calls that GitPython 3.1.44 makes for `repo.commit(<sha>)` and
`commit.diff(None)` (`git cat-file`, then `git diff <sha> --abbrev=40
--full-index -M --raw -z --no-color` with `LANGUAGE=C LC_ALL=C`), parses the
raw records the way GitPython's `Diff._handle_diff_line` does, and returns each
record's status and paths. The Oracle fails the case if the commit is missing,
if `git diff` exits non-zero (GitPython raises on both), or if any record's
`b_path` is not one of the three contaminated paths, which is the upstream
assertion. This check is what sees the index and the object database:
committing or staging a new file, or pruning the reference commit, fails
upstream's test and fails here.

The scope is `/app`, which in the baseline holds only the repository, with
`dclm/.git` captured as plain files so that Git in the Evaluation sees the
candidate's index, commits, refs and objects, as the native verifier does.

## Fidelity changes

- **Allowed domains (stricter).** Upstream allows internet access; the pack
  allows no domain. The reference solution uses only `grep`, `find`, `sed` and
  `xargs` from the image and needs no network. The task asks for nothing that
  needs one; an agent that wanted to download a tool (for example
  `git-filter-repo`) cannot, and must use what the image has.
- **Content of the other files is judged on SecureBench's hashes as well as
  through Git (stricter, only for candidates that tamper with Git).** Upstream
  asks Git whether other files changed, and Git's answer depends on metadata the
  candidate controls: `skip-worktree` or `assume-unchanged` index bits, `git
  replace` refs for the reference commit, `core.fileMode=false`, an fsmonitor
  hook, attribute filters. `other-files-unchanged` compares the content and
  executable bit SecureBench itself hashed during capture, so a candidate that
  changes another file fails even when Git is made to hide the change. For a
  candidate that leaves Git's metadata alone, both checks agree with upstream's
  test: Git compares the same bytes and, with the clone's `core.filemode=true`,
  the same executable bit. The attacks `attack-skip-worktree` and
  `attack-replace-commit` pass upstream's test and fail here.
- **A contaminated file that is a symlink (stricter).** Upstream's `open()`
  follows a symlink, so a symlink at a contaminated path to a correctly
  sanitized file passes upstream. Artifact checks read only regular files, so
  here it fails. No instruction suggests replacing a file with a symlink.
- **Contaminated files above 16 MiB or not valid UTF-8 (equivalent).** The
  `text` parser rejects files above 16 MiB, invalid UTF-8 and a leading
  byte-order mark. Upstream's read raises on invalid UTF-8 (the image sets no
  locale, so Python runs in UTF-8 mode with strict decoding), and a file above 16 MiB or with a byte-order mark
  cannot equal the expected file, so upstream fails all of them too.
- **Git environment (equivalent).** The adapter runs the baseline's
  `/usr/bin/git` 2.39.5, the same binary the native verifier's GitPython calls,
  with `GIT_CEILING_DIRECTORIES=/app` so that Git opens only `/app/dclm`, as
  `git.Repo("/app/dclm")` does. The adapter reimplements only the part of
  GitPython 3.1.44 the test reaches; three things it leaves out are listed in
  the next three bullets.
- **Paths containing a newline (equivalent).** GitPython splits Git's output on
  newline characters before parsing, so a tracked path that contains a newline
  is mis-parsed natively, while the adapter parses it whole. Such a path would
  be a new file outside the contaminated three, which fails in both graders.
- **Reference commit replaced by a tag (stricter, only for candidates that
  tamper with Git).** `repo.commit(sha)` is `rev_parse(sha + "^0")`, which
  peels a tag object to the commit it points to (`git/repo/fun.py`,
  `to_commit`). The adapter instead requires `git cat-file -t <sha>` to print
  `commit`. A candidate that uses `git replace -f` to make the reference commit
  resolve to a tag object can pass natively and fails here. A candidate that
  leaves Git's metadata alone cannot reach this difference.
- **`.gitmodules` that GitPython cannot parse (more lenient, only for
  candidates that commit such a file).** `Diff.__init__` (`git/diff.py`, lines
  440 to 444) iterates `repo.submodules` for every diff record. This parses
  HEAD's `.gitmodules` with GitPython's own parser, so a `.gitmodules` in HEAD
  that it cannot parse (for example a section without `path`) makes the native
  test error. The adapter does not read `.gitmodules`. The difference can only
  change a verdict when HEAD holds a `.gitmodules` that the index does not,
  because a `.gitmodules` in the index is an added file and fails the
  `git-diff` case anyway. The baseline has no `.gitmodules`.
- **Cases (equivalent).** Upstream has three tests and no random inputs; they
  become two artifact checks and one protocol case, as in the table above.

## How the adapter was compared with GitPython

We compared the adapter with the native code directly, besides comparing
Pier's verdicts in `qualification.json`. In the baseline image (memory-limited
container) we installed `gitpython==3.1.44`, the version upstream's `test.sh`
pins, and ran each of the nine candidates. On the resulting repository we
then ran both upstream's calls (`git.Repo("/app/dclm")`,
`repo.commit("d6987af0...")`, the sorted `b_path` of every record of
`commit.diff(None)`) and `evaluation/git_diff.py` on the same challenge the
pack sends.

- `reference`, `null`, `mutant-over-redaction`, `mutant-crlf`,
  `mutant-commit-helper`, `mutant-untracked-helper`, `attack-skip-worktree`
  and `attack-replace-commit`: identical `b_path` lists from GitPython and from
  the adapter (for `attack-replace-commit`, both empty).
- `mutant-purge-history`: GitPython raises `ValueError` from `repo.commit`, and
  the adapter reports `commit_found: false` and `diff_exit_status: 128`. Both
  fail.

The states near the boundary, where the adapter's result differs from
GitPython's, are the three listed under "Fidelity changes" above (newline in a
path, tag replacement, unparsable `.gitmodules`). Each needs a candidate that
writes unusual Git metadata on purpose, and none of the candidates here
reaches them.

## What the git-diff check trusts

The `git-diff` case runs Git on the candidate's `.git` directory, so the
candidate controls what it reports, as it does natively: for example, an
fsmonitor hook in `.git/config` could take over the adapter process and print
its own observation. The only values such a forgery can give are public ones
(the reference commit exists, nothing but the three files changed), so it is
the same as hardcoding them and outside SecureBench's scope. The part of
upstream's last test that a forgery could otherwise abuse, the content of the
other files, is judged by `other-files-unchanged` from SecureBench's own hashes,
which the candidate cannot influence.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` verbatim after `cd /app/dclm`
  (Harbor runs it in the image's working directory, and its `find .` depends on
  it).
- `null.sh`: changes nothing.
- `mutant-over-redaction.sh`: sanitizes correctly but also redacts every
  `AWS_SECRET_ACCESS_KEY=` assignment in the repository, changing four files
  that hold no secret. Aimed at `other-files-unchanged`, the manifest comparison
  that stands in for Git's diff. Expected: fails both.
- `mutant-crlf.sh`: sanitizes the three files with Python and writes CRLF line
  endings. Aimed at the Oracle's universal-newline normalization. Expected:
  passes both.
- `mutant-untracked-helper.sh`: sanitizes correctly with a helper script left
  untracked in the repository. Aimed at the manifest comparison ignoring new
  files, as Git's diff ignores untracked ones. Expected: passes both.
- `mutant-commit-helper.sh`: the same, but commits everything, helper included.
  Every original file is unchanged, so only the `git-diff` check catches it.
  Expected: fails both.
- `mutant-purge-history.sh`: sanitizes correctly, rewrites history to one
  commit and prunes the old objects, so upstream's reference commit is gone.
  Aimed at the `git-diff` check's commit lookup. Expected: fails both.
- `attack-skip-worktree.sh`: sanitizes the three files, damages four others,
  and hides them from Git with `skip-worktree`.
- `attack-replace-commit.sh`: the same damage, hidden by `git replace` of the
  reference commit with a forged commit whose tree is the damaged working tree.
- `scrub-secrets.txt` is not a candidate: the mutants and attacks run it with
  `sh` for the reference's replacements.

## Divergences from native

Every mutant gets the same verdict from both graders: `mutant-crlf` and
`mutant-untracked-helper` pass both; `mutant-over-redaction`,
`mutant-commit-helper` and `mutant-purge-history` fail both. The reference
passes both and the null candidate fails both.

- `attack-skip-worktree`: native passes (reward 1.0), SecureBench fails
  (`other-files-unchanged`: README.md, baselines/README.md,
  tools/commoncrawl/ray_config/cluster-west.yaml and tools/eval_expdb.py
  changed). SecureBench is right: four files that hold no secret were changed,
  which the instructions forbid and upstream's test means to catch; Git only
  stops comparing them because the candidate set their skip-worktree bits.
- `attack-replace-commit`: native passes (reward 1.0), SecureBench fails on the
  same four files. SecureBench is right for the same reason: `git replace` makes
  upstream's reference commit resolve to a forged commit whose tree is the
  damaged working tree, so Git reports no change at all.

## Review

Reviewer: a8ba5c3089ca04d21, 2026-10-26 (second review)

Pack digest checked: `sha256:8b88e9ae92b851aee8545ebe3a44331025dcc4b65387cc6987dc361a2a4bea42`
(`securebench validate`). It is unchanged since the first review, and every SecureBench run in
`qualification.json` records it. Since the first review only `CONVERSION.md` changed; `task/`
and `candidates/` are untouched, so points 1 to 7 and 9 stand as checked then and are repeated
briefly.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. One root, `/app`, with `dclm/.git` captured as plain files, so the candidate's
   index, refs and objects reach the Evaluation as they reach the native verifier. In the
   baseline `/app` holds only the repository, and there is no symlink under `/app`. Upstream's
   tests live in `/tests`, outside the image, and nothing in the repository is loaded by a test
   runner. The files Git loads by convention (`.git/config`, hooks, `.gitattributes`) are
   candidate-controlled here as they are natively; `/root/.gitconfig` is outside the scope.
   No case-folding collisions among the 538 tracked paths. Correct.
3. No expected value leaks. The expected sanitized files are byte-identical to upstream's
   `tests/` copies and sit only in `hidden/`. `evaluation/` holds the adapter and schemas, with
   no expected value. In the baseline image, no placeholder string occurs, no commit in the
   history contains one, and `/tests` does not exist. The secrets are in the baseline by design
   (they are the task's input). I re-derived `hidden/manifest.json` with `derive_manifest.py`
   in the baseline image: byte-identical. No allowed domain.
4. Challenges. The one challenge holds the repository path and the commit `d6987af0`, which is
   in the baseline's own history. Nothing else hidden.
5. Cases. Upstream's three tests become two artifact checks and one protocol case; nothing
   added; no randomness, and the seed is unused.
6. Oracle. Every expected value comes from `hidden/cases.json`, `hidden/expected/` and
   `hidden/manifest.json`; `oracle.py` holds only comparisons. It checks all three observation
   fields, reads only `b_path` from the diff records as upstream does, bounds its work by the
   listing (100,000 entries) and file (16 MiB) limits, fails closed on missing files, wrong
   statuses and unexpected evidence, and its universal-newline translation matches Python's
   `open(path, "r")`. The `text` parser's strict UTF-8 and byte-order-mark rejection agree with
   upstream. Regression tests by outcome: none.
7. Candidates. `reference.sh` run in the baseline leaves the three files equal to
   `hidden/expected/` byte for byte and nothing else modified. It is upstream's `solve.sh` with
   `cd /app/dclm`, a comment and a `#!/bin/sh` shebang; its body is POSIX and unchanged. The
   mutants run real code and are aimed at the newline normalization (`crlf`), the manifest that
   stands in for Git's content comparison (`over-redaction`, `untracked-helper`) and the
   adapter's commit lookup and record parsing (`commit-helper`, `purge-history`). Both attacks
   hide real damage from Git (skip-worktree bits, a `git replace` of the reference commit);
   SecureBench fails both on `other-files-unchanged`, which the run records confirm. Forging the
   `git-diff` observation through Git hooks can give only public values, as recorded.
8. Divergences. `qualification.json` reports no problems. The two divergences are the attacks
   (native 1.0, SecureBench failed); the explanations hold: skip-worktree bits and replace refs
   make Git stop comparing the damaged files, and SecureBench is right to fail them.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet. The row should be
   `terminal-bench  sanitize-git-repo  converted  -` with a note naming the trusted manifest and
   the empty domain list. No exclusion reason applies.

Upstream assertions: the five `not in` assertions per file map to the secrets loop of
`sanitized-files`; the equality assertion to its comparison with `hidden/expected/`;
`repo.commit(...)`, `commit.diff(None)` and the per-record `ValueError` of
`test_no_other_files_changed` to the `git-diff` case (`commit_found`, `diff_exit_status`,
`b_path` in the allowed list), with `other-files-unchanged` as the trusted check of the same
assertion's content part. None is dropped.

First-review findings:
- What the adapter leaves out of GitPython: fixed. "Fidelity changes" now lists the newline
  path, the tag peeling of `repo.commit` (stricter, only for candidates that tamper with Git)
  and the `.gitmodules` parse in `Diff.__init__` (more lenient, only reachable when HEAD holds a
  `.gitmodules` the index does not), each with a label and a correct reason.
- How the adapter was compared with GitPython: fixed. The new section records running
  GitPython 3.1.44 and the adapter on the state each candidate leaves. I repeated it with the
  converter's comparison script and `gitpython==3.1.44` in the baseline image for `reference`,
  `null`, `mutant-commit-helper`, `mutant-purge-history`, `attack-skip-worktree` and
  `attack-replace-commit`: the `b_path` lists are identical, and for `mutant-purge-history`
  GitPython raises `ValueError` while the adapter reports `commit_found: false` and exit status
  128, as recorded.

Findings:
- None.

Verdict: approved
