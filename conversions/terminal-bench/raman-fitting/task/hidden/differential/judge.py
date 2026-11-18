# Judges the observations gen.py recorded with the pack's Oracle and reports every case where
# its verdict differs from upstream's test. Run on the host from the repository root:
# uv run python -B judge.py <out.json> <task>/hidden/oracle.py <task>/hidden
import json, sys, importlib.util
from securebench.core.evidence import CaseEvidence, HostFacts, Ending, Observed
from securebench.core.jsondata import decode
spec = importlib.util.spec_from_file_location("o", sys.argv[2]); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
class R:
    def read_json(self, p): return json.load(open(sys.argv[3] + "/" + p))
plan = o.plan(R(), 0)
ctx = {c.context["test"]: c.context for c in plan.cases["results"]}
names = {"exists": "test_result_file_exists", "G": "test_G_Peak", "2D": "test_2D_Peak"}
bad = 0; n = 0
for r in json.load(open(sys.argv[1])):
    for k, test in names.items():
        n += 1
        raw = r["obs"][k]
        try:
            env = decode(raw.encode(), 4096)
            ev = CaseEvidence("results", 0, "", HostFacts(Ending.RETURNED, 0, 0.1), Observed(env["observation"]), ())
            ours = o.judge("results", ctx[test], ev).passed
        except Exception as exc:
            ours = "ERR %r %s" % (exc, raw[:100])
        if ours != r["upstream"][k]:
            bad += 1; print("DIFF", k, r["doc"][:100], r["upstream"][k], ours)
print("compared", n, "disagreements", bad)
