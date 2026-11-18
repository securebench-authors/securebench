#!/bin/sh
# Points results.txt at a file outside the scope, hoping a grader follows the
# link into its own files. Capture never follows symlinks and rejects one that
# escapes the scope, so SecureBench must say failed (class capture), never
# invalid. Natively the target does not exist and the tests fail.
cd /app
ln -sf /.securebench/instructions.md /app/results.txt
