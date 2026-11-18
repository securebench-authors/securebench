"""Static pack validation (task format)."""

import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from securebench.core.errors import PackError, Rejected
from securebench.core.task import Parser
from securebench.taskspec.domains import check_domain
from securebench.taskspec.load import load, pack_digest

F1 = Path(__file__).parents[2] / "fixtures" / "f1-answer-file" / "task"


def _copy(tmp_path: Path) -> Path:
    pack = tmp_path / "pack"
    shutil.copytree(F1, pack)
    return pack


def _edit_toml(pack: Path, old: str, new: str) -> None:
    path = pack / "task.toml"
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def test_f1_loads() -> None:
    task = load(F1)
    assert task.id == "f1-answer-file"
    assert task.public.workdir == "/srv"
    assert task.scope.roots[0].path == "/srv"
    assert task.artifact_checks[0].files[0].parser is Parser.JSON
    assert task.public.public_assets[0].target == "/data/numbers.txt"
    assert task.digest.startswith("sha256:")


def test_pack_digest_covers_content_and_executable_bit(tmp_path: Path) -> None:
    pack = _copy(tmp_path)
    before = pack_digest(pack)
    (pack / "public" / "numbers.txt").chmod(0o755)
    after_mode = pack_digest(pack)
    (pack / "public" / "numbers.txt").write_text("1\n")
    assert len({before, after_mode, pack_digest(pack)}) == 3


EDITS: list[tuple[str, str, str]] = [
    ("unknown key", 'id = "f1-answer-file"', 'id = "f1-answer-file"\nflavor = "x"'),
    ("bad name", 'id = "f1-answer-file"', 'id = "F1"'),
    (
        "bool as int",
        "max_entries = 64\nmax_bytes = 65536\n\n[[scope",
        "max_entries = true\nmax_bytes = 65536\n\n[[scope",
    ),
    (
        "root bound over scope",
        "max_entries = 64\nmax_bytes = 65536\n\n[[public",
        "max_entries = 65\nmax_bytes = 65536\n\n[[public",
    ),
    ("root is /", 'path = "/srv"', 'path = "/"'),
    ("protected root", 'path = "/srv"', 'path = "/etc/ssh/keys"'),
    ("root contains protected", 'path = "/srv"', 'path = "/var"'),
    ("case alias of protected", 'path = "/srv"', 'path = "/TMP/x"'),
    ("noncanonical root", 'path = "/srv"', 'path = "/srv/"'),
    ("workdir outside scope", 'workdir = "/srv"', 'workdir = "/opt"'),
    ("asset over scope root", 'target = "/data/numbers.txt"', 'target = "/srv/numbers.txt"'),
    ("asset missing", 'source = "numbers.txt"', 'source = "missing.txt"'),
    ("bad domain", "allowed_domains = []", 'allowed_domains = ["*.example.com"]'),
    ("ip domain", "allowed_domains = []", 'allowed_domains = ["10.0.0.1"]'),
    ("duplicate domain", "allowed_domains = []", 'allowed_domains = ["a.com", "a.com"]'),
    ("unknown parser", 'parser = "json"', 'parser = "csv"'),
    ("artifact outside scope", 'path = "/srv/answer.json"', 'path = "/opt/answer.json"'),
    ("artifact in .git", 'path = "/srv/answer.json"', 'path = "/srv/.git/answer.json"'),
    ("short digest", "@sha256:02108f5d", "@sha256:02108f5"),
    (
        "tag instead of digest",
        "python@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d",
        "python:3.12",
    ),
    ("bad pattern", "symlinks = false", 'symlinks = false\nexclude = ["tests/[ab]"]'),
    ("git dir not .git", "symlinks = false", 'symlinks = false\ngit_directories = ["repo"]'),
]


@pytest.mark.parametrize(("label", "old", "new"), EDITS, ids=[edit[0] for edit in EDITS])
def test_invalid_task_toml_is_rejected(tmp_path: Path, label: str, old: str, new: str) -> None:
    pack = _copy(tmp_path)
    _edit_toml(pack, old, new)
    with pytest.raises(PackError):
        load(pack)


def test_overlapping_roots_are_rejected(tmp_path: Path) -> None:
    pack = _copy(tmp_path)
    extra = '[[scope.roots]]\npath = "/SRV/sub"\nsymlinks = false\nmax_entries = 1\nmax_bytes = 1\n'
    _edit_toml(pack, "[[public_assets]]", extra + "\n[[public_assets]]")
    with pytest.raises(PackError, match="overlaps"):
        load(pack)


def _symlink_into_hidden(pack: Path) -> None:
    os.symlink("../hidden/expected.json", pack / "public" / "leak.json")


def _fifo(pack: Path) -> None:
    os.mkfifo(pack / "public" / "pipe")


def _stray_top_level(pack: Path) -> None:
    (pack / "notes.txt").write_text("x")


def _no_oracle(pack: Path) -> None:
    (pack / "hidden" / "oracle.py").unlink()


def _lane_is_file(pack: Path) -> None:
    (pack / "evaluation").write_text("x")


@pytest.mark.parametrize(
    "damage", [_symlink_into_hidden, _fifo, _stray_top_level, _no_oracle, _lane_is_file]
)
def test_pack_layout_violations_are_rejected(
    tmp_path: Path, damage: Callable[[Path], None]
) -> None:
    pack = _copy(tmp_path)
    damage(pack)
    with pytest.raises(PackError):
        load(pack)


def test_pack_itself_may_not_be_a_symlink(tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(F1)
    with pytest.raises(PackError):
        load(link)


@pytest.mark.parametrize(
    "domain",
    [
        "localhost",
        "a.localhost",
        "com",
        "Example.com",
        "a..com",
        "-a.com",
        "a_b.com",
        "a.com:80",
        "https://a.com",
        "a.com/x",
        "1.2.3.4",
        "x" * 64 + ".com",
    ],
)
def test_domain_rules(domain: str) -> None:
    with pytest.raises(Rejected):
        check_domain(domain)


def test_domain_trailing_dot_is_removed() -> None:
    assert check_domain("pypi.org.") == "pypi.org"
