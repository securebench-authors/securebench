#!/bin/sh
# Opens output.toml in append mode instead of truncating it. The first run in a
# fresh /app writes a correct file; a later run adds a second set of keys, which
# toml 0.10.2 rejects as duplicates. Aimed at the state the test-video run
# inherits from the example-video run, which the adapter replays.
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
path = "/app/jump_analyzer.py"
source = open(path).read()
old = """        # Save TOML file
        with open(output_path, 'w') as f:"""
assert source.count(old) == 1
source = source.replace(old, """        # Save TOML file
        with open(output_path, 'a') as f:""")
open(path, "w").write(source)
PY
