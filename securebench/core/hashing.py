"""SHA-256 digests in the one textual form SecureBench uses: `sha256:<64 lowercase hex>`."""

import hashlib

from securebench.core.errors import Rejected

PREFIX = "sha256:"
_HEX = frozenset("0123456789abcdef")


def sha256(data: bytes) -> str:
    """Return the digest of `data`."""
    return PREFIX + hashlib.sha256(data).hexdigest()


def check_digest(text: str) -> str:
    """Return `text` if it is exactly `sha256:` plus 64 lowercase hex characters.

    Raises `Rejected` otherwise. A digest is checked before it becomes part of
    a path.
    """
    hex_digits = text[len(PREFIX) :]
    if not text.startswith(PREFIX) or len(hex_digits) != 64 or not set(hex_digits) <= _HEX:
        raise Rejected(f"{text[:80]!r} is not a sha256 digest")
    return text


def hex_part(digest: str) -> str:
    """Return the 64 hex characters of a checked digest."""
    return check_digest(digest)[len(PREFIX) :]
