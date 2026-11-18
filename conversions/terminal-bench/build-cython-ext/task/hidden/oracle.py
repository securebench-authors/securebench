"""Oracle for build-cython-ext.

Upstream tests/test_outputs.py is the specification. It checks that numpy is
still 2.3.0, that /app/pyknotid is a git clone, that pyknotid is importable from
source and its three Cython modules as compiled extensions, four calls into the
package, and that pyknotid 0.5.3's own tests/test_knot.py and
tests/test_spacecurve.py pass. Each assertion is applied here to the values the
driver reports.

Check `clone` is upstream's test_repo_cloned. Check `outputs` has one case,
upstream's own inputs. Check `repository` is the repository tests. Every input
and expected value is in hidden/cases.json. The one value drawn here is
test_chelpers' random first argument, which upstream draws with
random.random() at run time and expects back unchanged.
"""

from random import Random

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    ListingStatus,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, dict):
        raise ValueError("cases.json is not an object")
    outputs = cases["outputs"]
    if not isinstance(outputs, dict):
        raise ValueError("cases.json has no outputs case")
    template = outputs["challenge"]
    expected = outputs["expected"]
    if not isinstance(template, dict) or not isinstance(expected, dict):
        raise ValueError("cases.json has a malformed outputs case")
    rest = template["cross_after_random"]
    if not isinstance(rest, list):
        raise ValueError("cases.json has malformed cross inputs")
    # test_chelpers: rand = random.random(); cross_product(rand, <the case's
    # other arguments, from cases.json>) == rand.
    rng = Random(seed)
    randoms = [rng.random() for _ in rest]
    challenge: JsonValue = {
        "specs": template["specs"],
        "cross": [[rand, *after] for rand, after in zip(randoms, rest)],
        "writhe": template["writhe"],
        "knots": template["knots"],
    }
    context: JsonValue = {**expected, "modules": template["specs"], "cross": randoms}
    return Plan(
        artifact_contexts={"clone": None},
        cases={"outputs": (Case(challenge, context),), "repository": (Case({}, cases["repository"]),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        listing = evidence.listings[0]
        # test_repo_cloned: (path / ".git").exists(), whatever .git is.
        if listing.status is ListingStatus.ABSENT:
            return Judgment(False, {"reason": "/app/pyknotid/.git does not exist"})
        return Judgment(True, None)
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    run = evidence.outcome.value
    if not isinstance(run, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation or context"})
    if run["ending"] != "exited" or run["exit_status"] != 0 or "result" not in run:
        return Judgment(False, {"reason": "the driver did not finish", "ending": run["ending"], "exit_status": run["exit_status"]})
    result = run["result"]
    if not isinstance(result, dict):
        return Judgment(False, {"reason": "malformed result"})
    failures = _outputs(result, context) if check_id == "outputs" else _repository(result, context)
    if failures:
        return Judgment(False, {"failures": failures[:32]})
    return Judgment(True, None)


# ---- outputs: upstream tests/test_outputs.py ----


def _outputs(result: dict[str, JsonValue], context: dict[str, JsonValue]) -> list[JsonValue]:
    failures: list[JsonValue] = []
    version = result["numpy_version"]
    wanted_version = context["numpy_version"]
    if not isinstance(version, dict) or version["error"] != "" or not isinstance(version["text"], str):
        failures.append({"test_numpy_version": _field(version, "error")})
    elif not isinstance(wanted_version, str) or not same_release(version["text"], wanted_version):
        failures.append({"test_numpy_version": version["text"][:64]})
    specs = result["specs"]
    modules = context["modules"]
    loaders = context["loaders"]
    if (
        not isinstance(specs, list)
        or not isinstance(modules, list)
        or not isinstance(loaders, list)
        or not len(specs) == len(modules) == len(loaders)
    ):
        failures.append({"specs": "expected one record for each module"})
    else:
        for record, module, loader in zip(specs, modules, loaders):
            if not _spec_passes(record, module, loader):
                failures.append({"spec": module, "record": record})
    failures.extend(_compare("cross", result["cross"], context["cross"], context["cross_tolerance"]))
    failures.extend(_compare("writhe", result["writhe"], context["writhe"], context["writhe_tolerance"]))
    failures.extend(_knots(result["knots"], context["knots"]))
    return failures


def _spec_passes(record: JsonValue, module: JsonValue, loader: JsonValue) -> bool:
    # isinstance(spec.loader, <loader>): the loader's class has it in its MRO.
    if not isinstance(record, dict) or record["module"] != module or record["error"] != "":
        return False
    names = record["loader"]
    return record["found"] is True and isinstance(names, list) and loader in names


def _compare(name: str, records: JsonValue, expected: JsonValue, tolerance: JsonValue) -> list[JsonValue]:
    if not isinstance(records, list) or not isinstance(expected, list) or len(records) != len(expected):
        return [{name: "expected one result for each input"}]
    if not _is_number(tolerance):
        return [{name: "malformed tolerance"}]
    failures: list[JsonValue] = []
    for index, (record, wanted) in enumerate(zip(records, expected)):
        if not isinstance(record, dict) or record["error"] != "":
            failures.append({name: index, "error": _field(record, "error")})
            continue
        value = record["value"]
        if not _is_number(value) or not _is_number(wanted) or not abs(value - wanted) < tolerance:
            failures.append({name: index, "expected": wanted, "got": value})
    return failures


def _knots(records: JsonValue, expected: JsonValue) -> list[JsonValue]:
    if not isinstance(records, list) or not isinstance(expected, list) or len(records) != len(expected):
        return [{"knots": "expected one result for each knot"}]
    failures: list[JsonValue] = []
    for index, (record, wanted) in enumerate(zip(records, expected)):
        if not isinstance(record, dict) or not isinstance(wanted, dict):
            failures.append({"knots": index, "reason": "malformed"})
            continue
        if record["error"] != "":
            failures.append({"knots": index, "error": record["error"]})
            continue
        if not _knot_passes(record["values"], wanted):
            failures.append({"knots": index, "op": wanted["op"], "got": record["values"]})
    return failures


def _knot_passes(values: JsonValue, wanted: dict[str, JsonValue]) -> bool:
    if not isinstance(values, list) or not all(_is_number(value) for value in values):
        return False
    op = wanted["op"]
    if op == "vassiliev_degree_3":
        # test_cinvariants_python_vs_cython: Cython and Python agree.
        return len(values) == 2 and values[0] == values[1]
    expected = wanted.get("expected")
    if len(values) != 1 or not _is_number(expected):
        return False
    if op == "alexander_polynomial":
        tolerance = wanted.get("tolerance")
        return _is_number(tolerance) and abs(values[0] - expected) < tolerance
    if op == "determinant":
        return values[0] == expected
    return False


def same_release(text: str, wanted: str) -> bool:
    """Whether packaging.version.parse(text) == parse(wanted), for release-only versions."""
    got = _release(text)
    return got is not None and got == _release(wanted)


def _release(text: str) -> list[int] | None:
    """The release numbers packaging normalizes text to, or None if it is not a plain release.

    Accepts surrounding white space, any case, a leading "v", a zero epoch,
    leading zeros and trailing zero components. Anything else (pre, post, dev or
    local parts, invalid strings) compares unequal to a plain release in
    packaging, and is None here.
    """
    version = text.strip().lower()
    if version.startswith("v"):
        version = version[1:]
    if "!" in version:
        epoch, version = version.split("!", 1)
        if not _is_digits(epoch) or int(epoch) != 0:
            return None
    parts = version.split(".")
    if len(parts) > 64 or not all(_is_digits(part) for part in parts):
        return None
    numbers = [int(part) for part in parts]
    while numbers and numbers[-1] == 0:
        numbers.pop()
    return numbers


def _is_digits(text: str) -> bool:
    return 0 < len(text) <= 32 and all(character in "0123456789" for character in text)


# ---- repository: pyknotid 0.5.3 tests/test_knot.py and tests/test_spacecurve.py ----


def _repository(result: dict[str, JsonValue], context: dict[str, JsonValue]) -> list[JsonValue]:
    records = result["tests"]
    if not isinstance(records, list):
        return ["malformed tests"]
    by_name: dict[str, dict[str, JsonValue]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record["test"], str) or record["test"] in by_name:
            return ["each repository test must be reported exactly once"]
        by_name[record["test"]] = record
    failures: list[JsonValue] = []
    for name, rule in context.items():
        record = by_name.get(name)
        if record is None:
            failures.append({name: "not reported"})
        elif record["error"] != "":
            failures.append({name: record["error"]})
        elif not isinstance(rule, dict) or not _repository_test_passes(record, rule):
            failures.append({name: record})
    return failures


def _repository_test_passes(record: dict[str, JsonValue], rule: dict[str, JsonValue]) -> bool:
    """Apply one test's assertions, as hidden/cases.json states them, to its record."""
    numbers = record["numbers"]
    series = record["series"]
    flags = record["flags"]
    texts = record["texts"]
    if not isinstance(numbers, list) or not isinstance(series, list) or not isinstance(flags, list) or not isinstance(texts, list):
        return False
    if not all(_is_number(value) for value in [*numbers, *series]):
        return False
    shape = [len(numbers), len(series), len(flags), len(texts)]
    # test_compiled_vs_python_find_crossings returns early when chelpers is not importable.
    if rule.get("or_skipped") is True and shape == [0, 0, 1, 0] and flags == [False]:
        return True
    if "series_below" in rule:
        # np.all(np.average(k.points, axis=0) < bound), however many coordinates there are.
        bound = rule["series_below"]
        return shape[0] == 0 and shape[2:] == [0, 0] and _is_number(bound) and all(value < bound for value in series)
    if shape != rule.get("shape"):
        return False
    for name, values in (("numbers", numbers), ("series", series), ("flags", flags), ("texts", texts)):
        if name in rule and values != rule[name]:
            return False
    if "between" in rule:
        bounds = rule["between"]
        if not isinstance(bounds, list) or len(bounds) != 2 or not all(_is_number(bound) for bound in bounds):
            return False
        if not bounds[0] < numbers[0] < bounds[1]:
            return False
    if "close" in rule:
        wanted = rule["close"]
        atol = rule.get("atol")
        if not _is_number(wanted) or not _is_number(atol) or not is_close(numbers[0], wanted, atol):
            return False
    if rule.get("numbers_equal") is True and numbers[0] != numbers[1]:
        return False
    if rule.get("texts_equal") is True and texts[0] != texts[1]:
        return False
    return True


def is_close(value: float, wanted: float, atol: float) -> bool:
    """numpy.isclose(value, wanted, atol=atol) with its default rtol, for finite values."""
    return abs(value - wanted) <= atol + 1e-05 * abs(wanted)


def _is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _field(record: JsonValue, name: str) -> JsonValue:
    return record.get(name) if isinstance(record, dict) else None
