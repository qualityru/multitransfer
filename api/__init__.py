from fastapi import Depends, FastAPI

# from api.auth.routes import router as auth_router
# from api.auth.services.auth import AuthTools
from api.transfer.routes import router as transfer_router

# from api.user.routes import router as user_router

api_app = FastAPI(
    # root_path="/v1",
    title="multitransfer API"
)


api_app.include_router(transfer_router)
