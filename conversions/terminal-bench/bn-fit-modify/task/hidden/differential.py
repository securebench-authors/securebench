"""Compare the Oracle's verdicts with upstream's tests run on pandas and scipy.

Not used in grading; kept so a reviewer can repeat the comparison recorded in
CONVERSION.md. Run it in a container with Python 3.13, pandas 2.3.2 and scipy
1.16.1, with this directory mounted at /pack/hidden:

    python3 -B differential.py 3000

The argument is the number of random samples drawn for the KS comparison.
"""
import io, json, math, random, sys, types
from dataclasses import dataclass
from enum import Enum

# Minimal stand-ins for the securebench types the Oracle imports.
ev = types.ModuleType("securebench.core.evidence")
class FileStatus(Enum):
    PRESENT = "present"
@dataclass
class Text:
    text: str
    lines: tuple
@dataclass
class Judgment:
    passed: bool
    diagnostic: object
@dataclass
class FileEvidence:
    path: str
    status: FileStatus
    value: object
@dataclass
class ArtifactEvidence:
    check_id: str
    files: tuple
    listings: tuple
for name, obj in dict(FileStatus=FileStatus, Text=Text, Judgment=Judgment, ArtifactEvidence=ArtifactEvidence,
                      CaseEvidence=type("CaseEvidence", (), {}), HiddenResources=object,
                      Plan=lambda **k: k).items():
    setattr(ev, name, obj)
jd = types.ModuleType("securebench.core.jsondata"); jd.JsonValue = object
for n in ("securebench", "securebench.core"):
    sys.modules[n] = types.ModuleType(n)
sys.modules["securebench.core.evidence"] = ev
sys.modules["securebench.core.jsondata"] = jd
sys.path.insert(0, "/pack/hidden")
import oracle
import pandas
from scipy.stats import kstest

expected = json.load(open("/pack/hidden/expected.json"))

def native_sample(text):
    try:
        df = pandas.read_csv(io.StringIO(text))
        assert not df.empty
        assert all(c in df.columns for c in ["U", "R", "Y", "M", "D"])
        assert len(df) == 10_000
        assert len(df.columns) == 5
        true_mean = -12.2965135 + 0.5495886 * 50.47989
        true_std = ((0.5495886**2) * 10.68515**2 + 14.0916**2) ** 0.5
        stat, p = kstest(df["D"], "norm", args=(true_mean, true_std))
        assert p >= 0.001
        return True
    except Exception:
        return False

def native_dag(text, check):
    try:
        df = pandas.read_csv(io.StringIO(text))
        assert not df.empty
        assert all(c in df.columns for c in ["from", "to"])
        edges = {(row["from"], row["to"]) for _, row in df.iterrows()}
        return edges == {tuple(e) for e in expected[check]["edges"]}
    except Exception:
        return False

def ours(text, check):
    evidence = ArtifactEvidence(check, (FileEvidence("/app/x", FileStatus.PRESENT, Text(text, ())),), ())
    return oracle.judge(check, expected[check], evidence).passed

mean, std = expected["bn-sample"]["mean"], expected["bn-sample"]["std"]
mismatches = 0
def compare(label, text, check="bn-sample"):
    global mismatches
    n = native_sample(text) if check == "bn-sample" else native_dag(text, check)
    o = ours(text, check)
    if n != o:
        mismatches += 1
        print("MISMATCH", label, "native", n, "oracle", o)
    return n

# 1. KS verdicts near the threshold: samples drawn with a mean shift that puts
# the statistic close to the bound.
rng = random.Random(1)
import numpy as np
from scipy.stats import norm
near = passes = 0
max_stat_diff = 0.0
for trial in range(int(sys.argv[1])):
    shift = rng.uniform(0.0, 0.04) * std
    values = [rng.gauss(mean + shift, std) for _ in range(10000)]
    ours_stat = oracle.ks_statistic(values, mean, std)
    native_stat = kstest(values, "norm", args=(mean, std)).statistic
    max_stat_diff = max(max_stat_diff, abs(ours_stat - native_stat))
    if abs(native_stat - expected["bn-sample"]["max_statistic"]) < 0.002:
        near += 1
        lines = ["U,R,Y,M,D"] + [f"1,2,3,4,{v!r}" for v in values]
        passes += compare(f"ks trial {trial}", "\n".join(lines) + "\n")
print("ks: near-threshold samples", near, "native passes", passes, "max |statistic diff|", max_stat_diff)
z = np.linspace(-40, 40, 400001)
print("ndtr max abs diff", max(abs(oracle.normal_cdf(float(v)) - float(norm.cdf(v))) for v in z))

# 2. CSV forms around a good sample.
values = [mean + std * float(norm.ppf((i + 0.5) / 10000)) for i in range(10000)]
def sample(header, row, end="\n", extra=""):
    return header + end + end.join(row(i, v) for i, v in enumerate(values)) + end + extra
forms = {
    "plain": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v!r}"),
    "r-write-csv": sample('"U","R","Y","M","D"', lambda i, v: f"1,2,3,4,{v:.15g}"),
    "r-row-names": sample('"","U","R","Y","M","D"', lambda i, v: f'"{i+1}",1,2,3,4,{v}'),
    "write-table-implicit-index": sample('"U","R","Y","M","D"', lambda i, v: f'"{i+1}",1,2,3,4,{v}'),
    "pandas-index": sample(",U,R,Y,M,D", lambda i, v: f"{i},1,2,3,4,{v}"),
    "crlf": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}", end="\r\n"),
    "cr": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}", end="\r"),
    "reordered": sample("D,M,Y,R,U", lambda i, v: f"{v},1,2,3,4"),
    "quoted-values": sample("U,R,Y,M,D", lambda i, v: f'"a","b","c","d","{v}"'),
    "spaces": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,  {v} "),
    "space-header": sample("U, R,Y,M,D", lambda i, v: f"1,2,3,4,{v}"),
    "blank-lines": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}" + ("\n\n  \t" if i % 7 == 0 else "")),
    "nan-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'nan' if i == 5 else v}"),
    "na-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'NA' if i == 5 else v}"),
    "empty-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'' if i == 5 else v}"),
    "short-row": sample("U,R,Y,M,D", lambda i, v: "1,2,3,4" if i == 5 else f"1,2,3,4,{v}"),
    "short-row-other": sample("D,U,R,Y,M", lambda i, v: f"{v},1,2" if i == 5 else f"{v},1,2,3,4"),
    "long-row": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v},9" if i == 5 else f"1,2,3,4,{v}"),
    "inf-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'-Infinity' if i == 0 else v}"),
    "inf-space": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{' inf' if i == 0 else v}"),
    "overflow-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'1e999' if i == 0 else v}"),
    "bad-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'1_0' if i == 0 else v}"),
    "bigint-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'18446744073709551615' if i == 0 else v}"),
    "bigint2-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'18446744073709551616' if i == 0 else v}"),
    "leading-zeros-one": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'0000000000000000000000012' if i == 0 else v}"),
    "dup-d": sample("U,R,Y,M,D,D", lambda i, v: f"1,2,3,4,{v},x"),
    "dup-d-first-bad": sample("U,R,Y,D,D", lambda i, v: f"1,2,3,x,{v}"),
    "six-cols": sample("U,R,Y,M,D,E", lambda i, v: f"1,2,3,4,{v},5"),
    "missing-m": sample("U,R,Y,X,D", lambda i, v: f"1,2,3,4,{v}"),
    "extra-row": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}", extra="1,2,3,4,5\n"),
    "quoted-newline": sample("U,R,Y,M,D", lambda i, v: f'"a\nb",2,3,4,{v}'),
    "quoted-doubled": sample("U,R,Y,M,D", lambda i, v: f'"a""b",2,3,4,"{v}"'),
    "quote-then-text": sample("U,R,Y,M,D", lambda i, v: f'1,2,3,4,"{v}"0'),
    "unterminated": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}", extra='"1,2\n'),
    "no-final-newline": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}").rstrip("\n"),
    "trailing-comma": sample("U,R,Y,M,D,", lambda i, v: f"1,2,3,4,{v},"),
    "header-only": "U,R,Y,M,D\n",
    "empty": "",
    "ws-row-start": sample("U,R,Y,M,D", lambda i, v: f"  1,2,3,4,{v}"),
    "bool": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'True' if i % 2 else 'False'}"),
    "shifted": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v + 1.0}"),
    "two-leading": sample("U,R,Y,M,D", lambda i, v: f"{i},x,1,2,3,4,{v}"),
    "three-leading": sample("U,R,Y,M,D", lambda i, v: f"{i},x,y,1,2,3,4,{v}"),
    "two-leading-short": sample("U,R,Y,M,D", lambda i, v: f"{i},x,1,2,3,4" if i == 5 else f"{i},x,1,2,3,4,{v}"),
    "two-leading-long": sample("U,R,Y,M,D", lambda i, v: f"{i},x,1,2,3,4,{v},9" if i == 5 else f"{i},x,1,2,3,4,{v}"),
    "big-int-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9999999999999999999999999' if i == 0 else v}"),
    "big-int-row-1": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9999999999999999999999999' if i == 1 else v}"),
    "big-int-row-5000": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9999999999999999999999999' if i == 5000 else v}"),
    "big-int-row-9999": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9999999999999999999999999' if i == 9999 else v}"),
    "neg-big-int-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'-9999999999999999999999999' if i == 0 else v}"),
    "neg-big-int-row-7": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'-9999999999999999999999999' if i == 7 else v}"),
    "huge-int-overflow-row-7": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9' * 400 if i == 7 else v}"),
    "big-int-after-integer-rows": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{i if i < 3 else '9999999999999999999999999' if i == 3 else v}"),
    "plus-big-int-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'+9999999999999999999999999' if i == 0 else v}"),
    "spaced-big-int-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{' 9999999999999999999999999 ' if i == 0 else v}"),
    "uint64-max-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'18446744073709551615' if i == 0 else v}"),
    "int64-max-plus-1-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'9223372036854775808' if i == 0 else v}"),
    "long-zero-padded-int-row-0": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{'0' * 40 + '12' if i == 0 else v}"),
    "many-extra-rows": sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{v}", extra="1\n" * 5000),
}
pieces = ["", "+", "-", " ", "0", "1", "9", "12", "9223372036854775807", "9223372036854775808",
          "18446744073709551615", "18446744073709551616", "9" * 25, ".", "5", "e", "E", "+3", "-2", "308",
          "999", "inf", "Infinity", "nan", "NA", "_", "x", "\t"]
fuzz = random.Random(7)
for trial in range(400):
    token = "".join(fuzz.choice(pieces) for _ in range(fuzz.randint(1, 4)))
    if "," in token or '"' in token:
        continue
    row = fuzz.choice([0, 5])
    forms[f"fuzz {token!r} at row {row}"] = sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{token if i == row else v}")
# Integer sequences at the start of D, followed by the normal float values,
# and columns of integers only (the quantiles rounded).
B25, U19 = "9" * 25, "10000000000000000000"
starts = {
    "u19,b25": [U19, B25], "u19,-5,b25": [U19, "-5", B25], "u19,u19,b25": [U19, U19, B25],
    "u19,7x20,b25": [U19] + ["7"] * 20 + [B25], "-5,u19,b25": ["-5", U19, B25],
    "uint64max,b25": ["18446744073709551615", B25], "u19,inf,b25": [U19, "inf", B25],
    "u19,1e3,b25": [U19, "1e3", B25], "-b25,b25": ["-" + B25, B25], "-b25,1.5": ["-" + B25, "1.5"],
    "u19,-b25": [U19, "-" + B25], "u19,-0": [U19, "-0"],
}
for name, start in starts.items():
    forms[f"start {name}"] = sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{start[i] if i < len(start) else v}")
rounded = [str(round(v)) for v in values]
integer_columns = {
    "rounded": rounded,
    "rounded,u19": [U19] + rounded[1:],
    "rounded,u19,-0": [U19, "-0"] + rounded[2:],
    "rounded,-2^63-1": ["-9223372036854775809"] + rounded[1:],
    "rounded,uint64max": ["18446744073709551615"] + rounded[1:],
}
for name, column in integer_columns.items():
    forms[f"integers {name}"] = "U,R,Y,M,D\n" + "".join(f"1,2,3,4,{x}\n" for x in column)
choices = ["-5", "7", "-0", "+3", U19, "18446744073709551615", "9223372036854775807",
           "9223372036854775808", "-9223372036854775808", "-9223372036854775809", B25, "-" + B25,
           "1.5", "inf", "1e3", " " + B25]
for trial in range(300):
    start = [fuzz.choice(choices) for _ in range(fuzz.randint(1, 3))]
    forms[f"fuzz start {start}"] = sample("U,R,Y,M,D", lambda i, v: f"1,2,3,4,{start[i] if i < len(start) else v}")
for label, text in forms.items():
    verdict = compare(label, text)
    if not label.startswith(("fuzz", "start", "integers")):
        print(f"  {label}: native {verdict}")

good = [("U","M"),("U","Y"),("U","D"),("U","R"),("Y","D"),("R","M")]
def dag(header, rows, end="\n"):
    return header + end + end.join(rows) + end
dags = {
    "r-write-csv": dag('"from","to"', [f'"{a}","{b}"' for a, b in good]),
    "plain": dag("from,to", [f"{a},{b}" for a, b in good]),
    "to-from": dag("to,from", [f"{b},{a}" for a, b in good]),
    "to-from-wrong": dag("to,from", [f"{a},{b}" for a, b in good]),
    "dups": dag("from,to", [f"{a},{b}" for a, b in good + good[:2]]),
    "missing": dag("from,to", [f"{a},{b}" for a, b in good[:-1]]),
    "extra": dag("from,to", [f"{a},{b}" for a, b in good + [("M", "D")]]),
    "index": dag(',from,to', [f'{i},{a},{b}' for i, (a, b) in enumerate(good)]),
    "implicit-index": dag('from,to', [f'{i},{a},{b}' for i, (a, b) in enumerate(good)]),
    "spaces": dag("from, to", [f"{a}, {b}" for a, b in good]),
    "value-space": dag("from,to", [f"{a} ,{b}" for a, b in good]),
    "blank-row": dag("from,to", [f"{a},{b}" for a, b in good] + [""]),
    "comma-row": dag("from,to", [f"{a},{b}" for a, b in good] + [","]),
    "lower": dag("from,to", [f"{a.lower()},{b.lower()}" for a, b in good]),
    "header-only": "from,to\n",
    "crlf": dag("from,to", [f"{a},{b}" for a, b in good], end="\r\n"),
    "short-row": dag("from,to", [f"{a},{b}" for a, b in good] + ["U"]),
    "two-leading": dag("from,to", [f"{i},x,{a},{b}" for i, (a, b) in enumerate(good)]),
    "three-leading": dag("from,to", [f"{i},x,y,{a},{b}" for i, (a, b) in enumerate(good)]),
    "two-leading-long": dag("from,to", [f"{i},x,{a},{b}" for i, (a, b) in enumerate(good)] + ["1,2,3,4,5"]),
    "many-dups": dag("from,to", [f"{a},{b}" for a, b in good * 2000]),
}
for label, text in dags.items():
    verdict = compare(label, text, "learned-dag")
    print(f"  dag {label}: native {verdict}")
starts_fuzzed = sum(label.startswith("fuzz start") for label in forms)
fuzzed = sum(label.startswith("fuzz") for label in forms) - starts_fuzzed
print("sample forms", len(forms) - fuzzed - starts_fuzzed, "fuzzed tokens", fuzzed,
      "fuzzed D starts", starts_fuzzed, "dag forms", len(dags))
print("mismatches", mismatches)
