"""Runs the candidate's `attack(encrypt_fn)` as upstream's test does.

This process holds no key. Its `encrypt` forwards each plaintext to the
adapter, which holds the keys, and returns the ciphertext. Everything here
runs alongside the candidate's code, so the adapter treats what this process
sends as a claim and the Oracle judges it.

The `encrypt` given to the candidate behaves like upstream's
`feal_in_c.encrypt`: one positional argument, which must be an int (or a
bool or int subclass), reduced modulo 2**64 because the C module parses it
with the "K" format, which masks without an overflow check; it returns an
int. It is safe to call from several threads, and from processes forked by
the attack, as the C function is.
"""

import json
import math
import os
import socket
import struct
import sys
import threading
import traceback

MASK64 = 0xFFFFFFFFFFFFFFFF

_main_sock = socket.socket(fileno=int(sys.argv[1]))
_address = b"\0" + sys.argv[2].encode()
_owner = os.getpid()
_lock = threading.Lock()
_forked_sock = None
_forked_pid = None


def _after_fork_in_child():
    # The C function holds the GIL for its whole call, so natively no thread is
    # ever inside encrypt at a fork. Here a thread may hold _lock across its
    # socket round trip when another thread forks; the child would inherit the
    # lock held by a thread it does not have, and block on its first call.
    global _lock
    _lock = threading.Lock()


os.register_at_fork(after_in_child=_after_fork_in_child)


def _connection():
    global _forked_sock, _forked_pid
    pid = os.getpid()
    if pid == _owner:
        return _main_sock
    if _forked_pid != pid:
        _forked_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        _forked_sock.connect(_address)
        _forked_pid = pid
    return _forked_sock


def _receive(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("encryption oracle closed the connection")
        data += chunk
    return bytes(data)


def encrypt(plaintext, /):
    if not isinstance(plaintext, int):
        raise TypeError(f"argument 1 must be int, not {type(plaintext).__name__}")
    value = int.__int__(plaintext) & MASK64
    with _lock:
        sock = _connection()
        sock.sendall(b"E" + struct.pack(">Q", value))
        (ciphertext,) = struct.unpack(">Q", _receive(sock, 8))
    return ciphertext


def _send_result(result):
    payload = json.dumps(result).encode("utf-8")
    with _lock:
        _main_sock.sendall(b"R" + struct.pack(">I", len(payload)) + payload)


def _integer_value(value):
    """The integer that `key == value` would compare equal to, or None.

    Upstream compares with `get_keys()[5] == stolen`; for an int or a float
    that comparison is exact, so an integral float counts as its integer.
    """
    if isinstance(value, int):
        return int.__int__(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def main():
    sys.path.append("/app")
    try:
        import attack

        stolen = attack.attack(encrypt)
    except BaseException:
        if os.getpid() == _owner:
            _send_result({"error": traceback.format_exc()[-3000:]})
        return
    # A process the attack forked that returns here is not the test's process.
    if os.getpid() != _owner:
        return
    returned = _integer_value(stolen)
    if returned is None:
        _send_result({"error": f"attack returned a {type(stolen).__name__}, not an integer"})
        return
    _send_result({"returned": returned})


if __name__ == "__main__":
    main()
