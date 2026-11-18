"""Rebuild hidden/cases.json from the upstream task.

Usage: python3 -B derive_cases.py <upstream task dir> <output cases.json>

Every value comes from the upstream task unchanged:
- the requests are the two input files under environment/task_file/input_data,
  which the baseline image ships at /app/task_file/input_data;
- the input hashes are EXPECTED_INPUT_HASHES in tests/test_outputs.py, and the
  script refuses to continue unless the shipped files match them;
- the granularity (64), the shape cap (8), the thresholds and the p95 quantile
  are the literals of tests/test_outputs.py;
- HEADS, HIDDEN and the cost constants are those of tests/cost_model_for_tests.py,
  read from its CostConsts defaults here so that a transcription error is impossible.
"""

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

INPUT_DIR = "/app/task_file/input_data"
OUTPUT_DIR = "/app/task_file/output_data"
EXPECTED_INPUT_HASHES = {
    "requests_bucket_1.jsonl": "8b3cf1e2b06074162038064dd2c114abe308acd32cec7d365ee63ee81978f7de",
    "requests_bucket_2.jsonl": "e15e2d4c4d55f875c42a6042610d6282f6c0657c39d3e0d0f087268252525cb5",
}
THRESHOLDS = {
    1: {"cost": 3.0e11, "pad_ratio": 0.055, "p95_latency_ms": 2.1e6, "sequential_timecost": 2.7e8},
    2: {"cost": 4.8e10, "pad_ratio": 0.15, "p95_latency_ms": 2.1e5, "sequential_timecost": 3.2e7},
}


def main(upstream: Path, out: Path) -> None:
    spec = importlib.util.spec_from_file_location("cm", upstream / "tests" / "cost_model_for_tests.py")
    assert spec is not None and spec.loader is not None
    cm = importlib.util.module_from_spec(spec)
    sys.modules["cm"] = cm
    spec.loader.exec_module(cm)

    buckets = []
    for index in (1, 2):
        name = f"requests_bucket_{index}.jsonl"
        data = (upstream / "environment" / "task_file" / "input_data" / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != EXPECTED_INPUT_HASHES[name]:
            raise SystemExit(f"{name}: sha256 {digest} differs from the upstream test's hash")
        requests = [json.loads(line) for line in data.decode("utf-8").splitlines()]
        buckets.append(
            {
                "input_path": f"{INPUT_DIR}/{name}",
                "input_sha256": digest,
                "plan_path": f"{OUTPUT_DIR}/plan_b{index}.jsonl",
                "requests": [
                    {"request_id": r["request_id"], "prompt_len": r["prompt_len"], "gen_len": r["gen_len"]}
                    for r in requests
                ],
                "thresholds": THRESHOLDS[index],
            }
        )

    cases = {
        "granularity": 64,
        "heads": cm.HEADS,
        "hidden": cm.HIDDEN,
        "max_shapes": 8,
        "p95_quantile": 0.95,
        "cost_consts": asdict(cm.CostConsts()),
        "buckets": buckets,
    }
    out.write_text(json.dumps(cases, indent=1) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
