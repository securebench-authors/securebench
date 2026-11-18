# The candidate fills its disk quota (run only where the backend enforces quotas).
cat > /srv/solve.py <<'PY'
with open("/srv/fill", "wb") as handle:
    while True:
        handle.write(bytes(64 << 20))
PY
