# headless-terminal

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/headless-terminal

## How the pack grades

Upstream's `tests/test.sh` installs vim with apt, installs pytest and requests with pip, and runs the seven tests of `tests/test_outputs.py` with pytest; the reward is pytest's exit status. Every test drives the candidate's `HeadlessTerminal` and then looks at a side effect of what the shell ran: a file in `/app`, or an HTTP response from a server the shell started in the background.

The pack has one protocol check, `tests`, with one case that runs all seven tests in order in one process:

- `setup_command` runs `dpkg -i` on the six packages in `evaluation/vim/`, the packages `apt-get install -y vim` installs in the baseline (see Fidelity changes).
- `evaluation/adapter.py` (stock Python) starts `evaluation/driver.py` under the baseline's `/usr/local/bin/python3`, the system Python the instructions tell the agent to install dependencies into. The driver's standard input is `/dev/null` and its standard output and error are unlinked temporary files, which is what pytest's default capture does to the test process; pytest's `sys.stdin` replacement is mimicked too. The driver's results come back through a result file in `/tmp`. A driver that exits non-zero, or leaves no readable result, makes the adapter report `unable`, as a test process that does not exit cleanly makes `test.sh` give reward 0.
- The seven upstream test functions live in `hidden/tests/`, one file per test, line for line. Each `assert` is replaced by a record of the values it compares. The keystrokes, waits and paths are upstream's. `plan` puts each test's name and source into the challenge, in upstream's order (see "Test inputs in hidden data").
- `driver.py` holds no test body. It sets up `sys.path` as pytest and upstream's module do (`sys.path.append("/app")`), defines every test it receives in one namespace, then runs them in the challenge's order. An exception from a test is recorded as `error`, which pytest would report as that test's failure.
- `hidden/cases.json` holds the list of tests to run and upstream's expected literals. `hidden/oracle.py` fails a test that recorded an error or a missing value, and otherwise compares as upstream does: `path.exists()` against true or false, `status_code == 200`, and `text.strip() == "Hello, world!"` with Python's own `str.strip`. The case passes only if all seven tests pass.

Mapping of upstream assertions:

| Upstream test | Assertions | Recorded | Oracle |
|---|---|---|---|
| `test_import` | import succeeds | `error` if it raises | no error |
| `test_send_non_interactive_command` | `/app/test.txt` exists; stripped text is `Hello, world!` | `exists`, `text` (raw `read_text()`) | equal; `text.strip()` equal |
| `test_send_interactive_command` | same for `/app/vim.txt`, written through vim | `exists`, `text` | same |
| `test_cancel_command` | `/app/cancel.txt` does not exist | `exists` | false |
| `test_startup_files` | same for `/app/special_file.txt` after the test appends an export to `$HOME/.bashrc` | `exists`, `text` | same |
| `test_shell_state_persists_between_commands` | same for `/app/secret.txt` | `exists`, `text` | same |
| `test_background_commands` | `requests.get("http://localhost:8000")` has status 200 and stripped text `Hello, world!` | `status_code`, `text` | equal; `text.strip()` equal |

## Fidelity changes

- **One case for the seven tests (equivalent).** pytest runs the tests in one process, in file order, and they share state: the tmux server and earlier terminals stay alive, `test_startup_files` appends to `~/.bashrc` for the tests after it, and every test creates a new terminal in the same process. Splitting them into one fresh environment per test would accept implementations that work only for the first terminal of a process (`mutant-fixed-session`). The driver runs them in upstream's order and, like pytest, keeps going after a failing test.
- **vim installed from vendored packages (equivalent).** `test.sh` runs `apt-get update; apt-get install -y vim` at grading time, and the Evaluation has no network. `evaluation/vim/` holds the exact six packages apt resolves for that command in the baseline today (`apt-get install -s vim`, then `apt-get download`, on 2026-11-03): vim, vim-common, vim-runtime and xxd 2:9.0.1378-2+deb12u2, libgpm2 1.20.7-10+b1 and libsodium23 1.0.18-1+deb12u1, from Debian 12. The setup installs them with `dpkg -i`, which works in an Evaluation with no capabilities. vim is not something the grader computes with; it is the interactive program the test drives through the candidate's terminal, so it cannot be reimplemented. The native verifier installs whatever the Debian mirror serves at grading time; if bookworm ships a newer vim, native and SecureBench would run different vim versions.
- **requests.get replaced by urllib (equivalent for this test).** pip is unavailable in the Evaluation. The driver's `_get` makes the same single GET with `urllib.request`, takes the status from 4xx and 5xx responses instead of raising (as requests does), and decodes the body with requests 2.32.5's own `get_encoding_from_headers` and `Response.text` logic, copied unchanged. Left out: requests' `charset_normalizer` guess for a response without a Content-Type (UTF-8 with replacement is used instead), gzip/deflate decoding, its redirect limit of 30 (urllib follows 10), and joining repeated Content-Type headers. `python -m http.server` serving `index.html` sends `Content-type: text/html` without compression or redirects, so both decode the body as ISO-8859-1 and yield the same text. A refused connection raises in both.
- **No pytest, requests or their dependencies in the system Python (stricter).** Natively, `test.sh` pip-installs pytest 8.4.1, requests 2.32.5 and pytest-json-ctrf 0.3.5 (with pluggy, iniconfig, packaging, pygments, urllib3, idna, certifi and charset_normalizer) into the same system Python before the tests import the candidate. A candidate that imports one of these without installing it passes natively and fails here. The instructions tell the agent to install its dependencies, so we do not provide them.
- **Test runner (equivalent).** The driver replaces pytest, so pytest plugins or configuration the candidate could install into the system Python no longer run. The driver mimics what pytest gives the test process: all tests defined before the first runs, file order, standard streams (fd 0 on `/dev/null`, fds 1 and 2 on temporary files, a `sys.stdin` that refuses reads), `/usr/local/bin` (the console script's directory) first on `sys.path` and `/app` appended last. pytest's `/tests` directory on `sys.path` does not exist here. A test that raises `KeyboardInterrupt` ends a pytest session; the driver records it as that test's error, and both fail.
- **Scope `/app` and `/usr/local` (stricter and more lenient).** The deliverable is `/app/headless_terminal.py`, and dependencies go into the system Python under `/usr/local`. Natively the tests run in the agent's own container, so everything the agent left behind is present. Here only the scope survives. `/usr` cannot be the root instead, because apt creates symlinks from `/usr/bin` into `/etc/alternatives`, which would fail capture. Files the agent left in `/app` (for example a `vim.txt` from its own trials) are captured and affect both graders alike. Everything else is lost, in two directions:
  - Stricter: an implementation that relies on a file it wrote outside the two roots passes natively and fails here, because that file is gone. Examples are a `~/.tmux.conf` or another tmux config under `/root`, a helper script under `/opt` or `/usr/bin`, an rc file it passes to bash, `pip install --user` packages in `/root/.local`, and packages installed with apt (whose files live in `/usr/bin`, `/usr/lib`, `/etc` and `/var/lib/dpkg`). The instructions do not forbid such helpers.
  - More lenient: state the agent left outside the scope can make the native grader fail a correct terminal, and SecureBench passes it. A `/server` directory makes `mkdir /server` fail (`check=True`). Any process still running can change the native verdict, not only one listening on port 8000. The most likely one is a tmux server left by the agent's own trials: natively, every terminal the tests create joins it and inherits its sessions, global environment and loaded configuration. Edits to `/root/.bashrc` are lost too.
- **Time budget (more lenient).** Natively one 900 s budget (`[verifier] timeout_sec = 900`) covers `apt-get update`, `apt-get install vim`, the pip installs and pytest together. Here the vim install has its own 600 s setup budget (`setup_timeout_seconds`), and the seven tests get the full 900 s (`timeout_seconds`). A slow but correct candidate whose tests take between roughly 850 s and 900 s times out natively and passes here. The upstream tests themselves wait about 13 s in total, so only a terminal that blocks for many minutes reaches this range.
- **Allowed domains empty (stricter).** Upstream allows the internet. The reference uses only tmux, which the baseline has, so the Agent environment gets no domains; an agent cannot pip-install a dependency such as pexpect, although the instructions mention installing dependencies.
- **Observation bounds (stricter, theoretical).** A recorded text above 512 KiB, or an error message above 2,000 characters (truncated by the driver, diagnostic only), does not fit the observation. A file that large cannot strip to `Hello, world!` unless it is mostly whitespace, so only that case could pass natively and fail here.

## Candidates

- `reference.sh`: upstream's `solve.sh` (copy `headless_terminal.py`, upstream's solution file, unchanged).
- `null.sh`: changes nothing; every test fails to import the module.
- `mutant-fixed-session.sh`: a fixed tmux session name. The first terminal works, later ones raise; aimed at running the seven tests in one process.
- `mutant-ignore-wait.sh`: ignores `wait_sec`; aimed at the driver keeping upstream's timing and at the refused-connection path of the `requests.get` replacement.
- `mutant-no-rc.sh`: starts `bash --norc`; aimed at the Evaluation's `HOME` and startup files matching native.
- `mutant-pipe-shell.sh`: an interactive bash on a pipe, no pseudo-terminal, output inherited from the test process; aimed at the driver's standard streams matching pytest's capture, which decide how bash and vim behave without a tty. It passes SecureBench: bash still reads `.bashrc`, vim reads its keys from the pipe, and the cancel test does not distinguish a real Ctrl-C (its file cannot appear within one second either way).
- `mutant-oneshot.sh`: each line runs in its own `bash -ic`; the background test passes through the urllib replacement while vim and the state test fail.
- `attack-verdict-claim.sh`: replaces the driver's result file at exit with records that claim a pass; the schema rejects them.
- `attack-adapter-takeover.sh`: writes a forged envelope to the adapter's standard output through `/proc/<parent>/fd/1` and kills the adapter.
- `attack-kill-environment.sh`: kills every reachable process when a terminal is created, so that the failure looks like an infrastructure error.

## Out of scope

Every expected value is a public literal from upstream's tests, and the candidate's code runs inside the driver process, so a candidate can write the expected files itself or forge the result file with those literals. That is hardcoding public answers, which SecureBench does not try to prevent, as the native grader does not.

## Test inputs in hidden data

Form: send the test source. The driver is Python, so it runs the code it receives.

- What moved: the bodies of the seven test functions, from `evaluation/driver.py` to `hidden/tests/<test name>.py`. Joined in upstream's order, the seven files equal the old driver's test functions byte for byte, except for the two comments `# assert path.exists()` and `# assert path.read_text().strip() == "Hello, world!"`. They sat in the driver's `_record_file` and now sit above each call to it. They are comments only.
- How the tests arrive: `plan` reads the test list from `hidden/cases.json` and sends each test as `{"name", "source"}` in the challenge. The adapter passes the list to the driver as its first argument, as it passed the names before, and the result path stays the second. The driver compiles every source into one namespace before it runs any test. That namespace holds what upstream's module gives its tests: `Path`, `shlex`, `subprocess`, the `requests.get` stand-in `_get` and the recorder `_record_file`. The driver then runs the tests in the challenge's order, as before.
- Bounds: each source is at most 1,024 bytes in `evaluation/challenge.json` (the largest is 756). `max_challenge_bytes` rose from 4,096 to 5,120; the challenge is 4,457 bytes.
- Same behavior: the reference run on the old pack and on the new one gave the same observation for the one case, all seven records identical; only the duration differed.

Places in `evaluation/` that still name a test value, and why none decides an expected value:

- `challenge.json` lists the seven test names, and `observation.json` names each test's recorded fields (`exists`, `text`, `status_code`, `error`). Names and field names say what is recorded, not what it should be. The one-bit values they hint at are listed below.
- `driver.py`: `sys.path` gets `/usr/local/bin` and `/app`; `/app` is where the instructions put the module. `_record_file` records whether a path the test names exists and its text. `_get` makes the GET the test asks for and returns its status and text. Neither holds a path, URL, keystroke or expected text.
- `adapter.py` runs the driver in `/app` under `/usr/local/bin/python3`, the interpreter the instructions name.
- `evaluation/vim/` and the setup command install vim. That tells an agent that a test drives vim, which the instructions already ask for ("Supports interactive programs"). It says nothing about what the test types or what file should appear.

Expected values decided by the instructions or a test's name alone (out of scope):

- `exists` for the five file tests: `true` for `test_send_non_interactive_command`, `test_send_interactive_command`, `test_startup_files` and `test_shell_state_persists_between_commands`, and `false` for `test_cancel_command`. Each is one bit that the test's name decides (a cancelled command must not leave its file behind).
- `status_code` 200 for `test_background_commands`: the HTTP success code, implied by a test that fetches from a server the terminal started.
- `test_import` has no value: only that the import raises nothing.

The expected text `Hello, world!` is no longer in `evaluation/`. It is in `hidden/tests/` (the keystrokes) and `hidden/cases.json`. As "Out of scope" says, it is also a public literal of upstream's published tests.

No attack changed. `attack-verdict-claim` still finds the result file as the driver's second argument; the two others do not reach into driver code.

## Divergences from native
None. Every mutant gets the same verdict from both graders: `mutant-pipe-shell` passes both, the other four fail both. The attacks are recorded only: `attack-verdict-claim` gets reward 0 natively, and `attack-adapter-takeover` and `attack-kill-environment` end natively with `RewardFileNotFoundError`, because killing the test process's parent (or every process) kills `test.sh` before it writes a reward. SecureBench fails all three with class `case_error`.

## Review

Reviewer: conversion-reviewer for headless-terminal, 2026-11-03 (second review, after the converter addressed the first review's two findings)

The changes since the first review touch only `CONVERSION.md`: the Scope bullet is rewritten and a "Time budget" bullet is added. `validate` still prints pack `sha256:da4f7749d64e1534e5de8af5484d0f713e4157c27609ec0580a969fc18ff53dd`, and no file under `task/` or `candidates/` is newer than `qualification.json`. Points 1 and 3 to 7 below therefore carry over from the first review unchanged. Point 2 and the fidelity record are re-checked against the new text.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. The roots are `/app` (the deliverable) and `/usr/local` (the system Python the instructions name). I checked the baseline image directly. Every symlink under both roots stays inside them (`/usr/local/bin/python -> python3`, `/usr/local/man -> share/man` and others like them). `/app` holds only `base_terminal.py`. No upstream test file is inside the scope: the tests live in `/tests` natively and in `/.securebench/evaluation/driver.py` here. The driver runs under the candidate's `/usr/local/bin/python3`, so the candidate controls the interpreter, the standard library, `.pth` files and `sitecustomize`. The instructions require that interpreter, and the candidate's module runs in the same process natively, so this gives a candidate no more than native does. All expected values are public, so it opens no route to a hidden value. No excludes are needed. The Scope bullet is now labelled "stricter and more lenient" and covers both directions: files outside the roots that an implementation relies on are lost, and leftover state outside the scope (`/server`, any running process, a leftover tmux server in particular, `.bashrc` edits) can fail a correct terminal natively. This fixes the first finding.
3. Expected values. The only expected values are upstream's public literals (`True`/`False`, `200`, `Hello, world!`), kept in `hidden/cases.json`. `evaluation/driver.py` contains `Hello, world!` only as the keystrokes upstream's tests send, which pass through the candidate's code in both graders. `grep -r "Hello, world"` over the baseline finds it only in pip's vendored rich and in tkinter. No allowed domains.
4. Challenges. The one challenge lists the seven test names and nothing else.
5. Cases. One case runs upstream's seven tests in upstream's order in one process, as pytest does; the reason (shared tmux server, `.bashrc` append, several terminals per process) holds, and `mutant-fixed-session` shows it matters. No cases added; the seed is unused, as upstream draws nothing random.
6. Oracle. `oracle.py` holds no expected value. It fails closed on a missing record, a recorded error, a non-boolean `exists`, a non-integer or boolean status and a missing text, and it ignores extra fields. Order of checks and `str.strip` match upstream's assertions. Work is bounded by the schema (512 KiB per text). Each driver test body is upstream's line for line (I diffed them mechanically); only the asserts and `requests.get` changed. I re-checked the `requests` replacement against requests 2.32.5. The copied `get_encoding_from_headers` and `Response.text` logic, the 4xx/5xx handling, the redirect limits and the refused-connection path are as described. The Evaluation sets no proxy variables (`securebench/isolation/docker.py`, `EnvironmentSpec`), so urllib also connects to localhost directly. The vendored vim: `apt-get update; apt-get install -s -y vim` in the baseline today resolves exactly the six packages and versions in `evaluation/vim/`, and each `.deb`'s SHA-256 equals the one in Debian's signed index (`apt-cache show`). No regression tests run by outcome.
7. Candidates. `reference.sh` copies upstream's `headless_terminal.py`, which `diff` shows is unchanged. Its only addition beyond `cd` and finding sibling files is `set -e`, which changes no behavior for a single `cp`. The five mutants run real code and aim at the places where the conversion differs from native: one process for all tests, timing and the refused-connection path of `_get`, HOME and `.bashrc`, standard streams without a tty, and the `_get` success path. The SecureBench diagnostics show which tests fail: `mutant-ignore-wait` fails vim and background (refused connection), `mutant-oneshot` fails vim and state, `mutant-no-rc` fails only startup files, and `mutant-fixed-session` fails every test after the first. The three attacks go through the driver's result file, the adapter's stdout through `/proc`, and kill(-1). All three end `failed`/`case_error`, never `invalid`. Since every expected value is public, no forgery can pass a hidden check; the "Out of scope" section says so correctly.
8. Divergences. `qualification.json` reports no problems, and every SecureBench run records pack `sha256:da4f7749d64e1534e5de8af5484d0f713e4157c27609ec0580a969fc18ff53dd`, the digest `validate` prints now. The runs record two framework commits, `605f7df8` and `5a19e3f2`; they differ only in `conversions/agents.tsv`, so the SecureBench code is the same. All five mutants agree with native. The native attack outcomes (`RewardFileNotFoundError` when `test.sh` is killed) are explained and plausible.
9. Inventory. No `headless-terminal` row exists at the moment; it was removed when the task went on standby (`bdc249af`). The coordinator should add `terminal-bench	headless-terminal	converted	-`. No exclusion reason applies.

Upstream assertions: all ten asserts across the seven tests are checked (see the mapping table above), together with the `check=True` calls and the import, which are recorded as errors when they raise. None are dropped. Every fidelity change has a label and a reason. The new "Time budget (more lenient)" bullet records the separate 600 s setup budget and the full 900 s case timeout against native's single 900 s verifier budget. This fixes the second finding.

Findings:
- None. Both findings of the first review are fixed in `CONVERSION.md` (the Scope bullet and the new Time budget bullet). The pack did not change.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- Item 2 (line 96), "the tests live in `/tests` natively and in `/.securebench/evaluation/driver.py` here" → the seven test bodies now arrive in the challenge as `source`, cut from `hidden/tests/<test name>.py`, and the driver no longer holds them.
- Item 3 (line 97), "`evaluation/driver.py` contains `Hello, world!` only as the keystrokes upstream's tests send" → the keystrokes are in the test bodies in `hidden/tests/`, not in `evaluation/driver.py`.
- Item 4 (line 98), "The one challenge lists the seven test names and nothing else" → the challenge now lists each test as `{"name", "source"}`.
- Item 6 (line 100), "Each driver test body is upstream's line for line" → the test bodies are now in `hidden/tests/<test name>.py`.
