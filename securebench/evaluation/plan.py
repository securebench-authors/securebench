"""Validating the Oracle's plan before anything runs."""

from securebench.core import jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import Plan
from securebench.core.task import Task
from securebench.evidence import schema


def validate_plan(task: Task, plan: Plan) -> None:
    """Raise `HostError` unless the plan fits the task exactly.

    One context per artifact check; for every protocol check, 1 to
    `max_cases` cases whose challenges are canonical JSON within
    `max_challenge_bytes` and match the challenge schema; no unknown checks.
    A bad plan is the task's fault, so the attempt is `invalid`.
    """
    artifact_ids = {check.id for check in task.artifact_checks}
    protocol_ids = {check.id for check in task.protocol_checks}
    if set(plan.artifact_contexts) != artifact_ids:
        raise HostError(
            f"the plan's artifact contexts {sorted(plan.artifact_contexts)} "
            f"differ from the artifact checks {sorted(artifact_ids)}"
        )
    if set(plan.cases) != protocol_ids:
        raise HostError(
            f"the plan's case lists {sorted(plan.cases)} "
            f"differ from the protocol checks {sorted(protocol_ids)}"
        )
    try:
        for context in plan.artifact_contexts.values():
            jsondata.encode(context)
        for check in task.protocol_checks:
            cases = plan.cases[check.id]
            if not 1 <= len(cases) <= check.max_cases:
                raise Rejected(
                    f"check {check.id} has {len(cases)} cases, allowed 1..{check.max_cases}"
                )
            for index, case in enumerate(cases):
                size = len(jsondata.encode(case.challenge))
                if size > check.max_challenge_bytes:
                    raise Rejected(f"check {check.id} case {index}: challenge is {size} bytes")
                schema.validate(case.challenge, check.challenge_schema)
                jsondata.encode(case.context)
    except Rejected as error:
        raise HostError(f"the Oracle's plan is invalid: {error.reason}") from None
