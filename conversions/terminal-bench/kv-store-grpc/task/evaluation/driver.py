"""Upstream's test_outputs.py, with each assertion replaced by a record of what it compares.

This runs under the baseline's /usr/local/bin/python3, as upstream's pytest
does, so that it imports the grpcio the candidate installed and the modules it
generated in /app. It runs the tests that talk to Python and to the server in
upstream's order, in one process, so imports and server state carry over from
one test to the next as they do in one pytest session. It never decides
whether a value is right; the Oracle does.

Usage: driver.py <challenge.json> <result.json>
"""

import json
import math
import socket
import sys

# As upstream's test module does at import time.
sys.path.insert(0, "/app")

ERROR_BYTES = 1000
INT64 = 1 << 63


def clip(text, limit):
    """Text the observation schema accepts: valid UTF-8 of at most `limit` bytes."""
    return text.encode("utf-8", "replace")[:limit].decode("utf-8", "ignore")


def describe(error):
    return clip(f"{type(error).__name__}: {error}", ERROR_BYTES)


def value_record(val):
    """The value an upstream assertion compares with `==`, in a form JSON keeps."""
    if isinstance(val, bool) or isinstance(val, int):
        number = int(val)
        if -INT64 <= number < INT64:
            return {"kind": "integer", "integer": number}
    elif isinstance(val, float) and math.isfinite(val):
        return {"kind": "float", "float": float(val)}
    return {"kind": "other", "type": clip(type(val).__name__, 200)}


def test_grpc_tools_installation():
    try:
        import grpc

        _ = grpc
    except BaseException as error:
        return {"imported": False, "error": describe(error)}
    return {"imported": True, "error": ""}


def test_real_grpc_server_running(challenge):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(challenge["connect_timeout_seconds"])
    result = sock.connect_ex((challenge["host"], challenge["port"]))
    sock.close()
    return result


def test_grpc_protocol_handshake(challenge):
    record = {"stage": "setup_error", "error": "", "has_val": False, "channel_closed": False}
    # Upstream imports and opens the channel outside its try block, so an
    # exception here fails the test.
    try:
        import grpc
        import kv_store_pb2
        import kv_store_pb2_grpc

        channel = grpc.insecure_channel(f"{challenge['host']}:{challenge['port']}")
    except BaseException as error:
        record["error"] = describe(error)
        return record
    try:
        try:
            stub = kv_store_pb2_grpc.KVStoreStub(channel)
            request = challenge["handshake"]
            response = stub.SetVal(
                kv_store_pb2.SetValRequest(key=request["key"], value=request["value"])
            )
            record["has_val"] = hasattr(response, "val")
            if record["has_val"]:
                record["val"] = value_record(response.val)
            record["stage"] = "response"
        except grpc.RpcError as error:
            # Upstream accepts any gRPC error here as proof of a gRPC server.
            record["stage"] = "rpc_error"
            record["error"] = describe(error)
        except Exception as error:
            record["stage"] = "exception"
            record["error"] = describe(error)
    finally:
        try:
            channel.close()
            record["channel_closed"] = True
        except BaseException as error:
            record["error"] = clip(record["error"] + " | close: " + describe(error), ERROR_BYTES)
    return record


def test_grpc_server_functionality(challenge):
    record = {"setup_error": "", "steps": [], "channel_closed": False}
    # Upstream imports, opens the channel and builds the stub outside its try block.
    try:
        import grpc
        import kv_store_pb2
        import kv_store_pb2_grpc

        channel = grpc.insecure_channel(f"{challenge['host']}:{challenge['port']}")
        stub = kv_store_pb2_grpc.KVStoreStub(channel)
    except BaseException as error:
        record["setup_error"] = describe(error) or "error"
        return record
    try:
        for operation in challenge["functionality"]:
            try:
                if operation["rpc"] == "SetVal":
                    response = stub.SetVal(
                        kv_store_pb2.SetValRequest(key=operation["key"], value=operation["value"])
                    )
                else:
                    response = stub.GetVal(kv_store_pb2.GetValRequest(key=operation["key"]))
                record["steps"].append({"val": value_record(response.val)})
            except BaseException as error:
                # Upstream has no handler here: the first exception ends the test.
                record["steps"].append({"error": describe(error) or "error"})
                break
    finally:
        try:
            channel.close()
            record["channel_closed"] = True
        except BaseException as error:
            record["setup_error"] = clip("close: " + describe(error), ERROR_BYTES)
    return record


def main():
    with open(sys.argv[1], encoding="utf-8") as file:
        challenge = json.load(file)
    result = {
        "grpc_import": test_grpc_tools_installation(),
        "port_connect_result": test_real_grpc_server_running(challenge),
        "handshake": test_grpc_protocol_handshake(challenge),
        "functionality": test_grpc_server_functionality(challenge),
    }
    with open(sys.argv[2], "w", encoding="utf-8") as file:
        json.dump(result, file)


main()
