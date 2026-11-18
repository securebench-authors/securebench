"""Lookup: reading the candidate for artifact checks without any environment (Section 5.4)."""

from securebench.candidate.state import (
    BaselineIndex,
    DirNode,
    FileNode,
    LinkNode,
    State,
    apply_delta,
    root_of,
)
from securebench.candidate.store import Store
from securebench.core import paths
from securebench.core.candidate import Manifest
from securebench.core.errors import HostError
from securebench.core.evidence import (
    EntryKind,
    FileRead,
    FileStatus,
    FoundFile,
    ListingEntry,
    ListingEvidence,
    ListingStatus,
)
from securebench.core.task import Scope


class FinalView:
    """The candidate's filesystem inside the scope: the baseline index with the delta applied."""

    def __init__(
        self, scope: Scope, index: BaselineIndex, manifest: Manifest, store: Store
    ) -> None:
        self.scope = scope
        self.state: State = apply_delta(index, manifest)
        self.store = store

    def _reachable(self, path: str) -> bool:
        """True when every directory between the scope root and `path` is a real directory."""
        root = root_of(self.scope, path)
        if root is None:
            raise HostError(f"lookup of {path!r} outside the scope")
        current = root.path
        for part in paths.components(paths.relative_to(path, root.path))[:-1]:
            current = f"{current}/{part}"
            if not isinstance(self.state.get(current), DirNode):
                return False
        return True


def read_file(view: FinalView, path: str, max_bytes: int) -> FileRead:
    """A `write` entry returns its blob, `delete` means absent, anything else the baseline's."""
    if not view._reachable(path):  # pyright: ignore[reportPrivateUsage]
        return FileStatus.ABSENT
    node = view.state.get(path)
    if node is None:
        return FileStatus.ABSENT
    if not isinstance(node, FileNode):
        return FileStatus.NOT_REGULAR
    if node.size > max_bytes:
        return FileStatus.TOO_LARGE
    return FoundFile(view.store.get_blob(node.sha256, node.size), node.sha256, node.executable)


def list_directory(view: FinalView, path: str, max_entries: int) -> ListingEvidence:
    """Every entry below `path`, answered from the manifest and the baseline index."""
    root = root_of(view.scope, path)
    if root is None:
        raise HostError(f"listing of {path!r} outside the scope")
    if path != root.path:
        if not view._reachable(path):  # pyright: ignore[reportPrivateUsage]
            return ListingEvidence(path, ListingStatus.ABSENT, ())
        node = view.state.get(path)
        if node is None:
            return ListingEvidence(path, ListingStatus.ABSENT, ())
        if not isinstance(node, DirNode):
            return ListingEvidence(path, ListingStatus.NOT_DIRECTORY, ())
    prefix = path + "/"
    below = sorted((p for p in view.state if p.startswith(prefix)), key=lambda p: p.encode())
    if len(below) > max_entries:
        return ListingEvidence(path, ListingStatus.TOO_MANY, ())
    entries: list[ListingEntry] = []
    for entry_path in below:
        node = view.state[entry_path]
        relative = entry_path[len(prefix) :]
        match node:
            case FileNode():
                entries.append(
                    ListingEntry(
                        relative, EntryKind.FILE, node.size, node.sha256, node.executable, None
                    )
                )
            case DirNode():
                entries.append(ListingEntry(relative, EntryKind.DIR, None, None, None, None))
            case LinkNode():
                entries.append(
                    ListingEntry(relative, EntryKind.SYMLINK, None, None, None, node.target)
                )
    return ListingEvidence(path, ListingStatus.PRESENT, tuple(entries))
