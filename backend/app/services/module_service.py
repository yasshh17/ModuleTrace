import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import module_repo
from app.schemas.schemas import ModuleDetailResponse, ModuleListItem, ModuleListResponse

logger = structlog.get_logger(__name__)


async def get_module_detail(db: AsyncSession, identifier: str) -> ModuleDetailResponse:
    """
    Return full module detail (including test history) for a given
    pcba_serial or IMEI.  Raises 404 when no match is found.
    """
    module = await module_repo.get_by_serial_or_imei(db, identifier)
    if module is None:
        logger.info("module_not_found", identifier=identifier)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )
    # ModuleDetailResponse.model_validate reads module.test_runs via the
    # alias="test_runs" Field, and each TestRunSummary flattens operator.name.
    return ModuleDetailResponse.model_validate(module)


async def list_modules(
    db: AsyncSession,
    *,
    status: str | None = None,
    product_sku: str | None = None,
    page: int = 1,
    size: int = 20,
) -> ModuleListResponse:
    """Return a paginated list of modules, optionally filtered by status and/or SKU."""
    modules, total = await module_repo.list_modules(
        db,
        status=status,
        product_sku=product_sku,
        page=page,
        size=size,
    )
    return ModuleListResponse(
        items=[ModuleListItem.model_validate(m) for m in modules],
        total=total,
        page=page,
        size=size,
    )
