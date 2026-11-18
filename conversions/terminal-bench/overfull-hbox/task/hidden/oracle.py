"""Oracle for overfull-hbox.

Upstream's tests (tests/test_outputs.py), one check each:

- `unmodified`: test_main_synonyms_not_modified. /app/main.tex and
  /app/synonyms.txt exist and, read in text mode, equal upstream's copies.
- `substitutions`: test_input_file_matches. /app/input.tex has the same tokens
  as upstream's, where each token keeps its leading and trailing non-word
  characters and its word is unchanged or a member of that word's synonym
  family. Like upstream, it compares tokens only, not the whitespace between
  them.
- `compile`: test_compilation_successful and test_no_overfull_hboxes. The log
  of compiling the pristine main.tex with the candidate's input.tex contains
  upstream's success line and does not contain upstream's warning text, both
  read from hidden/log.json.

The expected values are the files in hidden/: upstream's input.tex, main.tex
and synonyms.txt, and the two strings of hidden/log.json. `plan` builds the
synonym families from hidden/synonyms.txt the way upstream's test builds them.

Upstream tokenizes with `re`. The Oracle may not apply regular expressions to
evidence, so `_tokens` and `_split` reimplement `re.findall(r"\\S+", text)` and
`re.match(r"^(\\W*)(.*?)(\\W*)$", token)` with `str.split` and `str.isalnum`,
which test the same Unicode properties (`\\s` is `str.isspace`, `\\w` is
`str.isalnum` or `_`). CONVERSION.md records the differential test.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

UNMODIFIED = ("main.tex", "synonyms.txt")
# The adapter shows at most this many bytes of the log.
SHOWN = 524288


def plan(resources: HiddenResources, seed: int) -> Plan:
    del seed
    unmodified: dict[str, JsonValue] = {
        "/app/" + name: _text_mode(resources.read(name).decode("utf-8")) for name in UNMODIFIED
    }
    synonyms = _text_mode(resources.read("synonyms.txt").decode("utf-8"))
    families: dict[str, JsonValue] = {}
    # Upstream: each line is a family of mutual synonyms; a word on several
    # lines keeps the family of its last line. Iterating a file yields no empty
    # line after a final newline, so neither does this.
    lines = synonyms.split("\n")
    if lines[-1] == "":
        lines.pop()
    for line in lines:
        words = set(line.strip().split(", "))
        for word in words:
            members: list[JsonValue] = sorted(words)
            families[word] = members
    substitutions: dict[str, JsonValue] = {
        "original": _text_mode(resources.read("input.tex").decode("utf-8")),
        "families": families,
    }
    return Plan(
        artifact_contexts={"unmodified": unmodified, "substitutions": substitutions},
        cases={"compile": (Case({}, resources.read_json("log.json")),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, CaseEvidence):
        if check_id != "compile":
            return Judgment(False, {"reason": "unexpected check", "check": check_id})
        return _compile(context, evidence)
    if not isinstance(context, dict) or evidence.listings:
        return Judgment(False, {"reason": "malformed"})
    if check_id == "unmodified":
        return _unmodified(context, evidence.files)
    if check_id == "substitutions":
        return _substitutions(context, evidence.files)
    return Judgment(False, {"reason": "unexpected check", "check": check_id})


def _text_mode(text: str) -> str:
    """What Python's `open(path, "r")` returns: universal newlines become `\\n`."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read(item: FileEvidence) -> str | None:
    if item.status is not FileStatus.PRESENT or not isinstance(item.value, Text):
        return None
    return _text_mode(item.value.text)


def _unmodified(context: dict[str, JsonValue], files: tuple[FileEvidence, ...]) -> Judgment:
    paths = [item.path for item in files]
    if sorted(paths) != sorted(context) or len(set(paths)) != len(paths):
        return Judgment(False, {"reason": "unexpected files", "paths": list(paths)})
    for item in files:
        text = _read(item)
        if text is None:
            return Judgment(False, {"reason": f"{item.path} is {item.status.value}"})
        if text != context[item.path]:
            return Judgment(False, {"reason": f"{item.path} must not be modified"})
    return Judgment(True, None)


def _substitutions(context: dict[str, JsonValue], files: tuple[FileEvidence, ...]) -> Judgment:
    original = context["original"]
    families = context["families"]
    if len(files) != 1 or files[0].path != "/app/input.tex":
        return Judgment(False, {"reason": "unexpected files"})
    if not isinstance(original, str) or not isinstance(families, dict):
        return Judgment(False, {"reason": "malformed context"})
    agent = _read(files[0])
    if agent is None:
        return Judgment(False, {"reason": f"/app/input.tex is {files[0].status.value}"})
    tokens = _tokens(original)
    tokens_agent = _tokens(agent)
    if len(tokens) != len(tokens_agent):
        return Judgment(
            False,
            {"reason": "token count differs", "expected": len(tokens), "got": len(tokens_agent)},
        )
    for index, (token, token_agent) in enumerate(zip(tokens, tokens_agent, strict=True)):
        prefix, word, suffix = _split(token)
        prefix_agent, word_agent, suffix_agent = _split(token_agent)
        family = families.get(word)
        allowed = word_agent == word or (
            isinstance(family, list) and word_agent in family
        )
        if prefix != prefix_agent or suffix != suffix_agent or not allowed:
            return Judgment(
                False,
                {
                    "reason": "only words listed in synonyms.txt may change",
                    "token": index,
                    "expected": token,
                    "got": token_agent[:256],
                },
            )
    return Judgment(True, None)


def _tokens(text: str) -> list[str]:
    """Upstream's `re.findall(r"\\S+", text)` after spacing out em dashes.

    `str.split` splits on `str.isspace` characters, which are `\\s`.
    """
    return text.replace("---", " --- ").split()


def _is_word(character: str) -> bool:
    return character.isalnum() or character == "_"


def _split(token: str) -> tuple[str, str, str]:
    """Upstream's `re.match(r"^(\\W*)(.*?)(\\W*)$", token).groups()` for a token without whitespace."""
    start = 0
    while start < len(token) and not _is_word(token[start]):
        start += 1
    if start == len(token):
        return token, "", ""
    end = len(token)
    while not _is_word(token[end - 1]):
        end -= 1
    return token[:start], token[start:end], token[end:]


def _compile(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    required = context.get("must_contain")
    forbidden = context.get("must_not_contain")
    if not isinstance(required, str) or not isinstance(forbidden, str) or not required or not forbidden:
        return Judgment(False, {"reason": "malformed context"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    run = evidence.outcome.value
    if not isinstance(run, dict):
        return Judgment(False, {"reason": "malformed"})
    log = run["log"]
    size = run["log_bytes"]
    if not isinstance(log, str) or not isinstance(size, int):
        return Judgment(False, {"reason": "malformed"})
    if run["ending"] != "exited":
        return Judgment(False, {"reason": "pdflatex did not finish", "ending": run["ending"]})
    if run["log_present"] is not True:
        return Judgment(False, {"reason": "pdflatex wrote no main.log"})
    # Upstream reads main.log strictly as UTF-8 and searches all of it.
    if run["log_utf8"] is not True:
        return Judgment(False, {"reason": "main.log is not valid UTF-8"})
    if size > SHOWN or size != len(log.encode("utf-8")):
        return Judgment(False, {"reason": "main.log not shown in full", "log_bytes": size})
    text = _text_mode(log)
    if required not in text:
        return Judgment(False, {"reason": "Solution must compile successfully"})
    if forbidden in text:
        return Judgment(
            False,
            {"reason": "Solution must remove all overfull hboxes", "count": text.count(forbidden)},
        )
    return Judgment(True, None)
