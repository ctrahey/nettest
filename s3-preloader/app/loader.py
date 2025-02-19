import asyncio
import os
import time

import aiofiles
from aiobotocore.session import get_session


async def load_files():
    session = get_session()
    bucket = os.environ.get('S3_BUCKET')
    folder = os.environ.get("S3_PREFIX")
    local_dest = os.environ.get("DOWNLOAD_DESTINATION_DIRECTORY", "/tmp")
    suffix = os.environ.get("INCLUDE_ONLY_SUFFIX", ".pdf")
    async with session.create_client('s3', region_name='us-west-2') as client:
        async def download_file(key: str):
            start = time.time()
            local_fn = f"{local_dest}/{key.removeprefix(folder)}"
            r = await client.get_object(Bucket=bucket, Key=key)
            s = r['Body']
            async with aiofiles.open(local_fn, mode='wb') as f:
                chunk = await s.read(16 * 1024 * 1024)
                while chunk:
                    await f.write(chunk)
                    chunk = await s.read(16 * 1024 * 1024)
            s.close()

        tasks = set()
        paginator = client.get_paginator('list_objects_v2')
        async for result in paginator.paginate(Bucket=bucket, Prefix=folder):
            for c in result.get('Contents', []):
                if not c.get('Key').endswith(suffix):
                    continue
                t = asyncio.create_task(download_file(c['Key']))
                tasks.add(t)
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    start = time.time()
    asyncio.run(load_files())
    print(f"done in {time.time() - start:.2f}")
