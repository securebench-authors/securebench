"""Evaluation of a captured candidate against the real Docker backend (fixture F3)."""

import shutil
from pathlib import Path

import pytest

from securebench.candidate import capture, index
from securebench.candidate.store import Store
from securebench.core.task import Task
from securebench.core.verdict import FailureClass, Status
from securebench.evaluation.plan import validate_plan
from securebench.evaluation.run import Evaluation, evaluate
from securebench.isolation.backend import EnvironmentSpec, Resources
from securebench.isolation.docker import DockerBackend
from securebench.oracle.process import OracleProcess
from securebench.taskspec.load import load

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parents[2] / "fixtures"
RESOURCES = Resources(512 << 20, 1_000_000_000, 128, 1 << 30)


def _evaluate(
    backend: DockerBackend, stock_image: str, task: Task, script: str, tmp_path: Path
) -> Evaluation:
    store = Store(tmp_path / "store")
    baseline = backend.resolve_image(task.public.baseline.image)
    baseline_index = index.build_index(backend, stock_image, task, baseline, store)
    spec = EnvironmentSpec(baseline, (), None, task.public.workdir, None, (), RESOURCES)
    environment, ran = backend.run(spec, ["sh", "-c", script], b"", 60, 1 << 16)
    assert ran.facts.exit_status == 0, ran.stderr
    try:
        agent = backend.snapshot(environment)
    finally:
        backend.destroy(environment)
    try:
        manifest = capture.capture(backend, stock_image, task, baseline_index, agent, store)
    finally:
        backend.destroy_snapshot(agent)
    with OracleProcess(task) as oracle:
        plan = oracle.plan(1)
        validate_plan(task, plan)
        return evaluate(
            backend, stock_image, task, baseline_index, manifest, store, oracle, plan, RESOURCES, 2
        )


def test_missing_program_is_a_case_error(
    backend: DockerBackend, stock_image: str, tmp_path: Path
) -> None:
    task = load(FIXTURES / "f3-generated-file" / "task")
    result = _evaluate(backend, stock_image, task, "true", tmp_path)
    assert result.verdict.status is Status.FAILED
    assert result.verdict.failure_class is FailureClass.CASE_ERROR


STOCK_PYTHON = (
    '"/.securebench/python/lib64/ld-linux-x86-64.so.2", "--library-path", '
    '"/.securebench/python/usr/local/lib:/.securebench/python/lib/x86_64-linux-gnu'
    ':/.securebench/python/usr/lib/x86_64-linux-gnu", '
    '"/.securebench/python/usr/local/bin/python3"'
)


def test_adapter_runs_on_the_mounted_stock_interpreter(
    backend: DockerBackend, stock_image: str, tmp_path: Path
) -> None:
    pack = tmp_path / "pack"
    shutil.copytree(FIXTURES / "f3-generated-file" / "task", pack)
    spec = pack / "task.toml"
    baseline_python = '"/usr/local/bin/python3"'
    assert spec.read_text().count(baseline_python) == 1
    spec.write_text(spec.read_text().replace(baseline_python, STOCK_PYTHON))
    script = (FIXTURES / "f3-generated-file" / "candidates" / "correct.sh").read_text()
    result = _evaluate(backend, stock_image, load(pack), script, tmp_path)
    assert result.verdict.status is Status.PASSED, result.verdict
