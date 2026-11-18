"""Oracle for terminal-bench/constraints-scheduling.

Upstream's three tests read /app/meeting_scheduled.ics and the input calendars
with `Path.read_text()` and inspect them with regular expressions and
`datetime`. This Oracle repeats every assertion with hand-written string and
integer code, because an Oracle may neither apply regular expressions to
evidence nor import `datetime`. Each artifact check corresponds to one part of
upstream's tests:

- `inputs-unchanged`: the integrity loop at the top of
  `test_structure_event_title_attendees_duration_window`;
- `structure`: the rest of that test;
- `constraints`: `test_constraints_conflicts_business_hours`;
- `earliest`: `test_earliest_tiebreakers_and_carol_buffer`.

Every literal those tests compare with is in hidden/spec.json, and the busy
intervals and digests of the input calendars are in hidden/calendars.json.
The scheduling rules themselves (`_hard_ok`) are judging logic, transliterated
from upstream's `_hard_ok` line by line.

A point in time is an integer number of seconds: the proleptic Gregorian
ordinal of its date (as `date.toordinal()` counts) times 86400, plus the
seconds since midnight. Upstream's timestamps never carry a fraction of a
second, so this represents every `datetime` the tests can build.
"""

import hashlib

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

DAY = 86400
HOUR = 3600
MINUTE = 60
_DAYS_BEFORE_MONTH = (0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
_DAYS_IN_MONTH = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
# Bound of a whole-minute scan; upstream's scan ends at the first valid slot,
# which the upstream calendars put about 3,000 minutes after its start.
MAX_SCAN_STEPS = 1_000_000


def plan(resources: HiddenResources, seed: int) -> Plan:
    spec = resources.read_json("spec.json")
    calendars = resources.read_json("calendars.json")
    context = {"spec": spec, "calendars": calendars}
    return Plan(
        artifact_contexts={
            "inputs-unchanged": context,
            "structure": context,
            "constraints": context,
            "earliest": context,
        },
        cases={},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence) or not isinstance(context, dict):
        return _fail("unexpected evidence")
    spec = context.get("spec")
    calendars = context.get("calendars")
    if not isinstance(spec, dict) or not isinstance(calendars, dict):
        return _fail("malformed context")
    if check_id == "inputs-unchanged":
        return _judge_inputs(spec, calendars, evidence)
    texts = _texts(evidence)
    if isinstance(texts, Judgment):
        return texts
    if len(texts) != 1:
        return _fail("expected exactly one file")
    text = texts[0]
    if check_id == "structure":
        return _judge_structure(spec, text)
    busy = _busy(spec, calendars)
    if busy is None:
        return _fail("malformed hidden calendars")
    if check_id == "constraints":
        return _judge_constraints(spec, busy, text)
    if check_id == "earliest":
        return _judge_earliest(spec, calendars, busy, text)
    return _fail(f"unknown check {check_id}")


# --- the checks -------------------------------------------------------------


def _judge_inputs(spec: dict, calendars: dict, evidence: ArtifactEvidence) -> Judgment:
    """`assert app_text == repo_path.read_text()` or the `_EXPECTED_SHA256` digest."""
    texts = _texts(evidence)
    if isinstance(texts, Judgment):
        return texts
    names = spec["calendars"]
    if len(texts) != len(names):
        return _fail("expected one file per input calendar")
    for name, text in zip(names, texts):
        expected = calendars[name]["sha256"]
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            return _fail(f"Input modified: {name}")
    return Judgment(True, None)


def _judge_structure(spec: dict, c: str) -> Judgment:
    stripped = c.strip()
    if not stripped.startswith(spec["prefix"]):
        return _fail("file does not start with BEGIN:VCALENDAR")
    if not stripped.endswith(spec["suffix"]):
        return _fail("file does not end with END:VCALENDAR")
    for needed in spec["required_substrings"]:
        if needed not in c:
            return _fail(f"missing {needed}")

    vevents = _find_blocks(c, spec["vevent_begin"], spec["vevent_end"])
    if not vevents:
        return _fail("Missing VEVENT block")
    emails = spec["emails"]
    meeting = None
    for block in vevents:
        if spec["summary"] in block and all(e in block for e in emails):
            meeting = block
            break
    if meeting is None:
        return _fail("Meeting VEVENT with required SUMMARY and ATTENDEE entries not found")

    for email in emails:
        if not _has_attendee_line(meeting, spec["attendee_name"], spec["attendee_separators"], email):
            return _fail(f"Missing ATTENDEE property for {email} in meeting VEVENT")

    s = _first_stamp(meeting, spec["dtstart"])
    e = _first_stamp(meeting, spec["dtend"])
    if s is None or e is None:
        return _fail("meeting VEVENT has no parsable DTSTART or DTEND")
    if e - s != spec["duration_seconds"]:
        return _fail("meeting is not one hour long")
    year, month, day = _ymd(s // DAY)
    if not (year == spec["meeting_year"] and month == spec["meeting_month"]):
        return _fail("meeting is not in January 2024")
    if not (spec["meeting_first_day"] <= day <= spec["meeting_last_day"]):
        return _fail("meeting is not on January 15-19")
    if not _weekday(s) < 5:
        return _fail("meeting is not on a weekday")
    return Judgment(True, None)


def _judge_constraints(spec: dict, busy: list, c: str) -> Judgment:
    # Upstream takes the first DTSTART of the whole file, not of the meeting VEVENT.
    s = _first_stamp(c, spec["dtstart"])
    if s is None:
        return _fail("no DTSTART, or its first one is not a valid timestamp")
    e = _add(s, spec["duration_seconds"])
    if e is None:
        return _fail("date value out of range")
    if not _hard_ok(s, e):
        return _fail("meeting violates a hard constraint", s)
    for intervals in busy:
        if _overlap(s, e, intervals):
            return _fail("meeting conflicts with an existing event", s)
    return Judgment(True, None)


def _judge_earliest(spec: dict, calendars: dict, busy: list, c: str) -> Judgment:
    sched = _first_stamp(c, spec["dtstart"])
    if sched is None:
        return _fail("no DTSTART, or its first one is not a valid timestamp")
    duration = spec["duration_seconds"]

    t = _point(spec["scan_start"])
    steps = 0
    while t < sched:
        steps += 1
        if steps > MAX_SCAN_STEPS:
            return _fail("scan bound exceeded")
        if _weekday(t) < 5:
            t1 = t + duration
            if _hard_ok(t, t1) and not any(_overlap(t, t1, cal) for cal in busy):
                return _fail("Found earlier valid slot", t)
        t += MINUTE

    # Tie-breakers: the same hour and minute (seconds dropped) on every day.
    hour, minute, _ = _hms(sched)
    first_day = spec["tie_first_day"]
    u = _point([first_day[0], first_day[1], first_day[2], hour, minute])
    tie_end = _point(spec["tie_end"])
    candidates = []
    while u <= tie_end:
        if _weekday(u) < 5:
            u1 = u + duration
            if _hard_ok(u, u1) and not any(_overlap(u, u1, cal) for cal in busy):
                candidates.append(u)
        u += DAY
    has_monday = any(_weekday(d) == 0 for d in candidates)
    has_tue_fri = any(_weekday(d) in (1, 2, 3, 4) for d in candidates)
    if has_monday and has_tue_fri and _weekday(sched) not in (1, 2, 3, 4):
        return _fail("Tie-breaker: avoid Monday when alternatives exist", sched)

    if not (9 <= hour < 12):
        return _fail("Prefer Alice's morning (9-12) when possible", sched)

    carol = _intervals(calendars[spec["buffer_calendar"]]["busy"])
    if carol is None:
        return _fail("malformed hidden calendars")
    end = _add(sched, duration)
    if end is None:
        return _fail("date value out of range")
    end_hour, end_minute, _ = _hms(end)
    if end_hour > 16 or (end_hour == 16 and end_minute >= 45):
        buf_end = _add(end, 15 * MINUTE)
        if buf_end is None:
            return _fail("date value out of range")
        for es, ee in carol:
            if end < ee and buf_end > es:
                return _fail("Violates Carol late buffer (after)", sched)
    for _, ee in carol:
        ee_hour, ee_minute, _ = _hms(ee)
        if ee_hour > 16 or (ee_hour == 16 and ee_minute >= 45):
            b0 = ee
            b1 = ee + 15 * MINUTE
            if sched < b1 and end > b0:
                return _fail("Violates Carol late buffer (before)", sched)
    return Judgment(True, None)


# --- upstream's helpers -----------------------------------------------------


def _hard_ok(t0: int, t1: int) -> bool:
    """Upstream's `_hard_ok`, condition for condition, on (hour, minute, weekday)."""
    h0, m0, s0 = _hms(t0)
    h1, m1, _ = _hms(t1)
    if not ((h0 > 9) or (h0 == 9 and m0 >= 0)):  # Alice start
        return False
    if not ((h1 < 14) or (h1 == 14 and m1 <= 0)):  # Alice end
        return False
    if h0 < 10:  # Bob start
        return False
    if _weekday(t0) in (1, 3) and not (h1 < 16 or (h1 == 16 and m1 <= 30)):
        return False
    if not ((h1 < 17) or (h1 == 17 and m1 <= 0)):  # Carol day end
        return False

    # `t0.replace(hour=12, minute=0)` keeps t0's seconds.
    lunch0 = (t0 // DAY) * DAY + 12 * HOUR + s0
    lunch1 = (t0 // DAY) * DAY + 12 * HOUR + 30 * MINUTE + s0
    if t0 < lunch1 and t1 > lunch0:
        return False

    if t1 // DAY != t0 // DAY or _weekday(t0) >= 5:
        return False
    if not ((h0 > 9) or (h0 == 9 and m0 >= 0)):
        return False
    if not ((h1 < 18) or (h1 == 18 and m1 <= 0)):
        return False
    return True


def _overlap(a0: int, a1: int, intervals: list) -> bool:
    for b0, b1 in intervals:
        if a0 < b1 and a1 > b0:
            return True
    return False


def _find_blocks(c: str, begin: str, end: str) -> list:
    """`re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", c, flags=re.S)`.

    The lazy group ends at the first END:VEVENT after its BEGIN:VEVENT, and
    the next match starts after that END:VEVENT. A BEGIN:VEVENT with no
    END:VEVENT after it ends the search, as every later one has none either.
    """
    blocks = []
    position = 0
    while True:
        start = c.find(begin, position)
        if start < 0:
            return blocks
        stop = c.find(end, start + len(begin))
        if stop < 0:
            return blocks
        blocks.append(c[start + len(begin) : stop])
        position = stop + len(end)


def _has_attendee_line(block: str, name: str, separators: str, email: str) -> bool:
    """`re.search(rf"^ATTENDEE[:;].*{re.escape(email)}$", block, re.I | re.M)`.

    With re.M, `^` and `$` delimit the pieces between "\\n" characters, and
    `.` matches anything but "\\n". So some piece must start with ATTENDEE
    (ignoring case), then ":" or ";", and end with the email (ignoring case)
    after at least zero further characters.
    """
    head = len(name) + 1
    for line in block.split("\n"):
        if len(line) < head + len(email):
            continue
        if not _iequal(line[: len(name)], name):
            continue
        if line[len(name)] not in separators:
            continue
        if _iequal(line[len(line) - len(email) :], email):
            return True
    return False


def _iequal(text: str, pattern: str) -> bool:
    if len(text) != len(pattern):
        return False
    return all(_ichar(t, p) for t, p in zip(text, pattern))


def _ichar(t: str, p: str) -> bool:
    """One character as `re.IGNORECASE` matches it against the literal `p`.

    `p` is printable ASCII. Python's `re` compares simple lowercase mappings
    and adds a few extra equivalences; for ASCII literals these are exactly
    the dotted and dotless i (U+0130, U+0131), the long s (U+017F) and the
    Kelvin sign (U+212A). The table is checked against `re` over every code
    point (see CONVERSION.md).
    """
    lower = p.lower()
    if t == p or t == lower or t == p.upper():
        return True
    if lower == "i":
        return t in ("İ", "ı")
    if lower == "s":
        return t == "ſ"
    if lower == "k":
        return t == "K"
    return False


def _first_stamp(text: str, prefix: str) -> int | None:
    """`_dt(r"<prefix>(\\d{8}T\\d{6}Z)", text)`: the first match, then strptime.

    The search takes the leftmost match, so a later well-formed stamp never
    replaces an earlier one that strptime rejects.
    """
    start = text.find(prefix)
    while start >= 0:
        token = text[start + len(prefix) : start + len(prefix) + 16]
        if _stamp_shape(token):
            return _strptime(token)
        start = text.find(prefix, start + 1)
    return None


def _stamp_shape(token: str) -> bool:
    """`\\d{8}T\\d{6}Z`, where `\\d` is any Unicode decimal digit, as in `re`."""
    if len(token) != 16:
        return False
    return (
        all(ch.isdecimal() for ch in token[0:8])
        and token[8] == "T"
        and all(ch.isdecimal() for ch in token[9:15])
        and token[15] == "Z"
    )


def _strptime(token: str) -> int | None:
    """`datetime.strptime(token, "%Y%m%dT%H%M%SZ")` on a token of `_stamp_shape`.

    `_strptime` matches %Y with `\\d\\d\\d\\d`, %m with `1[0-2]|0[1-9]|[1-9]`,
    %d with `3[0-1]|[1-2]\\d|0[1-9]|[1-9]| [1-9]`, %H with `2[0-3]|[0-1]\\d|\\d`,
    %M with `[0-5]\\d|\\d` and %S with `6[0-1]|[0-5]\\d|\\d`. In a 16-character
    token every field must then take two characters (four for the year), and
    only the positions written `\\d` accept non-ASCII digits. `int()` reads
    those digits, and `datetime()` rejects year 0, impossible days and
    seconds 60 and 61.
    """
    digits = "0123456789"
    y, mo, d, h, mi, s = token[0:4], token[4:6], token[6:8], token[9:11], token[11:13], token[13:15]
    month_ok = (mo[0] == "1" and mo[1] in "012") or (mo[0] == "0" and mo[1] in digits[1:])
    day_ok = (
        (d[0] == "3" and d[1] in "01")
        or (d[0] in "12" and d[1].isdecimal())
        or (d[0] == "0" and d[1] in digits[1:])
    )
    hour_ok = (h[0] == "2" and h[1] in "0123") or (h[0] in "01" and h[1].isdecimal())
    minute_ok = mi[0] in "012345" and mi[1].isdecimal()
    second_ok = (s[0] == "6" and s[1] in "01") or (s[0] in "012345" and s[1].isdecimal())
    if not (month_ok and day_ok and hour_ok and minute_ok and second_ok):
        return None
    year, month, day = int(y), int(mo), int(d)
    hour, minute, second = int(h), int(mi), int(s)
    if year < 1 or second > 59:
        return None
    if day > _days_in_month(year, month):
        return None
    return _ordinal(year, month, day) * DAY + hour * HOUR + minute * MINUTE + second


# --- calendar arithmetic ----------------------------------------------------


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _leap(year):
        return 29
    return _DAYS_IN_MONTH[month]


def _ordinal(year: int, month: int, day: int) -> int:
    """`date(year, month, day).toordinal()`."""
    y = year - 1
    before_year = y * 365 + y // 4 - y // 100 + y // 400
    before_month = _DAYS_BEFORE_MONTH[month] + (1 if month > 2 and _leap(year) else 0)
    return before_year + before_month + day


def _ymd(ordinal: int) -> tuple[int, int, int]:
    """`date.fromordinal(ordinal)`, by counting from an estimate of the year."""
    year = max(1, (ordinal * 400) // 146097)
    while _ordinal(year + 1, 1, 1) <= ordinal:
        year += 1
    while _ordinal(year, 1, 1) > ordinal:
        year -= 1
    month = 1
    while month < 12 and _ordinal(year, month + 1, 1) <= ordinal:
        month += 1
    return year, month, ordinal - _ordinal(year, month, 1) + 1


_MAX_POINT = _ordinal(9999, 12, 31) * DAY + DAY - 1


def _add(t: int, seconds: int) -> int | None:
    """`t + timedelta(seconds=seconds)`, or None where `datetime` overflows."""
    result = t + seconds
    return result if result <= _MAX_POINT else None


def _weekday(t: int) -> int:
    """`datetime.weekday()`: Monday is 0."""
    return (t // DAY + 6) % 7


def _hms(t: int) -> tuple[int, int, int]:
    rest = t % DAY
    return rest // HOUR, rest % HOUR // MINUTE, rest % MINUTE


def _point(fields: list) -> int:
    year, month, day, hour, minute = fields
    return _ordinal(year, month, day) * DAY + hour * HOUR + minute * MINUTE


# --- evidence and hidden data -----------------------------------------------


def _texts(evidence: ArtifactEvidence) -> list | Judgment:
    """Each file's text as `Path.read_text()` returns it, with universal newlines."""
    texts = []
    for found in evidence.files:
        if found.status is not FileStatus.PRESENT:
            return _fail(f"{found.path} is {found.status.value}")
        if not isinstance(found.value, Text):
            return _fail(f"{found.path} was not read as text")
        texts.append(found.value.text.replace("\r\n", "\n").replace("\r", "\n"))
    return texts


def _intervals(pairs: list) -> list | None:
    out = []
    for start, end in pairs:
        a, b = _first_stamp(start, ""), _first_stamp(end, "")
        if a is None or b is None:
            return None
        out.append((a, b))
    return out


def _busy(spec: dict, calendars: dict) -> list | None:
    busy = []
    for name in spec["calendars"]:
        intervals = _intervals(calendars[name]["busy"])
        if intervals is None:
            return None
        busy.append(intervals)
    return busy


def _fail(reason: str, at: int | None = None) -> Judgment:
    diagnostic: dict = {"reason": reason}
    if at is not None:
        year, month, day = _ymd(at // DAY)
        hour, minute, second = _hms(at)
        diagnostic["at"] = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    return Judgment(False, diagnostic)
