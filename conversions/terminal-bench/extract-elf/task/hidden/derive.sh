#!/bin/sh
# Rederives hidden/cases.json the way upstream's test_output_matches_reference
# does at grading time: compile new.c with the baseline's gcc, then run the
# upstream reference script (hidden/ref.js, the REF string of
# tests/test_outputs.py, stripped as the test strips it) on the binary.
# It also confirms that the compiled binary is byte for byte hidden/new.o,
# which plan sends to the adapter in the case's challenge.
#
# Run from anywhere on a host with Docker: sh task/hidden/derive.sh
set -eu
pack="$(cd "$(dirname "$0")/.." && pwd)"
image="alexgshaw/extract-elf@sha256:6932e4cb318464307eacd497ef8dc617eaf551b6a90231f815ec0b911895cfed"

docker run --rm --network none --memory 1g --user "$(id -u):$(id -g)" \
  -v "$pack/hidden:/pack-hidden" \
  -w /tmp "$image" sh -eu -c '
    cp /pack-hidden/new.c /tmp/new.c
    gcc -o /tmp/new.o /tmp/new.c
    cmp /tmp/new.o /pack-hidden/new.o
    node /pack-hidden/ref.js /tmp/new.o > /tmp/reference.json
    python3 -I -c "
import json
with open(\"/tmp/reference.json\") as f:
    reference = json.load(f)
cases = [{\"program\": \"new.c\", \"binary\": \"new.o\", \"reference\": reference}]
with open(\"/pack-hidden/cases.json\", \"w\") as f:
    json.dump(cases, f, indent=1, sort_keys=True)
    f.write(\"\\n\")
print(len(reference), \"reference entries\")
"
  '
