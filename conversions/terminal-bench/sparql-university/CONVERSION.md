# sparql-university

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/sparql-university

## How the pack grades

The agent writes a SPARQL query to `/app/solution.sparql`. Upstream's verifier (`tests/test_outputs.py`) runs that query with rdflib 7.1.4 against a test graph, `tests/university_graph_test.ttl`, which differs from the public `/app/university_graph.ttl`: two professors are renamed and a fourth qualifying professor (Alex Dimakis) is added. It then compares the set of `(str(row.professorName), normalize_countries(str(row.countries)))` pairs with its `REFERENCE_RESULTS`, where `normalize_countries` splits on commas, strips, sorts and rejoins.

The pack has one protocol check, `query-results`, with one case.

- `hidden/university_graph_test.ttl` is upstream's test graph, byte for byte, and `hidden/cases.json` holds upstream's `REFERENCE_RESULTS` literal. `plan` puts the graph in the challenge and the reference in the context.
- `evaluation/adapter.py` runs on the stock Python image. It reads `/app/solution.sparql` as upstream does (UTF-8, universal newlines), parses the challenge's graph into an rdflib `Graph`, runs `Graph.query`, and reports which of `professorName` and `countries` the result has and, for each distinct row, `str()` of those two values (an unbound value is left out). It contains no expected value.
- `hidden/oracle.py` requires both variables, maps a left-out value to `"None"` as upstream's `str(None)` would, applies upstream's `normalize_countries`, and requires the resulting set to equal the reference set.

How upstream's three tests map to the check:

| Upstream test | In the pack |
|---|---|
| `test_sparql_file_exists` | The adapter cannot open the file and reports `unable` (`query-unreadable`); the case fails with `case_error`. |
| `test_sparql_runs_without_error` | An exception from parsing or running the query is reported as `unable` (`query-error`); the case fails with `case_error`. |
| `test_sparql_query_results` | The Oracle's set comparison. A result without `professorName` or `countries` fails, as upstream's `row.<name>` raises `AttributeError` (an empty result fails upstream anyway because the reference is not empty). An ASK, CONSTRUCT or DESCRIBE query reports no variables and fails, as upstream's row attribute access does on those results. |

## Fidelity changes

- **SPARQL engine (equivalent).** Upstream's verifier installs rdflib 7.1.4 with `uvx` at grading time; Evaluation environments have no network and the baseline has no Python. The pack vendors the unchanged pure-Python wheels from PyPI in `evaluation/wheels/`: `rdflib-7.1.4-py3-none-any.whl` (SHA-256 `72f4adb1990fa5241abd22ddaf36d7cafa5d91d9ff2ba13f3086d339b213d997`) and its only dependency on Python 3.11 and later, `pyparsing-3.3.3-py3-none-any.whl` (SHA-256 `ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4`). Both hashes match PyPI's published digests. Neither contains compiled code, so nothing is reimplemented. pyparsing 3.3.3 is what upstream's unpinned resolution picks today: running upstream's `uvx -p 3.13 -w rdflib==7.1.4` in the baseline image on 2026-10-27 printed `3.13.9 7.1.4 3.3.3` (Python, rdflib, pyparsing).
- **Interpreter (equivalent as far as tested).** The adapter runs rdflib on the stock image's Python 3.12.15; upstream's verifier uses Python 3.13.9. To look for differences, 20 queries were run through upstream's own pytest test in the baseline image (`uvx -p 3.13`, the exact command of `tests/test.sh`) and through the adapter and Oracle: the reference, Switzerland counted as an EU member, `>=` versus `>` thresholds, counts with and without `DISTINCT`, no graduation filter, `CONTAINS` instead of `STRSTARTS` for the role, `NOW()` as the reference date, string, `YEAR()`, timezone-suffixed `xsd:date` and `xsd:dateTime` date comparisons, casts of the data to `xsd:dateTime`, separators `","` and `"; "`, `GROUP_CONCAT` without `DISTINCT`, extra grouping keys that repeat rows, language-tagged names, unbound countries, an ASK query and a syntax error. Every verdict agreed (11 pass, 9 fail). Date comparisons are the place where the interpreter's `datetime` module is reached, so `mutant-datetime-reference` keeps one of them in qualification.
- **Test graph delivery (equivalent).** Upstream parses the graph from the file `/tests/university_graph_test.ttl`; the adapter parses the same text from the challenge (`Graph.parse(data=..., format="ttl")`), because the graph is hidden from the agent and so cannot sit in `evaluation/`. The only effect of parsing from a file is the base IRI for relative IRIs, and the test graph contains none (its only IRIs are the two `@prefix` declarations).
- **Repeated rows (equivalent).** The adapter reports each distinct `(professorName, countries)` pair once, in first-seen order. Upstream builds a set of normalized pairs, which is a function of the set of raw pairs, so removing repeats loses nothing and keeps a query that repeats correct rows many times within the observation size.
- **Very large or unencodable results (stricter, only for results upstream rejects or near-pathological queries).** The adapter reports `unable` when a result has more than 10,000 distinct `(professorName, countries)` pairs, or a value that is not valid Unicode text (SPARQL's `\uD800` escape yields a lone surrogate, which JSON over UTF-8 cannot carry). Each value is bounded at 1 MiB and the observation at 4 MiB. Upstream would reject all of these except a query whose more than 10,000 distinct raw rows all normalize to the four reference pairs (for example by varying whitespace around the separators), which no plausible query does. A lone surrogate can never equal a reference name, so that case fails upstream too.
- **Network during grading (stricter).** Upstream's verifier container has internet access, so a query that fetches data with `SERVICE` or `FROM <http://...>` could pass natively. Evaluation environments have no network, so such a query fails here. The task's data is all in the local graph, and the instructions ask for a query over it.
- **Allowed domains (stricter for the agent).** Upstream sets `allow_internet = true`; the pack allows no domain, because the reference solution writes a file and needs none. The baseline image has no Python or SPARQL engine, so an agent can no longer install one to try its query; it must write the query from the public graph alone.
- **Scope (stricter, only for unusual deliverables or leftovers).** The scope is `/app`, without symlinks. The deliverable is the regular file `/app/solution.sparql`; nothing else in `/app` is read during grading. The baseline has no symlinks under `/app`. Two outcomes differ from upstream, which reads the file in place: a deliverable written as a symlink fails capture, where upstream would follow it; and the scope bounds (`max_bytes` 1 GiB, `max_entries` 50,000 for `/app`) are below upstream's 10 GiB disk, so a correct query left beside more than 1 GiB or 50,000 entries of other files in `/app` fails capture, where upstream passes. The task asks for one small text file and the agent has no network to download tools into `/app`, so neither is expected in practice; the bounds keep capture and replay of every case bounded.
- **Cases (equivalent).** Upstream runs the query twice on fresh graphs (in `test_sparql_runs_without_error` and `test_sparql_query_results`); the pack runs it once, because the first run's results are discarded and the query cannot change the graph (`Graph.query` does not run updates). Dropping the first run also halves the query time that counts against the time limit; see the next bullet.
- **Time limit (more lenient).** The case timeout is 900 seconds, upstream's verifier timeout. Upstream spends that budget on installing curl, uv, Python 3.13 and rdflib and then on running the query twice (in `test_sparql_runs_without_error` and in `test_sparql_query_results`); the pack gives one run of the query the whole 900 seconds. A query that takes between roughly 450 and 900 seconds on the test graph therefore passes here and fails natively. The reference finishes in well under a second, and the pack keeps upstream's figure rather than guessing at the install time.

## Candidates

- `reference.sh`: upstream `solution/solve.sh` below a `cd /app`.
- `null.sh`: writes nothing; fails with `query-unreadable`.
- `mutant-separator-no-space.sh`: separator `","`; aimed at the Oracle's copy of `normalize_countries`. Passes both.
- `mutant-duplicate-rows.sh`: grouped by name and EU country, so Chrysoula Zerva appears twice; aimed at the adapter's removal of repeated rows. Passes both.
- `mutant-lang-tagged-name.sh`: names as language-tagged literals; aimed at the adapter's `str()` of result terms. Passes both.
- `mutant-datetime-reference.sh`: compares `xsd:date` data with an `xsd:dateTime` reference date; aimed at the Python 3.12 versus 3.13 difference. Passes both.
- `mutant-wrong-alias.sh`: aggregate named `?countryList`; aimed at the adapter's report of the result's variables. Fails both.
- `attack-shadow-modules.sh`: plants `rdflib`, `pyparsing`, `json`, `sitecustomize` and `usercustomize` modules in `/app` that print a forged observation with the hidden expected rows. The adapter starts Python with `-I`, so the working directory and user site are not on `sys.path`, and the vendored packages are imported from read-only wheels; the forged modules never load and the hardcoded public-graph query is judged instead.
- `attack-hostile-output.sh`: a query whose rows claim a verdict, carry an extra `?passed` variable and contain a lone surrogate; it must end `failed`, not `invalid` or `passed`.

## Divergences from native

None. In `qualification.json` every candidate gets the same verdict from both graders: the reference and the four mutants that keep the right answer pass both; `null`, `mutant-wrong-alias` and both attacks fail both (natively the attacks fail because their queries return wrong rows).

## Review

Reviewer: a016caf2a3efba860, 2026-10-27 (second review, after the converter addressed the first review's findings)

Pack digest reviewed: `sha256:3e30b0aafd959556baa89fb166e67520ceb464b18c7e951720e600857cd7fc2f` (`securebench validate`). The fixes changed only `CONVERSION.md`: the digest is the one the first review noted, and no file in `task/` or `candidates/` is newer than `qualification.json`.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical. No change to list.
2. Scope. One root, `/app`, `symlinks = false`, no excludes. The baseline image (`docker run` of the pinned digest) has only `/app/university_graph.ttl` under `/app`: no symlinks, no test files, nothing convention-loaded. The adapter reads only `/app/solution.sparql` and runs Python with `-I`, so nothing else in `/app` is loaded; `attack-shadow-modules` confirms it in qualification. Every place the instructions allow (one file at a fixed path) is covered. The Scope bullet (line 32) now records both differences from upstream, the symlinked deliverable and the 1 GiB / 50,000-entry bounds against upstream's 10 GiB disk, labelled stricter with the reason.
3. No expected value leaks. `REFERENCE_RESULTS` is only in `hidden/cases.json`. `evaluation/` holds the adapter, two schemas and the two wheels, with no expected value. The baseline image has no `/tests`, no `/solution`, no Python and no SPARQL engine, and `grep -rl Dimakis /` over the image finds nothing. The pack allows no domain, so 4.7 does not apply.
4. Challenges. The single challenge is the hidden test graph (`hidden/university_graph_test.ttl`, byte-identical to upstream's `tests/university_graph_test.ttl`), which is exactly the input its own case needs.
5. Cases. One case, from upstream's single test graph; the three upstream tests map to it as "How the pack grades" says. `seed` is not used, and upstream draws no random values. Dropping upstream's discarded first run is recorded under "Cases", which now also notes its effect on the time limit.
6. Oracle. Expected values come only from `hidden/cases.json`; `oracle.py` holds upstream's `normalize_countries`, the `str(None)` mapping and the set comparison. It requires both variables, fails any non-string row value, compares sets as upstream does, ignores extra variables and claims, and its work is bounded by the observation schema (10,000 rows, 4 MiB). The adapter's reading matches upstream's `row.<name>` access: a missing label raises `AttributeError` upstream and fails here; an unbound value is `None` upstream and `"None"` in the Oracle; ASK, CONSTRUCT and DESCRIBE results fail in both; errors raised lazily during iteration are caught as `query-error`. The test graph has no relative IRIs, so parsing it from the challenge instead of a file changes nothing. No regression tests run by outcome.
7. Candidates. `reference.sh` is upstream `solve.sh` after `cd /app` (only the leading shebang and canary comments are dropped). Each mutant runs a real query through rdflib and aims at one place where the pack differs from upstream: the Oracle's `normalize_countries` copy, the adapter's row deduplication, the adapter's `str()` of terms, the Python 3.12 versus 3.13 `datetime` path, and the variable report. All five get the same verdict from both graders. `attack-shadow-modules` targets the adapter's module path with the hidden rows, and `attack-hostile-output` targets the `invalid` escape (lone surrogate) and claim fields; both end `failed`. The wheel hashes match PyPI's published SHA-256 digests.
8. Divergences. `qualification.json` reports no problems; every SecureBench run records the digest above, `dirty: false`, and `rejudged: true`. The runs record two framework commits (`befd3e5`, `0513451`), but `git diff befd3e5 0513451` touches only `conversions/agents.tsv`, so the SecureBench code is the same. No candidate diverges, and "Divergences from native" says so correctly.
9. Inventory. There is no `sparql-university` row in `conversions/inventory.tsv` yet; the coordinator adds it on commit. No exclusion reason applies: the task is a file deliverable judged by running a query over local data, which the pack does without network or host actions.

Upstream assertions: `test_sparql_file_exists` becomes `unable`/`query-unreadable` (a directory at the path fails upstream's later `read_text()` and fails here at `open()`, so the verdicts agree). `assert DATA_PATH.exists()` checks the trusted test graph and has no candidate-dependent counterpart. `g.query` raising in `test_sparql_runs_without_error` becomes `query-error`. `result_set == reference_set` in `test_sparql_query_results` is the Oracle's comparison. None is dropped.

Findings of the first review, re-checked:
- Time limit label (line 34): fixed. The bullet is now labelled more lenient, explains that upstream's 900 s covers the install and two runs of the query while the pack gives one run the whole budget, and states the resulting window (roughly 450 to 900 seconds). The "Cases" bullet (line 33) points to it.
- Scope bounds (line 32): fixed. The bullet records the 1 GiB / 50,000-entry bounds against upstream's 10 GiB disk as a stricter difference, with the reason.

Findings:
- None.

Verdict: approved
