"""Oracle for terminal-bench/llm-inference-batching-scheduler.

Two checks:
- `input-integrity` (artifact): the two request files the candidate must leave
  unchanged still have upstream's SHA-256 (test_input_data_integrity).
- `plans` (protocol, one case): the adapter reports every record of plan_b1.jsonl
  and plan_b2.jsonl; `judge` applies the assertions of test_generate_and_schema,
  test_solution_shape_feasibility_and_batch_consistency,
  test_solution_coverage_no_duplicates and test_performance_thresholds, computing
  the metrics with a transliteration of upstream's tests/cost_model_for_tests.py
  over the hidden copy of the requests. test_output_files_exist is the adapter
  reporting `unable` when a plan file cannot be read.

All numbers the verdict depends on (requests, hashes, thresholds, shape
constants, cost constants) are in hidden/cases.json.
"""

import math
from collections import defaultdict

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    buckets = cases["buckets"]
    integrity = {"inputs": [{"path": b["input_path"], "sha256": b["input_sha256"]} for b in buckets]}
    challenge = {"plan_paths": [b["plan_path"] for b in buckets]}
    return Plan(
        artifact_contexts={"input-integrity": integrity},
        cases={"plans": (Case(challenge, cases),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "input-integrity" and isinstance(evidence, ArtifactEvidence):
        return _judge_integrity(context, evidence)
    if check_id == "plans" and isinstance(evidence, CaseEvidence):
        return _judge_plans(context, evidence)
    return Judgment(False, {"reason": f"unexpected evidence for check {check_id!r}"})


def _judge_integrity(context, evidence: ArtifactEvidence) -> Judgment:
    found = {item.path: item for item in evidence.files}
    for expected in context["inputs"]:
        item = found.get(expected["path"])
        if item is None:
            return Judgment(False, {"reason": f"no evidence for {expected['path']}"})
        if item.status is not FileStatus.PRESENT:
            return Judgment(False, {"reason": f"{expected['path']} is {item.status.value}"})
        # SecureBench writes file digests as "sha256:<hex>"; upstream's are bare hex.
        if item.sha256 != "sha256:" + expected["sha256"]:
            return Judgment(False, {"reason": f"{expected['path']} has been modified"})
    return Judgment(True, None)


class Failed(Exception):
    pass


def _judge_plans(context, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter did not report the plans"})
    plans = evidence.outcome.value.get("plans") if isinstance(evidence.outcome.value, dict) else None
    buckets = context["buckets"]
    if not isinstance(plans, list) or len(plans) != len(buckets):
        return Judgment(False, {"reason": "the observation does not hold one plan per bucket"})
    try:
        all_shapes = set()
        metrics = []
        for number, (bucket, records) in enumerate(zip(buckets, plans), start=1):
            where = f"bucket {number}"
            if not isinstance(records, list):
                raise Failed(f"{where}: plan is not a list")
            entries = [_entry(record, where) for record in records]
            requests = {r["request_id"]: r for r in bucket["requests"]}
            all_shapes |= _check_plan(context, requests, entries, where)
            values = _plan_metrics(context, requests, entries)
            metrics.append(values)
            for name, limit in bucket["thresholds"].items():
                if not values[name] <= limit:
                    raise Failed(f"{where}: {name} {values[name]} > {limit}")
        # test_performance_thresholds: joint cap across both plans.
        if len(all_shapes) > context["max_shapes"]:
            raise Failed(f"combined unique shapes {len(all_shapes)} exceed cap {context['max_shapes']}")
    except Failed as failure:
        return Judgment(False, {"reason": str(failure)})
    return Judgment(True, {"metrics": metrics})


def _entry(record, where):
    """One plan record as (request_id, batch key, shape) after strict type checks.

    The batch key mirrors the Python value upstream uses as a dict key: the
    string itself, or the number (the adapter reports booleans as 0 and 1).
    The shape is compared whole within a batch, as upstream compares the dicts,
    so it includes the other keys in their canonical JSON text.
    """
    if not isinstance(record, dict):
        raise Failed(f"{where}: a record is not an object")
    has_text = isinstance(record.get("batch_text"), str)
    has_number = isinstance(record.get("batch_number"), int | float) and not isinstance(
        record.get("batch_number"), bool
    )
    if has_text == has_number:
        raise Failed(f"{where}: a record has no single batch_id")
    batch = record["batch_text"] if has_text else record["batch_number"]
    fields = ("seq_align", "heads_align", "hidden_align")
    for name in fields:
        if not isinstance(record.get(name), int) or isinstance(record.get(name), bool):
            raise Failed(f"{where}: {name} is not an integer")
    if not isinstance(record.get("request_id"), str) or not isinstance(record.get("shape_extra"), str):
        raise Failed(f"{where}: a record misses request_id or shape_extra")
    shape = (record["seq_align"], record["heads_align"], record["hidden_align"], record["shape_extra"])
    return record["request_id"], batch, shape


def _align(x: int, g: int) -> int:
    return ((x + g - 1) // g) * g


def _check_plan(context, requests, entries, where):
    """The assertions of the schema, coverage and feasibility tests for one bucket."""
    gran = context["granularity"]
    plan_ids = [request_id for request_id, _, _ in entries]
    # test_generate_and_schema and test_solution_coverage_no_duplicates.
    if set(plan_ids) != set(requests):
        raise Failed(f"{where}: request_id mismatch: req={len(requests)} plan={len(set(plan_ids))}")
    if len(plan_ids) != len(set(plan_ids)):
        raise Failed(f"{where}: duplicate request_ids")
    shapes = set()
    for request_id, _, shape in entries:
        seq_align, heads_align, hidden_align, _ = shape
        if seq_align % gran != 0:
            raise Failed(f"{where}: seq_align {seq_align} not aligned to granularity {gran}")
        if heads_align != context["heads"]:
            raise Failed(f"{where}: heads_align {heads_align} != expected {context['heads']}")
        if hidden_align != context["hidden"]:
            raise Failed(f"{where}: hidden_align {hidden_align} != expected {context['hidden']}")
        # test_solution_shape_feasibility_and_batch_consistency, per record.
        if seq_align < _align(requests[request_id]["prompt_len"], gran):
            raise Failed(f"{where}: {request_id} seq_align {seq_align} below its aligned prompt")
        shapes.add((seq_align, heads_align, hidden_align))
    if len(shapes) > context["max_shapes"]:
        raise Failed(f"{where}: uses {len(shapes)} shapes, exceeds limit of {context['max_shapes']}")
    # Per batch: identical shapes (the per-record check already covers the
    # longest aligned prompt).
    first_shape = {}
    for _, batch, shape in entries:
        if first_shape.setdefault(batch, shape) != shape:
            raise Failed(f"{where}: batch {batch!r} mixes shapes")
    # The cost model sorts the batch ids; Python cannot order a string against a
    # number, so upstream's test raises TypeError on a plan that mixes them.
    kinds = {isinstance(batch, str) for batch in first_shape}
    if len(kinds) > 1:
        raise Failed(f"{where}: batch_ids mix strings and numbers, which upstream cannot sort")
    return shapes


def _plan_metrics(context, requests, entries):
    """CostModel(granularity=64).plan_metrics from tests/cost_model_for_tests.py.

    Transliterated statement by statement, in the same order of floating-point
    operations, so the metrics are bit-identical to upstream's.
    """
    c = context["cost_consts"]
    g = context["granularity"]
    hidden = context["hidden"]

    def prefill_cost(prompt_len):
        s = _align(prompt_len, g)
        return c["Kp_attn"] * (s**2) + c["Kp_mlp"] * (s * hidden)

    def prefill_lat(prompt_len):
        s = _align(prompt_len, g)
        return c["Tp_attn"] * (s**2) + c["Tp_mlp"] * (s * hidden)

    def sum_sq_arith(a, n):
        return n * (a * a) + a * n * (n - 1) + (n * (n - 1) * (2 * n - 1)) // 6

    def batch_metrics(reqs_list):
        s_max = max(_align(r["prompt_len"], g) for r in reqs_list)
        g_max = max(r["gen_len"] for r in reqs_list)
        cost_prefill = sum(prefill_cost(r["prompt_len"]) for r in reqs_list)
        lat_prefill = [prefill_lat(r["prompt_len"]) for r in reqs_list]
        a_cost, b_cost = c["Kd_attn"], c["Kd_mlp"] * hidden

        def sum_cost_for_g(n):
            a = s_max
            sum_sq = sum_sq_arith(a, n)
            sum_lin = n * a + n * (n - 1) / 2
            return a_cost * sum_sq + b_cost * sum_lin

        cost_decode = len(reqs_list) * sum_cost_for_g(g_max)

        def sum_lat_for_g(n):
            a = s_max
            a_lat, b_lat = c["Td_attn"], c["Td_mlp"] * hidden
            sum_sq = sum_sq_arith(a, n)
            sum_lin = n * a + n * (n - 1) / 2
            return a_lat * sum_sq + b_lat * sum_lin

        lat_decode_per_req = sum_lat_for_g(g_max)
        latencies = [lp + lat_decode_per_req for lp in lat_prefill]
        pad_prefill = sum(_align(r["prompt_len"], g) - r["prompt_len"] for r in reqs_list)
        pad_decode = sum(g_max - r["gen_len"] for r in reqs_list)
        real_tokens = sum(r["prompt_len"] + r["gen_len"] for r in reqs_list)
        return {
            "cost": cost_prefill + cost_decode,
            "pad_tokens": pad_prefill + pad_decode,
            "real_tokens": real_tokens,
            "latencies": latencies,
        }

    batches = defaultdict(list)
    batch_shape = {}
    for request_id, batch, shape in entries:
        batches[batch].append(requests[request_id])
        batch_shape[batch] = (shape[0], shape[1], shape[2])
    metrics_by_batch = {batch: batch_metrics(rs) for batch, rs in batches.items()}

    totals = {"cost": 0.0, "pad_tokens": 0, "real_tokens": 0, "latencies": []}
    for m in metrics_by_batch.values():
        for k in ("cost", "pad_tokens", "real_tokens"):
            totals[k] += m[k]

    lat_by_batch = {}
    for batch, m in metrics_by_batch.items():
        lats = list(m["latencies"])
        if lats:
            lats = [x + c["Tbatch_overhead_ms"] for x in lats]
        lat_by_batch[batch] = lats

    unique_shapes = set(batch_shape.values()) if batch_shape else set()
    compile_cost = 0.0
    for s, _, _ in unique_shapes:
        if s <= 0:
            continue
        compile_cost += c["Kshape_attn"] * (s**2) + c["Kshape_mlp"] * (s * hidden)
    totals["cost"] += compile_cost

    shape_to_batches = defaultdict(list)
    for batch, shp in batch_shape.items():
        shape_to_batches[shp].append(batch)
    for b_list in shape_to_batches.values():
        b_list.sort()
        lats = lat_by_batch.get(b_list[0], [])
        if lats and c["Tshape_compile_ms"] > 0:
            lats[0] += c["Tshape_compile_ms"]

    for batch in sorted(lat_by_batch):
        totals["latencies"].extend(lat_by_batch[batch])

    totals["cost"] += c["Kbatch_overhead_cost"] * len(metrics_by_batch)

    sequential_timecost = 0.0
    for batch in sorted(lat_by_batch):
        if lat_by_batch[batch]:
            sequential_timecost += max(lat_by_batch[batch])

    lats_sorted = sorted(totals["latencies"])
    if lats_sorted:
        p = context["p95_quantile"]
        k = max(0, min(len(lats_sorted) - 1, int(math.ceil(p * len(lats_sorted)) - 1)))
        p95 = lats_sorted[k]
    else:
        p95 = 0.0
    return {
        "cost": totals["cost"],
        "pad_ratio": totals["pad_tokens"] / max(1, totals["real_tokens"]),
        "p95_latency_ms": p95,
        "sequential_timecost": sequential_timecost,
    }
