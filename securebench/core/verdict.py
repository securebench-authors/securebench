"""Verdict vocabulary (architecture Section 10)."""

from dataclasses import dataclass
from enum import StrEnum

from securebench.core.jsondata import JsonValue


class Status(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"


class FailureClass(StrEnum):
    CAPTURE = "capture"
    SETUP = "setup"
    CASE_ERROR = "case_error"
    ORACLE = "oracle"


class AttemptFailed(Exception):
    """The candidate failed at a stage that ends the attempt with `failure_class`."""

    def __init__(self, failure_class: FailureClass, reason: str) -> None:
        super().__init__(f"{failure_class}: {reason}")
        self.failure_class = failure_class
        self.reason = reason


@dataclass(frozen=True)
class Verdict:
    """The binary outcome of an attempt, plus why.

    `failure_class` is set exactly when `status` is `failed`. `diagnostics`
    holds Oracle and framework detail, which may include expected values.
    """

    status: Status
    failure_class: FailureClass | None
    diagnostics: tuple[JsonValue, ...]

    def __post_init__(self) -> None:
        if (self.status is Status.FAILED) != (self.failure_class is not None):
            raise ValueError("failure_class must be set exactly when the status is failed")
