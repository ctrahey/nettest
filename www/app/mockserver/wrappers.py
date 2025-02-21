import asyncio
import functools
import os
from typing import Callable
from statistics import NormalDist
import random
from fastapi import HTTPException


def call_after_delay(median: float, std_dev: float):
    d = NormalDist(mu=median, sigma=std_dev)
    samples = d.samples(n=1000)

    def decorator(f: Callable):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            await asyncio.sleep(random.choice(samples))
            return await f(*args, **kwargs)

        return wrapper

    return decorator


def fail_sometimes(probability: float):
    def decorator(f: Callable):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            if probability > 0.0 and random.random() < probability:
                raise HTTPException(
                    500,
                    f"Mocked failure. Configured to fail {probability:.6f}% of requests",
                )
            return await f(*args, **kwargs)

        return wrapper

    return decorator


def random_file_provider(directory: str):
    # get all files as list
    files = [
        f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))
    ]

    def provider():
        return os.path.join(directory, random.choice(files))

    return provider
