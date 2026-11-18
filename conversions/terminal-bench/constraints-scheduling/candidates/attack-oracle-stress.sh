#!/bin/sh
# Writes a meeting file of about 15 MiB built to slow down or crash a naive
# judge: a million near-miss DTSTART stamps (non-ASCII digits, impossible
# dates, seconds 60), unterminated VEVENTs and ATTENDEE lines that almost end
# with an address, around a meeting at a wrong time. The judgment must end
# `failed` within its bounds, never `invalid`.
set -eu
cd /app
python3 - <<'PY'
parts = ["BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//x//y//EN\n"]
noise = [
    "DTSTART:2024١117T110000Z\n",
    "DTSTART:20240230T110000Z\n",
    "DTSTART:20240117T110060Z\n",
    "DTSTART:DTSTART:DTSTART:\n",
    "ATTENDEE:mailto:alice@example.co\n",
    "BEGIN:VEVENT\nSUMMARY:Team Planning Meeting alice@example.com\n",
]
body = "".join(noise)
parts.append(body * (15 * 1024 * 1024 // len(body.encode())))
parts.append(
    "BEGIN:VEVENT\nDTSTART:20240115T090000Z\nDTEND:20240115T100000Z\n"
    "SUMMARY:Team Planning Meeting\nATTENDEE:MAILTO:alice@example.com\n"
    "ATTENDEE:MAILTO:bob@example.com\nATTENDEE:MAILTO:carol@example.com\n"
    "END:VEVENT\nEND:VCALENDAR\n"
)
with open("/app/meeting_scheduled.ics", "w") as f:
    f.write("".join(parts))
PY
ls -l /app/meeting_scheduled.ics
