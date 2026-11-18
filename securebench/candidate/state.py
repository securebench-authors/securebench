"""Filesystem states inside a scope, and the pure delta semantics between them.

A state maps canonical absolute paths below the scope roots (never a root
itself) to nodes. Excluded paths never appear in a state.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from securebench.core import jsondata, paths
from securebench.core.candidate import (
    DeleteEntry,
    DirEntry,
    Manifest,
    ManifestEntry,
    SymlinkEntry,
    WriteEntry,
)
from securebench.core.errors import Rejected
from securebench.core.jsondata import JsonValue
from securebench.core.task import Scope, ScopeRoot


@dataclass(frozen=True)
class FileNode:
    sha256: str
    size: int
    executable: bool


@dataclass(frozen=True)
class DirNode:
    pass


@dataclass(frozen=True)
class LinkNode:
    target: str


type Node = FileNode | DirNode | LinkNode
type State = dict[str, Node]


@dataclass(frozen=True)
class BaselineIndex:
    """Every non-excluded baseline entry inside the scope.

    `keeps` lists directories that hold excluded entries; they cannot be
    deleted, because excluded content keeps its baseline state. `blobs` lists
    the baseline files whose content is in the store (artifact-check paths).
    """

    image: str
    scope: JsonValue
    nodes: State
    keeps: frozenset[str]
    blobs: frozenset[str]

    def to_json(self) -> JsonValue:
        blobs: list[JsonValue] = [path for path in sorted(self.blobs, key=_utf8)]
        keeps: list[JsonValue] = [path for path in sorted(self.keeps, key=_utf8)]
        nodes: dict[str, JsonValue] = {
            path: node_to_json(node) for path, node in self.nodes.items()
        }
        return {
            "blobs": blobs,
            "image": self.image,
            "keeps": keeps,
            "nodes": nodes,
            "scope": self.scope,
        }

    @property
    def digest(self) -> str:
        return jsondata.digest(self.to_json())


def node_to_json(node: Node) -> JsonValue:
    match node:
        case FileNode():
            return ["file", node.sha256, node.size, node.executable]
        case DirNode():
            return ["dir"]
        case LinkNode():
            return ["symlink", node.target]


def root_of(scope: Scope, path: str) -> ScopeRoot | None:
    for root in scope.roots:
        if paths.is_within(path, root.path):
            return root
    return None


def check_tree(scope: Scope, state: Mapping[str, Node]) -> None:
    """Every parent is a directory in the state, and every bound holds."""
    entries: dict[str, int] = {}
    sizes: dict[str, int] = {}
    for path, node in state.items():
        root = root_of(scope, path)
        if root is None or path == root.path:
            raise Rejected(f"{path!r} is outside the scope")
        parent = path.rsplit("/", 1)[0]
        if parent != root.path and not isinstance(state.get(parent), DirNode):
            raise Rejected(f"the parent of {path!r} is not a directory")
        entries[root.path] = entries.get(root.path, 0) + 1
        if isinstance(node, FileNode):
            sizes[root.path] = sizes.get(root.path, 0) + node.size
    for root in scope.roots:
        if entries.get(root.path, 0) > root.max_entries:
            raise Rejected(f"scope root {root.path} has more entries than its bound")
        if sizes.get(root.path, 0) > root.max_bytes:
            raise Rejected(f"scope root {root.path} holds more bytes than its bound")
    if len(state) > scope.max_entries or sum(sizes.values()) > scope.max_bytes:
        raise Rejected("the scope exceeds its entry or byte bound")


def check_symlink(root: ScopeRoot, path: str, target: str) -> None:
    """A candidate-authored link: permitted, relative, contained in its root."""
    if not root.symlinks:
        raise Rejected(f"symlink {path!r}: the scope root {root.path} does not permit symlinks")
    if not target or target.startswith("/") or "\\" in target or "\x00" in target:
        raise Rejected(f"symlink {path!r} has an absolute or malformed target")
    if len(target.encode("utf-8")) > paths.MAX_PATH_BYTES:
        raise Rejected(f"symlink {path!r} has an over-long target")
    depth = len(paths.components(paths.relative_to(path, root.path))) - 1
    for part in target.split("/"):
        if part == "..":
            depth -= 1
        elif part not in ("", "."):
            depth += 1
        if depth < 0:
            raise Rejected(f"symlink {path!r} escapes its scope root")


def compute_delta(
    scope: Scope, index: BaselineIndex, final: Mapping[str, Node]
) -> tuple[ManifestEntry, ...]:
    """The delta from the baseline index to the final state (architecture Section 5.3).

    Raises `Rejected` for candidate faults: a disallowed or escaping symlink, a
    directory that holds excluded content turned into something else, or a
    delta over the scope's bounds.
    """
    entries: list[ManifestEntry] = []
    for path, node in final.items():
        base = index.nodes.get(path)
        root = root_of(scope, path)
        if root is None:
            raise Rejected(f"{path!r} is outside the scope")
        if base == node:
            continue
        if path in index.keeps and not isinstance(node, DirNode):
            raise Rejected(f"{path!r} holds excluded content and cannot change type")
        match node:
            case FileNode():
                entries.append(WriteEntry(path, node.sha256, node.size, node.executable))
            case DirNode():
                entries.append(DirEntry(path))
            case LinkNode():
                check_symlink(root, path, node.target)
                entries.append(SymlinkEntry(path, node.target))
    for path in index.nodes:
        if path not in final and path not in index.keeps:
            entries.append(DeleteEntry(path))
    entries.sort(key=lambda entry: _utf8(entry.path))
    if len(entries) > scope.max_entries:
        raise Rejected(f"the delta has {len(entries)} entries, over the scope bound")
    if sum(entry.size for entry in entries if isinstance(entry, WriteEntry)) > scope.max_bytes:
        raise Rejected("the delta holds more bytes than the scope bound")
    return tuple(entries)


def apply_delta(index: BaselineIndex, manifest: Manifest) -> State:
    """The expected final state: the baseline index with the manifest's entries applied."""
    state = dict(index.nodes)
    for entry in manifest.entries:
        match entry:
            case WriteEntry():
                state[entry.path] = FileNode(entry.sha256, entry.size, entry.executable)
            case DirEntry():
                state[entry.path] = DirNode()
            case SymlinkEntry():
                state[entry.path] = LinkNode(entry.target)
            case DeleteEntry():
                state.pop(entry.path, None)
    return state


def check_manifest(scope: Scope, index: BaselineIndex, manifest: Manifest) -> None:
    """Re-apply the task's current scope rules to a stored candidate."""
    if manifest.scope != scope.to_json():
        raise Rejected("the candidate was captured under a different scope")
    if manifest.baseline_image != index.image:
        raise Rejected("the candidate was captured from a different baseline")
    for entry in manifest.entries:
        root = root_of(scope, entry.path)
        if root is None or entry.path == root.path:
            raise Rejected(f"{entry.path!r} is outside the scope")
        if isinstance(entry, DeleteEntry) and (
            entry.path not in index.nodes or entry.path in index.keeps
        ):
            raise Rejected(f"{entry.path!r} is deleted but not a deletable baseline entry")
        if isinstance(entry, SymlinkEntry):
            check_symlink(root, entry.path, entry.target)
    check_tree(scope, apply_delta(index, manifest))


def _utf8(path: str) -> bytes:
    return path.encode("utf-8")
