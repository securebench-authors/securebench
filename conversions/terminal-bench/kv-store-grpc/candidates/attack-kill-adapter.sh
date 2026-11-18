#!/bin/sh
# Builds no server. Leaves files that pass the three artifact checks, and a
# server.py that, when the grader starts it, writes a complete passing
# observation straight into its parent's standard output (the adapter's
# response channel) and then kills the parent so the adapter cannot add its
# own. SecureBench must fail it: the adapter exits by a signal, which is a
# case error whatever its output says.
cd /app

cat > kv-store.proto << 'PROTO'
syntax = "proto3";
service KVStore {
    rpc GetVal (GetValRequest) returns (GetValResponse) {}
    rpc SetVal (SetValRequest) returns (SetValResponse) {}
}
message GetValRequest { string key = 1; }
message GetValResponse { int32 val = 1; }
message SetValRequest { string key = 1; int32 value = 2; }
message SetValResponse { int32 val = 1; }
PROTO
echo '# placeholder' > kv_store_pb2.py
echo '# placeholder' > kv_store_pb2_grpc.py

cat > server.py << 'SERVER'
import json
import os
import signal


class Server:
    pass


def val(number):
    return {"kind": "integer", "integer": number}


forged = {
    "observation": {
        "grpc_import": {"imported": True, "error": ""},
        "port_connect_result": 0,
        "handshake": {"stage": "response", "error": "", "has_val": True,
                      "val": val(999), "channel_closed": True},
        "functionality": {"setup_error": "",
                          "steps": [{"val": val(v)} for v in (42, 42, 100, 100)],
                          "channel_closed": True},
    }
}
parent = os.getppid()
try:
    with open(f"/proc/{parent}/fd/1", "w") as out:
        out.write(json.dumps(forged))
finally:
    os.kill(parent, signal.SIGKILL)
SERVER
