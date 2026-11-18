"""Oracle for cobol-modernization.

The single case replays upstream's tests/test_outputs.py. The adapter reports
whether the required files existed and, for each run of /app/program.py, its
exit status and whether its standard output and error are UTF-8; the data
files left after the last run arrive as Output Artifacts. All expected
contents come from hidden/cases.json, which copies the literals of upstream's
test_program_output.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
    Text,
)
from securebench.core.jsondata import JsonValue

CHECK = "program-output"

# test_required_files_exist and test_data_files_exist.
REQUIRED = ("program_py", "accounts_dat", "books_dat", "transactions_dat", "input_dat")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("cases.json must hold a list of cases")
    cases = []
    for entry in data["cases"]:
        challenge = entry["challenge"]
        expected = entry["expected"]
        context = {
            "runs": len(challenge["inputs"]),
            "expected": [[path, text] for path, text in expected.items()],
        }
        cases.append(Case(challenge=challenge, context=context))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


def fail(reason: str, **details: JsonValue) -> Judgment:
    diagnostic: dict[str, JsonValue] = {"reason": reason}
    diagnostic.update(details)
    return Judgment(False, diagnostic)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return fail("unexpected evidence")
    if not isinstance(context, dict):
        return fail("malformed context")
    expected_runs = context.get("runs")
    expected = context.get("expected")
    if not isinstance(expected_runs, int) or not isinstance(expected, list):
        return fail("malformed context")

    if not isinstance(evidence.outcome, Observed):
        return fail("the adapter returned no observation")
    value = evidence.outcome.value
    if not isinstance(value, dict) or set(value) != {"existed", "runs"}:
        return fail("observation has unexpected fields")

    existed = value["existed"]
    if not isinstance(existed, dict) or set(existed) != set(REQUIRED):
        return fail("observation 'existed' has unexpected fields")
    for name in REQUIRED:
        if existed[name] is not True:
            return fail("a required file did not exist", file=name)

    # Upstream's subprocess.run(..., capture_output=True, text=True) raises
    # when either stream is not UTF-8, and the test asserts returncode == 0
    # after each run.
    runs = value["runs"]
    if not isinstance(runs, list):
        return fail("observation 'runs' is not a list")
    for index, run in enumerate(runs):
        if not isinstance(run, dict) or set(run) != {"returncode", "stdout_utf8", "stderr_utf8"}:
            return fail("run record has unexpected fields", run=index)
        if run["stdout_utf8"] is not True or run["stderr_utf8"] is not True:
            return fail("program.py wrote output that is not UTF-8", run=index)
        code = run["returncode"]
        if isinstance(code, bool) or code != 0:
            return fail("program.py exited with a non-zero status", run=index, returncode=code)
    if len(runs) != expected_runs:
        return fail("program.py did not complete every run", runs=len(runs))

    # Upstream compares Path.read_text() of each data file with a literal.
    artifacts = evidence.output_artifacts
    if len(artifacts) != len(expected):
        return fail("unexpected number of Output Artifacts")
    for found, pair in zip(artifacts, expected):
        if not isinstance(pair, list) or len(pair) != 2:
            return fail("malformed context")
        path, text = pair
        if found.path != path:
            return fail("Output Artifact out of order", expected_path=path)
        if found.status is not FileStatus.PRESENT:
            return fail("data file not readable as text", file=path, status=found.status.value)
        if not isinstance(found.value, Text):
            return fail("data file not parsed as text", file=path)
        if found.value.text != text:
            return fail("data file content mismatch", file=path, size=found.size)

    return Judgment(True, None)
