"""The `securebench` command: validate, qualify, run, rejudge and cleanup."""

import argparse
import sys
import tempfile
from pathlib import Path

from securebench.agent.harness import Harness, claude_code, codex, scripted
from securebench.agent.network import PROVIDERS
from securebench.candidate.store import Store
from securebench.core import jsondata
from securebench.core.errors import HostError, PackError, Rejected
from securebench.core.evidence import Plan, evidence_from_json
from securebench.core.jsondata import JsonValue
from securebench.core.limits import Limits, Settings
from securebench.isolation.backend import STOCK_IMAGE
from securebench.isolation.configuration import check_configuration
from securebench.isolation.docker import DockerBackend, remove_leftovers
from securebench.isolation.qualification import qualify
from securebench.oracle.process import OracleProcess
from securebench.results.records import framework
from securebench.results.run import RunDirectory, load_records
from securebench.runner.attempt import Context, Prepared, load_and_check, prepare, run_attempt

MIB = 1 << 20


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="securebench", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate task packs")
    validate.add_argument("packs", nargs="+", type=Path)
    validate.add_argument("--live", action="store_true", help="also check baselines in Docker")

    qualification = commands.add_parser("qualify", help="qualify this worker (B1 to B8)")
    qualification.add_argument("--output", type=Path, default=Path("qualification.json"))

    run = commands.add_parser("run", help="run tasks with a harness")
    run.add_argument("packs", nargs="+", type=Path)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument(
        "--harness",
        required=True,
        help="scripted:<script>, claude-code:<version>:<model>, "
        "claude-code-oauth:<version>:<model> or codex:<version>:<model>",
    )
    run.add_argument("--overlay", type=Path, help="the prepared overlay of a model harness")
    run.add_argument(
        "--reasoning-effort",
        help="the reasoning effort of the codex harness (minimal, low, medium, high or xhigh) "
        "or of a claude-code harness (low, medium, high, xhigh or max)",
    )
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--memory-mib", type=int, default=4096)
    run.add_argument("--cpus", type=float, default=2.0)
    run.add_argument("--pids", type=int, default=1024)
    run.add_argument("--disk-mib", type=int, default=10240)
    run.add_argument("--agent-timeout", type=int, default=3600)
    run.add_argument("--case-retries", type=int, default=2)
    run.add_argument("--provider-hosted-tools", action="store_true")
    run.add_argument("--qualification", type=Path, help="this worker's qualification record")
    run.add_argument(
        "--development",
        action="store_true",
        help="run on an unqualified worker; every record says admitted: false",
    )

    rejudge = commands.add_parser("rejudge", help="recompute every verdict of a run offline")
    rejudge.add_argument("run_dir", type=Path)

    commands.add_parser("cleanup", help="remove SecureBench containers, networks and images")

    arguments = parser.parse_args(argv)
    try:
        match arguments.command:
            case "validate":
                return _validate(arguments.packs, arguments.live)
            case "qualify":
                return _qualify(arguments.output)
            case "run":
                return _run(arguments)
            case "rejudge":
                return _rejudge(arguments.run_dir)
            case _:
                for identifier in remove_leftovers():
                    print(f"removed {identifier}")
                return 0
    except (PackError, HostError) as error:
        print(f"securebench: {error.reason}", file=sys.stderr)
        return 2


def _validate(packs: list[Path], live: bool) -> int:
    backend = DockerBackend(disk_quota=False)
    for pack in packs:
        task = load_and_check(pack)
        if live:
            stock = backend.resolve_image(STOCK_IMAGE)
            with tempfile.TemporaryDirectory() as directory:
                prepare(backend, stock, Store(Path(directory)), pack, 0)
        print(f"{task.id}: valid, pack {task.digest}")
    return 0


def _qualify(output: Path) -> int:
    backend = DockerBackend(disk_quota=False)
    stock = backend.resolve_image(STOCK_IMAGE)
    configuration = check_configuration(stock)
    record = qualify(DockerBackend(configuration.disk_quota), stock, configuration.facts)
    output.write_bytes(jsondata.encode({"id": record.id, "record": record.to_json()}))
    for probe in record.probes:
        print(
            f"{'PASS' if probe.passed else 'FAIL'} {probe.guarantee} {probe.name}: {probe.detail}"
        )
    for failure in configuration.failures:
        print(f"FAIL configuration: {failure}")
    print(f"qualification {record.id} written to {output}")
    return 0 if record.passed and not configuration.failures else 1


def _harness(text: str, overlay: Path | None, effort: str | None) -> Harness:
    kind, _, value = text.partition(":")
    if effort is not None and kind not in ("claude-code", "claude-code-oauth", "codex"):
        raise HostError("--reasoning-effort applies only to the codex and claude-code harnesses")
    if kind == "scripted" and value:
        return scripted(Path(value))
    version, _, model = value.partition(":")
    if kind in ("claude-code", "claude-code-oauth", "codex") and version and model:
        if overlay is None:
            raise HostError(f"the {kind} harness needs --overlay (see docs/operating.md)")
        if kind == "codex":
            return codex(overlay.resolve(), version, model, effort)
        return claude_code(overlay.resolve(), version, model, kind == "claude-code-oauth", effort)
    raise HostError(f"unknown harness {text!r}")


def _worker(stock: str, qualification_path: Path | None) -> tuple[bool, JsonValue, bool]:
    """Whether this worker may run admitted attempts, its record, and its disk-quota support."""
    configuration = check_configuration(stock)
    failures: list[str] = list(configuration.failures)
    qualification_id: str | None = None
    if qualification_path is None:
        failures.append("no qualification record was given")
    else:
        try:
            stored = jsondata.decode(qualification_path.read_bytes(), 1 << 24)
        except (OSError, Rejected) as error:
            raise HostError(f"cannot read the qualification record: {error}") from None
        if not isinstance(stored, dict) or not isinstance(stored.get("record"), dict):
            raise HostError("the qualification record is malformed")
        record = stored["record"]
        assert isinstance(record, dict)
        qualification_id = jsondata.digest(record)
        probes = record.get("probes")
        if not isinstance(probes, list) or not all(
            isinstance(probe, dict) and probe.get("passed") is True for probe in probes
        ):
            failures.append("the qualification record has failing probes")
        if record.get("facts") != configuration.facts:
            failures.append("the qualification record was made for a different configuration")
    listed: list[JsonValue] = list(failures)
    worker: JsonValue = {
        "configuration": configuration.facts,
        "failures": listed,
        "qualification": qualification_id,
    }
    return not failures, worker, configuration.disk_quota


def _run(arguments: argparse.Namespace) -> int:
    harness = _harness(arguments.harness, arguments.overlay, arguments.reasoning_effort)
    settings = Settings(
        provider_hosted_tools=arguments.provider_hosted_tools,
        case_retries=arguments.case_retries,
        limits=Limits(
            memory_bytes=arguments.memory_mib * MIB,
            nano_cpus=int(arguments.cpus * 1e9),
            pids=arguments.pids,
            disk_bytes=arguments.disk_mib * MIB,
            agent_timeout_seconds=arguments.agent_timeout,
        ),
    )
    probe = DockerBackend(disk_quota=False)
    stock = probe.resolve_image(STOCK_IMAGE)
    admitted, worker, disk_quota = _worker(stock, arguments.qualification)
    if not admitted and not arguments.development:
        print(f"securebench: this worker is not qualified: {worker}", file=sys.stderr)
        print("securebench: pass --development to run anyway (records say admitted: false)")
        return 2
    backend = DockerBackend(disk_quota)
    tasks: list[JsonValue] = [str(pack.resolve()) for pack in arguments.packs]
    configuration: JsonValue = {
        "admitted": admitted,
        "framework": framework(),
        "harness": {
            "command": list(harness.command),
            "name": harness.name,
            "overlay": str(harness.overlay),
            "version": harness.version,
        },
        "seed": arguments.seed,
        "settings": settings.to_json(),
        "tasks": tasks,
        "worker": worker,
    }
    with RunDirectory(arguments.run_dir, configuration) as run:
        store = Store(run.store_root)
        prepared: list[Prepared] = [
            prepare(backend, stock, store, pack, arguments.seed) for pack in arguments.packs
        ]
        context = Context(
            backend,
            stock,
            settings,
            arguments.seed,
            run,
            store,
            admitted,
            worker,
            PROVIDERS,
            (),
            (),
        )
        for item in prepared:
            previous = run.attempts(item.task.id)
            if any(isinstance(r, dict) and r.get("status") != "invalid" for r in previous):
                print(f"{item.task.id}: already has a result; skipped")
                continue
            record = run_attempt(context, item, harness)
            assert isinstance(record, dict)
            print(f"{item.task.id}: {record['status']} {record['failure_class'] or ''}".rstrip())
        print(f"run {run.finish()}")
    return 0


def _rejudge(run_dir: Path) -> int:
    """Recompute every judgment from stored evidence, without running anything (Section 11)."""
    configuration = jsondata.decode((run_dir / "run.json").read_bytes(), 1 << 24)
    if not isinstance(configuration, dict):
        raise HostError("run.json is malformed")
    seed, tasks = configuration["seed"], configuration["tasks"]
    if type(seed) is not int or not isinstance(tasks, list):
        raise HostError("run.json is malformed")
    records = load_records(run_dir)
    mismatches = 0
    checked = 0
    for pack in tasks:
        task = load_and_check(Path(str(pack)))
        with OracleProcess(task) as oracle:
            plan = oracle.plan(seed)
            for record in records:
                if isinstance(record, dict) and record.get("task") == task.id:
                    found, compared = _rejudge_record(oracle, plan, record)
                    mismatches += found
                    checked += compared
    print(f"rejudged {checked} judgments: {mismatches} mismatches")
    return 0 if mismatches == 0 else 1


def _rejudge_record(
    oracle: OracleProcess, plan: Plan, record: dict[str, JsonValue]
) -> tuple[int, int]:
    judged = record.get("judged")
    if not isinstance(judged, list):
        raise HostError("a stored record is malformed")
    mismatches = 0
    compared = 0
    for entry in judged:
        if not isinstance(entry, dict) or not isinstance(entry.get("judgment"), dict):
            continue
        check, case_index, stored = entry.get("check"), entry.get("case"), entry["judgment"]
        if not isinstance(check, str) or not isinstance(stored, dict):
            raise HostError("a stored judgment is malformed")
        try:
            evidence = evidence_from_json(entry.get("evidence"))
        except Rejected as error:
            raise HostError(f"stored evidence is malformed: {error.reason}") from None
        if case_index is None:
            context = plan.artifact_contexts[check]
        elif type(case_index) is int:
            context = plan.cases[check][case_index].context
        else:
            raise HostError("a stored case index is malformed")
        compared += 1
        if oracle.judge(check, context, evidence).passed != stored.get("passed"):
            mismatches += 1
            where = f"{record.get('task')} attempt {record.get('attempt')}"
            print(f"{where} {check} {case_index}: differs")
    return mismatches, compared


if __name__ == "__main__":
    sys.exit(main())
