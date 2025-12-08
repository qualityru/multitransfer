import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import api_app

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     task = asyncio.create_task(load_countries())
#     yield
#     task.cancel()
#     try:
#         await task
#     except:
#         pass


# app = FastAPI(lifespan=lifespan)
app = FastAPI()

app.mount("/api", api_app, "API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8015)
