from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.schemas.schemas import ParetoResponse, YieldResponse
from app.services import analytics_service

router = APIRouter()

_auth = Depends(require_role("engineer", "admin"))
_DaysQuery = Annotated[int, Query(ge=1, le=730, description="Look-back window in calendar days")]


@router.get(
    "/yield",
    response_model=YieldResponse,
    summary="First-pass yield by product",
    dependencies=[_auth],
)
async def get_yield(
    db: AsyncSession = Depends(get_db),
    days: _DaysQuery = 7,
) -> YieldResponse:
    """
    FCT first-pass yield grouped by product SKU for the last *days* calendar days.
    `fpy_pct` is rounded to two decimal places.
    """
    return await analytics_service.get_yield(db, days)


@router.get(
    "/failures",
    response_model=ParetoResponse,
    summary="Failure-mode Pareto",
    dependencies=[_auth],
)
async def get_failure_pareto(
    db: AsyncSession = Depends(get_db),
    days: _DaysQuery = 7,
) -> ParetoResponse:
    """
    Pareto of failure modes (FAIL runs with a non-null failure_mode) sorted by
    frequency descending.  `pct` is each mode's share of total failures in the window.
    """
    return await analytics_service.get_failure_pareto(db, days)
