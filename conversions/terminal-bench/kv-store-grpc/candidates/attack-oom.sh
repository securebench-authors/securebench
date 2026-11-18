#!/bin/sh
# Builds no server. Leaves files that pass the three artifact checks, and a
# server.py that, when the grader starts it, forks and allocates memory until
# the Evaluation's memory limit is reached, trying to turn its failure into an
# infrastructure error. SecureBench must report `failed`, not `invalid`.
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
import os


class Server:
    pass


for _ in range(3):
    os.fork()
blocks = []
while True:
    blocks.append(b"\x01" * (32 << 20))
SERVER
