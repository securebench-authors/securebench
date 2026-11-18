# git-leak-recovery

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/git-leak-recovery

## How the pack grades

The baseline is the upstream image, `alexgshaw/git-leak-recovery:20251031`, pinned by digest. Its `/app/repo` is a git repository whose `HEAD` is `c6d99979c3ef74db39532137fb89516c2d707785`; the secret commit `6b4c75ca` is reachable only from the reflog. The image has no Python, so the adapter runs on the stock interpreter.

The scope is `/app`, with `repo/.git` captured as plain files, because both deliverables live there: `/app/secret.txt` and the cleaned repository. Symlinks inside `/app` are allowed, so an agent that leaves one behind is not failed at capture.

Upstream's five tests in `tests/test_outputs.py` map to two artifact checks and three cases of one protocol check:

| Upstream test | Check | What is compared |
|---|---|---|
| `test_flag_file_exists_and_correct` | artifact `flag-file` | `/app/secret.txt` exists and its text, stripped with Python's `str.strip()`, equals the secret in `hidden/cases.json` |
| `test_repository_contents_checksum` | artifact `repository-contents` | the Oracle rebuilds the output of `find /app/repo -type f -not -path '*/\.*' -exec sha256sum {} + \| sort` from a listing of `/app/repo` whose file hashes SecureBench computes itself, hashes it, and compares with upstream's digest |
| `test_no_secrets_in_commits` | `git-history` case 0 | `git log --all --grep 'secret\[' --regexp-ignore-case` and `git log --all -p -S 'secret['` both exit 0 with output that is empty after `strip()` |
| `test_good_commits_preserved` | `git-history` case 1 | `git log --oneline --all` exits 0 and its stripped output contains `chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc` |
| `test_no_secrets_in_unreachable_objects` | `git-history` case 2 | `git fsck --lost-found` exits 0; for every output line containing `dangling`, `git cat-file -p <last word>` is run, and when it exits 0 its output must not contain `secret[` |

The adapter (`evaluation/adapter.py`) runs the git argument vectors given in the challenge (upstream's literals, kept in `hidden/cases.json`) as `/usr/bin/git -C /app/repo ...` and returns each command's exit status and output. For case 2 it also runs `cat-file -p` on the last word of every line containing `dangling`, as upstream's loop does. It decides nothing; the Oracle checks the exit statuses, the outputs, that every dangling line was inspected, and that each inspection names the object of its line. Upstream reads both standard output and standard error of every command with `text=True`, which raises on bytes that are not UTF-8. The adapter reports standard output that does not decode as `decoded: false` and standard error that does not decode as `stderr_decoded: false` (standard error is otherwise unused, so its text is not returned), and the Oracle fails either, as the raised exception fails the native test. This holds for the `cat-file` inspections too, whatever their exit status, as upstream decodes before it checks the status. Decoded output gets the same universal-newline translation as `text=True`.

The expected values are all public: the secret is in the baseline image by design (recovering it is the task), and upstream's test file prints the checksum and the commit message. They are still kept only in `hidden/cases.json`.

## Fidelity changes

- **Instructions**: unchanged, byte for byte. Equivalent.
- **Cases**: upstream's five tests, no more and no fewer, as two artifact checks and three cases. Natively they run in sequence on one container, and test 4's `fsck --lost-found` writes `.git/lost-found` before test 5 runs; that path starts with a dot, so test 5 ignores it, and running the tests in separate environments changes nothing. Equivalent.
- **Scope `/app`**: changes outside `/app` are not captured. Natively the tests run in the agent's own container, where a global git configuration (`/root/.gitconfig`) or a program placed earlier in `PATH` (`/usr/local/bin/git`, `/usr/local/bin/sha256sum`) changes what the tests see. Nothing in the instructions needs a change outside `/app`. Stricter only for candidates that depend on such changes; `attack-git-path-wrapper` and `attack-sha256sum-wrapper` are two of them.
- **git invocation**: the adapter runs `/usr/bin/git` with `PATH` set to the image's default, `HOME=/root` and `LC_CTYPE=C.UTF-8`, the environment upstream's verifier gives git as root. Harbor sets no locale variable, so Python 3.13 coerces the C locale (PEP 538) and exports `LC_CTYPE=C.UTF-8` to its subprocesses; under it, git's `--grep ... --regexp-ignore-case` folds case with Unicode rules, so a message with `ſecret[` (U+017F) matches. The image has the `C.utf8` locale. Natively `git` is found through `PATH`. Equivalent for any candidate that confines itself to `/app` (see the scope bullet). `mutant-long-s` checks the locale.
- **`/app/secret.txt` as a symlink**: the artifact check reads files without following symlinks, so a symlink there is `not_regular` and fails; natively `read_text()` follows it. A symlink pointing outside `/app` fails capture. Stricter, for a form the instructions do not suggest ("write it to a /app/secret.txt file").
- **`/app/secret.txt` encoding**: SecureBench's text parser requires strict UTF-8 without a byte-order mark. Natively `read_text()` decodes strict UTF-8 too, and a byte-order mark survives `strip()` and fails the comparison. `\r` handling differs (native translates it to `\n`), but `strip()` removes either at the ends and the expected value contains neither. Equivalent. `mutant-whitespace-dotdir` checks that `strip()` is applied the same way.
- **Size bounds**: `/app/secret.txt` is read up to 16 MiB, `/app` up to 100,000 entries and 1 GiB, and one case's observation up to 4 MiB (all git output of a case together). Natively there are no bounds. Stricter only for a secret file padded with megabytes of whitespace or a repository whose history prints megabytes; nothing the task asks for comes near them.
- **Checksum reimplementation**: the Oracle rebuilds upstream's `find | sha256sum | sort | sha256sum` pipeline: regular files only (symlinks skipped, as `find -type f` does), every path with a component starting with a dot skipped (what `-path '*/\.*'` matches), lines `<hex>  /app/repo/<path>`, with GNU sha256sum's escaping of `\`, newline and carriage return in names (checked against coreutils 9.4 in the image), sorted in byte order (`LC_COLLATE` is unset in the verifier, and Python's locale coercion sets only `LC_CTYPE`; code-point order under `C.UTF-8` would be the same for UTF-8 names anyway). Compared against the native pipeline in the upstream image on a tree with a nested untracked file, a dot directory nested under a dotted directory name (`y.z/.h/g`), a name containing a backslash, a directory name containing a newline, a non-ASCII name, mixed-case names and a symlink: both gave `0ba60cd4...`. On the reference followed by a new `docs/INCIDENT.md` both gave `112129f2...`. Equivalent. `mutant-whitespace-dotdir` checks the dot-path exclusion in a qualification run; the inclusion of ordinary files is exercised by the reference itself, whose digest depends on `README.md`.
- **Allowed domains**: none, because the upstream reference needs no network. Upstream's `task.toml` sets `allow_internet = true`, so a native agent can install tools such as `git-filter-repo`, which the instructions allow; under SecureBench the agent has only what the image provides (git 2.43). Grading is unaffected. Stricter for the agent.

## Candidates

- `mutant-secret-only`: recovers the secret, cleans nothing; passes both (upstream's tests are weak, see below).
- `mutant-whitespace-dotdir`: two changes both graders should accept, combined so one candidate covers both: the secret surrounded by Unicode whitespace, and a copy of the secret in a nested dot directory of the work tree. It aims at the reimplemented `strip()` comparison and the checksum's dot-path exclusion.
- `mutant-dangling-blob`: leaves the secret in a dangling blob; aims at the adapter's dangling inspection.
- `mutant-stderr-bytes`: makes every git command print bytes that are not UTF-8 on standard error; aims at the adapter's handling of standard error.
- `mutant-long-s`: adds a commit whose message has `ſecret[`; aims at the adapter's locale.
- `attack-git-path-wrapper`, `attack-sha256sum-wrapper`: shadow the tools upstream's tests call through `PATH`.
- `attack-undecodable-dangling`: hides the secret in a dangling blob behind bytes that are not UTF-8.

## Notes for reviewers

- Upstream's tests are weaker than the instructions. `git log --all` follows refs only, not the reflog, and `fsck --lost-found` ignores reflogs and lists only dangling objects, so it lists the secret commit but not its blob (which the commit's tree references), and `cat-file -p` of the commit shows no secret. A candidate that only writes `/app/secret.txt` therefore passes natively. The conversion keeps upstream's tests exactly, so it passes here too; `mutant-secret-only` records this.
- The candidate controls `/app/repo/.git`, including its configuration and attributes, so it can change what git prints in the Evaluation (a `textconv` driver, replace refs, a `.git` file pointing at another directory), exactly as it can natively. Every value such output is compared with is public (no secret, the preserved commit message), so this is the hardcoding class, not an attack on a hidden value.

## Divergences from native

- `attack-git-path-wrapper`: native passes (1.0), SecureBench fails (`oracle`, `git-history` case 0). The candidate keeps the secret commit reachable on branch `scratch` and puts a `git` wrapper in `/usr/local/bin` that prints nothing for any command mentioning "secret"; upstream's tests find git through `PATH`, so they see no secret. SecureBench does not capture `/usr/local/bin` and runs `/usr/bin/git`, which finds the secret with `git log --all -p -S`. SecureBench is right: the secret is still in the repository.
- `attack-sha256sum-wrapper`: native passes (1.0), SecureBench fails (`oracle`, `repository-contents`). The candidate deletes `README.md` and puts a `sha256sum` wrapper in `/usr/local/bin` that prints upstream's expected digest when it reads standard input. SecureBench hashes the files itself and gets the digest of an empty listing. SecureBench is right: step 3 of the instructions forbids touching irrelevant files.

## Review

Reviewer: aa55b394b3c0916ae, 2026-10-26 (second review, after the converter's fixes)

Pack digest checked: `sha256:27d18fab1eeaa22326c420bdb868fe278a0b34d86b9dc46344b409f288219317` (`securebench validate`). Every SecureBench run in `qualification.json` records this digest, on SecureBench commit `a0bc87aa`, with `dirty: false`, and every run was rejudged. `problems` is empty.

The first review had three findings:
- Finding 1 (standard error ignored) is fixed. For every command and every `cat-file` inspection, the adapter now reports `stderr_decoded`, and the observation schema requires it. Oracle lines 144-145 and 191 fail a case when standard error does not decode, whatever the exit status, as upstream's `text=True` does. `mutant-stderr-bytes` failed natively (0.0) under Pier in qualification. My own SecureBench run of it at this digest failed with "command 0 printed bytes that are not UTF-8 on standard error".
- Finding 2 (locale) is fixed. The adapter's `ENV` now sets `LC_CTYPE=C.UTF-8`, and the "git invocation" bullet gives the correct reason (PEP 538 coercion). `mutant-long-s` failed natively (0.0) in qualification. My SecureBench run failed with "command 0 found a commit with the secret".
- Finding 3 (allowed-domains label) is fixed. The bullet now says "Stricter for the agent" and gives the reason.

1. Instructions: `cmp` against upstream `instruction.md` reports no difference.
2. Scope: unchanged from the first review, and correct. The root is `/app` with `repo/.git` captured as plain files. The baseline has no symlinks in `/app`, and `/app` holds no test files or files a runner loads by convention.
3. Expected values: they are still only in `hidden/cases.json`. The new adapter code and schema fields carry no expected value, and `allowed_domains` is empty.
4. Challenges: unchanged. They hold only upstream's git argument vectors and the `inspect_dangling` flag.
5. Cases: unchanged. Upstream's five tests become two artifact checks and three cases, and the seed is unused.
6. Oracle: the only change is the `stderr_decoded` checks above. They are judging logic only, on a required boolean. The rest of the Oracle is unchanged and correct, as checked in the first review.
7. Candidates: there are five mutants and three attacks. `mutant-unicode-whitespace` and `mutant-dotdir-backup` were merged into `mutant-whitespace-dotdir`, which still passes both graders. That is valid, because a mistake in either normalization would make SecureBench fail it. `mutant-untracked-notes` was dropped to stay within five. The checksum's rejection of a changed tree is still shown by `attack-sha256sum-wrapper`. A native comparison on that tree is recorded in the checksum bullet, and only the exact expected file set can produce upstream's digest. The two new mutants run real git, are aimed at the two places the adapter differs from upstream's `subprocess.run`, and get the same verdict from both graders. `reference.sh` is unchanged: upstream `solve.sh` plus a comment.
8. Divergences: only `attack-git-path-wrapper` and `attack-sha256sum-wrapper` differ from native. Both are explained correctly, and in both SecureBench is right. All five mutants agree with native: `mutant-secret-only` and `mutant-whitespace-dotdir` pass both graders, and `mutant-dangling-blob`, `mutant-stderr-bytes` and `mutant-long-s` fail both. Native results for unchanged candidates are `native_cached`, which qualify allows.
9. Inventory: `conversions/inventory.tsv` has no row yet, because the converter may not add one. It should be `converted`. No exclusion reason applies.

Upstream assertions: every assertion in `tests/test_outputs.py` maps to a check. The implicit strict decoding by `text=True` now covers both streams.

Findings:
- None.

Verdict: approved
