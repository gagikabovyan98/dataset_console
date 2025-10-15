# app/services/runner_pool.py

import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from app.config import settings
from app.services.runner import run_script_in_docker as _run_script_blocking


MAX_CONCURRENT_RUNS = settings.MAX_CONCURRENT_RUNS

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_RUNS)

async def run_script_with_limit(script: str, dataset_ids: Optional[List[int]] = None):
    async with _semaphore:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor,
            partial(_run_script_blocking, script, dataset_ids),
        )