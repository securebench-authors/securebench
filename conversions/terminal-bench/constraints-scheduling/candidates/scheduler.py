"""A minute-granularity scheduler shared by the mutants and the input-forging attack.

It solves the task as the instructions describe and then writes the meeting in
one of several output styles; each mutant picks one deviation.

    python3 scheduler.py [--no-bob-start] [--style STYLE]

STYLE is one of:
  plain        LF line endings, `ATTENDEE:MAILTO:<email>`
  crlf-params  CRLF line endings (as RFC 5545 asks), ATTENDEE parameters and
               upper-case MAILTO addresses, the lower-case address in CN
  folded       RFC 5545 line folding at 75 octets, which splits long ATTENDEE lines
  merged       every existing event of the three calendars first, then the meeting
  floating     floating local times without the trailing `Z`
"""

import re
import sys
from datetime import datetime, timedelta

NAMES = ("alice_calendar.ics", "bob_calendar.ics", "carol_calendar.ics")
EMAILS = ("alice@example.com", "bob@example.com", "carol@example.com")


def events(path):
    text = open(path).read()
    out = []
    for block in re.findall(r"BEGIN:VEVENT.*?END:VEVENT", text, re.S):
        s = re.search(r"DTSTART:(\d{8}T\d{6}Z)", block)
        e = re.search(r"DTEND:(\d{8}T\d{6}Z)", block)
        if s and e:
            out.append((datetime.strptime(s.group(1), "%Y%m%dT%H%M%SZ"),
                        datetime.strptime(e.group(1), "%Y%m%dT%H%M%SZ"), block))
    return out


def valid(t0, busy, carol, bob_start):
    t1 = t0 + timedelta(hours=1)
    minutes0 = t0.hour * 60 + t0.minute
    minutes1 = t1.hour * 60 + t1.minute
    if t0.weekday() >= 5 or t1.date() != t0.date():
        return False
    if minutes0 < 9 * 60 or minutes1 > 14 * 60:  # Alice
        return False
    if bob_start and minutes0 < 10 * 60:  # Bob
        return False
    if t0.weekday() in (1, 3) and minutes1 > 16 * 60 + 30:
        return False
    if minutes1 > 17 * 60:  # Carol
        return False
    if minutes0 < 12 * 60 + 30 and minutes1 > 12 * 60:  # Carol's lunch
        return False
    if any(t0 < b1 and t1 > b0 for b0, b1, _ in busy):
        return False
    for b0, b1, _ in carol:  # Carol's buffer after meetings ending 16:45 or later
        late = b1.hour * 60 + b1.minute >= 16 * 60 + 45
        if late and t0 < b1 + timedelta(minutes=15) and t1 > b1:
            return False
    if minutes1 >= 16 * 60 + 45:
        if any(t1 < b1 and t1 + timedelta(minutes=15) > b0 for b0, b1, _ in carol):
            return False
    return True


def earliest(busy, carol, bob_start):
    all_valid = []
    t = datetime(2024, 1, 15, 9)
    while t < datetime(2024, 1, 19, 18):
        if valid(t, busy, carol, bob_start):
            all_valid.append(t)
        t += timedelta(minutes=1)
    if not all_valid:
        return None
    first = all_valid[0]
    # Among slots at the same time of day, avoid Monday.
    same = [u for u in all_valid if (u.hour, u.minute) == (first.hour, first.minute)]
    non_monday = [u for u in same if u.weekday() != 0]
    return first if first.weekday() != 0 or not non_monday else non_monday[0]


def fold(line):
    out = []
    while len(line.encode()) > 75:
        out.append(line[:75])
        line = " " + line[75:]
    out.append(line)
    return out


def render(start, style, existing):
    end = start + timedelta(hours=1)
    stamp = "%Y%m%dT%H%M%S" + ("" if style == "floating" else "Z")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SecureBench mutant//Scheduler//EN"]
    if style == "merged":
        for _, _, block in existing:
            lines += block.splitlines()
    lines += [
        "BEGIN:VEVENT",
        "UID:team-planning@example.com",
        "DTSTAMP:20240101T000000Z" if style != "floating" else "DTSTAMP:20240101T000000",
        "DTSTART:" + start.strftime(stamp),
        "DTEND:" + end.strftime(stamp),
        "SUMMARY:Team Planning Meeting",
    ]
    for email in EMAILS:
        if style == "crlf-params":
            lines.append(f"ATTENDEE;CN={email};ROLE=REQ-PARTICIPANT;RSVP=TRUE:MAILTO:{email.upper()}")
        elif style == "folded":
            name = email.split("@")[0].title()
            lines += fold(f"ATTENDEE;CN={name};ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{email}")
        else:
            lines.append(f"ATTENDEE:MAILTO:{email}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    newline = "\r\n" if style in ("crlf-params", "folded") else "\n"
    return newline.join(lines) + newline


def main(argv):
    bob_start = "--no-bob-start" not in argv
    style = argv[argv.index("--style") + 1] if "--style" in argv else "plain"
    calendars = [events(f"/app/{name}") for name in NAMES]
    busy = [e for cal in calendars for e in cal]
    start = earliest(busy, calendars[2], bob_start)
    if start is None:
        raise SystemExit("no slot")
    with open("/app/meeting_scheduled.ics", "w", newline="") as f:
        f.write(render(start, style, busy))
    print("scheduled", start)


if __name__ == "__main__":
    main(sys.argv[1:])
