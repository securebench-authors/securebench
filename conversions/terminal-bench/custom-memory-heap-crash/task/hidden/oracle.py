"""Oracle for custom-memory-heap-crash.

Upstream's five tests, as checks. Every expected value and every challenge is
in hidden/cases.json; this file holds only how to compare.

- `protected-files`: test_protected_files_not_modified. The MD5 of /app/main.cpp
  and /app/user.h equals upstream's constants. The text parser accepts only
  strict UTF-8 without a byte-order mark, so encoding the parsed text gives
  back the file's bytes; a file it cannot parse is not the UTF-8 original, so
  it fails here and upstream alike.
- `debug`, `release`, `valgrind`: test_program_compiles_debug and
  test_program_compiles_release (the compile of each check), then
  test_debug_build_runs_without_crash, test_release_build_runs_without_crash
  and test_no_memory_leaks_with_valgrind. The compile exits 0 and leaves the
  executable; the run ends within upstream's timeout with upstream's exit
  status; the compiler's and the run's output decode as UTF-8, as upstream's
  `text=True` requires.
"""

import hashlib

from securebench.core.errors import Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

PROTECTED = ("/app/main.cpp", "/app/user.h")
RUNS = ("debug", "release", "valgrind")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or sorted(data) != sorted(("protected-files", *RUNS)):
        raise Rejected("hidden/cases.json is malformed")
    protected = data["protected-files"]
    listed = protected.get("md5") if isinstance(protected, dict) else None
    if not isinstance(listed, dict) or sorted(listed) != sorted(PROTECTED):
        raise Rejected("hidden/cases.json is malformed")
    if not all(isinstance(digest, str) for digest in listed.values()):
        raise Rejected("hidden/cases.json is malformed")
    cases: dict[str, tuple[Case, ...]] = {}
    for run in RUNS:
        entries = data[run]
        if not isinstance(entries, list) or not entries:
            raise Rejected("hidden/cases.json is malformed")
        built = []
        for entry in entries:
            if not isinstance(entry, dict) or sorted(entry) != ["challenge", "exit_status"]:
                raise Rejected("hidden/cases.json is malformed")
            status = entry["exit_status"]
            if not isinstance(status, int) or isinstance(status, bool):
                raise Rejected("hidden/cases.json is malformed")
            built.append(Case(entry["challenge"], {"exit_status": status}))
        cases[run] = tuple(built)
    return Plan(artifact_contexts={"protected-files": {"md5": listed}}, cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    if check_id == "protected-files" and isinstance(evidence, ArtifactEvidence):
        return _protected(context, evidence)
    if check_id in RUNS and isinstance(evidence, CaseEvidence):
        return _run(context, evidence)
    return Judgment(False, {"reason": "unexpected check"})


def _protected(context: dict[str, JsonValue], evidence: ArtifactEvidence) -> Judgment:
    md5 = context.get("md5")
    if not isinstance(md5, dict) or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    if tuple(found.path for found in evidence.files) != PROTECTED:
        return Judgment(False, {"reason": "unexpected evidence"})
    for found in evidence.files:
        if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
            reason = f"{found.path} is {found.status.value}"
            return Judgment(False, {"reason": reason, "detail": found.reason})
        actual = hashlib.md5(found.value.text.encode("utf-8")).hexdigest()
        if actual != md5.get(found.path):
            return Judgment(False, {"reason": f"{found.path} has been modified", "md5": actual})
    return Judgment(True, None)


def _run(context: dict[str, JsonValue], evidence: CaseEvidence) -> Judgment:
    expected = context.get("exit_status")
    if not isinstance(expected, int) or isinstance(expected, bool):
        return Judgment(False, {"reason": "malformed context"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    seen = evidence.outcome.value
    if not isinstance(seen, dict):
        return Judgment(False, {"reason": "malformed observation"})
    built = seen["compile_exit_status"] == 0 and seen["executable"] is True
    if seen["compile_timed_out"] is not False or not built:
        return Judgment(False, {
            "reason": "the build failed",
            "compile_exit_status": seen["compile_exit_status"],
            "compile_timed_out": seen["compile_timed_out"],
            "executable": seen["executable"],
            "compile_output": seen["compile_output"],
        })
    if seen["compile_utf8"] is not True:
        return Judgment(False, {"reason": "the compiler's output is not valid UTF-8"})
    if seen["ran"] is not True or seen["timed_out"] is not False:
        return Judgment(False, {"reason": "the program did not run to its end in time"})
    if seen["exit_status"] != expected:
        return Judgment(False, {
            "reason": "the run did not exit as upstream requires",
            "exit_status": seen["exit_status"],
            "run_output": seen["run_output"],
        })
    # Upstream decodes standard output and standard error with text=True, so
    # invalid UTF-8 in either fails its test.
    if seen["utf8"] is not True:
        return Judgment(False, {"reason": "the program's output is not valid UTF-8"})
    return Judgment(True, None)
