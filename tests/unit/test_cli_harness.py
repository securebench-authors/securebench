"""Command-line behavior: --reasoning-effort and validate output (0035)."""

from pathlib import Path

import pytest

from securebench.runner.cli import main
from securebench.taskspec.load import pack_digest


def test_reasoning_effort_is_refused_for_a_scripted_harness(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arguments = ["run", str(tmp_path), "--run-dir", str(tmp_path / "run")]
    arguments += ["--harness", "scripted:x.sh", "--reasoning-effort", "low"]
    assert main(arguments) == 2
    message = "--reasoning-effort applies only to the codex and claude-code harnesses"
    assert message in capsys.readouterr().err


def test_validate_prints_the_pack_digest(capsys: pytest.CaptureFixture[str]) -> None:
    pack = Path(__file__).parents[2] / "fixtures" / "f1-answer-file" / "task"
    assert main(["validate", str(pack)]) == 0
    assert capsys.readouterr().out == f"f1-answer-file: valid, pack {pack_digest(pack)}\n"
