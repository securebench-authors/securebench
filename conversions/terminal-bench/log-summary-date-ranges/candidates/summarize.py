"""Shared by the mutants: counts severities per period, then writes /app/summary.csv
in the style each mutant names. Every style but `substring` counts correctly."""

import csv
import datetime
import os
import sys

STYLE = sys.argv[1]
TODAY = datetime.date(2025, 8, 12)
PERIODS = [
    ("today", TODAY),
    ("last_7_days", TODAY - datetime.timedelta(days=6)),
    ("last_30_days", TODAY - datetime.timedelta(days=29)),
    ("month_to_date", TODAY.replace(day=1)),
    ("total", None),
]
SEVERITIES = ["ERROR", "WARNING", "INFO"]

counts = {(period, sev): 0 for period, _ in PERIODS for sev in SEVERITIES}
for name in os.listdir("/app/logs"):
    day = datetime.date.fromisoformat(name.split("_", 1)[0])
    with open(os.path.join("/app/logs", name), encoding="utf-8") as handle:
        lines = handle.readlines()
    for sev in SEVERITIES:
        # `substring` falls into the task's trap: WARNING lines that mention ERROR.
        needle = sev if STYLE == "substring" else f"[{sev}]"
        hits = sum(1 for line in lines if needle in line)
        for period, start in PERIODS:
            if start is None or start <= day <= TODAY:
                counts[(period, sev)] += hits

rows = [["period", "severity", "count"]]
rows += [[period, sev, str(counts[(period, sev)])] for period, _ in PERIODS for sev in SEVERITIES]

if STYLE == "csv-writer":
    # csv.writer's default line terminator is "\r\n".
    with open("/app/summary.csv", "w", newline="", encoding="utf-8") as out:
        csv.writer(out).writerows(rows)
elif STYLE == "quote-all":
    # Every field quoted, and no newline after the last row.
    text = "\n".join(",".join(f'"{field}"' for field in row) for row in rows)
    with open("/app/summary.csv", "w", newline="", encoding="utf-8") as out:
        out.write(text)
elif STYLE == "blank-line":
    text = "".join(",".join(row) + "\n" for row in rows) + "\n"
    with open("/app/summary.csv", "w", newline="", encoding="utf-8") as out:
        out.write(text)
elif STYLE == "bom":
    with open("/app/summary.csv", "w", newline="", encoding="utf-8-sig") as out:
        out.write("".join(",".join(row) + "\n" for row in rows))
elif STYLE == "substring":
    with open("/app/summary.csv", "w", newline="", encoding="utf-8") as out:
        out.write("".join(",".join(row) + "\n" for row in rows))
else:
    sys.exit(f"unknown style {STYLE}")
