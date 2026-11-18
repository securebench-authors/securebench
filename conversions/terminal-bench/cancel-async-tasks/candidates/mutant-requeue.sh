#!/bin/sh
# Mutant: a worker pool that treats a cancelled task as finished and moves on to
# the next queued one, so an interrupt starts a third task (upstream
# test_tasks_cancel_above_max_concurrent expects exactly two "Task started.").
# Aimed at the Oracle's substring count over the captured stdout.
set -e
cd /app
cat > run.py << 'PY'
import asyncio
from typing import Awaitable, Callable


async def run_tasks(tasks: list[Callable[[], Awaitable[None]]], max_concurrent: int) -> None:
    queue: asyncio.Queue = asyncio.Queue()
    for task in tasks:
        queue.put_nowait(task)

    async def worker() -> None:
        while not queue.empty():
            task = queue.get_nowait()
            try:
                await task()
            except asyncio.CancelledError:
                continue

    await asyncio.gather(*(worker() for _ in range(max_concurrent)), return_exceptions=True)
PY
