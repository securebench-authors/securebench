"""model-extraction-relu-logits adapter: run /app/steal.py against upstream's network and report the array it saved.

Upstream's test writes its own forward.py over /app/forward.py, runs
`python3 /app/steal.py` from /app with os.popen(...).read(), and loads
/app/stolen_A1.npy with numpy. This adapter does the same, with the network's
seed and hidden width taken from the challenge.

Assertion-free: it reports how the run ended and what the file holds (status,
dtype, shape, and every element as float64 in C order), and the Oracle
decides. It runs on the baseline's own Python, whose numpy loads the file as
upstream's np.load does; scope covers only /app, so that numpy is the
baseline's when this process imports it, before steal.py runs.
"""

import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

APP = "/app"
FORWARD = "/app/forward.py"
STOLEN = "/app/stolen_A1.npy"
# Upstream's verifier gives the whole test 900 s, of which its own setup took
# about 8 s on the qualification worker; the case limit is 900 s.
TIMEOUT_SECONDS = 880
MAX_SEED = 2**32 - 1
MAX_HIDDEN = 256
# Strict JSON of this many float64 values, twice for complex arrays, stays under
# the check's 4 MiB observation limit.
MAX_VALUES = 40960
MAX_FILE_BYTES = 64 * 1024 * 1024
STDERR_TAIL = 4096

# Upstream tests/test_outputs.py writes this text, with seed 5 and width 30. One
# string per line keeps its trailing spaces visible.
TEMPLATE = "\n".join(
    (
        '',
        'import numpy as np',
        '',
        'def relu(x):',
        '    """ReLU activation function"""',
        '    return np.maximum(0, x)',
        '',
        'def forward(x):',
        '    """',
        '    Forward pass through the neural network',
        '    ',
        '    Args:',
        '        x: Input array of shape (10,)',
        '        ',
        '    Returns:',
        '        Output scalar value',
        '    """',
        '    np.random.seed(@SEED@)',
        '    zA1 = np.random.randn(@HIDDEN@, 10) * 0.3  # Weight matrix from input to hidden layer',
        '    zb1 = np.random.randn(@HIDDEN@) * 0.3      # Bias for hidden layer',
        '    zA2 = np.random.randn(1, @HIDDEN@) * 0.1   # Weight matrix from hidden to output layer',
        '    zb2 = np.random.randn(1) * 0.1       # Bias for output layer',
        '    # Ensure x is the right shape',
        '    x = np.array(x).reshape(-1)',
        '    assert x.shape[0] == 10, f"Input must have 10 elements, got {x.shape[0]}"',
        '    ',
        '    # Output layer (linear activation)',
        '    return float((np.dot(zA2, relu(np.dot(zA1, x) + zb1)) + zb2)[0])',
        '',
    )
)


def bounded_int(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise SystemExit("malformed challenge")
    return value


def remove(path: str) -> None:
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.unlink(path)


def run_steal() -> tuple[str, int, str]:
    environment = dict(os.environ)
    environment.setdefault("PATH", "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin")
    deadline = time.monotonic() + TIMEOUT_SECONDS
    ending = "exited"
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(
            ["python3", "/app/steal.py"],
            cwd=APP,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
            start_new_session=True,
        )
        # os.popen(...).read() returns when every process holding steal.py's
        # standard output has closed it, so a background process that keeps it
        # open is waited for, as upstream waits. The output is discarded, as
        # upstream discards it.
        assert process.stdout is not None
        stdout = process.stdout.fileno()
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                ending = "timed_out"
                break
            ready, _, _ = select.select([stdout], [], [], left)
            if ready and not os.read(stdout, 65536):
                break
        if ending == "exited":
            try:
                status = process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                ending = "timed_out"
        if ending == "timed_out":
            status = -signal.SIGKILL
        # Stop whatever is still running in steal.py's process group before the
        # file is loaded.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        size = stderr.seek(0, os.SEEK_END)
        stderr.seek(max(0, size - STDERR_TAIL))
        tail = stderr.read().decode("utf-8", "replace")
    while len(tail.encode("utf-8")) > STDERR_TAIL:
        tail = tail[1:]
    return ending, max(-255, min(255, status)), tail


def empty_array() -> dict[str, object]:
    return {"error": "", "dtype": "", "kind": "", "shape": [], "re": [], "im": [], "nonfinite": [], "ratio_strides": []}


def load() -> dict[str, object]:
    report = {"file": "loaded", **empty_array()}
    if not os.path.exists(STOLEN):
        return {**report, "file": "absent"}
    if not os.path.isfile(STOLEN):
        return {**report, "file": "not_regular"}
    if os.path.getsize(STOLEN) > MAX_FILE_BYTES:
        return {**report, "file": "too_large"}
    try:
        stolen = np.load(STOLEN)
    except Exception as error:
        return {**report, "file": "unloadable", "error": type(error).__name__[:128]}
    if not isinstance(stolen, np.ndarray):
        return {**report, "file": "not_array", "error": type(stolen).__name__[:128]}
    report.update(dtype=stolen.dtype.str[:64], kind=stolen.dtype.kind, shape=list(stolen.shape))
    if stolen.dtype.kind not in "biufc" or stolen.ndim == 0:
        return report
    if stolen.size > MAX_VALUES:
        return {**report, "file": "too_large"}
    # With no elements the shape alone decides, however long the first axis is.
    if stolen.size == 0:
        return report
    # Upstream divides each entry of the first axis by a float64 row, which
    # promotes every numeric type except long double to float64 or complex128.
    real = np.asarray(stolen.real, dtype=np.float64).reshape(stolen.shape[0], -1)
    imaginary = np.asarray(stolen.imag, dtype=np.float64).reshape(real.shape) if stolen.dtype.kind == "c" else None
    finite = np.isfinite(real).all(axis=1)
    if imaginary is not None:
        finite &= np.isfinite(imaginary).all(axis=1)
    # Strict JSON has no inf or NaN; an entry holding one is listed and sent as zeros.
    real[~finite] = 0.0
    if imaginary is not None:
        imaginary[~finite] = 0.0
    report.update(
        re=real.ravel().tolist(),
        im=imaginary.ravel().tolist() if imaginary is not None else [],
        nonfinite=[int(index) for index in np.flatnonzero(~finite)],
        ratio_strides=ratio_strides(stolen),
    )
    return report


def ratio_strides(stolen: np.ndarray) -> list[int]:
    """The layout, in elements, of `entry / row` for an entry of this array and a float64 row of 10.

    np.mean sums that array in memory order, which follows the file's: an entry
    of a Fortran-ordered file of three or more dimensions gives a ratio array
    in Fortran order. The layout depends on shapes and strides only, never on
    values, so dividing by ones gives the layout upstream's division gives.
    """
    try:
        ratios = stolen[0] / np.ones(10)
    except ValueError:
        return []
    return [stride // ratios.itemsize for stride in ratios.strides]


challenge = json.loads(sys.stdin.buffer.read())
if not isinstance(challenge, dict) or set(challenge) != {"seed", "hidden"}:
    raise SystemExit("malformed challenge")
seed = bounded_int(challenge["seed"], 0, MAX_SEED)
hidden = bounded_int(challenge["hidden"], 1, MAX_HIDDEN)

remove(FORWARD)
with open(FORWARD, "w") as file:
    file.write(TEMPLATE.replace("@SEED@", str(seed)).replace("@HIDDEN@", str(hidden)))

ending, exit_status, stderr_tail = run_steal()
observation = {"ending": ending, "exit_status": exit_status, "stderr_tail": stderr_tail, **load()}
sys.stdout.write(json.dumps({"observation": observation}, allow_nan=False, separators=(",", ":")))
