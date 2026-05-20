from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.schemas.schemas import TestRunCreate, TestRunResponse
from app.services import test_run_service

router = APIRouter()


@router.post(
    "/",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a test result",
    dependencies=[Depends(require_role("operator", "engineer", "admin"))],
)
async def create_test_run(
    body: TestRunCreate,
    db: AsyncSession = Depends(get_db),
) -> TestRunResponse:
    """
    Record the result of one test station run against a module.

    - **FAIL** at any station → module status transitions to `fail`.
    - **PASS** at **FCT** → module status transitions to `pass`.
    - All other combinations leave the module status unchanged.
    """
    return await test_run_service.create_test_run(db, body)
