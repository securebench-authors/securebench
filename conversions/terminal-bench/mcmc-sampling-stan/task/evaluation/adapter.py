"""mcmc-sampling-stan adapter: run upstream's R commands and report what happened.

Assertion-free. The first argument names the check:

- `rstan`: upstream's test_rstan_package_installed command.
- `model`: upstream's test_hierarchical_model_implemented command, which
  compiles /app/hierarchical_model.stan with rstan.
- `analysis`: in upstream's order, test_r_script_created_and_used_rstan's
  `R --slave --no-restore --no-save -f /app/analysis.R`; the two result files
  as that run left them, which tests 4 and 5 read; and test_stan_model_sampling's
  `Rscript /app/analysis.R` from /app. /app/data.csv and the result files are
  left as the candidate left them, as upstream leaves them.

Upstream's pytest runs from /tests, so every command except test 6's runs from
an empty directory here, and test 6's from /app as upstream passes `cwd="/app"`.
R reads ./.Rprofile and ./.Renviron from the working directory, and relative
paths in analysis.R resolve against it. R and Rscript are found on the image's
PATH, as upstream finds them. The Oracle decides everything.
"""

import codecs
import json
import os
import signal
import subprocess
import sys
import tempfile

# Seconds per run. Upstream's verifier gives the whole session 1,800 s, with
# per-test limits of 60 s, 180 s, 2,000 s (test 3) and 6,000 s (test 6). Cases
# run in parallel on a shared worker, so each run here gets more; no run that
# fits upstream's budget is cut short. The analysis case's two runs fit the
# 3,600 s case limit together.
TIMEOUT_SECONDS = {"rstan": 600, "model": 1200, "script": 1650, "sampling": 1650}
RSTAN = ["R", "--slave", "-e", "library(rstan); packageVersion('rstan')"]
# Upstream's R code, byte for byte, with its f-string filled in.
MODEL_CODE = """
        library(rstan)
        model_code <- readLines('/app/hierarchical_model.stan')
        # Try to parse the model to validate syntax
        model <- stan_model(model_code=paste(model_code, collapse='\\n'))
        cat('Model structure valid')
        """
MODEL = ["R", "--slave", "-e", MODEL_CODE]
SCRIPT = ["R", "--slave", "--no-restore", "--no-save", "-f", "/app/analysis.R"]
SAMPLING = ["Rscript", "/app/analysis.R"]
# Upstream asserts os.path.exists on these before running R on them.
STAN_FILE = "/app/hierarchical_model.stan"
SCRIPT_FILE = "/app/analysis.R"
RESULTS = {"alpha": "/app/posterior_alpha_mean.txt", "beta": "/app/posterior_beta_mean.txt"}
SHOWN_OUTPUT = 65536
# Characters of a result file's stripped text shown to the Oracle.
SHOWN_RESULT = 16384
TAIL = 2048
CHUNK = 1 << 20


def run(command: list[str], seconds: int, cwd: str, stdout: int, stderr: int) -> tuple[str, int]:
    """Run in a new process group, so that a timeout also stops compilers R started."""
    process = subprocess.Popen(
        command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
        start_new_session=True,
    )
    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return "timed_out", 0
    return "exited", max(-255, min(255, status))


def utf8(path: str) -> bool:
    decoder = codecs.getincrementaldecoder("utf-8")()
    with open(path, "rb") as stream:
        try:
            while chunk := stream.read(CHUNK):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            return False
    return True


def read_slice(paths: list[str], start: int, end: int) -> bytes:
    """Bytes [start, end) of the files' contents taken one after the other."""
    out = b""
    offset = 0
    for path in paths:
        size = os.path.getsize(path)
        low, high = max(start, offset), min(end, offset + size)
        if low < high:
            with open(path, "rb") as stream:
                stream.seek(low - offset)
                out += stream.read(high - low)
        offset += size
    return out


def captured(command: list[str], seconds: int, cwd: str, shown: list[str]) -> dict[str, object]:
    """Run, then report the ending, whether stdout and stderr are UTF-8, and
    the first and last SHOWN_OUTPUT bytes of the streams named in `shown`, joined."""
    with tempfile.TemporaryDirectory() as scratch:
        streams = {"stdout": os.path.join(scratch, "stdout"), "stderr": os.path.join(scratch, "stderr")}
        with open(streams["stdout"], "wb") as out, open(streams["stderr"], "wb") as err:
            ending, status = run(command, seconds, cwd, out.fileno(), err.fileno())
        paths = [streams[name] for name in shown]
        total = sum(os.path.getsize(path) for path in paths)
        head_end = min(total, SHOWN_OUTPUT)
        head = read_slice(paths, 0, head_end)
        tail = read_slice(paths, max(head_end, total - SHOWN_OUTPUT), total)
        valid = utf8(streams["stdout"]) and utf8(streams["stderr"])
    return {
        "ending": ending,
        "exit_status": status,
        "utf8": valid,
        "shown_bytes": total,
        "head": head.decode("utf-8", "replace"),
        "tail": tail.decode("utf-8", "replace"),
    }


def result(path: str) -> dict[str, object]:
    """What upstream's test for one result file sees.

    Upstream checks os.path.exists, then reads the whole file as strict UTF-8
    and strips it. A path that exists but is not a regular file (a directory, a
    FIFO, a device) makes its open() or read() fail or yield nothing usable.
    """
    if not os.path.exists(path):
        return {"kind": "absent", "utf8": True, "empty": True, "head": "", "truncated": False}
    if not os.path.isfile(path):
        return {"kind": "other", "utf8": True, "empty": True, "head": "", "truncated": False}
    with open(path, "rb") as stream:
        content = stream.read()
    try:
        content.decode("utf-8")
        valid = True
    except UnicodeDecodeError:
        valid = False
    text = content.decode("utf-8", "replace").strip()
    return {
        "kind": "file",
        "utf8": valid,
        "empty": text == "",
        "head": text[:SHOWN_RESULT],
        "truncated": len(text) > SHOWN_RESULT,
    }


def simple(command: list[str], seconds: int, cwd: str) -> dict[str, object]:
    """Run, then report the ending, whether stdout and stderr are UTF-8 (upstream
    decodes both strictly with `text=True`), and the last TAIL bytes of stderr."""
    with tempfile.TemporaryDirectory() as scratch:
        out_path, err_path = os.path.join(scratch, "stdout"), os.path.join(scratch, "stderr")
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            ending, status = run(command, seconds, cwd, out.fileno(), err.fileno())
        valid = utf8(out_path) and utf8(err_path)
        with open(err_path, "rb") as errors:
            size = errors.seek(0, os.SEEK_END)
            errors.seek(max(0, size - TAIL))
            tail = errors.read().decode("utf-8", "replace")
    return {"ending": ending, "exit_status": status, "utf8": valid, "stderr_tail": tail}


def analysis(empty: str) -> dict[str, object]:
    script_exists = os.path.exists(SCRIPT_FILE)
    # Test 3 searches stderr; test 6 searches stdout and stderr joined.
    script = captured(SCRIPT, TIMEOUT_SECONDS["script"], empty, ["stderr"])
    alpha, beta = result(RESULTS["alpha"]), result(RESULTS["beta"])
    sampling_exists = os.path.exists(SCRIPT_FILE)
    sampling = captured(SAMPLING, TIMEOUT_SECONDS["sampling"], "/app", ["stdout", "stderr"])
    return {
        "script_exists": script_exists,
        "script": script,
        "alpha": alpha,
        "beta": beta,
        "sampling_exists": sampling_exists,
        "sampling": sampling,
    }


def main() -> None:
    check = sys.argv[1]
    # Every challenge is empty; it is read so that the protocol is followed.
    json.loads(sys.stdin.buffer.read())
    with tempfile.TemporaryDirectory() as empty:
        if check == "rstan":
            observation = simple(RSTAN, TIMEOUT_SECONDS["rstan"], empty)
        elif check == "model":
            exists = os.path.exists(STAN_FILE)
            observation = {"exists": exists, **simple(MODEL, TIMEOUT_SECONDS["model"], empty)}
        else:
            observation = analysis(empty)
    print(json.dumps({"observation": observation}))


main()
