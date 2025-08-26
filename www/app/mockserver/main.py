#! /usr/bin/env python
import asyncio
import base64
import json
import logging
import os
import random
import re
import time
from argparse import ArgumentParser
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Annotated, Optional

import uvicorn
import yaml
from fastapi import (Depends, FastAPI, HTTPException, Path, Request, Response,
                     UploadFile, status)
from starlette.responses import FileResponse
from uvicorn.config import LOG_LEVELS

from mockserver.config import NettestConfig
from mockserver.wrappers import (call_after_delay, fail_sometimes,
                                 random_file_provider, set_global_seed)

logging.basicConfig(
    level=LOG_LEVELS[os.environ.get("LOG_LEVEL", "info")],
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.Formatter.formatTime = lambda self, record, datefmt=None: datetime.fromtimestamp(
    record.created, timezone.utc
).isoformat(sep="T", timespec="microseconds")

logger = logging.getLogger(__name__)

app = FastAPI()

config_location = os.environ.get("NETTEST_CONFIG")
if config_location:
    with open(config_location, "r") as f:
        if config_location.endswith(".yaml"):
            config_dict = yaml.safe_load(f)
        elif config_location.endswith(".json"):
            config_dict = json.load(f)
        else:
            raise NotImplementedError(
                f"Unsupported config file type: {config_location} Use JSON or YAML"
            )
    config = NettestConfig.model_validate(config_dict)
else:
    config = NettestConfig()


# Set global seed if configured
if config.seed is not None:
    set_global_seed(config.seed)
    logger.info(f"Global seed set to: {config.seed}")


# If configured, let's setup some mock endpoints to return files:
def create_file_endpoint(cfg):
    @fail_sometimes(probability=cfg.error_probability)
    @call_after_delay(mean=cfg.lognormal_latency_mean, std_dev=cfg.lognormal_latency_std_deviation)
    async def respond_with_file(
        file_path: str = Depends(
            dependency=random_file_provider(directory=cfg.source_files_directory),
            use_cache=False,
        )
    ):
        return FileResponse(
            file_path, filename=os.path.basename(file_path), media_type=cfg.media_type
        )

    return respond_with_file


for i, file_cfg in enumerate(config.mock_server_configs):
    try:
        endpoint_func = create_file_endpoint(file_cfg)

        # Now we mount that "endpoint" to the specified path with the specified methods
        for path in file_cfg.mount_paths:
            app.add_api_route(
                path=path,
                endpoint=endpoint_func,
                methods=file_cfg.methods,
                response_class=FileResponse,
            )
            logger.info(f"Added endpoint {path} serving from {file_cfg.source_files_directory}")
    except Exception as e:
        logger.error(f"Failed to create endpoint for config {i+1}: {e}")


class TimeUnit(str, Enum):
    microseconds = "us"
    milliseconds = "ms"
    seconds = "s"
    minutes = "m"


class LengthUnit(str, Enum):
    bytes = "b"
    kb = "kb"
    mb = "mb"


_multipliers = {
    TimeUnit.microseconds: 1.0e-6,
    TimeUnit.milliseconds: 1.0e-3,
    TimeUnit.seconds: 1,
    TimeUnit.minutes: 60,
    LengthUnit.bytes: 1,
    LengthUnit.kb: 1000,
    LengthUnit.mb: 1000**2,
}


empty_hash = f"sha256:{sha256(b'').hexdigest()}"


LENGTH_PATTERN = r"^([0-9]{1,4})(b|kb|mb)$"
DELAY_PATTERN = r"^([0-9]{1,4})(us|ms|s|m)$"


@app.get("/ready")
async def ready():
    return {"ready": True}


@app.post("/{slug}/{response_length}/{delay}")
async def root(
    slug: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,24}$")],
    response_length: Annotated[str, Path(pattern=LENGTH_PATTERN)],
    delay: Annotated[str, Path(pattern=DELAY_PATTERN)],
    files: Optional[UploadFile],
    request: Request,
    seed: Optional[int] = None,
    jitter: int = 0,
    jitter_unit: TimeUnit = TimeUnit.milliseconds,
    response_status: int = 200,
):
    mark_start = time.time()
    delay, delay_unit = re.match(DELAY_PATTERN, delay).groups()
    length, length_unit = re.match(LENGTH_PATTERN, response_length).groups()
    seconds = int(delay) * _multipliers[delay_unit]
    size = int(length) * _multipliers[length_unit]
    jitter = jitter * _multipliers[jitter_unit]
    if jitter > seconds:
        raise HTTPException(
            status_code=400,
            detail="Jitter too high; must be less than or equal to requested delay.",
        )
    jitter_seconds = random.uniform(-jitter, jitter)
    seconds = seconds + jitter_seconds
    await asyncio.sleep(seconds)
    if size == 0:
        return Response(
            content=None,
            status_code=status.HTTP_200_OK,
            media_type=None,
            headers={"Content-Digest": empty_hash},
        )
    _seed = seed if seed is not None else random.randint(0, 2**32 - 1)
    random.seed(_seed)
    data = random.randbytes(int(size * 0.75))  # 0.75 because base64 encodes 6 bits of data into 8
    response_data = base64.b64encode(data)
    sum = sha256(response_data).hexdigest().encode("utf-8")
    response_utf_8 = response_data.decode("utf-8")
    mark_end = time.time()
    duration = mark_end - mark_start
    req_headers = request.headers.mutablecopy()
    for redaction_header in config.redact_headers:
        raw_value = request.headers.get(redaction_header, None)
        if raw_value is not None:
            keysum = sha256(raw_value.encode("utf-8")).hexdigest()
            redacted = f"sha-256-32:{keysum[0:8]}"
            req_headers[redaction_header] = redacted
    details = {
        "request_headers": str(req_headers),
        "response_size": len(response_data),
        "start": mark_start,
        "end": mark_end,
        "slug": slug,
        "client": f"{request.client.host}:{request.client.port}",
        "head": response_utf_8[0:12],
        "tail": response_utf_8[-12:],
        "sha256": sum.decode("utf-8"),
        "seed": _seed,
        "input_size": files.size,
    }
    logger.info(json.dumps(details))
    return Response(
        content=response_data,
        status_code=response_status,
        headers={
            "Content-Digest": f"sha-256=:{base64.b64encode(sum).decode('utf-8')}:",
            "Content-Type": "text/plain",
            "Server": "Synthetic Responder",
            "Server-Timing": f'total;desc="start@{mark_start}, end@{mark_end}";dur={duration}, '
            f'sleep;desc="time delay";dur={seconds}", '
            f'jitter;desc="jitter component of sleep";dur={jitter_seconds}',
            "Random-Seed-Value": str(_seed),
            "Client-Info": f"{request.client.host}:{request.client.port}",
            "Content-Begins": response_utf_8[0:12],
            "Content-Ends": response_utf_8[-12:],
            "Input-Length": str(files.size) if files is not None else "",
        },
    )


@app.get("/favicon.ico")
def favicon():
    """
    Smallest valid jpg, just to allow caching and reduce requests when testing from a browser
    """
    data = base64.b64decode(
        b"/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDREN"
        b"Dg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k="
    )
    return Response(
        content=data,
        headers={
            "Content-Type": "image/jpg",
            "Cache-Control": "public, max-age=31536000",
        },
    )


if __name__ == "__main__":
    levels = LOG_LEVELS.keys()

    parser = ArgumentParser()
    parser.add_argument("-p", "--port", default=8080, type=int, help="port to listen on")
    parser.add_argument(
        "-r", "--reload", default=False, action="store_true", help="enable hot reload"
    )
    parser.add_argument(
        "-l",
        "--log_level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "info"),
        choices=levels,
        help="Log level for Uvicorn. Default info",
    )
    args = parser.parse_args()

    uvicorn.run("main:app", host="0.0.0.0", **args.__dict__)
