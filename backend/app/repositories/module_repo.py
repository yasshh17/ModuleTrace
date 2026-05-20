from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Module, Product, WorkOrder


# ---------------------------------------------------------------------------
# Shared eager-load options
# ---------------------------------------------------------------------------
# Used by the single-module lookups that need the full object graph for the
# ModuleDetailResponse schema (work_order → product, test_runs → operator).

def _detail_options():
    from app.models.models import TestRun, Operator
    return [
        selectinload(Module.work_order).selectinload(WorkOrder.product),
        selectinload(Module.test_runs).selectinload(TestRun.operator),
    ]


def _list_options():
    """Minimal load for ModuleListItem: work_order → product only."""
    return [
        selectinload(Module.work_order).selectinload(WorkOrder.product),
    ]


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

async def get_by_serial_or_imei(db: AsyncSession, identifier: str) -> Module | None:
    """
    Return a fully-loaded Module whose pcba_serial OR imei matches *identifier*.
    Eagerly loads: work_order → product, test_runs → operator.
    """
    stmt = (
        select(Module)
        .where(
            or_(
                Module.pcba_serial == identifier,
                Module.imei == identifier,
            )
        )
        .options(*_detail_options())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_module_detail(db: AsyncSession, module_id: int) -> Module | None:
    """
    Return a fully-loaded Module by primary key.
    Eagerly loads: work_order → product, test_runs → operator.
    """
    stmt = (
        select(Module)
        .where(Module.id == module_id)
        .options(*_detail_options())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# List with filtering + pagination
# ---------------------------------------------------------------------------

async def list_modules(
    db: AsyncSession,
    *,
    status: str | None = None,
    product_sku: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Module], int]:
    """
    Return *(items, total_count)*.

    Joins through work_order → product so both the status and sku filters can
    reference those tables.  Eager-loads work_order → product on the result
    set so callers can traverse the relationship without extra queries.

    Results are ordered newest-first (produced_at DESC).
    """
    # Base statement shared by both the data query and the count query.
    base = (
        select(Module)
        .join(Module.work_order)
        .join(WorkOrder.product)
    )

    filters = []
    if status is not None:
        filters.append(Module.status == status)
    if product_sku is not None:
        filters.append(Product.sku == product_sku)

    if filters:
        base = base.where(*filters)

    # ── total count (no loading, no ordering) ──────────────────────────── #
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # ── paginated data fetch ───────────────────────────────────────────── #
    data_stmt = (
        base
        .options(*_list_options())
        .order_by(Module.produced_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(data_stmt)).scalars().all()

    return list(rows), total


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

async def create_module(
    db: AsyncSession,
    *,
    pcba_serial: str,
    work_order_id: int,
) -> Module:
    module = Module(pcba_serial=pcba_serial, work_order_id=work_order_id)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


async def update_module_status(
    db: AsyncSession,
    module_id: int,
    status: str,
) -> Module | None:
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if module is None:
        return None
    module.status = status
    await db.commit()
    await db.refresh(module)
    return module
