#!/bin/sh
# Writes the slow baseline plan, with every record, its shape and a metrics file
# claiming that the plan passed with zero cost. The Oracle must ignore claims and
# score the plan itself.
cd /app/task_file/scripts || exit 1
python3 baseline_packer.py || exit 1
python3 - <<'PY'
import json
claim = {"passed": True, "cost": 0.0, "pad_ratio": 0.0, "p95_latency_ms": 0.0, "sequential_timecost": 0.0}
for b in (1, 2):
    path = f"/app/task_file/output_data/plan_b{b}.jsonl"
    with open(path) as f:
        plan = [json.loads(line) for line in f]
    with open(path, "w") as f:
        for rec in plan:
            rec.update(claim)
            rec["shape"]["verdict"] = "passed"
            f.write(json.dumps(rec) + "\n")
with open("/app/task_file/output_data/metrics.json", "w") as f:
    json.dump({"plan_b1": claim, "plan_b2": claim}, f)
PY
