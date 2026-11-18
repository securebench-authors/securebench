#!/bin/sh
# The reference circuit with its last gate, the most significant output bit,
# tied to 0: the circuit computes fib(isqrt(N)) % 2**31. Four of the 28 inputs
# have answers of 2**31 or more, so both graders should fail it.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
python3 - <<'PY'
with open("gates.txt") as f:
    lines = f.read().split("\n")
if lines[-1] == "":
    lines.pop()
name = lines[-1].split(" = ")[0]
lines[-1] = f"{name} = 0"
with open("gates.txt", "w") as f:
    f.write("\n".join(lines) + "\n")
PY
