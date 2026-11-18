"""Evaluation of one captured candidate: artifact checks, then protocol cases."""

import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

from securebench.candidate import capture as capture_module
from securebench.candidate import lookup, replay
from securebench.candidate.state import BaselineIndex
from securebench.candidate.store import Store
from securebench.candidate.utility import PYTHON_MOUNT
from securebench.core import jsondata
from securebench.core.candidate import Manifest
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import (
    CaseEvidence,
    Ending,
    Evidence,
    FileRead,
    Judgment,
    Malformed,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue
from securebench.core.task import EVALUATION_MOUNT, ProtocolCheck, Task
from securebench.core.verdict import AttemptFailed, FailureClass, Status, Verdict
from securebench.evidence import binding
from securebench.isolation.backend import (
    Cancelled,
    EnvironmentSpec,
    Mount,
    MountKind,
    Resources,
    Snapshot,
    read_only_bind,
)
from securebench.isolation.docker import DockerBackend
from securebench.oracle.process import OracleProcess

MAX_PARALLEL_CASES = 4
SETUP_OUTPUT_BOUND = 1 << 16


@dataclass(frozen=True)
class Judged:
    """One judged check (`case_index` is `None`) or case, with its evidence."""

    check_id: str
    case_index: int | None
    evidence: Evidence
    judgment: Judgment | None


@dataclass(frozen=True)
class Evaluation:
    verdict: Verdict
    judged: tuple[Judged, ...]
    host_errors: tuple[JsonValue, ...]


def evaluate(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    index: BaselineIndex,
    manifest: Manifest,
    store: Store,
    oracle: OracleProcess,
    plan: Plan,
    resources: Resources,
    case_retries: int,
) -> Evaluation:
    """Evaluate a candidate and return its verdict (architecture Sections 6.2 and 10).

    Raises `AttemptFailed` for capture and setup failures that end the
    attempt, and `HostError` for host failures outside a case.
    """
    judged: list[Judged] = []
    view = lookup.FinalView(task.scope, index, manifest, store)
    for check in task.artifact_checks:
        files = {
            spec.path: lookup.read_file(view, spec.path, spec.max_bytes) for spec in check.files
        }
        listings = {
            spec.path: lookup.list_directory(view, spec.path, spec.max_entries)
            for spec in check.listings
        }
        evidence = binding.artifact_evidence(check, files, listings)
        judgment = oracle.judge(check.id, plan.artifact_contexts[check.id], evidence)
        judged.append(Judged(check.id, None, evidence, judgment))
        if not judgment.passed:
            return _failed(FailureClass.ORACLE, judged, check.id, judgment.diagnostic)
    if not task.protocol_checks:
        return Evaluation(Verdict(Status.PASSED, None, ()), tuple(judged), ())
    candidate = replay.replay(backend, stock_image, task, index, manifest, store)
    snapshots: list[Snapshot] = [candidate]
    try:
        starts = {
            check.id: _setup(backend, stock_image, task, check, candidate, resources, snapshots)
            for check in task.protocol_checks
        }
        runner = _Cases(backend, stock_image, task, oracle, plan, resources, case_retries, starts)
        return runner.run(judged)
    finally:
        for snapshot in reversed(snapshots):
            backend.destroy_snapshot(snapshot)


def _mounts(stock_image: str, task: Task) -> tuple[Mount, ...]:
    """The stock interpreter, so adapters run in baselines without Python."""
    interpreter = Mount(MountKind.IMAGE, stock_image, PYTHON_MOUNT)
    if task.evaluation_dir.is_dir():
        return (interpreter, read_only_bind(task.evaluation_dir, EVALUATION_MOUNT))
    return (interpreter,)


def _spec(stock_image: str, task: Task, image: str, resources: Resources) -> EnvironmentSpec:
    mounts = _mounts(stock_image, task)
    return EnvironmentSpec(image, mounts, None, task.public.workdir, None, (), resources)


def _setup(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    check: ProtocolCheck,
    candidate: Snapshot,
    resources: Resources,
    snapshots: list[Snapshot],
) -> str:
    """Run the check's shared setup once and snapshot it (architecture Section 6.2 rule 4)."""
    if check.setup_command is None or check.setup_timeout_seconds is None:
        return candidate.image
    spec = _spec(stock_image, task, candidate.image, resources)
    environment, ran = backend.run(
        spec, check.setup_command, b"", check.setup_timeout_seconds, SETUP_OUTPUT_BOUND
    )
    try:
        if ran.facts.ending is not Ending.RETURNED or ran.facts.exit_status != 0:
            raise AttemptFailed(
                FailureClass.SETUP,
                f"setup for check {check.id} ended with {ran.facts.ending.value}"
                f" (status {ran.facts.exit_status})",
            )
        snapshot = backend.snapshot(environment)
    finally:
        backend.destroy(environment)
    snapshots.append(snapshot)
    return snapshot.image


@dataclass(frozen=True)
class _Result:
    judged: Judged | None
    failure: FailureClass | None
    diagnostic: JsonValue
    host_errors: tuple[str, ...]
    invalid: bool


class _Cases:
    """All cases of all protocol checks, in parallel; the first failure cancels the rest."""

    def __init__(
        self,
        backend: DockerBackend,
        stock_image: str,
        task: Task,
        oracle: OracleProcess,
        plan: Plan,
        resources: Resources,
        retries: int,
        starts: dict[str, str],
    ) -> None:
        self.backend = backend
        self.stock_image = stock_image
        self.task = task
        self.oracle = oracle
        self.oracle_lock = threading.Lock()
        self.plan = plan
        self.resources = resources
        self.retries = retries
        self.starts = starts
        self.cancel = threading.Event()

    def run(self, judged: list[Judged]) -> Evaluation:
        work = [
            (check, index)
            for check in self.task.protocol_checks
            for index in range(len(self.plan.cases[check.id]))
        ]
        results: list[_Result] = []
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CASES, len(work))) as pool:
            pending: set[Future[_Result | None]] = {
                pool.submit(self._case_with_retries, check, index) for check, index in work
            }
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    if result is None:
                        continue
                    results.append(result)
                    if result.failure is not None or result.invalid:
                        self.cancel.set()
        judged.extend(result.judged for result in results if result.judged is not None)
        host_errors: tuple[JsonValue, ...] = tuple(
            error for result in results for error in result.host_errors
        )
        failures = [result for result in results if result.failure is not None]
        if failures:
            first = failures[0]
            diagnostics: tuple[JsonValue, ...] = tuple(_diagnostic(result) for result in failures)
            return Evaluation(
                Verdict(Status.FAILED, first.failure, diagnostics), tuple(judged), host_errors
            )
        if any(result.invalid for result in results):
            return Evaluation(
                Verdict(Status.INVALID, None, host_errors), tuple(judged), host_errors
            )
        return Evaluation(Verdict(Status.PASSED, None, ()), tuple(judged), host_errors)

    def _case_with_retries(self, check: ProtocolCheck, index: int) -> _Result | None:
        """Repeat a case exactly after a host error, up to the configured count (Section 10)."""
        errors: list[str] = []
        for _ in range(self.retries + 1):
            if self.cancel.is_set():
                return None
            try:
                return self._case(check, index, tuple(errors))
            except Cancelled:
                return None
            except HostError as error:
                errors.append(f"check {check.id} case {index}: {error.reason}")
        return _Result(None, None, None, tuple(errors), True)

    def _case(self, check: ProtocolCheck, index: int, errors: tuple[str, ...]) -> _Result:
        case = self.plan.cases[check.id][index]
        spec = _spec(self.stock_image, self.task, self.starts[check.id], self.resources)
        challenge = jsondata.encode(case.challenge)
        environment, ran = self.backend.run(
            spec,
            check.command,
            challenge,
            check.timeout_seconds,
            check.max_observation_bytes,
            self.cancel,
        )
        try:
            returned = ran.facts.ending is Ending.RETURNED and ran.facts.exit_status == 0
            response = ran.stdout if returned else None
            artifacts: dict[str, FileRead] = {}
            failure: str | None = None
            outcome = binding.parse_response(response, check) if response is not None else None
            if isinstance(outcome, Observed) and check.output_artifacts:
                snapshot = self.backend.snapshot(environment)
                try:
                    files = tuple((spec.path, spec.max_bytes) for spec in check.output_artifacts)
                    artifacts = capture_module.collect(
                        self.backend, self.stock_image, files, snapshot
                    )
                except Rejected as error:
                    failure = error.reason
                finally:
                    self.backend.destroy_snapshot(snapshot)
        finally:
            self.backend.destroy(environment)
        evidence = binding.case_evidence(
            check, index, case.challenge, ran.facts, response, artifacts, failure
        )
        if not isinstance(evidence.outcome, Observed):
            reason = _outcome_reason(evidence)
            return _Result(
                Judged(check.id, index, evidence, None),
                FailureClass.CASE_ERROR,
                reason,
                errors,
                False,
            )
        with self.oracle_lock:
            judgment = self.oracle.judge(check.id, case.context, evidence)
        verdict = None if judgment.passed else FailureClass.ORACLE
        return _Result(
            Judged(check.id, index, evidence, judgment), verdict, judgment.diagnostic, errors, False
        )


def _outcome_reason(evidence: CaseEvidence) -> JsonValue:
    outcome = evidence.outcome
    if isinstance(outcome, Malformed):
        return {"malformed": outcome.reason}
    assert not isinstance(outcome, Observed)
    return {"unable": {"code": outcome.code, "message": outcome.message}}


def _diagnostic(result: _Result) -> JsonValue:
    judged = result.judged
    return {
        "case": judged.case_index if judged else None,
        "check": judged.check_id if judged else None,
        "diagnostic": result.diagnostic,
        "failure_class": result.failure.value if result.failure else None,
    }


def _failed(
    failure: FailureClass,
    judged: list[Judged],
    check_id: str,
    diagnostic: JsonValue,
) -> Evaluation:
    detail: JsonValue = {
        "case": None,
        "check": check_id,
        "diagnostic": diagnostic,
        "failure_class": failure.value,
    }
    return Evaluation(Verdict(Status.FAILED, failure, (detail,)), tuple(judged), ())
