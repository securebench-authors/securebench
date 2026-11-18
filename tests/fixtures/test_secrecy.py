"""G1 Mutual isolation, observed at the backend boundary during real attempts.

A recording backend wraps the real Docker backend and keeps every environment's
mounts and standard input. The tests then check what crossed into any
environment: never hidden resources, never a context, and for each case only
its own challenge.
"""

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from securebench.core import jsondata
from securebench.isolation.backend import Environment, EnvironmentSpec, Ran
from securebench.isolation.configuration import Configuration
from securebench.isolation.docker import DockerBackend
from securebench.oracle.process import OracleProcess
from securebench.taskspec.load import load
from tests.fixtures.conftest import FIXTURES, run_candidate

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class Call:
    spec: EnvironmentSpec
    command: tuple[str, ...]
    stdin: bytes


class RecordingBackend(DockerBackend):
    def __init__(self, disk_quota: bool) -> None:
        super().__init__(disk_quota)
        self.calls: list[Call] = []
        self.lock = threading.Lock()

    def run(
        self,
        spec: EnvironmentSpec,
        command: Sequence[str],
        stdin: bytes,
        timeout_seconds: float,
        output_bound: int,
        cancel: threading.Event | None = None,
    ) -> tuple[Environment, Ran]:
        with self.lock:
            self.calls.append(Call(spec, tuple(command), stdin))
        return super().run(spec, command, stdin, timeout_seconds, output_bound, cancel)


def test_hidden_material_and_contexts_never_enter_an_environment(
    configuration: Configuration, stock_image: str, tmp_path: Path
) -> None:
    pack = FIXTURES / "f3-generated-file" / "task"
    backend = RecordingBackend(configuration.disk_quota)
    outcome = run_candidate(
        backend,
        stock_image,
        pack,
        FIXTURES / "f3-generated-file" / "candidates" / "correct.sh",
        tmp_path / "run",
    )
    assert outcome.verdict == ("passed", None)
    task = load(pack)
    with OracleProcess(task) as oracle:
        plan = oracle.plan(1)
    hidden = str(task.hidden_dir)
    for call in backend.calls:
        for mount in call.spec.mounts:
            assert not mount.source.startswith(hidden), f"hidden lane mounted: {mount}"
        for case in plan.cases["sorting"]:
            context = jsondata.encode(case.context).strip()
            assert context not in call.stdin, "a context reached an environment"
    adapter_calls = [
        call for call in backend.calls if "/.securebench/evaluation/adapter.py" in call.command
    ]
    released = sorted(call.stdin for call in adapter_calls)
    expected = sorted(jsondata.encode(case.challenge) for case in plan.cases["sorting"])
    assert released == expected, "each case must receive exactly its own challenge"
    evaluation_dir = str(task.evaluation_dir)
    agent_calls = [
        call for call in backend.calls if any("/.securebench/harness" in p for p in call.command)
    ]
    assert len(agent_calls) == 1
    assert all(not m.source.startswith(evaluation_dir) for m in agent_calls[0].spec.mounts)
    assert agent_calls[0].stdin == (pack / "instructions.md").read_bytes()
