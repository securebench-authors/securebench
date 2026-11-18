"""Derives hidden/expected.json: the SHA-256 of the expected.csv that upstream's
generator (evaluation/gen_large_csv.py, a verbatim copy of tests/gen_large_csv.py)
writes in "expected" mode, which is the file upstream's test_input_equiv_expected
compares the transformed input.csv with.

Run from an empty directory, inside a container with a memory limit:

    python3 -I -B derive_expected.py <path to gen_large_csv.py>
"""

import hashlib
import json
import subprocess
import sys

subprocess.run([sys.executable, "-I", sys.argv[1], "expected"], check=True)
with open("expected.csv", "rb") as handle:
    digest = hashlib.sha256(handle.read()).hexdigest()
print(json.dumps({"input_sha256": digest}))
