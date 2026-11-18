"""Oracle for terminal-bench/fix-ocaml-gc.

One case runs upstream's `make -C testsuite one DIR=tests/basic` and then every
command ocamltest runs for the 40 tests of testsuite/tests/basic. The judge
requires what upstream's test asserts (the testsuite prints "40 tests passed")
and, because that line is printed by the candidate's own ocamltest, also every
check ocamltest makes for those tests, recomputed here from the raw outputs:
exit statuses, compiler and program outputs against the reference files, and
the bytecode comparison tools/cmpbyt makes.
"""

import binascii

from securebench.core.evidence import CaseEvidence, Judgment, Observed, Plan, Case, HiddenResources
from securebench.core.jsondata import JsonValue

CHECK = "basic-testsuite"
FILE_CAP = 10240
SUMMARY_CAP = 65536
DBUG = b"DBUG".hex()
MAX_REPORTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    references = {}
    for name in cases["references"]:
        references[name] = resources.read("reference/" + name).decode("utf-8")
    challenge = {"summary": {"dir": cases["summary"]["dir"], "argv": cases["summary"]["argv"]}, "steps": cases["steps"]}
    context = {
        "expected_substring": cases["summary"]["expected_substring"],
        "expectations": cases["expectations"],
        "references": references,
    }
    return Plan(artifact_contexts={}, cases={CHECK: (Case(challenge, context),)})


def decode(value, cap):
    """Bytes of a reported file, or None when it is malformed or was cut at the cap."""
    if not isinstance(value, dict):
        return None
    size, text = value.get("size"), value.get("content_b64")
    if not isinstance(size, int) or isinstance(size, bool) or not isinstance(text, str):
        return None
    try:
        data = binascii.a2b_base64(text.encode("ascii"), strict_mode=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return None
    if size > cap or size != len(data):
        return None
    return data


def ocaml_lines(data, normalise):
    """The line sequence ocamltest's Filecompare.line_seq_of_in_channel builds, or None where it raises Exit."""
    parts = data.split(b"\n")
    terminated = parts[:-1]
    last = parts[-1]
    lines = []
    for line in terminated:
        if normalise:
            if not line.endswith(b"\r"):
                return None
            line = line[:-1]
        lines.append(line + b"\n")
    if last:
        lines.append(last)
    return lines


def same_text(reference, output):
    """ocamltest's Filecompare.compare_text_files with no ignored lines: equal up to a uniform CRLF/LF difference."""
    if output == b"":
        return reference == b""
    if reference == b"":
        return False
    crlf_reference = reference.split(b"\n", 1)[0].endswith(b"\r")
    crlf_output = output.split(b"\n", 1)[0].endswith(b"\r")
    left = ocaml_lines(reference, crlf_reference and not crlf_output)
    right = ocaml_lines(output, crlf_output and not crlf_reference)
    return left is not None and right is not None and left == right


def valid_toc(toc):
    if not isinstance(toc, dict) or not isinstance(toc.get("magic_hex"), str):
        return False
    sections = toc.get("sections")
    if not isinstance(sections, list):
        return False
    for section in sections:
        if not isinstance(section, dict):
            return False
        if not isinstance(section.get("name_hex"), str) or len(section["name_hex"]) != 8:
            return False
        if not isinstance(section.get("length"), int) or not isinstance(section.get("sha256"), str):
            return False
    return len(toc["magic_hex"]) == 24


def same_bytecode(left, right, magic):
    """tools/cmpbyt: both trailers carry the build's exec magic number, and the
    same sections appear in the same order with the same contents, DBUG sections ignored."""
    if not valid_toc(left) or not valid_toc(right):
        return False
    if left["magic_hex"] != magic or right["magic_hex"] != magic:
        return False

    def kept(toc):
        return [(s["name_hex"], s["length"], s["sha256"]) for s in toc["sections"] if s["name_hex"] != DBUG]

    return kept(left) == kept(right)


def check(expectation, results, references):
    kind = expectation.get("kind")
    if kind == "same_bytecode":
        left, right = results.get(expectation["left"]), results.get(expectation["right"])
        if left is None or right is None:
            return "program missing from the observation"
        if same_bytecode(left.get("toc"), right.get("toc"), expectation["magic"].encode("ascii").hex()):
            return None
        return "bytecode programs differ or are not readable bytecode executables"
    result = results.get(expectation.get("step"))
    if result is None:
        return "step missing from the observation"
    if kind == "exit":
        if result.get("timed_out") is not False:
            return "timed out"
        returncode = result.get("returncode")
        if not isinstance(returncode, int) or isinstance(returncode, bool):
            return "command could not be started"
        if returncode != expectation["returncode"]:
            return f"exit status {returncode}, expected {expectation['returncode']}"
        return None
    data = decode(result.get("file"), FILE_CAP)
    if data is None:
        return "output missing or longer than any expected output"
    if kind == "empty":
        return None if data == b"" else "output should be empty"
    if kind == "text":
        reference = references[expectation["reference"]].encode("utf-8")
        return None if same_text(reference, data) else f"output differs from {expectation['reference']}"
    return "unknown expectation"


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})

    failures = []
    summary = observation.get("summary")
    stdout = None
    if isinstance(summary, dict) and summary.get("timed_out") is False:
        stdout = summary.get("stdout")
        if isinstance(stdout, dict) and stdout.get("size") == SUMMARY_CAP + 1:
            # The adapter kept the last SUMMARY_CAP bytes; the summary is printed last.
            stdout = dict(stdout, size=SUMMARY_CAP)
        stdout = decode(stdout, SUMMARY_CAP)
    if stdout is None or context["expected_substring"].encode("utf-8") not in stdout:
        failures.append({"what": "make -C testsuite one DIR=tests/basic", "reason": "summary does not say all 40 tests passed"})

    results = {}
    reported = observation.get("results")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "results missing"})
    for result in reported:
        if not isinstance(result, dict) or not isinstance(result.get("id"), str):
            return Judgment(False, {"reason": "malformed result"})
        if result["id"] in results:
            return Judgment(False, {"reason": "duplicate result", "id": result["id"]})
        results[result["id"]] = result

    failed_count = len(failures)
    for expectation in context["expectations"]:
        reason = check(expectation, results, context["references"])
        if reason is not None:
            failed_count += 1
            if len(failures) < MAX_REPORTED_FAILURES:
                failures.append({"what": expectation["what"], "reason": reason})
    if failed_count:
        return Judgment(False, {"failed_checks": failed_count, "first_failures": failures})
    return Judgment(True, {"checks": len(context["expectations"]) + 1})
