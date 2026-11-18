"""The task model: a validated task pack (architecture Section 2, task format Section 2).

`taskspec` builds these values; every other module only reads them. Paths in
the model are canonical; integer bounds are already checked.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from securebench.core.jsondata import JsonValue

EVALUATION_MOUNT = "/.securebench/evaluation"
INSTRUCTIONS_MOUNT = "/.securebench/instructions.md"

PROTECTED_PATHS: tuple[str, ...] = (
    "/.securebench",
    "/proc",
    "/sys",
    "/dev",
    "/run",
    "/var/run",
    "/tmp",
    "/var/tmp",
    "/var/lib/docker",
    "/var/lib/containerd",
    "/run/containerd",
    "/root",
    "/etc/passwd",
    "/etc/group",
    "/etc/shadow",
    "/etc/gshadow",
    "/etc/subuid",
    "/etc/subgid",
    "/etc/sudoers",
    "/etc/sudoers.d",
    "/etc/ssh",
    "/etc/apt",
    "/etc/dnf",
    "/etc/yum.repos.d",
    "/etc/pacman.conf",
    "/etc/pacman.d",
    "/var/lib/apt",
    "/var/lib/dpkg",
    "/var/lib/rpm",
    "/var/lib/pacman",
    "/var/cache/apt",
    "/var/cache/dnf",
    "/var/cache/yum",
)


class Parser(StrEnum):
    TEXT = "text"
    JSON = "json"


@dataclass(frozen=True)
class Repository:
    path: str
    commit: str


@dataclass(frozen=True)
class Baseline:
    image: str
    repository: Repository | None


@dataclass(frozen=True)
class ScopeRoot:
    path: str
    exclude: tuple[str, ...]
    git_directories: tuple[str, ...]
    symlinks: bool
    max_entries: int
    max_bytes: int


@dataclass(frozen=True)
class Scope:
    roots: tuple[ScopeRoot, ...]
    max_entries: int
    max_bytes: int

    def to_json(self) -> JsonValue:
        """The scope as canonical JSON data, recorded in every candidate manifest."""
        return {
            "max_bytes": self.max_bytes,
            "max_entries": self.max_entries,
            "roots": [
                {
                    "exclude": list(root.exclude),
                    "git_directories": list(root.git_directories),
                    "max_bytes": root.max_bytes,
                    "max_entries": root.max_entries,
                    "path": root.path,
                    "symlinks": root.symlinks,
                }
                for root in self.roots
            ],
        }


@dataclass(frozen=True)
class PublicAsset:
    source: Path
    target: str


@dataclass(frozen=True)
class FileSpec:
    """One file an artifact check reads, or one Output Artifact."""

    path: str
    parser: Parser
    max_bytes: int


@dataclass(frozen=True)
class ListingSpec:
    path: str
    max_entries: int


@dataclass(frozen=True)
class ArtifactCheck:
    id: str
    files: tuple[FileSpec, ...]
    listings: tuple[ListingSpec, ...]


@dataclass(frozen=True)
class ProtocolCheck:
    id: str
    command: tuple[str, ...]
    challenge_schema: JsonValue
    observation_schema: JsonValue
    max_cases: int
    timeout_seconds: int
    max_challenge_bytes: int
    max_observation_bytes: int
    setup_command: tuple[str, ...] | None
    setup_timeout_seconds: int | None
    output_artifacts: tuple[FileSpec, ...]


@dataclass(frozen=True)
class PublicTask:
    """The public part of a task: everything Agent-side code may see."""

    id: str
    source_benchmark: str
    baseline: Baseline
    workdir: str
    allowed_domains: tuple[str, ...]
    instructions: Path
    public_assets: tuple[PublicAsset, ...]


@dataclass(frozen=True)
class Task:
    """A validated task pack.

    `root` is the pack directory. `evaluation_dir` and `hidden_dir` are the
    `evaluation/` and `hidden/` lanes (the former may not exist). `digest`
    covers every file in the pack with its executable bit.
    """

    public: PublicTask
    root: Path
    scope: Scope
    artifact_checks: tuple[ArtifactCheck, ...]
    protocol_checks: tuple[ProtocolCheck, ...]
    evaluation_dir: Path
    hidden_dir: Path
    digest: str

    @property
    def id(self) -> str:
        return self.public.id
