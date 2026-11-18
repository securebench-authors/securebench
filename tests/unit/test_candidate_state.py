"""Delta semantics, the utility walker and the stream parser, without Docker."""

import io
import os
from pathlib import Path

import pytest

from securebench.candidate import stream
from securebench.candidate.state import (
    BaselineIndex,
    DirNode,
    FileNode,
    LinkNode,
    State,
    apply_delta,
    check_manifest,
    check_tree,
    compute_delta,
)
from securebench.core import hashing, jsondata
from securebench.core.candidate import DeleteEntry, DirEntry, Manifest, SymlinkEntry, WriteEntry
from securebench.core.errors import Rejected
from securebench.core.task import Scope, ScopeRoot
from securebench_utility import utility

A = hashing.sha256(b"a")
B = hashing.sha256(b"b")


def _scope(symlinks: bool = True, exclude: tuple[str, ...] = ()) -> Scope:
    return Scope((ScopeRoot("/srv", exclude, (), symlinks, 1000, 1 << 20),), 1000, 1 << 20)


def _index(nodes: State, keeps: frozenset[str] = frozenset()) -> BaselineIndex:
    return BaselineIndex("img", _scope().to_json(), nodes, keeps, frozenset())


def test_executable_bit_alone_is_a_change() -> None:
    index = _index({"/srv/f": FileNode(A, 1, False)})
    entries = compute_delta(_scope(), index, {"/srv/f": FileNode(A, 1, True)})
    assert entries == (WriteEntry("/srv/f", A, 1, True),)


def test_unchanged_state_gives_an_empty_delta() -> None:
    nodes: State = {"/srv/d": DirNode(), "/srv/d/f": FileNode(A, 1, False)}
    assert compute_delta(_scope(), _index(nodes), dict(nodes)) == ()


def test_directory_replaced_by_file_deletes_every_descendant() -> None:
    index = _index(
        {
            "/srv/d": DirNode(),
            "/srv/d/a": FileNode(A, 1, False),
            "/srv/d/e": DirNode(),
            "/srv/d/e/b": FileNode(B, 1, False),
        }
    )
    entries = compute_delta(_scope(), index, {"/srv/d": FileNode(B, 1, False)})
    assert entries == (
        WriteEntry("/srv/d", B, 1, False),
        DeleteEntry("/srv/d/a"),
        DeleteEntry("/srv/d/e"),
        DeleteEntry("/srv/d/e/b"),
    )


def test_deletion_bomb_is_charged_per_descendant() -> None:
    nodes: State = {"/srv/d": DirNode()}
    nodes.update({f"/srv/d/{i}": FileNode(A, 1, False) for i in range(20)})
    scope = Scope((ScopeRoot("/srv", (), (), False, 1000, 1 << 20),), 10, 1 << 20)
    with pytest.raises(Rejected, match="entries"):
        compute_delta(scope, _index(nodes), {})


def test_new_symlinks_must_be_permitted_and_contained() -> None:
    index = _index({"/srv/d": DirNode()})
    ok = compute_delta(_scope(), index, {"/srv/d": DirNode(), "/srv/d/l": LinkNode("../x")})
    assert ok[0] == SymlinkEntry("/srv/d/l", "../x")
    for target in ("../../etc/shadow", "/etc/shadow", "", "a\\b"):
        with pytest.raises(Rejected):
            compute_delta(_scope(), index, {"/srv/d": DirNode(), "/srv/d/l": LinkNode(target)})
    with pytest.raises(Rejected):
        compute_delta(_scope(symlinks=False), index, {"/srv/d": DirNode(), "/srv/l": LinkNode("d")})


def test_unchanged_baseline_symlinks_are_not_validated() -> None:
    nodes: State = {"/srv/null": LinkNode("/dev/null")}
    assert compute_delta(_scope(symlinks=False), _index(nodes), dict(nodes)) == ()


def test_directories_holding_excluded_content_are_kept() -> None:
    index = _index({"/srv/d": DirNode(), "/srv/d/a": FileNode(A, 1, False)}, frozenset({"/srv/d"}))
    assert compute_delta(_scope(), index, {}) == (DeleteEntry("/srv/d/a"),)
    with pytest.raises(Rejected):
        compute_delta(_scope(), index, {"/srv/d": FileNode(A, 1, False)})


def test_check_tree_rejects_orphans_and_parents_that_are_not_directories() -> None:
    with pytest.raises(Rejected):
        check_tree(_scope(), {"/srv/l": LinkNode("x"), "/srv/l/f": FileNode(A, 1, False)})
    with pytest.raises(Rejected):
        check_tree(_scope(), {"/srv/missing/f": FileNode(A, 1, False)})
    with pytest.raises(Rejected):
        check_tree(_scope(), {"/opt/f": FileNode(A, 1, False)})


def test_stored_candidates_are_rechecked_against_the_current_task() -> None:
    index = _index({"/srv/d": DirNode()})
    manifest = Manifest("img", _scope().to_json(), (SymlinkEntry("/srv/l", "d"),))
    check_manifest(_scope(), index, manifest)
    stricter = _scope(symlinks=False)
    with pytest.raises(Rejected):
        check_manifest(stricter, index, Manifest("img", stricter.to_json(), manifest.entries))
    with pytest.raises(Rejected):
        check_manifest(_scope(), index, Manifest("other", _scope().to_json(), manifest.entries))


def test_apply_delta_reconstructs_the_final_state() -> None:
    index = _index({"/srv/d": DirNode(), "/srv/d/a": FileNode(A, 1, False)})
    manifest = Manifest("img", {}, (DirEntry("/srv/e"), DeleteEntry("/srv/d/a")))
    assert apply_delta(index, manifest) == {"/srv/d": DirNode(), "/srv/e": DirNode()}


def _walk(target: Path, scope: Scope, known: dict[str, tuple[str, bool]] | None) -> bytes:
    out = io.BytesIO()
    writer = utility.Output(out)
    try:
        utility.walk(
            writer,
            str(target),
            jsondata.decode(jsondata.encode(scope.to_json()), 1 << 20),  # type: ignore[arg-type]
            utility.Budget({"max_entries": scope.max_entries, "max_bytes": scope.max_bytes}, 60),
            known,
            set(),
        )
    except utility.Rejection as error:
        writer.record({"t": "rejected", "reason": str(error)})
        return out.getvalue()
    writer.record({"t": "end"})
    return out.getvalue()


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "target" / "srv"
    (root / "d").mkdir(parents=True)
    (root / "d" / "a.txt").write_bytes(b"a")
    (root / "run.sh").write_bytes(b"b")
    (root / "run.sh").chmod(0o755)
    (root / "tests").mkdir()
    (root / "tests" / "t.py").write_bytes(b"t")
    return tmp_path / "target"


def test_utility_walk_and_host_parser_agree(tmp_path: Path) -> None:
    target = _tree(tmp_path)
    scope = _scope(exclude=("tests",))
    blobs: list[bytes] = []
    walk = stream.parse_walk(
        scope,
        stream.records(_walk(target, scope, {})),
        lambda d: blobs.append(d) or hashing.sha256(d),
    )
    assert walk.state == {
        "/srv/d": DirNode(),
        "/srv/d/a.txt": FileNode(A, 1, False),
        "/srv/run.sh": FileNode(B, 1, True),
    }
    assert walk.keeps == {"/srv"}
    assert sorted(blobs) == [b"a", b"b"]


def test_utility_sends_no_content_for_known_files(tmp_path: Path) -> None:
    target = _tree(tmp_path)
    known = {
        "/srv/d/a.txt": (hashing.hex_part(A), False),
        "/srv/run.sh": (hashing.hex_part(B), True),
    }
    data = _walk(target, _scope(exclude=("tests",)), known)
    assert b'"blob":true' not in data


def test_utility_rejects_special_files_and_unreadable_files(tmp_path: Path) -> None:
    target = _tree(tmp_path)
    os.mkfifo(target / "srv" / "pipe")
    with pytest.raises(Rejected, match="named pipe"):
        list(stream.records(_walk(target, _scope(exclude=("tests",)), None)))
    (target / "srv" / "pipe").unlink()
    (target / "srv" / "d" / "a.txt").chmod(0)
    try:
        if os.access(target / "srv" / "d" / "a.txt", os.R_OK):
            pytest.skip("running as a user that can read mode-000 files")
        with pytest.raises(Rejected, match="cannot be read"):
            list(stream.records(_walk(target, _scope(exclude=("tests",)), None)))
    finally:
        (target / "srv" / "d" / "a.txt").chmod(0o644)


def test_utility_enforces_bounds_while_walking(tmp_path: Path) -> None:
    target = _tree(tmp_path)
    small = Scope((ScopeRoot("/srv", ("tests",), (), False, 2, 1 << 20),), 1000, 1 << 20)
    with pytest.raises(Rejected, match="entries"):
        list(stream.records(_walk(target, small, None)))
    tiny = Scope((ScopeRoot("/srv", ("tests",), (), False, 100, 1),), 1000, 1)
    with pytest.raises(Rejected, match="bytes"):
        list(stream.records(_walk(target, tiny, None)))


def test_utility_never_follows_symlinks(tmp_path: Path) -> None:
    target = _tree(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("s")
    (target / "srv" / "link").symlink_to(outside)
    walk = stream.parse_walk(
        _scope(), stream.records(_walk(target, _scope(), None)), hashing.sha256
    )
    assert walk.state["/srv/link"] == LinkNode(str(outside))
    assert not any(path.startswith("/srv/link/") for path in walk.state)
