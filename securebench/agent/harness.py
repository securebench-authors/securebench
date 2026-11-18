"""Harness drivers (architecture Section 9.1).

A harness is a read-only tooling overlay, a command and its environment. The
instructions reach the harness verbatim on standard input and as a read-only
file; nothing else from the framework is added to the prompt.
"""

from dataclasses import dataclass
from pathlib import Path

from securebench.core import jsondata, paths
from securebench.core.errors import HostError, Rejected

HARNESS_MOUNT = "/.securebench/harness"


@dataclass(frozen=True)
class Harness:
    """What runs in the Agent environment.

    `providers` names the relay providers the harness calls; an empty tuple
    means the harness needs no model access. `version_command`, when set, is
    run in the task image before the Agent starts and must print `version`,
    so that a harness that cannot run in this image is found before the Agent starts.
    """

    name: str
    version: str
    overlay: Path
    command: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    providers: tuple[str, ...]
    version_command: tuple[str, ...] | None


def scripted(script: Path, providers: tuple[str, ...] = ()) -> Harness:
    """A fixed command sequence: the shell script `script`, run with `sh` from its own overlay.

    `providers` gives the script relay access, for tests of the relay itself.
    """
    if not script.is_file() or script.is_symlink():
        raise HostError(f"scripted harness {script} is not a regular file")
    return Harness(
        "scripted",
        "1",
        script.parent.resolve(),
        ("sh", f"{HARNESS_MOUNT}/{script.name}"),
        (),
        providers,
        None,
    )


RELAY = "http://relay:8080"
_MODEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-/[]")
_VERSION_CHARS = frozenset("0123456789abcdefghijklmnopqrstuvwxyz.-+")
# The values Codex accepts for model_reasoning_effort.
CODEX_EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh"})
# The values Claude Code accepts for --effort.
CLAUDE_CODE_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})


def claude_code(
    overlay: Path, version: str, model: str, oauth: bool = False, effort: str | None = None
) -> Harness:
    """Claude Code from an operator-prepared overlay (`docs/operating.md`), via the relay.

    The prompt arrives on standard input; the harness's own permission prompts
    are off because the container is the boundary. `HOME` stays the task image's,
    as natively, so the caches and settings the image keeps there are found.
    With `oauth`,
    the relay injects a subscription token instead of an API key.
    `effort`, when given, sets Claude Code's `--effort`.
    """
    entry = _entry(overlay, "@anthropic-ai/claude-code", "claude", version)
    if effort is not None and effort not in CLAUDE_CODE_EFFORTS:
        raise HostError(f"reasoning effort {effort!r} is not one of {sorted(CLAUDE_CODE_EFFORTS)}")
    reasoning = () if effort is None else ("--effort", effort)
    command = (
        *entry,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--model",
        _model(model),
        *reasoning,
    )
    provider = "anthropic-oauth" if oauth else "anthropic"
    # Claude Code sends OAuth-style requests only when it holds no API key.
    credential = (
        ("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-securebench-placeholder")
        if oauth
        else ("ANTHROPIC_API_KEY", "sk-ant-api03-securebench-placeholder")
    )
    environment = (
        ("ANTHROPIC_BASE_URL", f"{RELAY}/{provider}"),
        credential,
        ("DISABLE_AUTOUPDATER", "1"),
        ("DISABLE_TELEMETRY", "1"),
        ("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1"),
        # Task images often run as root; Claude Code then accepts skipping its
        # permission prompts only when told it runs in a sandbox, which it does.
        ("IS_SANDBOX", "1"),
    )
    return Harness(
        "claude-code-oauth" if oauth else "claude-code",
        version,
        overlay,
        command,
        environment,
        (provider,),
        (*entry, "--version"),
    )


def codex(overlay: Path, version: str, model: str, effort: str | None = None) -> Harness:
    """Codex from an operator-prepared overlay (`docs/operating.md`), via the relay.

    The provider is configured through `-c` flags so no repository file can
    redirect it; `-` reads the prompt from standard input.
    `effort`, when given, sets Codex's reasoning effort.
    `--json` and `--enable unified_exec` are the flags Pier's Codex agent passes, so
    that both graders run Codex alike.
    """
    entry = _entry(overlay, "@openai/codex", "codex", version)
    if effort is not None and effort not in CODEX_EFFORTS:
        raise HostError(f"reasoning effort {effort!r} is not one of {sorted(CODEX_EFFORTS)}")
    reasoning = () if effort is None else ("-c", f'model_reasoning_effort="{effort}"')
    provider = "model_providers.securebench"
    command = (
        *entry,
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        _model(model),
        "--json",
        "--enable",
        "unified_exec",
        "-c",
        "model_provider=securebench",
        "-c",
        f'{provider}.name="securebench"',
        "-c",
        f'{provider}.base_url="{RELAY}/openai/v1"',
        "-c",
        f'{provider}.env_key="OPENAI_API_KEY"',
        "-c",
        f'{provider}.wire_api="responses"',
        "-c",
        'web_search="disabled"',
        *reasoning,
        "-",
    )
    environment = (("OPENAI_API_KEY", "sk-securebench-placeholder"),)
    return Harness(
        "codex", version, overlay, command, environment, ("openai",), (*entry, "--version")
    )


def _entry(overlay: Path, package: str, binary: str, version: str) -> tuple[str, ...]:
    """The command that starts `binary` of `package` inside the mounted overlay.

    The overlay is operator-prepared (trusted); its package metadata must name
    exactly the pinned version. A native program (Claude Code ships one) runs
    directly; a JavaScript program runs with the overlay's `bin/node`.
    """
    if not version or not set(version) <= _VERSION_CHARS:
        raise HostError(f"harness version {version!r} is not a plain version string")
    root = overlay / "node_modules" / package
    try:
        metadata = jsondata.decode((root / "package.json").read_bytes(), 1 << 20)
    except (OSError, Rejected) as error:
        raise HostError(f"overlay {overlay} has no readable {package}: {error}") from None
    if not isinstance(metadata, dict) or metadata.get("version") != version:
        raise HostError(f"overlay {overlay} does not hold {package} version {version}")
    bins = metadata.get("bin")
    relative = bins.get(binary) if isinstance(bins, dict) else bins
    if not isinstance(relative, str):
        raise HostError(f"{package} in {overlay} declares no '{binary}' program")
    relative = relative.removeprefix("./")
    try:
        paths.check_relative(relative)
    except Rejected as error:
        raise HostError(f"{package} program path: {error.reason}") from None
    mounted = f"{HARNESS_MOUNT}/node_modules/{package}/{relative}"
    try:
        with (root / relative).open("rb") as program:
            native = program.read(4) == b"\x7fELF"
    except OSError as error:
        raise HostError(f"{package} program {relative} is unreadable: {error}") from None
    if native:
        return (mounted,)
    if not (overlay / "bin" / "node").is_file():
        raise HostError(f"overlay {overlay} has no bin/node for {package}")
    return (f"{HARNESS_MOUNT}/bin/node", mounted)


def _model(model: str) -> str:
    if not model or len(model) > 128 or not set(model) <= _MODEL_CHARS or model.startswith("-"):
        raise HostError(f"model name {model!r} is not allowed")
    return model
