"""Run the simulator on the candidate's /app/gates.txt for one input.

The setup command has already compiled /.securebench/evaluation/sim.c (a
copy of upstream's tests/sim.c) to /app/sim, as upstream's test compiles
/tests/sim.c to ./sim in /app. Like upstream's test, this runs `/app/sim N`
in /app, where the simulator reads gates.txt. The adapter reports the exit
status and the lines the simulator printed; the Oracle decides.
"""

import json
import subprocess
import sys

challenge = json.load(sys.stdin)
result = subprocess.run(
    ["/app/sim", str(challenge["n"])],
    cwd="/app",
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    check=False,
)
# The simulator prints only digits; a replaced character can only fail the Oracle's check.
lines = result.stdout.decode("utf-8", "replace").split("\n")
if lines[-1] == "":
    lines.pop()
observation = {"exit_status": result.returncode, "stdout_lines": lines}
sys.stdout.write(json.dumps({"observation": observation}))
