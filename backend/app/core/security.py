from datetime import timedelta, datetime, timezone
from typing import Callable

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User

# HTTPBearer extracts the token from "Authorization: Bearer <token>" and
# exposes a padlock in the Swagger UI where a token can be pasted directly.
_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------
# We call bcrypt directly rather than through passlib because passlib's
# bcrypt backend probe generates a 72-byte test password that bcrypt ≥ 4.0
# rejects with ValueError.  The bcrypt API is stable and straightforward.

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # Raised by bcrypt when hashed is not a valid bcrypt hash (e.g.
        # corrupted DB row).  Treat as a failed verification, not a crash.
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
    Encode *data* into a signed JWT that expires after *expires_delta*.

    The caller is responsible for passing the claims it wants in the token
    (typically {"sub": str(user.id), "role": user.role}).
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.  Raises HTTP 401 for any failure:
    expired signature, invalid signature, malformed token, etc.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that extracts the Bearer token, verifies it, and returns
    the matching User row from the database.

    Raises HTTP 401 when the token is missing, invalid, or references a
    user that no longer exists.
    """
    payload = decode_token(credentials.credentials)

    raw_sub = payload.get("sub")
    if raw_sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(raw_sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*roles: str) -> Callable:
    """
    Dependency factory that gates a route to users whose role is in *roles*.

    Usage::

        @router.delete("/{id}", dependencies=[Depends(require_role("admin"))])
        async def delete_something(...):
            ...

        # Or when you also need the user object:
        @router.post("/")
        async def create_something(user: User = Depends(require_role("admin", "engineer"))):
            ...
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted for this action",
            )
        return user

    return _check
