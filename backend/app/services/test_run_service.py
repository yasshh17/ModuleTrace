import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import module_repo, test_run_repo
from app.schemas.schemas import TestRunCreate, TestRunResponse

logger = structlog.get_logger(__name__)


def _derive_module_status(result: str, station: str) -> str | None:
    """
    Compute the module status transition implied by this test result.

    Rules (applied in order):
      FAIL at any station  → module.status = 'fail'
      PASS at FCT station  → module.status = 'pass'
      PASS / RETEST at any other station → no status change (return None)
    """
    if result == "FAIL":
        return "fail"
    if result == "PASS" and station == "FCT":
        return "pass"
    return None


async def create_test_run(
    db: AsyncSession,
    data: TestRunCreate,
) -> TestRunResponse:
    """
    Record a test result for the module identified by *data.module_serial*.

    Business rules:
      - Module must exist → 404 if not.
      - FAIL at any station sets module.status = 'fail'.
      - PASS at FCT sets module.status = 'pass'.
      - The TestRun INSERT and any module status change are committed atomically.
    """
    module = await module_repo.get_by_serial_or_imei(db, data.module_serial)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{data.module_serial}' not found",
        )

    new_module_status = _derive_module_status(data.result, data.station)

    run = await test_run_repo.create_test_run_with_status_update(
        db,
        module=module,
        station=data.station,
        result=data.result,
        failure_mode=data.failure_mode,
        measurements=data.measurements,
        operator_id=data.operator_id,
        new_module_status=new_module_status,
    )

    logger.info(
        "test_run_created",
        module_serial=data.module_serial,
        module_id=module.id,
        station=data.station,
        result=data.result,
        new_module_status=new_module_status,
    )

    return TestRunResponse.model_validate(run)
