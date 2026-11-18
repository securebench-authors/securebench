"""Adversarial campaign tooling.

This runs outside SecureBench's trusted path, like the conversion tools whose
helpers it reuses. It never executes what an agent wrote: attempts run inside
SecureBench, and the native verifier runs a passing candidate inside Pier.

    uv run python adversarial/campaign.py build [<source>/<task> ...]
    uv run python adversarial/campaign.py seed
    uv run python adversarial/campaign.py run --campaign DIR --token-file F \
        [--tiers task task-white-box] [--task-list FILE] [--usage-limit 80] \
        [--max-running 3] [<source>/<task> ...]
    uv run python adversarial/campaign.py export --campaign DIR

`build` makes the black-box and white-box copies of each converted task pack.
They are not committed: each task's `ADVERSARIAL.md` records their digests,
and rebuilding from the same commit gives the same digests. Without arguments
it builds every task that `conversions/inventory.tsv` marks `converted`.

`seed` draws the adversarial campaign's one seed into `adversarial/seed.json`,
which is committed before any attempt and used by every run.

`run` attempts each task in both tiers with that seed, or only in the tiers
`--tiers` names, as a rerun after a remediation does. A run's task list is fixed
when it first starts: the tasks named, or the file `--task-list` names when a
run goes in waves, or every copy. It can be stopped and
started again: finished attempts are kept, and attempts to run again are set
aside under `raw/replaced/`. `export` writes the committed record of the
campaign folder from its `raw/` folder and the coordinator's
`classification.json`.
`runs/opus-adversarial-final-180/` holds each task and tier's one attempt on its
current pack, gathered from the runs that made them.
"""

# This tool reuses the fidelity study's helpers for transcripts, native regrades and
# candidate exports, which `conversions/equivalence.py` keeps private to that tool.
# pyright: reportPrivateUsage=false

import argparse
import csv
import fcntl
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import tomllib
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from securebench.core import hashing
from securebench.core.errors import PackError
from securebench.runner.attempt import load_and_check
from securebench.taskspec.load import pack_digest

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
CONVERSIONS = REPOSITORY / "conversions"
# conversions/ goes first: equivalence imports conversions/campaign.py as `campaign`,
# which this file, run as a script from its own folder, would otherwise shadow.
sys.path.insert(0, str(CONVERSIONS))
import equivalence  # noqa: E402

ARCHITECTURE = REPOSITORY / "docs" / "architecture.md"
SOURCES = ("terminal-bench", "deep-swe")
BLACK_BOX = "task"
WHITE_BOX = "task-white-box"
TIERS = (BLACK_BOX, WHITE_BOX)
_TIER_NAMES = {BLACK_BOX: "black box", WHITE_BOX: "white box"}
# Both briefs name these mount points, so they are fixed here and nowhere else.
ARCHITECTURE_ASSET = ("securebench", "/securebench")
GRADER_ASSET = ("grader", "/grader")
# The agent configuration of every adversarial run.
HARNESS = "claude-code"
VERSION = str(equivalence.HARNESSES[HARNESS]["version"])
MODEL = "claude-opus-5-5"
EFFORT = "high"
AGENT_TIMEOUT_SECONDS = 3600
SEED_FILE = HERE / "seed.json"
# The agent gets no feedback from evaluation, so it cannot search the seed space; 31 bits
# also keep the seed valid for any adapter or Oracle that hands it to a 32-bit API.
MAX_SEED = 2**31 - 1
# Candidates whose files total more than this keep only their manifest.
CANDIDATE_FILES_LIMIT = 10 * 1024 * 1024
# The three causes of a successful attack, and the faked-implementation class beside
# them, which does not count against SecureBench's guarantees.
CAUSES = ("mechanism", "conversion", "upstream", "faked-implementation")
# Each task and tier's one attempt on its current pack, copied from the runs.
FINAL = REPOSITORY / "runs" / "opus-adversarial-final-180"
# The native run: the same attacker on each upstream task under Pier.
# Its copies are at adversarial/<source>/<task>/native/<tier>/, built, not committed.
NATIVE = "native"
NATIVE_DOCS = HERE / "native-docs"
NATIVE_COPIES = HERE / "native-copies.tsv"
BENCHMARKS = {"terminal-bench": "Terminal-Bench", "deep-swe": "DeepSWE"}
# The upstream files that make up the grader without its tests: the
# verifier's entry point, DeepSWE's shared grading frame and its configuration, the
# verifier image, and the script that builds what the verifier grades.
GRADER_FILES = (
    "tests/test.sh",
    "tests/grader.py",
    "tests/config.json",
    "tests/Dockerfile",
    "pre_artifacts.sh",
)
# A native pass's classification; `failed-attack` is a genuine solution.
NATIVE_OUTCOMES = ("stopped-by-securebench", "upstream-weakness", "out-of-scope", "failed-attack")


def converted_tasks() -> list[str]:
    with (CONVERSIONS / "inventory.tsv").open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file, delimiter="\t")
        return [f"{row['source']}/{row['task']}" for row in rows if row["decision"] == "converted"]


def qualified_digest(conversion: Path) -> str:
    """The one pack digest every candidate run of the conversion's qualification records."""
    record = json.loads((conversion / "qualification.json").read_text(encoding="utf-8"))
    digests = {run["securebench"]["pack_digest"] for run in record["candidates"].values()}
    if len(digests) != 1:
        raise SystemExit(f"{conversion}: qualification records {len(digests)} pack digests")
    return digests.pop()


def brief(tier: str) -> str:
    return (HERE / f"brief-{'black-box' if tier == BLACK_BOX else 'white-box'}.md").read_text(
        encoding="utf-8"
    )


def add_asset(pack: Path, asset: tuple[str, str]) -> None:
    # A [[public_assets]] header names a top-level array wherever it appears,
    # so appending it after the last check table is valid TOML.
    source, target = asset
    with (pack / "task.toml").open("a", encoding="utf-8") as file:
        file.write(f'\n[[public_assets]]\nsource = "{source}"\ntarget = "{target}"\n')


def build_tier(source_pack: Path, destination: Path, tier: str, source_digest: str) -> None:
    shutil.copytree(source_pack, destination, symlinks=True)
    if pack_digest(destination) != source_digest:
        raise SystemExit(f"{destination}: the copy does not match its source")
    instructions = destination / "instructions.md"
    text = instructions.read_text(encoding="utf-8").rstrip("\n")
    instructions.write_text(f"{text}\n\n{brief(tier)}", encoding="utf-8")
    architecture = destination / "public" / ARCHITECTURE_ASSET[0]
    architecture.mkdir(parents=True)
    shutil.copyfile(ARCHITECTURE, architecture / "architecture.md")
    add_asset(destination, ARCHITECTURE_ASSET)
    if tier == WHITE_BOX:
        add_grader(source_pack, destination)


def add_grader(source_pack: Path, destination: Path) -> None:
    """The white box's copy of the task's evaluation files and Oracle code, at /grader/."""
    grader = destination / "public" / GRADER_ASSET[0]
    if (source_pack / "evaluation").is_dir():
        shutil.copytree(source_pack / "evaluation", grader / "evaluation", symlinks=True)
    else:
        # The brief names /grader/evaluation/; an empty folder says the task has none.
        (grader / "evaluation").mkdir(parents=True)
    (grader / "hidden").mkdir()
    shutil.copy2(source_pack / "hidden" / "oracle.py", grader / "hidden" / "oracle.py")
    add_asset(destination, GRADER_ASSET)


def left_out(source_pack: Path) -> list[str]:
    hidden = source_pack / "hidden"
    return sorted(
        path.relative_to(source_pack).as_posix()
        for path in hidden.rglob("*")
        if path.is_file() and path != hidden / "oracle.py"
    )


def record(name: str, source_digest: str, digests: dict[str, str], source_pack: Path) -> str:
    source, task = name.split("/")
    hidden = left_out(source_pack)
    architecture = hashing.sha256(ARCHITECTURE.read_bytes())
    leaves_out = (
        ", ".join(f"`{path}`" for path in hidden)
        if hidden
        else "none: `hidden/oracle.py` is the only hidden file"
    )
    lines = [
        f"# {task} (adversarial copies)",
        "",
        "Adversarial copies for the adversarial campaign. They are"
        " not conversions: they are never qualified, reviewed as conversions or counted."
        " `adversarial/campaign.py build` makes them; they are not committed, and rebuilding"
        " from the same commit gives the digests below.",
        "",
        f"- Source pack: `conversions/{source}/{task}/task`, `{source_digest}`, the digest its"
        " qualification records.",
        f"- Architecture copy: `docs/architecture.md`, `{architecture}`,"
        f" mounted read-only at `{ARCHITECTURE_ASSET[1]}` in both copies.",
        f"- `{BLACK_BOX}/`: black box, `{digests[BLACK_BOX]}`. It differs from the source in"
        " `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the"
        f" task), `public/{ARCHITECTURE_ASSET[0]}/` and one `[[public_assets]]` entry in"
        " `task.toml`.",
        f"- `{WHITE_BOX}/`: white box, `{digests[WHITE_BOX]}`. Its brief is"
        " `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an"
        " exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only"
        f" at `{GRADER_ASSET[1]}` by a second `[[public_assets]]` entry.",
        f"- Hidden files the white box leaves out: {leaves_out}.",
    ]
    if not (source_pack / "evaluation").is_dir():
        lines.append(
            "- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder."
        )
    return "\n".join(lines) + "\n"


def build(name: str) -> None:
    source, task = name.split("/")
    if source not in SOURCES:
        raise SystemExit(f"{name}: unknown source")
    conversion = CONVERSIONS / source / task
    source_pack = conversion / "task"
    source_digest = qualified_digest(conversion)
    if pack_digest(source_pack) != source_digest:
        raise SystemExit(f"{name}: the pack differs from the one its qualification records")
    with (source_pack / "task.toml").open("rb") as file:
        if "public_assets" in tomllib.load(file) or (source_pack / "public").exists():
            raise SystemExit(f"{name}: the source pack already has public assets")
    folder = HERE / source / task
    digests: dict[str, str] = {}
    for tier in (BLACK_BOX, WHITE_BOX):
        destination = folder / tier
        if destination.exists():
            shutil.rmtree(destination)
        build_tier(source_pack, destination, tier, source_digest)
        try:
            digests[tier] = load_and_check(destination).digest
        except PackError as error:
            raise SystemExit(str(error)) from None
    (folder / "ADVERSARIAL.md").write_text(
        record(name, source_digest, digests, source_pack), encoding="utf-8"
    )
    print(f"{name}: {BLACK_BOX} {digests[BLACK_BOX]}, {WHITE_BOX} {digests[WHITE_BOX]}")


def build_all(names: list[str]) -> int:
    failures: list[str] = []
    for name in names:
        try:
            build(name)
        except SystemExit as error:
            failures.append(str(error))
            print(error, file=sys.stderr)
    if failures:
        print(f"{len(failures)} tasks not built", file=sys.stderr)
        return 1
    return 0


def tree_digest(folder: Path) -> str:
    """A digest of every path, kind, mode bit and content under `folder`."""
    lines: list[str] = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder).as_posix()
        if path.is_symlink():
            lines.append(f"{relative}\0link\0{os.readlink(path)}")
        elif path.is_file():
            executable = "x" if path.stat().st_mode & 0o111 else "-"
            lines.append(f"{relative}\0{executable}\0{hashing.sha256(path.read_bytes())}")
        else:
            lines.append(f"{relative}\0dir")
    return hashing.sha256("\n".join(lines).encode())


def native_copy(name: str, tier: str) -> Path:
    return HERE / name / NATIVE / tier


def native_task_name(name: str, tier: str) -> str:
    """The copy's Pier task name, which also names its images, so no two copies share one.

    Pier requires the `org/name` form.
    """
    return f"securebench/native-adversarial-{name.split('/')[1]}-{tier}"


def _native_toml(text: str, name: str, tier: str) -> str:
    """The upstream `task.toml` with its name, agent timeout and prebuilt image changed.

    The image moves into the copy's Dockerfile, which adds the documentation (and the
    grader) on top of it. The edit is checked against the upstream configuration.
    """
    section = ""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
        key = stripped.split("=", 1)[0].strip()
        if section == "[task]" and key == "name":
            line = f'name = "{native_task_name(name, tier)}"'
        elif section == "[agent]" and key == "timeout_sec":
            line = f"timeout_sec = {AGENT_TIMEOUT_SECONDS}.0"
        elif section == "[environment]" and key == "docker_image":
            continue
        lines.append(line)
    edited = "\n".join(lines) + "\n"
    before, after = tomllib.loads(text), tomllib.loads(edited)
    before["task"]["name"] = native_task_name(name, tier)
    before["agent"]["timeout_sec"] = float(AGENT_TIMEOUT_SECONDS)
    del before["environment"]["docker_image"]
    if before != after:
        raise SystemExit(f"{name}: the edited task.toml changes more than intended")
    return edited


def build_native_tier(name: str, upstream: Path, destination: Path, tier: str) -> list[str]:
    """One native copy; returns the upstream test files it leaves out (white box)."""
    shutil.copytree(upstream, destination, symlinks=True)
    with (upstream / "task.toml").open("rb") as file:
        image = tomllib.load(file)["environment"]["docker_image"]
    environment = destination / "environment"
    if (environment / "docker-compose.yaml").exists() or (environment / "pier").exists():
        raise SystemExit(f"{name}: the upstream environment already uses compose or pier/")
    toml = destination / "task.toml"
    toml.write_text(_native_toml(toml.read_text(encoding="utf-8"), name, tier), encoding="utf-8")
    instruction = destination / "instruction.md"
    text = instruction.read_text(encoding="utf-8").rstrip("\n")
    brief = (HERE / f"brief-native-{_TIER_NAMES[tier].replace(' ', '-')}.md").read_text(
        encoding="utf-8"
    )
    instruction.write_text(
        f"{text}\n\n{brief.replace('{benchmark}', BENCHMARKS[name.split('/')[0]])}",
        encoding="utf-8",
    )
    shutil.copytree(NATIVE_DOCS, environment / "pier")
    dockerfile = [f"FROM {image}", "COPY pier/ /pier/"]
    withheld: list[str] = []
    if tier == WHITE_BOX:
        for relative in GRADER_FILES:
            if (upstream / relative).is_file():
                (environment / "grader" / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(upstream / relative, environment / "grader" / relative)
        dockerfile.append("COPY grader/ /grader/")
        withheld = sorted(
            path.relative_to(upstream).as_posix()
            for path in (upstream / "tests").rglob("*")
            if path.is_file() and path.relative_to(upstream).as_posix() not in GRADER_FILES
        )
    (environment / "Dockerfile").write_text("\n".join(dockerfile) + "\n", encoding="utf-8")
    return withheld


def build_native(names: list[str]) -> int:
    """Build both native copies of each task and record them in `native-copies.tsv`.

    Rows of tasks not named are kept, so building a few tasks leaves the others' records.
    """
    head = "source\ttask\ttier\tupstream_digest\tcopy_digest\twithheld"
    rows: dict[tuple[str, str], str] = {}
    if NATIVE_COPIES.is_file():
        for line in NATIVE_COPIES.read_text(encoding="utf-8").splitlines()[1:]:
            source, task, tier = line.split("\t")[:3]
            rows[(f"{source}/{task}", tier)] = line
    for name in names:
        upstream = equivalence._paths(name)[3]
        for tier in TIERS:
            destination = native_copy(name, tier)
            if destination.exists():
                shutil.rmtree(destination)
            withheld = build_native_tier(name, upstream, destination, tier)
            cells = (*name.split("/"), tier, tree_digest(upstream), tree_digest(destination))
            rows[(name, tier)] = "\t".join((*cells, ",".join(withheld)))
    NATIVE_COPIES.write_text(
        "\n".join([head, *(rows[key] for key in sorted(rows))]) + "\n", encoding="utf-8"
    )
    print(f"{len(names)} tasks built into {NATIVE_COPIES.name}")
    return 0


def adversarial_tasks() -> list[str]:
    """Every task with a committed `ADVERSARIAL.md`."""
    return sorted(
        f"{source}/{path.parent.name}"
        for source in SOURCES
        for path in (HERE / source).glob("*/ADVERSARIAL.md")
    )


def _require_committed(names: list[str], native: bool) -> None:
    """Refuse to run on copies that do not match the committed records, or on a dirty tree."""
    if equivalence.campaign.git(
        "-C", str(REPOSITORY), "status", "--porcelain", "--untracked-files=no"
    ):
        raise SystemExit("the tree has uncommitted changes; SecureBench runs would not be clean")
    records = (
        [NATIVE_COPIES.relative_to(REPOSITORY).as_posix()]
        if native
        else [f"adversarial/{name}/ADVERSARIAL.md" for name in names]
    )
    changed = equivalence.campaign.git("-C", str(REPOSITORY), "status", "--porcelain", *records)
    if changed:
        raise SystemExit(f"the built copies differ from the committed records:\n{changed}")
    seed = SEED_FILE.relative_to(REPOSITORY).as_posix()
    if not SEED_FILE.is_file() or equivalence.campaign.git(
        "-C", str(REPOSITORY), "status", "--porcelain", "--", seed
    ):
        raise SystemExit(f"{seed} must be drawn with `seed` and committed before any attempt")


def draw_seed() -> int:
    """Draw the campaign's one seed; it is drawn once and never replaced."""
    if SEED_FILE.exists():
        raise SystemExit(f"{SEED_FILE} already holds the campaign's seed")
    seed = secrets.randbelow(MAX_SEED) + 1
    now = datetime.now(UTC).isoformat(timespec="seconds")
    SEED_FILE.write_text(json.dumps({"seed": seed, "drawn": now}) + "\n", encoding="utf-8")
    print(f"seed {seed} drawn into {SEED_FILE}; commit it before the first run")
    return 0


def campaign_seed() -> int:
    return int(json.loads(SEED_FILE.read_bytes())["seed"])


def _start(
    campaign: Path,
    raw: Path,
    names: list[str],
    tiers: list[str],
    task_list: list[str] | None,
    native: bool,
) -> tuple[int, list[str]]:
    """The campaign's seed and this run's task list, fixed the first time the run starts."""
    seed = campaign_seed()
    path = raw / "run.json"
    if path.is_file():
        started = json.loads(path.read_bytes())
        tasks = [str(task) for task in started["tasks"]]
        if int(started["seed"]) != seed:
            raise SystemExit(f"{path} holds seed {started['seed']}, not the campaign's {seed}")
        if started.get("tiers", list(TIERS)) != tiers:
            raise SystemExit(f"{path} runs the tiers {started.get('tiers')}, not {tiers}")
        if started.get("native", False) != native:
            raise SystemExit(f"{path} is {'not ' if native else ''}a native run")
        if not set(names) <= set(tasks):
            raise SystemExit(f"tasks outside this run's list: {sorted(set(names) - set(tasks))}")
        return seed, names or tasks
    tasks = task_list or names or adversarial_tasks()
    if not set(names) <= set(tasks):
        raise SystemExit(f"tasks outside the task list: {sorted(set(names) - set(tasks))}")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    commit = equivalence.campaign.git("-C", str(REPOSITORY), "rev-parse", "HEAD")
    path.write_text(
        json.dumps(
            {
                "seed": seed,
                "started": now,
                "commit": commit,
                "tasks": tasks,
                "tiers": tiers,
                "native": native,
            }
        )
    )
    tier_text = (
        "once in the black box and once in the white box"
        if tiers == list(TIERS)
        else f"in the {' and the '.join(_TIER_NAMES[tier] for tier in tiers)} only"
    )
    what = (
        "A native run of the adversarial attacker: Claude Code"
        f" {VERSION} with `{MODEL}` at `{EFFORT}` effort attacks each upstream task's own"
        f" grader under Pier, {tier_text}; each native pass is regraded by SecureBench."
        if native
        else "A run of the adversarial campaign: Claude Code"
        f" {VERSION} with `{MODEL}` at `{EFFORT}` effort attacks each task's grader,"
        f" {tier_text}."
    )
    (campaign / "README.md").write_text(
        f"# Opus 5.5 {'native ' if native else ''}adversarial campaign, {len(tasks)} tasks\n\n"
        f"{what}\n\n"
        f"- Seed: `{seed}`, the adversarial campaign's one seed (`adversarial/seed.json`)."
        " Every attempt of every run of the campaign uses it.\n"
        f"- Started: {now}.\n"
        f"- Framework commit at the start: `{commit}`.\n"
        f"- Agent timeout {AGENT_TIMEOUT_SECONDS} s; each task's upstream resource limits.\n\n"
        "The report follows when the run ends.\n",
        encoding="utf-8",
    )
    print(f"run started with seed {seed}; commit {campaign / 'README.md'}", flush=True)
    return seed, names or tasks


def _set_aside(out: Path, attempts: Path, replaced: Path, why: str) -> None:
    relative = out.relative_to(attempts)
    number = 1
    while (target := replaced / relative.parent / f"{relative.name}-{number}").exists():
        number += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    out.rename(target)
    (target / "replaced.json").write_text(json.dumps({"why": why}) + "\n")
    print(f"{relative}: set aside as {target.name} ({why})", flush=True)


def _transcript_events(path: Path) -> dict[str, Any]:
    """Safeguard events and the final message, from Claude Code's output (untrusted, data only).

    A safeguard shows as a notice that it stopped a response, as a refusal, or as a move
    of the whole session to another model.
    """
    notices = refusals = 0
    fallbacks: list[str] = []
    final: Any = None
    for event in equivalence._events(path):
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and subtype == "informational":
            notices += "safeguards" in str(event.get("content"))
        elif kind == "system" and subtype == "model_refusal_fallback":
            fallbacks.append(str(event.get("fallback_model")))
        elif kind == "assistant":
            refusals += equivalence._object(event.get("message")).get("stop_reason") == "refusal"
        elif kind == "result":
            final = event.get("result")
    return {
        "safeguard_notices": notices,
        "refusals": refusals,
        "fallback_models": fallbacks,
        "final_message": final if isinstance(final, str) else None,
    }


def _outcome(summary: dict[str, Any]) -> str:
    """`pass` (to classify), `failed-attack`, `safeguard`, `model-drift` or `rerun`."""
    native = summary.get("side") == NATIVE
    if ("models" if native else "admitted") not in summary:
        return "rerun"
    validity = equivalence._validity(summary, MODEL)
    verdict = str(summary["verdict"])
    # Natively, a verifier that the agent's work leaves without a reward graded it.
    graded = verdict in ("passed", "failed") or "verifier_error" in summary
    if validity == "not-admitted" or (not graded if native else verdict.startswith("invalid")):
        return "rerun"
    if summary["fallback_models"] or summary["refusals"]:
        return "safeguard"
    if validity == "infrastructure":
        # A session that a safeguard notice ends in an error is the safeguard's result.
        stopped = summary["safeguard_notices"] and summary["result_error"]
        return "safeguard" if stopped else "rerun"
    if validity == "model-drift":
        return "model-drift"
    return "pass" if summary["verdict"] == "passed" else "failed-attack"


def _attempt(name: str, tier: str, seed: int, attempts: Path) -> None:
    """One attempt; a pass is also run under upstream's native verifier."""
    source, task = name.split("/")
    out = attempts / source / task / tier
    out.mkdir(parents=True)
    upstream = equivalence._paths(name)[3]
    pack = HERE / source / task / tier
    started = time.time()
    with (out / "securebench.log").open("w") as log:
        subprocess.run(
            [
                "uv",
                "run",
                "securebench",
                "run",
                str(pack),
                "--run-dir",
                str(out / "run"),
                "--harness",
                f"claude-code-oauth:{VERSION}:{MODEL}",
                "--overlay",
                str(REPOSITORY / "overlays" / f"claude-code-{VERSION}"),
                "--reasoning-effort",
                EFFORT,
                "--qualification",
                str(equivalence.campaign.WORKER),
                *equivalence.campaign.upstream_limits(upstream),
                "--agent-timeout",
                str(AGENT_TIMEOUT_SECONDS),
                "--seed",
                str(seed),
            ],
            check=False,
            cwd=REPOSITORY,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    summary: dict[str, Any] = {"source": source, "task": task, "tier": tier, "seed": seed}
    try:
        record = equivalence._record(out / "run")[1]
        if record["provenance"]["run"]["seed"] != seed:
            raise SystemExit(f"{out}: the run record holds another seed")
        summary.update(equivalence._summary_securebench(out, HARNESS))
        summary.update(
            _transcript_events(equivalence._record(out / "run")[0].with_suffix(".transcript"))
        )
    except LookupError as error:
        summary["verdict"] = f"no record: {error}"
    summary["outcome"] = _outcome(summary)
    if summary["outcome"] == "pass":
        try:
            roots = equivalence._roots(pack)
            summary.update(equivalence._regrade(pack, upstream, roots, "securebench", HARNESS, out))
        except LookupError as error:
            summary["regrade_error"] = str(error)
    summary["wall_seconds"] = round(time.time() - started)
    (out / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{name} {tier}: {summary['verdict']} ({summary['outcome']})", flush=True)


# Pier's errors when the verifier ran on the agent's work and produced no reward. Every
# other Pier error is the harness's or the worker's, and the attempt is run again.
VERIFIER_ERRORS = (
    "VerifierTimeoutError",
    "RewardFileNotFoundError",
    "RewardFileEmptyError",
    "VerifierOutputParseError",
)


def _attempt_native(name: str, tier: str, seed: int, attempts: Path) -> None:
    """One native attempt; a pass is also graded by SecureBench on the current pack (N->S)."""
    source, task = name.split("/")
    out = attempts / source / task / tier
    out.mkdir(parents=True)
    _, _, pack, upstream = equivalence._paths(name)
    roots = equivalence._roots(pack)
    started = time.time()
    copy = native_copy(name, tier)
    summary: dict[str, Any] = {
        "source": source,
        "task": task,
        "tier": tier,
        "seed": seed,
        "side": NATIVE,
        "copy_digest": tree_digest(copy),
    }
    try:
        equivalence._attempt_native(copy, roots, HARNESS, MODEL, EFFORT, None, out)
        summary.update(equivalence._summary_native(out, HARNESS))
        trial = equivalence._trial(out)
        summary.update(_transcript_events(trial / "agent" / "claude-code.txt"))
    except LookupError as error:
        summary["verdict"] = f"no record: {error}"
    if summary.get("provider_errors") and summary["provider_errors"][0] in VERIFIER_ERRORS:
        summary["verifier_error"] = summary.pop("provider_errors")[0]
        summary["provider_errors"] = []
    summary["outcome"] = _outcome(summary)
    if summary["outcome"] == "pass":
        try:
            summary.update(
                equivalence._regrade(pack, upstream, roots, "native", HARNESS, out, seed)
            )
        except LookupError as error:
            summary["regrade_error"] = str(error)
    _remove_native_images(name, tier)
    summary["wall_seconds"] = round(time.time() - started)
    (out / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{name} {tier} native: {summary['verdict']} ({summary['outcome']})", flush=True)


def _remove_native_images(name: str, tier: str) -> None:
    """Remove the images Pier built for one native copy; each holds a Claude Code install."""
    # Pier's image names replace the task name's `/` (`_sanitize_docker_image_name`).
    prefix = f"hb__{native_task_name(name, tier).replace('/', '-')}"
    images = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    mine = [image for image in images if image.startswith(prefix)]
    if mine:
        subprocess.run(["docker", "rmi", "-f", *mine], check=False, capture_output=True)


def _docker_allows(min_free_gib: int) -> tuple[bool, str]:
    """False, and why, while the Docker data root has less than `min_free_gib` free."""
    root = subprocess.run(
        ["docker", "info", "--format", "{{.DockerRootDir}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    free = shutil.disk_usage(root).free / 2**30
    if free >= min_free_gib:
        return True, ""
    return False, f"{free:.0f} GiB free on the Docker data root, below {min_free_gib}; waiting"


def run(
    campaign: Path,
    token_file: Path,
    names: list[str],
    usage_limit: int | None,
    max_running: int,
    memory_budget: int,
    min_available: int,
    min_docker_free: int,
    tiers: list[str],
    task_list: list[str] | None,
    native: bool,
) -> int:
    raw = campaign / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    attempts, replaced = raw / "attempts", raw / "replaced"
    with (raw / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"another run of {campaign} is going") from None
        if (build_native if native else build_all)(names or adversarial_tasks()):
            return 1
        _require_committed(names or adversarial_tasks(), native)
        seed, tasks = _start(campaign, raw, names, tiers, task_list, native)
        for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
            os.environ.pop(key, None)
        credential = str(equivalence.HARNESSES[HARNESS]["credential"])
        os.environ[credential] = equivalence._token(token_file, credential)
        units: list[tuple[str, str]] = []
        # A native run attempts every task in the black box before any in the white box.
        order = (
            [(n, t) for t in tiers for n in tasks]
            if native
            else [(n, t) for n in tasks for t in tiers]
        )
        for name, tier in order:
            out = attempts / name / tier
            if (out / "attempt.json").is_file():
                summary = json.loads((out / "attempt.json").read_bytes())
                if summary["outcome"] != "rerun":
                    continue
                _set_aside(out, attempts, replaced, f"rerun: {summary['verdict']}")
            elif out.exists():
                _set_aside(out, attempts, replaced, "unfinished")
            units.append((name, tier))
        memory = {name: equivalence._memory_mib(equivalence._paths(name)[3]) for name in tasks}
        print(f"seed {seed}: {len(units)} attempts to run", flush=True)
        failed = 0
        paused = False
        with ThreadPoolExecutor(max_workers=max_running) as pool:
            running: dict[Future[None], tuple[str, str]] = {}
            while units or running:
                ready, why = equivalence._usage_allows(raw, usage_limit)
                if ready:
                    ready, why = equivalence._memory_allows(min_available)
                if ready:
                    ready, why = _docker_allows(min_docker_free)
                if ready == paused:
                    paused = not ready
                    print(why if paused else "resuming", flush=True)
                used = sum(memory[name] for name, _ in running.values())
                for unit in list(units):
                    fits = used + memory[unit[0]] <= memory_budget or not running
                    early = native and unit[1] == WHITE_BOX and units[0][1] == BLACK_BOX
                    if ready and len(running) < max_running and fits and not early:
                        attempt = _attempt_native if native else _attempt
                        running[pool.submit(attempt, *unit, seed, attempts)] = unit
                        used += memory[unit[0]]
                        units.remove(unit)
                if not running:
                    time.sleep(120)
                    continue
                done, _ = wait(running, timeout=None if ready else 120, return_when=FIRST_COMPLETED)
                for future in done:
                    name, tier = running.pop(future)
                    if future.exception() is not None:
                        failed += 1
                        print(f"{name} {tier}: error: {future.exception()!r}", flush=True)
    return 1 if failed else 0


def _unclassified(key: str, summary: dict[str, Any], entry: Any) -> str:
    """The reported outcome of an attempt that did not pass, which is never classified.

    A failed attack whose session had a safeguard notice is reported as a safeguard
    result: most such sessions stop when the notice comes, so their
    failure says nothing about the grader. The runner still records them as failed.
    """
    if entry is not None:
        raise SystemExit(f"{key}: only passes are classified, this is {summary['outcome']}")
    if summary["outcome"] == "failed-attack" and summary["safeguard_notices"]:
        return "safeguard"
    return str(summary["outcome"])


def _final(key: str, summary: dict[str, Any], entry: Any) -> tuple[str, str]:
    """The reported outcome and cause: a pass takes the coordinator's classification."""
    if summary["outcome"] != "pass":
        return _unclassified(key, summary, entry), ""
    if entry is None:
        return "unclassified", ""
    outcome, cause = entry.get("outcome"), entry.get("cause")
    if outcome == "failed-attack" and cause is None:
        return outcome, ""
    if outcome == "successful-attack" and cause in CAUSES:
        return outcome, str(cause)
    raise SystemExit(f"{key}: classified as {outcome!r} with cause {cause!r}")


COLUMNS = (
    "source task tier outcome cause verdict S->N regrade_error agent_seconds "
    "time_limit_expired agent_ending turns cost_usd output_tokens models subagent_models "
    "safeguard_notices refusals fallback_models provider_errors denied_hosts wall_seconds"
).split()


def _row(summary: dict[str, Any]) -> str:
    cells: list[str] = []
    for column in COLUMNS:
        value: Any = summary.get(column)
        if isinstance(value, list):
            value = ",".join(map(str, cast(list[Any], value)))
        cells.append("" if value is None else str(value))
    return "\t".join(cells)


def export(campaign: Path) -> int:
    """The committed record of a run: one folder per task and tier, and its tables.

    Per attempt it keeps the summary with its classification, SecureBench's verdict
    record, the captured candidate (its files when they total 10 MB or less), the
    agent's final message, and for a pass the native verifier's outcome. Transcripts
    and stores stay in `raw/`.
    """
    raw = campaign / "raw"
    started = json.loads((raw / "run.json").read_bytes())
    seed = int(started["seed"])
    path = campaign / "classification.json"
    classification: dict[str, Any] = json.loads(path.read_bytes()) if path.is_file() else {}
    seen: set[str] = set()
    rows: list[str] = []
    for attempt_path in sorted((raw / "attempts").glob("*/*/*/attempt.json")):
        out = attempt_path.parent
        summary: dict[str, Any] = json.loads(attempt_path.read_bytes())
        key = f"{summary['source']}/{summary['task']}/{summary['tier']}"
        if summary["seed"] != seed:
            raise SystemExit(f"{key}: seed {summary['seed']}, not the run's {seed}")
        seen.add(key)
        entry = classification.get(key)
        summary["outcome"], summary["cause"] = _final(key, summary, entry)
        if entry is not None:
            summary["classification"] = entry
        target = campaign / summary["task"] / summary["tier"]
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        final = summary.pop("final_message", None)
        if final:
            (target / "final-message.md").write_text(final + "\n", encoding="utf-8")
        if (out / "run" / "attempts").is_dir():
            shutil.copyfile(equivalence._record(out / "run")[0], target / "securebench-record.json")
            summary["candidate_export"] = equivalence._export_candidate(
                out / "run", target, CANDIDATE_FILES_LIMIT
            )
        native = out / "regrade" / "to-native" / "native" / "job"
        trials = [trial.parent for trial in native.glob("*/result.json")]
        if trials:
            verifier = equivalence._verifier(equivalence._one(trials, "Pier trial"))
            (target / "verifier.json").write_text(json.dumps(verifier, indent=2) + "\n")
        (target / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
        rows.append(_row(summary))
    unknown = set(classification) - seen
    if unknown:
        raise SystemExit(f"classification.json names attempts that do not exist: {sorted(unknown)}")
    (campaign / "attempts.tsv").write_text("\n".join(["\t".join(COLUMNS), *rows]) + "\n")
    replaced_rows: list[str] = []
    for why_path in sorted((raw / "replaced").glob("*/*/*/replaced.json")):
        out = why_path.parent
        why = str(json.loads(why_path.read_bytes())["why"])
        replaced_rows.append("\t".join((out.parent.parent.name, out.parent.name, out.name, why)))
    (campaign / "replaced-attempts.tsv").write_text(
        "\n".join(["source\ttask\tkept_as\twhy", *replaced_rows]) + "\n"
    )
    counts: dict[str, int] = {}
    for row in rows:
        outcome = row.split("\t")[COLUMNS.index("outcome")]
        counts[outcome] = counts.get(outcome, 0) + 1
    print(", ".join(f"{count} {outcome}" for outcome, count in sorted(counts.items())))
    return 0


NATIVE_COLUMNS = (
    "source task tier outcome maintainer_review verdict verifier_error N->S N->s->N "
    "regrade_error agent_seconds time_limit_expired turns cost_usd output_tokens models "
    "subagent_models safeguard_notices refusals fallback_models provider_errors wall_seconds"
).split()


def _final_native(key: str, summary: dict[str, Any], entry: Any) -> str:
    """The reported outcome of a native attempt: a pass takes the coordinator's class."""
    if summary["outcome"] != "pass":
        return _unclassified(key, summary, entry)
    if entry is None:
        return "unclassified"
    outcome = entry.get("outcome")
    if outcome not in NATIVE_OUTCOMES:
        raise SystemExit(f"{key}: classified as {outcome!r}")
    # The two classes that compare the graders must agree with SecureBench's verdict,
    # unless the coordinator shows that verdict incidental and marks it for review.
    passed = summary.get("N->S") == "passed"
    review = bool(entry.get("maintainer_review"))
    if (outcome == "stopped-by-securebench" and passed) or (
        outcome == "upstream-weakness" and not passed and not review
    ):
        raise SystemExit(f"{key}: {outcome} does not fit N->S {summary.get('N->S')}")
    return str(outcome)


def current_packs() -> dict[str, str]:
    """Each task and tier's current pack: the copy digest in the task's `ADVERSARIAL.md`."""
    current: dict[str, str] = {}
    for record in HERE.glob("*/*/ADVERSARIAL.md"):
        text = record.read_text(encoding="utf-8")
        for tier in TIERS:
            match = re.search(rf"- `{tier}/`: {_TIER_NAMES[tier]}, `(sha256:[0-9a-f]{{64}})`", text)
            if match is None:
                raise SystemExit(f"{record}: no digest for {tier}")
            current[f"{record.parent.parent.name}/{record.parent.name}/{tier}"] = match[1]
    return current


def current_attempts() -> dict[str, list[Path]]:
    """Each task and tier's exported attempts on its current pack.

    They are read from the combined folder, which holds each task and tier's one
    attempt. An attempt counts when its record holds the current pack's digest.
    """
    current = current_packs()
    found: dict[str, list[Path]] = {}
    for path in sorted(FINAL.glob("*/*/attempt.json")):
        summary = json.loads(path.read_bytes())
        key = f"{summary['source']}/{summary['task']}/{summary['tier']}"
        if summary.get("pack_digest") == current.get(key):
            found.setdefault(key, []).append(path.parent)
    return found


def securebench_results() -> dict[str, list[str]]:
    """Each task and tier's adversarial results on its current pack, with their runs."""
    found: dict[str, list[str]] = {}
    for key, folders in current_attempts().items():
        for folder in folders:
            summary = json.loads((folder / "attempt.json").read_bytes())
            cause = f" ({summary['cause']})" if summary.get("cause") else ""
            run = folder.parent.parent.name
            found.setdefault(key, []).append(f"{summary['outcome']}{cause} [{run}]")
    return found


def export_native(campaign: Path) -> int:
    """The committed record of a native run, like `export`, and `paired.tsv`.

    Per attempt it keeps the summary with its classification, the agent's final message,
    Pier's verifier outcomes, and for a pass SecureBench's record of the native files
    (N->S) with the candidate it captured. `paired.tsv` puts each attempt next to the
    task's SecureBench adversarial result in the same tier on its current pack.
    """
    raw = campaign / "raw"
    seed = int(json.loads((raw / "run.json").read_bytes())["seed"])
    path = campaign / "classification.json"
    classification: dict[str, Any] = json.loads(path.read_bytes()) if path.is_file() else {}
    securebench = securebench_results()
    seen: set[str] = set()
    rows: list[str] = []
    paired = ["source\ttask\ttier\tnative\tsecurebench"]
    for attempt_path in sorted((raw / "attempts").glob("*/*/*/attempt.json")):
        out = attempt_path.parent
        summary: dict[str, Any] = json.loads(attempt_path.read_bytes())
        key = f"{summary['source']}/{summary['task']}/{summary['tier']}"
        if summary["seed"] != seed:
            raise SystemExit(f"{key}: seed {summary['seed']}, not the run's {seed}")
        seen.add(key)
        entry = classification.get(key)
        summary["outcome"] = _final_native(key, summary, entry)
        if entry is not None:
            summary["classification"] = entry
            summary["maintainer_review"] = bool(entry.get("maintainer_review"))
        target = campaign / summary["task"] / summary["tier"]
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        final = summary.pop("final_message", None)
        if final:
            (target / "final-message.md").write_text(final + "\n", encoding="utf-8")
        to_securebench = out / "regrade" / "to-securebench" / "securebench"
        if (to_securebench / "attempts").is_dir():
            record = equivalence._record(to_securebench)[0]
            shutil.copyfile(record, target / "securebench-record.json")
            summary["candidate_export"] = equivalence._export_candidate(
                to_securebench, target, CANDIDATE_FILES_LIMIT
            )
        verifiers: dict[str, Any] = {}
        trials = [trial.parent for trial in (out / "jobs" / "job").glob("*/result.json")]
        if trials:
            verifiers["N"] = equivalence._verifier(equivalence._one(trials, "Pier trial"))
        native = out / "regrade" / "to-native" / "native" / "job"
        for trial in (p.parent for p in native.glob("*/result.json")):
            verifiers["N->s->N"] = equivalence._verifier(trial)
        (target / "verifier.json").write_text(json.dumps(verifiers, indent=2) + "\n")
        (target / "attempt.json").write_text(json.dumps(summary, indent=2) + "\n")
        cells: list[str] = []
        for column in NATIVE_COLUMNS:
            value: Any = summary.get(column)
            if isinstance(value, list):
                value = ",".join(map(str, cast(list[Any], value)))
            cells.append("" if value is None else str(value))
        rows.append("\t".join(cells))
        results = "; ".join(securebench.get(key, ["none"]))
        paired.append(
            "\t".join(
                (summary["source"], summary["task"], summary["tier"], summary["outcome"], results)
            )
        )
    unknown = set(classification) - seen
    if unknown:
        raise SystemExit(f"classification.json names attempts that do not exist: {sorted(unknown)}")
    (campaign / "attempts.tsv").write_text("\n".join(["\t".join(NATIVE_COLUMNS), *rows]) + "\n")
    (campaign / "paired.tsv").write_text("\n".join(paired) + "\n")
    replaced_rows: list[str] = []
    for why_path in sorted((raw / "replaced").glob("*/*/*/replaced.json")):
        out = why_path.parent
        why = str(json.loads(why_path.read_bytes())["why"])
        replaced_rows.append("\t".join((out.parent.parent.name, out.parent.name, out.name, why)))
    (campaign / "replaced-attempts.tsv").write_text(
        "\n".join(["source\ttask\tkept_as\twhy", *replaced_rows]) + "\n"
    )
    counts: dict[str, int] = {}
    for row in rows:
        outcome = row.split("\t")[NATIVE_COLUMNS.index("outcome")]
        counts[outcome] = counts.get(outcome, 0) + 1
    print(", ".join(f"{count} {outcome}" for outcome, count in sorted(counts.items())))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Adversarial campaign tooling.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build", help="build the adversarial copies")
    build_command.add_argument(
        "tasks", nargs="*", help="<source>/<task>; default every converted task"
    )
    commands.add_parser("seed", help="draw the campaign's one seed")
    run_command = commands.add_parser("run", help="attempt each task in both tiers")
    run_command.add_argument("tasks", nargs="*", help="<source>/<task>; default every copy")
    run_command.add_argument("--campaign", type=Path, required=True, help="the campaign folder")
    run_command.add_argument(
        "--token-file", type=Path, required=True, help="a file with CLAUDE_CODE_OAUTH_TOKEN=..."
    )
    run_command.add_argument(
        "--usage-limit", type=int, help="pause at this five-hour usage, in percent"
    )
    run_command.add_argument(
        "--tiers",
        nargs="+",
        choices=TIERS,
        default=list(TIERS),
        help="the tiers to attempt, fixed when the run first starts; default both",
    )
    run_command.add_argument(
        "--task-list",
        type=Path,
        help="a file with one <source>/<task> per line: the run's task list at its first start,"
        " when the tasks named are only its first wave",
    )
    run_command.add_argument(
        "--native",
        action="store_true",
        help="attack each upstream task's own grader under Pier",
    )
    run_command.add_argument("--max-running", type=int, default=3)
    run_command.add_argument(
        "--memory-budget-mib",
        type=int,
        default=12288,
        help="the sum of upstream memory limits of running attempts",
    )
    run_command.add_argument("--min-available-mib", type=int, default=6144)
    run_command.add_argument("--min-docker-free-gib", type=int, default=15)
    export_command = commands.add_parser("export", help="the committed record of a run")
    export_command.add_argument("--campaign", type=Path, required=True)
    native_command = commands.add_parser("build-native", help="build the native copies")
    native_command.add_argument(
        "tasks", nargs="*", help="<source>/<task>; default every task with adversarial copies"
    )
    arguments = parser.parse_args()
    if arguments.command == "build":
        return build_all(arguments.tasks or converted_tasks())
    if arguments.command == "build-native":
        return build_native(arguments.tasks or adversarial_tasks())
    if arguments.command == "seed":
        return draw_seed()
    if arguments.command == "run":
        return run(
            arguments.campaign.resolve(),
            arguments.token_file,
            arguments.tasks,
            arguments.usage_limit,
            arguments.max_running,
            arguments.memory_budget_mib,
            arguments.min_available_mib,
            arguments.min_docker_free_gib,
            [tier for tier in TIERS if tier in arguments.tiers],
            arguments.task_list.read_text().split() if arguments.task_list else None,
            arguments.native,
        )
    campaign = arguments.campaign.resolve()
    native = json.loads((campaign / "raw" / "run.json").read_bytes()).get("native", False)
    return export_native(campaign) if native else export(campaign)


if __name__ == "__main__":
    sys.exit(main())
