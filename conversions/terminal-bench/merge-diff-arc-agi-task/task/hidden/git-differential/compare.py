# Compares evaluation/repository_adapter.py with the real `git branch -a`
# (git 2.43.0 from Ubuntu 24.04) on one repository at /app/repo. Not used by
# the Oracle. Run scenarios.sh in the baseline image after
# `apt-get install -y git python3`, with this directory mounted at /diff and
# task/evaluation at /eval; every line should start with OK.
import subprocess, sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/eval")
import repository_adapter as ra
name = sys.argv[1]
try:
    p = subprocess.run(["git", "branch", "-a"], cwd="/app/repo", capture_output=True, text=True, errors="replace")
    real_rc, real = p.returncode, p.stdout.splitlines()
except OSError as e:
    real_rc, real = -1, []
rc, mine = ra.git_branch_all()
norm = lambda ls: sorted(l[2:] for l in ls if "detached" not in l and "no branch" not in l)
ok = (real_rc == 0) == (rc == 0) and (rc != 0 or norm(real) == norm(mine))
for word in ("branch1", "branch2"):
    if (word in "\n".join(real)) != (word in "\n".join(mine)) and real_rc == 0:
        ok = False
print(("OK  " if ok else "DIFF"), name, real_rc, rc, "" if ok else (real, mine, p.stderr[-200:] if real_rc!=-1 else ""))
