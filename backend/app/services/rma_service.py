import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import rma_repo
from app.schemas.schemas import RMACreate, RMAResponse, RMAUpdate

logger = structlog.get_logger(__name__)


async def get_rma_by_module(db: AsyncSession, module_serial: str) -> RMAResponse:
    """Return the RMA record for *module_serial*.  Raises 404 when not found."""
    rma = await rma_repo.get_rma_by_module_serial(db, module_serial)
    if rma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RMA not found",
        )
    return RMAResponse.model_validate(rma)


async def create_rma(db: AsyncSession, data: RMACreate) -> RMAResponse:
    """
    Open an RMA for *data.module_serial*.

    Business rules:
      - Module must exist → 404 if not.
      - Module must not already have an open RMA → 409 if it does.
      - RMA insertion and module status change are committed atomically.
    """
    module = await rma_repo.get_module_with_rma(db, data.module_serial)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    if module.rma is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RMA already open for this module",
        )

    rma = await rma_repo.create_rma_and_update_module_status(
        db,
        module=module,
        issue=data.issue,
    )

    logger.info("rma_created", module_serial=data.module_serial, rma_id=rma.id)
    return RMAResponse.model_validate(rma)


async def update_rma(
    db: AsyncSession,
    module_serial: str,
    data: RMAUpdate,
) -> RMAResponse:
    """
    Partially update an RMA.

    Only fields that are explicitly provided (non-None) in *data* are written.
    Providing None for a field means "leave it unchanged", not "set to null".
    """
    rma = await rma_repo.get_rma_by_module_serial(db, module_serial)
    if rma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RMA not found",
        )

    # Build the update payload from only the caller-supplied fields.
    updates: dict = {}
    if data.root_cause is not None:
        updates["root_cause"] = data.root_cause
    if data.status is not None:
        updates["status"] = data.status

    if updates:
        rma = await rma_repo.apply_updates_and_save(db, rma, updates, module_serial)

    logger.info("rma_updated", module_serial=module_serial, fields=list(updates))
    return RMAResponse.model_validate(rma)
