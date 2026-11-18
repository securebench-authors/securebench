"""Oracle for pytorch-model-cli.

Upstream's tests check that /app/weights.json, /app/cli_tool and
/app/prediction.txt exist, that prediction.txt holds the expected digit after
`strip()`, that `/app/cli_tool /app/weights.json /app/image.png` prints it, and
that the tool prints upstream's TRUE_PRED_CLASSES for the first 50 MNIST test
images.

Every expected value and every image is in `cases.json` and `mnist/`; this
file holds only how upstream's tests compare.
"""

from base64 import b64encode

from securebench.core.errors import Rejected
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

# The adapter shows at most this many bytes of each run's standard output.
SHOWN = 1024


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or set(data) != {"prediction", "cli-tool"}:
        raise Rejected("cases.json must hold prediction and cli-tool")
    prediction = data["prediction"]
    if not isinstance(prediction, dict) or not isinstance(prediction.get("content"), str):
        raise Rejected("cases.json prediction must hold a content string")
    entries = data["cli-tool"]
    if not isinstance(entries, list) or not entries:
        raise Rejected("cases.json cli-tool must hold at least one case")
    cases = tuple(_case(resources, entry) for entry in entries)
    return Plan(
        artifact_contexts={"weights-file": None, "cli-tool-file": None, "prediction": prediction},
        cases={"cli-tool": cases},
    )


def _case(resources: HiddenResources, entry: JsonValue) -> Case:
    if not isinstance(entry, dict) or set(entry) != {"images", "run", "image_png", "predictions"}:
        raise Rejected("a cli-tool case must hold images, run, image_png and predictions")
    paths = entry["images"]
    run = entry["run"]
    predictions = entry["predictions"]
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise Rejected("a cli-tool case's images must be paths")
    if not isinstance(run, int) or not isinstance(predictions, list) or len(predictions) != run:
        raise Rejected("a cli-tool case must have one prediction per run image")
    if run > len(paths):
        raise Rejected("a cli-tool case runs more images than it writes")
    if not isinstance(entry["image_png"], str):
        raise Rejected("a cli-tool case's image_png must be a string")
    images: list[JsonValue] = [b64encode(resources.read(path)).decode("ascii") for path in paths]
    return Case(
        {"images": images, "run": run},
        {"image_png": entry["image_png"], "predictions": predictions},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        found = evidence.files[0]
        if check_id == "prediction":
            return _prediction_file(context, found.status, found.value)
        # Upstream's Path.exists(): anything at the path counts.
        if found.status is FileStatus.ABSENT:
            return Judgment(False, {"reason": f"{found.path} does not exist"})
        return Judgment(True, None)
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    expected = context["predictions"]
    image_png = context["image_png"]
    runs = observation["images"]
    if not isinstance(expected, list) or not isinstance(runs, list) or len(runs) != len(expected):
        return Judgment(False, {"reason": "wrong number of runs"})
    # test_cli_tool_executable: stdout.strip() equals the expected digit.
    text = _stdout(observation["image_png"])
    if text is None or text.strip() != image_png:
        diagnostic = {
            "reason": "image.png is not predicted as expected",
            "run": observation["image_png"],
        }
        return Judgment(False, diagnostic)
    # test_cli_tool_output: int(stdout.strip()) == TRUE_PRED_CLASSES[i].
    for index, (run, prediction) in enumerate(zip(runs, expected, strict=True)):
        text = _stdout(run)
        if text is None or _as_int(text.strip()) != prediction:
            return Judgment(False, {"image": index, "expected": prediction, "run": run})
    return Judgment(True, None)


def _prediction_file(context: JsonValue, status: FileStatus, value: Text | JsonValue) -> Judgment:
    # test_prediction_file_exists and test_prediction_file_content: open() decodes
    # strictly, and the content must be the expected digit after strip().
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    if status is not FileStatus.PRESENT or not isinstance(value, Text):
        return Judgment(False, {"reason": f"prediction.txt is {status.value}"})
    if value.text.strip() != context["content"]:
        diagnostic = {
            "reason": "prediction.txt does not hold the expected digit",
            "content": value.text[:256],
        }
        return Judgment(False, diagnostic)
    return Judgment(True, None)


def _stdout(run: JsonValue) -> str | None:
    """The run's whole standard output, or None if it timed out, was not valid
    UTF-8 (upstream's text=True decodes strictly) or was not shown in full."""
    if not isinstance(run, dict):
        return None
    stdout = run["stdout"]
    size = run["stdout_bytes"]
    if run["ending"] != "exited" or run["utf8"] is not True:
        return None
    if not isinstance(stdout, str) or not isinstance(size, int):
        return None
    if size > SHOWN or size != len(stdout.encode("utf-8")):
        return None
    return stdout


def _as_int(text: str) -> int | None:
    """Upstream's int(text), the same conversion on at most SHOWN bytes."""
    try:
        return int(text)
    except ValueError:
        return None
