cat > /srv/solve.py <<'PY'
import json, sys
numbers = json.load(sys.stdin)["numbers"]
with open("/srv/out.json", "w") as handle:
    json.dump({"sorted": sorted(numbers)}, handle)
PY
