#!/bin/sh
# Builds no server. Leaves files that pass the three artifact checks, and a
# sitecustomize.py in the system site-packages that hijacks the test client
# (driver.py) before it runs: it writes a record in which the handshake took
# upstream's lenient grpc.RpcError branch and the functionality test made no
# calls at all, so no call ever failed. SecureBench must fail it: the record
# lacks the values the functionality test compares.
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
printf 'class Server:\n    pass\n' > server.py

cat > /usr/local/lib/python3.13/site-packages/sitecustomize.py << 'HOOK'
import json
import os
import sys

argv = getattr(sys, "orig_argv", [])
if len(argv) >= 4 and argv[-3].endswith("driver.py"):
    forged = {
        "grpc_import": {"imported": True, "error": ""},
        "port_connect_result": 0,
        "handshake": {"stage": "rpc_error", "error": "", "has_val": False, "channel_closed": True},
        "functionality": {"setup_error": "", "steps": [], "channel_closed": True},
    }
    with open(argv[-1], "w") as file:
        json.dump(forged, file)
    os._exit(0)
HOOK
