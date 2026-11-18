"""Reads /app/summary.csv exactly as upstream's test does and reports the rows.

Upstream's test runs `list(csv.reader(f))` on the file opened with `newline=""`
under Python 3.13 in UTF-8 mode. This adapter runs on the baseline's own
Python 3.13 (outside the scope, so the candidate cannot change it), with the
encoding spelled out so the result does not depend on the locale.
"""

import csv
import json
import sys


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


sys.stdin.read()
try:
    with open("/app/summary.csv", "r", encoding="utf-8", errors="strict", newline="") as handle:
        rows = list(csv.reader(handle))
except FileNotFoundError:
    unable("absent", "/app/summary.csv does not exist")
except UnicodeDecodeError as error:
    unable("not-utf8", str(error))
except csv.Error as error:
    unable("csv-error", str(error))
except OSError as error:
    unable("unreadable", str(error))
print(json.dumps({"observation": {"rows": rows}}))
