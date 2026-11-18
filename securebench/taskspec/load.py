"""Static pack validation.

`load` checks everything that can be checked without running anything: the
pack layout, every key and bound of `task.toml`, path rules, domains, exclude
patterns and schemas. The live baseline checks belong to `candidate`, and the
static Oracle checks to `oracle`.
"""

import os
import stat
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

from securebench.core import hashing, jsondata, paths, patterns
from securebench.core.errors import PackError, Rejected
from securebench.core.jsondata import JsonValue
from securebench.core.task import (
    PROTECTED_PATHS,
    ArtifactCheck,
    Baseline,
    FileSpec,
    ListingSpec,
    Parser,
    ProtocolCheck,
    PublicAsset,
    PublicTask,
    Repository,
    Scope,
    ScopeRoot,
    Task,
)
from securebench.evidence import schema
from securebench.taskspec.domains import check_domain

MAX_TASK_TOML_BYTES = 256 * 1024
MAX_INSTRUCTIONS_BYTES = 1024 * 1024
MAX_PACK_BYTES = 1 << 30
MAX_PACK_ENTRIES = 100_000

MAX_SCOPE_ENTRIES = 100_000
MAX_SCOPE_BYTES = 2 << 30
MAX_ROOTS = 16
MAX_DOMAINS = 1024
MAX_FILE_BYTES = 16 << 20
MAX_LISTING_ENTRIES = 100_000
MAX_CASES = 1000
MAX_TIMEOUT = 3600
MAX_SETUP_TIMEOUT = 7200
MAX_CHALLENGE_BYTES = 1 << 20
MAX_OBSERVATION_BYTES = 4 << 20
MAX_OUTPUT_ARTIFACTS = 64
MAX_OUTPUT_ARTIFACT_BYTES = 16 << 20
MAX_COMMAND_PARTS = 64
MAX_COMMAND_PART_BYTES = 4096

_TOP_LEVEL = {"task.toml", "instructions.md", "public", "evaluation", "hidden"}
_LANES = ("public", "evaluation", "hidden")
_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")
_HEX = frozenset("0123456789abcdef")
_IMAGE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._/:-")

type Table = dict[str, object]


def load(pack: Path) -> Task:
    """Load and validate the task pack at `pack`. Raises `PackError` with the first violation."""
    try:
        return _load(pack)
    except Rejected as error:
        raise PackError(f"{pack}: {error.reason}") from None


def pack_digest(pack: Path) -> str:
    """Digest of every regular file in the pack: relative path, executable bit and content."""
    files, directories = _walk(pack)
    listing: list[JsonValue] = []
    for relative in sorted(files, key=lambda path: path.encode("utf-8")):
        data = _read_bounded(pack / relative, MAX_PACK_BYTES)
        executable = bool(os.lstat(pack / relative).st_mode & stat.S_IXUSR)
        listing.append([relative, executable, hashing.sha256(data)])
    dirs: list[JsonValue] = [
        directory for directory in sorted(directories, key=lambda path: path.encode("utf-8"))
    ]
    return jsondata.digest({"directories": dirs, "files": listing})


def _load(pack: Path) -> Task:
    pack = pack.absolute()
    files, directories = _walk(pack)
    top = {path for path in files | directories if "/" not in path}
    if not top <= _TOP_LEVEL:
        raise Rejected(f"unexpected top-level entries {sorted(top - _TOP_LEVEL)}")
    for required in ("task.toml", "instructions.md", "hidden/oracle.py"):
        if required not in files:
            raise Rejected(f"{required} is missing or not a regular file")
    for lane in _LANES:
        if lane in files:
            raise Rejected(f"{lane} must be a directory")
    _read_bounded(pack / "instructions.md", MAX_INSTRUCTIONS_BYTES)
    try:
        text = _read_bounded(pack / "task.toml", MAX_TASK_TOML_BYTES).decode("utf-8", "strict")
        data = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise Rejected(f"task.toml is not valid UTF-8 TOML: {error}") from None
    top_table = _table(
        data,
        "task.toml",
        {"id", "source_benchmark", "baseline", "agent", "scope"},
        {"public_assets", "artifact_checks", "protocol_checks"},
    )
    task_id = _name(top_table["id"], "id")
    source = _name(top_table["source_benchmark"], "source_benchmark")
    scope = _scope(top_table["scope"])
    baseline = _baseline(top_table["baseline"], scope)
    workdir, domains = _agent(top_table["agent"], scope)
    assets = _public_assets(top_table.get("public_assets", []), pack, files, directories, scope)
    artifact_checks = tuple(
        _artifact_check(raw, scope, index)
        for index, raw in enumerate(_list(top_table.get("artifact_checks", []), "artifact_checks"))
    )
    protocol_checks = tuple(
        _protocol_check(raw, pack, files, index)
        for index, raw in enumerate(_list(top_table.get("protocol_checks", []), "protocol_checks"))
    )
    check_ids = [check.id for check in artifact_checks] + [check.id for check in protocol_checks]
    if not check_ids:
        raise Rejected("a task declares at least one check")
    if len(set(check_ids)) != len(check_ids):
        raise Rejected("check identifiers must be unique")
    public = PublicTask(
        task_id, source, baseline, workdir, domains, pack / "instructions.md", assets
    )
    return Task(
        public,
        pack,
        scope,
        artifact_checks,
        protocol_checks,
        pack / "evaluation",
        pack / "hidden",
        pack_digest(pack),
    )


def _walk(pack: Path) -> tuple[set[str], set[str]]:
    """Return the relative paths of regular files and directories; reject anything else."""
    if not stat.S_ISDIR(os.lstat(pack).st_mode):
        raise Rejected("the pack must be a real directory")
    files: set[str] = set()
    directories: set[str] = set()
    total_bytes = 0
    pending = [""]
    while pending:
        current = pending.pop()
        with os.scandir(pack / current if current else pack) as entries:
            for entry in entries:
                relative = f"{current}/{entry.name}" if current else entry.name
                try:
                    relative.encode("utf-8", "strict")
                except UnicodeEncodeError:
                    raise Rejected("a pack file name is not valid UTF-8") from None
                paths.check_relative(relative)
                if len(files) + len(directories) >= MAX_PACK_ENTRIES:
                    raise Rejected(f"the pack has more than {MAX_PACK_ENTRIES} entries")
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories.add(relative)
                    pending.append(relative)
                elif stat.S_ISREG(info.st_mode):
                    files.add(relative)
                    total_bytes += info.st_size
                    if total_bytes > MAX_PACK_BYTES:
                        raise Rejected(f"the pack is larger than {MAX_PACK_BYTES} bytes")
                else:
                    raise Rejected(f"{relative} is a symlink or special file")
    return files, directories


def _read_bounded(path: Path, max_bytes: int) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise Rejected(f"{path.name} is larger than {max_bytes} bytes")
    return data


def _table(value: object, where: str, required: set[str], optional: set[str]) -> Table:
    if not isinstance(value, dict):
        raise Rejected(f"{where} must be a table")
    table = cast(Table, value)
    keys = set(table)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise Rejected(f"{where} is missing {sorted(missing)}")
    if unknown:
        raise Rejected(f"{where} has unknown keys {sorted(unknown)}")
    return table


def _list(value: object, where: str, max_items: int = 1024) -> list[object]:
    if not isinstance(value, list):
        raise Rejected(f"{where} must be an array")
    items = cast(list[object], value)
    if len(items) > max_items:
        raise Rejected(f"{where} has more than {max_items} items")
    return items


def _string(value: object, where: str, max_bytes: int = 4096) -> str:
    if not isinstance(value, str):
        raise Rejected(f"{where} must be a string")
    if "\x00" in value or len(value.encode("utf-8")) > max_bytes:
        raise Rejected(f"{where} contains NUL or is longer than {max_bytes} bytes")
    return value


def _name(value: object, where: str) -> str:
    text = _string(value, where, 64)
    if not text or not set(text) <= _NAME_CHARS or text.startswith("-"):
        raise Rejected(f"{where} {text!r} must be a name: lowercase letters, digits and '-'")
    return text


def _int(value: object, where: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise Rejected(f"{where} must be an integer from {low} to {high}")
    return value


def _bool(value: object, where: str) -> bool:
    if type(value) is not bool:
        raise Rejected(f"{where} must be a boolean")
    return value


def _absolute(value: object, where: str) -> str:
    return _located(paths.check_absolute, _string(value, where), where)


def _relative(value: object, where: str) -> str:
    return _located(paths.check_relative, _string(value, where), where)


def _located(check: Callable[[str], str], text: str, where: str) -> str:
    try:
        return check(text)
    except Rejected as error:
        raise Rejected(f"{where}: {error.reason}") from None


def _scope(value: object) -> Scope:
    table = _table(value, "scope", {"max_entries", "max_bytes", "roots"}, set())
    max_entries = _int(table["max_entries"], "scope.max_entries", 1, MAX_SCOPE_ENTRIES)
    max_bytes = _int(table["max_bytes"], "scope.max_bytes", 1, MAX_SCOPE_BYTES)
    raw_roots = _list(table["roots"], "scope.roots", MAX_ROOTS)
    if not raw_roots:
        raise Rejected("scope.roots must list at least one root")
    roots: list[ScopeRoot] = []
    for index, raw in enumerate(raw_roots):
        where = f"scope.roots[{index}]"
        root_table = _table(
            raw,
            where,
            {"path", "symlinks", "max_entries", "max_bytes"},
            {"exclude", "git_directories"},
        )
        path = _absolute(root_table["path"], f"{where}.path")
        _not_protected(path, f"{where}.path")
        for other in roots:
            if paths.overlaps_folded(path, other.path):
                raise Rejected(f"{where}.path overlaps the root {other.path}")
        exclude = tuple(
            _located(patterns.check_pattern, _string(item, f"{where}.exclude"), f"{where}.exclude")
            for item in _list(
                root_table.get("exclude", []), f"{where}.exclude", patterns.MAX_PATTERNS
            )
        )
        git_directories = tuple(
            _git_directory(item, f"{where}.git_directories")
            for item in _list(root_table.get("git_directories", []), f"{where}.git_directories")
        )
        roots.append(
            ScopeRoot(
                path,
                exclude,
                git_directories,
                _bool(root_table["symlinks"], f"{where}.symlinks"),
                _int(root_table["max_entries"], f"{where}.max_entries", 1, max_entries),
                _int(root_table["max_bytes"], f"{where}.max_bytes", 1, max_bytes),
            )
        )
    return Scope(tuple(roots), max_entries, max_bytes)


def _git_directory(value: object, where: str) -> str:
    relative = _relative(value, where)
    if paths.components(relative)[-1] != ".git":
        raise Rejected(f"{where} entry {relative!r} must end in '.git'")
    return relative


def _not_protected(path: str, where: str) -> None:
    for protected in PROTECTED_PATHS:
        if paths.overlaps_folded(path, protected):
            raise Rejected(f"{where} {path!r} overlaps the framework-protected path {protected}")


def _root_of(path: str, scope: Scope) -> ScopeRoot | None:
    for root in scope.roots:
        if paths.is_within(path, root.path):
            return root
    return None


def _baseline(value: object, scope: Scope) -> Baseline:
    table = _table(value, "baseline", {"image"}, {"repository"})
    image = _image(_string(table["image"], "baseline.image", 512))
    repository = None
    if "repository" in table:
        repo = _table(table["repository"], "baseline.repository", {"path", "commit"}, set())
        repo_path = _absolute(repo["path"], "baseline.repository.path")
        if _root_of(repo_path, scope) is None:
            raise Rejected("baseline.repository.path must lie inside a scope root")
        commit = _string(repo["commit"], "baseline.repository.commit", 64)
        if len(commit) not in (40, 64) or not set(commit) <= _HEX:
            raise Rejected("baseline.repository.commit must be 40 or 64 lowercase hex characters")
        repository = Repository(repo_path, commit)
    return Baseline(image, repository)


def _image(image: str) -> str:
    repository, separator, digest = image.rpartition("@")
    if not separator:
        return _located(hashing.check_digest, image, "baseline.image")
    _located(hashing.check_digest, digest, "baseline.image")
    if not repository or not set(repository) <= _IMAGE_CHARS:
        raise Rejected(f"baseline.image repository {repository!r} is not valid")
    return image


def _agent(value: object, scope: Scope) -> tuple[str, tuple[str, ...]]:
    table = _table(value, "agent", {"workdir", "allowed_domains"}, set())
    workdir = _absolute(table["workdir"], "agent.workdir")
    if _root_of(workdir, scope) is None:
        raise Rejected("agent.workdir must lie inside a scope root")
    domains: list[str] = []
    for item in _list(table["allowed_domains"], "agent.allowed_domains", MAX_DOMAINS):
        domain = _located(check_domain, _string(item, "agent.allowed_domains"), "allowed_domains")
        if domain in domains:
            raise Rejected(f"agent.allowed_domains repeats {domain}")
        domains.append(domain)
    return workdir, tuple(domains)


def _public_assets(
    value: object, pack: Path, files: set[str], directories: set[str], scope: Scope
) -> tuple[PublicAsset, ...]:
    assets: list[PublicAsset] = []
    for index, raw in enumerate(_list(value, "public_assets")):
        where = f"public_assets[{index}]"
        table = _table(raw, where, {"source", "target"}, set())
        source = _relative(table["source"], f"{where}.source")
        if f"public/{source}" not in files | directories:
            raise Rejected(f"{where}.source public/{source} does not exist")
        target = _absolute(table["target"], f"{where}.target")
        _not_protected(target, f"{where}.target")
        for root in scope.roots:
            if paths.overlaps_folded(target, root.path):
                raise Rejected(f"{where}.target overlaps the scope root {root.path}")
        for other in assets:
            if paths.overlaps_folded(target, other.target):
                raise Rejected(f"{where}.target overlaps {other.target}")
        assets.append(PublicAsset(pack / "public" / source, target))
    return tuple(assets)


def _file_spec(value: object, where: str) -> FileSpec:
    table = _table(value, where, {"path", "parser", "max_bytes"}, set())
    path = _absolute(table["path"], f"{where}.path")
    parser_name = _string(table["parser"], f"{where}.parser", 16)
    if parser_name not in {parser.value for parser in Parser}:
        raise Rejected(f"{where}.parser {parser_name!r} is not a registry parser")
    max_bytes = _int(table["max_bytes"], f"{where}.max_bytes", 1, MAX_FILE_BYTES)
    return FileSpec(path, Parser(parser_name), max_bytes)


def _in_scope(path: str, scope: Scope, where: str) -> None:
    root = _root_of(path, scope)
    if root is None or path == root.path:
        raise Rejected(f"{where} {path!r} must lie inside a scope root")
    if patterns.is_excluded(root.exclude, root.git_directories, paths.relative_to(path, root.path)):
        raise Rejected(f"{where} {path!r} is excluded from the scope")


def _artifact_check(value: object, scope: Scope, index: int) -> ArtifactCheck:
    where = f"artifact_checks[{index}]"
    table = _table(value, where, {"id"}, {"files", "listings"})
    check_id = _name(table["id"], f"{where}.id")
    files: list[FileSpec] = []
    for file_index, raw in enumerate(_list(table.get("files", []), f"{where}.files", 64)):
        spec = _file_spec(raw, f"{where}.files[{file_index}]")
        _in_scope(spec.path, scope, f"{where}.files[{file_index}].path")
        files.append(spec)
    listings: list[ListingSpec] = []
    for listing_index, raw in enumerate(_list(table.get("listings", []), f"{where}.listings", 64)):
        listing_where = f"{where}.listings[{listing_index}]"
        listing = _table(raw, listing_where, {"path", "max_entries"}, set())
        path = _absolute(listing["path"], f"{listing_where}.path")
        _in_scope(path, scope, f"{listing_where}.path")
        max_entries = _int(
            listing["max_entries"], f"{listing_where}.max_entries", 1, MAX_LISTING_ENTRIES
        )
        listings.append(ListingSpec(path, max_entries))
    if not files and not listings:
        raise Rejected(f"{where} must read at least one file or listing")
    declared = [spec.path for spec in files] + [spec.path for spec in listings]
    if len(set(declared)) != len(declared):
        raise Rejected(f"{where} declares a path twice")
    return ArtifactCheck(check_id, tuple(files), tuple(listings))


def _command(value: object, where: str) -> tuple[str, ...]:
    parts = tuple(
        _string(part, where, MAX_COMMAND_PART_BYTES)
        for part in _list(value, where, MAX_COMMAND_PARTS)
    )
    if not parts or not all(parts):
        raise Rejected(f"{where} must be 1 to {MAX_COMMAND_PARTS} non-empty strings")
    _located(paths.check_absolute, parts[0], f"{where}[0]")
    return parts


def _schema_file(value: object, pack: Path, files: set[str], where: str) -> JsonValue:
    relative = _relative(value, where)
    if f"evaluation/{relative}" not in files:
        raise Rejected(f"{where} evaluation/{relative} does not exist")
    data = _read_bounded(pack / "evaluation" / relative, schema.MAX_SCHEMA_BYTES)
    try:
        loaded = jsondata.decode(data, schema.MAX_SCHEMA_BYTES)
        schema.check_schema(loaded)
    except Rejected as error:
        raise Rejected(f"{where}: {error.reason}") from None
    return loaded


def _protocol_check(value: object, pack: Path, files: set[str], index: int) -> ProtocolCheck:
    where = f"protocol_checks[{index}]"
    table = _table(
        value,
        where,
        {
            "id",
            "command",
            "challenge_schema",
            "observation_schema",
            "max_cases",
            "timeout_seconds",
            "max_challenge_bytes",
            "max_observation_bytes",
        },
        {"setup_command", "setup_timeout_seconds", "output_artifacts"},
    )
    setup_command = None
    setup_timeout = None
    if ("setup_command" in table) != ("setup_timeout_seconds" in table):
        raise Rejected(f"{where} needs setup_command and setup_timeout_seconds together")
    if "setup_command" in table:
        setup_command = _command(table["setup_command"], f"{where}.setup_command")
        setup_timeout = _int(
            table["setup_timeout_seconds"], f"{where}.setup_timeout_seconds", 1, MAX_SETUP_TIMEOUT
        )
    artifacts: list[FileSpec] = []
    raw_artifacts = _list(
        table.get("output_artifacts", []), f"{where}.output_artifacts", MAX_OUTPUT_ARTIFACTS
    )
    for artifact_index, raw in enumerate(raw_artifacts):
        artifact_where = f"{where}.output_artifacts[{artifact_index}]"
        spec = _file_spec(raw, artifact_where)
        _not_protected(spec.path, f"{artifact_where}.path")
        if any(paths.fold(part) == ".git" for part in paths.components(spec.path)):
            raise Rejected(f"{artifact_where}.path may not lie inside a .git directory")
        if any(paths.overlaps_folded(spec.path, other.path) for other in artifacts):
            raise Rejected(f"{artifact_where}.path overlaps another Output Artifact")
        artifacts.append(spec)
    if sum(spec.max_bytes for spec in artifacts) > MAX_OUTPUT_ARTIFACT_BYTES:
        raise Rejected(f"{where} Output Artifacts total more than {MAX_OUTPUT_ARTIFACT_BYTES}")
    return ProtocolCheck(
        _name(table["id"], f"{where}.id"),
        _command(table["command"], f"{where}.command"),
        _schema_file(table["challenge_schema"], pack, files, f"{where}.challenge_schema"),
        _schema_file(table["observation_schema"], pack, files, f"{where}.observation_schema"),
        _int(table["max_cases"], f"{where}.max_cases", 1, MAX_CASES),
        _int(table["timeout_seconds"], f"{where}.timeout_seconds", 1, MAX_TIMEOUT),
        _int(table["max_challenge_bytes"], f"{where}.max_challenge_bytes", 1, MAX_CHALLENGE_BYTES),
        _int(
            table["max_observation_bytes"],
            f"{where}.max_observation_bytes",
            1,
            MAX_OBSERVATION_BYTES,
        ),
        setup_command,
        setup_timeout,
        tuple(artifacts),
    )
