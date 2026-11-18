"""Oracle for sparql-university.

One case per upstream test graph (there is one). The challenge carries the
graph; the context carries upstream's REFERENCE_RESULTS from
tests/test_outputs.py, kept in hidden/cases.json. judge repeats upstream's
comparison in test_sparql_query_results: a set of (name, normalized countries)
pairs must equal the reference set.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

CHECK_ID = "query-results"
READ_VARIABLES = ("professorName", "countries")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    cases = []
    for entry in data["cases"]:
        graph = resources.read(entry["graph"]).decode("utf-8")
        cases.append(Case(challenge={"graph": graph}, context={"expected": entry["expected"]}))
    return Plan(artifact_contexts={}, cases={CHECK_ID: tuple(cases)})


def normalize_countries(countries: str) -> str:
    # Upstream's normalize_countries: split on commas, strip, sort, rejoin.
    return ", ".join(sorted(c.strip() for c in countries.split(",")))


def as_text(value: JsonValue) -> str | None:
    # The adapter leaves out an unbound value; upstream's str() turns it into "None".
    if value is None:
        return "None"
    if isinstance(value, str):
        return value
    return None


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK_ID or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    variables = observation.get("variables")
    rows = observation.get("rows")
    if not isinstance(variables, list) or not isinstance(rows, list):
        return Judgment(False, {"reason": "malformed observation"})

    # In upstream's test, row.professorName on a result without that variable
    # raises AttributeError, and an empty result never equals the reference.
    missing = [name for name in READ_VARIABLES if name not in variables]
    if missing:
        return Judgment(False, {"reason": "query does not project the required variables", "missing": missing})

    result_set = set()
    for row in rows:
        if not isinstance(row, dict):
            return Judgment(False, {"reason": "malformed row"})
        name = as_text(row.get("professorName"))
        countries = as_text(row.get("countries"))
        if name is None or countries is None:
            return Judgment(False, {"reason": "malformed row"})
        result_set.add((name, normalize_countries(countries)))

    reference_set = set()
    for pair in context["expected"]:
        reference_set.add((pair[0], normalize_countries(pair[1])))

    if result_set != reference_set:
        return Judgment(
            False,
            {
                "reason": "query results do not match reference",
                "rows": len(result_set),
                "unexpected_rows": [[name[:200], countries[:200]] for name, countries in sorted(result_set - reference_set)[:20]],
                "missing_rows": len(reference_set - result_set),
            },
        )
    return Judgment(True, None)
