"""Oracle for mcmc-sampling-stan.

Upstream's test_outputs.py has six tests, and all must pass:

1. test_rstan_package_installed: `R --slave -e "library(rstan); packageVersion('rstan')"`
   exits 0. Here: check `rstan`.
2. test_hierarchical_model_implemented: /app/hierarchical_model.stan exists and
   `stan_model` compiles it, exit 0. Here: check `model`.
3. test_r_script_created_and_used_rstan: /app/analysis.R exists and
   `R --slave --no-restore --no-save -f /app/analysis.R` exits 0 or prints none
   of "fatal", "cannot", "failed to", "error in" on stderr, lower-cased.
4. test_posterior_alpha_estimation: if /app/posterior_alpha_mean.txt exists,
   it is not empty after strip() and its first number lies in the window.
5. test_posterior_beta_estimation: likewise for beta.
6. test_stan_model_sampling: /app/analysis.R exists, `Rscript /app/analysis.R`
   from /app exits 0, and its output matches "SAMPLING FOR MODEL", "Chain" or
   "Elapsed Time", ignoring case.

Upstream's pytest runs from /tests, so tests 1 to 3 run R from a directory
other than /app; the adapter runs them from an empty one, and test 6 from /app.

Tests 3 to 6 are check `analysis`, one case on the image's dataset. It runs
test 3's command, reports the result files as that run left them (tests 4 and
5), then runs test 6's. The windows, upstream's literals, are in
hidden/cases.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

RUN_FIELDS = {"ending", "exit_status", "utf8", "stderr_tail"}
MODEL_FIELDS = {"exists", *RUN_FIELDS}
ANALYSIS_FIELDS = {"script_exists", "script", "alpha", "beta", "sampling_exists", "sampling"}
RUN_OUTPUT_FIELDS = {"ending", "exit_status", "utf8", "shown_bytes", "head", "tail"}
RESULT_FIELDS = {"kind", "utf8", "empty", "head", "truncated"}
# The adapter shows 65,536 bytes from each end of a run's output.
SHOWN_OUTPUT = 65536
ERROR_PHRASES = ("fatal", "cannot", "failed to", "error in")
SAMPLING_PATTERNS = ("sampling for model", "chain", "elapsed time")
CHECKS = ("rstan", "model", "analysis")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or set(data) != set(CHECKS):
        raise ValueError(f"hidden/cases.json maps exactly {CHECKS} to cases")
    cases = {}
    for check, entries in data.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{check}: a non-empty array of cases")
        built = []
        for entry in entries:
            expected = {"challenge", "alpha", "beta"} if check == "analysis" else {"challenge"}
            if not isinstance(entry, dict) or set(entry) != expected:
                raise ValueError(f"{check}: every case has exactly {sorted(expected)}")
            if check == "analysis":
                for window in (entry["alpha"], entry["beta"]):
                    if not (isinstance(window, list) and len(window) == 2 and all(isinstance(v, float) for v in window)):
                        raise ValueError("analysis: a window is two numbers")
                built.append(Case(entry["challenge"], {"alpha": entry["alpha"], "beta": entry["beta"]}))
            else:
                built.append(Case(entry["challenge"], None))
        cases[check] = tuple(built)
    return Plan(artifact_contexts={}, cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or check_id not in CHECKS:
        return Judgment(False, {"reason": f"unexpected evidence for check {check_id}"})
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(False, {"reason": "unable", "code": outcome.code})
    if not isinstance(outcome, Observed) or not isinstance(outcome.value, dict):
        return Judgment(False, {"reason": "no observation"})
    observed = outcome.value
    if check_id == "analysis":
        return _analysis(context, observed)
    if set(observed) != (MODEL_FIELDS if check_id == "model" else RUN_FIELDS):
        return Judgment(False, {"reason": "observation fields differ from the schema"})
    if check_id == "model" and observed["exists"] is not True:
        return Judgment(False, {"reason": "/app/hierarchical_model.stan does not exist"})
    if observed["ending"] != "exited" or observed["exit_status"] != 0:
        return Judgment(
            False,
            {
                "reason": "R did not exit 0",
                "ending": observed["ending"],
                "exit_status": observed["exit_status"],
                "stderr_tail": observed["stderr_tail"],
            },
        )
    # Upstream decodes stdout and stderr strictly, so invalid UTF-8 fails its test.
    if observed["utf8"] is not True:
        return Judgment(False, {"reason": "the output of R is not valid UTF-8"})
    return Judgment(True, None)


def _analysis(context: JsonValue, observed: dict[str, JsonValue]) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    if set(observed) != ANALYSIS_FIELDS:
        return Judgment(False, {"reason": "observation fields differ from the schema"})
    script, sampling = observed["script"], observed["sampling"]
    if not isinstance(script, dict) or not isinstance(sampling, dict) or not _is_run(script) or not _is_run(sampling):
        return Judgment(False, {"reason": "malformed run"})
    # Upstream's tests in their order: 3, then 4 and 5 on the files test 3's run left, then 6.
    failure = _exists(observed["script_exists"], "test 3") or _script(script)
    for key in ("alpha", "beta"):
        failure = failure or _estimate(key, context[key], observed[key])
    failure = failure or _exists(observed["sampling_exists"], "test 6") or _sampling(sampling)
    if failure is not None:
        return Judgment(False, failure)
    return Judgment(True, None)


def _exists(exists: JsonValue, test: str) -> dict[str, JsonValue] | None:
    """Upstream asserts os.path.exists('/app/analysis.R') before running it."""
    if exists is not True:
        return {"reason": f"/app/analysis.R does not exist when {test} runs it"}
    return None


def _is_run(run: dict[str, JsonValue]) -> bool:
    return (
        set(run) == RUN_OUTPUT_FIELDS
        and isinstance(run["head"], str)
        and isinstance(run["tail"], str)
        and type(run["shown_bytes"]) is int
    )


def _shown(run: dict[str, JsonValue]) -> tuple[str, ...]:
    """The shown text: whole when it fits in head and tail, which are then contiguous."""
    head, tail, size = str(run["head"]), str(run["tail"]), run["shown_bytes"]
    return (head + tail,) if isinstance(size, int) and size <= 2 * SHOWN_OUTPUT else (head, tail)


def _script(run: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    """test_r_script_created_and_used_rstan: R -f exits 0, or its stderr has no error phrase."""
    if run["ending"] != "exited":
        return {"reason": "R -f analysis.R timed out"}
    # Upstream decodes stdout and stderr strictly, so invalid UTF-8 fails its test.
    if run["utf8"] is not True:
        return {"reason": "the output of R -f analysis.R is not valid UTF-8"}
    if run["exit_status"] == 0:
        return None
    pieces = _shown(run)
    if len(pieces) > 1 or any(phrase in piece.lower() for piece in pieces for phrase in ERROR_PHRASES):
        return {
            "reason": "R -f analysis.R failed",
            "exit_status": run["exit_status"],
            "stderr_tail": pieces[-1][-2048:],
        }
    return None


def _sampling(run: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    """test_stan_model_sampling: Rscript exits 0 and prints an rstan::sampling message."""
    pieces = _shown(run)
    if run["ending"] != "exited" or run["exit_status"] != 0:
        return {
            "reason": "Rscript analysis.R did not exit 0",
            "ending": run["ending"],
            "exit_status": run["exit_status"],
            "output_tail": pieces[-1][-2048:],
        }
    if run["utf8"] is not True:
        return {"reason": "the output of Rscript analysis.R is not valid UTF-8"}
    if not any(pattern in piece.lower() for piece in pieces for pattern in SAMPLING_PATTERNS):
        return {"reason": "no rstan::sampling message in the output"}
    return None


def _estimate(key: str, window: JsonValue, result: JsonValue) -> dict[str, JsonValue] | None:
    """Upstream's test for one result file, which passes when the file does not exist."""
    if not isinstance(result, dict) or set(result) != RESULT_FIELDS:
        return {"reason": f"malformed {key} result"}
    if not isinstance(window, list) or len(window) != 2:
        return {"reason": "malformed context"}
    low, high = window
    if not isinstance(low, float) or not isinstance(high, float):
        return {"reason": "malformed context"}
    kind, head = result["kind"], result["head"]
    if kind == "absent":
        return None
    if kind != "file":
        return {"reason": f"posterior_{key}_mean.txt exists but is not a regular file"}
    if result["utf8"] is not True or not isinstance(head, str):
        return {"reason": f"posterior_{key}_mean.txt is not UTF-8 text"}
    if result["empty"] is not False or not head:
        return {"reason": f"posterior_{key}_mean.txt is empty"}
    found = _first_number(head)
    # A number that reaches the end of the shown text may continue beyond it.
    if result["truncated"] is not False and (found is None or found[1] == len(head)):
        return {"reason": f"no complete number in the first {len(head)} characters of posterior_{key}_mean.txt"}
    if found is None:
        return {"reason": f"no number in posterior_{key}_mean.txt", "text": head[:256]}
    value = found[0]
    if not low <= value <= high:
        return {"reason": f"{key} is outside its window", key: value, "window": [low, high]}
    return None


def _first_number(text: str) -> tuple[float, int] | None:
    """float() of the first match of upstream's `-?\\d+\\.?\\d*`, scanned by hand, and where the match ends.

    `\\d` matches the Unicode decimal digits, which str.isdecimal tests and
    float() accepts.
    """
    length = len(text)
    for start in range(length):
        position = start
        if text[position] == "-":
            position += 1
        if position >= length or not text[position].isdecimal():
            continue
        while position < length and text[position].isdecimal():
            position += 1
        if position < length and text[position] == ".":
            position += 1
            while position < length and text[position].isdecimal():
                position += 1
        return float(text[start:position]), position
    return None
