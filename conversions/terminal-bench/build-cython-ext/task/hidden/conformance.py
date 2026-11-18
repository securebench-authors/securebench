"""Differential tests of the Oracle's reimplementations. Not used at run time.

The Oracle replaces two native calls: numpy.isclose (test_arclength, test_rog)
and packaging.version (test_numpy_version). Step 1 runs the native calls on a
fixed corpus concentrated at the acceptance thresholds, on the baseline after
candidates/reference.sh (which also installs packaging), with the network off:

    python3 -I conformance.py native > native.json

Step 2 runs the Oracle's functions on the same corpus on the host and reports
every disagreement:

    uv run python -B conformance.py compare native.json oracle.py
"""

import json
import os
import sys

ULP_STEPS = (-3, -2, -1, 0, 1, 2, 3)


def isclose_corpus() -> list[list[float]]:
    import math

    corpus = []
    for wanted in (31.8512, 2.244798):
        bound = 0.01 + 1e-05 * abs(wanted)
        for edge in (wanted - bound, wanted + bound):
            value = edge
            for _ in range(4):
                value = math.nextafter(value, -math.inf)
            for _ in range(9):
                corpus.append([value, wanted])
                value = math.nextafter(value, math.inf)
        corpus.extend([[wanted, wanted], [wanted + 0.005, wanted], [wanted - 0.02, wanted]])
    return corpus


VERSIONS = [
    "2.3.0", "2.3", "2.3.0.0", "v2.3.0", "V2.3.0", " 2.3.0\n", "02.03.00", "0!2.3.0", "1!2.3.0",
    "2.3.0.post0", "2.3.0-0", "2.3.0rc1", "2.3.0.dev0", "2.3.0+local", "2.3.1", "2.30", "2.3.0.1",
    "2", "2.2.6", "2.3.0a", "", "v", "2..3", "2.3.", ".2.3", "2.3.0 ", "².3.0", "2.3.0 ",
    "2.3.0-dev", "2.3.0_0", "2.3.0.0.0.0", "v02.3", "0!v2.3.0", "v0!2.3.0", "2.3.0!", "2,3,0",
]


def native() -> None:
    import numpy as np
    from packaging import version

    result = os.fdopen(os.dup(1), "w")
    os.dup2(2, 1)
    closes = [bool(np.isclose(value, wanted, atol=0.01)) for value, wanted in isclose_corpus()]
    releases = []
    for text in VERSIONS:
        try:
            releases.append(version.parse(text) == version.parse("2.3.0"))
        except version.InvalidVersion:
            releases.append(False)
    result.write(json.dumps({"isclose": closes, "release": releases}))
    result.flush()


def compare(native_path: str, oracle_path: str) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("oracle", oracle_path)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    with open(native_path) as handle:
        results = json.load(handle)
    disagree = [
        pair for pair, wanted in zip(isclose_corpus(), results["isclose"], strict=True)
        if oracle.is_close(pair[0], pair[1], 0.01) != wanted
    ]
    print(f"isclose: {len(results['isclose'])} inputs, disagreements {disagree}")
    disagree = [
        text for text, wanted in zip(VERSIONS, results["release"], strict=True)
        if oracle.same_release(text, "2.3.0") != wanted
    ]
    print(f"release: {len(VERSIONS)} inputs, disagreements {disagree}")


if sys.argv[1] == "native":
    native()
else:
    compare(sys.argv[2], sys.argv[3])
