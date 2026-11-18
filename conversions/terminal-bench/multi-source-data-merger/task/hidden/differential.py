"""Differential test of the checks against upstream's tests.

Each case is a pair of deliverables, the reference's with one change. The
native side runs the three functions of upstream's tests/test_outputs.py on
pandas 2.3.3, pyarrow 22.0.0 and Python 3.13, as upstream's verifier does. The
SecureBench side runs evaluation/adapter.py on the baseline's pandas 2.2.3,
pyarrow 17.0.0 and Python 3.11, then this pack's Oracle. Not part of any run.

From conversions/terminal-bench/multi-source-data-merger, with B the pinned
baseline image and W a scratch directory:

1. In B with no network, generate the cases with B's pyarrow and read each one
   with the adapter:
       docker run --rm --network none -v "$PWD/candidates:/candidates:ro" \
         -v "$PWD/task:/task:ro" -v "W:/w" B \
         sh -c 'sh /candidates/reference.sh >/dev/null &&
                python3 -I -B /task/hidden/differential.py generate /w/cases &&
                python3 -I -B /task/hidden/differential.py observe /w/cases /w/observed'
2. In a container of B that has run the first half of upstream's tests/test.sh
   (curl, uv 0.9.5) and has upstream's tests in /tests:
       uvx -p 3.13 -w pytest==8.4.1 -w pandas==2.3.3 -w pyarrow==22.0.0 \
         python -I /task/hidden/differential.py native /w/cases > W/native.json
3. On the host, with the SecureBench checkout:
       uv run python -B task/hidden/differential.py judge W/observed W/native.json task
"""

import json
import os
import shutil
import subprocess
import sys

MERGED = "/app/merged_users.parquet"
CONFLICTS = "/app/conflicts.json"


def generate(out):
    """Write each case to out/<name>/ from the reference's outputs in /app."""
    from decimal import Decimal

    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    base = pd.read_parquet(MERGED)
    with open(CONFLICTS, encoding="utf-8") as stream:
        report = json.load(stream)
    cases = {}

    def frame_case(name, frame, **options):
        cases[name] = ("frame", frame, options)

    def table_case(name, table, **options):
        cases[name] = ("table", table, options)

    def report_case(name, text):
        cases[name] = ("report", text, {})

    def edited(change):
        copy = json.loads(json.dumps(report))
        change(copy)
        return json.dumps(copy)

    def row(frame, user):
        return frame.index[frame["user_id"] == user][0]

    table = pa.Table.from_pandas(base, preserve_index=False)
    frame_case("reference", base)
    frame_case("user_id-int32", base.astype({"user_id": "int32"}))
    frame_case("user_id-uint64", base.astype({"user_id": "uint64"}))
    frame_case("user_id-nullable-Int64", base.astype({"user_id": "Int64"}))
    frame_case("user_id-int8", base.astype({"user_id": "int8"}))
    frame_case("user_id-float64", base.astype({"user_id": "float64"}))
    frame_case("user_id-string", base.astype({"user_id": "str"}))
    decimals = pa.array([Decimal(int(v)) for v in base["user_id"]], pa.decimal128(5, 0))
    table_case("user_id-decimal", table.set_column(0, "user_id", decimals))
    scaled = pa.array([Decimal(int(v)).quantize(Decimal("0.01")) for v in base["user_id"]], pa.decimal128(7, 2))
    table_case("user_id-decimal-scaled", table.set_column(0, "user_id", scaled))
    frame_case("user_id-float-with-nan", base.assign(user_id=base["user_id"].astype("float64").where(base["user_id"] != 103)))
    frame_case("created_date-date32", base.assign(created_date=pd.to_datetime(base["created_date"]).dt.date))
    frame_case("created_date-timestamp", base.assign(created_date=pd.to_datetime(base["created_date"])))
    large = pa.schema([(f.name, pa.large_string() if f.name == "created_date" else f.type) for f in table.schema])
    table_case("created_date-large_string", table.cast(large))
    frame_case("name-categorical", base.astype({"name": "category"}))
    frame_case("strings-pandas-string-dtype", base.astype({"name": "string", "email": "string", "created_date": "string"}))
    frame_case("columns-reordered-and-extra", base[["status", "created_date", "email", "name", "user_id"]].assign(_source="x"))
    frame_case("no-status-column", base.drop(columns=["status"]))
    frame_case("rows-shuffled", base.iloc[[3, 1, 0, 2]])
    frame_case("index-stored", base.set_axis([10, 11, 12, 13]), index=True)
    frame_case("user_id-as-index", base.set_index("user_id"), index=True)
    frame_case("five-rows-duplicate-101", pd.concat([base, base.iloc[[0]]], ignore_index=True))
    frame_case("three-rows", base[base["user_id"] != 103])
    frame_case("five-rows-extra-user", pd.concat([base, base.iloc[[0]].assign(user_id=105)], ignore_index=True))
    for label, user, column, value in (
        ("102-name-Jane", 102, "name", "Jane"),
        ("103-email-null", 103, "email", None),
        ("103-created_date-slashes", 103, "created_date", "2024/03/01"),
        ("101-name-trailing-space", 101, "name", "John Doe "),
        ("101-created_date-unpadded", 101, "created_date", "2024-1-15"),
        ("104-email-uppercase", 104, "email", "ALICE@c.com"),
    ):
        changed = base.copy()
        changed.loc[row(changed, user), column] = value
        frame_case(label, changed)
    for compression in ("none", "gzip", "zstd", "brotli"):
        frame_case(f"compression-{compression}", base, compression=compression)
    table_case("parquet-1.0-data-page-v2", table, version="1.0", data_page_version="2.0")
    table_case("duplicate-name-column", pa.table([*table.columns, table.column("name")], names=[*table.column_names, "name"]))
    # pandas reads a Parquet list column as one numpy array per cell.
    strings = pa.list_(pa.string())
    nested_strings = pa.list_(strings)

    def listed(table, column, values, kind):
        return table.set_column(table.column_names.index(column), column, pa.array(values, kind))

    def lists(column, user=None, value=None):
        values = [[item] for item in base[column]]
        if user is not None:
            values[int(row(base, user))] = value
        return values

    for column in ("name", "email", "created_date"):
        table_case(f"{column}-list", listed(table, column, lists(column), strings))
    all_lists = table
    for column in ("name", "email", "created_date"):
        all_lists = listed(all_lists, column, lists(column), strings)
    table_case("strings-all-lists", all_lists)
    table_case("name-nested-list", listed(table, "name", [[v] for v in lists("name")], nested_strings))
    table_case("101-name-empty-list", listed(table, "name", lists("name", 101, []), strings))
    table_case("101-name-two-element-list", listed(table, "name", lists("name", 101, ["John Doe", "John Doe"]), strings))
    table_case("101-name-nested-two-element-list", listed(table, "name", [[v] for v in lists("name", 101, ["John Doe", "John Doe"])], nested_strings))
    table_case("101-name-list-wrong", listed(table, "name", lists("name", 101, ["John D."]), strings))
    table_case("102-name-two-element-list", listed(table, "name", lists("name", 102, ["Jane Smith", "Jane Smith"]), strings))
    cases["directory-partitioned-by-status"] = ("directory", base, {})
    cases["empty-file"] = ("empty", None, {})

    report_case("conflicts-reference", json.dumps(report))
    report_case("conflicts-indented", json.dumps(report, indent=4))
    report_case("total-float", edited(lambda r: r.update(total_conflicts=3.0)))
    report_case("total-string", edited(lambda r: r.update(total_conflicts="3")))
    report_case("total-4-with-3-listed", edited(lambda r: r.update(total_conflicts=4)))
    report_case("total-infinity", json.dumps(report).replace('"total_conflicts": 3', '"total_conflicts": Infinity'))
    status = {"user_id": 101, "field": "status", "values": {"source_a": "active", "source_b": True, "source_c": True}, "selected": "active"}
    report_case("extra-status-conflict", edited(lambda r: (r["conflicts"].append(status), r.update(total_conflicts=4))))
    report_case(
        "extra-status-conflict-with-nan",
        edited(lambda r: (r["conflicts"].append({**status, "values": {"source_a": "active", "source_b": "NAN_HERE"}}), r.update(total_conflicts=4))).replace('"NAN_HERE"', "NaN"),
    )
    other = {"user_id": 102, "field": "name", "values": {"source_a": "Jane Smith", "source_b": None}, "selected": "Jane Smith"}
    report_case("extra-conflict-for-102", edited(lambda r: (r["conflicts"].append(other), r.update(total_conflicts=4))))
    bookkeeping = {"user_id": 101, "field": "_source", "values": {"source_a": "source_a", "source_b": "source_b", "source_c": "source_c"}, "selected": "source_a"}
    report_case("extra-conflict-on-_source", edited(lambda r: (r["conflicts"].append(bookkeeping), r.update(total_conflicts=4))))
    report_case("status-conflict-twice", edited(lambda r: (r["conflicts"].extend([status, status]), r.update(total_conflicts=5))))
    report_case("email-listed-twice", edited(lambda r: (r["conflicts"].append(r["conflicts"][1]), r.update(total_conflicts=4))))
    report_case("only-email", edited(lambda r: r.update(conflicts=[r["conflicts"][1]], total_conflicts=1)))
    report_case("no-email", edited(lambda r: r.update(conflicts=[r["conflicts"][0], r["conflicts"][2]], total_conflicts=2)))
    report_case("conflicts-user_id-float", edited(lambda r: [c.update(user_id=101.0) for c in r["conflicts"]]))
    report_case("conflicts-user_id-string", edited(lambda r: [c.update(user_id="101") for c in r["conflicts"]]))
    report_case("selected-repeated-key", json.dumps(report).replace('"selected": "John Doe"', '"selected": "John D.", "selected": "John Doe"'))
    report_case("byte-order-mark", "\ufeff" + json.dumps(report))
    report_case("conflicts-as-object", edited(lambda r: r.update(conflicts={str(i): c for i, c in enumerate(r["conflicts"])})))
    report_case("top-level-list", json.dumps(report["conflicts"]))
    report_case("entry-without-field", edited(lambda r: r["conflicts"][0].pop("field")))
    report_case("email-without-source_c", edited(lambda r: r["conflicts"][1]["values"].pop("source_c")))
    report_case("dates-with-time", edited(lambda r: r["conflicts"][2].update(values={k: v + " 00:00:00" for k, v in r["conflicts"][2]["values"].items()})))
    report_case("name-selected-wrong", edited(lambda r: r["conflicts"][0].update(selected="John D.")))
    report_case("email-selected-wrong", edited(lambda r: r["conflicts"][1].update(selected="john@c.com")))
    report_case("email-source_a-wrong", edited(lambda r: r["conflicts"][1]["values"].update(source_a="john@b.com")))
    report_case("field-capitalized", edited(lambda r: [c.update(field=c["field"].capitalize()) for c in r["conflicts"]]))
    report_case("claims-pass", edited(lambda r: r.update(passed=True, verdict="all tests passed")))
    report_case("extra-entry-keys", edited(lambda r: [c.update(resolution="priority") for c in r["conflicts"]]))
    report_case("no-conflicts", json.dumps({"total_conflicts": 0, "conflicts": []}))
    report_case("total-true-one-entry", edited(lambda r: r.update(conflicts=[r["conflicts"][1]], total_conflicts=True)))
    report_case("entry-other-user-without-field", edited(lambda r: (r["conflicts"].append({"user_id": 102}), r.update(total_conflicts=4))))
    report_case("entry-without-user_id", edited(lambda r: (r["conflicts"].append({"field": "name"}), r.update(total_conflicts=4))))
    report_case("entry-not-object", edited(lambda r: (r["conflicts"].append("x"), r.update(total_conflicts=4))))
    report_case("no-conflict-for-101", edited(lambda r: [c.update(user_id=102) for c in r["conflicts"]]))
    report_case("second-email-conflict-wrong", edited(lambda r: (r["conflicts"].append({**r["conflicts"][1], "selected": "x"}), r.update(total_conflicts=4))))
    report_case("first-email-conflict-wrong", edited(lambda r: (r["conflicts"].insert(0, {**r["conflicts"][1], "selected": "x"}), r.update(total_conflicts=4))))
    report_case("email-values-not-object", edited(lambda r: r["conflicts"][1].update(values="john@a.com")))
    report_case("email-without-selected", edited(lambda r: r["conflicts"][1].pop("selected")))
    report_case("conflicts-as-string", edited(lambda r: r.update(conflicts="abc")))
    report_case("empty-object", "{}")
    cases["latin-1-bytes"] = ("report-bytes", json.dumps(report).replace("John D.", "Jos\u00e9 D.").encode("latin-1"), {})

    for name, (kind, value, options) in cases.items():
        folder = os.path.join(out, name)
        os.makedirs(folder)
        merged = os.path.join(folder, "merged_users.parquet")
        conflicts = os.path.join(folder, "conflicts.json")
        shutil.copyfile(CONFLICTS, conflicts)
        if kind in ("report", "report-bytes"):
            shutil.copyfile(MERGED, merged)
            with open(conflicts, "wb") as stream:
                stream.write(value.encode("utf-8") if kind == "report" else value)
        elif kind == "frame":
            value.to_parquet(merged, **{"index": False, **options})
        elif kind == "table":
            pq.write_table(value, merged, **options)
        elif kind == "directory":
            value.to_parquet(merged, partition_cols=["status"], index=False)
        else:
            open(merged, "wb").close()


def observe(cases, out):
    """Run the adapter on each case from /app, as an Evaluation would."""
    os.makedirs(out)
    for name in sorted(os.listdir(cases)):
        for target in (MERGED, CONFLICTS):
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.exists(target):
                os.remove(target)
            source = os.path.join(cases, name, os.path.basename(target))
            (shutil.copytree if os.path.isdir(source) else shutil.copyfile)(source, target)
        for check in ("merged", "conflicts"):
            ran = subprocess.run(
                ["/usr/local/bin/python3", "-I", "-B", "/task/evaluation/adapter.py", check],
                input=b"{}", capture_output=True, cwd="/app", check=True,
            )
            with open(os.path.join(out, f"{name}.{check}.json"), "wb") as stream:
                stream.write(ran.stdout)


def native(cases):
    """Upstream's three test functions on each case; prints {case: passed}."""
    sys.path.insert(0, "/tests")
    import test_outputs

    verdicts = {}
    for name in sorted(os.listdir(cases)):
        for target in (MERGED, CONFLICTS):
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.exists(target):
                os.remove(target)
            source = os.path.join(cases, name, os.path.basename(target))
            (shutil.copytree if os.path.isdir(source) else shutil.copyfile)(source, target)
        passed = True
        for test in (test_outputs.test_output_files_exist, test_outputs.test_merged_data_exact_values, test_outputs.test_conflict_report_values):
            try:
                test()
            except Exception:
                passed = False
        verdicts[name] = passed
    print(json.dumps(verdicts, indent=1, sort_keys=True))


def judge(observed, native_path, task):
    """Judge each observation with the Oracle and print both verdicts side by side."""
    import importlib.util

    from securebench.core.evidence import CaseEvidence, Ending, HostFacts, Observed, Unable

    spec = importlib.util.spec_from_file_location("oracle", os.path.join(task, "hidden", "oracle.py"))
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)

    class Hidden:
        def read(self, path):
            with open(os.path.join(task, "hidden", path), "rb") as stream:
                return stream.read()

        def read_json(self, path):
            return json.loads(self.read(path))

    plan = oracle.plan(Hidden(), 0)
    with open(native_path, encoding="utf-8") as stream:
        verdicts = json.load(stream)
    for name in sorted(verdicts):
        reasons = []
        for check in ("merged", "conflicts"):
            with open(os.path.join(observed, f"{name}.{check}.json"), encoding="utf-8") as stream:
                envelope = json.load(stream)
            if "observation" in envelope:
                outcome = Observed(envelope["observation"])
            else:
                outcome = Unable(envelope["unable"]["code"], envelope["unable"]["message"])
            evidence = CaseEvidence(check, 0, "sha256:0", HostFacts(Ending.RETURNED, 0, 0.0), outcome, ())
            judgment = oracle.judge(check, plan.cases[check][0].context, evidence)
            if not judgment.passed:
                reasons.append(f"{check}: {judgment.diagnostic['reason']}")
        securebench = not reasons
        mark = "  " if securebench == verdicts[name] else "**"
        print(f"{mark} {name:40} native {'pass' if verdicts[name] else 'fail'}  securebench {'pass' if securebench else 'fail'}  {'; '.join(reasons)}")


if __name__ == "__main__":
    command, *arguments = sys.argv[1:]
    {"generate": generate, "observe": observe, "native": native, "judge": judge}[command](*arguments)
