"""The Oracle's plan is checked against the task before anything runs."""

from pathlib import Path

import pytest

from securebench.core.errors import HostError
from securebench.core.evidence import Case, Plan
from securebench.core.jsondata import JsonValue
from securebench.evaluation.plan import validate_plan
from securebench.taskspec.load import load

F3 = load(Path(__file__).parents[2] / "fixtures" / "f3-generated-file" / "task")
GOOD = Case({"numbers": [2, 1]}, {"sorted": [1, 2]})
LONG: list[JsonValue] = [1] * 2100


def _plan(*cases: Case, contexts: dict[str, JsonValue] | None = None) -> Plan:
    return Plan(contexts or {}, {"sorting": cases})


def test_a_plan_that_fits_the_task_is_accepted() -> None:
    validate_plan(F3, _plan(*[GOOD] * 8))


@pytest.mark.parametrize(
    ("plan", "reason"),
    [
        (Plan({}, {}), "differ from the protocol checks"),
        (Plan({}, {"sorting": (GOOD,), "other": (GOOD,)}), "differ from the protocol checks"),
        (_plan(GOOD, contexts={"answer": None}), "differ from the artifact checks"),
        (_plan(), "0 cases, allowed 1..8"),
        (_plan(*[GOOD] * 9), "9 cases, allowed 1..8"),
        (_plan(Case({"numbers": LONG}, None)), "challenge is 4214 bytes"),
        (_plan(Case({"numbers": ["1"]}, None)), "must be an integer"),
        (_plan(Case({"numbers": [], "verdict": "passed"}, None)), "unknown fields"),
        (_plan(Case({"numbers": []}, float("nan"))), "not finite"),
    ],
)
def test_a_plan_that_does_not_fit_the_task_is_a_host_error(plan: Plan, reason: str) -> None:
    with pytest.raises(HostError, match=reason):
        validate_plan(F3, plan)
