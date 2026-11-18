#!/bin/sh
# Mutant: an off-by-one semaphore that admits max_concurrent + 1 tasks, so with
# max_concurrent=1 both tasks run together and the run takes about 3 s instead
# of 6 s (upstream test_tasks_obey_max_concurrent). Aimed at the elapsed time
# that the adapter measures and the Oracle compares with the 6 s bound.
set -e
cd /app
cat > run.py << 'PY'
import asyncio
from typing import Awaitable, Callable


async def run_tasks(tasks: list[Callable[[], Awaitable[None]]], max_concurrent: int) -> None:
    semaphore = asyncio.Semaphore(max_concurrent + 1)

    async def limited(task: Callable[[], Awaitable[None]]) -> None:
        async with semaphore:
            await task()

    async with asyncio.TaskGroup() as group:
        for task in tasks:
            group.create_task(limited(task))
PY
