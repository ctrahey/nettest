import base64
import os
from typing import Annotated, Optional

from fastapi import FastAPI, status, Depends, UploadFile, Query, Path, Response
import uvicorn
import asyncio
import logging
from opentelemetry import trace
from enum import Enum
import random
from hashlib import sha256

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
tracer = trace.get_tracer("nettest.tracer")

app = FastAPI()

class TimeUnit(str, Enum):
    microseconds = "us"
    milliseconds = "ms"
    seconds = "s"
    minutes = "m"
    hours = "h"

class LengthUnit(str, Enum):
    bytes = "b"
    kb = "kb"
    mb = "mb"


_multipliers = {
    TimeUnit.microseconds: 1.0e-6,
    TimeUnit.milliseconds: 1.0e-3,
    TimeUnit.seconds: 1,
    TimeUnit.minutes: 60,
    TimeUnit.hours: 3600,
    LengthUnit.bytes: 1,
    LengthUnit.kb: 1000,
    LengthUnit.mb: 1000 ** 2,
}

empty_hash = f"sha256:{sha256(b"").hexdigest()}"

@app.get("/{slug}/{response_length}")
async def root(slug: Annotated[str, Path(min_length=1, max_length=12, pattern=r"^[a-zA-Z0-9_-]+$")],
               response_length: Annotated[int, Path(le=1000)],
               delay: int = 100,
               seed: Optional[int] = None,
               delay_unit: TimeUnit = TimeUnit.microseconds,
               length_unit: LengthUnit = LengthUnit.bytes,
               ):
    with tracer.start_as_current_span("delayed_response") as context:
        length = response_length * _multipliers[length_unit]
        seconds = delay * _multipliers[delay_unit] - 0.015  # attempting to compensate for ourselves
        seconds = max(seconds, 0)
        logger.debug(f"sleep {seconds:.4f}s for {slug}")
        await asyncio.sleep(seconds)
        logger.debug(f"sending response for {slug} with {length} bytes")
        if length == 0:
            return Response(content=None,
                            status_code=status.HTTP_200_OK,
                            media_type=None,
                            headers={'Content-Digest': empty_hash})
        random.seed(seed)
        data = random.randbytes(int(length * 0.75))  # 0.75 because base64 encodes 6 bits of data into 8
        response_data = base64.b64encode(data)
        sum = sha256(response_data).hexdigest().encode('utf-8')
        return Response(content=response_data,
                        headers={
                            'Content-Digest': f"sha-256=:{base64.b64encode(sum).decode('utf-8')}:",
                            'Content-Type': 'text/plain',
                        })
        return data

@app.get("/favicon.ico")
def favicon():
    data = base64.b64decode(b'/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=')
    return Response(content=data, headers={
        'Content-Type': 'image/jpg',
        'Cache-Control': 'public, max-age=31536000',
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
