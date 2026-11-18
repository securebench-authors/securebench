"""Recompute the paper's fidelity table from the four fidelity runs.

    python3 runs/fidelity_table.py

It reads `attempts.tsv` in `runs/<agent>-fidelity-run-<n>/`. Each row is one attempt
with its verdicts:

- a native attempt compares N->S (SecureBench on the native agent's files) with
  N->s->N (the native grader on the candidate that N->S captured);
- a SecureBench attempt compares its own verdict with S->N (the native grader on
  its candidate).

A comparison counts when the attempt is valid and both graders gave a verdict. Five
tasks are left out of the comparison, because their native tests check something a
copy of the files does not carry. GPT's pass counts leave out `vulnerable-secret`,
where the provider's safeguards refused attempts.
"""

import csv
from pathlib import Path

RUNS = Path(__file__).parent
AGENTS = ("sonnet", "gpt")
LEFT_OUT = {
    "pypi-server",
    "kv-store-grpc",
    "openssl-selfsigned-cert",
    "hf-model-inference",
    "adaptive-rejection-sampler",
}
REFUSED = {"gpt": {"vulnerable-secret"}}


def outcome(verdict: str) -> str:
    return verdict.split("/")[0]


def main() -> None:
    compared = dict.fromkeys(AGENTS, 0)
    agreed = dict.fromkeys(AGENTS, 0)
    passed: dict[tuple[str, int, str], int] = {}
    for agent in AGENTS:
        for run in (1, 2):
            path = RUNS / f"{agent}-fidelity-run-{run}" / "attempts.tsv"
            with path.open(newline="") as file:
                for row in csv.DictReader(file, delimiter="\t"):
                    side = row["side"]
                    if row["verdict"] == "passed" and row["task"] not in REFUSED.get(agent, ()):
                        passed[agent, run, side] = passed.get((agent, run, side), 0) + 1
                    if row["task"] in LEFT_OUT or row["validity"] != "ok":
                        continue
                    if side == "native":
                        ours, theirs = outcome(row["N->S"]), outcome(row["N->s->N"])
                    else:
                        ours, theirs = outcome(row["verdict"]), outcome(row["S->N"])
                    if {ours, theirs} <= {"passed", "failed"}:
                        compared[agent] += 1
                        agreed[agent] += ours == theirs

    both_compared, both_agreed = sum(compared.values()), sum(agreed.values())
    print(f"{'':28}{'Sonnet':>12}{'GPT':>12}{'Both':>12}")
    print(f"{'Comparisons':28}{compared['sonnet']:>12}{compared['gpt']:>12}{both_compared:>12}")
    rates = [100 * agreed[a] / compared[a] for a in AGENTS] + [100 * both_agreed / both_compared]
    print(f"{'Graders agree':28}" + "".join(f"{rate:>11.1f}%" for rate in rates))
    differ = [compared[a] - agreed[a] for a in AGENTS] + [both_compared - both_agreed]
    print(f"{'Graders disagree':28}" + "".join(f"{count:>12}" for count in differ))
    print("Tasks passed, first / second run")
    for label, side in (("Natively", "native"), ("Under SecureBench", "securebench")):
        cells = [f"{passed[a, 1, side]} / {passed[a, 2, side]}" for a in AGENTS]
        print(f"  {label:26}" + "".join(f"{cell:>12}" for cell in cells))


if __name__ == "__main__":
    main()
