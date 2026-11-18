r"""Differential test of the Oracle's hand-written matchers against upstream's.

Not used by the Oracle. Upstream's tests apply regular expressions and
`datetime.strptime`, which the judge may not use. This script applies
upstream's own expressions, copied from tests/test_outputs.py, and the
Oracle's replacements to the same corpus, and prints one line per input:
its name, then `pass` or `fail`.

    docker run --rm --network none --memory 512m -v <hidden>:/d:ro <baseline> \
        python3 -I -B /d/differential.py native > native.txt
        upstream's expressions on the baseline's Python 3.13, with no TZ and
        no locale set, as in the verifier's container.
    uv run python -B hidden/differential.py ours > ours.txt
        run from the task directory: the Oracle's functions, loaded from
        hidden/oracle.py, with the Common Name and Organization from
        hidden/cases.json.
    diff native.txt ours.txt

The four groups are the `-dates` output (test_certificate_file's parse and
365-day comparison), the verification file (test_verification_file's four
assertions), the check script's output (test_python_verification_script's
date search), and fingerprint-only inputs.
"""

import sys

GOOD_SUBJECT = "subject=O = DevOps Team, CN = dev-internal.company.local\n"
GOOD_FINGERPRINT = "sha256 Fingerprint=" + ":".join(["BC", "7D"] * 16) + "\n"


def dates(before: str, after: str) -> str:
    return f"notBefore={before}\nnotAfter={after}\n"


DATES: dict[str, str] = {
    "reference": dates("Oct 12 00:08:00 2026 GMT", "Oct 12 00:08:00 2027 GMT"),
    "366-days": dates("Oct 12 00:08:00 2026 GMT", "Oct 13 00:08:00 2027 GMT"),
    "364-days": dates("Oct 12 00:08:00 2026 GMT", "Oct 11 00:08:00 2027 GMT"),
    "365-days-minus-1s": dates("Oct 12 00:08:00 2026 GMT", "Oct 12 00:07:59 2027 GMT"),
    "365-days-plus-23h59m59s": dates("Oct 12 00:00:00 2026 GMT", "Oct 12 23:59:59 2027 GMT"),
    "366-days-exactly": dates("Oct 12 00:00:00 2026 GMT", "Oct 13 00:00:00 2027 GMT"),
    "across-feb-29": dates("Mar  1 00:00:00 2027 GMT", "Mar  1 00:00:00 2028 GMT"),
    "across-feb-29-365": dates("Mar  1 00:00:00 2027 GMT", "Feb 29 00:00:00 2028 GMT"),
    "leap-year-inside": dates("Jan  1 00:00:00 2028 GMT", "Dec 31 00:00:00 2028 GMT"),
    "century-non-leap": dates("Mar  1 00:00:00 2099 GMT", "Mar  1 00:00:00 2100 GMT"),
    "century-leap-2000": dates("Mar  1 00:00:00 1999 GMT", "Feb 29 00:00:00 2000 GMT"),
    "year-9999": dates("Dec 31 00:00:00 9998 GMT", "Dec 31 00:00:00 9999 GMT"),
    "year-0001": dates("Jan  1 00:00:00 0001 GMT", "Jan  1 00:00:00 0002 GMT"),
    "year-0000": dates("Jan  1 00:00:00 0000 GMT", "Jan  1 00:00:00 0001 GMT"),
    "year-3-digits": dates("Jan  1 00:00:00 999 GMT", "Jan  1 00:00:00 1000 GMT"),
    "year-5-digits": dates("Jan  1 00:00:00 2026 GMT", "Jan  1 00:00:00 20270 GMT"),
    "feb-29-non-leap": dates("Feb 28 00:00:00 2026 GMT", "Feb 29 00:00:00 2027 GMT"),
    "day-32": dates("Oct 32 00:00:00 2026 GMT", "Nov  1 00:00:00 2027 GMT"),
    "day-00": dates("Oct 00 00:00:00 2026 GMT", "Oct 00 00:00:00 2027 GMT"),
    "day-zero-padded": dates("Oct 02 00:00:00 2026 GMT", "Oct 02 00:00:00 2027 GMT"),
    "day-3-digits": dates("Oct 002 00:00:00 2026 GMT", "Oct 002 00:00:00 2027 GMT"),
    "single-digit-clock": dates("Oct 2 1:2:3 2026 GMT", "Oct 2 1:2:3 2027 GMT"),
    "hour-24": dates("Oct 12 24:00:00 2026 GMT", "Oct 12 24:00:00 2027 GMT"),
    "minute-60": dates("Oct 12 00:60:00 2026 GMT", "Oct 12 00:60:00 2027 GMT"),
    "second-60": dates("Oct 12 00:00:60 2026 GMT", "Oct 12 00:00:60 2027 GMT"),
    "second-61": dates("Oct 12 00:00:61 2026 GMT", "Oct 12 00:00:61 2027 GMT"),
    "three-digit-second": dates("Oct 12 00:00:000 2026 GMT", "Oct 12 00:00:000 2027 GMT"),
    "fractional-seconds": dates("Oct 12 00:00:00.5 2026 GMT", "Oct 12 00:00:00.5 2027 GMT"),
    "utc": dates("Oct 12 00:00:00 2026 UTC", "Oct 12 00:00:00 2027 UTC"),
    "lowercase-zone-and-month": dates("oct 12 00:00:00 2026 gmt", "OCT 12 00:00:00 2027 Gmt"),
    "no-zone": dates("Oct 12 00:00:00 2026", "Oct 12 00:00:00 2027"),
    "zone-pst": dates("Oct 12 00:00:00 2026 PST", "Oct 12 00:00:00 2027 PST"),
    "zone-z": dates("Oct 12 00:00:00 2026 Z", "Oct 12 00:00:00 2027 Z"),
    "full-month-name": dates("October 12 00:00:00 2026 GMT", "October 12 00:00:00 2027 GMT"),
    "sept": dates("Sept 12 00:00:00 2026 GMT", "Sept 12 00:00:00 2027 GMT"),
    "tabs-between-fields": dates("Oct\t12\t00:00:00\t2026\tGMT", "Oct\t12\t00:00:00\t2027\tGMT"),
    "no-break-space-between-fields": dates(
        "Oct\u00a012 00:00:00 2026 GMT", "Oct\u00a012 00:00:00 2027 GMT"
    ),
    "ideographic-space": dates("Oct\u300012 00:00:00 2026 GMT", "Oct\u300012 00:00:00 2027 GMT"),
    "leading-and-trailing-spaces": dates(
        "  Oct 12 00:00:00 2026 GMT  ", "\tOct 12 00:00:00 2027 GMT \x0b"
    ),
    "missing-space": dates("Oct12 00:00:00 2026 GMT", "Oct12 00:00:00 2027 GMT"),
    "extra-token": dates("Oct 12 00:00:00 2026 GMT x", "Oct 12 00:00:00 2027 GMT x"),
    "bad-time-value": dates("Bad time value", "Bad time value"),
    "no-not-after": "notBefore=Oct 12 00:00:00 2026 GMT\n",
    "empty": "",
    "crlf": "notBefore=Oct 12 00:00:00 2026 GMT\r\nnotAfter=Oct 12 00:00:00 2027 GMT\r\n",
    "lone-cr": "notBefore=Oct 12 00:00:00 2026 GMT\rnotAfter=Oct 12 00:00:00 2027 GMT\r",
    "first-occurrence-wins": dates("Oct 12 00:00:00 2026 GMT", "Oct 12 00:00:00 2027 GMT")
    + dates("Oct 12 00:00:00 2000 GMT", "Oct 12 00:00:00 2000 GMT"),
    "after-before-order": "notAfter=Oct 12 00:00:00 2027 GMT\nnotBefore=Oct 12 00:00:00 2026 GMT\n",
    "arabic-indic-digits": dates(
        "Oct 12 00:00:00 \u0662\u0660\u0662\u0666 GMT", "Oct 12 00:00:00 2027 GMT"
    ),
    "long-s-month": dates("\u017fep 12 00:00:00 2026 GMT", "Sep 12 00:00:00 2027 GMT"),
    "arabic-second-digit-of-day": dates(
        "Oct 1\u0662 00:00:00 2026 GMT", "Oct 12 00:00:00 2027 GMT"
    ),
    "arabic-first-digit-of-day": dates("Oct \u06612 00:00:00 2026 GMT", "Oct 12 00:00:00 2027 GMT"),
    "arabic-single-digit-hour": dates("Oct 12 \u0660:00:00 2026 GMT", "Oct 12 0:00:00 2027 GMT"),
    "arabic-single-digit-day": dates("Oct \u0662 00:00:00 2026 GMT", "Oct 2 00:00:00 2027 GMT"),
    "arabic-31": dates("Oct 3\u0661 00:00:00 2026 GMT", "Oct 31 00:00:00 2027 GMT"),
    "separators-1c-1f-85": dates(
        "Oct\x1c12\x1d00:00:00\x1e2026\x85GMT", "Oct\x1f12 00:00:00 2027 GMT"
    ),
    "negative-span": dates("Oct 12 00:00:00 2027 GMT", "Oct 12 00:00:00 2026 GMT"),
}

VERIFICATION: dict[str, str] = {
    "reference": GOOD_SUBJECT
    + dates("Oct 12 00:08:00 2026 GMT", "Oct 12 00:08:00 2027 GMT")
    + GOOD_FINGERPRINT,
    "iso-dates": GOOD_SUBJECT + "Valid from 2026-10-12 to 2027-10-12\n" + GOOD_FINGERPRINT,
    "no-date": GOOD_SUBJECT + GOOD_FINGERPRINT,
    "no-fingerprint": GOOD_SUBJECT + dates("Oct 12 00:08:00 2026 GMT", "Oct 12 00:08:00 2027 GMT"),
    "no-common-name": "subject=O = DevOps Team\n" + "2027-10-12\n" + GOOD_FINGERPRINT,
    "no-organization": "subject=CN = dev-internal.company.local\n2027-10-12\n" + GOOD_FINGERPRINT,
    "uppercase-subject": GOOD_SUBJECT.upper() + "2027-10-12\n" + GOOD_FINGERPRINT,
    "organization-double-space": "DevOps  Team dev-internal.company.local 2027-10-12\n"
    + GOOD_FINGERPRINT,
    "arabic-indic-iso-date": GOOD_SUBJECT
    + "\u0662\u0660\u0662\u0667-\u0661\u0660-\u0661\u0662\n"
    + GOOD_FINGERPRINT,
    "fullwidth-iso-date": GOOD_SUBJECT
    + "\uff12\uff10\uff12\uff17-\uff11\uff10-\uff11\uff12\n"
    + GOOD_FINGERPRINT,
    "slash-date": GOOD_SUBJECT + "2027/10/12\n" + GOOD_FINGERPRINT,
    "iso-short-year": GOOD_SUBJECT + "27-10-12\n" + GOOD_FINGERPRINT,
    "iso-inside-digits": GOOD_SUBJECT + "120271-10-123\n" + GOOD_FINGERPRINT,
    "iso-at-start": "2027-10-12" + GOOD_SUBJECT + GOOD_FINGERPRINT,
    "iso-at-end": GOOD_SUBJECT + GOOD_FINGERPRINT + "2027-10-12",
    "openssl-date-one-digit-day": GOOD_SUBJECT + "Oct 2 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-three-digit-day": GOOD_SUBJECT + "Oct 123 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-one-digit-hour": GOOD_SUBJECT + "Oct 12 0:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-three-digit-year": GOOD_SUBJECT + "Oct 12 00:08:00 999\n" + GOOD_FINGERPRINT,
    "openssl-date-five-digit-year": GOOD_SUBJECT + "Oct 12 00:08:00 20271\n" + GOOD_FINGERPRINT,
    "openssl-date-uppercase-month": GOOD_SUBJECT + "OCT 12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-lowercase-month": GOOD_SUBJECT + "oct 12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-any-letters": GOOD_SUBJECT + "Xyz 12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-accented-month": GOOD_SUBJECT + "\u00c9ct 12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-no-space-after-month": GOOD_SUBJECT + "Oct12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-newlines-between": GOOD_SUBJECT + "Oct\n12\n00:08:00\n2027\n" + GOOD_FINGERPRINT,
    "openssl-date-separators-1c-1f": GOOD_SUBJECT
    + "Oct\x1c12\x1f00:08:00\x1d2027\n"
    + GOOD_FINGERPRINT,
    "openssl-date-no-break-space": GOOD_SUBJECT + "Oct\u00a012 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-zero-width-space": GOOD_SUBJECT
    + "Oct\u200b12 00:08:00 2027\n"
    + GOOD_FINGERPRINT,
    "openssl-date-arabic-digits": GOOD_SUBJECT
    + "Oct \u0661\u0662 00:08:00 2027\n"
    + GOOD_FINGERPRINT,
    "openssl-date-dot-separators": GOOD_SUBJECT + "Oct 12 00.08.00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-prefixed-by-letters": GOOD_SUBJECT + "XOct 12 00:08:00 2027\n" + GOOD_FINGERPRINT,
    "openssl-date-at-end-short": GOOD_SUBJECT + GOOD_FINGERPRINT + "Oct 12 00:08:00 202",
    "openssl-date-at-end": GOOD_SUBJECT + GOOD_FINGERPRINT + "Oct 12 00:08:00 2027",
    "empty": "",
}

SCRIPT_OUTPUT: dict[str, str] = {
    "reference": "Certificate Common Name: dev-internal.company.local\n"
    "Certificate Expiration Date: 2027-10-12\nCertificate verification successful\n",
    "openssl-format": "Certificate Expiration Date: Oct 12 00:08:59 2027 GMT\n",
    "slash-date": "Expires 2027/10/12\n",
    "day-month-year": "Expires 12-10-2027\n",
    "short-year": "Expires 27-10-12\n",
    "one-digit-month": "Expires 2027-1-12\n",
    "datetime-repr": "Expires 2027-10-12 00:08:59+00:00\n",
    "arabic-indic-digits": "Expires \u0662\u0660\u0662\u0667-\u0661\u0660-\u0661\u0662\n",
    "en-dash": "Expires 2027\u201310\u201312\n",
    "fullwidth-hyphen": "Expires 2027\uff0d10\uff0d12\n",
    "only-dashes": "----------\n",
    "only-digits": "20271012\n",
    "exact": "2027-10-12",
    "nine-chars": "2027-10-1",
    "empty": "",
}

FINGERPRINT: dict[str, str] = {
    "32-pairs": ":".join(["ab"] * 32),
    "31-pairs": ":".join(["ab"] * 31),
    "33-pairs": ":".join(["ab"] * 33),
    "uppercase": ":".join(["AB"] * 32),
    "sha1-20-pairs": ":".join(["ab"] * 20),
    "space-inside": ":".join(["ab"] * 16) + ": " + ":".join(["ab"] * 16),
    "dash-separated": "-".join(["ab"] * 32),
    "no-separator": "ab" * 32,
    "non-hex-letter": ":".join(["ab"] * 15 + ["ag"] + ["ab"] * 16),
    "fullwidth-colon": "\uff1a".join(["ab"] * 32),
    "fullwidth-hex": ":".join(["\uff41\uff42"] * 32),
    "kelvin-sign": ":".join(["ab"] * 31 + ["\u212a0"]),
    "prefixed-odd": "a" + ":".join(["ab"] * 32),
    "three-hex-groups": ":".join(["abc"] * 32),
    "one-bad-then-good": ":".join(["ab"] * 10) + "::" + ":".join(["cd"] * 32),
    "split-by-newline": ":".join(["ab"] * 16) + "\n:" + ":".join(["ab"] * 15),
    "dotted-i": "\u0130" + ":".join(["ab"] * 32),
    "empty": "",
}


def native() -> dict[str, bool]:
    import re
    from datetime import datetime

    results: dict[str, bool] = {}
    for name, stdout in DATES.items():
        # subprocess.run(text=True) reads \r\n and \r as \n.
        dates_output = stdout.replace("\r\n", "\n").replace("\r", "\n")
        try:
            not_before_match = re.search(r"notBefore=(.*)", dates_output)
            not_after_match = re.search(r"notAfter=(.*)", dates_output)
            assert not_before_match and not_after_match, "Could not parse certificate dates"
            not_before_str = not_before_match.group(1).strip()
            not_after_str = not_after_match.group(1).strip()
            not_before = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z")
            not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
            days_diff = (not_after - not_before).days
            assert days_diff == 365
            results[f"dates/{name}"] = True
        except (AssertionError, ValueError):
            results[f"dates/{name}"] = False
    for name, verification_content in VERIFICATION.items():
        date_formats_found = re.search(r"\d{4}-\d{2}-\d{2}", verification_content) or re.search(
            r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}(?:\s+[A-Z]+)?",
            verification_content,
        )
        results[f"verification/{name}"] = bool(
            "dev-internal.company.local" in verification_content.lower()
            and "devops team" in verification_content.lower()
            and date_formats_found
            and re.search(r"[0-9a-f]{2}(:[0-9a-f]{2}){31}", verification_content.lower())
        )
    for name, stdout in SCRIPT_OUTPUT.items():
        results[f"script/{name}"] = bool(re.compile(r"\d{4}-\d{2}-\d{2}").search(stdout))
    for name, text in FINGERPRINT.items():
        results[f"fingerprint/{name}"] = bool(
            re.search(r"[0-9a-f]{2}(:[0-9a-f]{2}){31}", text.lower())
        )
    return results


def ours() -> dict[str, bool]:
    import importlib.util
    import json
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("oracle", Path(__file__).with_name("oracle.py"))
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    expected = cases["artifact_checks"]["verification-file"]
    results: dict[str, bool] = {}
    for name, stdout in DATES.items():
        text = oracle._universal_newlines(stdout)
        before = oracle._time(oracle._field(text, "notBefore="))
        after = oracle._time(oracle._field(text, "notAfter="))
        results[f"dates/{name}"] = (
            before is not None and after is not None and (after - before) // 86400 == 365
        )
    for name, content in VERIFICATION.items():
        lower = content.lower()
        results[f"verification/{name}"] = bool(
            expected["common_name"] in lower
            and expected["organization"] in lower
            and (oracle._ymd(content) or oracle._openssl_date(content))
            and oracle._fingerprint(lower)
        )
    for name, stdout in SCRIPT_OUTPUT.items():
        results[f"script/{name}"] = oracle._ymd(stdout)
    for name, text in FINGERPRINT.items():
        results[f"fingerprint/{name}"] = oracle._fingerprint(text.lower())
    return results


if __name__ == "__main__":
    for case, passed in (native() if sys.argv[1] == "native" else ours()).items():
        print(case, "pass" if passed else "fail")
