# hf-model-inference

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/hf-model-inference

## How the pack grades

The agent downloads a sentiment model to `/app/model_cache/sentiment_model`,
writes a Flask service and runs it in the background. Upstream's four tests
then talk to that running service and load the saved model. A running process
does not survive capture: every Evaluation environment starts from the
baseline with only the candidate's file changes. So the conversion asks the
agent for one more file, `/app/start.sh`, and the adapter starts the service
with it (see "Fidelity changes").

Two protocol checks, one case each, both built by `plan` from
`hidden/cases.json`:

| Check | Upstream test | What runs in the Evaluation | What the Oracle requires |
|---|---|---|---|
| `model-loads` | `test_model_downloaded` | `evaluation/load_model.py` on the baseline's own `/usr/local/bin/python3` (which has transformers): `os.path.exists` on the model path, then `AutoModelForSequenceClassification.from_pretrained` and, if that did not raise, `AutoTokenizer.from_pretrained` | the path exists; neither load raised; neither returned `None` |
| `api` | `test_flask_api_running` | `evaluation/api_adapter.py` (stock interpreter) runs `sh /app/start.sh` from `/app`, waits up to 300 s for port 5000, then sends `GET http://0.0.0.0:5000` | the GET completed (any status), as upstream only requires that it raises nothing |
| `api` | `test_sentiment_endpoint` | the same adapter, then `POST http://localhost:5000/sentiment` with each of upstream's six texts; it decodes each body as `requests`' `Response.json()` does and reports the type of `sentiment`, `confidence`, `confidence.positive` and `confidence.negative`, with the value of strings and floats | per text: status 200; the body is a JSON object; `sentiment` is a string; `confidence` is an object; both scores are JSON floats (infinities and NaN included, as Python parses them); a `"positive"` label has positive > negative and any other label negative > positive; the label equals upstream's expected label |
| `api` | `test_api_error_handling` | the same adapter, then `POST /sentiment` with `{"invalid_field": "This should cause an error"}`; it reports the status, the JSON type of the body, and `"error" in body` when the body is an object, array or string (the only types for which Python's `in` does not raise) | status 400; the body is JSON; `"error" in body` is true |

The expected labels, the statuses 200 and 400, the label strings, the texts
and the request bodies are literals from upstream's `tests/test_outputs.py`,
kept in `hidden/cases.json`. The adapters report; they hold no expected value.

The candidate's code runs in both checks: `load_model.py` runs on the
candidate-controlled `/usr/local` Python, and `start.sh` runs as a child of
the api adapter. A candidate can therefore forge either observation, but only
with values it could hardcode: every expected value of this task is public
in upstream's test file, so such a forgery is hardcoding, which SecureBench
does not claim to detect. `attack-adapter-stdout` shows that writing an
observation into the adapter's standard output from `start.sh` fails.

## Fidelity changes

- **Instructions: a start script and a grading note (stricter).**
  `instructions.md` is upstream's `instruction.md` byte for byte, followed by
  one added paragraph: the service is checked in a fresh copy of the container
  that keeps only file changes under `/app` and `/usr/local` (except the
  torch, nvidia, triton and cusparselt packages), without network and without
  the agent's processes, and the agent must write `/app/start.sh`, which the
  grader runs with `sh /app/start.sh` from `/app`. Upstream checks the process
  the agent left running; no conversion can, because capture keeps files, not
  processes. Without the added paragraph the agent could not know that its
  service must be restartable from files, so every faithful-looking solution
  that started the service from an inline command would fail with no
  instruction it broke. A native solution with no `/app/start.sh`, or whose
  service needs something the Evaluation lacks (the Hugging Face cache under
  `/root/.cache`, a package installed outside `/usr/local`, or network at
  start-up), passes upstream and fails here.
- **The grader starts the service (more lenient).** Upstream requires the
  service to be already up when its tests start. Here the adapter starts it
  and waits up to 300 seconds for port 5000 to accept connections. A
  `start.sh` that runs the service in the foreground also works, since the
  adapter does not wait for the script to exit. A candidate whose service was
  never running in its own container, but whose `start.sh` starts it, passes
  here and fails upstream; the added instructions make `start.sh` the
  deliverable.
- **Scope (stricter).** Two roots: `/app`, and `/usr/local`, where pip
  installs system-wide packages as the instructions allow. `/usr/local`
  excludes the baseline's `torch`, `nvidia`, `triton` and `cusparselt`
  packages (5 GB of its 5.4 GB), so that the root fits the 2 GiB scope bound;
  changes to them are dropped. Files written anywhere else, such as
  `/opt`, `/etc` or `/root`, do not reach the Evaluation. The baseline has no
  symlink under either root that points out of it (the ones in
  `/usr/local/bin` and `/usr/local/lib` point inside `/usr/local`).
- **Allowed domains (stricter).** Upstream gives the agent the whole
  internet; here only `huggingface.co` and `hf.co`, which the reference uses
  (the Hub API on `huggingface.co`; file transfers on `us.aws.cdn.hf.co` and
  `cas-server.xethub.hf.co`, seen in the reference run's proxy log). The
  instructions allow installing packages system-wide, but PyPI is not
  reachable, so an agent can use only the packages the baseline has
  (transformers 4.56.0, torch 2.7.1, flask 3.1.1 and their dependencies).
- **All requests sent (equivalent).** `test_sentiment_endpoint` stops at
  its first failing text; the api adapter sends all of upstream's requests,
  in upstream's order, to one service. Every assertion must still hold, so
  the verdict is the same.
- **One environment per check (more lenient).** Upstream runs its four tests
  in the agent's container one after another, so the pytest process loads
  the model while the agent's service holds its own copy in the same 2 GiB.
  Here `test_model_downloaded` runs in its own fresh environment, so the
  model loader and the service no longer share one container's memory. A
  service whose memory use leaves no room for a second copy of the model
  could fail upstream and pass here.
- **The model loader runs with `python3 -I` (equivalent).** It ignores
  `PYTHON*` environment variables and the user site directory. The baseline
  sets no such variable, and the user site is under `/root`, outside the
  scope.
- **HTTP client reimplemented (equivalent, except redirects).** The
  Evaluation cannot install `requests`, so the api adapter uses the stock
  interpreter's `http.client` and mirrors what `requests` 2.32.4 and urllib3
  2.5.0 do on these calls: the same request headers (`Accept-Encoding: gzip,
  deflate`, since neither brotli nor zstandard is installed), the same JSON
  body bytes, urllib3's gzip and deflate decoding (multi-member gzip, trailing
  garbage, raw deflate, encoding lists), requests' charset choice from
  `Content-Type`, and `Response.json()`'s UTF guessing. Like requests'
  `HTTPAdapter.build_response`, the adapter parses the `Content-Type` charset
  of every response, the `GET /` included, so a bare `charset` parameter
  fails that request in both. HTTP parsing is `http.client` in both, since
  urllib3 builds on it. We compared the two on 130 crafted responses (status
  codes, field types, NaN and infinities, duplicate keys, text/plain and
  UTF-16 bodies, BOMs, bogus, empty and bare charsets on the POSTs and the
  GET, every content encoding, chunked and short bodies, closed connections,
  garbage status lines, error bodies that are objects, arrays, strings, null
  and numbers), running upstream's assertions through real `requests` 2.32.4
  against the adapter's reports judged by `oracle.py`. 129 verdicts agree.
  The comparison script is not in the pack; it starts a socket server that
  replays each crafted response, then runs both clients against it in the
  baseline image with `requests` 2.32.4 installed. requests'
  `build_response` also stores the response's cookies with
  `http.cookiejar`, which the adapter does not repeat; `http.cookiejar`
  ignores malformed `Set-Cookie` headers rather than raising, so this
  changes no verdict.
  The one difference, and the two that remain by construction:
  - Redirects are not followed. A `/sentiment` answered with a redirect fails
    here and may pass upstream (stricter); a `GET /` answered with a redirect
    passes here whether or not the target answers (more lenient). The
    instructions define `POST /sentiment` as answering with JSON, so a
    redirect there does not meet them. We do not follow the redirect of the
    `GET /` either: upstream's test only asks that the service accept
    connections on 0.0.0.0:5000, which a service that answers with a
    redirect does; following it faithfully would mean reimplementing
    requests' redirect handling (Location resolution, method rewriting,
    cookies carried across hops, the 30-hop limit), and a target on another
    host could not be reached anyway, since the Evaluation has no network.
  - When a body declares no charset and is 3 bytes or shorter, or its UTF
    form cannot be guessed, `requests` decodes it with charset_normalizer's
    guess; the adapter uses UTF-8. A body of 3 bytes or fewer cannot hold a
    passing response (the shortest passing error body, `"error"`, is 7
    bytes); a body whose UTF form cannot be guessed has a NUL byte among its
    first four, which no JSON text in UTF-8 has, so it fails here and passes
    upstream only if charset_normalizer finds an encoding in which it is
    valid JSON.
  - A string field longer than 1,024 bytes is reported without its value.
    It cannot equal a label, so the verdict is the same.
- **Reference (equivalent).** `reference.sh` is upstream's `solve.sh`
  unchanged, after a `cd /app`, followed by the lines that write
  `/app/start.sh` with upstream's own start command
  (`nohup python app.py > app.log 2>&1 &`), which the added instructions
  require. No drift repair was needed.
- **Limits and timeouts (more lenient).** Upstream's 1 CPU, 2,048 MiB and
  10,240 MiB. Upstream's single 900-second verifier budget covers installing
  pytest and requests and all four tests. Here the api case alone gets 900
  seconds, and the model-loads case its own 600 seconds; the two cases run
  in parallel. In the reference run each case took about 12 seconds, so
  neither bound is near what a working solution needs. The model-loads case
  gets 600 rather than 900 seconds because it only imports transformers and
  loads the model once; it stays a wide margin for a slow worker. A solution
  that needs more than 900 seconds overall, but less than each of these
  bounds, passes here and fails upstream.

## Limitation: answer reachable through an allowed domain

The reference downloads the model from `huggingface.co`, so that domain is
allowed. The same domain publishes upstream's test file, byte for byte, with
all six texts and their expected labels:
`https://huggingface.co/datasets/harborframework/terminal-bench-2.0/blob/main/hf-model-inference/tests/test_outputs.py`
(we fetched it and compared it with upstream's 4,239-byte file: identical).
Mirrors exist in the datasets `zai-org/terminal-bench-2-verified` and
`introvoyz041/terminal-bench-2.0` on the same domain. An agent can read the
expected labels there, as it can in the public upstream repository; the
labels are also what the public model computes for those texts.

## Candidates

| Candidate | What it does | Expected |
|---|---|---|
| `reference` | upstream solution, plus `/app/start.sh` | pass both |
| `null` | nothing | fail both |
| `mutant-int-scores` | confidences as integer percentages | fail both (types) |
| `mutant-plain-gzip` | right answers, gzip-compressed `text/plain` without charset | pass both (decoding) |
| `mutant-error-string-loopback` | binds to 127.0.0.1; the 400 body is a bare JSON string containing "error" | pass both (`0.0.0.0` GET, membership) |
| `mutant-model-only` | saves the model but not the tokenizer | fail both (model loading) |
| `mutant-lazy-foreground` | loads the model on the first request; `start.sh` runs in the foreground | pass both (start and wait) |
| `attack-adapter-stdout` | `start.sh` writes a passing observation into the adapter's standard output through `/proc/$PPID/fd/1` | SecureBench fails |
| `attack-verdict-claims` | constant "positive" answers with fields claiming success; writes a native reward file | SecureBench fails |
| `attack-capture-fifo` | the reference, plus a named pipe in the model directory | SecureBench fails (capture) |

## Divergences from native

- `attack-capture-fifo`: native passes (reward 1.0), SecureBench fails with
  class `capture`. SecureBench is right by its rules: the candidate is the
  reference plus a named pipe in `/app/model_cache/sentiment_model`, and
  capture rejects special files so that a candidate cannot hand the grader
  something it cannot copy. Natively the pipe is harmless because the tests
  run in the agent's own container. The attack shows that such a candidate
  ends `failed`, never `invalid`.

Every other candidate gets the same verdict from both graders: the
reference passes; `null`, `mutant-int-scores`, `mutant-model-only`,
`attack-adapter-stdout` and `attack-verdict-claims` fail;
`mutant-plain-gzip`, `mutant-error-string-loopback` and
`mutant-lazy-foreground` pass.

## Review

Reviewer: conversion-reviewer (Opus 5.5), 2026-10-26 (second review, after the converter's fixes). Pack digest reviewed: sha256:49115df7cff0f59de759ce7f61a05e74b3f166611d8efe843d6bfd57e6926b16 (`securebench validate`: valid). Since the first review (digest sha256:6b681c94...), the only pack file that changed is `task/evaluation/api_adapter.py`, which gained three lines in `send`. The candidates are unchanged, and `CONVERSION.md` changed as described under the findings below.

1. Instructions. `cmp`: the first 1,264 bytes equal upstream's `instruction.md`, and the added "Grading note" paragraph is listed as a stricter fidelity change, with its reason. The note matches what the adapter does. Result: correct.
2. Scope. Roots `/app` (empty in the baseline) and `/usr/local`, minus `torch`, `nvidia`, `triton` and `cusparselt`. In the baseline, what remains of `/usr/local` has 16,538 entries and 360 MB, within the bounds. No symlink under either root resolves outside it, and no upstream test or convention-loaded spec file is in the scope. The model loader runs on the candidate's interpreter, as pytest does natively, and every expected value is public. Result: correct.
3. Expected values. The labels are only in `hidden/cases.json`; `evaluation/`, the challenges and the baseline hold none. The new section "## Limitation: answer reachable through an allowed domain" names `huggingface.co`, the exact URL of upstream's test file there and the two mirrors. The file size I saw in the first review (4.24 kB, against upstream's 4,239 bytes) agrees with the converter's byte comparison. Result: correct.
4. Challenges. Each holds only what its case sends or tests. Result: correct.
5. Cases. Two cases cover upstream's four tests, nothing is added, and the seed is unused. Result: correct.
6. Oracle. `oracle.py` and `cases.json` are unchanged and correct, as found in the first review. `send` in the adapter now calls `header_encoding` on every response, as requests' `HTTPAdapter.build_response` does. I ran the new `send` in the baseline image against a server that answers `GET /` with `Content-Type: text/html; charset`: it now raises `AttributeError`, so the root GET fails here as it does natively. On the POSTs, the exception now surfaces as a request error instead of `json: invalid`, and the Oracle fails both, so no verdict changes. Result: correct.
7. Candidates. Unchanged since the first review: the reference is upstream `solve.sh` plus `cd /app` and the `start.sh` lines, the five mutants run real code aimed at the reimplemented parts, and the three attacks are task-specific. In `qualification.json` every mutant gets the same verdict from both graders, and every attack ends `failed` (`case_error`, `oracle`, `capture`). Result: correct.
8. Divergences. `qualification.json` reports `problems: []`. Every SecureBench run records pack digest sha256:49115df7..., the digest I validated, with `dirty: false`. Native results are cached from earlier runs, which is right, because no candidate file changed. The one divergence, `attack-capture-fifo` (native 1.0, SecureBench `failed`/`capture`), is explained: an attack has to end `failed`, the named pipe is harmless only in the native in-place grading, and the result is `failed`, not `invalid`. The explanation holds. Result: correct.
9. Inventory. There is no row yet, which is the coordinator's job. No Section 11 reason holds. Result: no exclusion.

Upstream assertions: all four tests map to checks, as in the first review: `test_model_downloaded` to `model-loads`; `test_flask_api_running`, `test_sentiment_endpoint` and `test_api_error_handling` to the `api` check's root, sentiment and invalid_request reports. None is dropped.

Status of the first review's findings:
- Missing allowed-domain limitation: fixed (the new section).
- Bare `charset` on the GET: fixed in `api_adapter.py` lines 130-132, confirmed by the run above. The reason for the lenient half of the redirect difference is now given (upstream asks only that the service accept connections, and a redirect target on another host is unreachable without network). It holds.
- "One environment per check" mislabelled: fixed. It is split into "All requests sent (equivalent)" and "One environment per check (more lenient)", with the case that differs.
- "Limits" unlabelled: fixed. It is now "Limits and timeouts (more lenient)", with the reason for 600 seconds and the case that differs.

Findings:
- None.

Verdict: approved
