"""Recompute the stored judgments of the released SecureBench records, without a model.

    uv run python runs/rejudge.py [runs/<folder> ...]

Each `securebench-record.json` holds the evidence of every check and case, and the
judgment the Oracle gave on it. This script starts each task's Oracle, rebuilds its
plan from the seed in the record and judges the stored evidence again. It needs
Linux, as the Oracle process does.

A record is skipped when its plan differs from the plan of the pack in
`conversions/`. That pack changed after the attempt, so the stored cases no longer
line up with its hidden data. `runs/fidelity-regrade/` lists those attempts graded
again on the current packs.
"""

import json
import sys
from pathlib import Path
from typing import Any

from securebench.core import jsondata
from securebench.core.evidence import plan_to_json
from securebench.oracle.process import OracleProcess
from securebench.runner.attempt import load_and_check
from securebench.runner.cli import _rejudge_record  # pyright: ignore[reportPrivateUsage]

RUNS = Path(__file__).resolve().parent
PACKS = {pack.parent.name: pack for pack in RUNS.parent.glob("conversions/*/*/task")}


def main() -> int:
    folders = [Path(argument) for argument in sys.argv[1:]] or [RUNS]
    groups: dict[tuple[str, int], list[tuple[Path, dict[str, Any]]]] = {}
    for folder in folders:
        for path in sorted(folder.rglob("securebench-record.json")):
            record = json.loads(path.read_bytes())
            seed = record["provenance"]["run"]["seed"]
            groups.setdefault((record["task"], seed), []).append((path, record))

    checked = mismatches = skipped = 0
    for (name, seed), records in sorted(groups.items()):
        with OracleProcess(load_and_check(PACKS[name])) as oracle:
            plan = oracle.plan(seed)
            digest = jsondata.digest(plan_to_json(plan))
            for path, record in records:
                if record["provenance"]["task"]["plan"] != digest:
                    skipped += 1
                    print(f"{path}: skipped, its pack changed after the attempt")
                    continue
                found, compared = _rejudge_record(oracle, plan, record)
                checked += compared
                mismatches += found
                if found:
                    print(f"{path}: {found} judgments differ")
    print(f"rejudged {checked} judgments: {mismatches} mismatches, {skipped} records skipped")
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
