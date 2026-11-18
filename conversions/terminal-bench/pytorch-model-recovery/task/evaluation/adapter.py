"""Adapter for pytorch-model-recovery.

Runs on the baseline's own Python 3.13 and PyTorch 2.7.1, which sit outside
the scope, so the candidate cannot change them. It does what upstream's five
tests do with the candidate's files, in one process, and returns the values
their assertions compare:

1. `torch.load("/app/weights.pt")`, and reports every tensor
   (test_weights_file_unchanged).
2. `torch.jit.load("/app/model.pt")`, and reports every tensor of its
   `state_dict()` (test_model_file_exists, test_state_dicts_match).
3. `eval()`, the model's predictions on the dataset, and
   `mse_loss(predictions, tgt_sequences)`, the value `agent_loss` of
   test_model_loss.
4. `load_state_dict` with the dict from step 1 (test_model_loads_weights).

A tensor is reported by key, dtype, shape and the SHA-256 of its bytes. Its
values go in full to an Output Artifact only when it differs from the
original tensor of the same key, which `original-sha256.json` describes, so
that the Oracle can run `torch.allclose`'s comparison on them. This only
keeps the evidence small: the Oracle checks every tensor reported without
values against its own copy of the original.

The dataset is the copy in `/.securebench/evaluation`, so the candidate cannot
change it. No step runs under `torch.no_grad()`, as upstream's do not: that
switch can select another kernel for the transformer layers.

The adapter holds no expected value and compares nothing. A step that raises
ends the case with an `unable` report naming the step.
"""

import base64
import hashlib
import json
import math
import os
import sys

import torch

WEIGHTS = "/app/weights.pt"
MODEL = "/app/model.pt"
DATASET = "/.securebench/evaluation/dataset.pt"
ORIGINAL = "/.securebench/evaluation/original-sha256.json"
DUMPS = "/srv/adapter"
WEIGHTS_DUMP = "/srv/adapter/weights.b64"
MODEL_DUMP = "/srv/adapter/model.b64"
MAX_TENSORS = 1024
MAX_KEY_BYTES = 512
MAX_DIMENSIONS = 16
MAX_MESSAGE_BYTES = 4096


class Step(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def run(code, action, *arguments):
    try:
        return action(*arguments)
    except Step:
        raise
    except BaseException as error:
        raise Step(code, f"{type(error).__name__}: {error}") from None


def tensor_record(key, value, original, dump):
    if not isinstance(key, str) or len(key.encode("utf-8")) > MAX_KEY_BYTES:
        raise Step("state-dict", f"unexpected key {str(key)[:64]!r}")
    if not isinstance(value, torch.Tensor):
        raise Step("state-dict", f"{key} is a {type(value).__name__}, not a tensor")
    if value.dim() > MAX_DIMENSIONS:
        raise Step("state-dict", f"{key} has {value.dim()} dimensions")
    data = value.detach().cpu().contiguous().clone()
    size = data.numel() * data.element_size()
    raw = bytes(data.untyped_storage())[:size]
    record = {
        "key": key,
        "dtype": str(data.dtype)[:64],
        "shape": list(data.shape),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    dumped = original.get(key) != record
    if dumped:
        dump += raw
    record["dumped"] = dumped
    record["bytes"] = len(raw) if dumped else 0
    return record


def tensor_records(state, original, dump):
    if not isinstance(state, dict):
        raise Step("state-dict", f"a {type(state).__name__}, not a dict")
    items = list(state.items())
    return {
        "count": len(items),
        "tensors": [tensor_record(key, value, original, dump) for key, value in items[:MAX_TENSORS]],
    }


def model_loss(model, src, tgt):
    predictions = model(src, tgt)
    loss = torch.nn.functional.mse_loss(predictions, tgt)
    if not isinstance(loss, torch.Tensor) or loss.numel() != 1 or loss.is_complex():
        raise Step("loss", "mse_loss did not return one real number")
    value = float(loss.item())
    if math.isfinite(value):
        return {"value": value, "kind": "finite"}
    kind = "nan" if math.isnan(value) else ("inf" if value > 0 else "-inf")
    return {"value": 0.0, "kind": kind}


def write_dump(path, dump):
    os.makedirs(DUMPS, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(base64.b64encode(bytes(dump)))


def observe():
    dataset = torch.load(DATASET)
    src, tgt = dataset["src_sequences"], dataset["tgt_sequences"]
    with open(ORIGINAL, encoding="utf-8") as handle:
        original = {record["key"]: record for record in json.load(handle)}
    weights_dump = bytearray()
    model_dump = bytearray()
    loaded = run("weights-load", torch.load, WEIGHTS)
    weights_file = run("weights-state-dict", tensor_records, loaded, original, weights_dump)
    model = run("model-load", torch.jit.load, MODEL)
    state = run(
        "model-state-dict", lambda: tensor_records(dict(model.state_dict()), original, model_dump)
    )
    run("model-eval", model.eval)
    loss = run("forward-loss", model_loss, model, src, tgt)
    run("load-original", model.load_state_dict, loaded)
    write_dump(WEIGHTS_DUMP, weights_dump)
    write_dump(MODEL_DUMP, model_dump)
    return {"weights_file": weights_file, "model": state, "loss": loss}


def main():
    sys.stdin.buffer.read()
    try:
        response = {"observation": observe()}
    except Step as step:
        message = str(step).encode("utf-8")[:MAX_MESSAGE_BYTES].decode("utf-8", "ignore")
        response = {"unable": {"code": step.code, "message": message}}
    sys.stdout.write(json.dumps(response, allow_nan=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
