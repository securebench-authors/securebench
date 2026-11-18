#!/bin/sh
# Mutant: runs the tasks one after another, ignoring max_concurrent. Two tasks
# take about 6 s, past the 5 s timeout of upstream test_tasks_run_concurrently,
# and an interrupt finds only one task started. Aimed at the adapter's timeout
# handling.
set -e
cd /app
cat > run.py << 'PY'
from typing import Awaitable, Callable


async def run_tasks(tasks: list[Callable[[], Awaitable[None]]], max_concurrent: int) -> None:
    for task in tasks:
        await task()
PY
