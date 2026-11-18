#!/bin/sh
set -eu
cd /app
python3 "$(dirname "$0")/summarize.py" csv-writer
