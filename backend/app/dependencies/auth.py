from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import InvalidTokenError, decode_access_token
from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.repositories.user_repository import UserRepository

security_scheme = HTTPBearer(auto_error=False)


def get_database(request: Request) -> MongoDatabase:
    return request.app.state.database


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    database: MongoDatabase = Depends(get_database),
    request: Request = None,
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    try:
        payload = decode_access_token(credentials.credentials, request.app.state.settings)
        revoked = await database.database.revokedTokens.find_one({"jti": payload["jti"]})
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")
        user = await UserRepository(database).find_by_id(payload["sub"])
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists.")
    return user
