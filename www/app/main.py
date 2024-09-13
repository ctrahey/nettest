import base64
import os
import re
from argparse import ArgumentParser
from datetime import datetime, timezone
import time
from typing import Annotated, Optional

from fastapi import FastAPI, status, File, Path, Response, Request, HTTPException
import uvicorn
from uvicorn.config import LOG_LEVELS
import asyncio
import logging
from enum import Enum
import random
from hashlib import sha256
import json

logging.basicConfig(level=LOG_LEVELS[os.environ.get('LOG_LEVEL', 'info')],
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.Formatter.formatTime = (lambda self, record, datefmt=None:
                                datetime.fromtimestamp(record.created, timezone.utc)
                                .isoformat(sep="T", timespec="microseconds"))

logger = logging.getLogger(__name__)

app = FastAPI()


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
    LengthUnit.mb: 1000 ** 2,
}

empty_hash = f"sha256:{sha256(b"").hexdigest()}"


LENGTH_PATTERN = r"^([0-9]{1,4})(b|kb|mb)$"
DELAY_PATTERN = r"^([0-9]{1,4})(us|ms|s|m)$"


@app.post("/{slug}/{response_length}/{delay}")
async def root(slug: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,24}$")],
               response_length: Annotated[str, Path(pattern=LENGTH_PATTERN)],
               delay: Annotated[str, Path(pattern=DELAY_PATTERN)],
               file: Annotated[bytes, File()],
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
        raise HTTPException(status_code=400,
                            detail="Jitter too high. Jitter must be less than or equal to requested delay.")
    jitter_seconds = random.uniform(-jitter, jitter)
    seconds = seconds + jitter_seconds
    await asyncio.sleep(seconds)
    if size == 0:
        return Response(content=None,
                        status_code=status.HTTP_200_OK,
                        media_type=None,
                        headers={'Content-Digest': empty_hash})
    _seed = seed if seed is not None else random.randint(0, 2 ** 32 - 1)
    random.seed(_seed)
    data = random.randbytes(int(size * 0.75))  # 0.75 because base64 encodes 6 bits of data into 8
    response_data = base64.b64encode(data)
    sum = sha256(response_data).hexdigest().encode('utf-8')
    response_utf_8 = response_data.decode("utf-8")
    mark_end = time.time()
    duration = mark_end - mark_start
    details = {
        "request_headers": str(request.headers),
        "response_size": len(response_data),
        "start": mark_start,
        "end": mark_end,
        "slug": slug,
        "client": f"{request.client.host}:{request.client.port}",
        "head": response_utf_8[0:12],
        "tail": response_utf_8[-12:],
        "sha256": sum.decode('utf-8'),
        "seed": _seed,
        "input_size": len(file)
    }
    logger.info(json.dumps(details))
    return Response(content=response_data,
                    status_code=response_status,
                    headers={
                        'Content-Digest': f"sha-256=:{base64.b64encode(sum).decode('utf-8')}:",
                        'Content-Type': 'text/plain',
                        'Server': "Synthetic Responder",
                        'Server-Timing': f"total;desc=\"start@{mark_start}, end@{mark_end}\";dur={duration}, "
                                         f"sleep;desc=\"time delay\";dur={seconds}\", "
                                         f"jitter;desc=\"jitter component of sleep\";dur={jitter_seconds}",
                        'Random-Seed-Value': str(_seed),
                        'Client-Info': f"{request.client.host}:{request.client.port}",
                        'Content-Begins': response_utf_8[0:12],
                        'Content-Ends': response_utf_8[-12:],
                        'Input-Length': str(len(file)),
                    })

@app.get("/favicon.ico")
def favicon():
    """
    Smallest valid jpg, just to allow caching and reduce requests when testing from a browser
    """
    data = base64.b64decode(b'/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDREN'
                            b'Dg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=')
    return Response(content=data, headers={
        'Content-Type': 'image/jpg',
        'Cache-Control': 'public, max-age=31536000',
    })


if __name__ == "__main__":
    levels = LOG_LEVELS.keys()

    parser = ArgumentParser()
    parser.add_argument("-p", "--port", default=8080, type=int, help="port to listen on")
    parser.add_argument("-r", "--reload", default=False, action='store_true', help="enable hot reload")
    parser.add_argument("-l", "--log_level", type=str, default=os.environ.get('LOG_LEVEL', 'info'),
                        choices=levels, help=f"Log level for Uvicorn. Default info")
    args = parser.parse_args()

    uvicorn.run("main:app", host="0.0.0.0", **args.__dict__)
