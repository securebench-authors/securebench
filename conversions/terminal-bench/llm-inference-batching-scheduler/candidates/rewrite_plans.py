"""Rewrite the plans the reference wrote, for the mutants. Usage: rewrite_plans.py <mode>.

float-shapes   every shape value as a JSON float (192.0), and an extra shape
               key "rank" whose value cycles through 1, 1.0 and true, which
               Python's dict equality treats as equal within a batch
pretty-json    each record pretty-printed over several lines, as in the
               instructions' example
int-batch-ids  batch ids renumbered as JSON integers 0, 1, 2, ...
"""

import json
import sys

OUT = "/app/task_file/output_data"


def main(mode: str) -> None:
    for name in ("plan_b1.jsonl", "plan_b2.jsonl"):
        path = f"{OUT}/{name}"
        with open(path) as f:
            plan = [json.loads(line) for line in f]
        numbers: dict[str, int] = {}
        ranks = (1, 1.0, True)
        with open(path, "w") as f:
            for index, rec in enumerate(plan):
                if mode == "float-shapes":
                    rec["shape"] = {k: float(v) for k, v in rec["shape"].items()}
                    rec["shape"]["rank"] = ranks[index % 3]
                    f.write(json.dumps(rec) + "\n")
                elif mode == "pretty-json":
                    f.write(json.dumps(rec, indent=4) + "\n")
                elif mode == "int-batch-ids":
                    rec["batch_id"] = numbers.setdefault(rec["batch_id"], len(numbers))
                    f.write(json.dumps(rec) + "\n")
                else:
                    raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main(sys.argv[1])
