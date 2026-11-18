"""Oracle for large-scale-text-editing.

Two checks, which together hold every assertion of upstream's tests/test_outputs.py:

- `script` (artifact check): test_apply_macros_exists and test_apply_macros_well_formed,
  judged on /app/apply_macros.vim as captured. Upstream's regular expressions are
  rewritten as hand-written scans with the same results; each scan names the
  expression it replaces.
- `run` (one protocol case): test_apply_macros_runs, test_input_equiv_expected and
  test_macros_nonempty_and_efficient, judged on the values the adapter reports.

The expected digest of the transformed file is in hidden/expected.json; the keystroke
bound of 200 is upstream's threshold.
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

MAX_KEYSTROKES = 200
QUOTES = "'\""
REGISTERS = "abc"

# Python's re.IGNORECASE also matches these characters to the lowercase ASCII
# letters of upstream's patterns (measured with Python 3.13 over every code point:
# only "i" and "s" have extra matches). Every pattern letter is lowercase.
EXTRA_CASE_MATCHES = {"i": "İı", "s": "ſ"}

# The commands after the range prefix in upstream's first family of forbidden
# patterns, `:(\d*|[\$%\+\-\.]|(\d+,\d*)|(\d*,\$))*{cmd}\b`.
FILE_COMMANDS = (
    "r", "read", "source", "so", "e", "edit", "sp", "split",
    "vs", "vsplit", "tabe", "tabedit", "new", "vnew",
)
CALLS = ("system(", "glob(", "expand(", "executable(", "filereadable(")
INTERPRETERS = ("py", "lua", "perl", "ruby")

# Every forbidden pattern starts with one of these characters (under re.IGNORECASE);
# the scan skips other positions to stay fast on long macros.
FIRST_CHARACTERS = frozenset(":sSgGeEfFlL\u017f")


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    return Plan(
        artifact_contexts={"script": None},
        cases={"run": (Case({}, expected),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "script" and isinstance(evidence, ArtifactEvidence):
        return _judge_script(evidence)
    if check_id == "run" and isinstance(evidence, CaseEvidence):
        return _judge_run(context, evidence)
    return Judgment(False, {"reason": "unexpected evidence"})


# ---------------------------------------------------------------------------
# script: test_apply_macros_exists, test_apply_macros_well_formed


def _judge_script(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"/app/apply_macros.vim is {found.status.value}"})
    # Path.read_text translates "\r\n" and "\r" to "\n" (universal newlines).
    text = found.value.text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip() and not line.strip().startswith('"')
    ]
    for token in _normal_tokens(text):
        if token not in ("@a", "@b", "@c"):
            return Judgment(False, {"reason": "only @a/@b/@c may be used with :%normal!", "found": token[:200]})
    if not any(line in (":wq", ":x") for line in lines):
        return Judgment(False, {"reason": "missing :wq or :x"})
    if not all(any(_mentions_setreg(line, register) for line in lines) for register in REGISTERS):
        return Judgment(False, {"reason": "must define all 3 macros"})
    if not all(any(f":%normal! @{register}" in line for line in lines) for register in REGISTERS):
        return Judgment(False, {"reason": "must execute all 3 macros"})
    for number, line in enumerate(lines, 1):
        if not _is_valid_line(line):
            return Judgment(False, {"reason": "invalid command", "line": number, "text": line[:200]})
    return Judgment(True, None)


def _normal_tokens(text: str) -> list[str]:
    """re.findall(r"^\\s*:%normal!\\s+(\\S+)", text, re.MULTILINE)."""
    tokens = []
    position = 0
    size = len(text)
    while position <= size:
        if position == 0 or text[position - 1] == "\n":
            cursor = position
            while cursor < size and text[cursor].isspace():
                cursor += 1
            if text.startswith(":%normal!", cursor):
                cursor += len(":%normal!")
                start = cursor
                while cursor < size and text[cursor].isspace():
                    cursor += 1
                if cursor > start:
                    token_start = cursor
                    while cursor < size and not text[cursor].isspace():
                        cursor += 1
                    if cursor > token_start:
                        tokens.append(text[token_start:cursor])
                        # findall resumes after the match; the next "^" is a later line start.
                        position = cursor
                        continue
        next_line = text.find("\n", position)
        if next_line < 0:
            break
        position = next_line + 1
    return tokens


def _mentions_setreg(line: str, register: str) -> bool:
    """re.search(r"call setreg\\(['\\"]<register>['\\"],", line)."""
    start = line.find("call setreg(")
    while start >= 0:
        rest = line[start + len("call setreg("):]
        if len(rest) >= 3 and rest[0] in QUOTES and rest[1] == register and rest[2] in QUOTES and rest[3:4] == ",":
            return True
        start = line.find("call setreg(", start + 1)
    return False


def _is_valid_line(line: str) -> bool:
    """Upstream's _is_valid_line."""
    if line in (":wq", ":x"):
        return True
    # re.match(r"^:%normal! @[abc]$", line); the line is stripped, so "$" is its end.
    if line in (":%normal! @a", ":%normal! @b", ":%normal! @c"):
        return True
    if _starts_with_setreg(line) and (line.endswith("')") or line.endswith('")')):
        keystrokes = _extract_keystrokes(line)
        if keystrokes is None:
            return False
        return _is_valid_keystroke_sequence(keystrokes)
    return False


def _starts_with_setreg(line: str) -> bool:
    """re.match(r"^:?call setreg\\(['\\"][abc]['\\"],", line)."""
    rest = line[1:] if line.startswith(":") else line
    head = "call setreg("
    if not rest.startswith(head):
        return False
    tail = rest[len(head):]
    return len(tail) >= 4 and tail[0] in QUOTES and tail[1] in REGISTERS and tail[2] in QUOTES and tail[3] == ","


def _extract_keystrokes(line: str) -> str | None:
    """re.search(r"setreg\\(['\\"][abc]['\\"],\\s*['\\"]([^'\\"]*)['\\"]", line).group(1), or None."""
    start = line.find("setreg(")
    while start >= 0:
        cursor = start + len("setreg(")
        if (
            line[cursor:cursor + 1] in tuple(QUOTES)
            and line[cursor + 1:cursor + 2] in tuple(REGISTERS)
            and line[cursor + 2:cursor + 3] in tuple(QUOTES)
            and line[cursor + 3:cursor + 4] == ","
        ):
            cursor += 4
            while cursor < len(line) and line[cursor].isspace():
                cursor += 1
            if line[cursor:cursor + 1] in tuple(QUOTES):
                content_start = cursor + 1
                end = content_start
                while end < len(line) and line[end] not in QUOTES:
                    end += 1
                if end < len(line):
                    return line[content_start:end]
        start = line.find("setreg(", start + 1)
    return None


def _is_valid_keystroke_sequence(keystrokes: str) -> bool:
    """Upstream's _is_valid_keystroke_sequence: no forbidden pattern found with re.IGNORECASE."""
    if not keystrokes:
        return True
    size = len(keystrokes)
    for index in range(size):
        char = keystrokes[index]
        if char not in FIRST_CHARACTERS:
            continue
        if char == ":" and (_file_command_at(keystrokes, index) or _interpreter_at(keystrokes, index)):
            return False
        if char == ":" and keystrokes[index + 1:index + 2] == "!" and index + 2 < size and _is_word(keystrokes[index + 2]):
            return False  # :!\w
        for call in CALLS:
            if _matches_folded(keystrokes, index, call):
                return False  # system\( and the like
        if _matches_folded(keystrokes, index, "function"):
            after = _skip_space(keystrokes, index + len("function"))
            if keystrokes[after:after + 1] == "!":
                return False  # function\s*!
        if _matches_folded(keystrokes, index, "let"):
            after = index + len("let")
            if after < size and keystrokes[after].isspace():
                return False  # let\s+
        if _matches_folded(keystrokes, index, "eval"):
            after = _skip_space(keystrokes, index + len("eval"))
            if keystrokes[after:after + 1] == "(":
                return False  # eval\s*\(
    return True


def _file_command_at(text: str, colon: int) -> bool:
    """Whether `:(\\d*|[\\$%\\+\\-\\.]|(\\d+,\\d*)|(\\d*,\\$))*{cmd}\\b` matches at `colon`.

    The repeated group matches exactly the strings of digits and "$%+-.," in which
    every comma has a digit right before it or a "$" right after it. `pending` marks
    a comma still waiting for its "$"; while one waits, the prefix is not matched.
    """
    pending = False
    cursor = colon + 1
    while True:
        if not pending:
            for command in FILE_COMMANDS:
                if _matches_folded(text, cursor, command) and _is_boundary(text, cursor + len(command)):
                    return True
        if cursor >= len(text):
            return False
        char = text[cursor]
        if char == ",":
            if pending:
                return False
            pending = not (cursor - 1 > colon and text[cursor - 1].isdecimal())
        elif char.isdecimal() or char in "$%+-.":
            if pending and char != "$":
                return False
            pending = False
        else:
            return False
        cursor += 1


def _interpreter_at(text: str, colon: int) -> bool:
    """`:py\\b`, `:lua\\b`, `:perl\\b` and `:ruby\\b` at `colon`."""
    return any(
        _matches_folded(text, colon + 1, name) and _is_boundary(text, colon + 1 + len(name))
        for name in INTERPRETERS
    )


def _matches_folded(text: str, start: int, pattern: str) -> bool:
    """Whether the lowercase ASCII `pattern` occurs at `start` under re.IGNORECASE."""
    if start + len(pattern) > len(text):
        return False
    for offset, expected in enumerate(pattern):
        char = text[start + offset]
        if char == expected or char == expected.upper() or char in EXTRA_CASE_MATCHES.get(expected, ""):
            continue
        return False
    return True


def _is_word(char: str) -> bool:
    """\\w for str patterns: str.isalnum() or "_"."""
    return char.isalnum() or char == "_"


def _is_boundary(text: str, position: int) -> bool:
    """\\b after a word character: the end of text or a non-word character."""
    return position >= len(text) or not _is_word(text[position])


def _skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


# ---------------------------------------------------------------------------
# run: test_apply_macros_runs, test_input_equiv_expected, test_macros_nonempty_and_efficient


def _judge_run(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter did not report an observation"})
    observed = evidence.outcome.value
    if not isinstance(context, dict) or not isinstance(observed, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    expected_sha256 = context.get("input_sha256")
    if not isinstance(expected_sha256, str):
        return Judgment(False, {"reason": "unexpected context"})

    # test_apply_macros_runs
    if observed.get("vim_timed_out") is not False:
        return Judgment(False, {"reason": "vim timed out after 600 seconds"})
    if observed.get("vim_returncode") != 0:
        return Judgment(False, {"reason": "vim did not exit 0", "returncode": observed.get("vim_returncode")})

    # test_input_equiv_expected
    if observed.get("input_kind") != "read":
        return Judgment(False, {"reason": "missing transformed file", "input": observed.get("input_kind")})
    if observed.get("input_sha256") != expected_sha256:
        return Judgment(False, {"reason": "transformed file does not match expected"})

    # test_macros_nonempty_and_efficient
    if observed.get("defs_written") is not True:
        return Judgment(False, {"reason": "could not read the script to load the macros"})
    if observed.get("defs_timed_out") is not False:
        return Judgment(False, {"reason": "vim timed out loading the macros"})
    if observed.get("defs_returncode") != 0:
        return Judgment(False, {"reason": "vim exited non-zero loading the macros", "returncode": observed.get("defs_returncode")})
    keystrokes = _dump(observed.get("keystrokes"))
    registers = _dump(observed.get("registers"))
    if keystrokes is None:
        return Judgment(False, {"reason": "keystroke output file was not created"})
    if registers is None:
        return Judgment(False, {"reason": "registers output file was not created"})
    counts = _parse_counts(keystrokes.strip())
    if counts is None:
        return Judgment(False, {"reason": "could not parse keystrokes line", "line": keystrokes.strip()[:200]})
    a, b, c, total = counts
    if not (a > 0 and b > 0 and c > 0):
        return Judgment(False, {"reason": "macros must be non-empty", "a": a, "b": b, "c": c})
    if total != a + b + c:
        return Judgment(False, {"reason": "keystroke sum mismatch"})
    if not total < MAX_KEYSTROKES:
        return Judgment(False, {"reason": f"total keystrokes must be < {MAX_KEYSTROKES}", "total": total})
    lines = [line.strip() for line in registers.splitlines()]
    if len(lines) < 3:
        return Judgment(False, {"reason": "registers output should have at least 3 lines"})
    ra, rb, rc = lines[:3]
    if not (ra != rb and rb != rc and ra != rc):
        return Judgment(False, {"reason": "macros a, b, c must be distinct"})
    return Judgment(True, {"keystrokes": total})


def _dump(value: JsonValue) -> str | None:
    """The text of a dump file the adapter read, or None if it is missing or truncated."""
    if not isinstance(value, dict):
        return None
    text = value.get("text")
    if value.get("present") is not True or value.get("truncated") is not False or not isinstance(text, str):
        return None
    return text


def _parse_counts(line: str) -> tuple[int, int, int, int] | None:
    """re.match(r"^KEYSTROKES a=(\\d+) b=(\\d+) c=(\\d+) total=(\\d+)$", line), as integers."""
    values = []
    cursor = 0
    for label in ("KEYSTROKES a=", " b=", " c=", " total="):
        if not line.startswith(label, cursor):
            return None
        cursor += len(label)
        start = cursor
        while cursor < len(line) and line[cursor].isdecimal():
            cursor += 1
        if cursor == start:
            return None
        try:
            values.append(int(line[start:cursor]))
        except ValueError:
            return None  # more digits than int() accepts, as in upstream
    if cursor != len(line):
        return None
    return values[0], values[1], values[2], values[3]
