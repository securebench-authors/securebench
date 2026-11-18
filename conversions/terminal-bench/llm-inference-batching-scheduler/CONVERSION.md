# llm-inference-batching-scheduler

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/llm-inference-batching-scheduler

## How the pack grades

The agent must write two JSON Lines plans, `/app/task_file/output_data/plan_b1.jsonl`
and `plan_b2.jsonl`, and leave the two request files under
`/app/task_file/input_data` unchanged. Upstream's six tests all read that final
state; any failing test fails the task. They map to two checks:

| Upstream test | Check | How |
|---|---|---|
| `test_input_data_integrity` | `input-integrity` (artifact) | The capture's SHA-256 of each request file must equal upstream's `EXPECTED_INPUT_HASHES` (kept in `hidden/cases.json`). |
| `test_output_files_exist` | `plans` (protocol, 1 case) | The adapter reports `unable` when a plan file cannot be opened, which fails the case. |
| `test_generate_and_schema` | `plans` | Same request_id set as the input; `seq_align % 64 == 0`; `heads_align == 32`; `hidden_align == 4096`; at most 8 shapes per bucket. |
| `test_solution_shape_feasibility_and_batch_consistency` | `plans` | `seq_align >=` the request's aligned prompt; every record of a batch has an equal `shape` dict. |
| `test_solution_coverage_no_duplicates` | `plans` | Same set of ids and no id twice. |
| `test_performance_thresholds` | `plans` | The four metrics of each bucket against upstream's thresholds, and at most 8 shapes across both buckets. |

The adapter (`evaluation/adapter.py`, standard-library Python on the stock
interpreter) parses each plan exactly as upstream does,
`[json.loads(line) for line in open(path)]`, and reports every record as typed
values: `request_id`, the batch id (`batch_text` for a string, `batch_number`
for a number), the three shape integers, and `shape_extra`, the canonical JSON
text of any other keys in `shape`. It holds no expected value and decides
nothing beyond whether a record is usable at all (next section).

`hidden/oracle.py` applies the assertions above. For the metrics it runs a
statement-by-statement transliteration of upstream's
`tests/cost_model_for_tests.py` (`CostModel.plan_metrics`) over the hidden copy
of the requests, so the plan is scored against the original requests even if
the candidate edited its copy. `hidden/cases.json` holds every number the
verdict depends on: the requests, the input hashes, the granularity, the shape
constants, the shape cap, the thresholds, the p95 quantile and the cost
constants. `hidden/derive_cases.py` rebuilds it from the upstream task
(`python3 -B derive_cases.py <upstream task dir> cases.json`); it checks the
shipped request files against upstream's hashes and reads `HEADS`, `HIDDEN` and
the cost constants from upstream's cost model rather than copying them by hand.

## Fidelity changes

- **Records upstream cannot use are reported as `unable` by the adapter
  (equivalent).** Each of these makes an upstream test raise or fail an
  assertion, so the task fails either way: a line that is not JSON (a blank
  line, a record pretty-printed over several lines, a UTF-8 BOM); a record that
  is not an object or lacks `request_id`, `batch_id` or `shape`, or whose
  `shape` lacks one of its three keys; a `request_id` that is not a string (it
  cannot equal any input id); a shape value that is a boolean, a string, null,
  a non-integral or non-finite number, or beyond 2^53 in magnitude (it fails
  `% 64 == 0`, `== 32`, `== 4096` or, for a huge `seq_align`, the cost
  threshold: the per-shape compile cost alone is 500·seq_align², above both cost
  thresholds once seq_align exceeds 24,494); a plan longer than 5,000 lines (a
  plan must have exactly one line per request, 800 per bucket); a request id
  longer than 256 bytes (input ids are 8 to 10 bytes).
- **Integral float shape values are reported as integers (equivalent).**
  Upstream's comparisons, its `int()` conversion in the cost model and its dict
  equality treat `192.0` exactly as `192`.
- **Batch ids may be strings or numbers, as upstream allows (equivalent).**
  Upstream uses `batch_id` as a dict key and sorts the keys. The adapter reports
  a string as `batch_text` and a number as `batch_number` (a boolean as 0 or 1,
  since Python treats `true` as 1), and the Oracle groups and sorts these values
  with the same Python semantics. A plan that mixes string and numeric batch ids
  fails, because upstream's `sorted()` raises `TypeError` on it.
- **Some batch ids and request ids are reported as `unable` (stricter for the
  cases upstream could accept, all edge cases).** Arrays and objects cannot be
  dict keys upstream, and a null batch id can only stand alone (one batch for a
  whole bucket, far above the cost thresholds), so those fail upstream too.
  Upstream could accept the following, which fail here:
  - a batch id that is a non-finite number (the strict-JSON transport has no
    NaN or infinity);
  - a string batch id longer than 512 bytes (the bound keeps the observation
    within its size limit);
  - an integer batch id of magnitude 2^63 or more (SecureBench's JSON reader
    accepts integer literals of at most 20 characters);
  - a string batch id holding a lone surrogate such as `"\ud800"`, which
    `json.loads` accepts but strict JSON transport cannot carry. A request id
    with a lone surrogate is also reported `unable`; it cannot equal an input
    id, so upstream fails it too.

  Every finite float batch id is reported: `observation.schema.json` bounds
  `batch_number` by the largest finite double.
- **Extra keys in `shape` are compared through canonical JSON text
  (equivalent, with one stricter edge).** Upstream compares whole `shape` dicts
  within a batch, so extra keys matter only for that equality. The adapter
  reports them as JSON text with sorted keys, after mapping booleans and
  integral floats to integers so that values Python finds equal (`1`, `1.0`,
  `true`) print identically. Extra values holding NaN or infinity, or longer
  than 512 bytes of text, are reported as `unable` (stricter; upstream could
  accept them).
- **Extra keys in a record are ignored (equivalent).** Upstream ignores them too.
- **The metrics are computed by a transliteration of upstream's cost model
  (equivalent).** It performs the same floating-point operations in the same
  order. Compared with upstream's `CostModel.plan_metrics` on 802 plans (the
  reference's two plans and 400 random perturbations of each: moved, merged
  and split batches, raised shapes, shuffled records, integer and float batch
  ids, float shapes), all four metrics were bit-identical on every plan, so
  every threshold comparison agrees, however close to the threshold. The
  differential test was run on the host in the scratch directory and is not
  part of the pack.
- **Scope excludes `**/.venv` and `**/venv` (equivalent for those names;
  stricter for other names).** Nothing graded is inside a virtual environment,
  and a venv's absolute symlink to the system interpreter would otherwise make
  capture fail a correct candidate. A virtual environment under any other name
  inside `/app` (for example `/app/env`) still holds that absolute symlink, so
  capture fails the candidate (class `capture`) while upstream passes it. An
  exclude pattern cannot name every directory an agent might choose, and
  excluding all of `/app` except the graded files is not expressible.
- **A request file replaced by a symlink fails the integrity check (stricter,
  edge case).** The artifact check reads regular files only; upstream follows
  the link and passes if the target is identical.
- **No network for the agent (stricter).** Upstream's `task.toml` sets
  `allow_internet = true`; the pack's `allowed_domains` is empty, so an agent
  cannot `pip install` a library (numpy, scipy, a solver) to build its
  scheduler. The brief allows only the domains the reference needs, and the
  reference uses only the standard library and the image's Python. The image
  has no third-party packages, so an agent must write its scheduler in plain
  Python.
- **Instructions and cases: unchanged.** `instructions.md` is upstream's
  `instruction.md` byte for byte. Upstream's tests read one final state; the
  pack has one protocol case plus the artifact check.

`reference.sh` runs upstream's `solution/solve.sh`, kept byte for byte as
`candidates/solve-upstream.bash`, with bash: upstream's script uses
`set -o pipefail`, which the POSIX `sh` that SecureBench's scripted harness uses
does not support. No drift repair was needed.

## Verdict comparison with upstream's own tests

`mutant-float-shapes` carries two of these variants into qualification: float
shape values, and an extra shape key cycling through `1`, `1.0` and `true`
within each batch. Upstream's pytest passes that plan (checked in the task
image), and so does SecureBench.

Besides qualification, 19 plan variants were graded both by upstream's
`tests/test_outputs.py` (pytest 8.4.1 in the task image) and by the adapter plus
Oracle. All 19 verdicts agree:

| Variant | Both graders |
|---|---|
| reference plans; reversed record order; CRLF line endings; float shape values; integer, float and boolean-plus-integer batch ids; extra record keys; the same extra shape key on every record; extra shape values `1` and `1.0` within a batch | pass |
| trailing blank line; pretty-printed records; UTF-8 BOM; a duplicate record; a missing record; `heads_align` as the string `"32"`; one batch with an extra shape key the others lack; string and integer batch ids mixed; a ninth shape | fail |

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both
graders: the reference and `mutant-float-shapes`, `mutant-int-batch-ids` and
`mutant-under-threshold` pass; `null`, `mutant-pretty-json` and
`mutant-over-threshold` fail. All three attacks fail in SecureBench and also
score 0 natively.

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-27 (second review, after the converter's fixes)

Pack digest reviewed: `sha256:3fbf4085313d8b460f4d1bc593f364c27c0cc00afff00cc4a0e3b665a5a35ab7` (`securebench validate`: valid). Since the first review (digest `b8f3a831…`), only `evaluation/observation.schema.json`, `candidates/mutant-float-shapes.sh`, `candidates/rewrite_plans.py` and this record changed. The adapter, the Oracle, `cases.json` and `derive_cases.py` are unchanged.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. One root, `/app`, which must contain the workdir `/app`. The baseline has no symlinks under `/app` and no `/.securebench`. Upstream's tests live outside the image, and the adapter runs the stock interpreter with `-I` and imports nothing from the candidate, so no test or convention-loaded file needs excluding. `**/.venv` and `**/venv` match at any depth. A virtual environment under any other name fails capture; this is now recorded as stricter in the scope bullet, with the reason no pattern can cover it.
3. No expected value leaks. There is no `public/`; `evaluation/` holds the adapter and two schemas, with no expected value. The request files and the cost model in the baseline are public by design, and the thresholds are in the instructions. The Oracle reads every number from `hidden/cases.json`, never from the Evaluation. Re-running `hidden/derive_cases.py` on the upstream task reproduces `cases.json` byte for byte. Domains are empty, so 4.7 does not apply.
4. Challenges. The challenge is the two plan paths only.
5. Cases. One protocol case for upstream's single final-state run, plus the integrity artifact check. No case added; the seed is unused.
6. Oracle. Unchanged since the first review: only judging logic and a cost-model transliteration; every field checked; coverage and duplicates counted as upstream does; work bounded by the schema; claims ignored. My independent differential (600 random plans, every batch-id type, through `adapter.record`, a JSON round trip and `_plan_metrics`, against upstream's `tests/cost_model_for_tests.py`) gave bit-identical metrics on all of them. The `batch_number` bound is now ±1.7976931348623157e308, the largest finite double, so every finite float batch id upstream accepts is reported. No regression tests run by outcome.
7. Candidates. `reference.sh` runs upstream `solve.sh` unchanged with bash. `mutant-float-shapes` now also adds an extra shape key `rank` that cycles through `1`, `1.0` and `true` by record index. Every batch with two or more records therefore holds unequal JSON spellings of values Python finds equal, which exercises the adapter's `canonical()` text and the Oracle's whole-shape comparison. Both graders pass it. The other mutants cover JSON Lines reading, batch-id typing and the cost model on both sides of a threshold. The three attacks are a rewritten agent-writable cost model, tampered request files and forged claims; all fail in SecureBench.
8. Divergences. `qualification.json` was written after the last change. It reports no problems, and every SecureBench run records digest `3fbf4085…` and framework commit `f9b42b7` (not dirty), with `rejudged: true` and no native result cached. Verdicts agree on every candidate. The reference, `mutant-float-shapes`, `mutant-int-batch-ids` and `mutant-under-threshold` pass both graders. `null`, `mutant-pretty-json` and `mutant-over-threshold` fail both. The three attacks fail in SecureBench and score 0 natively. "Divergences from native" says "None", and that matches.
9. Inventory. No row yet, as expected before approval. No exclusion reason applies.

Upstream assertions: every assertion of the six upstream tests maps to a check (table in "How the pack grades"). None is dropped.

Findings from the first review, re-checked:
- Domains recorded as unchanged: fixed. A new bullet, "No network for the agent (stricter)", gives the reason, and the "unchanged" bullet now covers only instructions and cases.
- No mutant for the extra-shape-key canonicalization: fixed, by folding it into `mutant-float-shapes` (still five mutants). Qualified: both graders pass.
- Unlisted stricter edges: fixed. Integer batch ids of 2^63 or more and lone-surrogate ids are listed. Large finite float batch ids are no longer stricter, because the schema bound is now the largest double. Other venv names are recorded in the scope bullet.

Findings:
- None.

Verdict: approved
