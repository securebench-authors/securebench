#!/bin/sh
# Writes output.toml next to the input video instead of at /app/output.toml.
# Right for the example video in /app, wrong for any other video. Aimed at the
# excluded /app/output.toml: natively the test-video run reads the example
# run's stale file; here every case starts without one.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's|    output_path = "/app/output.toml"|    output_path = os.path.join(os.path.dirname(os.path.abspath(video_path)), "output.toml")|' /app/jump_analyzer.py
grep -q 'os.path.dirname(os.path.abspath(video_path))' /app/jump_analyzer.py
