"""The utility program: walk, collect and replay filesystems inside utility environments.

This file runs inside containers with only the standard library and nothing else
from SecureBench. It never runs a program from the filesystem it
reads, never follows a symlink and treats every filesystem problem as a
rejection. The host validates everything it prints.

Usage: `python3 -I -S -B utility.py`, with one request on standard input.

Request: one JSON header line, then (for `replay`) the blobs it names, back to back.

- `{"op": "walk", "target": T, "scope": S, "known": {path: [sha256, executable]},
  "blob_paths": [path, ...], "deadline_seconds": N}` walks every scope root under
  the directory `T`. Files are hashed; a file's bytes are sent when its
  (sha256, executable) differs from `known`, or when its path is in `blob_paths`.
  With `known` null, bytes are sent only for `blob_paths`.
- `{"op": "collect", "target": T, "files": [[path, max_bytes], ...]}` reads
  declared single files.
- `{"op": "replay", "scope": S, "entries": [...], "blobs": [[sha256, size], ...],
  "deadline_seconds": N}` applies manifest entries to this container's own
  filesystem, after walking the scope once before and once after.

Output: a stream of records, each one JSON line, some followed by raw bytes.

- `{"t": "dir", "p": path}`
- `{"t": "file", "p": path, "size": n, "x": bool, "sha256": hex}` (bytes not sent), or
  `{"t": "file", "p": path, "size": n, "x": bool, "blob": true}` followed by `n` bytes
- `{"t": "symlink", "p": path, "target": text}`
- `{"t": "excluded_in", "p": path}`: the directory (or scope root) holds excluded entries
- `{"t": "collected", "p": path, "status": "absent" | "directory" | "not_regular" | "too_large" |
  "unreadable"}` or `{"t": "collected", "p": path, "status": "present", "size": n,
  "x": bool}` followed by `n` bytes
- `{"t": "phase", "name": "before" | "after"}` separates the two replay walks
- `{"t": "rejected", "reason": text}` ends the stream after a rejection
- `{"t": "end"}` ends a successful stream
"""

import hashlib
import json
import os
import stat
import sys
import time
import unicodedata
from typing import IO, Any

MAX_NAME_BYTES = 255
MAX_PATH_BYTES = 4096
MAX_COMPONENTS = 128
MAX_TARGET_BYTES = 4096
CHUNK = 1 << 20


class Rejection(Exception):
    """The filesystem breaks a rule; reported as a `rejected` record."""


class Budget:
    """Entry and byte budgets shared across all roots, plus one deadline."""

    def __init__(self, scope: dict[str, Any], deadline_seconds: float) -> None:
        self.max_entries: int = scope["max_entries"]
        self.max_bytes: int = scope["max_bytes"]
        self.entries = 0
        self.bytes = 0
        self.deadline = time.monotonic() + deadline_seconds

    def tick(self) -> None:
        if time.monotonic() > self.deadline:
            raise Rejection("the walk did not finish before its deadline")


class Output:
    def __init__(self, stream: IO[bytes]) -> None:
        self.stream = stream

    def record(self, record: dict[str, Any], data: bytes = b"") -> None:
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        self.stream.write(line.encode("ascii") + b"\n" + data)

    def file_bytes(self, path: str, size: int, budget: Budget | None) -> None:
        """Stream a file's bytes, failing if it changed size underneath us."""
        with _open_regular(path) as handle:
            remaining = size
            while remaining:
                if budget is not None:
                    budget.tick()
                chunk = handle.read(min(CHUNK, remaining))
                if not chunk:
                    raise Rejection(f"{path} shrank while being read")
                self.stream.write(chunk)
                remaining -= len(chunk)
            if handle.read(1):
                raise Rejection(f"{path} grew while being read")


def main() -> int:
    stdin = sys.stdin.buffer
    out = Output(sys.stdout.buffer)
    header = json.loads(stdin.readline())
    try:
        if header["op"] == "walk":
            budget = Budget(header["scope"], header["deadline_seconds"])
            raw_known = header["known"]
            known = (
                None
                if raw_known is None
                else {path: (value[0], value[1]) for path, value in raw_known.items()}
            )
            walk(out, header["target"], header["scope"], budget, known, set(header["blob_paths"]))
        elif header["op"] == "collect":
            collect(out, header["target"], header["files"])
        elif header["op"] == "replay":
            replay(out, stdin, header)
        else:
            raise Rejection(f"unknown op {header['op']!r}")
    except Rejection as error:
        out.record({"t": "rejected", "reason": str(error)[:4000]})
        sys.stdout.flush()
        return 0
    except OSError as error:
        out.record({"t": "rejected", "reason": f"filesystem error: {error}"[:4000]})
        sys.stdout.flush()
        return 0
    out.record({"t": "end"})
    sys.stdout.flush()
    return 0


def fold(component: str) -> str:
    return unicodedata.normalize("NFC", component).casefold()


def component_matches(pattern: str, text: str) -> bool:
    p = t = 0
    star = -1
    resume = 0
    while t < len(text):
        if p < len(pattern) and pattern[p] == "*":
            star, resume = p, t
            p += 1
        elif p < len(pattern) and pattern[p] == text[t]:
            p += 1
            t += 1
        elif star >= 0:
            p = star + 1
            resume += 1
            t = resume
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)


def pattern_matches(pattern: str, parts: list[str]) -> bool:
    """The same semantics as `securebench.core.patterns.matches`, over folded components."""
    reachable = [True] + [False] * len(parts)
    for part in (fold(item) for item in pattern.split("/")):
        following = [False] * (len(parts) + 1)
        for j, ok in enumerate(reachable):
            if not ok:
                continue
            if part == "**":
                for k in range(j, len(parts) + 1):
                    following[k] = True
                break
            if j < len(parts) and component_matches(part, parts[j]):
                following[j + 1] = True
        reachable = following
    return any(reachable[1:])


def excluded(root: dict[str, Any], relative: str) -> bool:
    parts = relative.split("/")
    allowed = {tuple(directory.split("/")) for directory in root["git_directories"]}
    for index, part in enumerate(parts):
        if fold(part) == ".git" and tuple(parts[: index + 1]) not in allowed:
            return True
    folded = [fold(part) for part in parts]
    return any(pattern_matches(pattern, folded) for pattern in root["exclude"])


def check_name(name: str, path: str) -> None:
    try:
        encoded = name.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise Rejection(f"a file name under {path[:200]!r} is not valid UTF-8") from None
    if len(encoded) > MAX_NAME_BYTES or "\\" in name:
        raise Rejection(f"file name {name[:100]!r} is too long or contains a backslash")


def walk(
    out: Output,
    target: str,
    scope: dict[str, Any],
    budget: Budget,
    known: dict[str, tuple[str, bool]] | None,
    blob_paths: set[str],
) -> None:
    """Walk every root. With `known` set to `None`, file bytes are never sent."""
    for root in scope["roots"]:
        walk_root(out, target, root, budget, known, blob_paths)


def walk_root(
    out: Output,
    target: str,
    root: dict[str, Any],
    budget: Budget,
    known: dict[str, tuple[str, bool]] | None,
    blob_paths: set[str],
) -> None:
    root_path: str = root["path"]
    host_root = target.rstrip("/") + root_path
    info = os.lstat(host_root)
    if not stat.S_ISDIR(info.st_mode):
        raise Rejection(f"scope root {root_path} is not a real directory")
    device = info.st_dev
    entries = 0
    file_bytes = 0
    pending = [""]
    while pending:
        relative_dir = pending.pop()
        directory = host_root + ("/" + relative_dir if relative_dir else "")
        try:
            listing = os.scandir(directory)
        except PermissionError:
            raise Rejection(f"directory {root_path}/{relative_dir} cannot be read") from None
        holds_excluded = False
        with listing:
            for entry in listing:
                budget.tick()
                check_name(entry.name, relative_dir)
                relative = f"{relative_dir}/{entry.name}" if relative_dir else entry.name
                if excluded(root, relative):
                    holds_excluded = True
                    continue
                path = f"{root_path}/{relative}"
                if len(path.encode("utf-8")) > MAX_PATH_BYTES or path.count("/") > MAX_COMPONENTS:
                    raise Rejection(f"path {path[:200]!r} is too long or too deep")
                entries += 1
                budget.entries += 1
                if entries > root["max_entries"] or budget.entries > budget.max_entries:
                    raise Rejection(f"scope root {root_path} has more entries than its bound")
                info = entry.stat(follow_symlinks=False)
                if info.st_dev != device:
                    raise Rejection(f"{path} is on another filesystem")
                host_path = f"{host_root}/{relative}"
                if stat.S_ISDIR(info.st_mode):
                    out.record({"t": "dir", "p": path})
                    pending.append(relative)
                elif stat.S_ISREG(info.st_mode):
                    file_bytes += info.st_size
                    budget.bytes += info.st_size
                    if file_bytes > root["max_bytes"] or budget.bytes > budget.max_bytes:
                        raise Rejection(f"scope root {root_path} holds more bytes than its bound")
                    executable = bool(info.st_mode & stat.S_IXUSR)
                    digest = hash_file(host_path, info.st_size, budget)
                    unchanged = known is None or known.get(path) == (digest, executable)
                    if unchanged and path not in blob_paths:
                        out.record(
                            {
                                "t": "file",
                                "p": path,
                                "size": info.st_size,
                                "x": executable,
                                "sha256": digest,
                            }
                        )
                    else:
                        out.record(
                            {
                                "t": "file",
                                "p": path,
                                "size": info.st_size,
                                "x": executable,
                                "blob": True,
                            }
                        )
                        out.file_bytes(host_path, info.st_size, budget)
                elif stat.S_ISLNK(info.st_mode):
                    raw = os.readlink(host_path)
                    try:
                        raw.encode("utf-8", "strict")
                    except UnicodeEncodeError:
                        raise Rejection(f"symlink {path!r} has a non-UTF-8 target") from None
                    if len(raw.encode("utf-8")) > MAX_TARGET_BYTES:
                        raise Rejection(f"symlink {path!r} has an over-long target")
                    out.record({"t": "symlink", "p": path, "target": raw})
                else:
                    raise Rejection(f"{path} is a device, socket or named pipe")
        if holds_excluded:
            out.record({"t": "excluded_in", "p": f"{root_path}/{relative_dir}".rstrip("/")})


def _open_regular(path: str) -> IO[bytes]:
    """Open without following links or blocking on a swapped-in FIFO (G2)."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except PermissionError:
        raise Rejection(f"{path} cannot be read") from None
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise Rejection(f"{path} is no longer a regular file")
    os.set_blocking(descriptor, True)
    return os.fdopen(descriptor, "rb")


def hash_file(path: str, size: int, budget: Budget | None) -> str:
    digest = hashlib.sha256()
    seen = 0
    with _open_regular(path) as handle:
        while True:
            if budget is not None:
                budget.tick()
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            seen += len(chunk)
            if seen > size:
                raise Rejection(f"{path} grew while being hashed")
            digest.update(chunk)
    if seen != size:
        raise Rejection(f"{path} shrank while being hashed")
    return digest.hexdigest()


def collect(out: Output, target: str, files: list[list[Any]]) -> None:
    """Read declared files; a symlink anywhere on the path makes the file not regular."""
    for path, max_bytes in files:
        status, info = locate(target, path)
        if status is not None:
            out.record({"t": "collected", "p": path, "status": status})
            continue
        assert info is not None
        if info.st_size > max_bytes:
            out.record({"t": "collected", "p": path, "status": "too_large"})
            continue
        host_path = target.rstrip("/") + path
        try:
            with _open_regular(host_path) as handle:
                data = handle.read(max_bytes + 1)
        except Rejection:
            out.record({"t": "collected", "p": path, "status": "unreadable"})
            continue
        if len(data) != info.st_size:
            raise Rejection(f"{path} changed size while being read")
        executable = bool(info.st_mode & stat.S_IXUSR)
        out.record(
            {"t": "collected", "p": path, "status": "present", "size": len(data), "x": executable},
            data,
        )


def locate(target: str, path: str) -> tuple[str | None, os.stat_result | None]:
    """Walk the path's components with lstat."""
    current = target.rstrip("/")
    parts = path.strip("/").split("/")
    for index, part in enumerate(parts):
        current = f"{current}/{part}"
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return "absent", None
        except PermissionError:
            return "unreadable", None
        last = index == len(parts) - 1
        if stat.S_ISLNK(info.st_mode):
            return "not_regular", None
        if not last and not stat.S_ISDIR(info.st_mode):
            return "absent", None
        if last:
            if stat.S_ISDIR(info.st_mode):
                return "directory", None
            if not stat.S_ISREG(info.st_mode):
                return "not_regular", None
            return None, info
    return "absent", None


def replay(out: Output, stdin: IO[bytes], header: dict[str, Any]) -> None:
    """Apply manifest entries to "/" in a fixed safe order."""
    scope = header["scope"]
    out.record({"t": "phase", "name": "before"})
    walk(out, "/", scope, Budget(scope, header["deadline_seconds"]), None, set())
    os.umask(0)
    entries: list[dict[str, Any]] = header["entries"]
    blobs: dict[str, bytes] = {}
    for digest, size in header["blobs"]:
        data = stdin.read(size)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise Rejection("replay input blob does not match its digest")
        blobs[digest] = data
    for entry in sorted((e for e in entries if e["kind"] == "delete"), key=depth, reverse=True):
        remove(entry["path"])
    creating = [e for e in entries if e["kind"] != "delete"]
    for entry in sorted(creating, key=depth):
        try:
            info = os.lstat(entry["path"])
        except FileNotFoundError:
            continue
        same_dir = entry["kind"] == "dir" and stat.S_ISDIR(info.st_mode)
        same_file = entry["kind"] == "write" and stat.S_ISREG(info.st_mode)
        if not same_dir and not same_file:
            remove(entry["path"])
    for entry in sorted((e for e in creating if e["kind"] == "dir"), key=depth):
        check_parents(entry["path"])
        if not os.path.lexists(entry["path"]):
            with writable_parent(entry["path"]):
                os.mkdir(entry["path"], 0o755)
    for entry in (e for e in creating if e["kind"] == "write"):
        check_parents(entry["path"])
        write_file(entry["path"], blobs[entry["sha256"].removeprefix("sha256:")], entry)
    for entry in (e for e in creating if e["kind"] == "symlink"):
        check_parents(entry["path"])
        check_link(entry["path"], entry["target"], scope)
        with writable_parent(entry["path"]):
            os.symlink(entry["target"], entry["path"])
    for entry in sorted((e for e in creating if e["kind"] == "dir"), key=depth, reverse=True):
        os.chmod(entry["path"], 0o755, follow_symlinks=False)
    out.record({"t": "phase", "name": "after"})
    walk(out, "/", scope, Budget(scope, header["deadline_seconds"]), None, set())


def depth(entry: dict[str, Any]) -> int:
    path: str = entry["path"]
    return path.count("/")


def check_parents(path: str) -> None:
    """Every parent component must be a real directory at write time."""
    current = ""
    for part in path.strip("/").split("/")[:-1]:
        current = f"{current}/{part}"
        if not stat.S_ISDIR(os.lstat(current).st_mode):
            raise Rejection(f"a parent of {path} is not a real directory")


def check_link(path: str, target: str, scope: dict[str, Any]) -> None:
    """Recheck symlink containment at creation."""
    root = next(
        (
            r["path"]
            for r in scope["roots"]
            if path == r["path"] or path.startswith(r["path"] + "/")
        ),
        None,
    )
    if root is None or target.startswith("/") or not target:
        raise Rejection(f"symlink {path} has an unsafe target")
    depth = path[len(root) :].count("/") - 1
    for part in target.split("/"):
        depth += -1 if part == ".." else (0 if part in ("", ".") else 1)
        if depth < 0:
            raise Rejection(f"symlink {path} escapes its scope root")


class writable_parent:
    """Temporarily add owner write permission to a root-owned parent without capabilities."""

    def __init__(self, path: str) -> None:
        self.parent = os.path.dirname(path)
        self.mode: int | None = None

    def __enter__(self) -> None:
        info = os.lstat(self.parent)
        if not os.access(self.parent, os.W_OK):
            if info.st_uid != os.getuid():
                raise Rejection(f"{self.parent} is not writable by the replay user")
            self.mode = stat.S_IMODE(info.st_mode)
            os.chmod(self.parent, self.mode | stat.S_IWUSR | stat.S_IXUSR)

    def __exit__(self, *_: object) -> None:
        if self.mode is not None:
            os.chmod(self.parent, self.mode)


def remove(path: str) -> None:
    """Remove one entry; a directory must already be empty."""
    info = os.lstat(path)
    with writable_parent(path):
        if stat.S_ISDIR(info.st_mode):
            if os.listdir(path):
                raise Rejection(f"{path} is not empty and cannot be removed")
            os.rmdir(path)
        else:
            os.unlink(path)


def write_file(path: str, data: bytes, entry: dict[str, Any]) -> None:
    """Write through a temporary file and rename; never write in place."""
    if len(data) != entry["size"]:
        raise Rejection(f"blob for {path} has the wrong size")
    directory, name = os.path.split(path)
    temporary = f"{directory}/.securebench-replay-{os.getpid()}-{name}"[: len(directory) + 250]
    mode = 0o755 if entry["executable"] else 0o644
    with writable_parent(path):
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fchmod(handle.fileno(), mode)
                os.fsync(handle.fileno())
            if os.path.lexists(path) and stat.S_ISDIR(os.lstat(path).st_mode):
                raise Rejection(f"{path} is a directory and cannot be replaced by a file")
            os.rename(temporary, path)
        except BaseException:
            if os.path.lexists(temporary):
                os.unlink(temporary)
            raise


if __name__ == "__main__":
    sys.exit(main())
