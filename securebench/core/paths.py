"""Canonical path text and the two ways of comparing paths.

Canonical rules (task format Section 5): no empty, `.` or `..` component; no
trailing slash, backslash or NUL; valid UTF-8; at most `MAX_PATH_BYTES` bytes
and `MAX_COMPONENTS` components. Absolute paths start with exactly one `/` and
are never `/` itself.

Decisions that protect, exclude or detect collisions use folded comparison
(NFC normalization plus case folding per component). Decisions that grant
access use exact comparison.
"""

import unicodedata

from securebench.core.errors import Rejected

MAX_PATH_BYTES = 4096
MAX_COMPONENTS = 128


def check_absolute(path: str) -> str:
    """Return `path` if it is a canonical absolute path other than `/`; else raise `Rejected`."""
    if not path.startswith("/"):
        raise Rejected(f"path {path[:200]!r} is not absolute")
    _check_components(path, path[1:])
    return path


def check_relative(path: str) -> str:
    """Return `path` if it is a canonical relative path; else raise `Rejected`."""
    if path.startswith("/"):
        raise Rejected(f"path {path[:200]!r} is not relative")
    _check_components(path, path)
    return path


def components(path: str) -> tuple[str, ...]:
    """Split a canonical path into its components."""
    return tuple(path.lstrip("/").split("/"))


def fold(component: str) -> str:
    """Return the folded form of one component: NFC normalization, then case folding."""
    return unicodedata.normalize("NFC", component).casefold()


def is_within(path: str, root: str) -> bool:
    """Exact containment: `path` equals `root` or lies below it. Both canonical absolute."""
    return path == root or path.startswith(root + "/")


def is_within_folded(path: str, root: str) -> bool:
    """Folded containment: like `is_within`, comparing folded components."""
    inner = [fold(part) for part in components(path)]
    outer = [fold(part) for part in components(root)]
    return inner[: len(outer)] == outer


def overlaps_folded(a: str, b: str) -> bool:
    """True when either path, folded, equals or contains the other."""
    return is_within_folded(a, b) or is_within_folded(b, a)


def relative_to(path: str, root: str) -> str:
    """Return `path` relative to `root`, or `""` when equal. `path` must be within `root`."""
    if path == root:
        return ""
    if not is_within(path, root):
        raise Rejected(f"path {path[:200]!r} is not inside {root[:200]!r}")
    return path[len(root) + 1 :]


def _check_components(path: str, body: str) -> None:
    if "\x00" in path or "\\" in path:
        raise Rejected(f"path {path[:200]!r} contains NUL or a backslash")
    try:
        size = len(path.encode("utf-8", "strict"))
    except UnicodeEncodeError:
        raise Rejected(f"path {path[:200]!r} is not valid UTF-8") from None
    if size > MAX_PATH_BYTES:
        raise Rejected(f"path is {size} bytes, over {MAX_PATH_BYTES}")
    parts = body.split("/")
    if len(parts) > MAX_COMPONENTS:
        raise Rejected(f"path has {len(parts)} components, over {MAX_COMPONENTS}")
    for part in parts:
        if part in ("", ".", ".."):
            raise Rejected(f"path {path[:200]!r} is not canonical")
