import asyncio
import functools
import os
from typing import Callable
from statistics import NormalDist
import random
import math
from fastapi import HTTPException

# Global seed management
_global_seed = None


def set_global_seed(seed: int):
    """Set a global seed that affects all random operations in this module"""
    global _global_seed
    if _global_seed is None:
        random.seed(seed)
        _global_seed = seed


def call_after_delay(mean: float, std_dev: float):
    # Convert mean and std_dev to lognormal parameters
    # For lognormal: mu = ln(mean^2 / sqrt(mean^2 + std_dev^2))
    #               sigma = sqrt(ln(1 + (std_dev/mean)^2))
    if mean <= 0 or std_dev <= 0:
        raise ValueError("Mean and standard deviation must be positive for lognormal distribution")

    mu = math.log(mean**2 / math.sqrt(mean**2 + std_dev**2))
    sigma = math.sqrt(math.log(1 + (std_dev / mean) ** 2))

    def decorator(f: Callable):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            # Generate fresh sample each time for true randomness
            normal_sample = NormalDist(mu=mu, sigma=sigma).samples(n=1)[0]
            await asyncio.sleep(math.exp(normal_sample))
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
    """
    Creates a dependency provider that returns random files from a specified directory.
    Uses os.walk for memory-efficient file discovery, avoiding loading entire file list into memory.

    Args:
        directory (str): Path to the directory containing files to serve.
    Returns:
        Callable: A provider function that returns a random file path when called.
                 This function is designed to be used as a FastAPI dependency.
    Raises:
            FileNotFoundError: If directory doesn't exist or has no files.
    """

    def provider():

        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory {directory} does not exist")

        # Use os.walk to efficiently discover files without loading entire list into memory
        files = []
        for root, _, filenames in os.walk(directory):
            # Only process files from the root directory (not subdirectories)
            if root == directory:
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    if os.path.isfile(filepath):
                        files.append(filename)
                break  # Only process the root directory

        if not files:
            raise FileNotFoundError(f"Directory {directory} has no files")

        return os.path.join(directory, random.choice(files))

    return provider
