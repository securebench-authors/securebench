"""Errors shared by every module, each tied to the zone that caused it.

Architecture Section 10 attributes every error to a zone. Code raises the error
type of the zone it knows about, and the stage that owns the attempt turns it
into a verdict. Nothing is swallowed: every error carries a precise reason.
"""


class SecureBenchError(Exception):
    """Base class. `reason` is a human-readable, precise description."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Rejected(SecureBenchError):
    """Untrusted input broke a rule.

    Parsers, validators and path checks raise only this for bad input. The
    caller knows where the input came from and attributes it (capture, case,
    pack validation).
    """


class PackError(SecureBenchError):
    """The task pack or its baseline violates the task format.

    Raised before any Agent starts. The author must fix the pack.
    """


class HostError(SecureBenchError):
    """Trusted host-side machinery failed: container runtime, store, framework bug.

    During a case this leads to a retry; elsewhere the attempt is `invalid`.
    """
