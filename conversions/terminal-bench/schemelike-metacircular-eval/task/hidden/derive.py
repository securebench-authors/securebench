"""Derive hidden/cases.json for schemelike-metacircular-eval.

Run inside the baseline image, with upstream's tests/ mounted where upstream's
verifier mounts it:

    docker run --rm --network none --memory 2g --cpus 1 \
      -v <upstream task>/tests:/tests:ro -v <hidden>:/out <baseline image> \
      python3 -B /out/derive.py /out/cases.json

It uses upstream's own test_outputs.py functions: find_test_files for the
programs (tests/test and tests/shadow_test), detect_input_requirements for each
program's input, and run_scheme_direct, in a directory holding only upstream's
unmodified interp.py and the program, for the expected output. That is the
"direct" run upstream compares against, made with the interp.py the task
ships instead of the candidate's /app/interp.py. Each entry also records
whether upstream also runs the program through eval.scm twice ("05-simple",
"calculator.scm" and "closures.scm" in its path).
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("test_outputs", "/tests/test_outputs.py")
assert spec is not None and spec.loader is not None
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)

cases = []
for test_file in upstream.find_test_files():
    name = os.path.basename(test_file)
    test_input = upstream.detect_input_requirements(test_file)
    with tempfile.TemporaryDirectory() as directory:
        shutil.copy2("/tests/interp.py", directory)
        shutil.copy2(test_file, directory)
        os.chdir(directory)
        stdout, stderr, code = upstream.run_scheme_direct(name, test_input)
        os.chdir("/")
    if code != 0 or stderr:
        raise SystemExit(f"{test_file}: direct run failed ({code}): {stderr}")
    cases.append(
        {
            "suite": Path(test_file).parent.name,
            "name": name,
            "program": Path(test_file).read_text(encoding="utf-8"),
            "input": test_input or "",
            "expected": stdout,
            "twice": "05-simple" in test_file
            or "calculator.scm" in test_file
            or "closures.scm" in test_file,
        }
    )

Path(sys.argv[1]).write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
print(f"{len(cases)} programs, {sum(case['twice'] for case in cases)} also run twice")
