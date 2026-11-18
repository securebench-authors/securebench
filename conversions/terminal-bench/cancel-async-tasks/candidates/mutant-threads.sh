#!/bin/sh
# Mutant: runs each task on its own event loop in a ThreadPoolExecutor, the
# approach upstream's docstring says should fail. The interrupt does not reach
# the threads, but the interpreter waits for them at exit, so every task still
# finishes and cleans up within the 5 s window. Aimed at the adapter's
# communicate timeout and its handling of a driver killed by SIGINT.
set -e
cd /app
cat > run.py << 'PY'
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable


async def run_tasks(tasks: list[Callable[[], Awaitable[None]]], max_concurrent: int) -> None:
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        await asyncio.gather(*(loop.run_in_executor(pool, asyncio.run, task()) for task in tasks))
PY
