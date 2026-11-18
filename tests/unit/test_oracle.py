"""The Oracle contract: static checks, the import guard and the judging process."""

import shutil
import sys
from pathlib import Path

import pytest

from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Ending,
    EntryKind,
    FileEvidence,
    FileStatus,
    HostFacts,
    ListingEntry,
    ListingEvidence,
    ListingStatus,
    Malformed,
    Observed,
    Text,
    Unable,
    evidence_from_json,
    evidence_to_json,
)
from securebench.core.jsondata import JsonValue
from securebench.oracle import process, worker
from securebench.oracle.process import OracleProcess
from securebench.oracle.static import check_oracle_source
from securebench.taskspec.load import load

F1 = Path(__file__).parents[2] / "fixtures" / "f1-answer-file" / "task"

HEADER = (
    "def plan(resources, seed):\n    return None\n\n"
    "def judge(check_id, context, evidence):\n    return None\n"
)


def _answer(value: JsonValue) -> ArtifactEvidence:
    file = FileEvidence(
        "/srv/answer.json", FileStatus.PRESENT, value, 12, "sha256:" + "a" * 64, None
    )
    return ArtifactEvidence("answer", (file,), ())


@pytest.mark.parametrize(
    "source",
    [
        "import os\n",
        "import re\n",
        "import json\n",
        "import subprocess\n",
        "from pickle import loads\n",
        "import random\n",
        "from random import randint\n",
        "from . import x\n",
        "from math import *\n",
        "x = open('/etc/passwd')\n",
        "x = eval('1')\n",
        "x = getattr(object, 'x')\n",
        "x = ().__class__.__bases__\n",
        "x = __builtins__\n",
        "def f():\n    global y\n",
        "x = __import__('os')\n",
        "x = id(1)\n",
    ],
)
def test_static_checks_reject_forbidden_code(source: str) -> None:
    with pytest.raises(Rejected):
        check_oracle_source(HEADER + source, "oracle.py")


def test_static_checks_require_plan_and_judge() -> None:
    with pytest.raises(Rejected):
        check_oracle_source("def plan(resources, seed):\n    return None\n", "oracle.py")


def test_static_checks_accept_the_f1_oracle_and_seeded_randomness() -> None:
    check_oracle_source((F1 / "hidden" / "oracle.py").read_text(), "oracle.py")
    check_oracle_source(HEADER + "from random import Random\nimport math\n", "oracle.py")


def test_evidence_round_trips_through_json() -> None:
    artifact = ArtifactEvidence(
        "a",
        (
            FileEvidence(
                "/srv/t", FileStatus.PRESENT, Text("x\n", ("x",)), 2, "sha256:" + "b" * 64, None
            ),
            FileEvidence("/srv/j", FileStatus.PRESENT, None, 4, "sha256:" + "c" * 64, None),
            FileEvidence("/srv/m", FileStatus.ABSENT, None, None, None, None),
        ),
        (
            ListingEvidence(
                "/srv/d",
                ListingStatus.PRESENT,
                (ListingEntry("f", EntryKind.FILE, 1, "sha256:" + "d" * 64, True, None),),
            ),
        ),
    )
    case = CaseEvidence(
        "c", 3, "sha256:" + "e" * 64, HostFacts(Ending.RETURNED, 0, 1.5), Observed({"k": [1]}), ()
    )
    for evidence in (
        artifact,
        case,
        CaseEvidence("c", 0, "d", HostFacts(Ending.TIMED_OUT, None, 9.0), Malformed("r"), ()),
        CaseEvidence("c", 0, "d", HostFacts(Ending.RETURNED, 0, 1.0), Unable("x", "y"), ()),
    ):
        assert evidence_from_json(evidence_to_json(evidence)) == evidence


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "case"},
        {"kind": "artifact", "check_id": "a", "files": [], "listings": [], "x": 1},
        {
            "kind": "artifact",
            "check_id": "a",
            "files": [
                {
                    "path": "p",
                    "status": "gone",
                    "reason": None,
                    "sha256": None,
                    "size": None,
                    "value": None,
                }
            ],
            "listings": [],
        },
    ],
)
def test_malformed_stored_evidence_is_rejected(value: JsonValue) -> None:
    with pytest.raises(Rejected):
        evidence_from_json(value)


def test_f1_oracle_plans_and_judges_in_its_own_process() -> None:
    with OracleProcess(load(F1)) as oracle:
        plan = oracle.plan(7)
        assert plan.artifact_contexts == {"answer": {"sum": 1294}}
        context = plan.artifact_contexts["answer"]
        assert oracle.judge("answer", context, _answer({"sum": 1294})).passed
        assert not oracle.judge("answer", context, _answer({"sum": 1293})).passed
        assert not oracle.judge("answer", context, _answer({"sum": True})).passed
        assert not oracle.judge("answer", context, _answer({"sum": 1294, "verdict": "pass"})).passed


def _pack_with_oracle(tmp_path: Path, source: str) -> Path:
    pack = tmp_path / "pack"
    shutil.copytree(F1, pack)
    (pack / "hidden" / "oracle.py").write_text(source)
    return pack


PLAN = (
    "from securebench.core.evidence import Judgment, Plan\n"
    "def plan(resources, seed):\n"
    "    return Plan({'answer': resources.read_json('expected.json')}, {})\n"
)


def test_an_oracle_that_raises_or_hangs_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = PLAN + (
        "def judge(check_id, context, evidence):\n"
        "    if evidence.files[0].value == {'sum': 0}:\n"
        "        while True:\n"
        "            pass\n"
        "    raise ValueError('boom')\n"
    )
    monkeypatch.setattr(process, "JUDGE_TIMEOUT_SECONDS", 1)
    with OracleProcess(load(_pack_with_oracle(tmp_path, source))) as oracle:
        raised = oracle.judge("answer", None, _answer({"sum": 1}))
        assert not raised.passed and "boom" in str(raised.diagnostic)
        hung = oracle.judge("answer", None, _answer({"sum": 0}))
        assert not hung.passed and "did not answer" in str(hung.diagnostic)
        again = oracle.judge("answer", None, _answer({"sum": 1}))
        assert "boom" in str(again.diagnostic)


@pytest.mark.skipif(sys.platform != "linux", reason="macOS does not enforce RLIMIT_AS")
def test_an_oracle_that_exhausts_its_memory_fails_the_check(tmp_path: Path) -> None:
    # The allocation is sized from evidence, as in wazero-multi-module-snapshots,
    # and fails at once without touching the host's memory.
    source = PLAN + (
        "def judge(check_id, context, evidence):\n"
        "    padded = [0] * evidence.files[0].value['count']\n"
        "    return Judgment(True, len(padded))\n"
    )
    too_many = worker.MAX_MEMORY_BYTES // 8 + 1
    with OracleProcess(load(_pack_with_oracle(tmp_path, source))) as oracle:
        exhausted = oracle.judge("answer", None, _answer({"count": too_many}))
        assert not exhausted.passed and "MemoryError" in str(exhausted.diagnostic)
        assert oracle.judge("answer", None, _answer({"count": 1 << 20})).passed


def test_a_judgment_with_a_non_boolean_verdict_fails(tmp_path: Path) -> None:
    source = PLAN + "def judge(check_id, context, evidence):\n    return Judgment(1, None)\n"
    with OracleProcess(load(_pack_with_oracle(tmp_path, source))) as oracle:
        assert not oracle.judge("answer", None, _answer({})).passed


def test_a_diagnostic_too_deep_to_record_fails_the_check(tmp_path: Path) -> None:
    source = PLAN + (
        "def judge(check_id, context, evidence):\n"
        "    diagnostic = 0\n"
        "    for _ in range(evidence.files[0].value['levels'] - 1):\n"
        "        diagnostic = [diagnostic]\n"
        "    return Judgment(True, diagnostic)\n"
    )
    with OracleProcess(load(_pack_with_oracle(tmp_path, source))) as oracle:
        deepest = oracle.judge("answer", None, _answer({"levels": process.MAX_DIAGNOSTIC_DEPTH}))
        assert deepest.passed
        levels = process.MAX_DIAGNOSTIC_DEPTH + 1
        too_deep = oracle.judge("answer", None, _answer({"levels": levels}))
        assert not too_deep.passed and "too deeply" in str(too_deep.diagnostic)


def test_a_context_too_deep_to_send_fails_the_check() -> None:
    context: JsonValue = 0
    for _ in range(63):
        context = [context]
    with OracleProcess(load(F1)) as oracle:
        judgment = oracle.judge("answer", context, _answer({"sum": 1294}))
        assert not judgment.passed and "cannot be sent" in str(judgment.diagnostic)


def test_a_failing_plan_is_a_host_error(tmp_path: Path) -> None:
    source = (
        "def plan(resources, seed):\n    return resources.read('../task.toml')\n"
        "def judge(check_id, context, evidence):\n    return None\n"
    )
    with (
        OracleProcess(load(_pack_with_oracle(tmp_path, source))) as oracle,
        pytest.raises(HostError),
    ):
        oracle.plan(0)


def test_the_worker_refuses_to_load_a_forbidden_oracle(tmp_path: Path) -> None:
    source = PLAN + (
        "def judge(check_id, context, evidence):\n    import importlib\n    return None\n"
    )
    pack = _pack_with_oracle(tmp_path, source)
    with OracleProcess(load(pack)) as oracle, pytest.raises(HostError):
        oracle.plan(0)


def test_the_oracle_writes_no_bytecode(tmp_path: Path) -> None:
    pack = _pack_with_oracle(tmp_path, (F1 / "hidden" / "oracle.py").read_text())
    with OracleProcess(load(pack)) as oracle:
        oracle.plan(0)
    assert not list(pack.rglob("__pycache__"))
