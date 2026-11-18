"""Oracle for train-fasttext.

Upstream has two tests, and both must pass. test_model_size asserts that
/app/model.bin is smaller than 150 MiB. test_accuracy loads the model with
fastText, predicts a label for each of the 40,000 reviews of the private test
set, and asserts that the fraction matching the true labels is above 0.62.

Here one case covers both. The adapter reads /app/model.bin, reports its size,
and predicts a label for every review with a reimplementation of fastText
0.9.2. The true labels are in hidden/labels.json (derived by hidden/derive.py)
and never leave the host. The judge computes the accuracy as sklearn's
accuracy_score does: matching reviews divided by all reviews.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

MAX_MODEL_SIZE = 150 * 1024 * 1024
ACCURACY_THRESHOLD = 0.62
FIELDS = {"model_bytes", "labels", "predictions"}


def plan(resources: HiddenResources, seed: int) -> Plan:
    labels = resources.read_json("labels.json")
    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) for x in labels):
        raise ValueError("hidden/labels.json must be a non-empty array of strings")
    case = Case({"reviews": len(labels)}, {"labels": labels})
    return Plan(artifact_contexts={}, cases={"accuracy": (case,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "accuracy" or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": f"unexpected evidence for check {check_id}"})
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(False, {"reason": "unable", "code": outcome.code})
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict) or not isinstance(context.get("labels"), list):
        return Judgment(False, {"reason": "malformed context"})
    expected = context["labels"]
    observed = outcome.value
    if not isinstance(observed, dict) or set(observed) != FIELDS:
        return Judgment(False, {"reason": "observation fields differ from the schema"})
    size, labels, predictions = observed["model_bytes"], observed["labels"], observed["predictions"]
    if type(size) is not int or size < 0:
        return Judgment(False, {"reason": "model size is not a size"})
    if size >= MAX_MODEL_SIZE:
        return Judgment(False, {"reason": "model too large", "model_bytes": size})
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        return Judgment(False, {"reason": "labels must be strings"})
    if len(set(labels)) != len(labels):
        return Judgment(False, {"reason": "labels are repeated"})
    if not isinstance(predictions, list) or len(predictions) != len(expected):
        return Judgment(False, {"reason": "one prediction per review is required"})
    correct = 0
    for review, (prediction, truth) in enumerate(zip(predictions, expected, strict=True)):
        if type(prediction) is not int or not -1 <= prediction < len(labels):
            return Judgment(False, {"reason": "prediction out of range", "review": review})
        if prediction == -1:
            # fastText returns no label, so upstream's `predict(text)[0][0]` raises.
            return Judgment(False, {"reason": "no prediction", "review": review})
        if labels[prediction] == truth:
            correct += 1
    accuracy = correct / len(expected)
    diagnostic: JsonValue = {
        "accuracy": accuracy,
        "correct": correct,
        "reviews": len(expected),
        "model_bytes": size,
    }
    return Judgment(accuracy > ACCURACY_THRESHOLD, diagnostic)
