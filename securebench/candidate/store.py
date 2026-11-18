"""The content-addressed candidate store (architecture Section 5.1).

Layout under the store root: `blobs/<hex>` and `manifests/<hex>.json`. Every
write goes through a temporary file, `fsync` and an atomic rename. Every read
re-hashes and checks the size. A blob that is already present is verified,
never trusted. The store assumes one writer: the run that owns it holds the run
lock.
"""

import os
import tempfile
from pathlib import Path

from securebench.core import hashing, jsondata
from securebench.core.candidate import Manifest, manifest_from_json
from securebench.core.errors import HostError, Rejected
from securebench.core.jsondata import JsonValue

MAX_MANIFEST_BYTES = 256 << 20


class Store:
    """Blobs and manifests under one directory, all content-addressed."""

    def __init__(self, root: Path) -> None:
        self.root = root
        for part in ("blobs", "manifests"):
            (root / part).mkdir(parents=True, exist_ok=True)

    def put_blob(self, data: bytes) -> str:
        digest = hashing.sha256(data)
        path = self.root / "blobs" / hashing.hex_part(digest)
        if path.exists():
            self.get_blob(digest, len(data))
        else:
            _write_atomic(path, data)
        return digest

    def get_blob(self, digest: str, size: int) -> bytes:
        try:
            path = self.root / "blobs" / hashing.hex_part(digest)
        except Rejected as error:
            raise HostError(f"blob digest: {error.reason}") from None
        data = _read_bounded(path, size)
        if len(data) != size or hashing.sha256(data) != digest:
            raise HostError(f"blob {digest} in the store is corrupted")
        return data

    def put_manifest(self, manifest: Manifest) -> str:
        data = jsondata.encode(manifest.to_json())
        candidate_id = hashing.sha256(data)
        self._put_document(self.root / "manifests" / f"{hashing.hex_part(candidate_id)}.json", data)
        return candidate_id

    def get_manifest(self, candidate_id: str) -> Manifest:
        value = self._get_document(self.root / "manifests", candidate_id, MAX_MANIFEST_BYTES)
        try:
            return manifest_from_json(value)
        except Rejected as error:
            raise HostError(
                f"stored manifest {candidate_id} is malformed: {error.reason}"
            ) from None

    def _put_document(self, path: Path, data: bytes) -> None:
        if path.exists():
            if _read_bounded(path, len(data)) != data:
                raise HostError(f"{path.name} in the store differs from the same digest's content")
            return
        _write_atomic(path, data)

    def _get_document(self, directory: Path, digest: str, bound: int) -> JsonValue:
        try:
            path = directory / f"{hashing.hex_part(digest)}.json"
        except Rejected as error:
            raise HostError(f"document digest: {error.reason}") from None
        data = _read_bounded(path, bound)
        if hashing.sha256(data) != digest:
            raise HostError(f"{path.name} in the store is corrupted")
        try:
            return jsondata.decode(data, bound)
        except Rejected as error:
            raise HostError(f"{path.name} in the store is malformed: {error.reason}") from None


def _read_bounded(path: Path, bound: int) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(bound + 1)
    except FileNotFoundError:
        raise HostError(f"{path.name} is missing from the store") from None
    if len(data) > bound:
        raise HostError(f"{path.name} in the store is larger than expected")
    return data


def _write_atomic(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
