"""A compromised utility environment forging its output."""

import pytest

from securebench.candidate import stream
from securebench.candidate.state import check_tree
from securebench.core import hashing, jsondata
from securebench.core.errors import Rejected
from securebench.core.jsondata import JsonValue
from securebench.core.task import Scope, ScopeRoot

SCOPE = Scope((ScopeRoot("/srv", ("tests",), (), False, 100, 1 << 20),), 100, 1 << 20)


def _stream(*records: JsonValue, end: bool = True) -> bytes:
    data = b"".join(jsondata.encode(record) for record in records)
    return data + (jsondata.encode({"t": "end"}) if end else b"")


def _parse(data: bytes) -> stream.Walk:
    walk = stream.parse_walk(SCOPE, stream.records(data), hashing.sha256)
    check_tree(SCOPE, walk.state)
    return walk


@pytest.mark.parametrize(
    "data",
    [
        _stream({"t": "dir", "p": "/etc"}),
        _stream({"t": "dir", "p": "/srv"}),
        _stream({"t": "dir", "p": "/srv/../etc"}),
        _stream({"t": "dir", "p": "/srv/a"}, {"t": "dir", "p": "/srv/a"}),
        _stream({"t": "dir", "p": "/srv/a", "extra": 1}),
        _stream({"t": "file", "p": "/srv/f", "size": 1, "x": False, "sha256": "zz"}),
        _stream({"t": "file", "p": "/srv/f", "size": True, "x": False, "sha256": "a" * 64}),
        _stream({"t": "file", "p": "/srv/f", "size": 1, "x": 1, "sha256": "a" * 64}),
        _stream({"t": "symlink", "p": "/srv/l", "target": "x"}, {"t": "dir", "p": "/srv/l/d"}),
        _stream({"t": "dir", "p": "/srv/orphan/d"}),
        _stream({"t": "verdict", "p": "/srv/x"}),
        _stream({"t": "dir", "p": "/srv/a"}, end=False),
        _stream({"t": "rejected", "reason": "special file"}),
        _stream({"t": "dir", "p": "/srv/a"}) + b"trailing",
        b'{"t":"file","p":"/srv/f","size":10,"x":false,"blob":true}\nabc',
        b"x" * 70_000,
    ],
)
def test_forged_walk_output_is_rejected(data: bytes) -> None:
    with pytest.raises(Rejected):
        _parse(data)


def test_excluded_paths_are_dropped_whatever_the_utility_sent() -> None:
    walk = _parse(_stream({"t": "dir", "p": "/srv/tests"}, {"t": "dir", "p": "/srv/TESTS"}))
    assert walk.state == {}


def test_host_hashes_blob_content_itself() -> None:
    data = b'{"blob":true,"p":"/srv/f","size":3,"t":"file","x":false}\nabc' + jsondata.encode(
        {"t": "end"}
    )
    walk = _parse(data)
    assert walk.blobs["/srv/f"] == hashing.sha256(b"abc")
