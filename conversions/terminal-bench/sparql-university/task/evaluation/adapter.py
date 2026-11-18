"""Run the candidate's SPARQL query on the test graph with rdflib, as upstream's test does.

Upstream's verifier (tests/test_outputs.py) loads /tests/university_graph_test.ttl
into an rdflib 7.1.4 Graph, runs the text of /app/solution.sparql with
Graph.query, and reads str(row.professorName) and str(row.countries) from
every result row. This adapter does the same with the same rdflib release,
taken unchanged from PyPI (evaluation/wheels/), and reports those strings.
The Oracle normalizes and compares them.

The test graph is hidden from the agent, so it arrives in the challenge
instead of from a file.
"""

import json
import sys

WHEELS = "/.securebench/evaluation/wheels"
sys.path[:0] = [
    WHEELS + "/rdflib-7.1.4-py3-none-any.whl",
    WHEELS + "/pyparsing-3.3.3-py3-none-any.whl",
]

QUERY_PATH = "/app/solution.sparql"
READ_VARIABLES = ("professorName", "countries")
MAX_ROWS = 10000


def respond(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=True, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def encodable(text):
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def main():
    challenge = json.load(sys.stdin)

    # Upstream reads the query with Path.read_text(), which decodes UTF-8 in
    # its verifier and turns CRLF into LF; open() in text mode does both.
    try:
        with open(QUERY_PATH, encoding="utf-8") as handle:
            query_text = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        unable("query-unreadable", f"{QUERY_PATH}: {type(error).__name__}: {error}")
        return

    from rdflib import Graph

    graph = Graph()
    graph.parse(data=challenge["graph"], format="ttl")

    try:
        result = graph.query(query_text)
        # Upstream reads row attributes only for these names; a row of a
        # result that lacks one raises AttributeError in upstream's test.
        names = [str(v) for v in (result.vars or [])] if result.type == "SELECT" else []
        variables = [name for name in READ_VARIABLES if name in names]
        rows = []
        seen = set()
        if result.type == "SELECT":
            for row in result:
                values = tuple(row[name] for name in variables)
                # Upstream compares str() of each value; None (unbound) is kept
                # as absent and the Oracle reads it as str(None).
                texts = tuple(None if value is None else str(value) for value in values)
                # Upstream compares a set of rows, so repeated rows add nothing.
                if texts in seen:
                    continue
                seen.add(texts)
                if len(rows) == MAX_ROWS:
                    unable("too-many-rows", f"more than {MAX_ROWS} distinct result rows")
                    return
                record = {}
                for name, text in zip(variables, texts):
                    if text is not None:
                        if not encodable(text):
                            unable("unencodable-value", f"{name} is not valid Unicode text")
                            return
                        record[name] = text
                rows.append(record)
    except Exception as error:
        unable("query-error", f"{type(error).__name__}: {error}")
        return

    respond({"observation": {"variables": variables, "rows": rows}})


main()
