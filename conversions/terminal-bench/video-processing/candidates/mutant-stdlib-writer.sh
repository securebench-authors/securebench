#!/bin/sh
# Drops the toml dependency: writes output.toml by hand, with float frame
# numbers and CRLF line endings, and reads it back with the standard library's
# tomllib. Correct per upstream (floats compare numerically, toml 0.10.2 reads
# CRLF through io.open). Aimed at the adapter's value conversion and at the
# Oracle's standard library list, which must accept tomllib.
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
path = "/app/jump_analyzer.py"
source = open(path).read()
source = source.replace("import toml\n", "import tomllib\n", 1)
old = """        with open(output_path, 'w') as f:
            toml.dump(toml_data, f)
        """
new = """        with open(output_path, 'w', newline='') as f:
            f.write('jump_takeoff_frame_number = %r\\r\\n' % float(jump_start))
            f.write('jump_land_frame_number = %r\\r\\n' % float(jump_end))
        with open(output_path, 'rb') as f:
            tomllib.load(f)
        """
assert source.count(old) == 1
source = source.replace(old, new)
open(path, "w").write(source)
PY
