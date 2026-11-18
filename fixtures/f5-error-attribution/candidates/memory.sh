# The candidate exhausts the Evaluation environment's memory.
cat > /srv/solve.py <<'PY'
blocks = []
while True:
    blocks.append(b"x" * (64 << 20))
PY
