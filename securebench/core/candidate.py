"""The candidate manifest (architecture Section 5.1).

A candidate is (baseline, scope, delta). The manifest records the baseline
image, the scope it was captured under, and the delta entries. Its identity is
the digest of its canonical JSON form. Entry paths are canonical absolute paths
inside the scope, strictly ascending by UTF-8 bytes.
"""

from dataclasses import dataclass

from securebench.core import hashing, jsondata, paths
from securebench.core.errors import Rejected
from securebench.core.jsondata import JsonValue


@dataclass(frozen=True)
class WriteEntry:
    """A regular file: its content's digest and size, and its executable bit."""

    path: str
    sha256: str
    size: int
    executable: bool


@dataclass(frozen=True)
class DirEntry:
    path: str


@dataclass(frozen=True)
class SymlinkEntry:
    path: str
    target: str


@dataclass(frozen=True)
class DeleteEntry:
    path: str


type ManifestEntry = WriteEntry | DirEntry | SymlinkEntry | DeleteEntry


@dataclass(frozen=True)
class Manifest:
    baseline_image: str
    scope: JsonValue
    entries: tuple[ManifestEntry, ...]

    def to_json(self) -> JsonValue:
        """The manifest as JSON data; `encode` of this is what the store holds."""
        return {
            "baseline_image": self.baseline_image,
            "entries": [_entry_to_json(entry) for entry in self.entries],
            "scope": self.scope,
        }

    @property
    def id(self) -> str:
        """The candidate identity: the digest of the canonical encoding."""
        return jsondata.digest(self.to_json())


def manifest_from_json(value: JsonValue) -> Manifest:
    """Parse manifest data with exact key sets and strict types.

    Checks shape only: paths canonical and strictly ascending, digests
    well-formed, integers not booleans. Scope and bound checks belong to
    `candidate`. Raises `Rejected`.
    """
    top = _exact_object(value, {"baseline_image", "entries", "scope"}, "manifest")
    image = top["baseline_image"]
    if not isinstance(image, str) or not image:
        raise Rejected("manifest baseline_image must be a non-empty string")
    raw_entries = top["entries"]
    if not isinstance(raw_entries, list):
        raise Rejected("manifest entries must be an array")
    entries: list[ManifestEntry] = []
    previous: bytes | None = None
    for raw in raw_entries:
        entry = _entry_from_json(raw)
        key = entry.path.encode("utf-8")
        if previous is not None and key <= previous:
            raise Rejected(f"manifest entry {entry.path!r} is out of order or repeated")
        previous = key
        entries.append(entry)
    return Manifest(image, top["scope"], tuple(entries))


_KEYS: dict[str, set[str]] = {
    "write": {"kind", "path", "sha256", "size", "executable"},
    "dir": {"kind", "path"},
    "symlink": {"kind", "path", "target"},
    "delete": {"kind", "path"},
}

MAX_FILE_BYTES = 1 << 40


def _entry_to_json(entry: ManifestEntry) -> JsonValue:
    match entry:
        case WriteEntry():
            return {
                "executable": entry.executable,
                "kind": "write",
                "path": entry.path,
                "sha256": entry.sha256,
                "size": entry.size,
            }
        case DirEntry():
            return {"kind": "dir", "path": entry.path}
        case SymlinkEntry():
            return {"kind": "symlink", "path": entry.path, "target": entry.target}
        case DeleteEntry():
            return {"kind": "delete", "path": entry.path}


def _entry_from_json(raw: JsonValue) -> ManifestEntry:
    if not isinstance(raw, dict):
        raise Rejected("manifest entry must be an object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in _KEYS:
        raise Rejected(f"manifest entry kind {kind!r} is unknown")
    fields = _exact_object(raw, _KEYS[kind], f"{kind} entry")
    path = fields["path"]
    if not isinstance(path, str):
        raise Rejected("manifest entry path must be a string")
    paths.check_absolute(path)
    match kind:
        case "write":
            digest, size, executable = fields["sha256"], fields["size"], fields["executable"]
            if not isinstance(digest, str):
                raise Rejected("write entry sha256 must be a string")
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
                raise Rejected(f"write entry size for {path!r} is not a valid integer")
            if type(executable) is not bool:
                raise Rejected(f"write entry executable for {path!r} must be a boolean")
            return WriteEntry(path, hashing.check_digest(digest), size, executable)
        case "dir":
            return DirEntry(path)
        case "symlink":
            target = fields["target"]
            if not isinstance(target, str):
                raise Rejected("symlink entry target must be a string")
            return SymlinkEntry(path, target)
        case _:
            return DeleteEntry(path)


def _exact_object(value: JsonValue, keys: set[str], what: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise Rejected(f"{what} must be an object")
    if set(value) != keys:
        raise Rejected(f"{what} has keys {sorted(value)}, expected {sorted(keys)}")
    return value
