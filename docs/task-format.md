# Task pack format

A task pack is one directory. Its layout fixes the visibility class of every resource (architecture Section 4), and one TOML file declares everything else. Pack validation (`taskspec`) rejects anything this document does not allow.

## 1. Layout

```
<task>/
  task.toml           the task specification (Section 2)
  instructions.md     public: given to the agent verbatim
  public/             public assets (class `public`)
  evaluation/         evaluation inputs (class `evaluation_inputs`)
  hidden/             hidden resources (class `hidden`); hidden/oracle.py is the Oracle
```

- `task.toml` and `instructions.md` are required. `public/`, `evaluation/` and `hidden/` are optional, except that `hidden/oracle.py` is required.
- No other entries may exist at the top level.
- No symlink may appear anywhere in the pack, and every entry is a regular file or a directory.
- File names are valid UTF-8, and paths follow the canonical path rules in Section 5.
- `task.toml` is at most 256 KiB, `instructions.md` at most 1 MiB, and the whole pack at most 1 GiB and 100,000 entries.

How each class reaches the environments:

| Resource | Agent environment | Evaluation environment | Host |
|---|---|---|---|
| `instructions.md` | read-only at `/.securebench/instructions.md` | no | yes |
| `public/<source>` | read-only at the declared `target` | no | yes |
| `evaluation/` | no | read-only at `/.securebench/evaluation` | yes |
| `hidden/` | no | no | yes, through the Oracle only |
| stock Python image (framework, not in the pack) | no | read-only at `/.securebench/python` (Section 3) | n/a |

The `public/` assets are not mounted into Evaluation environments. A task that needs a public file during evaluation also places a copy in `evaluation/`. This keeps each environment's mount list fixed by one rule.

## 2. `task.toml`

TOML 1.0, read with `tomllib`. Every table has an exact key set: unknown keys are rejected, and so are missing required keys. Integers must be TOML integers (a boolean is never accepted as an integer), and every integer is checked against the range given here. Strings are bounded as stated; "name" means 1 to 64 bytes of lowercase ASCII letters, digits and `-`, starting with a letter or digit.

### Top level

| Key | Type | Rule |
|---|---|---|
| `id` | string | name |
| `source_benchmark` | string | name |
| `baseline` | table | Section 2.1 |
| `agent` | table | Section 2.2 |
| `scope` | table | Section 2.3 |
| `public_assets` | array of tables | optional, Section 2.4 |
| `artifact_checks` | array of tables | optional, Section 2.5 |
| `protocol_checks` | array of tables | optional, Section 2.6 |

A task declares at least one check. Check identifiers are names and are unique across both kinds of check.

### 2.1 `[baseline]`

| Key | Type | Rule |
|---|---|---|
| `image` | string | `<repository>@sha256:<64 lowercase hex>`, or `sha256:<64 lowercase hex>` for a local image ID |
| `repository` | table | optional: `path` (absolute directory inside a scope root) and `commit` (40 or 64 lowercase hex characters) |

When `repository` is present, the live baseline check confirms that `<path>/.git` is a real directory, `HEAD` equals `commit`, and the working tree is clean, including untracked files.

### 2.2 `[agent]`

| Key | Type | Rule |
|---|---|---|
| `workdir` | string | absolute path inside a scope root; the working directory of every environment the task starts |
| `allowed_domains` | array of strings | at most 1,024 entries; each a domain under Section 7; may be empty |

### 2.3 `[scope]`

| Key | Type | Rule |
|---|---|---|
| `max_entries` | integer | 1 to 100,000; bound on entries walked across all roots |
| `max_bytes` | integer | 1 to 2 GiB; bound on file bytes walked across all roots |
| `roots` | array of tables | 1 to 16 roots |

Each `[[scope.roots]]`:

| Key | Type | Rule |
|---|---|---|
| `path` | string | absolute canonical path; not `/`; a real directory in the baseline |
| `exclude` | array of strings | optional; patterns under Section 6; at most 256 |
| `git_directories` | array of strings | optional; relative paths whose last component is `.git`; these are captured as plain files instead of being excluded |
| `symlinks` | boolean | whether internal symlinks may be created or changed |
| `max_entries` | integer | 1 to the scope's `max_entries` |
| `max_bytes` | integer | 1 to the scope's `max_bytes` |

Roots may not overlap one another, compared with folding (Section 5). No root may equal, contain or sit inside a framework-protected path (Section 8).

### 2.4 `[[public_assets]]`

| Key | Type | Rule |
|---|---|---|
| `source` | string | relative canonical path of a file or directory under `public/` |
| `target` | string | absolute canonical mount point in the Agent environment |

A target may not equal, contain or sit inside a scope root or a framework-protected path, and no two targets may overlap. All compared with folding.

### 2.5 `[[artifact_checks]]`

A passive check (`artifact_checks`) reads the candidate by lookup and starts no environment.

| Key | Type | Rule |
|---|---|---|
| `id` | string | name |
| `files` | array of tables | optional; each `path`, `parser`, `max_bytes` |
| `listings` | array of tables | optional; each `path`, `max_entries` |

At least one file or listing. `path` is an absolute canonical path inside a scope root and not excluded. `parser` is `text` or `json`; `json` accepts nesting of at most 57 levels, so that the value still fits in a result record. `max_bytes` is 1 to 16 MiB, and `max_entries` is 1 to 100,000. A file path that is absent, or not a regular file in the candidate, is a normal state passed to the Oracle.

### 2.6 `[[protocol_checks]]`

| Key | Type | Rule |
|---|---|---|
| `id` | string | name |
| `command` | array of strings | 1 to 64 elements, each 1 to 4,096 bytes and free of NUL; the first is an absolute path |
| `challenge_schema` | string | relative path of a schema file under `evaluation/` |
| `observation_schema` | string | relative path of a schema file under `evaluation/` |
| `max_cases` | integer | 1 to 1,000 |
| `timeout_seconds` | integer | 1 to 3,600; per case |
| `max_challenge_bytes` | integer | 1 to 1 MiB |
| `max_observation_bytes` | integer | 1 to 4 MiB; bounds the whole response |
| `setup_command` | array of strings | optional; same rules as `command` |
| `setup_timeout_seconds` | integer | required with `setup_command`, 1 to 7,200 |
| `output_artifacts` | array of tables | optional; each `path`, `parser`, `max_bytes` |

Output file paths (`output_artifacts`) follow the passive check path rules, except that they need not lie inside a scope root. They may not sit inside a `.git` directory or a framework-protected path. The sum of `max_bytes` over one check's output files is at most 16 MiB, and there are at most 64 of them.

## 3. Adapter protocol

For each case the framework starts a fresh Evaluation environment and runs `command` with the working directory `agent.workdir`. The challenge arrives on standard input as canonical JSON: sorted keys, no spaces, a trailing newline (`securebench/core/jsondata.py`). The adapter writes exactly one JSON value to standard output, which is one of two envelopes:

```json
{"observation": <value matching the observation schema>}
{"unable": {"code": "<1 to 128 bytes>", "message": "<0 to 4,096 bytes>"}}
```

Every Evaluation environment also has the stock Python image mounted read-only at `/.securebench/python`, so an adapter can be standard-library Python even when the baseline has no interpreter. It starts through the stock image's own loader:

```toml
command = [
  "/.securebench/python/lib64/ld-linux-x86-64.so.2",
  "--library-path",
  "/.securebench/python/usr/local/lib:/.securebench/python/lib/x86_64-linux-gnu:/.securebench/python/usr/lib/x86_64-linux-gnu",
  "/.securebench/python/usr/local/bin/python3", "-I", "/.securebench/evaluation/adapter.py",
]
```

An adapter started this way that runs another Python process repeats this invocation, because `sys.executable` alone does not find the stock libraries.

The second envelope reports that the adapter could not exercise the candidate. It is kept as a diagnostic, and the case fails with class `case_error`. Standard error is discarded. A response larger than `max_observation_bytes`, or that is not valid UTF-8, strict JSON or one of these envelopes, fails the case with class `case_error`. So does a non-zero exit, a timeout or a memory kill.

`setup_command`, when present, runs once on the replayed candidate with the same mounts and no standard input. Exit status 0 means success. Any other ending fails the attempt with class `setup`. Its filesystem is then snapshotted, and every case starts from its own copy.

## 4. Schemas

Challenge and observation schemas are strict JSON files of at most 64 KiB, with depth at most 16 and at most 1,024 schema nodes. A schema node is an object with an exact key set for its type:

| `type` | Other keys |
|---|---|
| `"object"` | `properties` (object of name to schema node, at most 256), optional `optional` (array of property names that may be absent). Unknown fields are always rejected. |
| `"array"` | `items` (schema node), `max_items` (0 to 100,000), optional `min_items` |
| `"string"` | `max_bytes` (0 to 4 MiB, counted in UTF-8 bytes), optional `enum` (1 to 256 distinct strings) |
| `"integer"` | `minimum`, `maximum` (both required, at most 2^63 in magnitude) |
| `"number"` | `minimum`, `maximum` (both required, finite) |
| `"boolean"` | none |
| `"null"` | none |

No patterns or character sets (architecture Section 7.3). Booleans never satisfy `integer` or `number`. An integer satisfies `number`.

## 5. Paths

### Canonical path text

- An absolute path starts with exactly one `/`.
- No component is empty, `.` or `..`, and the path has no trailing `/`, backslash or NUL.
- It is valid UTF-8, at most 4,096 bytes and at most 128 components.

A relative path follows the same rules without the leading `/`. Every path in a task specification must be canonical. Pack validation does not normalize paths; it rejects any that aren't canonical.

### Folding

Decisions that protect, exclude or detect collisions compare components after Unicode NFC normalization and case folding. Containment that grants access ("this path is inside root R") uses exact components.

## 6. Exclude patterns

A pattern is a relative path matched against a path relative to its scope root, one component at a time:

- A component `**` matches zero or more whole components.
- Inside any other component, `*` matches zero or more characters other than `/`.
- No other character is special. `?`, `[`, `]` and `\` are rejected.

A pattern that matches a path excludes that path and everything below it. Matching uses folding. Every root implicitly carries the pattern `**/.git`, except for the paths listed in its `git_directories`. Changes to excluded paths are dropped from the candidate.

## 7. Allowed domains

Each entry is lowercase ASCII, with at most one trailing dot, which is removed. The rules:
- Labels are 1 to 63 characters of letters, digits and `-`, and don't start or end with `-`.
- A name has at least two labels and is at most 253 characters.
- No scheme, port, path, wildcard, IP literal, `localhost` or `*.localhost`.
- Duplicates are rejected.

An entry allows itself and its subdomains, matched on a dot boundary.

## 8. Framework-protected paths

No scope root, public asset target or output file path may equal, contain or sit inside any of these (system paths no task may weaken, plus the framework's own directory):

```
/.securebench /proc /sys /dev /run /var/run /tmp /var/tmp /var/lib/docker /var/lib/containerd /run/containerd /root /etc/passwd /etc/group /etc/shadow /etc/gshadow /etc/subuid /etc/subgid /etc/sudoers /etc/sudoers.d /etc/ssh /etc/apt /etc/dnf /etc/yum.repos.d /etc/pacman.conf /etc/pacman.d /var/lib/apt /var/lib/dpkg /var/lib/rpm /var/lib/pacman /var/cache/apt /var/cache/dnf /var/cache/yum
```

The baseline must not contain `/.securebench`.

## 9. Example: fixture F1

```
f1-answer-file/
  task.toml
  instructions.md
  public/numbers.txt
  hidden/oracle.py
  hidden/expected.json
```

`instructions.md`:

```markdown
The file /data/numbers.txt contains one integer per line. Write their sum to
/srv/answer.json as a JSON object of the form {"sum": <integer>}.
```

`task.toml`:

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

`hidden/oracle.py` reads `expected.json` in `plan` and compares in `judge`. The contract it implements is described in the `oracle` module's interface.
