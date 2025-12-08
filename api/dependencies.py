from fastapi import Request  # твой класс JWTTools
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from api.auth.schemas import AuthUserRole
from api.auth.services.helpers import JWTTools


class AuthUserData(BaseModel):
    user: dict  # {"id": 1, "role": 0}


def get_current_user(request: Request) -> int:
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = auth_header.split(" ")[1]
    payload = JWTTools.decode_jwt(token)

    if not payload.user and not payload.user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return payload.user.id


http_bearer = HTTPBearer()


async def require_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
):
    token = credentials.credentials
    token_data = JWTTools.decode_jwt(token)

    user = token_data.user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    if user.role != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role required",
        )

    if user.id == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User token required.",
        )

    return user


async def require_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
):
    token = credentials.credentials
    token_data = JWTTools.decode_jwt(token)

    user = token_data.user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    if user.id != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin token required.",
        )

    return user
