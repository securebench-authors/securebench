"""Run directories: append-only records, manifest integrity, resume rules (Section 11)."""

from pathlib import Path

import pytest

from securebench.core.errors import HostError
from securebench.core.jsondata import JsonValue
from securebench.results.run import RunDirectory

CONFIG: JsonValue = {"seed": 1}


def test_records_are_append_only_and_listed(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        run.record("task-a", 1, {"status": "invalid"})
        assert run.next_attempt("task-a") == 2
        run.record("task-a", 2, {"status": "passed"})
        with pytest.raises(HostError, match="never overwritten"):
            run.record("task-a", 2, {"status": "failed"})
        assert run.attempts("task-a") == [{"status": "invalid"}, {"status": "passed"}]


def test_logs_are_stored_byte_for_byte_and_never_overwritten(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        run.save_log("task-a", 1, "transcript", b"\xff untrusted")
        with pytest.raises(HostError, match="never overwritten"):
            run.save_log("task-a", 1, "transcript", b"replaced")
    log = tmp_path / "run" / "attempts" / "task-a" / "1.transcript"
    assert log.read_bytes() == b"\xff untrusted"


def test_resume_requires_the_same_configuration(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        run.record("task-a", 1, {"status": "passed"})
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        assert run.next_attempt("task-a") == 2
    with (
        pytest.raises(HostError, match="different configuration"),
        RunDirectory(tmp_path / "run", {"seed": 2}),
    ):
        pass


def test_tampering_is_detected_on_resume(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        run.record("task-a", 1, {"status": "failed"})
    (tmp_path / "run" / "attempts" / "task-a" / "1.json").write_text('{"status":"passed"}\n')
    with pytest.raises(HostError, match="changed"), RunDirectory(tmp_path / "run", CONFIG):
        pass


def test_one_process_per_run(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG), pytest.raises(HostError, match="another process"):
        with RunDirectory(tmp_path / "run", CONFIG):
            pass


def test_finish_writes_a_root_digest_and_closes_the_run(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run:
        run.record("task-a", 1, {"status": "passed"})
        digest = run.finish()
    assert digest.startswith("sha256:")
    with pytest.raises(HostError, match="finished"), RunDirectory(tmp_path / "run", CONFIG):
        pass


def test_task_names_cannot_escape_the_run_directory(tmp_path: Path) -> None:
    with RunDirectory(tmp_path / "run", CONFIG) as run, pytest.raises(HostError):
        run.record("../x", 1, {})
