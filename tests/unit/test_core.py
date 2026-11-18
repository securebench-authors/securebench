"""Unit tests for `securebench.core`."""

import pytest

from securebench.core import hashing, jsondata, paths
from securebench.core.candidate import (
    DeleteEntry,
    DirEntry,
    Manifest,
    SymlinkEntry,
    WriteEntry,
    manifest_from_json,
)
from securebench.core.errors import Rejected
from securebench.core.limits import Limits
from securebench.core.verdict import FailureClass, Status, Verdict

DIGEST = "sha256:" + "a" * 64


def test_canonical_encoding_is_sorted_compact_utf8_with_newline() -> None:
    assert jsondata.encode({"b": 1, "a": ["é", 1.5, None, True]}) == (
        '{"a":["é",1.5,null,true],"b":1}\n'.encode()
    )


def test_canonical_encoding_test_vectors_are_stable() -> None:
    assert jsondata.digest({"x": [1, 2]}) == (
        "sha256:d8c17a1cbc8452732fab43a39c20436463f5f6a4f95378396ee7c8ac35663428"
    )


def test_decode_round_trips_canonical_encoding() -> None:
    value: jsondata.JsonValue = {"k": [1, -2, 0.25, "s", {"n": None}]}
    assert jsondata.decode(jsondata.encode(value), 1000) == value


def test_digest_check_accepts_only_lowercase_sha256() -> None:
    assert hashing.check_digest(DIGEST) == DIGEST
    for bad in ["sha256:" + "A" * 64, "sha256:../../x", "sha256:" + "a" * 63, "md5:" + "a" * 64]:
        with pytest.raises(Rejected):
            hashing.check_digest(bad)


@pytest.mark.parametrize(
    "path", ["/", "//app", "/app/", "/a//b", "/a/./b", "/a/../b", "/a\\b", "/a\x00b", "rel"]
)
def test_absolute_paths_must_be_canonical(path: str) -> None:
    with pytest.raises(Rejected):
        paths.check_absolute(path)


def test_path_bounds_are_enforced() -> None:
    with pytest.raises(Rejected):
        paths.check_absolute("/" + "/".join(["a"] * 129))
    with pytest.raises(Rejected):
        paths.check_absolute("/" + "a" * 4096)
    with pytest.raises(Rejected):
        paths.check_absolute("/\udc80")


def test_containment_is_exact_but_overlap_is_folded() -> None:
    assert paths.is_within("/app/x", "/app")
    assert not paths.is_within("/App/x", "/app")
    assert not paths.is_within("/apple", "/app")
    assert paths.overlaps_folded("/App/x", "/app")
    assert paths.overlaps_folded("/café", "/café")
    assert not paths.overlaps_folded("/apple", "/app")


def test_relative_to() -> None:
    assert paths.relative_to("/app/a/b", "/app") == "a/b"
    assert paths.relative_to("/app", "/app") == ""
    with pytest.raises(Rejected):
        paths.relative_to("/apple", "/app")


def test_manifest_round_trips_and_has_a_stable_identity() -> None:
    manifest = Manifest(
        "img@" + DIGEST,
        {"roots": []},
        (
            DirEntry("/app/d"),
            WriteEntry("/app/f", DIGEST, 3, True),
            SymlinkEntry("/app/l", "f"),
            DeleteEntry("/app/z"),
        ),
    )
    parsed = manifest_from_json(jsondata.decode(jsondata.encode(manifest.to_json()), 10_000))
    assert parsed == manifest
    assert parsed.id == manifest.id


def _manifest_json(*entries: jsondata.JsonValue) -> jsondata.JsonValue:
    return {"baseline_image": "img", "scope": {}, "entries": list(entries)}


@pytest.mark.parametrize(
    "entries",
    [
        [{"kind": "dir", "path": "/b"}, {"kind": "dir", "path": "/a"}],
        [{"kind": "dir", "path": "/a"}, {"kind": "dir", "path": "/a"}],
        [{"kind": "dir", "path": "/a", "extra": 1}],
        [{"kind": "write", "path": "/a", "sha256": DIGEST, "size": True, "executable": False}],
        [{"kind": "write", "path": "/a", "sha256": DIGEST, "size": 1, "executable": 1}],
        [{"kind": "write", "path": "/a", "sha256": "sha256:../x", "size": 1, "executable": False}],
        [{"kind": "chmod", "path": "/a"}],
        [{"kind": "dir", "path": "/a/../b"}],
    ],
)
def test_manifest_parsing_is_total(entries: list[jsondata.JsonValue]) -> None:
    with pytest.raises(Rejected):
        manifest_from_json(_manifest_json(*entries))


def test_verdict_requires_failure_class_exactly_when_failed() -> None:
    Verdict(Status.FAILED, FailureClass.ORACLE, ())
    with pytest.raises(ValueError):
        Verdict(Status.FAILED, None, ())
    with pytest.raises(ValueError):
        Verdict(Status.PASSED, FailureClass.ORACLE, ())


def test_limits_reject_booleans_and_non_positive_values() -> None:
    with pytest.raises(ValueError):
        Limits(True, 1, 1, 1, 1)
    with pytest.raises(ValueError):
        Limits(1, 0, 1, 1, 1)
