# Brief: convert one task

Every conversion agent receives this text verbatim, followed by one line naming the task: `Task: <source>/<task>`. Nothing else is added except answers to questions the agent asks. This brief is complete: a converter needs no other document of this repository to do its work. The review brief, `conversions/brief-review.md`, checks conversions against it.

---

You are converting one upstream benchmark task into a SecureBench task pack. The repository is `/home/user/securebench`. Your conversion will be reviewed by another agent and by human reviewers at a research venue, so every choice must be visible and justified in the files you write.

This brief is your complete instructions. Other documents in the repository describe how SecureBench itself is built; you do not need them.

## 1. How SecureBench grades a task

An **agent** (a model in its harness) works on the task in an **Agent environment**: a container started from the task's **baseline** image, with the task's instructions and public files mounted read-only. When it stops, SecureBench **captures** the **candidate**: the changes the agent made under the task's **scope** (a set of directories, minus excluded patterns). Nothing outside the scope survives.

The candidate is then graded by **checks**:

- An **artifact check** reads files or directory listings from the candidate directly, without running anything.
- A **protocol check** runs **cases**. For each case, SecureBench starts a fresh **Evaluation environment** from the baseline, **replays** the candidate on top of it, and runs the check's **adapter**. The adapter receives the case's **challenge** on standard input, exercises the candidate's code, and writes one JSON **observation** to standard output. Evaluation environments have no network.

A task can use a single check type or both, depending on its needs.

The **Oracle**, `hidden/oracle.py`, runs on the host. Its `plan` fixes every case before evaluation starts: a challenge, which goes to the Evaluation, and a **context**, which stays on the host and usually holds the expected values. Its `judge` compares each piece of evidence with its context and says pass or fail. Artifact checks run first; if they pass, all cases of all protocol checks run in parallel, so no case may rely on another's order. An attempt passes only if every artifact check and every case passes, and the first failed case cancels the rest.

What the candidate controls, it can forge. The candidate's code runs inside every Evaluation environment, so it can take over the adapter process, rewrite files the adapter reads, or print anything. Only the Oracle decides correctness, and it trusts nothing from an Evaluation beyond what it can check against its own expected values.

Every attempt ends `passed`, `failed` or `invalid`:

| Where an error occurs                                                                                                                                                                    | Result                               |
|---|---|
| Capture (size bounds, special files, symlinks that escape the scope, unreadable files)                                                                                                   | `failed`, class `capture`            |
| The check's shared setup                                                                                                                                                                 | `failed`, class `setup`              |
| Inside an Evaluation: adapter crash, timeout, memory kill, malformed or out-of-schema response, unreadable Output Artifact, or the adapter reporting it could not exercise the candidate | `failed`, class `case_error`         |
| The Oracle's judgment                                                                                                                                                                    | `failed`, class `oracle`             |
| On the host (container runtime, host resources, a framework bug)                                                                                                                         | retried; `invalid` if it still fails |

`invalid` means the attempt does not count. A wrong candidate must always end `failed`, never `invalid`: a grader that lets a candidate turn its failure into an infrastructure error has an escape hatch.

## 2. Read first

1. This brief, in full.
2. The whole upstream task under `conversions/upstream/<source>/` (for DeepSWE, `tasks/<task>`): `instruction.md`, `task.toml`, `environment/`, `tests/` and `solution/`. Read every test that checks what the task asks for. Regression tests that run by outcome (Section 5, "Never trust a test report") need reading only as far as choosing how to run them.

Other conversions in `conversions/` follow earlier versions of this brief and may contradict it. Do not use them as examples.

## 3. Where you may write

Only inside `conversions/<source>/<task>/`. Do not edit anything else in the repository, do not commit, and do not change `conversions/inventory.tsv`. Run formatters and other tools that write files only on your own folder: other agents' conversions sit beside it.  If something outside your folder prevents a correct conversion or if a rule in this brief cannot be met, do not work around it. Stop and describe it in your report; the coordinator decides.

Your folder:

```
conversions/<source>/<task>/
  task/              the pack (Section 4); its id is the upstream task name
  candidates/        reference.sh, null.sh, mutant-*.sh, attack-*.sh, and files they use (Section 6)
  CONVERSION.md      the fidelity record (Section 7)
  qualification.json written by `campaign.py qualify` (Section 8)
```

## 4. The pack

A task pack is one directory. Its layout fixes who can see each file, and one TOML file declares everything else. `uv run securebench validate <pack>` checks the pack against this section and prints the pack digest after `valid`. The rules about the baseline image (scope roots and `repository` in 4.2, `/.securebench` in 4.8) need Docker: `validate --live` checks them too, and every run checks them before the agent starts.

### 4.1 Layout

```
task/
  task.toml           the task specification (4.2)
  instructions.md     public: given to the agent verbatim
  public/             public assets
  evaluation/         evaluation inputs: adapters, drivers, schemas
  hidden/             hidden resources; hidden/oracle.py is the Oracle
```

- `task.toml`, `instructions.md` and `hidden/oracle.py` are required. `public/` and `evaluation/` are optional. No other entries may exist at the top level.
- No symlinks anywhere in the pack; every entry is a regular file or a directory.
- File names are valid UTF-8, and paths follow the rules in 4.6.
- `task.toml` is at most 256 KiB, `instructions.md` at most 1 MiB, and the whole pack at most 1 GiB and 100,000 entries.

Where each part is visible:

| Part                                                         | Agent environment                            | Evaluation environment                  | Host                         |
|---|---|---|---|
| `instructions.md`                                            | read-only at `/.securebench/instructions.md` | no                                      | yes                          |
| `public/<source>`                                            | read-only at the declared `target`           | no                                      | yes                          |
| `evaluation/`                                                | no                                           | read-only at `/.securebench/evaluation` | yes                          |
| `hidden/`                                                    | no                                           | no                                      | yes, through the Oracle only |

A task that needs a public file during evaluation also places a copy in `evaluation/`. Remember that the agent can read the baseline image and everything in `public/`, and that the candidate's code can read everything in `evaluation/` while a case runs. Assume the agent knows `evaluation/` and `hidden/oracle.py` as well: only the data files in `hidden/` and the run seed are secret, so nothing in `evaluation/` may decide an expected value (Section 5, "Test inputs").

### 4.2 `task.toml`

TOML 1.0. Every table has an exact key set: unknown keys and missing required keys are rejected. Integers must be TOML integers (a boolean is never an integer) and are checked against the ranges given here. A "name" is 1 to 64 bytes of lowercase ASCII letters, digits and `-`, starting with a letter or digit.

Top level:

| Key                | Type            | Rule                                                  |
|---|---|---|
| `id`               | string          | name; the upstream task name                          |
| `source_benchmark` | string          | name; the source name from `conversions/sources.toml` |
| `baseline`         | table           | below                                                 |
| `agent`            | table           | below                                                 |
| `scope`            | table           | below                                                 |
| `public_assets`    | array of tables | optional                                              |
| `artifact_checks`  | array of tables | optional                                              |
| `protocol_checks`  | array of tables | optional                                              |

A task declares at least one check. Check identifiers are names, unique across both kinds.

`[baseline]`:

| Key          | Type   | Rule                                                                                                       |
|---|---|---|
| `image`      | string | `<repository>@sha256:<64 lowercase hex>`, or `sha256:<64 lowercase hex>` for a local image ID              |
| `repository` | table  | optional: `path` (absolute directory inside a scope root) and `commit` (40 or 64 lowercase hex characters) |

With `repository`, SecureBench confirms before the agent starts that `<path>/.git` is a real directory, `HEAD` equals `commit`, and the working tree is clean, untracked files included.

`[agent]`:

| Key               | Type             | Rule                                                                          |
|---|---|---|
| `workdir`         | string           | absolute path inside a scope root; the working directory of every environment |
| `allowed_domains` | array of strings | at most 1,024; may be empty (4.7)                                             |

`[scope]`:

| Key           | Type            | Rule                                           |
|---|---|---|
| `max_entries` | integer         | 1 to 100,000; entries walked across all roots  |
| `max_bytes`   | integer         | 1 to 2 GiB; file bytes walked across all roots |
| `roots`       | array of tables | 1 to 16 roots                                  |

Each `[[scope.roots]]`:

| Key               | Type             | Rule                                                                                   |
|---|---|---|
| `path`            | string           | absolute; not `/`; a real directory in the baseline                                    |
| `exclude`         | array of strings | optional; patterns (4.6); at most 256                                                  |
| `git_directories` | array of strings | optional; relative paths ending in `.git`, captured as plain files instead of excluded |
| `symlinks`        | boolean          | whether the candidate may create or change internal symlinks                           |
| `max_entries`     | integer          | 1 to the scope's `max_entries`                                                         |
| `max_bytes`       | integer          | 1 to the scope's `max_bytes`                                                           |

Roots may not overlap one another, and no root may equal, contain or sit inside a protected path (4.8).

`[[public_assets]]`:

| Key      | Type   | Rule                                                 |
|---|---|---|
| `source` | string | relative path of a file or directory under `public/` |
| `target` | string | absolute mount point in the Agent environment        |

A target may not equal, contain or sit inside a scope root or a protected path, and no two targets may overlap.

`[[artifact_checks]]` read the candidate without starting an environment:

| Key        | Type            | Rule                                                                          |
|---|---|---|
| `id`       | string          | name                                                                          |
| `files`    | array of tables | optional; each `path`, `parser` (`text` or `json`), `max_bytes` (1 to 16 MiB) |
| `listings` | array of tables | optional; each `path`, `max_entries` (1 to 100,000)                           |

At least one file or listing. Each `path` is absolute, inside a scope root and not excluded. A missing file, or one that is not a regular file, is a normal state passed to the Oracle.

`[[protocol_checks]]`:

| Key                     | Type             | Rule                                                                               |
|---|---|---|
| `id`                    | string           | name                                                                               |
| `command`               | array of strings | 1 to 64 elements, each 1 to 4,096 bytes without NUL; the first is an absolute path |
| `challenge_schema`      | string           | relative path of a schema under `evaluation/`                                      |
| `observation_schema`    | string           | relative path of a schema under `evaluation/`                                      |
| `max_cases`             | integer          | 1 to 1,000                                                                         |
| `timeout_seconds`       | integer          | 1 to 3,600; per case                                                               |
| `max_challenge_bytes`   | integer          | 1 to 1 MiB                                                                         |
| `max_observation_bytes` | integer          | 1 to 4 MiB; bounds the whole response                                              |
| `setup_command`         | array of strings | optional; same rules as `command`                                                  |
| `setup_timeout_seconds` | integer          | required with `setup_command`, 1 to 7,200                                          |
| `output_artifacts`      | array of tables  | optional; each `path`, `parser`, `max_bytes`                                       |

Output Artifact paths follow the artifact check rules, except that they need not lie inside a scope root. They may not sit inside a `.git` directory or a protected path. One check has at most 64 Output Artifacts, totalling at most 16 MiB.

### 4.3 Adapter protocol

For each case, SecureBench starts a fresh Evaluation environment and runs `command` in `agent.workdir`. The challenge arrives on standard input as canonical JSON. The adapter writes exactly one JSON value to standard output:

```json
{"observation": <value matching the observation schema>}
{"unable": {"code": "<1 to 128 bytes>", "message": "<0 to 4,096 bytes>"}}
```

`unable` reports that the adapter could not exercise the candidate (for example, the candidate's code does not build). It is kept as a diagnostic, and the case fails with class `case_error`. Standard error is discarded. A response that is too large, not valid UTF-8, not strict JSON (one value, no duplicate keys, no NaN or infinities), or not one of these envelopes fails the case with class `case_error`, as does a non-zero exit, a timeout or a memory kill.

Every Evaluation environment has the stock Python image mounted read-only at `/.securebench/python`, so an adapter can be standard-library Python even when the baseline has no interpreter. It is not mounted in the Agent environment, so a solution cannot rely on it. Start it through the stock image's own loader:

```toml
command = [
  "/.securebench/python/lib64/ld-linux-x86-64.so.2",
  "--library-path",
  "/.securebench/python/usr/local/lib:/.securebench/python/lib/x86_64-linux-gnu:/.securebench/python/usr/lib/x86_64-linux-gnu",
  "/.securebench/python/usr/local/bin/python3", "-I", "/.securebench/evaluation/adapter.py",
]
```

An adapter started this way that runs another Python process repeats this invocation, because `sys.executable` alone does not find the stock libraries. Using the stock image is optional; an adapter may use the baseline's own tools instead.

`setup_command`, when present, runs once on the replayed candidate, with the same mounts and no standard input, for work that needs no challenge, such as a build. Exit status 0 is success; anything else fails the attempt with class `setup`. Its filesystem is then snapshotted, and every case starts from its own copy. The snapshot is candidate-controlled, like everything else in the Evaluation.

Cases follow these rules:

- One challenge in, one observation out. A case may contain several operations, but it receives all its inputs at once; there are no interactive cases.
- Operations inside one case share state. Anything that must be independent goes into a separate case.
- The case list is fixed before evaluation starts and never depends on earlier evidence.
- Each case is judged alone. A property that spans several fresh runs (such as identical output across runs) must fit inside one case.
- A challenge contains only what its case needs, and leaks no other hidden material.

### 4.4 Schemas

Challenge and observation schemas are strict JSON files of at most 64 KiB, depth at most 16, and at most 1,024 schema nodes. A schema node is an object with an exact key set for its type:

| `type` | Other keys |
|---|---|
| `"object"` | `properties` (name to schema node, at most 256), optional `optional` (property names that may be absent); unknown fields are always rejected |
| `"array"` | `items` (schema node), `max_items` (0 to 100,000), optional `min_items` |
| `"string"` | `max_bytes` (0 to 4 MiB, UTF-8 bytes), optional `enum` (1 to 256 distinct strings) |
| `"integer"` | `minimum`, `maximum` (both required, at most 2^63 in magnitude) |
| `"number"` | `minimum`, `maximum` (both required, finite) |
| `"boolean"` | none |
| `"null"` | none |

There are no patterns or character sets. Booleans never satisfy `integer` or `number`; an integer satisfies `number`.

Artifact checks parse files only as UTF-8 text or strict JSON. Any other format (CSV, binary files, Git repositories) is read by a protocol check: the adapter parses it inside the Evaluation and returns a typed observation. There are no task-specific parsers.

Declare structured values as typed fields rather than encoding them in text: a list of file names is an array of bounded strings, a count is an integer. When output is text by nature, such as the lines a program prints, return each line as a bounded string. Whether a string has the right format is a correctness question, so the Oracle checks it.

### 4.5 The Oracle's interface

`hidden/oracle.py` defines two top-level functions:

```python
def plan(resources: HiddenResources, seed: int) -> Plan: ...
def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment: ...
```

The types come from `securebench.core.evidence` and `securebench.core.jsondata`:

- `HiddenResources` has `read(path) -> bytes` and `read_json(path) -> JsonValue` for files under `hidden/`. Only `plan` receives it.
- `Plan(artifact_contexts, cases)`: one context per artifact check id, and one non-empty tuple of `Case(challenge, context)` per protocol check id.
- `Judgment(passed, diagnostic)`: the verdict on one artifact check or one case, with a JSON diagnostic.
- `ArtifactEvidence(check_id, files, listings)`. Each `FileEvidence` has `path`, `status` (`present`, `absent`, `not_regular`, `too_large`, `unparsable`), `value` (a `Text(text, lines)` or a JSON value, set only when present), `size`, `sha256` and `reason`. Each `ListingEvidence` has `path`, `status` (`present`, `absent`, `not_directory`, `too_many`) and `entries`, each with `path` (relative), `kind` (`file`, `dir`, `symlink`), `size`, `sha256`, `executable` and `target`.
- `CaseEvidence(check_id, case_index, challenge_digest, facts, outcome, output_artifacts)`. `facts` holds how the case ended (`returned`, `timed_out`, `memory_killed`, `output_exceeded`, `crashed`), the exit status and the duration. The duration is for diagnostics only, never an acceptance criterion. `outcome` is `Observed(value)`, `Unable(code, message)` or `Malformed(reason)`. `output_artifacts` are `FileEvidence`.

`seed` is the run seed, an operator setting. Most Oracles do not use it. Use it only when upstream's tests draw random values themselves: draw them from `Random(seed)`, never from another source, so that a rerun with the same seed repeats the same cases. Never add randomness that upstream's tests do not have.

`securebench validate` rejects an Oracle that breaks these static rules:

- Imports only from: `__future__`, `abc`, `base64`, `binascii`, `bisect`, `cmath`, `collections`, `collections.abc`, `copy`, `dataclasses`, `decimal`, `enum`, `fractions`, `functools`, `hashlib`, `heapq`, `itertools`, `math`, `operator`, `statistics`, `string`, `struct`, `typing`, `unicodedata`, `zlib`, `securebench.core.errors`, `securebench.core.evidence` and `securebench.core.jsondata`; and `random` only as `from random import Random`. No relative imports and no `import *`.
- Never names `__import__`, `breakpoint`, `compile`, `delattr`, `eval`, `exec`, `exit`, `getattr`, `globals`, `help`, `id`, `input`, `locals`, `open`, `quit`, `setattr` or `vars`, any other name starting with `__` except `__name__`, or any attribute starting with `__`.
- No `global` or `nonlocal`. At most 1 MiB of source.

A minimal task: the agent sums the integers in a public file and writes the sum to an answer file. Its `task.toml`:

```toml
id = "f1-answer-file"
source_benchmark = "securebench-fixtures"

[baseline]
image = "python@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d"

[agent]
workdir = "/srv"
allowed_domains = []

[scope]
max_entries = 64
max_bytes = 65536

[[scope.roots]]
path = "/srv"
symlinks = false
max_entries = 64
max_bytes = 65536

[[public_assets]]
source = "numbers.txt"
target = "/data/numbers.txt"

[[artifact_checks]]
id = "answer"

[[artifact_checks.files]]
path = "/srv/answer.json"
parser = "json"
max_bytes = 4096
```

Its Oracle, with the expected sum in `hidden/expected.json`:

```python
from securebench.core.evidence import ArtifactEvidence, CaseEvidence, FileStatus, HiddenResources, Judgment, Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    return Plan(artifact_contexts={"answer": resources.read_json("expected.json")}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"answer is {found.status.value}"})
    if found.value != context:
        return Judgment(False, {"reason": "wrong answer"})
    return Judgment(True, None)
```

### 4.6 Paths and exclude patterns

Every path in `task.toml` is canonical: an absolute path starts with exactly one `/`; no component is empty, `.` or `..`; there is no trailing `/`, backslash or NUL; it is valid UTF-8, at most 4,096 bytes and 128 components. A relative path follows the same rules without the leading `/`. Validation never normalizes a path; it rejects one that is not canonical.

Comparisons that protect, exclude or detect collisions apply Unicode NFC normalization and case folding to each component, so `Tests` and `tests` collide. Containment that grants access ("this path is inside root R") compares exact components.

An exclude pattern is a relative path matched against a path relative to its scope root, one component at a time:

- A component `**` matches zero or more whole components.
- Inside any other component, `*` matches zero or more characters other than `/`.
- No other character is special; `?`, `[`, `]` and `\` are rejected.

A pattern that matches a path excludes that path and everything below it, so `tests` and `tests/*` both exclude every file inside `tests`, at any depth. To exclude files by name wherever they are, start the pattern with `**`: `**/conftest.py`, `**/*_test.go`. Matching uses folding, so `tests` also excludes `Tests`. Every root implicitly excludes `**/.git`, except the paths listed in its `git_directories`.

Changes to excluded paths are dropped from the candidate without failing it: writes, deletes, type changes and new files below them. Agents routinely add or fix tests, and native graders do not penalize that, so the candidate loses those edits instead of failing.

Capture never follows symlinks. When the baseline has a symlink inside a scope root that points out of it (for example `/app/data -> /data`), an agent writing through it writes outside the scope, and the change is not captured. Look for such symlinks in the baseline when you choose the scope.

Only content, file type and the executable bit survive replay. Ownership, other permission bits and timestamps do not.

### 4.7 Allowed domains

Each entry is lowercase ASCII, with at most one trailing dot, which is removed. Labels are 1 to 63 letters, digits and `-`, not starting or ending with `-`. A name has at least two labels and at most 253 characters. No scheme, port, path, wildcard, IP literal, `localhost` or `*.localhost`, and no duplicates. An entry allows itself and its subdomains, on a dot boundary.

An allowed domain is fully usable by the agent. It must not offer a channel between runs. When a domain the reference needs also makes the answer reachable, for example because upstream's hidden test data is published there, keep the domain and record it in `CONVERSION.md` under "## Limitation: answer reachable through an allowed domain", naming the domain and where on it the answer is.

### 4.8 Protected paths

No scope root, public asset target or Output Artifact path may equal, contain or sit inside any of these:

```
/.securebench /proc /sys /dev /run /var/run /tmp /var/tmp /var/lib/docker /var/lib/containerd /run/containerd /root /etc/passwd /etc/group /etc/shadow /etc/gshadow /etc/subuid /etc/subgid /etc/sudoers /etc/sudoers.d /etc/ssh /etc/apt /etc/dnf /etc/yum.repos.d /etc/pacman.conf /etc/pacman.d /var/lib/apt /var/lib/dpkg /var/lib/rpm /var/lib/pacman /var/cache/apt /var/cache/dnf /var/cache/yum
```

The baseline must not contain `/.securebench`.

## 5. How to convert

- **Baseline.** The upstream `docker_image`, pinned by the digest `docker pull` reports.
- **Instructions.** `instructions.md` is upstream `instruction.md` byte for byte. The agent receives it verbatim and nothing else from SecureBench, and never sees the scope, so the instructions must define every deliverable. A requirement the conversion needs beyond them would have to be written into `instructions.md`, where it is a fidelity change.
- **Specification.** The upstream tests are the specification. Every assertion they make becomes part of a check, or is listed in `CONVERSION.md` as a fidelity change with its reason.
- **Never trust a test report, with one exception.** A pass or fail report from a test runner is not evidence of what the candidate computes, because the candidate's code runs in the runner's process and can rewrite the report: a repository-root `conftest.py` that rewrote every pytest outcome to "passed" fooled the native grader of several DeepSWE tasks, and code under test can do the same from inside its own modules. Adapters call the candidate's code and return the values it produced, and the Oracle compares them. This holds for every test that checks what the task asks for (for DeepSWE, the fail-to-pass tests): transliterate it mechanically, replacing each assertion with a record of the values it compares, and keep the expected values and the test's inputs in `hidden/` ("Test inputs" below).
  The one exception is the tests upstream runs only to check that existing behavior still works (for DeepSWE, the pass-to-pass tests). Run them with upstream's own test runner on test files restored from the baseline, never the candidate's copies, and record each test's outcome with a small plugin from `evaluation/` or the runner's machine-readable output. The Oracle requires every listed test to pass. Every file the runner loads by convention (`conftest.py`, plugins, configuration) is excluded from the scope or restored from the baseline. Candidate code can still forge these outcomes from inside the runner, as it can natively, so a forger passes these tests but not the feature tests; record this in `CONVERSION.md` under "## Limitation: regression test outcomes", with the number of tests it covers.
- **Evaluation has no network.** Anything the native verifier installs at grading time is unavailable. Write adapters in standard-library Python on the stock interpreter (4.3), or use tools the baseline already has outside the scope.
- **Reimplemented native tools.** When an adapter or the Oracle replaces a native tool or library call (a decoder, a numeric loader, a float32 summation), verdicts can differ near the acceptance thresholds. Match the native one. Test your version against it on inputs concentrated near those thresholds, and record the comparison and any difference you cannot avoid in `CONVERSION.md`. Reimplement, in readable code, only the part of the library the upstream test reaches for the deliverable the instructions ask for; never vendor a compiled library into the pack. Record what the reimplementation leaves out as a fidelity change.
- **Adapters report; the Oracle judges.** An adapter turns a challenge into calls on the candidate's code and returns the values that code produced. It contains no expected value and decides nothing. It reports only what the candidate did and never fills in what it should have done: an adapter that records a "cleaned up" event itself whenever its socket closes decides the task's requirement in trusted code, and a candidate that skips the cleanup scores the same as a correct one. Assume the candidate can take over the adapter process. For a repository task, the adapter typically builds and runs a small driver in `evaluation/` against the candidate's code. The driver runs the test its challenge carries and returns the values the upstream tests assert on.
- **Expected values.** Every value the Oracle compares evidence with lives in a data file under `hidden/`, together with its case's challenge (for example `hidden/cases.json`): a literal from an upstream test, or a value obtained by running the upstream reference on an upstream input. `plan` reads the data files and builds the cases; `judge` compares. `oracle.py` holds only judging logic: how to compare (equality, a tolerance, a normalization, a threshold upstream's test uses, a property such as "sorted" that needs no reference answer), and no expected value or code that computes one, so that the Oracle's code can be read, audited or shown without revealing any answer. The only exception is an upstream test that draws random inputs at run time and computes their expected results with a reference: then `plan` draws the inputs from `Random(seed)` and computes the results as upstream's test does, and `CONVERSION.md` says so. Never compute an expected value from a value the candidate reports (a forged environment parameter plus self-consistent results would then pass). Never take one from files in the Evaluation filesystem or inside the scope, even when they ship with the baseline image, because replay applies the candidate's changes on top of that image: a native grader that compared answers against an agent-writable reference passed garbage-plus-matching-reference. When you derive expected values by running the upstream reference, check them against what the upstream tests assert, and keep the script you derived them with in `hidden/`, or describe the derivation in `CONVERSION.md`, so a reviewer can redo it.
- **Test inputs.** Whatever decides an expected value lives in `hidden/` and reaches the Evaluation only in its case's challenge. Depending on the test, that is its literal values, the classes, objects and helpers the test file defines, or the sequence of calls it makes. An agent that knows `evaluation/` and the task's instructions must not be able to work out any expected value. In `cattrs`, a driver that calls `partial_structure({"a": 1, "b": 123}, Defaulted)` tells anyone who knows the library that `r.value.a` is `1`, even when `1` itself is in `hidden/`. `evaluation/` holds only what decides no expected value: the runner, the recorder, fixed building blocks that the challenge chooses from, the protections against tampering, and the schemas. Use one of these forms:
  - **Send the test source (the default).** The transliterated tests live in `hidden/`, `plan` puts each case's test code in its challenge, and the driver runs the code it receives. `evaluation/` then holds no test bodies. Prefer this form whenever the driver can run code it is sent, as Python and JavaScript or TypeScript drivers can.
  - **Send values or steps.** Where running code from the challenge is impractical, such as a compiled driver the setup builds before any case runs, the driver may keep each test's structure and take its values or steps from the challenge. Then show in `CONVERSION.md`, test by test, that nothing left in the driver decides an expected value. A class default such as `field(init=False, default=42)` decides `r.value.c == 42`, so it goes in the challenge too.
  - **Stand-ins for compile-only test files.** When the candidate's code must compile against upstream's test file, as a Go package must, put a stand-in in `evaluation/` with the same declarations and no test bodies, never the test file itself.

  The rule does not cover inputs the agent works on directly (task files the instructions name, the repository, data in the baseline image), or regression tests run by outcome, which use the baseline's own test files.
- **Cases.** Keep upstream's cases, no more and no fewer.
- **Oracle.** `judge` is deterministic and free of side effects: no network, files or processes. It never evaluates, deserializes, executes, or uses as a path or command any value taken from the evidence; a native grader that opened a file name read from the candidate's output exposed path traversal. It never applies regular expressions to evidence; a format check is a simple hand-written check on the bounded string. Computation is allowed. In addition:
  - Check every required field. An observation with only a status field, or one that claims success while an embedded field says the run failed, must fail. Prefer schemas without embedded status strings, so that `unable` is the adapter's only failure channel.
  - Count the way upstream's test counts. When upstream's test counts distinct correct items, deduplicate, so that a candidate cannot repeat one correct item to reach a threshold.
  - Bound every computation over candidate data. The Oracle runs on the host without a sandbox, so any decoder or simulation over candidate bytes needs explicit size, iteration and output bounds, and ends in a failed judgment, never a crash. Its process has a 4 GiB memory limit as a last resort; a correct candidate must stay far below it.
  - Ignore the candidate's claims. Extra fields or text that claim a verdict mean nothing: a correct answer with a claim still passes, and a wrong one still fails.
  - Judge each case alone. SecureBench combines the judgments; the Oracle has no verdict of its own.
  - Fail closed on anything unexpected.
- **Scope.** Cover every solution the instructions allow. Exclude test files wherever the language keeps them, so a candidate cannot rewrite the specification: not only `tests/`, but also Go's `_test.go` files beside the sources, and convention-loaded files such as `conftest.py` and package initializers that run on import.
- **Allowed domains.** The least the reference solution needs.
- **Limits.** `campaign.py` runs both graders with the upstream task's CPU, memory and disk. Do not work around them.

## 6. Candidates

Each candidate is one POSIX `sh` script in `candidates/`. The same script runs in both graders: SecureBench runs it with the `scripted:` harness, and `campaign.py` runs it natively as Harbor's `solution/solve.sh` under Pier's oracle agent. So a script:

- changes to its working directory explicitly;
- finds sibling files through `"$(dirname "$0")"` (both graders copy the whole `candidates/` folder beside it);
- for DeepSWE, commits its work, because the native harness grades only commits since the base commit.

| Kind                                                         | What it is                                                                                                                                        | SecureBench must say | Native    |
|---|---|---|---|
| `reference.sh`                                               | The upstream solution unchanged, plus only what both graders need (`cd`, finding sibling files, for DeepSWE the commit) and drift repairs (below) | `passed`             | must pass |
| `null.sh`                                                    | Changes nothing                                                                                                                                   | `failed`             | must fail |
| `mutant-*.sh`, one to five                                   | A plausible wrong implementation that really runs, aimed where the conversion's check is least like upstream's assertion (below)                  | the same as native   | recorded  |
| `attack-*.sh`, one to three, at least one aimed at this task | A candidate that tampers with grading instead of solving the task                                                                                 | `failed`             | recorded  |

`failed` means status `failed`, never `invalid`.

A mutant must run real code. A mutant that only edits an observation proves that the Oracle rejects a value, not that a broken implementation produces it.

**Mutants test fidelity.** A mutant shows that SecureBench and the native harness reach the same verdict on the same wrong code. If they differ, the conversion added or dropped a check: fix the pack, not the mutant. A mutant that passes both graders is fine; never add a case or an assertion to make it fail. Aim mutants where the conversion's check is least like upstream's assertion: a reimplemented native tool, a normalization, a tolerance, or a value the adapter extracts or converts before the Oracle compares it. Write at least one for each such place.

**At most five mutants and three attacks.** Every candidate adds runs to every qualification, and `qualify` refuses more. Keep the mutants aimed where the conversion's check is least like upstream's assertion, and the attacks on the routes most specific to this task. A candidate whose code forges the records or reports SecureBench reads, filling them only with values it could hardcode (upstream's public expected values), is outside SecureBench's scope, as hardcoding is: it is not an attack and needs no recorded limitation. It is an attack when the forgery passes a check whose expected value is hidden, or makes the Oracle accept a value it never sees.

**Drift repair.** When the environment has drifted since the upstream image was built, `reference.sh` may add the smallest commands that repair it, such as `apt-get update` before the first `apt install` when the image's package lists point at versions the mirror no longer serves. A repair changes nothing about how the task is solved. If the unmodified reference fails natively, find out why before you repair anything, and keep the evidence. List each repair under "Fidelity changes" in `CONVERSION.md`, with the native evidence that the unrepaired reference fails.

## 7. `CONVERSION.md`

```markdown
# <task>

Upstream: <source>@<commit>/<path>

## Fidelity changes
One bullet per difference from upstream: instructions, scope, domains, cases,
reimplementations of native tools. Each is labelled stricter, more lenient or
equivalent, with the reason.

## Divergences from native
One bullet per candidate whose native and SecureBench verdicts differ,
explaining which is right.
```

A conversion that runs regression tests by outcome (Section 5, "Never trust a test report") adds the section "## Limitation: regression test outcomes". A conversion whose allowed domains make the answer reachable (Section 4.7) adds the section "## Limitation: answer reachable through an allowed domain". You may add sections that help a reviewer, such as how the pack grades and how the upstream tests map to checks. The reviewer appends a `## Review` section at the end; never edit it.

## 8. Qualification

```bash
python3 conversions/campaign.py qualify conversions/<source>/<task>
```

runs every candidate once through both graders, SecureBench and the native harness (Pier), runs `securebench rejudge` on every SecureBench run, and writes `qualification.json`. Comparisons with native always use the real native harness, never an offline approximation of it. SecureBench gets the CPU, memory and disk limits from the upstream task's `[environment]`, as Pier does. The reference and the null candidate run first; if either gets a wrong verdict, qualify stops without running the others, and it runs nothing when a candidate is missing or unknown, there are more than five mutants or three attacks, a pack file is ignored by git, the pack holds an empty directory, or the pack is above 50 MiB. A native result is reused from an earlier qualification on the same worker when the upstream task, the Pier version, the candidate script, any candidate script it calls and the files in `candidates/` that are not candidate scripts are unchanged, and `qualification.json` marks it `native_cached`; native errors and timeouts always run again. Qualify reports a problem when:

- a SecureBench run is not admitted;
- a file in the pack is ignored by git (for example a `__pycache__`), so the committed pack would have another digest;
- the pack holds an empty directory, which git cannot commit but the pack digest counts;
- the pack is above 50 MiB (Section 11, `pack-size`);
- the SecureBench runs disagree on the SecureBench code, the worker record or the pack digest, or one was made with uncommitted changes to the SecureBench code;
- `rejudge` does not reproduce a verdict;
- the reference does not pass both graders, or the null candidate does not fail both;
- a mutant gets a different verdict from SecureBench than from the native harness (a native agent timeout counts as a native fail);
- an attack gets anything but `failed` from SecureBench;
- `reference`, `null` or a mutant is missing, a candidate has an unknown kind, or there are more than five mutants or three attacks.

## 9. Working loop

1. `uv run securebench validate conversions/<source>/<task>/task`.
2. Try one candidate at a time:

   ```bash
   uv run securebench run conversions/<source>/<task>/task --run-dir <scratch dir> \
     --harness scripted:<candidate> --qualification qualification.json \
     --cpus <c> --memory-mib <m> --disk-mib <d>
   ```

   Use the upstream task's `[environment]` values for the limits. Read the record in `<run dir>/attempts/`.
3. When every candidate behaves, fill in `CONVERSION.md` (Section 7), except "Divergences from native".
4. Start `python3 conversions/campaign.py qualify conversions/<source>/<task>` in the background. Then send the coordinator (SendMessage to `main`) exactly one line, `Ready for review: conversions/<source>/<task>`. A reviewer starts reading your conversion while qualify runs.
5. While qualify runs, change nothing in `task/` or `candidates/`. If it reports problems that need such a change, make it, send `Pack changed: conversions/<source>/<task>`, and run qualify again, until it reports no problems.
6. Explain every divergence between the graders in `qualification.json` under "Divergences from native", and say which grader is right. Then end with the report.

## 10. Shared machine

Other agents run conversions on the same Docker daemon at the same time.

- Keep what you read short. Everything you read stays in your context and is read again at every later step, so search a large file or read it in parts, and print only the lines you need from a long log.

- Never run `docker system prune`, `docker image prune` or `docker rm` on containers you did not start. Never remove images.
- Stop only processes you started, by their PID. Never kill by pattern (`pkill -f`, `killall`): other agents' qualifications match the same names.
- To wait for a background process, use the notice the Bash tool gives when a background command exits, or wait on its PID (`while kill -0 <pid> 2>/dev/null; do sleep 30; done`). Never wait on `pgrep -f`: the waiting loop's own command line matches the pattern, so the loop never ends.
- The scratch directory is shared by every agent of the session. Keep all your scratch files in a subdirectory named after your task (`<task>` for the converter, `<task>-review` for the reviewer), and never write in another agent's.
- Never run the integration test suite.
- When you import a module from a pack (an Oracle, an adapter, a derivation script), run Python with `-B` or set `PYTHONDONTWRITEBYTECODE=1`. A `__pycache__` written into `task/` changes the pack digest, also under another agent's running qualification.
- Run anything heavy or adversarial (native tools on crafted inputs, model or file differentials, builds) inside a container with a memory limit (`docker run --memory ...`), never directly on the host. A host process that exhausts memory is killed together with the coordinating session and every agent in it.
- The data root is small. If a pull fails for lack of space, stop and report it.

## 11. Exclusion

If the task cannot be converted for one of these reasons, and the reason holds for every possible conversion, stop. Report the reason with the evidence (file and line). Difficulty and effort are never reasons.

| Reason                      | Meaning                                                                                                                                                                                                                                                                                                                                                                                        |
|---|---|
| `trusted-external-state`    | Needs a trusted record of outbound effects, a service holding secrets the candidate must query without reading, or traffic between instances                                                                                                                                                                                                                                                   |
| `host-actions`              | Needs signals, restarts, clock control or fault injection on the Evaluation                                                                                                                                                                                                                                                                                                                    |
| `speed-target`              | Accepts only if faster than a reference                                                                                                                                                                                                                                                                                                                                                        |
| `network-during-evaluation` | The behavior under test needs network access at evaluation time                                                                                                                                                                                                                                                                                                                                |
| `cross-case-property`       | The property spans several fresh runs                                                                                                                                                                                                                                                                                                                                                          |
| `execution-property`        | The property is about how a computation ran, not its result (for example a leak report from a tool inside the Evaluation, which the candidate controls)                                                                                                                                                                                                                                        |
| `upstream-broken`           | The upstream reference fails the native harness on a qualified worker, even after the drift repairs Section 6 allows                                                                                                                                                                                                                                                                           |
| `worker-limits`             | Needs a GPU or more memory, CPU or disk than the campaign worker has                                                                                                                                                                                                                                                                                                                           |
| `pack-size`                 | A faithful conversion needs a pack above 50 MiB, for example wheels or model weights that the Evaluation cannot download                                                                                                                                                                                                                                                                       |
| `privileged-environment`    | Needs Linux capabilities (changing file ownership or user, overriding permissions) that every Evaluation environment drops, ownership and permissions that replay does not keep, or leaves deliverables that capture cannot read (including deliverables in a protected path, 4.8, which no scope may cover). Services that run as their own users, such as a mail server, are the common case |

## 12. Writing style

Write `CONVERSION.md` and comments plainly and directly. Comments in code explain why, never what.

## 13. Report

End with a short report:

- the files you wrote;
- the checks and how each maps to upstream assertions;
- the fidelity changes;
- the final `qualify` output;
- anything you are unsure about or that a reviewer should look at first.

