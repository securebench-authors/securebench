"""Conversion campaign tooling (docs/conversion.md).

This runs outside SecureBench's trusted path. It drives the `securebench` and
`pier` command-line tools on scripted candidates and compares their verdicts,
so that every converted task carries a cross-grade record anyone can recompute.

    python conversions/campaign.py fetch
    python conversions/campaign.py order <source>
    python conversions/campaign.py qualify conversions/<source>/<task>
    python conversions/campaign.py seed-native-cache
    python conversions/campaign.py committed [conversions/<source>/<task> ...]
"""

import argparse
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import IO, Any

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "upstream"
WORKER = HERE.parent / "qualification.json"
WORK_ROOT = "/var/tmp"
# The work directory is deleted when qualify ends; an invalid run's record is
# kept here so its host error can be diagnosed.
INVALID_ROOT = Path(WORK_ROOT) / "securebench-invalid"
# Candidate runs share the worker; each unit may use up to the upstream task's memory.
PARALLEL_MEMORY_MIB = 16384
MAX_WORKERS = 4
# Two qualifications at once exceeded the worker's memory and the OOM killer took
# down the coordinating session, so they queue on this lock.
QUALIFY_LOCK = Path(WORK_ROOT) / "securebench-qualify.lock"
# A native result depends only on the upstream task, the candidate and Pier, never
# on the pack, so a qualification after a pack change reuses it.
NATIVE_CACHE = Path(WORK_ROOT) / "securebench-native-cache"
# Packs are committed to a repository host that warns on files above 50 MiB and
# refuses files above 100 MiB.
MAX_PACK_BYTES = 50 * 1024 * 1024
# Each candidate adds runs to every qualification, which agents wait through.
CANDIDATE_LIMITS = {"mutant": 5, "attack": 3}


def load_sources() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    with (HERE / "sources.toml").open("rb") as file:
        config = tomllib.load(file)
    return config, {source["name"]: source for source in config["source"]}


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def fetch() -> None:
    """Clone every source at its pinned commit, or confirm an existing clone is at it."""
    _, sources = load_sources()
    for name, source in sources.items():
        clone = UPSTREAM / name
        if not clone.exists():
            git(
                "clone",
                "--quiet",
                "--filter=blob:none",
                "--no-checkout",
                source["repository"],
                str(clone),
            )
        git("-C", str(clone), "checkout", "--quiet", source["commit"])
        if git("-C", str(clone), "status", "--porcelain"):
            raise SystemExit(f"{clone} has local changes")
        print(f"{name}: {source['commit']}")


def tasks_dir(source: dict[str, Any]) -> Path:
    clone = UPSTREAM / source["name"]
    if git("-C", str(clone), "rev-parse", "HEAD") != source["commit"]:
        raise SystemExit(f"{clone} is not at the pinned commit; run fetch")
    return clone / source["tasks"]


def order(name: str) -> list[str]:
    """Every task of a source, sorted by SHA-256 of `<seed>:<task>`."""
    config, sources = load_sources()
    root = tasks_dir(sources[name])
    tasks = [entry.name for entry in root.iterdir() if (entry / "task.toml").is_file()]
    return sorted(
        tasks, key=lambda task: hashlib.sha256(f"{config['seed']}:{task}".encode()).hexdigest()
    )


def _environment(upstream: Path) -> dict[str, Any]:
    with (upstream / "task.toml").open("rb") as file:
        return tomllib.load(file)["environment"]


def parallel_units(upstream: Path) -> int:
    """How many candidate runs go at once: as many as fit the memory budget, at most four."""
    return max(1, min(MAX_WORKERS, PARALLEL_MEMORY_MIB // int(_environment(upstream)["memory_mb"])))


def upstream_limits(upstream: Path) -> list[str]:
    """The upstream task's own resource limits, so that both graders give the candidate the same."""
    environment = _environment(upstream)
    return [
        "--cpus",
        str(environment["cpus"]),
        "--memory-mib",
        str(environment["memory_mb"]),
        "--disk-mib",
        str(environment["storage_mb"]),
    ]


def grade_securebench(
    pack: Path, script: Path, limits: list[str], work: Path, seed: int | None = None
) -> dict[str, Any]:
    """SecureBench on a scripted candidate, with `seed` when given."""
    run_dir = work / "securebench"
    subprocess.run(
        [
            "uv",
            "run",
            "securebench",
            "run",
            str(pack),
            "--run-dir",
            str(run_dir),
            "--harness",
            f"scripted:{script}",
            "--qualification",
            str(WORKER),
            *limits,
            *(["--seed", str(seed)] if seed is not None else []),
        ],
        check=False,
        cwd=HERE.parent,
    )
    records = sorted((run_dir / "attempts").glob("*/*.json"))
    if len(records) != 1:
        return {"status": "no record", "failure_class": None, "rejudged": False}
    record = json.loads(records[0].read_bytes())
    kept: dict[str, Any] = {}
    if record["status"] == "invalid":
        keep = INVALID_ROOT / pack.parent.name / work.name
        shutil.copytree(records[0].parent, keep, dirs_exist_ok=True)
        reasons = [*record["host_errors"], *record["diagnostics"]]
        kept = {"host_error": json.dumps(reasons)[:500], "kept": str(keep)}
    rejudge = subprocess.run(
        ["uv", "run", "securebench", "rejudge", str(run_dir)],
        check=False,
        cwd=HERE.parent,
        capture_output=True,
        text=True,
    )
    return {
        "admitted": record["admitted"],
        "status": record["status"],
        "failure_class": record["failure_class"],
        "pack_digest": record["provenance"]["task"]["pack"],
        "framework": record["provenance"]["framework"],
        "qualification": record["provenance"]["worker"]["qualification"],
        "rejudged": rejudge.returncode == 0,
        **kept,
    }


def grade_native(upstream: Path, candidates: Path, script: Path, work: Path) -> float | str:
    """Pier's oracle agent with the candidate standing in as `solution/solve.sh`."""
    task = work / "native-task" / upstream.name
    shutil.copytree(upstream, task)
    shutil.rmtree(task / "solution", ignore_errors=True)
    shutil.copytree(candidates, task / "solution")
    shutil.copy2(script, task / "solution" / "solve.sh")
    jobs = work / "native"
    subprocess.run(
        [
            "pier",
            "run",
            "-p",
            str(task),
            "--agent",
            "oracle",
            "-o",
            str(jobs),
            "-n",
            "1",
            "-q",
            "--job-name",
            "job",
            # The default --delete also removes the pulled baseline image, which
            # concurrent SecureBench runs on this daemon may be about to use.
            "--no-delete",
        ],
        check=False,
    )
    trials = [path for path in (jobs / "job").glob("*/result.json")]
    if len(trials) != 1:
        return "no result"
    result = json.loads(trials[0].read_bytes())
    if result.get("exception_info") is not None:
        return f"error: {result['exception_info'].get('exception_type')}"
    return float(result["verifier_result"]["rewards"]["reward"])


def _tree_digest(root: Path, leave_out: frozenset[str] = frozenset()) -> str:
    """SHA-256 over every path, type, executable bit and content below `root`, minus `leave_out`."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in leave_out:
            continue
        if path.is_symlink():
            entry = f"link {relative} {path.readlink()}".encode()
        elif path.is_dir():
            entry = f"dir {relative}".encode()
        else:
            executable = path.stat().st_mode & 0o111 != 0
            content = hashlib.sha256(path.read_bytes()).hexdigest()
            entry = f"file {relative} {executable} {content}".encode()
        digest.update(hashlib.sha256(entry).digest())
    return digest.hexdigest()


def _native_key(upstream_digest: str, pier: str, candidates: Path, script: Path) -> dict[str, str]:
    """What a candidate's native result depends on.

    That is the upstream task, Pier, the script, the candidate scripts it runs (a mutant
    often runs `reference.sh` and then edits), and every other file beside them. Other
    candidates are left out, so deleting or editing one keeps the rest cached.
    """
    scripts = {path.name: path.read_text(errors="replace") for path in candidates.glob("*.sh")}
    used = {script.name}
    pending = [script.name]
    while pending:
        text = scripts[pending.pop()]
        for name in scripts:
            if name not in used and name in text:
                used.add(name)
                pending.append(name)
    return {
        "upstream": upstream_digest,
        "pier": pier,
        "script": script.name,
        "candidates": _tree_digest(candidates, frozenset(scripts) - used),
    }


def _cache_path(key: dict[str, str]) -> Path:
    return (
        NATIVE_CACHE
        / f"{hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()}.json"
    )


def _store_native(key: dict[str, str], native: float) -> None:
    NATIVE_CACHE.mkdir(exist_ok=True)
    cached = _cache_path(key)
    partial = cached.with_suffix(".partial")
    partial.write_text(json.dumps({"key": key, "native": native}) + "\n")
    partial.replace(cached)


def _cached_native(
    key: dict[str, str], upstream: Path, candidates: Path, script: Path, work: Path
) -> tuple[float | str, bool]:
    """The native result and whether it came from the cache; only rewards are cached."""
    cached = _cache_path(key)
    if cached.exists():
        return float(json.loads(cached.read_bytes())["native"]), True
    native = grade_native(upstream, candidates, script, work)
    # Errors and timeouts can depend on load, so they are run again next time.
    if isinstance(native, float):
        _store_native(key, native)
    return native, False


def seed_native_cache() -> None:
    """Cache the native rewards of qualification records whose candidates have not changed since."""
    pins, sources = load_sources()
    stored = skipped = 0
    for record_path in sorted(HERE.glob("*/*/qualification.json")):
        record = json.loads(record_path.read_bytes())
        candidates = record_path.parent / "candidates"
        source = sources.get(record["source"])
        recorded_at = git(
            "-C", str(HERE.parent), "log", "-1", "--format=%H", "--", str(record_path)
        )
        changed = recorded_at == "" or (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(HERE.parent),
                    "diff",
                    "--quiet",
                    recorded_at,
                    "--",
                    str(candidates),
                ],
                check=False,
            ).returncode
            != 0
        )
        changed = (
            changed
            or git("-C", str(HERE.parent), "status", "--porcelain", "--", str(candidates)) != ""
        )
        if (
            source is None
            or changed
            or record.get("pier") != pins["pier"]
            or record.get("upstream_commit") != source["commit"]
        ):
            skipped += len(record["candidates"])
            continue
        upstream_digest = _tree_digest(tasks_dir(source) / record["task"])
        for name, run in record["candidates"].items():
            script = candidates / f"{name}.sh"
            if isinstance(run["native"], float) and script.exists():
                key = _native_key(upstream_digest, pins["pier"], candidates, script)
                _store_native(key, run["native"])
                stored += 1
            else:
                skipped += 1
    print(f"stored {stored} native results, skipped {skipped}")


def _known(name: str) -> bool:
    prefix, _, rest = name.partition("-")
    return name in ("reference", "null") or (prefix in ("mutant", "attack") and rest != "")


PACKAGES = ("securebench", "securebench_utility", "securebench_relay_proxy")


def _code(commit: str) -> str:
    """The SecureBench code at a commit; commits that change only documents share it."""
    return git("-C", str(HERE.parent), "rev-parse", *(f"{commit}:{name}" for name in PACKAGES))


def _consistency(runs: list[dict[str, Any]]) -> list[str]:
    """All runs of one qualification share clean SecureBench code, worker record and pack."""
    problems: list[str] = []
    codes = {_code(run["framework"]["commit"]) for run in runs}
    if len(codes) > 1:
        problems.append(f"the runs used {len(codes)} different versions of the SecureBench code")
    for key in ("qualification", "pack_digest"):
        values = {json.dumps(run.get(key), sort_keys=True) for run in runs}
        if len(values) > 1:
            problems.append(f"the runs have {len(values)} different values of {key}")
    if any(run.get("framework", {}).get("dirty") for run in runs):
        problems.append("a run was made from a tree with uncommitted changes")
    return problems


# Under a loaded worker a slow failing candidate can hit Pier's agent time limit,
# so a native timeout is a native fail, as it is for the native benchmark.
NATIVE_TIMEOUT = "error: AgentTimeoutError"


def _native_passed(native: Any) -> bool | None:
    """The native verdict, or None for a result that is neither a pass nor a fail."""
    if native == 1.0:
        return True
    if native == 0.0 or native == NATIVE_TIMEOUT:
        return False
    return None


def _problems(name: str, run: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if "kept" in run["securebench"]:
        problems.append(
            f"{name}: invalid: {run['securebench']['host_error']} "
            f"(record kept in {run['securebench']['kept']})"
        )
    status, native = run["securebench"]["status"], run["native"]
    if not run["securebench"].get("admitted"):
        problems.append(f"{name}: the SecureBench run was not admitted")
    if not run["securebench"].get("rejudged"):
        problems.append(f"{name}: rejudge did not reproduce the verdict")
    if name == "reference" and (status != "passed" or native != 1.0):
        problems.append(f"{name}: must pass both graders")
    elif name == "null" and (status != "failed" or native != 0.0):
        problems.append(f"{name}: must fail both graders")
    elif name.startswith("mutant-"):
        native_passed = _native_passed(native)
        if native_passed is None:
            problems.append(f"{name}: native result {native!r} is neither a pass nor a fail")
        elif status != ("passed" if native_passed else "failed"):
            problems.append(f"{name}: SecureBench says {status}, native says {native!r}")
    elif name.startswith("attack-") and status != "failed":
        problems.append(f"{name}: SecureBench must say failed, not {status}")
    return problems


def wait_for_the_worker(lock: IO[str]) -> None:
    """Take the worker's qualification lock, released when `lock` closes or the process dies."""
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("waiting for another qualification on this worker to finish", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)


def qualify(conversion: Path) -> int:
    conversion = conversion.resolve()
    source_name, task = conversion.parent.name, conversion.name
    _, sources = load_sources()
    upstream = tasks_dir(sources[source_name]) / task
    candidates = conversion / "candidates"
    scripts = sorted(candidates.glob("*.sh"))
    names = [script.stem for script in scripts]
    problems = [f"{name}: unknown candidate kind" for name in names if not _known(name)]
    problems += [f"missing {name}.sh" for name in ("reference", "null") if name not in names]
    if not any(name.startswith("mutant-") for name in names):
        problems.append("no mutant candidate")
    for kind, limit in CANDIDATE_LIMITS.items():
        count = sum(name.startswith(f"{kind}-") for name in names)
        if count > limit:
            problems.append(f"{count} {kind} candidates, above the limit of {limit}")
    # The pack digest covers every file; one git ignores (a __pycache__) would
    # not be committed, and the record could not be reproduced from the repository.
    ignored = git(
        "-C",
        str(HERE.parent),
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        str(conversion / "task"),
    )
    problems += [
        f"{path}: ignored by git, so not part of the committed pack" for path in ignored.split()
    ]
    # Git cannot store an empty directory, but the pack digest counts it.
    problems += [
        f"{path}: an empty directory, which git cannot commit, so not part of the committed pack"
        for path in sorted((conversion / "task").rglob("*"))
        if path.is_dir() and not any(path.iterdir())
    ]
    size = sum(path.stat().st_size for path in (conversion / "task").rglob("*") if path.is_file())
    if size > MAX_PACK_BYTES:
        problems.append(f"the pack is {size / 2**20:.1f} MiB, above the 50 MiB limit (pack-size)")
    limits = upstream_limits(upstream)
    matrix: dict[str, Any] = {}
    runs: list[dict[str, Any]] = []
    workers = parallel_units(upstream)
    upstream_digest = _tree_digest(upstream)
    pier = load_sources()[0]["pier"]
    # On disk, not in /tmp: on the worker /tmp is a small in-memory filesystem that
    # concurrent qualifications filled up.
    with (
        QUALIFY_LOCK.open("a") as lock,
        tempfile.TemporaryDirectory(prefix=f"qualify-{task}-", dir=WORK_ROOT) as directory,
    ):
        wait_for_the_worker(lock)

        def unit(script: Path) -> dict[str, Any]:
            """One candidate through both graders; units share nothing."""
            work = Path(directory) / script.stem
            work.mkdir()
            key = _native_key(upstream_digest, pier, candidates, script)
            native, cached = _cached_native(key, upstream, candidates, script, work)
            return {
                "securebench": grade_securebench(conversion / "task", script, limits, work),
                "native": native,
                "native_cached": cached,
            }

        def run(group: list[Path]) -> list[str]:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {script: pool.submit(unit, script) for script in group}
            found: list[str] = []
            for script in group:
                result = futures[script].result()
                matrix[script.stem] = result
                if "framework" in result["securebench"]:
                    runs.append(result["securebench"])
                found += _problems(script.stem, result)
            return found

        # The reference and the null candidate run first. If either is wrong, or the
        # candidates are, the pack or the candidates will change, and every other
        # run would be wasted.
        first = [script for script in scripts if script.stem in ("reference", "null")]
        rest = [script for script in scripts if script not in first]
        if problems:
            problems.append("no candidate was run")
        else:
            problems += run(first)
            if problems:
                problems.append(f"the other {len(rest)} candidates were not run")
            else:
                problems += run(rest)
    problems += _consistency(runs)
    record = {
        "source": source_name,
        "task": task,
        "upstream_commit": sources[source_name]["commit"],
        "securebench_commit": git("-C", str(HERE.parent), "rev-parse", "HEAD"),
        "pier": load_sources()[0]["pier"],
        "workers": workers,
        "candidates": matrix,
        "problems": problems,
    }
    (conversion / "qualification.json").write_text(json.dumps(record, indent=2) + "\n")
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(f"{task}: {'qualified' if not problems else 'not qualified'}")
    return 0 if not problems else 1


def committed_digest(conversion: Path, export: Path) -> str:
    """The digest of the conversion's pack as committed at HEAD, from a `git archive` export."""
    archive = subprocess.run(
        ["git", "-C", str(HERE.parent), "archive", "HEAD", f"{conversion}/task"],
        check=True,
        capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(export)], input=archive, check=True)
    output = subprocess.run(
        ["uv", "run", "securebench", "validate", str(export / conversion / "task")],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return output.rsplit("pack ", 1)[-1]


def committed(conversions: list[Path]) -> int:
    """Check that each conversion's committed pack has the digest its qualification records.

    The coordinator runs it after committing a conversion. It catches
    what `qualify` cannot see before the commit: a pack file left out of the commit.
    """
    names = [Path(c).resolve().relative_to(HERE.parent) for c in conversions] or [
        record.parent.relative_to(HERE.parent)
        for record in sorted(HERE.glob("*/*/qualification.json"))
    ]

    def check(name: Path) -> str | None:
        record = json.loads((HERE.parent / name / "qualification.json").read_text())
        qualified = {run["securebench"]["pack_digest"] for run in record["candidates"].values()}
        with tempfile.TemporaryDirectory() as export:
            digest = committed_digest(name, Path(export))
        if qualified != {digest}:
            return f"{name}: committed pack {digest}, qualification records {sorted(qualified)}"
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        problems = [problem for problem in pool.map(check, names) if problem]
    print("\n".join(problems) or f"{len(names)} conversions: committed packs match")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversion campaign tooling")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch")
    commands.add_parser("order").add_argument("source")
    commands.add_parser("qualify").add_argument("conversion", type=Path)
    commands.add_parser("seed-native-cache")
    commands.add_parser("committed").add_argument("conversions", type=Path, nargs="*")
    arguments = parser.parse_args()
    match arguments.command:
        case "fetch":
            fetch()
        case "order":
            print("\n".join(order(arguments.source)))
        case "seed-native-cache":
            seed_native_cache()
        case "committed":
            return committed(arguments.conversions)
        case _:
            return qualify(arguments.conversion)
    return 0


if __name__ == "__main__":
    sys.exit(main())
