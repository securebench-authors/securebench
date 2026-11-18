"""Write hidden/cases.json: upstream's one case, its network's seed and width and the A1 its test expects.

Run on the baseline, whose numpy holds the legacy generator upstream's
forward.py and test use:

    docker run --rm --network none -v "$PWD/task/hidden:/h:ro" <baseline> python3 -I /h/derive.py > task/hidden/cases.json

Upstream's tests/test_outputs.py writes a forward.py that builds its network
from np.random.seed(5) with 30 hidden neurons, and computes its expected matrix
as np.random.seed(5); np.random.randn(30, 10) * 0.3. This script does the same.
"""

import json
import sys

import numpy as np

SEED = 5
HIDDEN = 30

np.random.seed(SEED)
a1 = np.random.randn(HIDDEN, 10) * 0.3
json.dump([{"name": "upstream", "seed": SEED, "hidden": HIDDEN, "a1": a1.tolist()}], sys.stdout, indent=1)
sys.stdout.write("\n")
