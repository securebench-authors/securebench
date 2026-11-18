# kv-store-grpc

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/kv-store-grpc

## How the pack grades

Upstream's verifier runs seven pytest tests in `tests/test_outputs.py` against the
agent's container, while the server the agent left running in the background is
still up. We map them to three artifact checks and one protocol check with a
single case:

| Upstream test | Check | What is compared |
|---|---|---|
| `test_proto_file_creation` | artifact `proto-file` | `/app/kv-store.proto` exists and contains the five strings upstream asserts (`hidden/cases.json`), by Python `in` |
| `test_protobuf_generation` | artifact `generated-files` | `/app/kv_store_pb2.py` and `/app/kv_store_pb2_grpc.py` exist (any status but `absent`, as `Path.exists` accepts any file type) |
| `test_server_file_creation` | artifact `server-file` | `/app/server.py` exists and contains `class Server` |
| `test_grpc_tools_installation` | protocol `grpc-server` | `import grpc` raised nothing |
| `test_real_grpc_server_running` | protocol `grpc-server` | `connect_ex(("127.0.0.1", 5328))` with a 5 s timeout returned 0 |
| `test_grpc_protocol_handshake` | protocol `grpc-server` | `SetVal(key="handshake", value=999)` either raised a `grpc.RpcError` (upstream accepts this) or returned a response that has `val` and `val == 999`; imports, channel creation and `channel.close()` raised nothing |
| `test_grpc_server_functionality` | protocol `grpc-server` | `SetVal(test_key, 42)`, `GetVal(test_key)`, `SetVal(test_key, 100)`, `GetVal(test_key)` all returned, with `val` equal to 42, 42, 100, 100; setup and close raised nothing |

The protocol case runs in one Evaluation environment. `evaluation/adapter.py`
(stock Python) starts `/usr/local/bin/python3 server.py` in `/app` in its own
session, waits up to 60 s for 127.0.0.1:5328 to accept a TCP connection, then
runs `evaluation/driver.py` under the baseline's `/usr/local/bin/python3`, the
interpreter upstream's `pytest` runs on. The driver is upstream's test module
with each assertion replaced by a record of the values it compares. It runs the
four tests in upstream's order in one process, so imports and server state carry
over as they do in one pytest session (the handshake's key `handshake` is set
before the functionality test runs). It uses the candidate's `grpc` and its
generated `kv_store_pb2*` modules from `/app`, as upstream does. Each `val` is
recorded as an integer, a finite float or `other` (with its type name), and the
Oracle reproduces Python's `val == expected` for an integer `expected`. The
challenge, the expected values and the expected strings are in
`hidden/cases.json`. `oracle.py` contains only the comparisons.

## Fidelity changes

- **The conversion starts the server; the agent's running process is not graded**
  (more lenient and stricter). Instruction step 5 asks the agent to run
  `server.py` and leave it running, and upstream's tests talk to that process. No
  process survives capture, so the adapter starts `python3 server.py` from
  `/app` itself, the way the instructions and the upstream solution run it.
  More lenient: an agent that never started the server, or whose server died,
  can still pass. Stricter: the server must start with that command, without
  arguments, in a fresh environment, from files in the scope. A server that the
  agent ran some other way (another file, command-line arguments, state in
  `/root` or `/tmp`) passes upstream if it serves port 5328 correctly, but fails
  here. This is the closest observable form of "Run the server.py file".
- **Startup wait** (more lenient). Upstream connects once with a 5 s timeout,
  long after the agent started its server. The adapter first waits up to 60 s
  for the port to accept a connection, then runs upstream's single 5 s connect.
  A server that takes more than 60 s to start fails here; natively it would pass
  if the agent waited for it.
- **Scope** (stricter in edge cases). The roots are `/app` (the deliverables) and
  `/usr/local`, where a system-wide `pip install` for the baseline's Python 3.13
  puts packages and console scripts. Installs elsewhere are lost: a `pip install
  --user` into `/root/.local` (a protected path that no scope may cover; the
  instructions ask for a system-wide install) or packages reached through
  environment variables or files outside these roots. Debian's `python3-grpcio`
  is installed for the system Python 3.11 under `/usr/lib/python3`, which
  upstream's Python 3.13 does not see either. `**/__pycache__` is excluded in
  both roots: those are bytecode caches that Python rebuilds (equivalent).
  Symlinks inside each root are allowed, so a virtual environment in `/app`
  does not fail capture.
- **File checks read the captured files** (stricter or more lenient in edge cases).
  `kv-store.proto` and `server.py` must be regular UTF-8 files without a
  byte-order mark and at most 1 MiB. Upstream follows symlinks, reads any size,
  and keeps a leading BOM as a character. For the generated files, upstream's
  `Path.exists()` is false for a dangling symlink, but here any entry that is
  not `absent` counts as existing, so a dangling symlink passes (more lenient).
  None of these cases arises from following the instructions.
- **Test dependencies** (equivalent for every candidate that follows the
  instructions). `test.sh` installs pytest, requests, psutil and
  pytest-json-ctrf from the network before it runs the tests. The Evaluation has
  no network and the driver needs none of them, so nothing is installed. A
  candidate that broke `pip` fails natively at that step but is graded on the
  tests here.
- **Value comparison** (equivalent for protobuf messages). The Oracle reproduces
  `val == expected` for integers (booleans count as 0 and 1) and finite floats,
  so a proto that declares `double` fields passes as it does upstream
  (`mutant-double-val`). Any other type, such as a string, never compares equal.
  Upstream could compare equal with an exotic object that overrides `__eq__`, but
  protobuf scalar fields never return one.
- **Time limits** (stricter only for very slow servers). Upstream's RPCs have no
  deadline and run under the 900 s verifier timeout. Here the driver has 480 s
  and the case 600 s.
- **Order of checks** (equivalent). The three file tests run as artifact checks
  before the protocol case. Upstream runs all seven and fails on any failure,
  so the verdict is the same.
- Instructions, cases and allowed domains (`pypi.org` and
  `files.pythonhosted.org`, which the reference's `pip install` needs) are
  unchanged from upstream. The candidates make no drift repairs: `reference.sh`
  is `solve.sh` plus `cd /app`, which the upstream solution assumes.

## Candidates

- `mutant-double-val`: `double` fields; passes upstream through `999.0 == 999`.
  This tests the value record.
- `mutant-string-val`: values returned as strings; fails upstream. This tests
  that the record keeps the type.
- `mutant-no-overwrite`: `SetVal` never overwrites; the last `GetVal` returns 42.
- `mutant-byte-range`: `SetVal(999)` aborts with `INVALID_ARGUMENT`. This passes
  upstream's lenient handshake branch and tests that branch.
- `mutant-slow-start`: binds the port after 3 s. This tests the adapter's
  startup wait.
- `attack-forged-record`: a `sitecustomize.py` hijacks the driver and writes a
  record with the lenient handshake branch and no functionality calls.
- `attack-kill-adapter`: `server.py` writes a complete forged observation into
  the adapter's standard output, then kills the adapter.
- `attack-oom`: `server.py` forks and exhausts memory, trying to turn its
  failure into an infrastructure error.

## Divergences from native
None. In `qualification.json` every candidate gets the same verdict from both
graders: reference passes; null fails; `mutant-double-val`, `mutant-byte-range`
and `mutant-slow-start` pass; `mutant-no-overwrite` and `mutant-string-val`
fail. All three attacks fail natively (reward 0) and fail in SecureBench:
`attack-forged-record` with class `oracle`, `attack-kill-adapter` and
`attack-oom` with class `case_error`.

## Review

Reviewer: ab1d3ec64b00f5f6e, 2026-10-27

1. Instructions: `cmp task/instructions.md upstream/.../instruction.md` reports no
   difference.
2. Scope: roots `/app` (the deliverables) and `/usr/local` (where `pip install`
   for the baseline's `/usr/local/bin/python3.13` puts packages and scripts).
   The baseline's `/app` is empty. Every symlink under `/usr/local` in the
   baseline (`python -> python3`, `pip -> pip3`, `man -> share/man`, ...)
   stays inside the root. Upstream's tests live in `/tests`, outside the
   baseline and the scope; the driver is read-only under
   `/.securebench/evaluation`. `**/__pycache__` matches a `__pycache__`
   component at any depth (4.6) and is equivalent: Python never imports a
   module from `__pycache__` without its source. Convention-loaded files
   (`sitecustomize.py`, `.pth`) stay in scope, as they must for a normal pip
   install; the candidate controls the interpreter anyway, and every value the
   driver records is compared by the Oracle. The lost installs (`--user`,
   Debian's `python3-grpcio`) are recorded and match what upstream's
   `/usr/local` Python sees.
3. No expected value leaks: `public/` does not exist; `evaluation/` holds the
   adapter, driver and two schemas, with no expected values; the baseline image
   (`docker run` of the pinned digest) has an empty `/app`, no `/tests`, and only
   pip in site-packages. The expected values (999, 42, 42, 100, 100 and the five
   proto substrings) are upstream's public test literals and follow from the
   challenge itself, so a full forgery is hardcoding and out of scope. No
   limitation section is needed for `pypi.org`.
4. Challenges: the one challenge carries host, port, connect timeout and the
   RPC inputs upstream sends; no expected value.
5. Cases: one case, one pytest session as upstream runs it; the seed is not
   used, and upstream draws no random values.
6. Oracle: every expected value and substring comes from `hidden/cases.json`;
   `oracle.py` only compares. It checks every field (import, connect result,
   handshake stage, `has_val`, `val`, `channel_closed`, functionality
   `setup_error`, four steps without error, `channel_closed`), fails closed on
   missing or extra kinds, uses no regex, and its work is constant. I walked
   each upstream assertion: `test_proto_file_creation` (exists plus five `in`
   checks), `test_grpc_tools_installation` (import), `test_protobuf_generation`
   (two `exists`), `test_server_file_creation` (exists plus `class Server`),
   `test_real_grpc_server_running` (`connect_ex == 0`),
   `test_grpc_protocol_handshake` (setup outside the try, `RpcError` accepted,
   `hasattr` and `== 999` otherwise, any other exception fails, close in
   `finally`) and `test_grpc_server_functionality` (setup outside the try, four
   calls and values, close in `finally`) all map to a check, and the driver
   reproduces where upstream's try blocks start and end. Text parsing keeps `\r`
   where upstream translates it, which cannot change an `in` check on
   substrings without line breaks. The value record reproduces `==` for int,
   bool and finite float; NaN, out-of-range ints and other types fail, as they
   compare unequal upstream. Minor wording only: "protobuf scalar fields never
   return one" assumes protobuf, but `kv_store_pb2.py` is candidate code; an
   object with a custom `__eq__` can only reproduce public values, so this
   changes no honest verdict. No regression tests run by outcome.
7. Candidates: `reference.sh` is `solve.sh` plus `cd /app` (diffed). The five
   mutants run real gRPC servers and aim at the value record (double, string),
   the lenient `RpcError` branch (byte-range), the adapter's startup wait
   (slow-start) and state (no-overwrite); all agree with native. The attacks
   hijack the driver through `sitecustomize.py` with an incomplete record (aimed
   at this task's lenient branch), write into the adapter's stdout and kill it,
   and exhaust memory; all end `failed`.
8. Divergences: none. In `qualification.json` every candidate gets the same
   verdict from both graders, `problems` is empty, every run is admitted,
   rejudged and records pack digest
   `sha256:febd01f18fcdb2255315cf8a5d2fb48f45cdcae37cbd9ad12c6e55d38e7affd9`, the
   digest `validate` printed before and after qualification. The runs record two
   framework commits (47cc04f, fd0e8f8), both clean; they differ only in
   `conversions/agents.tsv`, so the SecureBench code is the same.
9. Inventory: no row yet in `conversions/inventory.tsv` (the coordinator adds it
   on commit). The task converts; no exclusion reason applies.

Findings:
- None that blocks. The comment on `__eq__` in "Value comparison" could say
  "candidate-written modules" instead of "protobuf scalar fields"; it affects
  no verdict.

Verdict: approved
