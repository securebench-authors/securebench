"""Oracle for pytorch-model-recovery.

Upstream's five tests, judged on what the adapter reports from one Evaluation:

- test_weights_file_unchanged: /app/weights.pt has the ground truth's keys,
  and every tensor is `torch.allclose` to the ground truth.
- test_model_file_exists and test_model_loads_weights: /app/model.pt loads with
  `torch.jit.load`, and `load_state_dict` accepts /app/weights.pt. The adapter
  reports a failure of either as `unable`, which fails the case before it
  reaches the judge.
- test_state_dicts_match: the model's state dict has /app/weights.pt's keys,
  and every tensor whose key does not contain "output_layer" is
  `torch.allclose` to /app/weights.pt's.
- test_model_loss: the model's `mse_loss` on the dataset, computed by the
  adapter as upstream computes it, is below the reference model's
  (`baseline_loss` in `expected.json`, from `derive.py`).

`torch.allclose` is reimplemented here in float32 arithmetic, as PyTorch
computes it; `conformance.py` checks it against PyTorch near its threshold.
"""

import base64
import binascii
import hashlib
import math
import struct
from dataclasses import dataclass

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

FROZEN_EXCEPT = "output_layer"
FLOAT32 = "torch.float32"
WEIGHTS_DUMP = "/srv/adapter/weights.b64"
MODEL_DUMP = "/srv/adapter/model.b64"


def _float32(value: float) -> float:
    """`value` rounded to float32, as PyTorch stores the result of a float32 operation."""
    try:
        rounded: float = struct.unpack("<f", struct.pack("<f", value))[0]
        return rounded
    except OverflowError:
        return math.copysign(math.inf, value)


# torch.allclose's defaults, which upstream's tests use. PyTorch casts them to
# the tensors' dtype before computing.
RTOL = _float32(1e-05)
ATOL = _float32(1e-08)


@dataclass(frozen=True)
class Tensor:
    """A tensor as reported, with its bytes when the adapter sent them."""

    dtype: str
    shape: list[int]
    sha256: str
    raw: bytes | None


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not isinstance(expected["tensors"], list):
        raise ValueError("expected.json is malformed")
    values = resources.read("weights.f32")
    sizes = 0
    for record in expected["tensors"]:
        if not isinstance(record, dict) or not isinstance(record["shape"], list):
            raise ValueError("expected.json is malformed")
        sizes += 4 * math.prod(size for size in record["shape"] if isinstance(size, int))
    if sizes != len(values) or not isinstance(expected["baseline_loss"], float):
        raise ValueError("weights.f32 does not match expected.json")
    context: JsonValue = {
        "tensors": expected["tensors"],
        "values": base64.b64encode(values).decode("ascii"),
        "baseline_loss": expected["baseline_loss"],
    }
    return Plan(artifact_contexts={}, cases={"model": (Case({}, context),)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "malformed observation"})

    dumps: dict[str, bytes] = {}
    for item in evidence.output_artifacts:
        if item.status is not FileStatus.PRESENT or not isinstance(item.value, Text):
            return Judgment(False, {"reason": f"{item.path} is {item.status.value}"})
        try:
            dumps[item.path] = base64.b64decode(item.value.text, validate=True)
        except (binascii.Error, ValueError):
            return Judgment(False, {"reason": f"{item.path} is not base64"})
    if set(dumps) != {WEIGHTS_DUMP, MODEL_DUMP}:
        return Judgment(False, {"reason": "missing tensor dumps"})

    truth = _truth(context)

    # test_weights_file_unchanged
    weights = _reported(observation["weights_file"], dumps[WEIGHTS_DUMP])
    if isinstance(weights, str):
        return Judgment(False, {"reason": f"/app/weights.pt: {weights}"})
    if set(weights) != set(truth):
        return Judgment(False, {"reason": "/app/weights.pt keys differ", **_key_difference(weights, truth)})
    for key, true in truth.items():
        problem = _allclose(weights[key], true, truth[key])
        if problem is not None:
            return Judgment(False, {"reason": f"/app/weights.pt {key}: {problem}"})

    # test_state_dicts_match: the model against /app/weights.pt, as upstream.
    model = _reported(observation["model"], dumps[MODEL_DUMP])
    if isinstance(model, str):
        return Judgment(False, {"reason": f"model state dict: {model}"})
    if set(model) != set(weights):
        return Judgment(False, {"reason": "model state dict keys differ", **_key_difference(model, weights)})
    for key, reported in model.items():
        if FROZEN_EXCEPT in key:
            continue
        problem = _allclose(reported, weights[key], truth[key])
        if problem is not None:
            return Judgment(False, {"reason": f"model {key}: {problem}"})

    # test_model_loss: agent_loss < true_loss.
    loss = observation["loss"]
    baseline = context["baseline_loss"]
    if not isinstance(loss, dict) or not isinstance(baseline, float):
        return Judgment(False, {"reason": "malformed loss"})
    kind = loss["kind"]
    value = loss["value"]
    if kind == "finite" and isinstance(value, (int, float)):
        below = value < baseline
    else:
        below = kind == "-inf"
    losses: dict[str, JsonValue] = {"model": value if kind == "finite" else kind, "baseline": baseline}
    if not below:
        return Judgment(False, {"reason": "loss not below the original model's loss", "losses": losses})
    return Judgment(True, {"losses": losses})


def _truth(context: dict[str, JsonValue]) -> dict[str, Tensor]:
    tensors = context["tensors"]
    encoded = context["values"]
    if not isinstance(tensors, list) or not isinstance(encoded, str):
        raise ValueError("malformed context")
    values = base64.b64decode(encoded)
    truth: dict[str, Tensor] = {}
    offset = 0
    for record in tensors:
        if not isinstance(record, dict):
            raise ValueError("malformed context")
        key, dtype, shape, sha256 = record["key"], record["dtype"], record["shape"], record["sha256"]
        if not isinstance(key, str) or not isinstance(dtype, str) or not isinstance(sha256, str):
            raise ValueError("malformed context")
        if not isinstance(shape, list) or not all(isinstance(size, int) for size in shape):
            raise ValueError("malformed context")
        sizes = [size for size in shape if isinstance(size, int)]
        size = 4 * math.prod(sizes)
        truth[key] = Tensor(dtype, sizes, sha256, values[offset : offset + size])
        offset += size
    return truth


def _reported(reported: JsonValue, dump: bytes) -> dict[str, Tensor] | str:
    """The reported state dict by key, or why it cannot be read."""
    if not isinstance(reported, dict):
        return "malformed"
    count = reported["count"]
    tensors = reported["tensors"]
    if not isinstance(tensors, list) or count != len(tensors):
        return f"{count} tensors, {len(tensors) if isinstance(tensors, list) else 'none'} reported"
    result: dict[str, Tensor] = {}
    offset = 0
    for record in tensors:
        if not isinstance(record, dict):
            return "malformed"
        key, dtype, shape, sha256 = record["key"], record["dtype"], record["shape"], record["sha256"]
        dumped, size = record["dumped"], record["bytes"]
        if not isinstance(key, str) or not isinstance(dtype, str) or not isinstance(sha256, str):
            return "malformed"
        if not isinstance(shape, list) or not all(isinstance(item, int) for item in shape):
            return "malformed"
        if not isinstance(dumped, bool) or not isinstance(size, int):
            return "malformed"
        if key in result:
            return f"duplicate key {key}"
        raw: bytes | None = None
        if dumped:
            raw = dump[offset : offset + size]
            offset += size
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha256:
                return f"{key}: dumped bytes do not match the record"
        elif size != 0:
            return "malformed"
        result[key] = Tensor(dtype, [item for item in shape if isinstance(item, int)], sha256, raw)
    if offset != len(dump):
        return "dump has bytes no record accounts for"
    return result


def _key_difference(seen: dict[str, Tensor], expected: dict[str, Tensor]) -> dict[str, JsonValue]:
    missing: list[JsonValue] = list(sorted(set(expected) - set(seen))[:16])
    unexpected: list[JsonValue] = list(sorted(set(seen) - set(expected))[:16])
    return {"missing": missing, "unexpected": unexpected}


def _values(tensor: Tensor, original: Tensor) -> tuple[float, ...] | None:
    """A float32 tensor's values. A tensor sent without its bytes is, by the
    adapter's rule, the original tensor of its key; anything else fails."""
    if tensor.raw is None:
        if (tensor.dtype, tensor.shape, tensor.sha256) != (original.dtype, original.shape, original.sha256):
            return None
        raw = original.raw
    else:
        raw = tensor.raw
    if raw is None or tensor.dtype != FLOAT32 or len(raw) != 4 * math.prod(tensor.shape):
        return None
    values: tuple[float, ...] = struct.unpack(f"<{len(raw) // 4}f", raw)
    return values


def _allclose(tensor: Tensor, other: Tensor, original: Tensor) -> str | None:
    """None when `torch.allclose(tensor, other)` holds; otherwise why not.

    `original` is the ground-truth tensor of the same key, which supplies the
    values of a tensor reported without its bytes.
    """
    # torch.allclose raises on different dtypes. Shapes must be equal too:
    # test_model_loss loads /app/weights.pt into the reference architecture and
    # test_model_loads_weights loads it into the model, and load_state_dict
    # raises on a shape that differs.
    if tensor.dtype != other.dtype:
        return f"dtype {tensor.dtype}, not {other.dtype}"
    if tensor.shape != other.shape:
        return f"shape {tensor.shape}, not {other.shape}"
    candidate = _values(tensor, original)
    reference = _values(other, original)
    if candidate is None or reference is None:
        return "values not reported"
    if tensor.sha256 == other.sha256 and all(math.isfinite(value) for value in reference):
        return None
    flags = _isclose(candidate, reference)
    if all(flags):
        return None
    return f"{flags.count(False)} of {len(flags)} values not close"


def _round32(values: list[float]) -> list[float]:
    try:
        return list(struct.unpack(f"<{len(values)}f", struct.pack(f"<{len(values)}f", *values)))
    except OverflowError:
        return [_float32(value) for value in values]


def _isclose(a: tuple[float, ...], b: tuple[float, ...]) -> list[bool]:
    """`torch.isclose(a, b)` with default tolerances, for float32 values.

    PyTorch computes `|a - b| <= atol + |rtol * b|` in float32, one rounded
    operation at a time, and also counts equal values (such as equal
    infinities) as close. Each operation here is done in float64 and rounded
    to float32; for +, - and * that gives the same result as float32
    arithmetic, because float64 has more than twice float32's precision.
    """
    allowed = _round32([ATOL + abs(value) for value in _round32([RTOL * value for value in b])])
    actual = _round32([x - y for x, y in zip(a, b, strict=True)])
    return [
        x == y or (math.isfinite(error) and abs(error) <= limit)
        for x, y, error, limit in zip(a, b, actual, allowed, strict=True)
    ]
