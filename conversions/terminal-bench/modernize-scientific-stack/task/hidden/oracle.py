"""Oracle for modernize-scientific-stack.

Upstream's tests (tests/test_outputs.py) run the modernized script, search its
stdout with `re.search(r'Station 101.*?(-?\\d+\\.\\d+)', output, re.IGNORECASE | re.DOTALL)`
(and the same for Station 102 without the optional minus), and compare the
number found with a literal within 0.1. A second test asks for a dependency
file. `judge` repeats those assertions on the adapter's report. It applies no
regular expression to evidence: `find_number` is a hand-written equivalent of
that search. Expected values and the paths come from hidden/cases.json.
"""

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

CHECK = "modernized-script"

# The characters Python's `re` accepts for each cased label character under
# re.IGNORECASE, measured on the baseline's Python 3.13 by testing every code
# point. Uncased characters (digits, space) match only themselves.
IGNORECASE_MATCHES = {
    "S": "Ssſ",
    "s": "Ssſ",
    "t": "Tt",
    "a": "Aa",
    "i": "Iiİı",
    "o": "Oo",
    "n": "Nn",
}
UNCASED = "0123456789 "


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict)
    context = data["context"]
    assert isinstance(context, dict)
    stations = context["stations"]
    assert isinstance(stations, list)
    for station in stations:
        assert isinstance(station, dict)
        label = station["label"]
        assert isinstance(label, str)
        for char in label:
            assert char in IGNORECASE_MATCHES or char in UNCASED, char
    return Plan(artifact_contexts={}, cases={CHECK: (Case(data["challenge"], context),)})


def label_at(text: str, start: int, label: str) -> bool:
    if start + len(label) > len(text):
        return False
    for offset, char in enumerate(label):
        found = text[start + offset]
        if char in UNCASED:
            if found != char:
                return False
        elif found not in IGNORECASE_MATCHES[char]:
            return False
    return True


def number_end(text: str, start: int) -> int:
    """End of `\\d+\\.\\d+` matched at `start`, or -1. `\\d` in a str pattern is str.isdecimal()."""
    index = start
    while index < len(text) and text[index].isdecimal():
        index += 1
    if index == start or index + 1 >= len(text) or text[index] != ".":
        return -1
    if not text[index + 1].isdecimal():
        return -1
    index += 1
    while index < len(text) and text[index].isdecimal():
        index += 1
    return index


def find_number(text: str, label: str, optional_minus: bool) -> str | None:
    """The group `re.search(label + r'.*?(-?\\d+\\.\\d+)', text, IGNORECASE | DOTALL)` captures.

    The search starts at the leftmost occurrence of the label; a later
    occurrence cannot succeed where an earlier one failed, because its
    remaining text is a suffix of the earlier one's. The lazy `.*?` then takes
    the first position where the number matches, trying the minus sign first.
    """
    start = -1
    for position in range(len(text) - len(label) + 1):
        if label_at(text, position, label):
            start = position + len(label)
            break
    if start < 0:
        return None
    position = start
    while position < len(text):
        if optional_minus and text[position] == "-":
            end = number_end(text, position + 1)
            if end >= 0:
                return text[position:end]
        end = number_end(text, position)
        if end >= 0:
            return text[position:end]
        # A number starting later inside the same digit run would end at the
        # same character and fail the same way, so skip the run: this keeps
        # the search linear in the length of the candidate's output.
        run_end = position
        while run_end < len(text) and text[run_end].isdecimal():
            run_end += 1
        position = max(run_end, position + 1)
    return None


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def judge(check_id: str, context: JsonValue, evidence: object) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed):
        return fail("no observation")
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return fail("observation is not an object")

    # test_dependency_file_exists
    expected_paths = context["dependency_files"]
    reported = observation.get("dependency_files")
    if not isinstance(reported, list) or not isinstance(expected_paths, list):
        return fail("dependency files not reported")
    if [entry.get("path") if isinstance(entry, dict) else None for entry in reported] != expected_paths:
        return fail("dependency files reported for other paths")
    if not any(isinstance(entry, dict) and entry.get("exists") is True for entry in reported):
        return fail("no dependency file", paths=expected_paths)

    # test_modernized_code_runs
    if observation.get("script_exists") is not True:
        return fail("script not found")
    if observation.get("csv_exists") is not True:
        return fail("CSV data file not found")
    run = observation.get("run")
    if not isinstance(run, dict):
        return fail("script was not run")
    if run.get("timed_out") is not False:
        return fail("script timed out")
    if run.get("stderr_decodable") is not True:
        return fail("stderr is not valid UTF-8")
    if run.get("returncode") != 0 or isinstance(run.get("returncode"), bool):
        return fail("script failed to run", returncode=run.get("returncode"))
    lines = run.get("stdout_lines")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        return fail("stdout is not valid UTF-8")
    output = "\n".join(lines)

    substrings = context["required_substrings"]
    assert isinstance(substrings, list)
    for substring in substrings:
        assert isinstance(substring, str)
        if substring not in output:
            return fail("missing station in output", expected=substring)
    lowercase = context["required_lowercase_substring"]
    assert isinstance(lowercase, str)
    if lowercase not in output.lower():
        return fail("missing phrase in output", expected=lowercase)

    stations = context["stations"]
    assert isinstance(stations, list)
    found_values: dict[str, JsonValue] = {}
    for station in stations:
        assert isinstance(station, dict)
        label = station["label"]
        optional_minus = station["optional_minus"]
        expected = station["expected"]
        tolerance = station["tolerance"]
        assert isinstance(label, str) and isinstance(optional_minus, bool)
        assert isinstance(expected, float) and isinstance(tolerance, float)
        number = find_number(output, label, optional_minus)
        if number is None:
            return fail("no mean temperature found", station=label)
        value = float(number)
        if not abs(value - expected) < tolerance:
            return fail("wrong mean temperature", station=label, found=number[:64])
        found_values[label] = number[:64]
    return Judgment(True, {"found": found_values})
