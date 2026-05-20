"""
RMA repository — all SQLAlchemy for RMA reads and writes lives here.

The two write functions (create_rma_and_update_module_status,
apply_updates_and_save) accept an already-loaded Module or RMA object
from the calling service.  This keeps the session, the object, and the
commit in the same layer without introducing a second round-trip.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Module, RMA


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

async def get_module_with_rma(db: AsyncSession, module_serial: str) -> Module | None:
    """
    Return a Module with its *rma* relationship eagerly loaded.
    Used by the service to check whether an RMA already exists before
    creating a new one (the 409 guard).
    """
    stmt = (
        select(Module)
        .where(Module.pcba_serial == module_serial)
        .options(selectinload(Module.rma))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_rma_by_module_serial(db: AsyncSession, module_serial: str) -> RMA | None:
    """
    Return an RMA joined to its Module, eagerly loading Module so that
    RMAResponse._flatten_module_serial can read rma.module.pcba_serial
    without triggering a lazy load.
    """
    stmt = (
        select(RMA)
        .join(RMA.module)
        .where(Module.pcba_serial == module_serial)
        .options(selectinload(RMA.module))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

async def create_rma_and_update_module_status(
    db: AsyncSession,
    *,
    module: Module,
    issue: str,
) -> RMA:
    """
    Atomically insert a new RMA row and set module.status = 'rma'.

    *module* must already be in this session's identity map (i.e. loaded
    earlier in the same request) so that the status update and the INSERT
    share one transaction and one commit.

    Returns the new RMA with its *module* relationship loaded (needed for
    RMAResponse serialisation).
    """
    rma = RMA(module_id=module.id, issue=issue)
    db.add(rma)
    module.status = "rma"
    await db.commit()
    # Re-fetch so rma.module is populated for RMAResponse.
    return await get_rma_by_module_serial(db, module.pcba_serial)


async def apply_updates_and_save(
    db: AsyncSession,
    rma: RMA,
    updates: dict,
    module_serial: str,
) -> RMA:
    """
    Apply *updates* dict to *rma*, commit, then re-fetch with module loaded.

    The service decides which keys go into *updates* — that is the business
    logic (partial update: None means "do not change").  This function only
    handles the SQLAlchemy persistence.
    """
    for key, value in updates.items():
        setattr(rma, key, value)
    await db.commit()
    return await get_rma_by_module_serial(db, module_serial)
