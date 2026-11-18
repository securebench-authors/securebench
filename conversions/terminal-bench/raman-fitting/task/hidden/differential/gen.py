# Differential between upstream's tests/test_outputs.py and this pack's adapter.
# Run: docker run --rm --network none -v <dir with this file, test_outputs.py, adapter.py>:/d <baseline> python /d/gen.py
# then judge.py on the host. Runs inside the baseline image: writes each crafted /app/results.json, records upstream's
# per-test verdict and the adapter's observation for each case.
import json, math, os, shutil, subprocess, sys, importlib.util
spec = importlib.util.spec_from_file_location("t", "/d/test_outputs.py"); t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
E = {"G": {"x0": (1580.3, "a", 5), "gamma": (9.06, "a", 1), "amplitude": (8382.69, "r", .05), "offset": (5561.03, "r", .1)},
     "2D": {"x0": (2670.08, "r", .05), "gamma": (17.52, "a", 1), "amplitude": (12314.42, "r", .05), "offset": (1239.09, "r", .1)}}
base = {p: {k: v[0] for k, v in f.items()} for p, f in E.items()}
def edge_values(e, mode, tol):
    out = []
    for sign in (1, -1):
        b = e + sign * tol if mode == "a" else e * (1 + sign * tol)
        for k in range(-3, 4):
            b2 = b
            for _ in range(abs(k)):
                b2 = math.nextafter(b2, math.inf if k > 0 else -math.inf)
            out.append(b2)
        out += [b * (1 + 1e-12), b * (1 - 1e-12), round(b), math.floor(b), math.ceil(b)]
    return out
docs = []
for p, f in E.items():
    for k, (e, mode, tol) in f.items():
        for v in edge_values(e, mode, tol):
            d = json.loads(json.dumps(base)); d[p][k] = v; docs.append(json.dumps(d))
        for raw in ['"1580.3"', 'null', 'true', 'false', '[1]', '{}', 'NaN', 'Infinity', '-Infinity', '1e999', '9' * 400, '9' * 5000, str(int(e)), '%r' % e]:
            # Write the raw JSON literal in place of this one field.
            parts = {pp: ", ".join(f'"{kk}": ' + (raw if (pp, kk) == (p, k) else repr(vv)) for kk, vv in base[pp].items()) for pp in base}
            docs.append("{" + ", ".join(f'"{pp}": {{{parts[pp]}}}' for pp in base) + "}")
        d = json.loads(json.dumps(base)); del d[p][k]; docs.append(json.dumps(d))
good = json.dumps(base)
docs += [good, "[]", '"x"', "1", "null", "{}", '{"G": "abc", "2D": [1]}', '{"G": 1}',
         '{"G": {"x0": 0, "gamma": 0, "amplitude": 0, "offset": 0}, ' + good[1:],  # duplicate keys, last wins
         good[:-1] + ', "G": {"x0": 0}}', '﻿' + good, good + "\n\n", good + "x",
         '{"G": {"x0": 1580.3, "gamma": 9.06, "amplitude": 8382.69, "offset": 5561.03, "err": NaN}, "2D": {"x0": 2670.08, "gamma": 17.52, "amplitude": 12314.42, "offset": 1239.09, "s": Infinity}}',
         "[" * 100000 + "]" * 100000, "", "MISSING", "DIR", "LATIN1"]
res = []
for doc in docs:
    path = "/app/results.json"
    if os.path.isdir(path): shutil.rmtree(path)
    elif os.path.exists(path): os.remove(path)
    if doc == "DIR": os.mkdir(path)
    elif doc == "LATIN1":
        open(path, "wb").write(('{"G": {"x0": 1580.3, "gamma": 9.06, "amplitude": 8382.69, "offset": 5561.03, "n": "\xe9"}, "2D": {"x0": 2670.08, "gamma": 17.52, "amplitude": 12314.42, "offset": 1239.09}}').encode("latin-1"))
    elif doc != "MISSING": open(path, "w", encoding="utf-8").write(doc)
    up = {}
    for name, fn in (("exists", t.test_result_file_exists), ("G", t.test_G_Peak), ("2D", t.test_2D_Peak)):
        try: fn(); up[name] = True
        except BaseException: up[name] = False
    obs = {}
    for name, ch in (("exists", {}), ("G", {"peak": "G"}), ("2D", {"peak": "2D"})):
        r = subprocess.run(["/usr/local/bin/python3", "-I", "/d/adapter.py"], input=json.dumps(ch), capture_output=True, text=True, cwd="/app")
        obs[name] = r.stdout if r.returncode == 0 else "EXIT %d %s" % (r.returncode, r.stderr[-200:])
    res.append({"doc": doc[:120], "upstream": up, "obs": obs})
json.dump(res, open("/d/out.json", "w"))
print(len(res))
