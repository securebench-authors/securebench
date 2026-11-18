"""Result records and provenance (architecture Section 11)."""

import subprocess
from collections.abc import Sequence
from pathlib import Path

from securebench.core.evidence import Evidence, Judgment, evidence_to_json
from securebench.core.jsondata import JsonValue
from securebench.core.verdict import Verdict
from securebench.results.run import EXECUTION_CONTRACT

REPOSITORY = Path(__file__).resolve().parents[2]
UNTRUSTED_FIELDS = ("judged[].evidence", "agent.transcript", "logs.transcript", "logs.stderr")
"""Fields that hold agent-controlled content: bounded bytes, escaped when displayed,
marked as data whenever an LLM reads them (architecture Section 11)."""


# What the dirty flag covers: the code a run executes. Task packs and documents in
# the same repository are left out; a run records its pack by digest instead.
_CODE_PATHS = (
    "securebench",
    "securebench_utility",
    "securebench_relay_proxy",
    "pyproject.toml",
    "uv.lock",
)


def framework() -> JsonValue:
    """The SecureBench commit, whether its code has uncommitted changes, and the contract."""
    commit = _git("rev-parse", "HEAD").strip() or "unknown"
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no", "--", *_CODE_PATHS).strip())
    return {"commit": commit, "dirty": dirty, "execution_contract": EXECUTION_CONTRACT}


def _git(*arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPOSITORY), *arguments],
            capture_output=True,
            timeout=30,
            check=False,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                "GIT_OPTIONAL_LOCKS": "0",
            },
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.decode("utf-8", "replace") if result.returncode == 0 else ""


def attempt_record(
    *,
    task_id: str,
    attempt: int,
    verdict: Verdict,
    provenance: JsonValue,
    candidate_id: str | None,
    agent: JsonValue,
    judged: Sequence[tuple[str, int | None, Evidence, Judgment | None]],
    host_errors: Sequence[JsonValue],
    logs: dict[str, str],
    admitted: bool,
) -> JsonValue:
    """Assemble one attempt's record. Evidence is stored for every check and case that ran."""
    entries: list[JsonValue] = [
        {
            "case": case_index,
            "check": check_id,
            "evidence": evidence_to_json(evidence),
            "judgment": None
            if judgment is None
            else {"diagnostic": judgment.diagnostic, "passed": judgment.passed},
        }
        for check_id, case_index, evidence, judgment in judged
    ]
    log_digests: dict[str, JsonValue] = dict(logs)
    untrusted: list[JsonValue] = list(UNTRUSTED_FIELDS)
    return {
        "admitted": admitted,
        "agent": agent,
        "attempt": attempt,
        "candidate": candidate_id,
        "diagnostics": list(verdict.diagnostics),
        "failure_class": verdict.failure_class.value if verdict.failure_class else None,
        "host_errors": list(host_errors),
        "judged": entries,
        "logs": log_digests,
        "provenance": provenance,
        "status": verdict.status.value,
        "task": task_id,
        "untrusted_fields": untrusted,
    }
