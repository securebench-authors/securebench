"""Oracle for openssl-selfsigned-cert.

Upstream's six tests (tests/test_outputs.py), and where each is checked:

- test_directory_structure: `ssl-directory`, /app/ssl is a directory.
- test_key_file: the mode assertion `<= 0o600` cannot be checked, because
  replay keeps only the owner execute bit. `openssl` fails a key with that
  bit set, following links as `os.stat` does, and requires upstream's
  substring in the output of `openssl rsa -text -noout`.
- test_certificate_file: `openssl` requires the Common Name in the output of
  `openssl x509 -text -noout`, the Organization in its lowercase, and the
  number of whole days between the notBefore and notAfter that `-dates`
  prints.
- test_combined_pem_file: `combined-pem` requires both markers in the text,
  and `openssl` requires `openssl x509` on the file to exit 0.
- test_verification_file: `verification-file`, the same substring and shape
  checks as upstream's.
- test_python_verification_script: `check-script`, one run of the script on
  the delivered files, with upstream's three checks on its output.

Every expected value and challenge is in hidden/cases.json, a literal of the
upstream tests; this file holds only how to compare. Upstream decodes every
output strictly as UTF-8, so invalid output fails here too. Upstream applies
regular expressions and `strptime`. The judge may do neither, so `_ymd`,
`_openssl_date`, `_fingerprint` and `_time` are hand-written equivalents,
compared with upstream's on a corpus by hidden/differential.py. Every scan is
linear in text of at most 1 MiB.
"""

from securebench.core.errors import PackError
from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    ListingStatus,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

ARTIFACT_CHECKS = ("ssl-directory", "combined-pem", "verification-file")
PROTOCOL_CHECKS = ("openssl", "check-script")
OPENSSL_RUNS = ("key_text", "certificate_text", "certificate_dates", "pem_certificate")
OPENSSL_SHOWN = 131072
SCRIPT_SHOWN = 65536
RUN_KEYS = frozenset(
    {"ending", "exit_status", "stdout", "stdout_bytes", "stdout_utf8", "stderr_utf8"}
)
HEX = "0123456789abcdef"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
SHOWN = 256


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise PackError("cases.json is not an object")
    artifact = data.get("artifact_checks")
    protocol = data.get("protocol_checks")
    if not isinstance(artifact, dict) or not isinstance(protocol, dict):
        raise PackError("cases.json lacks artifact_checks or protocol_checks")
    if sorted(artifact) != sorted(ARTIFACT_CHECKS) or sorted(protocol) != sorted(PROTOCOL_CHECKS):
        raise PackError("cases.json does not list exactly the pack's checks")
    cases: dict[str, tuple[Case, ...]] = {}
    for check_id in PROTOCOL_CHECKS:
        listed = protocol[check_id]
        if not isinstance(listed, list) or not listed:
            raise PackError(f"cases.json: {check_id} has no cases")
        built: list[Case] = []
        for case in listed:
            if not isinstance(case, dict) or sorted(case) != ["challenge", "expected"]:
                raise PackError(f"cases.json: a case of {check_id} is malformed")
            built.append(Case(case["challenge"], case["expected"]))
        cases[check_id] = tuple(built)
    return Plan(artifact_contexts=dict(artifact), cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        if evidence.check_id != check_id:
            return _fail("unexpected evidence")
        if check_id == "ssl-directory":
            return _ssl_directory(evidence)
        if check_id == "combined-pem":
            return _combined_pem(context, evidence)
        if check_id == "verification-file":
            return _verification_file(context, evidence)
        return _fail("unexpected check")
    if evidence.check_id != check_id or not isinstance(evidence.outcome, Observed):
        return _fail("no observation")
    if check_id == "openssl":
        return _openssl(context, evidence.outcome.value)
    if check_id == "check-script":
        return _check_script(context, evidence.outcome.value)
    return _fail("unexpected check")


def _fail(reason: str, **details: JsonValue) -> Judgment:
    diagnostic: dict[str, JsonValue] = {"reason": reason}
    diagnostic.update(details)
    return Judgment(False, diagnostic)


def _strings(
    context: JsonValue, keys: tuple[str, ...], others: tuple[str, ...] = ()
) -> dict[str, str] | None:
    """The context's fields `keys`, each a non-empty string.

    None unless the context has exactly `keys` and `others`; the caller checks `others`.
    """
    if not isinstance(context, dict) or sorted(context) != sorted(keys + others):
        return None
    found: dict[str, str] = {}
    for key in keys:
        item = context[key]
        if not isinstance(item, str) or not item:
            return None
        found[key] = item
    return found


def _ssl_directory(evidence: ArtifactEvidence) -> Judgment:
    if evidence.files or len(evidence.listings) != 1 or evidence.listings[0].path != "/app/ssl":
        return _fail("unexpected evidence")
    listing = evidence.listings[0]
    if listing.status is not ListingStatus.PRESENT:
        return _fail(f"/app/ssl is {listing.status.value}")
    return Judgment(True, None)


def _text(evidence: ArtifactEvidence, path: str) -> str | Judgment:
    if evidence.listings or len(evidence.files) != 1 or evidence.files[0].path != path:
        return _fail("unexpected evidence")
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return _fail(f"{path} is {found.status.value}")
    if not isinstance(found.value, Text):
        return _fail("unexpected evidence")
    return found.value.text


def _combined_pem(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    if not isinstance(context, dict) or sorted(context) != ["markers"]:
        return _fail("malformed context")
    markers = context["markers"]
    if not isinstance(markers, list) or not markers:
        return _fail("malformed context")
    text = _text(evidence, "/app/ssl/server.pem")
    if isinstance(text, Judgment):
        return text
    for marker in markers:
        if not isinstance(marker, str) or not marker:
            return _fail("malformed context")
        if marker not in text:
            return _fail(f"server.pem does not contain {marker}")
    return Judgment(True, None)


def _verification_file(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    expected = _strings(context, ("common_name", "organization"))
    if expected is None:
        return _fail("malformed context")
    text = _text(evidence, "/app/ssl/verification.txt")
    if isinstance(text, Judgment):
        return text
    lower = text.lower()
    if expected["common_name"] not in lower:
        return _fail("verification.txt does not contain the Common Name")
    if expected["organization"] not in lower:
        return _fail("verification.txt does not contain the Organization")
    if not (_ymd(text) or _openssl_date(text)):
        return _fail("verification.txt does not contain a date in either format")
    if not _fingerprint(lower):
        return _fail("verification.txt does not contain a SHA-256 fingerprint")
    return Judgment(True, None)


def _run(value: JsonValue, shown: int) -> dict[str, JsonValue] | str:
    """The run if it ended, printed valid UTF-8 on both streams and was shown in full.

    Upstream's `subprocess.run(..., text=True)` decodes both streams strictly,
    so invalid bytes on either fail its test.
    """
    if not isinstance(value, dict) or frozenset(value) != RUN_KEYS:
        return "malformed run"
    stdout = value["stdout"]
    size = value["stdout_bytes"]
    if not isinstance(stdout, str) or not isinstance(size, int) or isinstance(size, bool):
        return "malformed run"
    if value["ending"] != "exited":
        return f"the run ended {value['ending']}"
    if value["stdout_utf8"] is not True or value["stderr_utf8"] is not True:
        return "the output is not valid UTF-8"
    if size > shown or size != len(stdout.encode("utf-8")):
        return "the output was not shown in full"
    return value


def _openssl(context: JsonValue, value: JsonValue) -> Judgment:
    expected = _strings(context, ("key_text", "common_name", "organization"), ("days",))
    if expected is None or not isinstance(context, dict):
        return _fail("malformed context")
    days_expected = context["days"]
    if not isinstance(days_expected, int) or isinstance(days_expected, bool):
        return _fail("malformed context")
    if not isinstance(value, dict) or frozenset(value) != frozenset({"key_mode", *OPENSSL_RUNS}):
        return _fail("malformed observation")
    if value["key_mode"] not in ("no_owner_execute", "not_a_file"):
        # A missing key fails on the key text below.
        return _fail("server.key has the owner execute bit, so its mode is above 0600")
    runs: dict[str, str] = {}
    for name in OPENSSL_RUNS:
        run = _run(value[name], OPENSSL_SHOWN)
        if isinstance(run, str):
            return _fail(f"{name}: {run}")
        if name == "pem_certificate" and run["exit_status"] != 0:
            return _fail("openssl x509 cannot read a certificate from server.pem")
        stdout = run["stdout"]
        if not isinstance(stdout, str):
            return _fail("malformed observation")
        runs[name] = stdout
    if expected["key_text"] not in runs["key_text"]:
        return _fail("the key text lacks the expected key size", got=runs["key_text"][:SHOWN])
    if expected["common_name"] not in runs["certificate_text"]:
        return _fail("the certificate does not have the Common Name")
    if expected["organization"] not in runs["certificate_text"].lower():
        return _fail("the certificate does not have the Organization")
    dates = _universal_newlines(runs["certificate_dates"])
    not_before = _time(_field(dates, "notBefore="))
    not_after = _time(_field(dates, "notAfter="))
    if not_before is None or not_after is None:
        return _fail("cannot parse the certificate dates", got=dates[:SHOWN])
    # timedelta.days: whole days, rounded down.
    days = (not_after - not_before) // 86400
    if days != days_expected:
        return _fail("the certificate's validity is not the expected number of days", days=days)
    return Judgment(True, None)


def _check_script(context: JsonValue, value: JsonValue) -> Judgment:
    expected = _strings(context, ("success", "common_name"))
    if expected is None:
        return _fail("malformed context")
    run = _run(value, SCRIPT_SHOWN)
    if isinstance(run, str):
        return _fail(run)
    stdout = run["stdout"]
    if not isinstance(stdout, str):
        return _fail("malformed observation")
    if run["exit_status"] != 0:
        return _fail("the script did not exit 0", exit_status=run["exit_status"])
    if expected["success"] not in stdout:
        return _fail("the script did not print the success message", got=stdout[:SHOWN])
    if expected["common_name"] not in stdout:
        return _fail("the script does not print the Common Name", got=stdout[:SHOWN])
    if not _ymd(stdout):
        return _fail("the script does not print a YYYY-MM-DD date", got=stdout[:SHOWN])
    return Judgment(True, None)


def _universal_newlines(text: str) -> str:
    """What `subprocess.run(text=True)` returns: `\\r\\n` and `\\r` read as `\\n`."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _field(text: str, name: str) -> str | None:
    """`re.search(name + "(.*)", text).group(1).strip()`, or None without a match."""
    start = text.find(name)
    if start < 0:
        return None
    start += len(name)
    end = text.find("\n", start)
    return (text[start:] if end < 0 else text[start:end]).strip()


def _digits(token: str, *alternatives: str) -> int | None:
    """The value of `token` if it matches one of strptime's alternatives.

    In an alternative, `d` is `\\d` (any Unicode decimal digit) and any other
    character lists the ASCII digits allowed there, as in `2[0-3]`. For
    example, strptime's `%H` is `2[0-3]|[0-1]\\d|\\d`, here "2|0123", "01|d", "d".
    """
    for alternative in alternatives:
        classes = alternative.split("|")
        if len(token) == len(classes) and all(
            c.isdecimal() if allowed == "d" else c in allowed
            for c, allowed in zip(token, classes, strict=True)
        ):
            return int(token)
    return None


def _time(text: str | None) -> int | None:
    """Seconds since 0001-01-01 for `datetime.strptime(text, "%b %d %H:%M:%S %Y %Z")`.

    None where strptime raises. strptime matches `%b\\s+%d\\s+%H:%M:%S\\s+%Y\\s+%Z`
    in full, ignoring case. No field holds whitespace, so splitting on it gives
    the fields (`%d`'s alternative ` [1-9]` only moves a space out of the
    `\\s+` before it). The month is a C-locale abbreviation in any case
    (U+017F does not match `s`: hidden/differential.py checks it). The zone
    is UTC or GMT: the verifier's
    container sets no TZ. `datetime` then rejects seconds 60 and 61, year 0
    and dates that do not exist.
    """
    if text is None:
        return None
    tokens = text.split()
    if len(tokens) != 5 or tokens[4].lower() not in ("utc", "gmt"):
        return None
    name = tokens[0].lower()
    clock = tokens[2].split(":")
    if name not in MONTHS or len(clock) != 3:
        return None
    month = MONTHS.index(name) + 1
    day = _digits(tokens[1], "3|01", "12|d", "0|123456789", "123456789")
    hour = _digits(clock[0], "2|0123", "01|d", "d")
    minute = _digits(clock[1], "012345|d", "d")
    second = _digits(clock[2], "6|01", "012345|d", "d")
    year = _digits(tokens[3], "d|d|d|d")
    if day is None or hour is None or minute is None or second is None or year is None:
        return None
    if year < 1 or second > 59 or day > _month_days(year, month):
        return None
    return ((_ordinal(year, month, day) * 24 + hour) * 60 + minute) * 60 + second


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _month_days(year: int, month: int) -> int:
    if month == 2:
        return 29 if _leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def _ordinal(year: int, month: int, day: int) -> int:
    before = year - 1
    days = before * 365 + before // 4 - before // 100 + before // 400
    return days + sum(_month_days(year, m) for m in range(1, month)) + day


def _ymd(text: str) -> bool:
    """`re.search(r"\\d{4}-\\d{2}-\\d{2}", text)`, where `\\d` is any Unicode decimal digit."""
    shape = "dddd-dd-dd"
    dash = text.find("-", 4)
    while 0 <= dash <= len(text) - 6:
        start = dash - 4
        if all(
            text[start + i] == "-" if kind == "-" else text[start + i].isdecimal()
            for i, kind in enumerate(shape)
        ):
            return True
        dash = text.find("-", dash + 1)
    return False


def _openssl_date(text: str) -> bool:
    r"""`re.search(r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}(?:\s+[A-Z]+)?", text)`.

    The optional zone never decides whether there is a match. Whitespace and
    digits are disjoint, so each `\s+` and `\d{1,2}` has one way to match.
    """
    for start in range(len(text) - 2):
        if text[start] in UPPER and text[start + 1] in LOWER and text[start + 2] in LOWER:
            if _openssl_date_at(text, start + 3):
                return True
    return False


def _openssl_date_at(text: str, at: int) -> bool:
    at = _spaces(text, at)
    if at < 0:
        return False
    digits = _decimals(text, at)
    if digits - at not in (1, 2):
        return False
    at = _spaces(text, digits)
    if at < 0 or at + 8 > len(text):
        return False
    clock = text[at : at + 8]
    if not all(c == ":" if i in (2, 5) else c.isdecimal() for i, c in enumerate(clock)):
        return False
    at = _spaces(text, at + 8)
    return at >= 0 and _decimals(text, at) - at >= 4


def _spaces(text: str, at: int) -> int:
    """The index after one or more whitespace characters at `at`, or -1."""
    end = at
    while end < len(text) and text[end].isspace():
        end += 1
    return end if end > at else -1


def _decimals(text: str, at: int) -> int:
    end = at
    while end < len(text) and text[end].isdecimal():
        end += 1
    return end


def _fingerprint(lower: str) -> bool:
    """`re.search(r"[0-9a-f]{2}(:[0-9a-f]{2}){31}", lower)`, in one pass from the end.

    `units[p]` counts the consecutive `:hh` groups starting at `p`, stepping 3.
    """
    size = len(lower)
    units = [0] * (size + 3)
    for p in range(size - 3, -1, -1):
        if lower[p] == ":" and lower[p + 1] in HEX and lower[p + 2] in HEX:
            units[p] = 1 + units[p + 3]
    for start in range(size - 1):
        if lower[start] in HEX and lower[start + 1] in HEX and units[start + 2] >= 31:
            return True
    return False
