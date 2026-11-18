"""Oracle for git-leak-recovery.

Each check mirrors one upstream test in tests/test_outputs.py; the expected
values (the secret, the checksum, the commit message and the searched
substring) are in hidden/cases.json.
"""

import hashlib

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    EntryKind,
    FileStatus,
    HiddenResources,
    Judgment,
    ListingStatus,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json is not an object")
    cases = data["git-history"]
    if not isinstance(cases, list):
        raise ValueError("git-history cases are not a list")
    return Plan(
        artifact_contexts={
            "flag-file": data["flag-file"],
            "repository-contents": data["repository-contents"],
        },
        cases={
            "git-history": tuple(
                Case(case["challenge"], case["context"])
                for case in cases
                if isinstance(case, dict)
            )
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return _fail("context is not an object")
    if check_id == "flag-file" and isinstance(evidence, ArtifactEvidence):
        return _judge_flag(context, evidence)
    if check_id == "repository-contents" and isinstance(evidence, ArtifactEvidence):
        return _judge_contents(context, evidence)
    if check_id == "git-history" and isinstance(evidence, CaseEvidence):
        return _judge_history(context, evidence)
    return _fail(f"unexpected evidence for check {check_id}")


def _fail(reason: str) -> Judgment:
    return Judgment(False, {"reason": reason})


def _judge_flag(context: dict[str, JsonValue], evidence: ArtifactEvidence) -> Judgment:
    # assert flag_path.exists(); assert read_text().strip() == expected
    if len(evidence.files) != 1:
        return _fail("expected exactly one file")
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return _fail(f"/app/secret.txt is {found.status.value}")
    if found.value.text.strip() != context["expected"]:
        return _fail("/app/secret.txt does not hold the secret")
    return Judgment(True, None)


def _escape_name(name: str) -> str:
    # sha256sum escapes these characters and marks the line with a leading backslash.
    return name.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def _judge_contents(context: dict[str, JsonValue], evidence: ArtifactEvidence) -> Judgment:
    # find <root> -type f -not -path '*/\.*' -exec sha256sum {} + | sort | sha256sum
    if len(evidence.listings) != 1:
        return _fail("expected exactly one listing")
    listing = evidence.listings[0]
    if listing.status is not ListingStatus.PRESENT:
        return _fail(f"{context['root']} is {listing.status.value}")
    root = context["root"]
    if not isinstance(root, str):
        return _fail("context root is not a string")
    lines: list[bytes] = []
    for entry in listing.entries:
        if entry.kind is not EntryKind.FILE or entry.sha256 is None:
            continue
        # The pattern '*/\.*' matches any path with a component starting with a dot.
        if any(part.startswith(".") for part in entry.path.split("/")):
            continue
        # SecureBench writes digests as "sha256:<hex>"; sha256sum prints the bare hex.
        if not entry.sha256.startswith("sha256:"):
            return _fail("unexpected digest format in the listing")
        name = f"{root}/{entry.path}"
        escaped = _escape_name(name)
        prefix = "\\" if escaped != name else ""
        lines.append(f"{prefix}{entry.sha256.removeprefix('sha256:')}  {escaped}\n".encode())
    # `sort` runs without a locale in upstream's verifier: byte order.
    lines.sort()
    digest = hashlib.sha256(b"".join(lines)).hexdigest()
    if digest != context["expected_sha256"]:
        return _fail(f"repository contents checksum is {digest}")
    return Judgment(True, None)


def _command_results(evidence: CaseEvidence) -> tuple[list[dict[str, JsonValue]], list[dict[str, JsonValue]]] | str:
    if not isinstance(evidence.outcome, Observed):
        return "the adapter did not return an observation"
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return "observation is not an object"
    commands = value["commands"]
    dangling = value["dangling"]
    if not isinstance(commands, list) or not isinstance(dangling, list):
        return "observation fields are not lists"
    results = [item for item in commands if isinstance(item, dict)]
    inspections = [item for item in dangling if isinstance(item, dict)]
    if len(results) != len(commands) or len(inspections) != len(dangling):
        return "observation entries are not objects"
    return results, inspections


def _judge_history(context: dict[str, JsonValue], evidence: CaseEvidence) -> Judgment:
    parsed = _command_results(evidence)
    if isinstance(parsed, str):
        return _fail(parsed)
    results, inspections = parsed
    rule = context["rule"]
    expected_commands = {"all_empty": 2, "contains": 1, "dangling_clean": 1}.get(str(rule))
    if expected_commands is None or len(results) != expected_commands:
        return _fail("wrong number of command results")
    # Upstream reads both streams of every command with text=True, which raises
    # on bytes that are not UTF-8, and then asserts the return code is 0.
    for index, result in enumerate(results):
        if result["decoded"] is not True:
            return _fail(f"command {index} printed bytes that are not UTF-8")
        if result["stderr_decoded"] is not True:
            return _fail(f"command {index} printed bytes that are not UTF-8 on standard error")
        if result["returncode"] != 0:
            return _fail(f"command {index} exited with {result['returncode']}")
    if rule == "all_empty":
        # test_no_secrets_in_commits: assert not result.stdout.strip()
        for index, result in enumerate(results):
            stdout = result["stdout"]
            if not isinstance(stdout, str) or stdout.strip():
                return _fail(f"command {index} found a commit with the secret")
        if inspections:
            return _fail("unexpected dangling inspections")
        return Judgment(True, None)
    if rule == "contains":
        # test_good_commits_preserved: assert message in result.stdout.strip()
        stdout = results[0]["stdout"]
        needle = context["needle"]
        if not isinstance(stdout, str) or not isinstance(needle, str) or needle not in stdout.strip():
            return _fail("the preserved commit message is missing")
        if inspections:
            return _fail("unexpected dangling inspections")
        return Judgment(True, None)
    return _judge_dangling(context, results[0], inspections)


def _judge_dangling(
    context: dict[str, JsonValue],
    fsck: dict[str, JsonValue],
    inspections: list[dict[str, JsonValue]],
) -> Judgment:
    # test_no_secrets_in_unreachable_objects: for every fsck line containing
    # "dangling", `cat-file -p <last word>` must not print the needle when it
    # exits with 0. parts[1] is read for the message, so a line of one word
    # raises there.
    stdout = fsck["stdout"]
    needle = context["needle"]
    if not isinstance(stdout, str) or not isinstance(needle, str):
        return _fail("malformed fsck result")
    lines = [line for line in stdout.splitlines() if "dangling" in line]
    if len(lines) != len(inspections):
        return _fail("the dangling objects inspected do not match fsck's output")
    for line, inspection in zip(lines, inspections, strict=True):
        parts = line.split()
        if len(parts) < 2:
            return _fail("fsck printed a dangling line without an object type")
        if inspection["object"] != parts[-1]:
            return _fail("an inspection does not match its fsck line")
        if inspection["decoded"] is not True or inspection["stderr_decoded"] is not True:
            return _fail(f"dangling {parts[1]} printed bytes that are not UTF-8")
        content = inspection["stdout"]
        if not isinstance(content, str):
            return _fail("malformed inspection")
        if inspection["returncode"] == 0 and needle in content:
            return _fail(f"found the secret in a dangling {parts[1]}")
    return Judgment(True, None)
