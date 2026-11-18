# constraints-scheduling

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/constraints-scheduling

## How the pack grades

The agent writes `/app/meeting_scheduled.ics` next to the three input
calendars. Upstream's verifier (`tests/test_outputs.py`) reads that file and the
calendars under `/app` and has three tests. The pack has four artifact checks
and no protocol check, since nothing has to run: every assertion is about the
text of four files.

| Check | Files read | Upstream assertions |
|---|---|---|
| `inputs-unchanged` | the three `/app/*_calendar.ics` | the integrity loop at the top of `test_structure_event_title_attendees_duration_window`: each calendar, read with `Path.read_text()`, has the digest in `_EXPECTED_SHA256` |
| `structure` | `/app/meeting_scheduled.ics` | the rest of that test: the stripped text starts with `BEGIN:VCALENDAR` and ends with `END:VCALENDAR`; it contains `VERSION:2.0`, `PRODID:`, `BEGIN:VEVENT`, `END:VEVENT`; the first VEVENT holding `SUMMARY:Team Planning Meeting` and the three addresses has an `ATTENDEE` line ending with each address (case-insensitive); its first `DTSTART`/`DTEND` are one hour apart, on a weekday of January 15-19, 2024 |
| `constraints` | `/app/meeting_scheduled.ics` | `test_constraints_conflicts_business_hours`: the first `DTSTART` of the whole file, with an end one hour later, satisfies `_hard_ok` and overlaps no event of the three calendars |
| `earliest` | `/app/meeting_scheduled.ics` | `test_earliest_tiebreakers_and_carol_buffer`: no valid slot at any whole minute from 2024-01-15 09:00 up to that `DTSTART`; the Monday tie-breaker; `9 <= hour < 12`; both of Carol's late-buffer loops |

The attempt passes only if all four checks pass, as upstream's reward needs all
three tests to pass.

`hidden/spec.json` holds every literal these tests compare with (header
strings, the summary, the addresses, the date window, the scan window).
`hidden/calendars.json` holds each calendar's digest and its busy intervals,
derived from the upstream input files by `hidden/derive.py` with upstream's own
regular expressions; the script also asserts that the digests equal the ones
upstream's test hard-codes. `hidden/oracle.py` contains only judging logic:
upstream's `_hard_ok` transliterated condition by condition, the overlap
test, the minute scan and the tie-breaker loop. With the upstream calendars,
the only `DTSTART` that passes `constraints` and `earliest` together inside
the week is 2024-01-17 11:00:00 (Wednesday), which is what the upstream
reference writes; it does not appear in the Oracle.

## Reimplemented native tools

An Oracle may not apply regular expressions to evidence or import `datetime`,
so the Oracle repeats upstream's `re` and `datetime` calls with string and
integer code:

- `Path.read_text()`: UTF-8, strict, with universal newlines. SecureBench's
  text parser decodes strict UTF-8; the Oracle then turns `\r\n` and lone `\r`
  into `\n`. The verifier's Python runs in UTF-8 mode (the image has no
  locale; `sys.flags.utf8_mode` is 1 there), so its decoding is the same.
- `re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", c, re.S)`: `str.find` from each
  `BEGIN:VEVENT` to the first `END:VEVENT` after it.
- `re.search(rf"^ATTENDEE[:;].*{email}$", meeting, re.I | re.M)`: split on
  `\n`, compare the head and the tail of each line. `re.IGNORECASE` matches
  an ASCII letter also with U+0130/U+0131 (for `i`), U+017F (`s`) and U+212A
  (`k`); the Oracle's character table is checked against `re` on every code
  point.
- `re.search(r"DTSTART:(\d{8}T\d{6}Z)")` and `datetime.strptime(...,
  "%Y%m%dT%H%M%SZ")`: the leftmost `DTSTART:` followed by the shape, where
  `\d` is any Unicode decimal digit as in `re`; then the field patterns of
  `_strptime` (only some positions accept non-ASCII digits) and the range
  checks of `datetime()` (year 0, impossible days, seconds 60 and 61 fail).
  If the leftmost match does not parse, the test fails, as upstream's does;
  a later stamp is not tried.
- `datetime` arithmetic: seconds since the proleptic Gregorian epoch of
  `date.toordinal()`, `weekday()`, `replace(hour=12, minute=0)` keeping the
  seconds, and the overflow of `datetime.max`.

We compared the Oracle with upstream's test functions run by Python 3.13 (the
version upstream's `test.sh` installs) in a `python:3.13-slim` container:
`\d` against `str.isdecimal` and the case table against `re.I` on all
1,114,112 code points; `_ymd`/`_ordinal`/`_weekday` against `date` on about
66,000 ordinals across the whole range; `_strptime` against
`datetime.strptime` on 300,000 random stamps, 15% of the digits non-ASCII;
and the three checks against the three tests on about 13,000 meeting files:
every whole-minute start from January 14 to 20, starts with seconds, wrong
durations, other years including 0001 and 9999, decoy DTSTARTs before the
meeting, CR and CRLF line endings, attendee variants (parameters, upper
case, U+0130 and U+212A in addresses, missing separator, trailing space),
leading and trailing Unicode whitespace, a byte-order mark, invalid UTF-8,
non-ASCII digits, nested and unterminated VEVENTs, folded lines and 3,000
random byte mutations of a correct file (13,151 files, 666 of which upstream
passes); plus edits to a calendar. Every attempt verdict agreed, and so did
every per-test verdict except for the file with a byte-order mark: there
upstream's `structure` test fails while its other two pass, and the pack fails
all three checks because the parser rejects the file. The attempt fails in
both. The script is not part of the pack; a reviewer can redo the
comparison by calling upstream's test functions and `judge` on the same files.

## Fidelity changes

- **Calendar integrity: stricter in one direction, more lenient in the
  other.** Upstream compares each `/app` calendar with
  `/tests/../inputs/<name>` when that file exists, and only otherwise with its
  hard-coded digests. The pack always compares with upstream's digests, and
  nothing outside `/app` is captured. `/inputs` is not among the task's
  deliverables, and the instructions define integrity by the `/app` files
  alone ("Do not modify `/app/alice_calendar.ics`, ..."), so the pack judges
  only those.
  - Stricter: `/inputs` does not exist in the image, but the agent runs as
    root and can create it, edit the calendars, copy them there, and have the
    later tests judge against the edited calendars (`attack-forge-inputs`).
    Upstream passes this and the pack fails it.
  - More lenient: a candidate that leaves the `/app` calendars untouched but
    leaves an `/inputs/<calendar>` that differs from them, or that is a
    directory or unreadable, fails upstream's integrity check (or crashes it)
    and passes the pack.
- **Calendars for conflicts and the scan: equivalent.** Upstream's
  `constraints` and `earliest` tests read the calendars from `/app`; the pack
  uses the busy intervals derived from the upstream inputs. Whenever
  `inputs-unchanged` passes, the `/app` calendars have exactly these
  intervals, so the verdict is the same (apart from the `/inputs` route
  above).
- **Scope: equivalent, apart from stricter capture residuals.** The scope is `/app`
  with everything inside its subdirectories excluded (`*/*`). Only the four
  files directly in `/app` are graded, so dropping the rest changes no
  verdict, and it keeps a virtual environment or scratch tree, whose absolute
  symlinks capture rejects, from failing an otherwise correct attempt.
  Symlinks are allowed but capture only relative ones that stay inside
  `/app`.
  Capture still refuses some states that upstream ignores. These are stricter
  residuals; no scope can avoid them, and we know of no real solution that
  leaves them. The capture walk runs without `CAP_DAC_OVERRIDE`. It lists every
  first-level subdirectory of `/app` and checks each entry's name before it
  applies the exclude (`securebench_utility/utility.py`, `walk_root`). So
  each of the following ends the attempt `failed`, class `capture`, while
  upstream, which runs as root and reads only the four graded files, can pass:
  - a file directly in `/app` that its mode makes unreadable. The reviewer
    confirmed this case with a run: upstream's solution followed by
    `chmod 000 /app/notes.txt` ended `failed capture` ("... notes.txt cannot
    be read"), and upstream passes it;
  - a first-level subdirectory of `/app` that cannot be listed;
  - an entry, directly in `/app` or inside a first-level subdirectory, whose
    name is not valid UTF-8 or contains a backslash;
  - a device, socket or named pipe directly in `/app`;
  - an absolute symlink directly in `/app` (next bullet).
- **The output as a symlink: stricter.** If `/app/meeting_scheduled.ics` or a
  calendar is a symlink, upstream reads through it; the artifact check reports
  `not_regular` and the Oracle fails it. An absolute symlink directly in
  `/app` fails capture. The instructions ask for the agent to "create" the
  file, and we know of no solution that leaves a symlink.
- **File size: stricter.** The meeting file is read up to 16 MiB, the largest
  bound an artifact check allows, and each calendar up to 64 KiB. A larger
  meeting file fails; upstream would read it. A larger calendar fails both
  graders because it cannot have the original digest.
- **Byte-order mark: equivalent.** SecureBench's text parser rejects a file
  that starts with a byte-order mark. Upstream's `read_text()` keeps it as
  U+FEFF, which `str.strip()` does not remove, so `startswith("BEGIN:VCALENDAR")`
  fails, and a calendar with one no longer has its digest.
- **Python version: equivalent.** The Oracle runs on the host's Python 3.12,
  upstream's tests on Python 3.13. `str.strip()`, `str.isdecimal()` and the
  case table depend on the Unicode database of the version; we found no
  difference on the code points above.
- **Instructions, cases, domains: unchanged.** `instructions.md` is upstream's
  `instruction.md` byte for byte. Upstream has no network requirement at
  grading time and the reference needs none, so `allowed_domains` is empty.
  The seed is unused, as upstream's tests draw no random values.

## Upstream weakness kept

Upstream's `constraints` and `earliest` tests judge the first `DTSTART` of the
whole file, while only `structure` looks at the meeting VEVENT, and it checks
just the week and the duration. A file whose first `DTSTART` is a decoy
(for example a 2023 weekday at 11:00 in an extra VEVENT) therefore passes all
three tests with the meeting itself at any weekday hour of January 15-19.
Making the pack read the meeting's own `DTSTART` would be a stricter check
than upstream's, so the pack keeps upstream's behavior. `mutant-merged`
exercises the same rule from the other side: a file that repeats the existing
events before the meeting fails both graders, because its first `DTSTART`
conflicts.

## Candidates

- `reference.sh` runs upstream's `solution/solve.sh`, kept byte for byte as
  `upstream-solve.bash`, with bash from `/app`.
- `null.sh` changes nothing.
- `scheduler.py` is a correct minute-granularity scheduler with output styles;
  the mutants and `attack-forge-inputs` use it.
- `mutant-no-bob-start` drops Bob's 10 AM rule and schedules Tuesday 09:00
  (aimed at the transliterated `_hard_ok` and the scan).
- `mutant-crlf-params` writes the right slot with CRLF line endings, ATTENDEE
  parameters and upper-case `MAILTO:` addresses (aimed at the newline
  translation and the case-insensitive match; upstream passes it).
- `mutant-folded` writes the right slot with RFC 5545 line folding, which
  splits the ATTENDEE lines (aimed at the line splitting).
- `mutant-merged` repeats the existing events before the meeting (aimed at
  which `DTSTART` the Oracle reads).
- `mutant-floating` writes floating times without `Z` (aimed at the stamp
  search and `strptime`).
- `attack-forge-inputs` edits Alice's calendar, copies the edited calendars to
  `/inputs` and schedules the freed Monday 10:00 slot.
- `attack-oracle-stress` writes a 15 MiB file of near-miss stamps,
  unterminated VEVENTs and almost-matching ATTENDEE lines around a wrong
  meeting; the judgment must stay bounded and end `failed`.

## Divergences from native

- `attack-forge-inputs`: native reward 1.0, SecureBench `failed` (class
  `oracle`, "Input modified: alice_calendar.ics"). SecureBench is right. The
  candidate deletes one of Alice's meetings and copies the edited calendars to
  `/inputs`, which upstream's integrity check prefers over its hard-coded
  digests; upstream then judges the freed Monday 10:00 slot against the
  edited calendars. The instructions forbid modifying the calendars, and the
  meeting overlaps Alice's real Monday 10:00 meeting.

Every other candidate gets the same verdict from both graders: the reference
passes both; `null`, `mutant-no-bob-start`, `mutant-folded`, `mutant-merged`,
`mutant-floating` and `attack-oracle-stress` fail both; `mutant-crlf-params`
passes both.


## Review

Reviewer: a3ec7a88b4d5371da, 2026-10-26 (second review, after the converter addressed the first review's findings)

Pack digest at review: `sha256:74ebb9ca414a8958e16d9d86dc332618e39c944490d895edfc63b90cb5232d10` (`securebench validate`). It is the same digest as in the first review. Only `CONVERSION.md` changed: `task/`, `candidates/` and `qualification.json` are unchanged.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. One root `/app`, with `exclude = ["*/*"]`. Under the component-wise matching rules this drops every path with two or more components, so only entries directly in `/app` are captured. The baseline `/app` holds only the three calendars: no symlinks, no tests, no convention-loaded files, and no `/inputs` or `/tests` in the image. Upstream's tests live outside `/app`, so a candidate cannot rewrite them. The capture residuals that no scope can avoid are now recorded under "Scope". I checked each against `securebench_utility/utility.py` (`walk_root`, `check_name`) and the capture environment (no capabilities). Each holds: an unreadable file directly in `/app` (my run confirmed it: `failed capture`); an unlistable first-level subdirectory; an invalid or backslash name directly in `/app` or one level down; a device, socket or FIFO directly in `/app`; an absolute symlink directly in `/app`.
3. No expected value leaks. There is no `public/` and no `evaluation/`. `hidden/` holds the literals of upstream's tests (`spec.json`) and the calendars' digests and busy intervals (`calendars.json`). I recomputed `calendars.json` from the upstream inputs with upstream's regular expressions, and the digests and intervals match. The baseline image's calendars have upstream's digests. The answer (Wednesday 11:00) follows from the public calendars, which is the task itself, and it appears nowhere in the pack. No candidate-writable file feeds an expected value. No domains are allowed.
4. Challenges. There are no protocol checks, so there are no challenges.
5. Cases. Four artifact checks: `inputs-unchanged` plus `structure` together cover upstream's first test, `constraints` the second and `earliest` the third. No assertion was added. The seed is unused, and upstream draws no random values.
6. Oracle. Unchanged since the first review. The only literals in `oracle.py` are the rules and thresholds of upstream's `_hard_ok`, the tie-breaker and the buffer. Every comparison literal comes from `hidden/`. Over candidate data the work is linear, and the scan is bounded. Failures always come back as judgments. My differential test in `python:3.13-slim`, with upstream's three test functions against `judge` on 1,598 meeting files and 12 calendar edits, agreed on every attempt verdict. The only per-test difference is the byte-order mark case, which is recorded. The `re.I` table matches `_ichar` on every code point.
7. Candidates. Unchanged. `reference.sh` runs upstream's `solve.sh` byte for byte, adding only `cd /app` and `bash`. `null.sh` changes nothing. Each of the five mutants runs the real `scheduler.py` and targets a reimplemented piece. `attack-forge-inputs` is specific to this task, and `attack-oracle-stress` exercises the bounds.
8. Divergences. `qualification.json` reports no problems. All nine SecureBench runs are admitted and rejudged, on the digest above, at a clean framework commit. The one divergence, `attack-forge-inputs` (native 1.0, SecureBench `failed`), is explained correctly.
9. Inventory. There is no row yet in `conversions/inventory.tsv`, which is the coordinator's to add (`converted`, `-`). No exclusion reason applies.

Upstream assertions: each one in the three tests maps to a check. None is dropped.

First review's findings:
- The calendar integrity bullet is now labelled "stricter in one direction, more lenient in the other". It describes both the `attack-forge-inputs` route and a differing, directory or unreadable `/inputs/<calendar>`, and gives the reason (`/inputs` is not a deliverable, and the instructions define integrity by the `/app` files). Fixed.
- The scope bullet now lists the capture residuals as stricter, with the mechanism and the confirming run. Fixed.

Findings:
- None.

Verdict: approved
