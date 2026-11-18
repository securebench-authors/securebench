"""Oracle for multi-source-data-merger.

Upstream's tests (tests/test_outputs.py) assert that both files exist; that the
merged Parquet has exactly 4 rows whose user_id set is {101, 102, 103, 104};
that users 101 and 104 have the expected name, email and created_date; and that
conflicts.json has total_conflicts >= 1 equal to the length of `conflicts`, at
least one conflict for user 101, and, if user 101 has an email conflict, that
the first one's values.source_a and selected are "john@a.com".

This Oracle checks exactly those assertions, with the semantics of upstream's
Python comparisons on the values the adapter decoded: a string equals only an
equal string (also inside up to 16 nested one-element arrays, as numpy
compares them), and a number equals an integer when it is that int, a float or a
decimal of the same value, or (for 0 and 1) a boolean. Every expected value is
in hidden/cases.json, copied from upstream's test.
"""

from decimal import Decimal, DecimalException

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

# The column upstream selects rows by. It names where to look, not what to find.
KEY = "user_id"


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, dict):
        raise ValueError("hidden/cases.json is not an object")
    built = {}
    for check_id in ("merged", "conflicts"):
        listed = cases[check_id]
        if not isinstance(listed, list) or not listed:
            raise ValueError(f"hidden/cases.json has no cases for {check_id}")
        built[check_id] = tuple(Case(case["challenge"], case["expected"]) for case in listed)
    return Plan(artifact_contexts={}, cases=built)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected artifact evidence"})
    if isinstance(evidence.outcome, Unable):
        return Judgment(False, {"reason": "deliverable missing or unreadable", "code": evidence.outcome.code})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    if check_id == "merged":
        return _merged(context, observed)
    if check_id == "conflicts":
        return _conflicts(context, observed)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def _present(cell: JsonValue) -> bool:
    """The key exists, so upstream's indexing does not raise KeyError."""
    return isinstance(cell, dict) and cell["kind"] != "absent"


def _is_text(cell: JsonValue, text: str) -> bool:
    """`value == text` in Python, for a value decoded from the deliverable."""
    return isinstance(cell, dict) and cell["kind"] == "str" and cell["exact"] is True and cell["text"] == text


def _equals_number(cell: JsonValue, number: int) -> bool:
    """`value == number` in Python: an int, float or decimal of the same value, or a bool for 0 and 1."""
    if not isinstance(cell, dict) or cell["exact"] is not True:
        return False
    text = cell["text"]
    if not isinstance(text, str):
        return False
    if cell["kind"] == "int":
        return text == str(number)
    if cell["kind"] == "float":
        return text == repr(float(number))
    if cell["kind"] == "bool":
        return number in (0, 1) and text == ("True" if number == 1 else "False")
    if cell["kind"] == "decimal":
        try:
            value = Decimal(text)
            return not value.is_nan() and value == number
        except (DecimalException, ValueError):
            return False
    return False


def _merged(expected: dict[str, JsonValue], observed: dict[str, JsonValue]) -> Judgment:
    columns = observed["columns"]
    rows = observed["rows"]
    row_count = expected["row_count"]
    user_ids = expected["user_ids"]
    users = expected["users"]
    if not isinstance(row_count, int) or not isinstance(user_ids, list) or not isinstance(users, list):
        return Judgment(False, {"reason": "malformed context"})
    if not isinstance(columns, list) or not isinstance(rows, list):
        return Judgment(False, {"reason": "malformed"})
    if observed["column_count"] != len(columns):
        return Judgment(False, {"reason": "more columns than reported", "column_count": observed["column_count"]})
    needed = [KEY]
    for user in users:
        if not isinstance(user, dict):
            return Judgment(False, {"reason": "malformed context"})
        needed.extend(name for name in user if name != KEY and name not in needed)
    for name in needed:
        # Upstream's df[name] and row[name] raise KeyError for a missing column.
        # A repeated column gives a frame or series where upstream expects one
        # value, and set(...) or `assert series == text` then fails as well.
        found = sum(1 for column in columns if _is_text(column, name))
        if found != 1:
            return Judgment(False, {"reason": f"column {name} appears {found} times"})
    # Upstream: len(df) == 4.
    if observed["row_count"] != row_count or len(rows) != row_count:
        return Judgment(False, {"reason": "wrong number of rows", "rows": observed["row_count"]})
    # Upstream: set(df["user_id"]) == {101, 102, 103, 104}. A value equal to
    # none of them adds an element to the set; the set is equal only when every
    # value matches one of them and each of them is matched.
    matched = set()
    row_ids = []
    for row in rows:
        if not isinstance(row, dict):
            return Judgment(False, {"reason": "malformed"})
        match = next((number for number in user_ids if isinstance(number, int) and _equals_number(row[KEY], number)), None)
        if match is None:
            return Judgment(False, {"reason": "user_id set differs", "user_id": row[KEY]})
        matched.add(match)
        row_ids.append(match)
    if matched != set(user_ids):
        return Judgment(False, {"reason": "user_id set differs", "missing": sorted(set(user_ids) - matched)})
    # Upstream: df[df["user_id"] == N].iloc[0], then each field == its literal.
    # The adapter reports a value inside one-element arrays (a Parquet list
    # cell) by its innermost value; `assert array == text` passes for those
    # whatever the nesting, so the number of wrapping arrays is not judged.
    # The adapter unwraps at most 16; a deeper cell fails (see CONVERSION.md).
    for user in users:
        number = user[KEY]
        if number not in row_ids:
            return Judgment(False, {"reason": "malformed context"})
        row = rows[row_ids.index(number)]
        for name, want in user.items():
            if name == KEY:
                continue
            if not isinstance(want, str) or not _is_text(row[name], want):
                return Judgment(False, {"reason": f"wrong {name}", "user_id": number, "got": row[name]})
    return Judgment(True, None)


def _conflicts(expected: dict[str, JsonValue], observed: dict[str, JsonValue]) -> Judgment:
    minimum = expected["min_total_conflicts"]
    user_id = expected["user_id"]
    field = expected["field"]
    source_a = expected["source_a"]
    selected = expected["selected"]
    if not (isinstance(minimum, int) and isinstance(user_id, int) and isinstance(field, str)):
        return Judgment(False, {"reason": "malformed context"})
    if not (isinstance(source_a, str) and isinstance(selected, str)):
        return Judgment(False, {"reason": "malformed context"})
    # report["total_conflicts"] raises unless the report is an object with that key.
    if observed["report"] != "object":
        return Judgment(False, {"reason": "conflicts.json is not an object"})
    total = observed["total_conflicts"]
    if not _present(total):
        return Judgment(False, {"reason": "no total_conflicts"})
    # len(report["conflicts"]) and iterating it with c["user_id"] succeed only
    # for a list of objects (a non-empty string or object yields strings).
    entries = observed["conflicts"]
    if not isinstance(entries, list) or observed["conflicts_kind"] != "list":
        return Judgment(False, {"reason": "conflicts is not a list"})
    if observed["conflict_count"] != len(entries):
        return Judgment(False, {"reason": "more conflicts than reported", "count": observed["conflict_count"]})
    # Upstream: total_conflicts >= 1 and len(conflicts) == total_conflicts.
    if len(entries) < minimum or not _equals_number(total, len(entries)):
        return Judgment(False, {"reason": "total_conflicts does not match", "total": total, "listed": len(entries)})
    # Upstream: [c for c in conflicts if c["user_id"] == 101], at least one.
    for entry in entries:
        if not isinstance(entry, dict) or entry["kind"] != "object" or not _present(entry["user_id"]):
            return Judgment(False, {"reason": "a conflict is not an object with a user_id"})
    mine = [entry for entry in entries if _equals_number(entry["user_id"], user_id)]
    if not mine:
        return Judgment(False, {"reason": f"no conflict for user {user_id}"})
    # Upstream: [c for c in those if c["field"] == "email"]; if any, the first
    # has values["source_a"] and selected equal to the expected value.
    for entry in mine:
        if not _present(entry["field"]):
            return Judgment(False, {"reason": f"a conflict for user {user_id} has no field"})
    chosen = [entry for entry in mine if _is_text(entry["field"], field)]
    if chosen:
        first = chosen[0]
        if first["values"] != "object":
            return Judgment(False, {"reason": f"values of the {field} conflict is not an object"})
        if not _is_text(first["source_a"], source_a):
            return Judgment(False, {"reason": f"wrong source_a in the {field} conflict", "got": first["source_a"]})
        if not _is_text(first["selected"], selected):
            return Judgment(False, {"reason": f"wrong selected in the {field} conflict", "got": first["selected"]})
    return Judgment(True, None)
