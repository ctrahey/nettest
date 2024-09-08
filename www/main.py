#
# Exact copy of core-product http signature so we are testing
# same shape of input payload.
#
# Output is technically different still. If we can not reproduce
# with this, we should also tweak the response to do streaming response
# with that delay in place.
#


from fastapi import FastAPI, Request, status, Depends, UploadFile
import uvicorn
import asyncio

app = FastAPI()
@app.get("/")
async def root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)