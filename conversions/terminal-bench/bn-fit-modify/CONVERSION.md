# bn-fit-modify

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/bn-fit-modify

## How the pack grades

The agent writes three CSV files in `/app`. The pack has three artifact checks,
one per file, each reading the file as UTF-8 text; there is no protocol check
and nothing of the candidate runs during grading. The Oracle tokenizes each file
the way `pandas.read_csv` does with its defaults and judges it as the upstream
tests do. All expected values are in `task/hidden/expected.json`, written by
`task/hidden/derive_expected.py` (run with Python 3.13 and scipy 1.16.1, the
verifier's versions).

| Upstream test (`tests/test_outputs.py`) | Check | What the Oracle requires |
|---|---|---|
| `test_learned_dag_structure_exists` | `learned-dag` | `/app/learned_dag.csv` is a present regular file |
| `test_learned_dag_structure_csv_col_names` | `learned-dag` | it parses, has at least one data row, and has columns `from` and `to` |
| `test_learned_dag_structure` | `learned-dag` | the set of `(from, to)` pairs equals the six expected edges |
| `test_intervened_dag_structure_exists` | `intervened-dag` | `/app/intervened_dag.csv` is a present regular file |
| `test_intervened_dag_structure_csv_col_names` | `intervened-dag` | as for the learned DAG |
| `test_intervened__data_structure` | `intervened-dag` | the set of pairs equals the five expected edges |
| `test_bn_sample_exists` | `bn-sample` | `/app/final_bn_sample.csv` is a present regular file |
| `test_sampled_csv_col_names` | `bn-sample` | it parses, has at least one data row, and has columns `U`, `R`, `Y`, `M`, `D` |
| `test_sampled_data` | `bn-sample` | exactly 10,000 rows and 5 columns, every `D` value a number pandas would read, and the one-sample KS statistic of `D` against the expected normal at most the bound below |

The edge sets, column names, counts and the formulas for `true_mean` and
`true_std` are upstream literals; `derive_expected.py` evaluates the two
formulas with the same Python expressions.

## Fidelity changes

- **Instructions: equivalent.** `task/instructions.md` is upstream
  `instruction.md` byte for byte.
- **KS acceptance rule: equivalent.** Upstream accepts when
  `scipy.stats.kstest(D, "norm", args=(true_mean, true_std)).pvalue >= 0.001`.
  With 10,000 rows scipy's p-value is `kstwo.sf(statistic, 10000)`, which
  decreases in the statistic, so the same verdict is "statistic at most
  0.019477480462373648", the largest double whose survival function is still at
  least 0.001. `derive_expected.py` finds it by bisection and asserts that the
  survival function is non-increasing on a grid of 2,001 points within 1e-5 of
  it and gives the right side on the 50 doubles on each side of it. The Oracle
  computes the statistic exactly as scipy's `ks_1samp` does (sorted values,
  `max(i/n - F(x_i))` and `max(F(x_i) - (i-1)/n)`), with the normal CDF written
  as scipy's `ndtr` branches on `erf` and `erfc`.
  Comparison with native: on 3,000 samples of 10,000 normal draws with mean
  shifts chosen to put the statistic near the bound, the Oracle's statistic
  differs from scipy's by at most 1.1e-16; the 426 samples whose statistic was
  within 0.002 of the bound (264 accepted by scipy) all got the same verdict
  from the Oracle as from upstream's test code run with pandas 2.3.2 and scipy
  1.16.1. The CDF differs from `scipy.stats.norm.cdf` by at most 2.2e-16 on
  400,001 points in [-40, 40]. Two mutants sit within 1e-4 of the bound on
  either side (below).
- **CSV reading: equivalent, with the narrow exceptions listed.** The Oracle
  reimplements the parts of `pandas.read_csv` the tests reach: the C
  tokenizer's quoting (a quote opens a quoted field only at the field's start;
  doubled quotes inside; text after a closing quote joins the field),
  `\n`, `\r\n` and `\r` line ends, skipped lines that are empty or hold only
  spaces and tabs, the error on a row with too many fields, padding of short
  rows, and the index pandas builds when the first data row has more fields
  than the header: the extra leading fields become the index, one of them for
  R's `write.table(sep = ",")`, a MultiIndex for two or more, and later rows
  may have at most that many fields. Column lookup uses the first header
  field with the name, as pandas' renaming of repeated names (`D`, `D.1`)
  gives. For `D`, a value counts as a number with pandas' grammar: optional
  whitespace, sign, digits with at most one point, optional exponent, or an
  infinity word (`inf`, `infinity`, any case, optional sign, no whitespace).
  A literal that overflows a double fails, as pandas then leaves the column
  as strings. Integer literals are read as doubles, except where pandas'
  integer pass keeps the column as strings: pandas reads the column as
  integers first, row by row, and the first value that is not an integer
  literal makes it parse the whole column as doubles. A positive integer
  beyond 2^64 - 1 met before that value fails the file, whatever integers
  (including negatives) come before it. A column of integer literals only
  fails when it needs both int64 and uint64: a value below -2^63, or one
  above 2^63 - 1 together with a negative one (a `-` sign counts, even on
  zero). We inferred this rule by probing pandas 2.3.2, not from its
  source, so the integer forms and random integer sequences of the
  differential below are its evidence.
  Any other value (empty, `NA`, `nan`, `True`, `1_0`, ...) fails, since
  pandas makes it NaN or leaves the column non-numeric, and upstream's KS
  test then fails either way.
  A differential against `pandas.read_csv` 2.3.2 plus upstream's assertions
  agreed on all 76 sample-file forms, 21 DAG-file forms, 325 random
  single-`D`-value tokens (placed at row 0 or row 5) and 202 random
  sequences of one to three integer, float or infinity values at the start
  of `D`. The forms cover R's `write.csv` and `write.table`, pandas' index
  column, two and three leading index fields, CRLF and CR line ends,
  reordered and quoted columns, blank lines, NaN, `NA`, empty, short and
  long rows, infinities, overflow, integers around the int64 and uint64
  limits, 25-digit integers at rows 0, 1, 3 (after integer rows), 5000 and
  9999, the integer sequences of the second review (such as 10^19, -5, then
  a 25-digit integer), columns of integers only, repeated and missing
  columns, quoted newlines, unterminated quotes, header-only and empty
  files, extra rows, set semantics, `to,from` order and 12,000 repeated
  edges. The script that ran both comparisons is
  `task/hidden/differential.py`; grading does not use it.
  The Oracle stops reading the sample file once it has seen more than 10,001
  records (the header and 10,000 rows), since upstream fails any sample with
  more rows; this changes no verdict and bounds the Oracle's memory, which
  runs on the host. Measured with `tracemalloc` on adversarial files of the
  maximal size, `judge` peaks at about 150 MiB for a 16 MiB sample (one
  quoted field, or 16 million commas) and 1 MiB for 16 MiB of one-character
  lines, and at about 95 MiB for a 1 MiB DAG file of one-character lines.
  DAG files are read whole, because upstream accepts any number of repeated
  edges. Remaining differences, none of which a solution would plausibly
  produce:
  - *Stricter:* a file starting with a UTF-8 byte-order mark is unparsable
    under SecureBench's text parser and fails; pandas strips the mark.
  - *Stricter:* a DAG file above 1 MiB or a sample file above 16 MiB is
    `too_large` and fails; pandas has no limit. The reference's sample is
    about 0.9 MiB.
  - *Either way:* pandas' default float parser can differ from Python's
    `float` by one unit in the last place, and its overflow cut-off near the
    largest double may differ from Python's rounding; these affect a verdict
    only for a KS statistic within about 1e-16 of the bound.
- **Scope: equivalent for grading, stricter at capture.** The scope is `/app`
  with everything below its subdirectories excluded (`*/*`): the checks read
  only three files directly in `/app`, and the exclusion keeps a virtual
  environment or R library the agent creates there from failing the capture
  with absolute symlinks or size. What remains stricter: a symlink with an
  absolute target directly in `/app`, or more than 2 GiB of files directly in
  `/app`, fails the capture; and a deliverable that is itself a symlink is
  `not_regular` and fails, where pandas would follow it. Files the agent writes
  outside `/app` were never read by the upstream tests either.
- **Allowed domains: stricter.** Upstream gives the agent unrestricted internet
  (`allow_internet = true`). The pack allows only `cloud.r-project.org`, the
  CRAN mirror the image's R is configured with and the only host the reference
  contacts (it installs `remotes` and `bnlearn` 4.9 from there). An agent that
  installs software from elsewhere (PyPI, the Ubuntu archive, GitHub) cannot do
  so under SecureBench. The answer is not published on CRAN.
- **Cases: equivalent.** Upstream has nine tests over three files and no
  random choices of its own; the pack has three artifact checks covering all
  nine. The sample the candidate writes is random (the reference does not set
  a seed), as it is natively; upstream's docstring reports that the reference
  never failed the KS test in repeated runs.

## Candidates

- `reference.sh`: `cd /app`, then upstream `solution/solve.sh` byte for byte.
  No drift repair was needed.
- `null.sh`: changes nothing.
- `mutant-no-intervention.sh`: correct DAG files, but samples the fitted network
  without intervening on Y. Fails both graders (D's mean is about 38 instead of
  15).
- `mutant-near-threshold-pass.sh` and `mutant-near-threshold-fail.sh`: fix Y
  at 1.5 and 1.51 instead of 0 with a seeded sampler (`sample_intervened.R`),
  giving KS statistics 0.019404 (p = 0.00106) and 0.019521 (p = 0.00097), just
  on either side of the bound. They aim at the reimplemented KS test.
- `mutant-write-table.sh`: rewrites all three files with R's `write.table`,
  which pandas reads with an implicit index column. Aims at the reimplemented
  CSV reader; passes both graders.
- `mutant-dag-to-from.sh`: rewrites the DAG files unquoted, with columns in the
  instructions' `to,from` order and one row repeated. Aims at column lookup by
  name and set comparison; passes both graders.
- `attack-nan-d.sh`: correct DAG files and every `D` value `nan`. A KS maximum
  taken by comparisons would ignore NaN and accept.
- `attack-missing-d.sh`: correct DAG files and a sample whose rows lack the
  `D` field that the header names. pandas pads NaN and fails.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: `reference`, `mutant-near-threshold-pass`, `mutant-write-table` and
`mutant-dag-to-from` pass both; `null`, `mutant-no-intervention`,
`mutant-near-threshold-fail`, `attack-nan-d` and `attack-missing-d` fail both
(SecureBench class `oracle`).

## Review

Reviewer: conversion-reviewer (bn-fit-modify-review), 2026-10-26 (third review, pack `sha256:da06349a51a46f2a5b0beaff218dfbf90e4b712290ca14c6827df0c3b0756e3b`)

Since the second review, only `leaves_column_as_text` in `task/hidden/oracle.py`, `task/hidden/differential.py` and this file changed. `instructions.md`, `task.toml`, `expected.json`, `derive_expected.py` and the candidates are unchanged, so points 1 to 5, 7 and 9 stand as checked in the first and second reviews. I re-checked point 6 (the Oracle) and point 8 (qualification).

1. Instructions. Unchanged; identical to upstream `instruction.md` (`cmp`).
2. Scope. Unchanged: `/app` with `*/*` excluded. The deliverables are covered, and the baseline `/app` holds only the input data, with no symlinks. Holds.
3. Expected value leaks. Unchanged. There is no `public/` and no `evaluation/`, every expected value is in `hidden/expected.json`, and the baseline image has no tests or solution. `cloud.r-project.org` does not publish the answer. Holds.
4. Challenges. There are no protocol checks, so there are no challenges. Not applicable.
5. Cases. Three artifact checks cover upstream's nine tests, with no addition. The seed is unused. Holds.
6. Oracle. `validate` passes.
   - The integer rule now follows pandas' integer pass. The first non-integer value ends the pass and the column becomes doubles. A positive integer beyond 2^64 - 1 met before that keeps the column as strings, and so does an integer-only column that needs both int64 and uint64.
   - I checked the rule exhaustively against pandas 2.3.2. The pool had 15 values: integers at and around the int64 and uint64 limits, 25-digit positive and negative integers, `-0`, `+0`, a padded integer, `1.5` and `inf`. Over all 54,240 sequences of one to four of them, pandas' numeric dtype for `D` matched the Oracle's acceptance with 0 mismatches.
   - Full-verdict re-runs on 10,000-row samples also show no mismatch: the six sequences of my second-review finding, the earlier 25-digit row positions, leading-index files and integer fuzz. So do `differential.py 200` (76 sample forms, 325 tokens, 202 fuzzed `D` starts, 21 DAG forms) and my earlier fuzz (0 mismatches).
   - The memory bound is unchanged and holds: peak RSS is at most 180 MiB on 16 MiB adversarial samples, and 119 MiB on a 1 MiB DAG file.
   - All expected values remain in `hidden/expected.json`, and `oracle.py` holds only parsing and comparison logic. Holds.
7. Candidates. Unchanged. The reference is upstream's solution byte for byte after `cd /app`, the mutants run real code aimed at the KS reimplementation and the CSV reader, and both attacks fail. Holds.
8. Divergences. `qualification.json` records `sha256:da06349a...` on all nine SecureBench runs, the digest I validated, and `problems` is empty. Every run is admitted and rejudged, with no dirty runs. The runs name three framework commits; `git diff` shows the SecureBench code is identical across them. Native results are reused from cache, because the candidates and upstream are unchanged. Every candidate gets the same verdict from both graders, and "Divergences from native" says so correctly. Holds.
9. Inventory. There is no `bn-fit-modify` row yet; the coordinator adds it as converted. No exclusion applies.

Upstream assertions. All nine tests map to checks as the table in "How the pack grades" shows. None is dropped. Every remaining difference is listed with a label and a reason: the byte-order mark (stricter), the file size bounds (stricter), and the float parser's last-place rounding (either way, within about 1e-16 of the bound).

Earlier findings. All are fixed: leading index fields (first review), oversized integers (first and second reviews), the Oracle's memory (first review) and the missing divergences section (first review).

Findings:
- None.

Verdict: approved
