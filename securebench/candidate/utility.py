"""Running the utility program in utility environments (architecture Section 8.3)."""

from pathlib import Path

from securebench.core import jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import Ending
from securebench.core.jsondata import JsonValue
from securebench.isolation.backend import (
    Environment,
    EnvironmentSpec,
    Mount,
    MountKind,
    Ran,
    Resources,
    read_only_bind,
)
from securebench.isolation.docker import DockerBackend

UTILITY_DIR = Path(__file__).resolve().parents[2] / "securebench_utility"
UTILITY_MOUNT = "/.securebench/utility"
TARGET_MOUNT = "/.securebench/target"
PYTHON_MOUNT = "/.securebench/python"
UTILITY_RESOURCES = Resources(2 << 30, 1_000_000_000, 64, 8 << 30)
UTILITY_TIMEOUT_SECONDS = 900
WALK_DEADLINE_SECONDS = 600
RECORD_OVERHEAD = 8192
_PROGRAM = ["-I", "-S", "-B", f"{UTILITY_MOUNT}/utility.py"]


def output_bound(max_entries: int, max_bytes: int) -> int:
    """What a correct utility can print for a walk within these bounds."""
    return max_bytes + (max_entries + 16) * RECORD_OVERHEAD


def run_on_snapshot(
    backend: DockerBackend, stock_image: str, target_image: str, request: JsonValue, bound: int
) -> bytes:
    """Run the utility in the stock image with `target_image` mounted read-only as data."""
    spec = EnvironmentSpec(
        stock_image,
        (
            Mount(MountKind.IMAGE, target_image, TARGET_MOUNT),
            read_only_bind(UTILITY_DIR, UTILITY_MOUNT),
        ),
        None,
        "/",
        "0",
        (),
        UTILITY_RESOURCES,
    )
    environment, ran = backend.run(
        spec, ["python3", *_PROGRAM], _request(request), UTILITY_TIMEOUT_SECONDS, bound
    )
    backend.destroy(environment)
    return _output(ran)


def run_replay(
    backend: DockerBackend, stock_image: str, baseline_image: str, request: bytes, bound: int
) -> tuple[Environment, bytes]:
    """Run the replay program inside a fresh container of the baseline image.

    The interpreter, its libraries and its dynamic loader all come from the
    stock image, mounted read-only; nothing from the baseline is executed.
    The caller snapshots and destroys the environment.
    """
    loader, library_path = _interpreter(backend, stock_image)
    spec = EnvironmentSpec(
        baseline_image,
        (
            Mount(MountKind.IMAGE, stock_image, PYTHON_MOUNT),
            read_only_bind(UTILITY_DIR, UTILITY_MOUNT),
        ),
        None,
        "/",
        "0",
        (),
        UTILITY_RESOURCES,
    )
    command = [
        PYTHON_MOUNT + loader,
        "--library-path",
        ":".join(PYTHON_MOUNT + part for part in library_path),
        f"{PYTHON_MOUNT}/usr/local/bin/python3",
        *_PROGRAM,
    ]
    environment, ran = backend.run(spec, command, request, UTILITY_TIMEOUT_SECONDS, bound)
    try:
        return environment, _output(ran)
    except BaseException:
        backend.destroy(environment)
        raise


_LOADERS: dict[str, tuple[str, tuple[str, ...]]] = {}


def _interpreter(backend: DockerBackend, stock_image: str) -> tuple[str, tuple[str, ...]]:
    """The stock image's dynamic loader and library directories, found once per image."""
    if stock_image in _LOADERS:
        return _LOADERS[stock_image]
    program = (
        "import glob, sysconfig\n"
        "loaders = sorted(glob.glob('/lib/ld-linux*.so.*') + glob.glob('/lib64/ld-linux*.so.*'))\n"
        "print(loaders[0] if loaders else '-')\n"
        "print(sysconfig.get_config_var('MULTIARCH'))\n"
    )
    spec = EnvironmentSpec(stock_image, (), None, "/", "0", (), UTILITY_RESOURCES)
    environment, ran = backend.run(spec, ["python3", "-I", "-S", "-c", program], b"", 60, 4096)
    backend.destroy(environment)
    lines = ran.stdout.decode("ascii", "replace").split()
    if ran.facts.ending is not Ending.RETURNED or len(lines) != 2 or not lines[0].startswith("/"):
        raise HostError(f"cannot locate the stock interpreter's loader: {ran.stdout[:200]!r}")
    loader, arch = lines
    found = (loader, ("/usr/local/lib", f"/lib/{arch}", f"/usr/lib/{arch}"))
    _LOADERS[stock_image] = found
    return found


def _request(request: JsonValue) -> bytes:
    return jsondata.encode(request)


def _output(ran: Ran) -> bytes:
    """A utility that hit a limit was driven there by candidate data; a crash is our bug."""
    if ran.facts.ending in (Ending.OUTPUT_EXCEEDED, Ending.TIMED_OUT, Ending.MEMORY_KILLED):
        raise Rejected(f"the utility environment ended with {ran.facts.ending.value}")
    if ran.facts.ending is not Ending.RETURNED or ran.facts.exit_status != 0:
        detail = ran.stderr.decode("utf-8", "replace")[-2000:]
        raise HostError(f"the utility program failed ({ran.facts}): {detail}")
    return ran.stdout
