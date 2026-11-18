"""Shared machinery for the end-to-end fixture runs (docs/testing.md)."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from securebench.agent.harness import Harness, scripted
from securebench.candidate.store import Store
from securebench.core.jsondata import JsonValue
from securebench.core.limits import Limits, Settings
from securebench.isolation.docker import DockerBackend
from securebench.results.run import RunDirectory
from securebench.runner.attempt import Context, prepare, run_attempt

FIXTURES = Path(__file__).parents[2] / "fixtures"
SETTINGS = Settings(
    provider_hosted_tools=False,
    case_retries=2,
    limits=Limits(512 << 20, 1_000_000_000, 256, 2 << 30, 300),
)


@dataclass
class Outcome:
    record: dict[str, JsonValue]
    store: Store

    @property
    def verdict(self) -> tuple[JsonValue, JsonValue]:
        return self.record["status"], self.record["failure_class"]


def run_candidate(
    backend: DockerBackend,
    stock_image: str,
    pack: Path,
    script: Path,
    run_dir: Path,
    *,
    providers: dict[str, dict[str, JsonValue]] | None = None,
    extra_hosts: tuple[tuple[str, str], ...] = (),
    extra_networks: tuple[str, ...] = (),
    settings: Settings = SETTINGS,
    harness: Harness | None = None,
) -> Outcome:
    """One attempt through the real runner, as `securebench run` makes it.

    The harness is the scripted `script` unless `harness` is given.
    """
    providers = providers or {}
    configuration: JsonValue = {"pack": str(pack), "script": str(script)}
    with RunDirectory(run_dir, configuration) as run:
        store = Store(run.store_root)
        prepared = prepare(backend, stock_image, store, pack, 1)
        context = Context(
            backend,
            stock_image,
            settings,
            1,
            run,
            store,
            False,
            {"test": True},
            providers,
            extra_hosts,
            extra_networks,
        )
        chosen = harness or scripted(script, tuple(providers))
        record = run_attempt(context, prepared, chosen)
    assert isinstance(record, dict)
    return Outcome(record, store)


@pytest.fixture(scope="session")
def f2_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """F2's pack with the image ID of its freshly built baseline."""
    built = subprocess.run(
        [
            "docker",
            "build",
            "--quiet",
            "--label",
            "securebench.fixture=f2",
            str(FIXTURES / "f2-repository-build" / "baseline"),
        ],
        capture_output=True,
        check=True,
        timeout=1800,
    )
    image = built.stdout.decode().strip()
    pack = tmp_path_factory.mktemp("f2") / "task"
    shutil.copytree(FIXTURES / "f2-repository-build" / "task", pack)
    toml = pack / "task.toml"
    placeholder = 'image = "sha256:' + "0" * 64 + '"'
    toml.write_text(toml.read_text().replace(placeholder, f'image = "{image}"'))
    return pack
