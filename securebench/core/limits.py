"""Run-wide resource limits and operator settings (architecture Sections 8.4, 11)."""

from dataclasses import dataclass

from securebench.core.jsondata import JsonValue


@dataclass(frozen=True)
class Limits:
    """Per-environment caps, global for a run and recorded in provenance (B6)."""

    memory_bytes: int
    nano_cpus: int
    pids: int
    disk_bytes: int
    agent_timeout_seconds: int

    def __post_init__(self) -> None:
        """Reject non-positive or boolean values."""
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"limit {name} must be a positive integer")

    def to_json(self) -> JsonValue:
        return {
            "agent_timeout_seconds": self.agent_timeout_seconds,
            "disk_bytes": self.disk_bytes,
            "memory_bytes": self.memory_bytes,
            "nano_cpus": self.nano_cpus,
            "pids": self.pids,
        }


@dataclass(frozen=True)
class Settings:
    """Operator settings (architecture Section 11)."""

    provider_hosted_tools: bool
    case_retries: int
    limits: Limits

    def __post_init__(self) -> None:
        if type(self.case_retries) is not int or not 0 <= self.case_retries <= 10:
            raise ValueError("case_retries must be an integer from 0 to 10")

    def to_json(self) -> JsonValue:
        return {
            "case_retries": self.case_retries,
            "limits": self.limits.to_json(),
            "provider_hosted_tools": self.provider_hosted_tools,
        }
