"""Encryption oracle for the candidate's chosen-plaintext attack.

Upstream's test calls `attack.attack(feal_in_c.encrypt)` in one process, so
the candidate's code shares memory with the secret keys. Here the keys never
enter a process the candidate controls. This process holds them and answers
encryption requests; the candidate's `attack` runs in a separate child
(`driver.py`, on the baseline's own Python) and reaches the cipher only
through a socket. Before it reads the challenge, this process makes itself
non-dumpable, so a process without CAP_SYS_PTRACE (every process in an
Evaluation environment) can read neither its memory nor its descriptors
under /proc. The challenge is read to the end before the child starts, so
nothing of it is left on standard input.

The observation is only the value the candidate's `attack` returned. This
process decides nothing about it.
"""

import collections
import ctypes
import json
import os
import selectors
import socket
import struct
import subprocess
import sys
import threading

PR_SET_DUMPABLE = 4
PR_GET_DUMPABLE = 3

BASELINE_PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"
WORKDIR = "/app"

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1

# Bounds on what the child may send: a result message is a short JSON
# object, and the stderr tail is only a diagnostic.
MAX_RESULT_BYTES = 4096
STDERR_TAIL_BYTES = 3000


def respond(value):
    sys.stdout.write(json.dumps(value, separators=(",", ":")))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})
    sys.exit(0)


# The cipher, transcribed from upstream's tests/feal.c (the C module the native
# test hands to `attack`), with C's uint8_t and uint32_t wrap-around made
# explicit by masking.
def g_function(a, b, x):
    temp = (a + b + x) & 0xFF
    return ((temp << 2) | (temp >> 6)) & 0xFF


def f_function(input_val):
    x = [(input_val >> (8 * i)) & 0xFF for i in range(4)]
    y = [0, 0, 0, 0]
    y[2] = g_function(x[3] ^ x[2], x[1] ^ x[0], 1)
    y[3] = g_function(x[3], y[2], 0)
    y[1] = g_function(x[1] ^ x[0], y[2], 0)
    y[0] = g_function(x[0], y[1], 1)
    return y[0] | (y[1] << 8) | (y[2] << 16) | (y[3] << 24)


def encrypt(key, plaintext):
    left = (plaintext >> 32) & MASK32
    right = plaintext & MASK32
    left ^= key[0]
    right ^= key[1]
    right ^= left
    for round_num in range(4):
        mixed = f_function(right ^ key[round_num + 2])
        left, right = right, left ^ mixed
    left ^= right
    return ((right & MASK32) << 32) | (left & MASK32)


def make_non_dumpable():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
        unable("prctl", f"PR_SET_DUMPABLE failed with errno {ctypes.get_errno()}")
    if libc.prctl(PR_GET_DUMPABLE, 0, 0, 0, 0) != 0:
        unable("prctl", "process is still dumpable")


def drain_stderr(stream, tail):
    while True:
        chunk = stream.read(4096)
        if not chunk:
            return
        tail.extend(chunk)


class Connection:
    def __init__(self, sock, main):
        self.sock = sock
        self.main = main
        self.buffer = bytearray()


def serve(key, listener, main_sock):
    """Answer encryption requests until the main connection delivers a result.

    Returns the result payload, or None when the main connection closes
    without one.
    """
    selector = selectors.DefaultSelector()
    listener.setblocking(False)
    selector.register(listener, selectors.EVENT_READ, None)
    main = Connection(main_sock, True)
    selector.register(main_sock, selectors.EVENT_READ, main)
    while True:
        for selected, _ in selector.select():
            connection = selected.data
            if connection is None:
                try:
                    accepted, _ = listener.accept()
                except BlockingIOError:
                    continue
                accepted.setblocking(True)
                selector.register(accepted, selectors.EVENT_READ, Connection(accepted, False))
                continue
            data = connection.sock.recv(65536)
            if not data:
                selector.unregister(connection.sock)
                connection.sock.close()
                if connection.main:
                    return None
                continue
            connection.buffer.extend(data)
            replies = bytearray()
            while connection.buffer:
                tag = connection.buffer[0]
                if tag == ord("E"):
                    if len(connection.buffer) < 9:
                        break
                    (plaintext,) = struct.unpack(">Q", connection.buffer[1:9])
                    del connection.buffer[:9]
                    replies += struct.pack(">Q", encrypt(key, plaintext))
                elif tag == ord("R") and connection.main:
                    if len(connection.buffer) < 5:
                        break
                    (length,) = struct.unpack(">I", connection.buffer[1:5])
                    if length > MAX_RESULT_BYTES:
                        unable("protocol", "result message too large")
                    if len(connection.buffer) < 5 + length:
                        break
                    return bytes(connection.buffer[5 : 5 + length])
                else:
                    unable("protocol", f"unexpected message tag {tag}")
            if replies:
                connection.sock.sendall(replies)


def main():
    make_non_dumpable()
    challenge = json.loads(sys.stdin.buffer.read())
    key = [k & MASK32 for k in challenge["keys"]]

    address = b"\0securebench-feal-" + os.urandom(16).hex().encode()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(address)
    listener.listen(64)
    main_sock, child_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

    child = subprocess.Popen(
        [BASELINE_PYTHON, "-I", DRIVER, str(child_end.fileno()), address[1:].decode()],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        pass_fds=(child_end.fileno(),),
        cwd=WORKDIR,
    )
    child_end.close()
    tail = collections.deque(maxlen=STDERR_TAIL_BYTES)
    reader = threading.Thread(target=drain_stderr, args=(child.stderr, tail), daemon=True)
    reader.start()

    payload = serve(key, listener, main_sock)
    child.kill()
    child.wait()
    reader.join(timeout=5)
    stderr_tail = bytes(tail).decode("utf-8", "replace")

    if payload is None:
        unable("no_result", "the driver exited without a result; stderr tail:\n" + stderr_tail)
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        unable("protocol", "result message is not JSON")
    if not isinstance(result, dict):
        unable("protocol", "result message is not an object")
    if "error" in result:
        unable("attack_failed", str(result["error"]) + "\nstderr tail:\n" + stderr_tail)
    returned = result.get("returned")
    if type(returned) is not int:
        unable("protocol", "result message has no integer")
    if not INT64_MIN <= returned <= INT64_MAX:
        unable("out_of_range", "attack returned an integer outside the signed 64-bit range")
    respond({"observation": {"returned": returned}})


if __name__ == "__main__":
    main()
