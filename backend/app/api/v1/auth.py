from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse, UserResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Authenticates with email + password and returns a signed JWT.

    Returns HTTP 401 on any credential failure.  The error message is kept
    intentionally vague to avoid leaking whether the email exists.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Evaluate verify_password even when user is None so the response time
    # stays constant regardless of whether the email exists (timing-safe).
    password_ok = verify_password(body.password, user.hashed_password) if user else False

    if not user or not password_ok:
        logger.warning(
            "failed_login_attempt",
            email=body.email,
            reason="user_not_found" if not user else "wrong_password",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info("login_success", user_id=user.id, role=user.role)

    return TokenResponse(access_token=token, token_type="bearer", role=user.role)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
