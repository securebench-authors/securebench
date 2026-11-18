"""Oracle for gpt2-codegolf.

Upstream's single test asserts, in order: /app/gpt2.c exists and is smaller
than 5000 bytes; `gcc -O3 /app/gpt2.c -lm` exits 0; `/app/a.out ...` exits 0
within 90 seconds; and its stdout contains the expected continuation. Its
`subprocess.run(..., text=True)` calls also fail the test when any captured
stream is not strict UTF-8. The size and expected text live in
hidden/cases.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
    Ending,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    cases = tuple(
        Case(challenge=entry["challenge"], context={"expected_substring": entry["expected_substring"]})
        for entry in data["generate"]
    )
    return Plan(artifact_contexts={"source": data["source"]}, cases={"generate": cases})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "source" and isinstance(evidence, ArtifactEvidence):
        return judge_source(context, evidence)
    if check_id == "generate" and isinstance(evidence, CaseEvidence):
        return judge_generate(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def judge_source(context, evidence):
    if len(evidence.files) != 1 or evidence.files[0].path != context["path"]:
        return Judgment(False, {"reason": "unexpected file evidence"})
    found = evidence.files[0]
    # The C file need not be UTF-8 for gcc, so an unparsable text file still has a size to judge.
    if found.status not in (FileStatus.PRESENT, FileStatus.UNPARSABLE) or not isinstance(found.size, int):
        return Judgment(False, {"reason": f"{found.path} is {found.status.value}"})
    if found.size >= context["size_below"]:
        return Judgment(False, {"reason": "source too large", "size": found.size, "limit": context["size_below"]})
    return Judgment(True, {"size": found.size})


def judge_generate(context, evidence):
    if evidence.facts.ending is not Ending.RETURNED or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the case did not return an observation", "ending": evidence.facts.ending.value})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    compiled = observation.get("compile")
    if not isinstance(compiled, dict):
        return Judgment(False, {"reason": "no compile record"})
    if compiled.get("exit_status") != 0:
        return Judgment(False, {"reason": "compilation failed", "exit_status": compiled.get("exit_status"), "stderr": tail(compiled.get("stderr"))})
    if compiled.get("stdout_utf8") is not True or compiled.get("stderr_utf8") is not True:
        return Judgment(False, {"reason": "compiler output is not UTF-8, which upstream's test cannot decode"})
    run = observation.get("run")
    if not isinstance(run, dict):
        return Judgment(False, {"reason": "no run record"})
    if run.get("timed_out") is not False:
        return Judgment(False, {"reason": "program timed out"})
    if run.get("exit_status") != 0:
        return Judgment(False, {"reason": "program failed", "exit_status": run.get("exit_status"), "stderr": tail(run.get("stderr"))})
    if run.get("stdout_utf8") is not True or run.get("stderr_utf8") is not True:
        return Judgment(False, {"reason": "program output is not UTF-8, which upstream's test cannot decode"})
    stdout = run.get("stdout")
    if not isinstance(stdout, str):
        return Judgment(False, {"reason": "no stdout"})
    # text=True applies universal newlines before upstream's `in` test.
    text = stdout.replace("\r\n", "\n").replace("\r", "\n")
    if context["expected_substring"] in text:
        return Judgment(True, {"stdout": tail(stdout)})
    if run.get("stdout_truncated") is not False:
        return Judgment(False, {"reason": "expected text not in the kept prefix of an over-long stdout"})
    return Judgment(False, {"reason": "wrong output", "stdout": tail(stdout)})


def tail(value):
    if not isinstance(value, str):
        return None
    return value[-2000:]
