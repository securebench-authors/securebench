"""Degrade the reference's plan for one bucket until it sits at a threshold.

Usage: near_threshold.py <over|under> <bucket>

Starting from the reference's plan, requests are moved one at a time into the
batch with the shortest generation bound above their own that their prompt
fits, which adds a little decode padding and cost. After each move the plan is scored with the public
cost model. `over` writes the first plan that exceeds a threshold of the
instructions' table; `under` writes the last plan before that one. The two
mutants put plans just either side of the acceptance boundary, where the
Oracle's transliterated cost model must agree with upstream's.
"""

import json
import sys

sys.path.insert(0, "/app/task_file/scripts")
from cost_model import CostModel  # noqa: E402

THRESHOLDS = {
    1: {"cost": 3.0e11, "pad_ratio": 0.055, "p95_latency_ms": 2.1e6, "sequential_timecost": 2.7e8},
    2: {"cost": 4.8e10, "pad_ratio": 0.15, "p95_latency_ms": 2.1e5, "sequential_timecost": 3.2e7},
}


def exceeded(metrics: dict, limits: dict) -> list[str]:
    return [k for k, v in limits.items() if metrics[k] > v]


def main(mode: str, bucket: int) -> None:
    with open(f"/app/task_file/input_data/requests_bucket_{bucket}.jsonl") as f:
        reqs = {r["request_id"]: r for r in map(json.loads, f)}
    path = f"/app/task_file/output_data/plan_b{bucket}.jsonl"
    with open(path) as f:
        plan = [json.loads(line) for line in f]
    cm = CostModel(granularity=64)
    limits = THRESHOLDS[bucket]
    if exceeded(cm.plan_metrics(reqs, plan), limits):
        raise SystemExit("the reference plan already exceeds a threshold")
    previous = [dict(p) for p in plan]
    for index in range(len(plan)):
        rec = plan[index]
        bounds: dict[str, int] = {}
        shapes: dict[str, dict] = {}
        for p in plan:
            if p["shape"]["seq_align"] == rec["shape"]["seq_align"] and p["batch_id"] != rec["batch_id"]:
                bounds[p["batch_id"]] = max(bounds.get(p["batch_id"], 0), reqs[p["request_id"]]["gen_len"])
                shapes[p["batch_id"]] = p["shape"]
        gen = reqs[rec["request_id"]]["gen_len"]
        above = sorted(b for b in bounds if bounds[b] > gen)
        if not above:
            continue
        target = min(above, key=lambda b: bounds[b])
        plan[index] = {"request_id": rec["request_id"], "batch_id": target, "shape": dict(shapes[target])}
        metrics = cm.plan_metrics(reqs, plan)
        over = exceeded(metrics, limits)
        if over:
            chosen = plan if mode == "over" else previous
            final = cm.plan_metrics(reqs, chosen)
            print(f"{mode}: move {index} exceeds {over}; " + ", ".join(f"{k} {final[k]} (limit {limits[k]})" for k in limits))
            with open(path, "w") as f:
                for p in chosen:
                    f.write(json.dumps(p) + "\n")
            return
        previous = [dict(p) for p in plan]
    raise SystemExit("no move exceeded a threshold")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
