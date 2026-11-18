"""Fidelity study: real agents on converted tasks, graded both ways.

Each attempt runs a model harness, Claude Code or Codex, on one task,
natively under Pier or under SecureBench, and its files are then graded by the other
grader too:

- native: N as run; N->S, SecureBench on the agent's scope roots as copied before
  the native verifier; N->s->N, native on the candidate N->S captured.
- securebench: S as run; S->N, native on the captured candidate.

Like campaign.py, this runs outside SecureBench's trusted path. It builds the
cross-grading candidates on the host from files only and never executes what an
agent wrote; the scripted candidates run inside each grader's own containers.

    python3 conversions/equivalence.py run --model M --token-file F --out DIR [--effort E] \
        [--harness codex] [--usage-limit 80] [--memory-budget-mib N] [--max-running N] \
        [--min-available-mib N] <source>/<task>...
    python3 conversions/equivalence.py run --model scripted:reference --out DIR <source>/<task>...
    python3 conversions/equivalence.py regrade ATTEMPT...
    python3 conversions/equivalence.py report DIR...
    python3 conversions/equivalence.py export ATTEMPTS --out DIR [--replaced DIR] [--notes FILE]
"""

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import tomllib
from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import campaign

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SIDES = ("native", "securebench")
# Per harness: its pinned version, the credential its runs read from --token-file, and the
# reasoning efforts it accepts. Claude Code runs on a
# subscription token, Codex on an OpenAI API key.
HARNESSES: dict[str, dict[str, Any]] = {
    "claude-code": {
        "version": "2.1.289",
        "credential": "CLAUDE_CODE_OAUTH_TOKEN",
        "efforts": ("low", "medium", "high", "xhigh", "max"),
    },
    "codex": {
        "version": "0.160.0",
        "credential": "OPENAI_API_KEY",
        "efforts": ("minimal", "low", "medium", "high", "xhigh"),
    },
}
# Pier with its pre-copy `chown` removed; it runs with Pier's own interpreter.
PIER = (Path(shutil.which("pier") or "pier").resolve().parent / "python", HERE / "pier_no_chown.py")
# Pier's Codex install links `node` and `codex` into /usr/local/bin when they are elsewhere
# (pier/agents/installed/codex.py, `install_spec`). They are the harness's, not the agent's,
# and SecureBench's overlay has no such files, so a native copy leaves them out.
HARNESS_LINKS = {"codex": ("/usr/local/bin/node", "/usr/local/bin/codex")}
# The relay refuses these on every Claude Code run; they are not provider errors.
KNOWN_REFUSALS = {"/api/hello", "/v1/messages/count_tokens"}
# The relay's refusal of a request that uses a provider-hosted tool, such as web search
# (securebench_relay_proxy/relay.py). It is part of SecureBench's environment, like a
# denied host, and not a provider error, so the attempt stays valid.
HOSTED_TOOLS_REFUSAL = "403 provider-hosted tools are disabled"


def _paths(name: str) -> tuple[str, str, Path, Path]:
    source, task = name.split("/")
    _, sources = campaign.load_sources()
    return source, task, HERE / source / task / "task", campaign.tasks_dir(sources[source]) / task


def _roots(pack: Path) -> list[str]:
    with (pack / "task.toml").open("rb") as file:
        return [root["path"] for root in tomllib.load(file)["scope"]["roots"]]


def _copy_name(index: int) -> str:
    """Where root `index` is copied under a trial's `artifacts/`; roots may share a basename."""
    return f"root-{index}"


def _memory_mib(upstream: Path) -> int:
    with (upstream / "task.toml").open("rb") as file:
        return int(tomllib.load(file)["environment"]["memory_mb"])


def _agent_timeout(upstream: Path) -> int:
    with (upstream / "task.toml").open("rb") as file:
        return int(tomllib.load(file)["agent"]["timeout_sec"])


def _separate_verifier(upstream: Path) -> bool:
    with (upstream / "task.toml").open("rb") as file:
        return tomllib.load(file).get("verifier", {}).get("environment_mode") == "separate"


def _commits(pack: Path, upstream: Path) -> bool:
    """Whether native grades only committed work while the pack does not capture `/app/.git`.

    Upstream's pre_artifacts.sh submits `git diff <base> HEAD`. A candidate carried over
    from such a pack is then committed, as SecureBench graded its working tree.
    """
    if not (upstream / "pre_artifacts.sh").is_file():
        return False
    with (pack / "task.toml").open("rb") as file:
        roots = tomllib.load(file)["scope"]["roots"]
    return not any(r["path"] == "/app" and ".git" in r.get("git_directories", []) for r in roots)


def _log(out: Path, name: str) -> Any:
    return (out / f"{name}.log").open("w")


def _scripted(model: str, pack: Path) -> Path | None:
    """The candidate a `scripted:<candidate>` model names; checks this tool at no model cost."""
    if not model.startswith("scripted:"):
        return None
    return pack.parent / "candidates" / f"{model.removeprefix('scripted:')}.sh"


def _attempt_native(
    upstream: Path,
    roots: list[str],
    harness: str,
    model: str,
    effort: str | None,
    script: Path | None,
    out: Path,
) -> None:
    # Pier copies --artifact paths out before the verifier, but also uploads them into
    # a separate verifier's environment, which changes what it grades. There the
    # agent's container is kept instead, and the roots are copied from it afterwards.
    separate = _separate_verifier(upstream)
    if separate:
        artifacts = ["--ek", "keep_containers=true"]
    else:
        # A job config names each copy, which --artifact cannot.
        config = out / "artifacts.json"
        copies = [{"source": root, "destination": _copy_name(i)} for i, root in enumerate(roots)]
        config.write_text(json.dumps({"artifacts": copies}))
        artifacts = ["-c", str(config)]
    if script is None:
        task = upstream
        agent = [
            "--agent",
            harness,
            "-m",
            f"{'openai' if harness == 'codex' else 'anthropic'}/{model}",
            "--ak",
            f"version={HARNESSES[harness]['version']}",
            # Pier passes it as Claude Code's --effort, and as Codex's
            # model_reasoning_effort, whose default there is high.
            *(["--ak", f"reasoning_effort={effort}"] if effort else []),
        ]
    else:
        # Pier's oracle agent with the candidate as solve.sh, as campaign.grade_native does.
        task = out / "native-task" / upstream.name
        shutil.copytree(upstream, task)
        shutil.rmtree(task / "solution", ignore_errors=True)
        shutil.copytree(script.parent, task / "solution")
        shutil.copy2(script, task / "solution" / "solve.sh")
        agent = ["--agent", "oracle"]
    with _log(out, "pier") as log:
        subprocess.run(
            [
                *map(str, PIER),
                "run",
                "-p",
                str(task),
                *agent,
                *artifacts,
                "-o",
                str(out / "jobs"),
                "--job-name",
                "job",
                "-n",
                "1",
                "-k",
                "1",
                # The default --delete also removes the task image, which the
                # regrades of this attempt and concurrent runs may be about to use.
                "--no-delete",
                "-y",
            ],
            check=False,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if separate:
        _copy_from_kept_containers(out, roots)


def _docker(*arguments: str) -> str:
    return subprocess.run(["docker", *arguments], check=True, capture_output=True, text=True).stdout


def _copy_from_kept_containers(out: Path, roots: list[str]) -> None:
    """Copy each root from the trial's stopped agent container, then remove its containers.

    The containers of a trial carry its name as their Compose project, the agent's
    exactly and the separate verifier's as a prefix (Pier docker.py and trial.py).
    """
    trial = _trial(out)
    name = str(json.loads((trial / "result.json").read_bytes())["trial_name"]).lower()
    labels = _docker(
        "ps",
        "-a",
        "--filter",
        "label=com.docker.compose.project",
        "--format",
        '{{.ID}} {{.Label "com.docker.compose.project"}} {{.Label "com.docker.compose.service"}}',
    )
    containers = [line.split() for line in labels.splitlines()]
    agent = [c[0] for c in containers if c[1] == name and c[2] == "main"]
    if len(agent) == 1:
        for index, root in enumerate(roots):
            target = trial / "artifacts" / _copy_name(index)
            target.mkdir(parents=True)
            _docker("cp", f"{agent[0]}:{root}/.", str(target))
    mine = [c for c in containers if c[1].startswith(name)]
    if mine:
        _docker("rm", "-f", *(c[0] for c in mine))
    for project in {c[1] for c in mine}:
        networks = _docker(
            "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"
        )
        if networks.split():
            _docker("network", "rm", *networks.split())


def _attempt_securebench(
    pack: Path,
    upstream: Path,
    harness: str,
    model: str,
    effort: str | None,
    script: Path | None,
    out: Path,
) -> None:
    version = HARNESSES[harness]["version"]
    if script is None:
        preset = "codex" if harness == "codex" else "claude-code-oauth"
        agent = [
            "--harness",
            f"{preset}:{version}:{model}",
            "--overlay",
            str(REPO / "overlays" / f"{harness}-{version}"),
            *(["--reasoning-effort", effort] if effort else []),
        ]
    else:
        agent = ["--harness", f"scripted:{script}"]
    with _log(out, "securebench") as log:
        subprocess.run(
            [
                "uv",
                "run",
                "securebench",
                "run",
                str(pack),
                "--run-dir",
                str(out / "run"),
                *agent,
                "--qualification",
                str(campaign.WORKER),
                *campaign.upstream_limits(upstream),
                "--agent-timeout",
                str(_agent_timeout(upstream)),
            ],
            check=False,
            cwd=REPO,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def _one(paths: list[Path], what: str) -> Path:
    if len(paths) != 1:
        raise LookupError(f"expected one {what}, found {len(paths)}")
    return paths[0]


def _trial(out: Path) -> Path:
    return _one(
        [path.parent for path in (out / "jobs" / "job").glob("*/result.json")], "Pier trial"
    )


def _record(run_dir: Path) -> tuple[Path, dict[str, Any]]:
    path = _one(sorted((run_dir / "attempts").glob("*/*.json")), "SecureBench record")
    return path, json.loads(path.read_bytes())


def _root_member(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid, info.gid, info.uname, info.gname = 0, 0, "root", "root"
    return info


def _without_links(root: str, harness: str) -> Callable[[tarfile.TarInfo], tarfile.TarInfo | None]:
    """A tar filter for a copy of `root` that drops the harness's install links."""
    prefix = root.rstrip("/") + "/"
    links = {
        "./" + link.removeprefix(prefix)
        for link in HARNESS_LINKS.get(harness, ())
        if link.startswith(prefix)
    }

    def member(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if info.issym() and info.name in links else _root_member(info)

    return member


def _restore_bundle(trial: Path, roots: list[str], bundle: Path, harness: str) -> Path:
    """A scripted candidate that makes each scope root what the native agent left.

    The harness's own install links are left out (`HARNESS_LINKS`).
    """
    manifest = trial / "artifacts" / "manifest.json"
    entries: list[dict[str, str]] = json.loads(manifest.read_bytes()) if manifest.is_file() else []
    copied = {entry["source"]: entry["status"] for entry in entries}
    for index, root in enumerate(roots):
        if copied.get(root, "ok") != "ok" or not (trial / "artifacts" / _copy_name(index)).is_dir():
            raise LookupError(f"{root} was not copied from the native agent's container")
    bundle.mkdir()
    lines = ["#!/bin/sh", "set -e", 'here=$(cd "$(dirname "$0")" && pwd)']
    for index, root in enumerate(roots):
        name = _copy_name(index)
        with tarfile.open(bundle / f"{name}.tar", "w") as archive:
            archive.add(
                trial / "artifacts" / name, arcname=".", filter=_without_links(root, harness)
            )
        lines += [
            f"find '{root}' -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +",
            f"tar -xpf \"$here/{name}.tar\" -C '{root}'",
        ]
    script = bundle / "restore.sh"
    script.write_text("\n".join(lines) + "\n")
    return script


def _apply_bundle(run_dir: Path, bundle: Path, commit: bool) -> Path:
    """A scripted candidate that applies a captured candidate the way replay does.

    Deleted paths, and paths a file or symlink will take, are removed first; a path
    that a directory will take is removed only if it is not already a directory.
    """
    _, record = _record(run_dir)
    if record["candidate"] is None:
        raise LookupError(f"no candidate was captured ({_securebench_verdict(record)})")
    digest = record["candidate"].removeprefix("sha256:")
    manifest = json.loads((run_dir / "store" / "manifests" / f"{digest}.json").read_bytes())
    bundle.mkdir()
    remove: list[str] = []
    directories: list[str] = []
    now = time.time()
    with tarfile.open(bundle / "candidate.tar", "w") as archive:
        for entry in manifest["entries"]:
            path, kind = entry["path"], entry["kind"]
            info = _root_member(tarfile.TarInfo(path.lstrip("/")))
            info.mtime = now
            if kind == "delete":
                remove.append(path)
            elif kind == "dir":
                directories.append(path)
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(info)
            elif kind == "symlink":
                remove.append(path)
                info.type, info.linkname = tarfile.SYMTYPE, entry["target"]
                archive.addfile(info)
            else:
                remove.append(path)
                blob = run_dir / "store" / "blobs" / entry["sha256"].removeprefix("sha256:")
                info.size, info.mode = entry["size"], 0o755 if entry["executable"] else 0o644
                with blob.open("rb") as content:
                    archive.addfile(info, content)
    (bundle / "remove").write_bytes(b"".join(path.encode() + b"\0" for path in remove))
    (bundle / "dirs").write_bytes(b"".join(path.encode() + b"\0" for path in directories))
    script = bundle / "apply.sh"
    script.write_text(
        "#!/bin/sh\n"
        "set -e\n"
        'here=$(cd "$(dirname "$0")" && pwd)\n'
        'xargs -0 rm -rf -- < "$here/remove"\n'
        'xargs -0 sh -c \'for p; do if [ -L "$p" ] || { [ -e "$p" ] && [ ! -d "$p" ]; }; '
        'then rm -f -- "$p"; fi; done\' sh < "$here/dirs"\n'
        'tar -xpmf "$here/candidate.tar" -C /\n'
        + (
            "cd /app\n"
            "git -c safe.directory=/app add -A\n"
            "git -c safe.directory=/app -c user.name=candidate -c user.email=candidate@local "
            'commit -q --no-verify -m "Candidate" || true\n'
            if commit
            else ""
        )
    )
    return script


def _native_verdict(native: float | str) -> str:
    if native == 1.0:
        return "passed"
    if native == 0.0 or native == campaign.NATIVE_TIMEOUT:
        return "failed"
    return str(native)


def _securebench_verdict(result: dict[str, Any]) -> str:
    if result.get("failure_class"):
        return f"{result['status']}/{result['failure_class']}"
    return str(result["status"])


def _regrade(
    pack: Path,
    upstream: Path,
    roots: list[str],
    side: str,
    harness: str,
    out: Path,
    seed: int | None = None,
) -> dict[str, Any]:
    limits = campaign.upstream_limits(upstream)
    regrade = out / "regrade"
    regrade.mkdir()
    commits = _commits(pack, upstream)
    if side == "native":
        restore = _restore_bundle(_trial(out), roots, regrade / "restore", harness)
        (regrade / "to-securebench").mkdir()
        to_securebench = campaign.grade_securebench(
            pack, restore, limits, regrade / "to-securebench", seed
        )
        verdicts = {"N->S": _securebench_verdict(to_securebench), "N->S_run": to_securebench}
        # A failed capture leaves no candidate to carry back, so N->s->N has no verdict.
        try:
            apply = _apply_bundle(
                regrade / "to-securebench" / "securebench", regrade / "apply", commits
            )
        except LookupError as error:
            return {**verdicts, "N->s->N": f"none: {error}"}
        (regrade / "to-native").mkdir()
        native = campaign.grade_native(upstream, apply.parent, apply, regrade / "to-native")
        return {**verdicts, "N->s->N": _native_verdict(native)}
    try:
        apply = _apply_bundle(out / "run", regrade / "apply", commits)
    except LookupError as error:
        return {"S->N": f"none: {error}"}
    (regrade / "to-native").mkdir()
    native = campaign.grade_native(upstream, apply.parent, apply, regrade / "to-native")
    return {"S->N": _native_verdict(native)}


def _object(value: Any) -> dict[str, Any]:
    """A JSON object, or an empty one for anything else."""
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _events(path: Path) -> Iterator[dict[str, Any]]:
    """The JSON objects of a JSON-lines file; other lines, such as warnings, are skipped."""
    if not path.is_file():
        return
    for line in path.read_text(errors="replace").splitlines():
        try:
            yield _object(json.loads(line))
        except json.JSONDecodeError:
            continue


def _transcript(path: Path) -> dict[str, Any]:
    """Models and usage from Claude Code's stream-json output (untrusted, parsed as data only)."""
    main: set[str] = set()
    subagents: set[str] = set()
    result: dict[str, Any] = {}
    for event in _events(path):
        if event.get("type") == "assistant":
            model = str(_object(event.get("message")).get("model"))
            (subagents if event.get("parent_tool_use_id") else main).add(model)
        elif event.get("type") == "result":
            result = event
    usage = _object(result.get("usage"))
    return {
        "models": sorted(main),
        "subagent_models": sorted(subagents),
        "cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "cache_write_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "turns": result.get("num_turns"),
        "result_error": result.get("is_error") if result else "no result",
    }


def _codex_transcript(path: Path, models: set[str]) -> dict[str, Any]:
    """Usage from Codex's `--json` output (untrusted, parsed as data only).

    The output names no model, so `models` come from Codex's session files natively and
    from the relay's log under SecureBench. Input tokens exclude cached
    input, as Claude Code counts them; output tokens include reasoning. Codex reports no
    cost and no count of model calls.
    """
    totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    completed = False
    failure: str | None = None
    for event in _events(path):
        if event.get("type") == "turn.completed":
            completed = True
            usage = _object(event.get("usage"))
            for key in totals:
                value = usage.get(key)
                totals[key] += value if isinstance(value, int) else 0
        elif event.get("type") == "turn.failed":
            failure = " ".join(str(_object(event.get("error")).get("message")).split())[:300]
    return {
        "models": sorted(models),
        "subagent_models": [],
        "cost_usd": None,
        "input_tokens": totals["input_tokens"] - totals["cached_input_tokens"],
        "cache_write_tokens": None,
        "cache_read_tokens": totals["cached_input_tokens"],
        "output_tokens": totals["output_tokens"],
        "turns": None,
        "result_error": failure or (False if completed else "no result"),
    }


def _session_models(folder: Path) -> set[str]:
    """The models of Codex's session files, which Pier copies out (`turn_context` events)."""
    return {
        str(_object(event.get("payload")).get("model"))
        for path in folder.rglob("*.jsonl")
        for event in _events(path)
        if event.get("type") == "turn_context"
    }


def _relay_models(path: Path) -> set[str]:
    """The models the agent's requests named, as the relay logged them."""
    return {str(event["model"]) for event in _events(path) if event.get("model") is not None}


def _relay_errors(path: Path) -> list[str]:
    errors: list[str] = []
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("event") != "request" or event.get("path") in KNOWN_REFUSALS:
            continue
        if event.get("status") != 200:
            errors.append(f"{event.get('status')} {event.get('reason', '')}".strip())
    return errors


def _denied_hosts(path: Path) -> list[str]:
    if not path.is_file():
        return []
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return sorted({str(e.get("host")) for e in events if e.get("decision") == "denied"})


def _seconds(timing: dict[str, Any] | None) -> float | None:
    if not timing or not timing.get("started_at") or not timing.get("finished_at"):
        return None
    started = datetime.fromisoformat(timing["started_at"])
    return (datetime.fromisoformat(timing["finished_at"]) - started).total_seconds()


def _summary_native(out: Path, harness: str) -> dict[str, Any]:
    trial = _trial(out)
    agent = trial / "agent"
    transcript = (
        _codex_transcript(agent / "codex.txt", _session_models(agent / "sessions"))
        if harness == "codex"
        else _transcript(agent / "claude-code.txt")
    )
    result = _object(json.loads((trial / "result.json").read_bytes()))
    exception = _object(result.get("exception_info")).get("exception_type")
    reward = _object(_object(result.get("verifier_result")).get("rewards")).get("reward")
    errors = [] if exception in (None, "AgentTimeoutError") else [str(exception)]
    return {
        "verdict": _native_verdict(float(reward)) if reward is not None else f"error: {exception}",
        "agent_seconds": _seconds(result.get("agent_execution")),
        "time_limit_expired": exception == "AgentTimeoutError",
        "harness_version": _object(result.get("agent_info")).get("version"),
        "provider_errors": errors,
        "denied_hosts": [],
        **transcript,
    }


def _summary_securebench(out: Path, harness: str) -> dict[str, Any]:
    path, record = _record(out / "run")
    stem = path.with_suffix("")
    relay = stem.with_suffix(".relay")
    transcript = (
        _codex_transcript(stem.with_suffix(".transcript"), _relay_models(relay))
        if harness == "codex"
        else _transcript(stem.with_suffix(".transcript"))
    )
    rejudge = subprocess.run(
        ["uv", "run", "securebench", "rejudge", str(out / "run")],
        check=False,
        cwd=REPO,
        capture_output=True,
    )
    return {
        "verdict": _securebench_verdict(record),
        "admitted": record["admitted"],
        "dirty": record["provenance"]["framework"]["dirty"],
        "rejudged": rejudge.returncode == 0,
        "pack_digest": record["provenance"]["task"]["pack"],
        "agent_seconds": record["agent"]["duration_seconds"],
        "time_limit_expired": record["agent"]["time_limit_expired"],
        "agent_ending": record["agent"]["ending"],
        "harness_version": record["provenance"]["agent"]["version"],
        "provider_errors": _relay_errors(relay),
        "denied_hosts": _denied_hosts(stem.with_suffix(".proxy")),
        **transcript,
    }


def _validity(summary: dict[str, Any], model: str) -> str:
    """`ok`, or why the attempt is left out and run again."""
    if summary.get("admitted") is False or summary.get("dirty") or summary.get("rejudged") is False:
        return "not-admitted"
    if model.startswith("scripted:"):
        return "ok"
    # An agent stopped at its time limit, or killed at the task's memory limit (which
    # natively applies too), never writes Claude Code's final result event.
    stopped = summary["time_limit_expired"] or summary.get("agent_ending") == "memory_killed"
    no_result = summary["result_error"] == "no result" and stopped
    result_error = summary["result_error"] and not no_result
    errors = [e for e in summary["provider_errors"] if not e.startswith(HOSTED_TOOLS_REFUSAL)]
    # SecureBench's own `invalid` is a host error, never the agent's (architecture Section 10).
    invalid = str(summary["verdict"]).startswith("invalid")
    if invalid or errors or result_error or "<synthetic>" in summary["models"]:
        return "infrastructure"
    if summary["models"] != [model]:
        return "model-drift"
    return "ok"


def _unit(name: str, harness: str, model: str, effort: str | None, side: str, root: Path) -> None:
    """One attempt and its regrades; its `attempt.json` marks it done."""
    source, task, pack, upstream = _paths(name)
    out = root / model.replace(":", "-") / source / task / side
    if (out / "attempt.json").is_file():
        return
    if out.exists():
        raise SystemExit(f"{out} holds an unfinished attempt; move it aside first")
    out.mkdir(parents=True)
    roots = _roots(pack)
    script = _scripted(model, pack)
    started = time.time()
    if side == "native":
        _attempt_native(upstream, roots, harness, model, effort, script, out)
        summary = _summary_native(out, harness)
    else:
        _attempt_securebench(pack, upstream, harness, model, effort, script, out)
        summary = _summary_securebench(out, harness)
    try:
        cross = _regrade(pack, upstream, roots, side, harness, out)
    except LookupError as error:
        cross = {"regrade_error": str(error)}
    summary = {
        "source": source,
        "task": task,
        "harness": harness,
        "model": model,
        "effort": effort,
        "side": side,
        **summary,
        **cross,
        "wall_seconds": round(time.time() - started),
    }
    summary["validity"] = _validity(summary, model)
    (out / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{model} {name} {side}: {summary['verdict']} ({summary['validity']})", flush=True)


def _token(path: Path, name: str) -> str:
    for line in path.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip()
    raise SystemExit(f"{path} has no {name}=... line with a value")


def run(
    names: list[str],
    harness: str,
    model: str,
    effort: str | None,
    token_file: Path | None,
    root: Path,
    usage_limit: int | None,
    memory_budget: int,
    max_running: int,
    min_available: int | None,
) -> int:
    if campaign.git("-C", str(REPO), "status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("the tree has uncommitted changes; SecureBench runs would not be clean")
    # Pier and the harnesses prefer these when set; the study uses --token-file's credential
    # only, with each provider's own endpoint.
    for key in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
    ):
        os.environ.pop(key, None)
    spec = HARNESSES[harness]
    if not model.startswith("scripted:"):
        if token_file is None:
            raise SystemExit("a model run needs --token-file")
        if effort and effort not in spec["efforts"]:
            raise SystemExit(f"{harness} accepts --effort {', '.join(spec['efforts'])}")
        if usage_limit is not None and harness != "claude-code":
            raise SystemExit("--usage-limit reads Claude Code's usage reports only")
        os.environ[spec["credential"]] = _token(token_file, spec["credential"])
    elif effort:
        raise SystemExit("--effort applies only to a model run")
    timeouts = {name: _agent_timeout(_paths(name)[3]) for name in names}
    # Longest first, so that the slowest attempts do not start last and hold up the end.
    units = sorted(
        ((name, side) for name in names for side in SIDES), key=lambda unit: -timeouts[unit[0]]
    )
    memory = {name: _memory_mib(_paths(name)[3]) for name in names}
    failed = 0
    paused = False
    with campaign.QUALIFY_LOCK.open("a") as lock:
        campaign.wait_for_the_worker(lock)
        with ThreadPoolExecutor(max_workers=max_running) as pool:
            running: dict[Future[None], tuple[str, str]] = {}
            while units or running:
                used = sum(memory[name] for name, _ in running.values())
                ready, why = _usage_allows(root, usage_limit)
                if ready:
                    ready, why = _memory_allows(min_available)
                if ready == paused:
                    paused = not ready
                    print(why if paused else "resuming", flush=True)
                for unit in list(units):
                    fits = used + memory[unit[0]] <= memory_budget or not running
                    if ready and len(running) < max_running and fits:
                        arguments = (unit[0], harness, model, effort, unit[1], root)
                        running[pool.submit(_unit, *arguments)] = unit
                        used += memory[unit[0]]
                        units.remove(unit)
                if not running:
                    time.sleep(120)
                    continue
                done, _ = wait(running, timeout=None if ready else 120, return_when=FIRST_COMPLETED)
                for future in done:
                    name, side = running.pop(future)
                    if future.exception() is not None:
                        failed += 1
                        print(f"{model} {name} {side}: error: {future.exception()!r}", flush=True)
    return 1 if failed else 0


def regrade(attempts: list[Path]) -> int:
    """Cross-grade finished attempts again, keeping their agent runs.

    For a cross-grade that the worker or this tool broke while the attempt itself stands.
    The earlier grades move to `regrade-replaced-<n>/`, and `attempt.json` counts them.
    """
    if campaign.git("-C", str(REPO), "status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("the tree has uncommitted changes; SecureBench runs would not be clean")
    with campaign.QUALIFY_LOCK.open("a") as lock:
        campaign.wait_for_the_worker(lock)
        for out in attempts:
            summary = _object(json.loads((out / "attempt.json").read_bytes()))
            name = f"{summary['source']}/{summary['task']}"
            _, _, pack, upstream = _paths(name)
            replaced = int(summary.get("regrades_replaced") or 0) + 1
            (out / "regrade").rename(out / f"regrade-replaced-{replaced}")
            for key in ("N->S", "N->S_run", "N->s->N", "S->N", "regrade_error"):
                summary.pop(key, None)
            harness = str(summary.get("harness") or "claude-code")
            try:
                cross = _regrade(pack, upstream, _roots(pack), summary["side"], harness, out)
            except LookupError as error:
                cross = {"regrade_error": str(error)}
            summary.update(cross, regrades_replaced=replaced)
            (out / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
            verdicts = {k: v for k, v in cross.items() if not k.endswith("_run")}
            print(f"{name} {summary['side']}: regraded {verdicts}", flush=True)
    return 0


def _memory_allows(min_available: int | None) -> tuple[bool, str]:
    """False, and why, while the host has less than `min_available` MiB of memory available.

    The memory budget counts upstream limits, not use; this guards the host itself,
    where running out of memory has killed the coordinating session before.
    """
    if min_available is None:
        return True, ""
    with open("/proc/meminfo") as file:
        fields = dict(line.split(":", 1) for line in file)
    available = int(fields["MemAvailable"].split()[0]) // 1024
    if available >= min_available:
        return True, ""
    return False, f"{available} MiB of memory available, below {min_available}; waiting"


def _usage(root: Path) -> tuple[float, float] | None:
    """The latest five-hour usage and its reset time that Claude Code reported in a transcript.

    Every Claude Code run streams `rate_limit_event`s with the account's usage, so the
    newest transcript under `root` tells how much of the five-hour window is used.
    """
    transcripts = [*root.glob("*/*/*/*/run/attempts/*/*.transcript")]
    transcripts += root.glob("*/*/*/*/jobs/job/*/agent/claude-code.txt")
    for path in sorted(transcripts, key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
        with path.open("rb") as file:
            file.seek(max(0, path.stat().st_size - 4_000_000))
            tail = file.read().decode(errors="replace")
        for line in reversed(tail.splitlines()):
            if '"rate_limit_event"' not in line:
                continue
            try:
                info = _object(_object(json.loads(line)).get("rate_limit_info"))
            except json.JSONDecodeError:
                continue
            window = _object(_object(info.get("unifiedWindows")).get("five_hour"))
            if "utilization" in window and "resetsAt" in window:
                return float(window["utilization"]), float(window["resetsAt"])
    return None


def _usage_allows(root: Path, limit: int | None) -> tuple[bool, str]:
    """False, and why, while the latest five-hour usage is at or above `limit` percent."""
    usage = None if limit is None else _usage(root)
    if limit is None or usage is None or usage[1] <= time.time() or usage[0] * 100 < limit:
        return True, ""
    return False, f"five-hour usage {usage[0]:.0%}, waiting for the reset at {time.ctime(usage[1])}"


COLUMNS = (
    "source task model effort side validity verdict N->S N->s->N S->N agent_seconds "
    "time_limit_expired cost_usd input_tokens cache_write_tokens cache_read_tokens "
    "output_tokens turns models subagent_models harness_version provider_errors denied_hosts "
    "regrade_error wall_seconds"
).split()


def _load(path: Path) -> dict[str, Any]:
    """An `attempt.json`, with its validity recomputed under the current rules."""
    summary = _object(json.loads(path.read_bytes()))
    if summary.get("side") == "securebench" and "agent_ending" not in summary:
        # Rows written before the field existed: SecureBench's record has it.
        summary["agent_ending"] = _record(path.parent / "run")[1]["agent"]["ending"]
    # Recomputed, so that a correction to the rules applies to attempts already run.
    summary["validity"] = _validity(summary, str(summary["model"]))
    return summary


def _row(summary: dict[str, Any]) -> str:
    cells: list[str] = []
    for column in COLUMNS:
        value: Any = summary.get(column, "")
        if isinstance(value, list):
            value = ",".join(map(str, cast(list[Any], value)))
        cells.append(str(value))
    return "\t".join("" if cell == "None" else cell for cell in cells)


def report(roots: list[Path]) -> int:
    print("\t".join(COLUMNS))
    for path in sorted(p for root in roots for p in root.glob("*/*/*/*/attempt.json")):
        print(_row(_load(path)))
    return 0


def _verifier(trial: Path) -> dict[str, Any]:
    """A Pier verifier's reward and the tests that did not pass, from its own output files."""
    folder = trial / "verifier"
    out: dict[str, Any] = {}
    if (folder / "reward.json").is_file():
        out["reward"] = json.loads((folder / "reward.json").read_bytes())
    elif (folder / "reward.txt").is_file():
        out["reward"] = (folder / "reward.txt").read_text().strip()
    if (folder / "ctrf.json").is_file():
        results = _object(_object(json.loads((folder / "ctrf.json").read_bytes())).get("results"))
        tests = [_object(t) for t in cast(list[Any], results.get("tests") or [])]
        out["summary"] = results.get("summary")
        out["not_passed"] = sorted(str(t.get("name")) for t in tests if t.get("status") != "passed")
    return out


def _export_candidate(run_dir: Path, target: Path, limit: int) -> dict[str, Any]:
    """The candidate SecureBench captured in `run_dir`: its manifest, and its files when small.

    The archive holds every written file, directory and symlink at its path, with fixed
    owners and times so that the same candidate always gives the same bytes; deletions
    are only in the manifest.
    """
    _, record = _record(run_dir)
    if record["candidate"] is None:
        return {"captured": False}
    digest = str(record["candidate"]).removeprefix("sha256:")
    manifest_path = run_dir / "store" / "manifests" / f"{digest}.json"
    shutil.copyfile(manifest_path, target / "candidate-manifest.json")
    entries = [
        _object(e) for e in cast(list[Any], json.loads(manifest_path.read_bytes())["entries"])
    ]
    size = sum(int(e.get("size") or 0) for e in entries)
    included = size <= limit
    if included:
        with (
            gzip.GzipFile(target / "candidate.tar.gz", "wb", mtime=0) as packed,
            tarfile.open(fileobj=packed, mode="w", format=tarfile.PAX_FORMAT) as archive,
        ):
            for entry in sorted(entries, key=lambda e: str(e["path"])):
                kind = entry["kind"]
                if kind == "delete":
                    continue
                info = _root_member(tarfile.TarInfo(str(entry["path"]).lstrip("/")))
                info.mtime = 0
                if kind == "dir":
                    info.type, info.mode = tarfile.DIRTYPE, 0o755
                    archive.addfile(info)
                elif kind == "symlink":
                    info.type, info.linkname = tarfile.SYMTYPE, str(entry["target"])
                    archive.addfile(info)
                else:
                    blob = (
                        run_dir / "store" / "blobs" / str(entry["sha256"]).removeprefix("sha256:")
                    )
                    info.size, info.mode = (
                        int(entry["size"]),
                        0o755 if entry["executable"] else 0o644,
                    )
                    with blob.open("rb") as content:
                        archive.addfile(info, content)
    return {
        "captured": True,
        "candidate": record["candidate"],
        "bytes": size,
        "files_included": included,
    }


def export(attempts: Path, out: Path, replaced: Path | None, notes: Path | None, limit: int) -> int:
    """The committed record of a campaign: one folder per task, and its tables.

    Per side it keeps SecureBench's verdict record of that side's files, the native
    verifiers' outcomes, and the captured candidate (its files only up to `limit` bytes).
    Transcripts, Pier jobs and stores stay in the campaign's raw folder.
    """
    remarks = _object(json.loads(notes.read_bytes())) if notes else {}
    task_notes, reasons = _object(remarks.get("tasks")), _object(remarks.get("replaced"))
    out.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    replaced_rows: list[str] = []
    for path in sorted(attempts.glob("*/*/*/*/attempt.json")):
        attempt, task = path.parent, path.parent.parent.name
        summary = _load(path)
        rows.append(_row(summary))
        folder = out / task
        target = folder / attempt.name
        target.mkdir(parents=True, exist_ok=True)
        run_dir = (
            attempt / "run"
            if attempt.name == "securebench"
            else attempt / "regrade" / "to-securebench" / "securebench"
        )
        if (run_dir / "attempts").is_dir():
            shutil.copyfile(_record(run_dir)[0], target / "securebench-record.json")
            summary["candidate_export"] = _export_candidate(run_dir, target, limit)
        verifiers: dict[str, Any] = {}
        if attempt.name == "native":
            verifiers["N"] = _verifier(_trial(attempt))
        regrade = attempt / "regrade" / "to-native" / "native" / "job"
        for trial in (p.parent for p in regrade.glob("*/result.json")):
            verifiers["N->s->N" if attempt.name == "native" else "S->N"] = _verifier(trial)
        (target / "verifier.json").write_text(json.dumps(verifiers, indent=2) + "\n")
        result_path = folder / "result.json"
        result = _object(json.loads(result_path.read_bytes())) if result_path.is_file() else {}
        result.update(task=task, source=summary["source"], notes=task_notes.get(task, []))
        result[attempt.name] = summary
        earlier: list[dict[str, Any]] = []
        for old in sorted(replaced.glob(f"*/{task}/*")) if replaced else []:
            if not old.name.startswith(attempt.name):
                continue
            entry: dict[str, Any] = {"kept_as": old.name, "why": reasons.get(old.name, "")}
            if (old / "attempt.json").is_file():
                kept = _load(old / "attempt.json")
                entry.update(
                    {k: kept.get(k) for k in ("validity", "verdict", "N->S", "N->s->N", "S->N")}
                )
            earlier.append(entry)
            replaced_rows.append(
                "\t".join(
                    str(x or "")
                    for x in (
                        summary["source"],
                        task,
                        attempt.name,
                        entry["kept_as"],
                        entry["why"],
                        entry.get("validity"),
                        entry.get("verdict"),
                        entry.get("N->S"),
                        entry.get("N->s->N"),
                        entry.get("S->N"),
                    )
                )
            )
        result.setdefault("replaced", {})[attempt.name] = earlier
        result_path.write_text(json.dumps(result, indent=2) + "\n")
    (out / "attempts.tsv").write_text("\n".join(["\t".join(COLUMNS), *rows]) + "\n")
    head = "source task side kept_as why_replaced validity verdict N->S N->s->N S->N".split()
    (out / "replaced-attempts.tsv").write_text("\n".join(["\t".join(head), *replaced_rows]) + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fidelity study tooling")
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("names", nargs="+", help="<source>/<task>")
    runner.add_argument("--model", required=True, help="a model id, or scripted:<candidate>")
    runner.add_argument(
        "--harness",
        choices=sorted(HARNESSES),
        default="claude-code",
        help="the model harness on both sides",
    )
    runner.add_argument(
        "--effort",
        choices=("minimal", "low", "medium", "high", "xhigh", "max"),
        help="the harness's reasoning effort on both sides; its default when omitted",
    )
    runner.add_argument(
        "--token-file",
        type=Path,
        help="a file with CLAUDE_CODE_OAUTH_TOKEN=... (claude-code) or OPENAI_API_KEY=... (codex)",
    )
    runner.add_argument("--out", type=Path, required=True)
    runner.add_argument(
        "--usage-limit",
        type=int,
        help="start no attempt while five-hour usage is at or above it (%%)",
    )
    runner.add_argument(
        "--memory-budget-mib",
        type=int,
        default=campaign.PARALLEL_MEMORY_MIB,
        help="the sum of the upstream memory limits of the attempts that run at once",
    )
    runner.add_argument("--max-running", type=int, default=campaign.MAX_WORKERS)
    runner.add_argument(
        "--min-available-mib",
        type=int,
        help="start no attempt while the host has less memory available than this",
    )
    commands.add_parser("report").add_argument("roots", nargs="+", type=Path)
    commands.add_parser("regrade", help="cross-grade finished attempts again").add_argument(
        "attempts", nargs="+", type=Path, help="an attempt folder, .../<source>/<task>/<side>"
    )
    exporter = commands.add_parser("export", help="the committed record of a campaign")
    exporter.add_argument("attempts", type=Path, help="the raw attempts folder of one model")
    exporter.add_argument("--out", type=Path, required=True)
    exporter.add_argument("--replaced", type=Path, help="the raw folder of replaced attempts")
    exporter.add_argument(
        "--notes", type=Path, help='JSON: {"tasks": {task: [note]}, "replaced": {name: why}}'
    )
    exporter.add_argument(
        "--candidate-limit-bytes",
        type=int,
        default=10_000_000,
        help="include a candidate's files only up to this total size; its manifest always",
    )
    arguments = parser.parse_args()
    if arguments.command == "run":
        return run(
            arguments.names,
            arguments.harness,
            arguments.model,
            arguments.effort,
            arguments.token_file,
            arguments.out,
            arguments.usage_limit,
            arguments.memory_budget_mib,
            arguments.max_running,
            arguments.min_available_mib,
        )
    if arguments.command == "export":
        return export(
            arguments.attempts,
            arguments.out,
            arguments.replaced,
            arguments.notes,
            arguments.candidate_limit_bytes,
        )
    if arguments.command == "regrade":
        return regrade(arguments.attempts)
    return report(arguments.roots)


if __name__ == "__main__":
    sys.exit(main())
