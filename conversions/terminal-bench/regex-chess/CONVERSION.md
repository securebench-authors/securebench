# regex-chess

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/regex-chess

## How the pack grades

The deliverable is one data file, `/app/re.json`, a list of `[regex, replacement]` pairs. Upstream's `tests/test_outputs.py` has four tests, and each becomes part of a check:

| Upstream test | SecureBench check | What it compares |
| --- | --- | --- |
| `test_not_long`, `len(open("/app/re.json").read()) < 10e6` | artifact check `not-long-characters` (text parser) | character count, computed as Python's text mode counts it |
| `test_not_long`, `len(json.loads(...)) < 1e5` | artifact check `not-long-pairs` (text parser) | `len()` of the top-level value, computed from the text as Python's `json` would decode it |
| `test_immortal_game` | case 0 of protocol check `legal-moves` | 24 positions |
| `test_game_of_century` | case 1 of `legal-moves` | 42 positions |
| `test_naroditsky_ivanchuk` | case 2 of `legal-moves` | 42 positions |

For each game case the challenge is the list of FENs that upstream's `do_test_game` passes to `verify_legal_moves`, in the same order (including the starting position twice, as upstream tests it twice). The adapter, `evaluation/adapter.py`, runs upstream's `run_solution` loop on each FEN (the same `json.load(open("/app/re.json"))` and `re.sub` calls, on the baseline's own Python 3.13.7, which lies outside the scope) and returns each final string unchanged. If the loop raises, the adapter reports `unable`, as upstream's test errors. The Oracle then does the rest of `run_solution` and both assertions of `verify_legal_moves`: it splits the string on `"\n"`, drops the last two space-separated fields of each line, requires every line to be one of python-chess's positions (or to become one when its en-passant field is replaced by `-`), and requires the number of lines to equal the number of python-chess positions. Like upstream, it counts lines, not distinct lines.

The expected positions are in `hidden/cases.json`. `hidden/derive.py` produced them inside the baseline image, which has python-chess 1.11.2, the version upstream's `test.sh` pins; it copies upstream's PGNs, position walk and expected-set construction unchanged. To redo it:

```sh
docker run --rm -v "$PWD/task/hidden:/h:ro" \
  alexgshaw/regex-chess@sha256:e3b6d61d2d3930fbbdc5f7bf091a7f8b7f6125e1951ef8a7dbe165b1ef62942c \
  python3 -I /h/derive.py > cases.json
```

The position counts (24, 42, 42) match what upstream's tests print when run on the reference, and the reference passes every case.

The adapter starts the interpreter with `-I`, so `/app`, the working directory, is never on `sys.path`: a candidate cannot replace `json` or `re` by placing modules there (`attack-cwd-module-hijack`). Changes the agent makes to the interpreter itself are outside the scope and are not replayed (`attack-stdlib-patch`).

## Fidelity changes

- **Instructions:** `instructions.md` is upstream `instruction.md` byte for byte. Equivalent.
- **Scope:** all of `/app`, internal symlinks allowed, at the framework's maximum bounds (100,000 entries, 2 GiB). The instructions name only `/app/re.json`, so every solution they allow lives there. Changes outside `/app`, for example to the image's Python, are not graded. Stricter only for a solution that leaves more than 2 GiB or 100,000 entries in `/app`, which capture rejects, or that relies on changes outside `/app`, which is tampering with the grader rather than solving the task.
- **`re.json` as a symlink:** the artifact checks do not follow symlinks, so a `/app/re.json` that is a symlink (even to another file in `/app`) is `not_regular` and fails; upstream follows it. Stricter; the instructions ask for a JSON file at that path.
- **Character count:** upstream counts the characters Python's text mode returns. SecureBench's text parser keeps `\r`, so the Oracle subtracts one character per `\r\n`, which is exactly what universal newlines remove (a lone `\r` becomes `\n` and keeps the length). Both reject a byte-order mark (upstream through `json.loads`) and invalid UTF-8. The text check reads at most 16 MiB, so a file above 16 MiB that still has fewer than 10,000,000 characters (possible only with mostly multi-byte characters) fails here and passes upstream. Stricter in that case, equivalent otherwise. `mutant-crlf-escaped-markers` sits between the two counts (more than 10,000,000 bytes, 9,979,768 characters) and passes.
- **Pair count:** upstream takes `len()` of what Python's `json` loads. SecureBench's strict JSON parser rejects some files Python's `json` loads, among them lone-surrogate escapes such as `"\ud800"`, which a working list of string pairs can use as a marker. So this check reads the file with the text parser, and the Oracle computes the length itself with a small bounded scanner (`_json_length` in `hidden/oracle.py`): the number of elements of a top-level array, the number of distinct keys of a top-level object, or the number of code points of a top-level string, with escapes and surrogate pairs decoded as Python's `json` does; any other top-level value has no length and fails, as `len()` raises upstream. The scanner checks only what it needs to count. A file it accepts but Python's `json` rejects (for example a trailing comma, or nesting between Python's recursion limit and the scanner's bound of 10,000 levels, where Python always fails) still fails every game case, because the adapter loads the file with Python's `json` exactly as upstream and reports `unable` when that raises, so the overall verdict is upstream's. We compared the scanner with `len(json.loads(text))` in the baseline's Python 3.13.7 on 200,000 generated documents (nested arrays and objects, duplicate and escaped keys, lone and paired surrogates, invalid escapes, control characters, `NaN`, trailing garbage): every document Python's `json` loads got the same length, and none without a length got one. On the reference's file, `mutant-crlf-escaped-markers`' and `mutant-too-many-pairs`' it gives 40,460, 40,463 and 100,000, as Python does. The scan takes time linear in the file: every loop advances through the text, and each search for the next quote or backslash is kept and reused until the scan passes it, so no part of the text is searched twice. On 16 MiB files in the baseline's Python it took 8.4 s for one string of `\n` escapes, 5.2 s for `["a","b"]` pairs, 5.1 s for a string of `\u00e9` escapes and 0.9 s for one string without escapes, well inside the framework's 60-second judge timeout. Equivalent. `mutant-crlf-escaped-markers` (a lone-surrogate marker and a 1,200,000-escape string) passes and `mutant-too-many-pairs` (exactly 100,000 pairs) fails.
- **Output bounds:** the adapter's observation allows 64 positions per case, 64 KiB per position's final string and 4 MiB per case, and strict JSON cannot carry a lone surrogate. A correct output has at most 218 lines of a FEN plus the two counter fields that upstream drops unread, so these bounds reject a correct answer only if its counter fields hold kilobytes of garbage or a lone surrogate. Stricter in those cases. `mutant-long-counters` writes 300-character counters and passes.
- **Timeout:** each game case may take 3,600 seconds, upstream's verifier timeout. Upstream runs the three games and the size test one after another inside one 3,600-second budget, which also covers installing uv and pytest. The reference takes about 90 to 135 seconds per game on one CPU in both. More lenient for a candidate whose regexes take more than about 1,200 seconds per game; the instructions set no speed requirement, and dividing upstream's shared budget among cases would be arbitrary.
- **Order:** artifact checks run before the cases, and the first failure cancels the rest; upstream runs every test and fails if any fails. The verdict is the same conjunction. Equivalent.
- **Interpreter:** the adapter uses the baseline's Python 3.13.7. Upstream's `test.sh` runs `uvx -p 3.13`, which finds the same interpreter in the image: `attack-stdlib-patch`, which patches that interpreter's `re`, passes the native grader. Equivalent.
- **Domains:** none. The reference needs no network. Equivalent: upstream's network was used only to install the test tooling.
- **Cases:** upstream's three game tests and its size test, no more and no fewer.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` unchanged after a `cd /app`. It always records an en-passant square after a double push, so it exercises upstream's en-passant leniency.
- `null.sh`: changes nothing; there is no `re.json`.
- `mutant-no-en-passant-square.sh`: the reference plus a pair that blanks the en-passant field. Aimed at the Oracle's copy of the leniency, which accepts an extra square but not a missing one. Expected to fail both graders.
- `mutant-duplicate-move.sh`: the reference plus a pair that replaces the last move with a copy of the first. Aimed at counting lines rather than distinct lines. Expected to pass both graders.
- `mutant-crlf-escaped-markers.sh`: the reference plus two pairs that write and remove a lone-surrogate marker (`["$", "\ud800"], ["\ud800", ""]`) and one never-matching pair whose replacement is 1,200,000 `é` markers, which `json.dump` writes as `\u00e9` escapes. It is rewritten with CRLF line endings and padded between the byte and character limits. Aimed at both reimplemented counts: the character count, and the pair count, which SecureBench's strict JSON parser could not read and which a scanner rescanning from each escape would not finish within the judge timeout. Its output equals the reference's. Expected to pass both.
- `mutant-too-many-pairs.sh`: the reference padded with never-matching pairs to exactly 100,000. Aimed at the threshold of the Oracle's pair count. Expected to fail both.
- `mutant-long-counters.sh`: the reference with 300-character move counters. Aimed at the Oracle dropping the counter fields and at the observation bounds. Expected to pass both.
- `attack-cwd-module-hijack.sh`: plants `re.py`, `json.py`, `sitecustomize.py` and `usercustomize.py` in `/app` that answer with python-chess, plus a one-pair `re.json` only the hijacked `re.sub` understands. Verified to pass upstream's game test when `/app` is on `sys.path`; the adapter's `-I` keeps it off.
- `attack-stdlib-patch.sh`: patches `re.sub` in the image's Python standard library to answer with python-chess for a marker pattern. Verified to pass upstream's game test inside the agent's container; SecureBench does not capture the patch.
- `attack-memory-bomb.sh`: 40 pairs that each double the string, to turn a failure into an infrastructure error. It ends `failed`, class `case_error`.

## Divergences from native

- `attack-stdlib-patch`: native reward 1.0, SecureBench `failed` (class `oracle`). SecureBench is right. The candidate's `re.json` is a single marker pair that solves nothing; it passes natively only because upstream's verifier runs in the agent's own container, and `uvx -p 3.13` picks up the image's Python 3.13.7, whose `re.sub` the candidate patched to answer with python-chess. SecureBench captures only `/app`, so the patch never reaches the Evaluation and the marker is applied as a plain regex, leaving each FEN unchanged.

Every other candidate gets the same verdict from both graders: `reference`, `mutant-crlf-escaped-markers`, `mutant-duplicate-move` and `mutant-long-counters` pass both; `null`, `mutant-no-en-passant-square`, `mutant-too-many-pairs`, `attack-cwd-module-hijack` and `attack-memory-bomb` fail both.

## Review

Reviewer: a673d2d8d1d0be403, 2026-10-27 (review 3)

Pack digest at review: `sha256:c886e1903cbc5d64f986cb63703f9263be4a645b96291f6af3f1413147b2da28` (`securebench validate`: valid). Every SecureBench run in `qualification.json` records this digest.

Finding of review 1 (the strict JSON parser rejects lone surrogates): fixed. `not-long-pairs` reads `/app/re.json` with the text parser, and `_json_length` in `hidden/oracle.py` counts the top-level value as Python's `json` would. `mutant-crlf-escaped-markers` carries a lone-surrogate marker and passes both graders.

Finding of review 2 (the scanner's running time grew with the square of the input): fixed. `_next` keeps the last position found for each needle and searches again only once the scan has passed it. Positions only grow, so each needle's searches cover the text once. The other loops all advance the index.
- I timed the new scanner in the baseline's Python 3.13.7 on 16 MiB files: 6.7 s for one string of `\n` escapes, 4.4 s for `é` escapes, 3.5 s for surrogate pairs and 5.3 s for lone high surrogates followed by an escape. For other shapes: 4.4 s for `["a","b"]` pairs without backslashes, 6.0 s for 5.6 million empty strings, 2.6 s for 8.4 million zeros, 2.8 s for 1.4 million object keys, and 2.5 s for 9,990 levels of nesting followed by zeros.
- Every case is well inside the 60-second judge timeout, and a file a correct solution can use (under 10,000,000 characters) takes less.
- The file that failed in review 2 (1.2 million `é` escapes) is now part of `mutant-crlf-escaped-markers`, which passes both graders.
- The cache does not change the counts. I compared the new scanner with `len(json.loads(text))` on 200,000 random documents (nested arrays and objects, duplicate, escaped and surrogate keys, commas and brackets inside strings, invalid escapes, control characters, `\r`, `NaN`, random insertions). On the 149,463 that Python loads there were no mismatches.
- The "Pair count" bullet now gives measured times that agree with mine.

1. Instructions: `cmp` against upstream `instruction.md` finds no difference. Equivalent.
2. Scope: unchanged, one root `/app`. The baseline's `/app` holds only `check.py` and has no symlinks. Grading loads nothing from `/app` by convention. The adapter runs the baseline's `/usr/local/bin/python3` with `-I`, so no file in `/app` can reach the interpreter. No problem.
3. Expected values: only in `hidden/cases.json`. `evaluation/` (the adapter and two schemas, unchanged) and the baseline image hold none. There are no allowed domains. No problem.
4. Challenges: each challenge carries only its own game's FENs. No problem.
5. Cases: unchanged. `derive.py` reproduces `cases.json` byte for byte. Upstream's own `test_outputs.py` walk, run in the baseline with a recorder in place of `verify_legal_moves`, gives the same FENs and expected sets (24, 42, 42), the starting position included twice as upstream tests it. Nothing was added and the seed is unused. No problem.
6. Oracle: `oracle.py` holds only judging logic and upstream's two thresholds. Every expected position is read from `hidden/`. The game judgment applies upstream's `run_solution` post-processing and both `verify_legal_moves` assertions line for line: it counts lines, not distinct lines, and keeps the en-passant leniency. It requires the single `outputs` field with one string per FEN, and any non-observation outcome fails. The character count matches universal newlines. The pair count matches Python's `json` wherever Python loads the file. Where Python does not, the adapter's `json.load` fails every game case, as upstream's tests fail. All work over candidate data is bounded: the schema limits the game observations, and the scan of the 16 MiB text runs in linear time. No problem.
7. Candidates: `reference.sh` is upstream `solve.sh` plus a shebang, a comment and `cd /app`. `null.sh` changes nothing. There are five mutants, each running real regexes. Each targets a place where the conversion's check differs from upstream: line counting, the en-passant leniency, the counter fields and observation bounds, both reimplemented length counts (lone surrogate, escape-dense string, CRLF, a size between the byte and character limits), and the pair threshold. The three attacks fit this task: a working-directory module hijack, a standard-library patch outside the scope, and a memory bomb that ends `case_error`, not `invalid`. I found no further tampering route. The deliverable is data, the interpreter lies outside the scope, and runaway regexes end as a timeout or memory kill, both `failed`.
8. Divergences: `qualification.json` reports no problems. All runs were admitted, rejudged and clean (`dirty: false`) at the digest above. They record four framework commits, but `git diff` shows no change under `securebench/` between them. The reference passes both graders and the null candidate fails both. Every mutant gets the same verdict from both: `mutant-crlf-escaped-markers`, `mutant-duplicate-move` and `mutant-long-counters` pass, and `mutant-no-en-passant-square` and `mutant-too-many-pairs` fail. Every attack ends `failed`. The one divergence is `attack-stdlib-patch` (native 1.0, SecureBench `failed`), and the explanation holds: the patch to the image's `re` lies outside `/app`, so it is not captured. Its native pass also confirms that `uvx -p 3.13` uses the image's Python 3.13.7, which supports the "Interpreter" bullet.
9. Inventory: `conversions/inventory.tsv` has no `regex-chess` row yet; the coordinator adds it on commit. No exclusion reason applies: the task converts.

Upstream assertions: `test_not_long`'s two assertions map to `not-long-characters` and `not-long-pairs`. In `verify_legal_moves`, the membership assertion (with the en-passant alternative) and the count assertion are applied to every FEN `do_test_game` walks in each of the three game tests. An exception in `run_solution` becomes the adapter's `unable`, as upstream's test errors. `do_test_game`'s PGN-parse `ValueError` cannot fire on the fixed PGNs. Nothing is dropped, and every fidelity change in `CONVERSION.md` is labelled with its reason.

Findings:
- None.

Verdict: approved
