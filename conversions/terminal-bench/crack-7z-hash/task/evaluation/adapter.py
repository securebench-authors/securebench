"""Report the raw bytes of the file the challenge names.

The native test opens /app/solution.txt with open(), which follows symlinks,
so this adapter does the same. It returns the bytes unchanged; decoding,
stripping and comparing are the Oracle's job.
"""

import base64
import json
import sys

# Base64 of this many bytes, plus the envelope, stays below the check's
# max_observation_bytes (4 MiB).
LIMIT = 3_000_000


def respond(value: object) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    path = challenge["path"]
    try:
        with open(path, "rb") as handle:
            data = handle.read(LIMIT + 1)
    except OSError as error:
        respond({"unable": {"code": "unreadable", "message": f"{path}: {type(error).__name__}"}})
        return
    if len(data) > LIMIT:
        respond({"unable": {"code": "too-large", "message": f"{path} is larger than {LIMIT} bytes"}})
        return
    respond({"observation": {"content_base64": base64.b64encode(data).decode("ascii")}})


main()
