# openssl-selfsigned-cert

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/openssl-selfsigned-cert

## The conversion in short

The baseline is `python:3.13-slim-bookworm` with openssl 3.0.17 and an empty `/app`. The agent must make a 2048-bit RSA key, a self-signed certificate, a combined PEM file and a verification file in `/app/ssl/`, and write `/app/check_cert.py`. Upstream has six tests in `tests/test_outputs.py`, run by pytest with Python 3.13 that `uv` installs at grading time. No step needs the network, so every check runs on the baseline's own tools: openssl at `/usr/bin/openssl` and Python 3.13.7 at `/usr/local/bin/python`, both outside the scope.

The pack has three artifact checks and two protocol checks, each protocol check with one case, as upstream runs each test once. Every case runs in a fresh Evaluation environment. The `openssl` check runs only the baseline's openssl, so no candidate code runs before the evidence for the key and the certificate is taken. The adapter (`evaluation/adapter.py`, standard-library Python on the stock interpreter) reports each command's ending, exit status, standard output (up to 128 KiB for openssl, 64 KiB for the script), the full output length, and whether standard output and standard error were valid UTF-8. It compares nothing. Both challenges are empty, because upstream's commands take no input. Every expected value is a literal of the upstream tests and lives in `hidden/cases.json`; `hidden/oracle.py` holds only how to compare.

## How upstream's tests map to checks

One row per assertion of `tests/test_outputs.py`. Upstream has no regression tests.

| Upstream assertion (`tests/test_outputs.py`) | Check and case | Expected value (`hidden/cases.json`) |
|---|---|---|
| `test_directory_structure`: `os.path.exists("/app/ssl")` (line 11) | `ssl-directory`: the listing of `/app/ssl` is `present` | none |
| `test_directory_structure`: `os.path.isdir("/app/ssl")` (line 12) | `ssl-directory`: the same listing (a file reads `not_directory`) | none |
| `test_key_file`: `os.path.exists("/app/ssl/server.key")` (line 18) | `openssl`, run `key_text`: `openssl rsa` on a missing file prints nothing, so the next row fails | none |
| `test_key_file`: `st_mode & 0o777 <= 0o600` (line 22) | `openssl`, field `key_mode`: the adapter reads `os.stat` of the key, following links as upstream does, and a key with the owner execute bit fails. Fidelity change "Key mode" | none |
| `test_key_file`: `"2048 bit"` in `openssl rsa -in server.key -text -noout` (line 31) | `openssl`, run `key_text`: the same substring | `openssl.expected.key_text` |
| `test_certificate_file`: `os.path.exists("/app/ssl/server.crt")` (line 37) | `openssl`, run `certificate_text`: `openssl x509` on a missing file prints nothing, so the next row fails | none |
| `test_certificate_file`: `"dev-internal.company.local"` in `openssl x509 -text -noout` (line 47) | `openssl`, run `certificate_text`: the same substring | `openssl.expected.common_name` |
| `test_certificate_file`: `"devops team"` in that output's lowercase (line 52) | `openssl`, run `certificate_text`: the same | `openssl.expected.organization` |
| `test_certificate_file`: `notBefore=(.*)` and `notAfter=(.*)` both found in `openssl x509 -noout -dates` (line 70) | `openssl`, run `certificate_dates`: `_field`, hand-written (differential test below) | none |
| `test_certificate_file`: both parse with `strptime("%b %d %H:%M:%S %Y %Z")` (lines 75, 76) | `openssl`, run `certificate_dates`: `_time`, hand-written (differential test below) | none |
| `test_certificate_file`: `(not_after - not_before).days == 365` (line 79) | `openssl`, run `certificate_dates`: the same floor division | `openssl.expected.days` |
| `test_combined_pem_file`: `os.path.exists("/app/ssl/server.pem")` (line 87) | `combined-pem`: the file is `present` | none |
| `test_combined_pem_file`: `"PRIVATE KEY"` in the file (line 93) | `combined-pem`: the same substring | `combined-pem.markers[0]` |
| `test_combined_pem_file`: `"CERTIFICATE"` in the file (line 94) | `combined-pem`: the same substring | `combined-pem.markers[1]` |
| `test_combined_pem_file`: `openssl x509 -in server.pem -text -noout` exits 0 (line 102) | `openssl`, run `pem_certificate`: exit status 0 | none |
| `test_verification_file`: `os.path.exists("/app/ssl/verification.txt")` (line 108) | `verification-file`: the file is `present` | none |
| `test_verification_file`: `"dev-internal.company.local"` in its lowercase (line 114) | `verification-file`: the same | `verification-file.common_name` |
| `test_verification_file`: `"devops team"` in its lowercase (line 117) | `verification-file`: the same | `verification-file.organization` |
| `test_verification_file`: `\d{4}-\d{2}-\d{2}` or the OpenSSL date pattern found (lines 121 to 129) | `verification-file`: `_ymd` or `_openssl_date`, hand-written (differential test below) | none: a format |
| `test_verification_file`: `[0-9a-f]{2}(:[0-9a-f]{2}){31}` found in its lowercase (line 134) | `verification-file`: `_fingerprint`, hand-written (differential test below) | none: a format |
| `test_python_verification_script`: `os.path.exists("/app/check_cert.py")` (line 142) | `check-script`, its one case: `python` on a missing script exits 2, so the next row fails | none |
| `test_python_verification_script`: `python /app/check_cert.py` exits 0 (line 146) | `check-script`: exit status 0 | none |
| `test_python_verification_script`: `"Certificate verification successful"` in its standard output (line 149) | `check-script`: the same substring | `check-script.expected.success` |
| `test_python_verification_script`: `"dev-internal.company.local"` in its standard output (line 152) | `check-script`: the same substring | `check-script.expected.common_name` |
| `test_python_verification_script`: `\d{4}-\d{2}-\d{2}` found in its standard output (line 158) | `check-script`: `_ymd`, hand-written (differential test below) | none: a format |
| Every `subprocess.run(..., capture_output=True, text=True)` decodes both streams strictly as UTF-8 (the verifier sets no locale, so Python 3.13 runs in UTF-8 mode); invalid bytes raise and fail the test | Every run must report `stdout_utf8` and `stderr_utf8` true, and its output shown in full | none |

## Differential test of the hand-written matchers

The judge may not use regular expressions or `strptime`, which upstream's tests use, because the Oracle runs on the host and must stay bounded and simple. `hidden/differential.py` applies upstream's expressions, copied from the tests, and the Oracle's replacements to the same 125 inputs, and its docstring gives the commands. The native side ran on the baseline's Python 3.13.7, with no TZ and no locale, as in the verifier's container. The Oracle side ran on the framework's Python 3.12. Both sides give the same result on every input; we re-ran it after the remediation, with the same result. The inputs are weighted toward the boundaries:

- `-dates` output (57 inputs): exactly 365 days; 365 days minus 1 s; 365 days plus 23:59:59; 366 and 364 days; spans across 29 February, the century years 2000 and 2100, the years 0001 and 9999; year 0000, 3 and 5 digits; 29 February in a non-leap year; days 00, 32, zero-padded and 3 digits; single-digit clock fields; hour 24, minute 60, seconds 60 and 61, 3-digit seconds, fractional seconds; zones UTC, gmt, none, PST and Z; month names in other cases, full or as `Sept`, and U+017F in `Sep`; tabs, U+00A0, U+3000, U+0085 and `\x1c` to `\x1f` between fields; leading and trailing whitespace; a missing space; an extra token; `Bad time value`; `notAfter` missing, first, or repeated; CRLF and lone CR; Arabic-Indic digits in each field.
- Verification files (35 inputs): the reference's file; ISO dates only; no date, no fingerprint, no Common Name, no Organization; uppercase subject; double space in the Organization; ISO dates in Arabic-Indic or fullwidth digits, with slashes, a 2-digit year, inside longer digit runs, at the start and at the end; OpenSSL dates with a 1- or 3-digit day, a 1-digit hour, a 3- or 5-digit year, an uppercase, lowercase, accented or arbitrary month, no space after the month, newlines, `\x1c` to `\x1f`, U+00A0 or a zero-width space between fields, Arabic-Indic digits, dots in the clock, a letter before the month, and at the very end.
- Script output (15 inputs) and fingerprints (18 inputs): other date orders and separators (en dash, fullwidth hyphen), Unicode digits; 31, 32 and 33 hex pairs, uppercase, SHA-1, a space or newline inside, dashes, no separator, a non-hex letter, a fullwidth colon or fullwidth hex, the Kelvin sign, U+0130 before it, a broken run followed by a good one.

The matchers are linear in their input. On adversarial 1 MiB texts (repeated hex pairs, dashes, month-like words, long whitespace runs, digits, near-miss fingerprints), each runs in under 0.6 s (measured before the remediation, which did not change the matchers).

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Key mode (more lenient, with a stricter corner).** Upstream asserts `os.stat("/app/ssl/server.key").st_mode & 0o777 <= 0o600` (line 22). Replay keeps only the executable bit of each file, so no conversion can tell 0600 from 0644. In the `openssl` check, where no candidate code runs, the adapter reports `os.stat` of the key, which follows links as upstream's does, and the Oracle fails a key with the owner execute bit. Upstream also fails it for every mode from 0700 up. A link to an owner-executable file fails too (`attack-key-symlink-executable`). A key without that bit but with group or other permissions (0644, 0640, 0604 and so on) fails upstream and passes here: the reference followed by `chmod 644 /app/ssl/server.key` passes SecureBench (run `sha256:181ef497...`, on the pack before remediation, which judged the key the same way). It is not a committed candidate, because a committed attack must fail SecureBench and a mutant must match native. Upstream compares the mode as a number, so modes with the owner execute bit and owner permissions below read-write (0100 to 0577, for example 0500) pass upstream and fail here; no plausible solution gives a private key such a mode. Replay also writes the key as 0644 into every Evaluation, where the agent left 0600, so a correct `check_cert.py` that checks the key's mode before reporting success would fail. The `check-script` adapter therefore sets the key to 0600, following a link, before it runs the script: 0600 is the one mode the instructions require, and a key with the owner execute bit already fails the `openssl` check. The first review's script, the reference with `check_cert.py` returning without success unless the key is 0600, passed (run `sha256:a851f6dc...`, before remediation). The coordinator chose to convert the task with this change rather than exclude it as `privileged-environment`; the reviewer and the maintainer judge whether it is acceptable.
- **Date and pattern matching (equivalent).** Hand-written replacements of upstream's regular expressions and `strptime`, with the same result on all 125 inputs of the differential test. The `-dates` output comes from openssl, which prints a fixed format.
- **Python for the script (stricter and more lenient, both negligible).** Upstream runs `python` from the environment `uvx` builds, whose base interpreter is the baseline's own Python 3.13.7, without the system site-packages. We checked it by running test.sh's install steps and `uvx -p 3.13 -w pytest==8.4.1` in the baseline with network: `python` on the test's `PATH` is uv's environment, with `sys.base_prefix` `/usr/local`, and a `cryptography` installed beforehand with the system `pip` cannot be imported from it. Here the adapter runs `/usr/local/bin/python`, the same interpreter, with the system site-packages, which hold only pip. A package installed into the system site-packages is outside the scope here and invisible to upstream's run, so a script that needs one fails both. The two interpreters do not see the same packages, though. The review ran test.sh's install steps and the full `uvx -p 3.13 -w pytest==8.4.1 -w pytest-json-ctrf==0.3.5 pytest` command in the baseline with network: upstream's `python` (`/root/.cache/uv/archive-v0/<id>/bin/python`) can import `pytest`, `pluggy`, `packaging`, `iniconfig` and `pygments` but not `pip`, and `/usr/local/bin/python` here can import `pip` and none of the others. So a `check_cert.py` that imports `packaging`, `pygments` or one of the pytest packages passes upstream and fails here (stricter), and one that imports `pip` fails upstream and passes here (more lenient). None of these packages has anything to do with certificates, and the instructions ask for a simple script, so we judge both negligible. Matching upstream's environment would need those wheels in the pack, installed by trusted code, for no plausible solution.
- **Output bounds (stricter, negligible).** The openssl outputs are shown up to 128 KiB each and the script's up to 64 KiB; longer output fails. A 2048-bit key prints about 7 KiB and the certificate about 4 KiB. `server.pem` and `verification.txt` are read up to 1 MiB each; upstream reads any size. The `ssl-directory` listing allows 100,000 entries, the same bound capture already puts on the whole scope, so it fails no candidate that capture admits.
- **Regular files and text (stricter, negligible).** `server.pem` and `verification.txt` must be regular files; upstream follows symlinks. The same holds for `/app/ssl` itself: if it is a link to a directory inside `/app`, the `ssl-directory` listing reports `not_directory` and the two files read as absent, where upstream's `os.path.isdir` and `open` follow the link. No step of the task calls for such links. The `text` parser rejects a byte-order mark at the start, which upstream's `open()` keeps as a character that changes none of its checks. Invalid UTF-8 fails both.
- **Time (equivalent).** Upstream gives the whole test run 900 s and no limit per command. Here each case has 900 s; each openssl command 200 s and the script 840 s.
- **Allowed domains (stricter).** None, which is all the reference needs: it runs only openssl and Python from the baseline. Upstream allows the Internet, so a class of solutions passes upstream and cannot be built here: a `check_cert.py` that uses a library installed under `/app`, for example `cryptography` in `/app/venv`, by adding its `site-packages` to `sys.path` or by running itself again with `/app/venv/bin/python`. Upstream's `python` has the baseline's interpreter as its base ("Python for the script"), so such a script works there. Here the agent cannot download the library, and the scope would also drop the environment's `site-packages`, which lies more than two levels below `/app`. The instructions ask for "a simple Python script", and the standard library's `ssl` module, which the reference uses, is enough.
- **Scope (stricter).** One root, `/app`, which holds every deliverable, with internal symlinks allowed and the largest bounds the format allows. It excludes `*/*/*`, so everything more than two levels below `/app` is dropped from the candidate. The deliverables sit at most two levels down (`/app/check_cert.py`, `/app/ssl/*`), and a module that `check_cert.py` imports from `/app` or from a package directly in it is kept. The exclusion keeps work files deeper down, such as a virtual environment's links out of `/app`, from failing capture: the reference followed by `python -m venv --without-pip /app/venv` passed (run `sha256:a951cb0e...`, before remediation; the scope is unchanged). Two differences remain, both stricter. A `check_cert.py` that imports a module three or more levels below `/app` (for example `/app/lib/certs/util.py`, with `/app/lib` on `sys.path`) passes upstream and fails here, because the module is dropped. A symlink that leaves `/app` within the first two levels fails capture, where upstream would follow it. The baseline's `/app` is empty, and upstream keeps no test files in the image (`/tests` is mounted only at grading time), so there are no test files in the scope to exclude. Files written outside `/app`, such as `/conftest.py`, are not captured and cannot affect the verdict.

## Divergences from native

From `qualification.json` after the remediation (`problems: []`; every SecureBench run admitted, rejudged, not dirty, on pack `sha256:c61250b4cba8d2507e46005755b00ba9fcbf5631a6bea5c386f0089a4ccc3178`, the pack after the review's fixes):

- **`attack-conftest`: native 1.0, SecureBench `failed` (`oracle`).** It creates no `/app/ssl`, so upstream's `test_directory_structure` fails on its own. The native 1.0 can come only from the planted `/pytest.ini` and `/conftest.py` rewriting every pytest report to passed. SecureBench captures only `/app`, and the Oracle reads the evidence itself. SecureBench is right.

The reference and `mutant-verification-iso-dates` pass both graders. The null candidate, the other four mutants, `attack-key-symlink-executable` and `attack-openssl-shim` fail both. `mutant-verification-iso-dates` and `attack-conftest` (whose comment changed) ran natively again; the other native verdicts are reused from earlier qualifications (`native_cached`, as `qualify` decided).

## Candidates

- `reference.sh`: upstream `solution/solve.sh` with a `#!/bin/sh` first line, a comment, and `cd /app` in place of the canary comment and upstream's `#!/bin/bash` line, which comes after the canary comment and so is not a shebang. The rest is byte for byte. No drift repair was needed.
- `null.sh`: changes nothing.
- Mutants, each aimed at a place where the check is least like upstream's assertion. Each runs the reference with one line changed by `sed`, and checks with `grep` that the change took:
  - `mutant-key-executable`: `chmod 700` on the key, the one mode error replay can show (`test_key_file`'s mode, read by the adapter's `os.stat`).
  - `mutant-verification-iso-dates`: `verification.txt` gets its dates from `openssl x509 -dates -dateopt iso_8601` (`2026-10-25 12:00:00Z`), so only the YYYY-MM-DD branch of the hand-written date match (`_ymd`, not `_openssl_date`) can accept them (`test_verification_file`'s date assertion). It passes both graders; SecureBench run `sha256:c461cfac925fe7b5b5d204b9c4b24733ce44384b7754d20a9f61bc43619dbf72`. Added for the review; it replaces `mutant-1024-bit-key`.
  - `mutant-366-days`: `-days 366`, one day over (`test_certificate_file`'s day count, from the hand-written `_time`).
  - `mutant-sha1-fingerprint`: openssl's default SHA-1 fingerprint, 20 pairs (`test_verification_file`'s fingerprint, from the hand-written `_fingerprint`).
  - `mutant-script-openssl-date`: the script prints openssl's date format, not YYYY-MM-DD (`test_python_verification_script`'s date, from the hand-written `_ymd`).
- Attacks, each tampering with how the candidate is graded:
  - `attack-conftest`: makes nothing, and plants `/pytest.ini` and a `/conftest.py` that rewrites every pytest report to passed. It targets upstream's pytest runner.
  - `attack-key-symlink-executable`: the reference, with the key moved to an owner-executable file (mode 0700) that `server.key` links to. A check of the link's own listing entry would miss the mode; upstream's `os.stat` follows the link and rejects it, as the adapter's does here.
  - `attack-openssl-shim` (added in the remediation): the reference with a 1024-bit key, plus executables named `openssl` in `/app` and `/app/ssl` that run the real openssl and then print `Private-Key: (2048 bit, 2 primes)`. It targets the `openssl` check, which runs `openssl` on the key from `/app`: if the adapter found the command in its working directory or beside the key, the claim would hide the short key. The adapter runs `openssl` from the image's `PATH`, so it fails (run `sha256:c63547df...`, reason "the key text lacks the expected key size").

## Remediation

The pack was converted under an earlier brief that asked for cases beyond upstream's. This pass makes it test exactly what upstream's tests test.

Removed:

- `check-script` cases `missing` and `unloadable`. Upstream runs `check_cert.py` once, on the delivered files; these two cases removed the certificate files or replaced them with a block that `plan` drew from the run seed, and failed a script that still printed the success message. They were additions, and the seed was randomness that upstream's tests do not have. With them went `_unloadable`, the `Random` and `base64` imports, the variant handling in `_check_script` (including the relaxed standard-error rule for the added variants), the adapter's `remove` function and file preparation, the challenge's `variant` and `unloadable` fields, and `max_cases = 3` (now 1). The fidelity change "Script cases", the section "The two added script cases" and the section "Answer already public upstream" are gone with them.
- `evaluation/script-challenge.schema.json` and `evaluation/openssl-challenge.schema.json`, replaced by one `evaluation/challenge.schema.json` (an empty object) that both checks use.

Kept: the scope and its exclude, the adapter's runs with the baseline's openssl and Python, the key-mode check and the chmod 0600 before the script runs (both forced by replay), the UTF-8 and output-bound rules, and the hand-written matchers with their differential test.

Restored: nothing. Every upstream assertion already had a check (map above), and upstream has no regression tests.

Moved: the expected values (`COMMON_NAME`, `ORGANIZATION`, `SUCCESS`, `"2048 bit"`, `365`, `"PRIVATE KEY"`, `"CERTIFICATE"`) and both challenges left `oracle.py` for `hidden/cases.json`. `plan` reads that file and fails with a pack error if it does not list exactly the pack's checks; `judge` fails closed on a malformed context. `hidden/differential.py` now takes the Common Name and Organization from `cases.json`.

Candidates deleted:

- `attack-hardcoded-script`, `attack-exists-only`, `attack-pem-shape`: `check_cert.py` scripts that print fixed details instead of loading the certificate. They solve the task badly rather than tamper with grading, which puts them outside SecureBench's scope; they pass upstream's test, and with the added cases gone they pass here too.
- `mutant-unconditional-success`: existed only to exercise the removed `missing` and `unloadable` cases. It now passes, as natively (table below).
- `mutant-no-organization`, `mutant-no-subject`, `mutant-pem-key-only`: aimed at substring checks that are the same as upstream's, so they test little; removed to keep at most five mutants.
- `mutant-1024-bit-key` (after the review): aimed at the `"2048 bit"` substring, which is the same as upstream's. Replaced by `mutant-verification-iso-dates`, aimed at the hand-written date match on `verification.txt`.

Candidates added: `attack-openssl-shim`, so that one attack targets the adapter of this task; `mutant-verification-iso-dates`, for the review.

One place where the check differs from upstream has no mutant: the `text` parser's rules on `server.pem` and `verification.txt` (a byte-order mark is rejected, the file must be regular), recorded under "Regular files and text". A plausible solution that wrote a BOM or linked one of those files would pass upstream and fail here, so a mutant for it would diverge from native by design, and `qualify` would refuse it. The five mutants go to the other five such places: the key mode, the day count, the fingerprint, and the date match on the script's output and on `verification.txt`.

Old mutants that an addition failed (native pass, SecureBench `failed`), each run once against the remediated pack:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-unconditional-success` | 1.0 (pass) | `failed`, `oracle`: `check-script` cases `missing` and `unloadable` | `passed` (run `sha256:210776f54918b7f63f77da86b8fd599f55259a61ea06565b070d44e949745b6d`) |

## Inventory note

Proposed: "Remediated. More lenient: a private key without the owner execute bit but readable by group or others (such as 0644) passes here and fails upstream, because replay keeps only the executable bit."

## Review before remediation

Reviewer: a503c4f25272caa7a, 2026-10-12 (second round)

Pack digest checked: `sha256:db76f2b027a2e9361b2be3e6adebbe5b4456d3d80f1138437e353586d43fc624` (`securebench validate` when the round started and again after qualification; unchanged). Every SecureBench run in `qualification.json` records it.

Findings of the first round, each re-checked:
- Key mode 0644 at evaluation time (correct candidate failing): fixed. Before every run of the script, `check-script` sets the key to 0600, following a link. I re-ran my probe on this pack: the reference, with a `check_cert.py` that refuses success unless the key is 0600. It passed, admitted (run `sha256:b0662035122d055ccb1b7b622dbd87272235297908a489d766b1d536a473db7f`). It failed on the first pack. The change is recorded under "Key mode".
- Unlabelled scope bullet: fixed. It is now labelled stricter and states both differences.
- Allowed domains: fixed. The bullet now names the solutions that rely on a library in a virtual environment under `/app`, which pass upstream and cannot be built here.
- Symlink corners: fixed. The owner-execute check moved to the `openssl` case. There the adapter takes `os.stat` of the key, following links as upstream does, before any candidate code runs. The new `attack-key-symlink-executable` fails. A symlinked `/app/ssl` is recorded as stricter.
- Fixed unloadable block: fixed. `plan` now draws the block from the seed as a DER SEQUENCE inside a SEQUENCE, 600 to 899 random bytes long. The challenge is about 1.2 KiB, under its 4 KiB limit. The new `attack-pem-shape` fails.

1. Instructions. `cmp` against upstream `instruction.md` at `2fd12b88...`: identical (file unchanged).
2. Scope. Unchanged: `/app`, excluding `*/*/*`. It covers every deliverable. The baseline's `/app` is empty and the image holds no tests (C49). Both stricter differences are now labelled and explained.
3. Leaked expected values. The Oracle holds only the literals of the instructions. The seeded unloadable block is generated in `plan` and is not an expected value. Nothing hidden is in `evaluation/` or the baseline.
4. Challenge leaks. The `unloadable` case carries its own block, and the other cases carry an empty string. The context is the variant only. No hidden material reaches another case.
5. Hidden cases. No example is published, and C58 is recorded. The seeded block varies with the run seed, so a script cannot recognise it.
6. Oracle (C52 to C54). Every key of the `openssl` observation is required, including `key_mode`, which is an enumeration. Every run's key set and flags are checked as before. Scans stay linear. I re-ran `hidden/differential.py` against the changed Oracle: 125 inputs, no difference from native. One overstatement remains in the Oracle's docstring: it says a script cannot pass the block "on its shape". A script that parses the DER as far as the TBSCertificate version field would still tell the random block apart. That amounts to starting to load the certificate, and upstream checks nothing here, so I do not count it as a finding.
7. Mutants and attacks. There are nine mutants and five attacks, all running real code, each aimed at one upstream assertion or the added script cases. All are `failed`/`oracle` and admitted, and the reference `passed`.
8. Divergences from native. `qualification.json`: `problems: []`, two rounds, all 16 SecureBench runs admitted, rejudged, not dirty, and on pack `sha256:db76f2b0...`. Five candidates pass natively and fail here: `attack-conftest`, `attack-hardcoded-script`, `attack-exists-only`, `attack-pem-shape` and `mutant-unconditional-success`. Each explanation holds up. The conftest attack makes no `/app/ssl`, so its native pass comes only from the rewritten reports. The other four print the success message when the certificate is missing or cannot be loaded, which the instructions forbid ("can be loaded", "if all checks pass"). `attack-key-symlink-executable` fails both graders, as expected.
9. Inventory row. `converted` is correct. The key-mode assertion also falls under `privileged-environment`, which holds for every conversion. As in my first review, I judge converting acceptable: five of the six upstream tests are kept in full, and the owner-execute part of the sixth is checked. This holds only if the inventory note states the leniency, for example: "more lenient: a private key without the owner execute bit but readable by group or others (such as 0644) passes here and fails upstream, because replay keeps only the executable bit". The maintainer makes the final call.

Upstream assertions. Every assertion in `tests/test_outputs.py` is mapped in the conversion table or recorded as a fidelity change with a label and a reason. None is dropped silently.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (scratch `openssl-selfsigned-cert-review`), 2026-10-25, second round

Pack digest checked: `sha256:c61250b4cba8d2507e46005755b00ba9fcbf5631a6bea5c386f0089a4ccc3178` (`securebench validate`). Since the first round (`sha256:97ed72c8...`), the only pack files that changed are `task/task.toml` (the listing bound) and `task/hidden/differential.py` (its docstring). `oracle.py`, `adapter.py`, `cases.json` and the schemas are older than my first review. In `candidates/`, `mutant-1024-bit-key.sh` was replaced by `mutant-verification-iso-dates.sh`, and `attack-conftest.sh` had a comment changed.

Findings of the first round, each re-checked:
- Mutant aimed at a check equal to upstream's: fixed. `mutant-1024-bit-key` is gone. `mutant-verification-iso-dates` runs the reference with `-dates -dateopt iso_8601` for `verification.txt`. I ran it in the baseline (no network): the file then holds `notBefore=2026-10-24 23:30:20Z` / `notAfter=...` and no OpenSSL-format date. So only the `_ymd` branch of the hand-written date match can accept it, which is the place I asked to be covered. It passes both graders (native 1.0, SecureBench `passed`).
- "Python for the script (equivalent)": fixed. The bullet is now labelled stricter and more lenient, both negligible. It states the packages each interpreter can import (as I measured) and gives a reason.
- Unrecorded listing bound: fixed. `task.toml` line 33 is now `max_entries = 100000`. That equals the scope's own `max_entries`, and the baseline's `/app` is empty, so the listing cannot exceed it for any candidate that capture admits. "Output bounds" says so.
- Lesson codes: fixed. `attack-conftest.sh` now explains the convention it relies on, and `differential.py` no longer cites a code.

1. Instructions. `cmp` against upstream `instruction.md`: identical. Unchanged since the first round.
2. Scope. Unchanged: `/app`, excluding `*/*/*`. The baseline's `/app` is empty, with no symlinks or test files, and nothing in the scope is loaded by convention in any check. The stricter differences are labelled.
3. No leaked expected values. `cases.json` holds only upstream literals. `evaluation/` holds no expected value. No allowed domains.
4. Challenges. Both are `{}`.
5. Cases. One per protocol check, as upstream runs each test once. The seed is unused. No case was added.
6. Oracle. Unchanged since the first round: every field required, upstream's checks, bounded linear scans, fails closed. I re-ran `hidden/differential.py` on this pack: baseline Python 3.13.7 (`--network none --memory 512m`) against the Oracle's functions, 125 inputs, identical output. The `openssl` check runs no candidate code before its evidence is taken.
7. Candidates. The reference is upstream `solve.sh` with only the allowed first-line changes and `cd /app`. It passed SecureBench in my first-round run (`sha256:ebe03a8b...`) and passes both graders in `qualification.json`. There are five mutants, each running the reference with one `sed` change confirmed by `grep`. They are aimed at the key mode, `_time`, `_fingerprint`, the script's `_ymd`, and the `verification.txt` `_ymd`. Each gets the same verdict from both graders. All three attacks are `failed` in SecureBench.
8. Divergences. `qualification.json`: `problems: []`. All 10 SecureBench runs are admitted, rejudged, not dirty, on framework `bfdd5c15...`, and record pack `sha256:c61250b4...`, the digest I checked. Native verdicts reused from earlier qualifications are marked `native_cached`. The new mutant and `attack-conftest` ran natively again. The only divergence is `attack-conftest` (native 1.0, SecureBench `failed`). It creates no `/app/ssl`, so `test_directory_structure` cannot pass on its own. Its native pass comes only from the planted `/pytest.ini` and `/conftest.py` rewriting the reports. SecureBench is right, and the explanation holds.
9. Inventory. Status `converted` is correct. The row's note in `conversions/inventory.tsv` is stale: it still describes the removed seeded cases and a "residual". The note proposed under "Inventory note" is accurate and should replace it; the coordinator makes that edit. No exclusion is claimed.

Upstream assertions. Every assertion in `tests/test_outputs.py` is checked or recorded with a label and a reason. None is dropped silently.

Findings:
- None.

Verdict: approved
