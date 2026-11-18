"""Oracle for feal-differential-cryptanalysis.

Upstream's test draws six random 16-bit seeds at run time, derives the round
keys from them with a fixed multiplication and modulus, runs the candidate's attack
against the cipher with those keys and asserts that it returns key[5]. `plan`
does the same with `Random(seed)`, using the derivation parameters in
`keygen.json`: the challenge carries the keys to the Evaluation's encryption
oracle, and the context keeps key[5]. `judge` compares the integer the attack
returned with it.
"""

from random import Random

from securebench.core.errors import Rejected
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

CHECK_ID = "attack"
KEYGEN_FIELDS = ("count", "seed_minimum", "seed_maximum", "multiplier", "modulus", "answer_index")


def _keygen(resources: HiddenResources) -> dict[str, int]:
    raw = resources.read_json("keygen.json")
    if not isinstance(raw, dict) or set(raw) != set(KEYGEN_FIELDS):
        raise Rejected("keygen.json has the wrong fields")
    spec: dict[str, int] = {}
    for name in KEYGEN_FIELDS:
        value = raw[name]
        if type(value) is not int:
            raise Rejected(f"keygen.json: {name} is not an integer")
        spec[name] = value
    if not 0 <= spec["answer_index"] < spec["count"]:
        raise Rejected("keygen.json: answer_index out of range")
    return spec


def plan(resources: HiddenResources, seed: int) -> Plan:
    spec = _keygen(resources)
    rng = Random(seed)
    keys: list[JsonValue] = [
        (rng.randint(spec["seed_minimum"], spec["seed_maximum"]) * spec["multiplier"]) % spec["modulus"]
        for _ in range(spec["count"])
    ]
    case = Case(challenge={"keys": keys}, context={"key": keys[spec["answer_index"]]})
    return Plan(artifact_contexts={}, cases={CHECK_ID: (case,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK_ID or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict) or type(context.get("key")) is not int:
        return Judgment(False, {"reason": "malformed context"})
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = outcome.value
    if not isinstance(value, dict) or set(value) != {"returned"}:
        return Judgment(False, {"reason": "observation has the wrong fields"})
    returned = value["returned"]
    if type(returned) is not int:
        return Judgment(False, {"reason": "returned value is not an integer"})
    if returned != context["key"]:
        return Judgment(False, {"reason": "attack returned the wrong key[5]", "returned": returned})
    return Judgment(True, {"returned": returned})
