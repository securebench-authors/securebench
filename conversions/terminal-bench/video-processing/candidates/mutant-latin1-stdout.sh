#!/bin/sh
# Prints the velocity unit as a raw Latin-1 byte after writing a correct
# output.toml. The native test captures output with text=True, so the byte
# makes subprocess.run raise. Aimed at the adapter's UTF-8 decoding of the
# captured output, which reimplements that implicit native check.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's|^        print(f"Velocity: {velocity:.1f} ft/s")$|        print(f"Velocity: {velocity:.1f} ft/s", flush=True)\n        sys.stdout.buffer.write(b"(\\xb1 0.1 ft/s)\\n")|' /app/jump_analyzer.py
grep -q 'xb1' /app/jump_analyzer.py
