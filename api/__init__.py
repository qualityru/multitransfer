from fastapi import FastAPI

from api.transfer.routes import router as transfer_router

api_app = FastAPI(title="Multitransfer API")
api_app.include_router(transfer_router)
