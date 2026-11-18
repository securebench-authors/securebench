#!/bin/sh
# A scheduler that just misses bucket 1's cost threshold (by under 1%). Aimed at
# the Oracle's transliteration of the cost model, which replaces upstream's.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 "$(dirname "$0")/near_threshold.py" over 1
