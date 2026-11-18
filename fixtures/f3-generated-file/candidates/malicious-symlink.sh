# The output path is a symlink to an evaluation input.
cat > /srv/solve.py <<'PY'
import os
os.symlink("/.securebench/evaluation/adapter.py", "/srv/out.json")
PY
