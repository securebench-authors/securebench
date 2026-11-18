"""The attempt lifecycle (architecture Sections 9 to 11). Wiring only."""

from dataclasses import dataclass
from pathlib import Path

from securebench.agent.harness import Harness
from securebench.agent.network import start_services, stop_services
from securebench.agent.run import preflight, resources, run_agent
from securebench.candidate import capture, index
from securebench.candidate.state import BaselineIndex
from securebench.candidate.store import Store
from securebench.core import hashing, jsondata
from securebench.core.errors import HostError, PackError, Rejected
from securebench.core.evidence import Ending, Evidence, Judgment, Plan, plan_to_json
from securebench.core.jsondata import JsonValue
from securebench.core.limits import Settings
from securebench.core.task import Task
from securebench.core.verdict import AttemptFailed, Status, Verdict
from securebench.evaluation.plan import validate_plan
from securebench.evaluation.run import evaluate
from securebench.isolation.docker import DockerBackend
from securebench.oracle.process import OracleProcess
from securebench.oracle.static import check_oracle_source
from securebench.results.records import attempt_record, framework
from securebench.results.run import RunDirectory
from securebench.taskspec.load import load


@dataclass(frozen=True)
class Context:
    """Everything shared by the attempts of one run."""

    backend: DockerBackend
    stock_image: str
    settings: Settings
    seed: int
    run: RunDirectory
    store: Store
    admitted: bool
    worker: JsonValue
    providers: dict[str, dict[str, JsonValue]]
    extra_hosts: tuple[tuple[str, str], ...]
    extra_networks: tuple[str, ...]


@dataclass(frozen=True)
class Prepared:
    """A task that passed pack validation, with its baseline index and validated plan."""

    task: Task
    baseline_image: str
    index: BaselineIndex
    plan: Plan
    provenance: JsonValue


def load_and_check(pack: Path) -> Task:
    """Static pack validation, including the static Oracle checks. Raises `PackError`."""
    task = load(pack)
    oracle = task.hidden_dir / "oracle.py"
    try:
        check_oracle_source(oracle.read_text(encoding="utf-8"), "hidden/oracle.py")
    except (Rejected, UnicodeDecodeError) as error:
        raise PackError(f"{pack}: {error}") from None
    return task


def prepare(
    backend: DockerBackend, stock_image: str, store: Store, pack: Path, seed: int
) -> Prepared:
    """Pack validation, static and live, before any Agent starts.

    Raises `PackError` or `HostError`.
    """
    task = load_and_check(pack)
    baseline_image = backend.resolve_image(task.public.baseline.image)
    baseline_index = index.build_index(backend, stock_image, task, baseline_image, store)
    index.check_repository(backend, stock_image, task, baseline_image)
    with OracleProcess(task) as oracle:
        plan = oracle.plan(seed)
    validate_plan(task, plan)
    provenance: JsonValue = {
        "baseline_image": baseline_image,
        "baseline_index": baseline_index.digest,
        "image": task.public.baseline.image,
        "oracle": hashing.sha256((task.hidden_dir / "oracle.py").read_bytes()),
        "pack": task.digest,
        "plan": jsondata.digest(plan_to_json(plan)),
        "task": hashing.sha256((task.root / "task.toml").read_bytes()),
    }
    return Prepared(task, baseline_image, baseline_index, plan, provenance)


def run_attempt(context: Context, prepared: Prepared, harness: Harness) -> JsonValue:
    """Run one attempt from Agent start to verdict, record it, and return the record."""
    task = prepared.task
    number = context.run.next_attempt(task.id)
    logs: dict[str, str] = {}
    agent: JsonValue = None
    candidate_id: str | None = None
    judged: list[tuple[str, int | None, Evidence, Judgment | None]] = []
    host_errors: list[JsonValue] = []
    backend = context.backend
    try:
        preflight(backend, task.public, prepared.baseline_image, harness, context.settings.limits)
        providers = {name: context.providers[name] for name in harness.providers}
        services = start_services(
            backend,
            context.stock_image,
            task.public.allowed_domains,
            providers,
            context.settings.provider_hosted_tools,
            context.extra_hosts,
            context.extra_networks,
        )
        try:
            agent_run = run_agent(
                backend,
                task.public,
                prepared.baseline_image,
                harness,
                services,
                context.settings.limits,
            )
        finally:
            relay_log, proxy_log = stop_services(backend, services)
            logs["relay"] = context.run.save_log(task.id, number, "relay", relay_log)
            logs["proxy"] = context.run.save_log(task.id, number, "proxy", proxy_log)
        logs["transcript"] = context.run.save_log(
            task.id, number, "transcript", agent_run.transcript
        )
        logs["stderr"] = context.run.save_log(task.id, number, "stderr", agent_run.stderr)
        agent = {
            "duration_seconds": agent_run.facts.duration_seconds,
            "ending": agent_run.facts.ending.value,
            "exit_status": agent_run.facts.exit_status,
            "time_limit_expired": agent_run.facts.ending is Ending.TIMED_OUT,
        }
        try:
            manifest = capture.capture(
                backend,
                context.stock_image,
                task,
                prepared.index,
                agent_run.snapshot,
                context.store,
            )
        finally:
            backend.destroy_snapshot(agent_run.snapshot)
        candidate_id = manifest.id
        with OracleProcess(task) as oracle:
            evaluation = evaluate(
                backend,
                context.stock_image,
                task,
                prepared.index,
                manifest,
                context.store,
                oracle,
                prepared.plan,
                resources(context.settings.limits),
                context.settings.case_retries,
            )
        verdict = evaluation.verdict
        judged = [
            (item.check_id, item.case_index, item.evidence, item.judgment)
            for item in evaluation.judged
        ]
        host_errors = list(evaluation.host_errors)
    except AttemptFailed as failure:
        verdict = Verdict(Status.FAILED, failure.failure_class, ({"reason": failure.reason},))
    except HostError as error:
        verdict = Verdict(Status.INVALID, None, ({"host_error": error.reason},))
    provenance: JsonValue = {
        "agent": {
            "command": list(harness.command),
            "harness": harness.name,
            "overlay": harness_digest(harness),
            "version": harness.version,
        },
        "candidate": candidate_id,
        "framework": framework(),
        "run": {"seed": context.seed, "settings": context.settings.to_json()},
        "task": prepared.provenance,
        "worker": context.worker,
    }
    record = attempt_record(
        task_id=task.id,
        attempt=number,
        verdict=verdict,
        provenance=provenance,
        candidate_id=candidate_id,
        agent=agent,
        judged=judged,
        host_errors=host_errors,
        logs=logs,
        admitted=context.admitted,
    )
    context.run.record(task.id, number, record)
    return record


def harness_digest(harness: Harness) -> str:
    """The tooling overlay's digest: every file's path, executable bit and content."""
    entries: list[JsonValue] = []
    for path in sorted(harness.overlay.rglob("*"), key=lambda item: str(item).encode()):
        relative = str(path.relative_to(harness.overlay))
        if path.is_symlink():
            entries.append([relative, "symlink", str(path.readlink())])
        elif path.is_file():
            executable = bool(path.stat().st_mode & 0o100)
            entries.append([relative, executable, hashing.sha256(path.read_bytes())])
    return jsondata.digest(entries)
