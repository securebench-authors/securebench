"""Differential test of the adapter's index against pypiserver 2.3.2, the server upstream's reference runs.

For each set of distribution files below, it runs upstream's command,
`python -m pip install --index-url http://localhost:<port>/simple vectorops==0.1.0`,
in a fresh virtual environment against three servers of the same directory:

- `pypiserver`: pypiserver 2.3.2 as the reference starts it, which redirects
  requests for projects it does not hold to pypi.org;
- `no-fallback`: the same with --disable-fallback;
- `adapter`: the adapter's own discovery and index (evaluation/adapter.py).

It prints whether pip succeeded and which version it installed. Run it with
network access (pypiserver, and the fallback, need pypi.org):

    docker run --rm --memory 2g -v <pack>:/pack:ro \
      alexgshaw/pypi-server@sha256:d18bb30f47c7dcaa3acdbc31ac7413c98eadca2ea16540bbd380f2f063b95276 \
      python3 -B -I /pack/hidden/differential_index.py
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import time

WORK = "/tmp/differential"
PYTHON = "/usr/local/bin/python3"


def sh(*command: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def build(version: str, requires: tuple[str, ...] = (), formats: str = "gztar") -> str:
    """Build a sdist and a wheel of a working vectorops; return the dist directory."""
    source = f"{WORK}/src/{version}-{formats}-{len(requires)}"
    os.makedirs(f"{source}/vectorops", exist_ok=True)
    with open(f"{source}/vectorops/__init__.py", "w") as file:
        file.write("def dotproduct(a, b):\n    return sum(x * y for x, y in zip(a, b))\n")
    with open(f"{source}/setup.py", "w") as file:
        file.write(
            "from setuptools import setup\n"
            f"setup(name='vectorops', version={version!r}, packages=['vectorops'], install_requires={list(requires)!r})\n"
        )
    built = sh(PYTHON, "setup.py", "-q", "sdist", f"--formats={formats}", "bdist_wheel", cwd=source)
    assert built.returncode == 0, built.stderr
    return f"{source}/dist"


def files(directory: str, *suffixes: str) -> list[str]:
    return sorted(
        f"{directory}/{name}" for name in os.listdir(directory) if name.endswith(suffixes)
    )


def scenarios() -> dict[str, list[tuple[str, str]]]:
    """Scenario name -> list of (source file, name to serve it under)."""
    v010 = build("0.1.0")
    v011 = build("0.1.1")
    v01 = build("0.1")
    zipped = build("0.1.0", formats="zip")
    dependent = build("0.1.0", requires=("six",))
    wheel, sdist = files(v010, ".whl")[0], files(v010, ".tar.gz")[0]

    def same(*paths: str) -> list[tuple[str, str]]:
        return [(path, os.path.basename(path)) for path in paths]

    return {
        "wheel and sdist (reference)": same(wheel, sdist),
        "wheel only": same(wheel),
        "sdist only": same(sdist),
        "zip sdist only": same(*files(zipped, ".zip")),
        "0.1.1 wheel and 0.1.0 sdist": same(files(v011, ".whl")[0], sdist),
        "0.1.0 and 0.1.1 wheels": same(wheel, files(v011, ".whl")[0]),
        "version 0.1 wheel": same(*files(v01, ".whl")),
        "capitalised file names": [
            (wheel, os.path.basename(wheel).replace("vectorops", "VectorOps")),
            (sdist, os.path.basename(sdist).replace("vectorops", "VectorOps")),
        ],
        "wheel depending on six": same(*files(dependent, ".whl")),
        "0.1.1 wheel only": same(files(v011, ".whl")[0]),
    }


def install(port: int) -> str:
    environment = f"{WORK}/env-{port}-{time.monotonic_ns()}"
    sh(PYTHON, "-m", "venv", environment)
    ran = sh(
        f"{environment}/bin/python",
        "-m",
        "pip",
        "install",
        "--index-url",
        f"http://localhost:{port}/simple",
        "vectorops==0.1.0",
    )
    if ran.returncode != 0:
        return "fails"
    shown = sh(f"{environment}/bin/python", "-m", "pip", "show", "vectorops").stdout
    version = next(
        (line.split(": ", 1)[1] for line in shown.splitlines() if line.startswith("Version: ")), "?"
    )
    return f"installs {version}"


def pypiserver(directory: str, port: int, fallback: bool) -> subprocess.Popen[bytes]:
    command = [f"{WORK}/server/bin/pypi-server", "run", "-p", str(port), directory]
    if not fallback:
        command.insert(2, "--disable-fallback")
    server = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    return server


def main() -> None:
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    sh(PYTHON, "-m", "venv", f"{WORK}/server")
    installed = sh(
        f"{WORK}/server/bin/pip", "install", "-q", "pypiserver==2.3.2", "packaging==25.0"
    )
    assert installed.returncode == 0, installed.stderr
    spec = importlib.util.spec_from_file_location("adapter", "/pack/evaluation/adapter.py")
    assert spec is not None and spec.loader is not None
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    port = 9000
    for title, served in scenarios().items():
        directory = f"{WORK}/served/{port}"
        os.makedirs(directory)
        for source, name in served:
            shutil.copy(source, f"{directory}/{name}")
        outcomes = {}
        for label, fallback in (("pypiserver", True), ("no-fallback", False)):
            port += 1
            server = pypiserver(directory, port, fallback)
            outcomes[label] = install(port)
            server.kill()
            server.wait()
        port += 1
        adapter.ROOTS = (directory,)
        adapter.PORT = port
        index = adapter.serve(adapter.find_distributions())
        outcomes["adapter"] = install(port)
        index.shutdown()
        names = ", ".join(name for _, name in served)
        print(
            f"{title} [{names}]: "
            + "; ".join(f"{label} {outcome}" for label, outcome in outcomes.items())
        )
        sys.stdout.flush()


main()
