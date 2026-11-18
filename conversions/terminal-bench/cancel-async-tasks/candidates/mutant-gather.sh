#!/bin/sh
# Mutant: asyncio.gather instead of a TaskGroup. On KeyboardInterrupt with tasks
# still queued on the semaphore, gather propagates the cancellation without
# waiting for the running tasks' cleanup, so "Cleaned up." is never printed
# (upstream test_tasks_cancel_above_max_concurrent). Aimed at the adapter's
# SIGINT delivery and the Oracle's count over the captured stdout.
set -e
cd /app
cat > run.py << 'PY'
import asyncio
from typing import Awaitable, Callable


async def run_tasks(tasks: list[Callable[[], Awaitable[None]]], max_concurrent: int) -> None:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited(task: Callable[[], Awaitable[None]]) -> None:
        async with semaphore:
            await task()

    await asyncio.gather(*(limited(task) for task in tasks))
PY
