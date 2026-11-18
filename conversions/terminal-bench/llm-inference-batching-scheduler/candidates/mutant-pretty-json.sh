#!/bin/sh
# Each record pretty-printed over several lines, like the example in the
# instructions. Upstream parses one JSON value per line; aimed at the adapter's
# reading of JSON Lines.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 "$(dirname "$0")/rewrite_plans.py" pretty-json
