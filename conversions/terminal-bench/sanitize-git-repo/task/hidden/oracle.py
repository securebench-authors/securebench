"""Oracle for terminal-bench/sanitize-git-repo.

Three checks, mapped to upstream's tests/test_outputs.py:

- sanitized-files: test_removal_of_secret_information and
  test_correct_replacement_of_secret_information on the three contaminated files.
- other-files-unchanged: test_no_other_files_changed, judged on the hashes
  SecureBench computes for the candidate's files.
- git-diff: test_no_other_files_changed, judged on what Git reports in the
  Evaluation, which also covers the index and the object database.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
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

MAX_REPORTED = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    sanitized = cases["sanitized_files"]
    files = [
        {"path": item["path"], "expected": resources.read(item["expected"]).decode("utf-8")}
        for item in sanitized["files"]
    ]
    unchanged = cases["other_files_unchanged"]
    manifest = resources.read_json(unchanged["manifest"])
    git_diff = cases["git_diff"]
    return Plan(
        artifact_contexts={
            "sanitized-files": {"files": files, "secrets": sanitized["secrets"]},
            "other-files-unchanged": {"listing": unchanged["listing"], "files": manifest["files"]},
        },
        cases={
            "git-diff": (
                Case(git_diff["challenge"], {"allowed_b_paths": git_diff["allowed_b_paths"]}),
            ),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "sanitized-files" and isinstance(evidence, ArtifactEvidence):
        return _sanitized_files(context, evidence)
    if check_id == "other-files-unchanged" and isinstance(evidence, ArtifactEvidence):
        return _other_files_unchanged(context, evidence)
    if check_id == "git-diff" and isinstance(evidence, CaseEvidence):
        return _git_diff(context, evidence)
    return Judgment(False, {"reason": "unexpected evidence", "check": check_id})


def _universal_newlines(text: str) -> str:
    # The upstream test reads both sides with open(path, "r"), which turns
    # "\r\n" and a lone "\r" into "\n" before comparing.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _sanitized_files(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    found = {item.path: item for item in evidence.files}
    for expected in context["files"]:
        path = expected["path"]
        item = found.get(path)
        if item is None:
            return Judgment(False, {"reason": "file missing from evidence", "path": path})
        if item.status is not FileStatus.PRESENT or not isinstance(item.value, Text):
            return Judgment(False, {"reason": f"file is {item.status.value}", "path": path})
        text = _universal_newlines(item.value.text)
        # test_removal_of_secret_information: no secret, compared case-insensitively.
        lowered = text.lower()
        for secret in context["secrets"]:
            if secret.lower() in lowered:
                return Judgment(False, {"reason": "a secret is still present", "path": path})
        # test_correct_replacement_of_secret_information: equal to upstream's sanitized file.
        if text != _universal_newlines(expected["expected"]):
            return Judgment(False, {"reason": "file differs from the sanitized version", "path": path})
    return Judgment(True, None)


def _other_files_unchanged(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.listings) != 1:
        return Judgment(False, {"reason": "expected one listing"})
    listing = evidence.listings[0]
    if listing.path != context["listing"] or listing.status is not ListingStatus.PRESENT:
        return Judgment(False, {"reason": f"listing is {listing.status.value}", "path": listing.path})
    entries = {entry.path: entry for entry in listing.entries}
    changed = []
    for path, reference in context["files"].items():
        entry = entries.get(path)
        if entry is None:
            changed.append({"path": path, "change": "deleted"})
        elif entry.kind is not EntryKind.FILE:
            changed.append({"path": path, "change": f"now a {entry.kind.value}"})
        elif entry.sha256 != reference["sha256"]:
            changed.append({"path": path, "change": "content"})
        elif entry.executable is not reference["executable"]:
            changed.append({"path": path, "change": "executable bit"})
    if changed:
        return Judgment(False, {"reason": "files outside the contaminated ones changed", "count": len(changed), "first": changed[:MAX_REPORTED]})
    return Judgment(True, None)


def _git_diff(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = outcome.value
    # repo.commit(<commit>) raises when the commit is gone.
    if observation["commit_found"] is not True:
        return Judgment(False, {"reason": "the upstream test's reference commit is missing"})
    # GitPython raises when `git diff` exits non-zero.
    if observation["diff_exit_status"] != 0:
        return Judgment(False, {"reason": "git diff failed", "exit_status": observation["diff_exit_status"]})
    allowed = context["allowed_b_paths"]
    changed = [entry["b_path"] for entry in observation["entries"] if entry["b_path"] not in allowed]
    if changed:
        return Judgment(False, {"reason": "git reports other files changed", "count": len(changed), "first": changed[:MAX_REPORTED]})
    return Judgment(True, None)
