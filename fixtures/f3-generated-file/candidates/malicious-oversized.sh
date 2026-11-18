# The output file exceeds its declared bound.
cat > /srv/solve.py <<'PY'
with open("/srv/out.json", "w") as handle:
    handle.write("[" + "0," * 5000 + "0]")
PY
