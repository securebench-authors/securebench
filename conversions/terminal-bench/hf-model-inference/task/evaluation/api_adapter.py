"""Adapter of the api check: upstream's three service tests, in upstream's order.

The agent's service does not survive capture, so the adapter starts it again
with the candidate's /app/start.sh and waits for port 5000. Then it sends the
requests the upstream tests send, as requests 2.32.4 sends them, decodes each
response as requests' `Response.json()` does, and reports the type and value
of every field the tests assert on. It decides nothing; the Oracle judges.
"""

import codecs
import http.client
import json
import math
import os
import socket
import subprocess
import sys
import time
import zlib

START_SCRIPT = "/app/start.sh"
PORT = 5000
STARTUP_SECONDS = 300
# The headers requests 2.32.4 sends; gzip and deflate are the encodings it
# accepts when neither brotli nor zstandard is installed, as in the baseline.
HEADERS = {
    "User-Agent": "python-requests/2.32.4",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
}
STRING_BYTES = 1024
ERROR_CHARS = 200


def describe(error: BaseException) -> str:
    message = f"{type(error).__name__}: {error}"[:ERROR_CHARS]
    return message.encode("utf-8", "replace").decode("utf-8")


def start_service() -> bool:
    """Start the candidate's service; whether it stays in the foreground does not matter."""
    if not os.path.isfile(START_SCRIPT):
        return False
    try:
        subprocess.Popen(
            ["/bin/sh", START_SCRIPT],
            cwd="/app",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    return True


def wait_for_port() -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("0.0.0.0", PORT), timeout=2):
                return
        except OSError:
            time.sleep(1)


# urllib3 2.5.0's GzipDecoder, DeflateDecoder and the choice between them.
def gunzip(data: bytes) -> bytes:
    out = b""
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    later_member = False
    while True:
        try:
            out += decoder.decompress(data)
        except zlib.error:
            # urllib3 accepts trailing garbage after the first member.
            if later_member:
                return out
            raise
        data = decoder.unused_data
        if not data:
            return out + decoder.flush()
        later_member = True
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)


def inflate(data: bytes) -> bytes:
    decoder = zlib.decompressobj()
    try:
        out = decoder.decompress(data)
    except zlib.error:
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
        out = decoder.decompress(data)
    return out + decoder.flush()


DECODERS = {"gzip": gunzip, "x-gzip": gunzip, "deflate": inflate}


def decode_content(encoding: str | None, data: bytes) -> bytes:
    encoding = (encoding or "").lower()
    if encoding in DECODERS:
        return DECODERS[encoding](data)
    names = [name.strip() for name in encoding.split(",")]
    if "," in encoding and any(name in DECODERS for name in names):
        # A list is decoded last-applied first, and urllib3 decodes a name it
        # does not know in such a list as deflate.
        for name in reversed(names):
            data = DECODERS.get(name, inflate)(data)
    return data


def send(host: str, method: str, body: object | None) -> tuple[int, str | None, bytes]:
    headers = dict(HEADERS)
    payload = None
    if body is not None:
        # requests serializes `json=` with json.dumps and encodes it as UTF-8.
        payload = json.dumps(body, allow_nan=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(payload))
    path = "/" if method == "GET" else "/sentiment"
    connection = http.client.HTTPConnection(host, PORT)
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = response.read()
        content_type = response.getheader("Content-Type")
        # requests' HTTPAdapter.build_response computes the encoding of every
        # response, the GET's included, and raises on a bare `charset`.
        header_encoding(content_type)
        data = decode_content(response.getheader("Content-Encoding"), data)
        return response.status, content_type, data
    finally:
        connection.close()


# requests.utils.get_encoding_from_headers and _parse_content_type_header.
def header_encoding(content_type: str | None) -> str | None:
    if not content_type:
        return None
    tokens = content_type.split(";")
    media, params = tokens[0].strip(), {}
    for param in tokens[1:]:
        param = param.strip()
        if param:
            key, value = param, True
            equals = param.find("=")
            if equals != -1:
                key = param[:equals].strip("\"' ")
                value = param[equals + 1 :].strip("\"' ")
            params[key.lower()] = value
    if "charset" in params:
        return params["charset"].strip("'\"")  # a bare `charset` raises, as in requests
    if "text" in media:
        return "ISO-8859-1"
    if "application/json" in media:
        return "utf-8"
    return None


# requests.utils.guess_json_utf.
def guess_json_utf(data: bytes) -> str | None:
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"
    nullcount = sample.count(b"\x00")
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == b"\x00\x00":
            return "utf-16-be"
        if sample[1::2] == b"\x00\x00":
            return "utf-16-le"
    if nullcount == 3:
        if sample[:3] == b"\x00\x00\x00":
            return "utf-32-be"
        if sample[1:] == b"\x00\x00\x00":
            return "utf-32-le"
    return None


def response_json(content_type: str | None, data: bytes) -> object:
    """requests.models.Response.json; raises when requests raises."""
    encoding = header_encoding(content_type)
    if not encoding and data and len(data) > 3:
        guessed = guess_json_utf(data)
        if guessed is not None:
            try:
                return json.loads(data.decode(guessed))
            except UnicodeDecodeError:
                pass
    if not data:
        text = ""
    else:
        # requests falls back to charset_normalizer's guess here; the stock
        # interpreter has no charset_normalizer, so this takes UTF-8.
        try:
            text = str(data, encoding or "utf-8", errors="replace")
        except (LookupError, TypeError):
            text = str(data, errors="replace")
    return json.loads(text)


def kind(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, float):
        return "float"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "list"
    return "dict"


def typed(container: object, key: str) -> dict:
    """The type and, for strings and floats, the value of `container[key]`."""
    if not isinstance(container, dict) or key not in container:
        return {"type": "absent"}
    value = container[key]
    report: dict = {"type": kind(value)}
    if isinstance(value, str):
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError:
            encoded = None
        # A longer string cannot equal a label, so its value is not needed.
        if encoded is not None and len(encoded) <= STRING_BYTES:
            report["string"] = value
    elif isinstance(value, float):
        if math.isfinite(value):
            report["number"] = value
        elif math.isnan(value):
            report["nonfinite"] = "nan"
        else:
            report["nonfinite"] = "inf" if value > 0 else "-inf"
    return report


def exchange(host: str, method: str, body: object | None) -> tuple[dict, object]:
    """Send one request; report how it ended and return the decoded body, if any."""
    try:
        status, content_type, data = send(host, method, body)
    except Exception as error:
        return {"error": describe(error)}, None
    report: dict = {"status": status}
    try:
        decoded = response_json(content_type, data)
    except Exception:
        report["json"] = "invalid"
        return report, None
    report["json"] = kind(decoded)
    return report, decoded


def main() -> None:
    challenge = json.load(sys.stdin)
    if start_service():
        wait_for_port()

    # test_flask_api_running: requests.get("http://0.0.0.0:5000") must not fail.
    try:
        status, _, _ = send("0.0.0.0", "GET", None)
        root = {"status": status}
    except Exception as error:
        root = {"error": describe(error)}

    # test_sentiment_endpoint.
    sentiment = []
    for text in challenge["texts"]:
        report, result = exchange("localhost", "POST", {"text": text})
        if report.get("json") == "dict":
            report["sentiment"] = typed(result, "sentiment")
            report["confidence"] = typed(result, "confidence")
            confidence = result.get("confidence")
            report["positive"] = typed(confidence, "positive")
            report["negative"] = typed(confidence, "negative")
        sentiment.append(report)

    # test_api_error_handling: `"error" in error_data`, which is a key test on
    # an object, a membership test on an array and a substring test on a string.
    invalid, error_data = exchange("localhost", "POST", challenge["invalid_request"])
    if invalid.get("json") in ("dict", "list", "str"):
        invalid["has_member"] = challenge["error_member"] in error_data

    observation = {"root": root, "sentiment": sentiment, "invalid_request": invalid}
    sys.stdout.write(json.dumps({"observation": observation}, allow_nan=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
