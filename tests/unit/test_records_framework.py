"""The framework provenance of a record: commit and dirty flag (Section 11)."""

import subprocess
from pathlib import Path

import pytest

from securebench.results import records


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(repository), *arguments], check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "securebench").mkdir()
    (tmp_path / "securebench" / "code.py").write_text("x = 1\n")
    (tmp_path / "conversions").mkdir()
    (tmp_path / "conversions" / "pack.toml").write_text("a = 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    monkeypatch.setattr(records, "REPOSITORY", tmp_path)
    return tmp_path


def _dirty() -> bool:
    provenance = records.framework()
    assert isinstance(provenance, dict)
    return provenance["dirty"] is True


def test_a_clean_tree_is_not_dirty(repository: Path) -> None:
    assert not _dirty()


def test_a_changed_task_pack_does_not_make_the_code_dirty(repository: Path) -> None:
    (repository / "conversions" / "pack.toml").write_text("a = 2\n")
    assert not _dirty()


def test_a_changed_code_file_makes_the_record_dirty(repository: Path) -> None:
    (repository / "securebench" / "code.py").write_text("x = 2\n")
    assert _dirty()
