"""Oracle for terminal-bench/build-pmars.

There is one case per upstream test function in tests/test_outputs.py. The
adapter reports raw results (path existence, each shell command's exit status
and standard output, the matches of a glob under /app); this module applies
the test's assertions to them.

Upstream applies two regular expressions to command output. They are
reimplemented here by hand with the same Unicode classes Python's `re` uses
for str patterns: \\d is str.isdecimal, \\s is str.isspace, \\w is
str.isalnum or "_".
"""

import base64
import binascii

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

CHECK = "upstream-tests"
# Bounds the decoder; the observation schema already caps each string.
MAX_STDOUT_BASE64 = 1300000

# The shape of each test's observation: entries in "exists", entries in
# "commands", and the "exists"/"glob_counts" lengths of the single glob, if any.
SHAPES = {
    "test_pmars_works": (1, 3, None),
    "test_headless_no_x11": (0, 1, None),
    "test_debian_source_used": (0, 0, (1, 0)),
    "test_built_from_source": (0, 0, (1, 1)),
}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = tuple(Case(entry["challenge"], entry["context"]) for entry in resources.read_json("cases.json"))
    return Plan(artifact_contexts={}, cases={CHECK: cases})


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed):
        return fail("the adapter returned no observation")
    observation = evidence.outcome.value
    test = context.get("test")
    if test not in SHAPES or not well_shaped(observation, SHAPES[test]):
        return fail("observation does not have the shape of its test", test=test)
    if test == "test_pmars_works":
        return judge_pmars_works(context, observation)
    if test == "test_headless_no_x11":
        return judge_headless(context, observation)
    if test == "test_debian_source_used":
        return judge_source(observation, need_c_files=False)
    return judge_source(observation, need_c_files=True)


def well_shaped(observation: JsonValue, shape: tuple) -> bool:
    exists_count, command_count, glob_shape = shape
    if not isinstance(observation, dict):
        return False
    exists = observation.get("exists")
    commands = observation.get("commands")
    globs = observation.get("source_globs")
    if not isinstance(exists, list) or len(exists) != exists_count:
        return False
    if not all(isinstance(value, bool) for value in exists):
        return False
    if not isinstance(commands, list) or len(commands) != command_count:
        return False
    for command in commands:
        if not isinstance(command, dict):
            return False
        if not isinstance(command.get("exit_status"), int) or isinstance(command.get("exit_status"), bool):
            return False
        if not isinstance(command.get("stdout_base64"), str):
            return False
    if not isinstance(globs, list) or len(globs) != (0 if glob_shape is None else 1):
        return False
    for glob in globs:
        if not isinstance(glob, dict) or not isinstance(glob.get("matches"), list):
            return False
        for match in glob["matches"]:
            if not isinstance(match, dict) or not isinstance(match.get("name"), str):
                return False
            if not isinstance(match.get("exists"), list) or len(match["exists"]) != glob_shape[0]:
                return False
            if not all(isinstance(value, bool) for value in match["exists"]):
                return False
            counts = match.get("glob_counts")
            if not isinstance(counts, list) or len(counts) != glob_shape[1]:
                return False
            if not all(isinstance(value, int) and not isinstance(value, bool) for value in counts):
                return False
    return True


def shell_result(command: dict) -> str | None:
    """What upstream's run_shell_command returns, or None where it raises.

    check_output(..., text=True) decodes strictly as UTF-8 and translates
    "\\r\\n" and "\\r" to "\\n". On a non-zero exit it returns the captured
    output if there is any, and otherwise re-raises.
    """
    encoded = command["stdout_base64"]
    if len(encoded) > MAX_STDOUT_BASE64:
        return None
    try:
        raw = base64.b64decode(encoded, validate=True)
        text = raw.decode("utf-8")
    except (binascii.Error, ValueError):
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if command["exit_status"] != 0 and not text:
        return None
    return text.strip()


def is_word(char: str) -> bool:
    return char.isalnum() or char == "_"


def address_match_end(text: str, start: int) -> int | None:
    """Where r"\\b(\\d{5})\\s+\\w+\\.\\w+" matches at `start`, or None.

    Every quantifier is greedy, and no backtracking can rescue a failed
    attempt: whitespace is never a word character, and "." is neither.
    """
    length = len(text)
    previous_is_word = start > 0 and is_word(text[start - 1])
    current_is_word = start < length and is_word(text[start])
    if previous_is_word == current_is_word:
        return None
    position = start
    for _ in range(5):
        if position >= length or not text[position].isdecimal():
            return None
        position += 1
    spaces = position
    while position < length and text[position].isspace():
        position += 1
    if position == spaces:
        return None
    word = position
    while position < length and is_word(text[position]):
        position += 1
    if position == word or position >= length or text[position] != ".":
        return None
    position += 1
    word = position
    while position < length and is_word(text[position]):
        position += 1
    if position == word:
        return None
    return position


def count_addresses(text: str) -> int:
    """len(re.findall(r"\\b(\\d{5})\\s+\\w+\\.\\w+", text)): non-overlapping, left to right."""
    count = 0
    position = 0
    while position < len(text):
        end = address_match_end(text, position)
        if end is None:
            position += 1
        else:
            count += 1
            position = end
    return count


def decimal_run_end(text: str, position: int) -> int | None:
    start = position
    while position < len(text) and text[position].isdecimal():
        position += 1
    return None if position == start else position


def matches_results(text: str, label: str) -> bool:
    """re.match(r"Results: \\d+ \\d+ \\d+", text): anchored at the start only."""
    if not text.startswith(label):
        return False
    position = len(label)
    for _ in range(3):
        if position >= len(text) or text[position] != " ":
            return False
        end = decimal_run_end(text, position + 1)
        if end is None:
            return False
        position = end
    return True


def judge_pmars_works(context: dict, observation: dict) -> Judgment:
    if observation["exists"] != [True]:
        return fail("pmars not installed at /usr/local/bin/pmars")
    minimum = context["min_addresses"]
    for warrior, command in zip(("rave.red", "flashpaper.red"), observation["commands"][:2]):
        result = shell_result(command)
        if result is None:
            return fail("the debugger command failed or printed non-UTF-8", warrior=warrior)
        addresses = count_addresses(result)
        if addresses < minimum:
            return fail("expected stepping", warrior=warrior, addresses=addresses)
    battle = shell_result(observation["commands"][2])
    if battle is None:
        return fail("the battle command failed or printed non-UTF-8")
    if not matches_results(battle, context["results_label"]):
        return fail("expected 'Results: X Y Z' format", got=battle[:200])
    return Judgment(True, None)


def judge_headless(context: dict, observation: dict) -> Judgment:
    result = shell_result(observation["commands"][0])
    if result is None:
        return fail("ldd failed without output or printed non-UTF-8")
    for library in context["forbidden_libraries"]:
        if library in result:
            return fail("pmars links against an X11 library", library=library)
    return Judgment(True, None)


def judge_source(observation: dict, need_c_files: bool) -> Judgment:
    # Upstream takes the first glob result in directory order, which is not
    # fixed; byte order of the name is the deterministic stand-in.
    matches = observation["source_globs"][0]["matches"]
    if not matches:
        return fail("no pmars source directory found in /app")
    first = min(matches, key=lambda match: match["name"].encode("utf-8"))
    if not first["exists"][0]:
        missing = "src" if need_c_files else "debian"
        return fail(f"no {missing} directory", directory=first["name"])
    if need_c_files and first["glob_counts"][0] == 0:
        return fail("no C source files found", directory=first["name"])
    return Judgment(True, None)
