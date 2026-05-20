from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Module, Product, TestRun, WorkOrder


# ---------------------------------------------------------------------------
# Transactional write (used by test_run_service)
# ---------------------------------------------------------------------------

async def create_test_run_with_status_update(
    db: AsyncSession,
    *,
    module: Module,
    station: str,
    result: str,
    failure_mode: str | None = None,
    measurements: dict | None = None,
    operator_id: int | None = None,
    new_module_status: str | None,
) -> TestRun:
    """
    Atomically insert a TestRun and, when *new_module_status* is not None,
    update the module's status in the same transaction.

    *module* must already be in this session's identity map so that the
    status mutation and the INSERT share one commit.
    """
    run = TestRun(
        module_id=module.id,
        station=station,
        result=result,
        failure_mode=failure_mode,
        measurements=measurements,
        operator_id=operator_id,
    )
    db.add(run)
    if new_module_status is not None:
        module.status = new_module_status
    await db.commit()
    await db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

async def create_test_run(
    db: AsyncSession,
    *,
    module_id: int,
    station: str,
    result: str,
    failure_mode: str | None = None,
    measurements: dict | None = None,
    operator_id: int | None = None,
) -> TestRun:
    run = TestRun(
        module_id=module_id,
        station=station,
        result=result,
        failure_mode=failure_mode,
        measurements=measurements,
        operator_id=operator_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# Analytics — core queries, return list[dict]
# ---------------------------------------------------------------------------

async def get_yield_by_product(
    db: AsyncSession,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """
    First-pass yield grouped by product, restricted to FCT station runs
    within *from_date* .. *to_date* (inclusive).

    Returns a list of plain dicts with keys:
      sku, name, total_tested, total_passed

    The caller (AnalyticsService) computes fpy_pct from these values.
    """
    stmt = (
        select(
            Product.sku,
            Product.name,
            func.count().label("total_tested"),
            func.sum(
                case((TestRun.result == "PASS", 1), else_=0)
            ).label("total_passed"),
        )
        .select_from(TestRun)
        .join(Module, TestRun.module_id == Module.id)
        .join(WorkOrder, Module.work_order_id == WorkOrder.id)
        .join(Product, WorkOrder.product_id == Product.id)
        .where(
            TestRun.station == "FCT",
            TestRun.tested_at.between(from_date, to_date),
        )
        .group_by(Product.sku, Product.name)
        .order_by(Product.sku)
    )

    rows = (await db.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]


async def get_failure_pareto(
    db: AsyncSession,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """
    Pareto of failure modes across all stations within *from_date* .. *to_date*.

    Only FAIL rows with a non-null failure_mode are considered.

    Returns a list of plain dicts with keys:
      failure_mode, count, pct   (pct = share of total failures, 0–100)

    Ordered by count DESC (most frequent first).
    Pct is computed in the database via a scalar subquery so the result
    is consistent even when the caller receives a partial page.
    """
    failure_filter = (
        TestRun.result == "FAIL",
        TestRun.failure_mode.isnot(None),
        TestRun.tested_at.between(from_date, to_date),
    )

    # Scalar subquery for the denominator — reuses the same filter so it
    # stays consistent with the grouped rows above.
    total_subq = (
        select(func.count())
        .where(*failure_filter)
        .scalar_subquery()
    )

    stmt = (
        select(
            TestRun.failure_mode,
            func.count().label("count"),
            # Guard against zero denominator (e.g. called on an empty date range).
            case(
                (total_subq > 0, func.count() * 100.0 / total_subq),
                else_=0.0,
            ).label("pct"),
        )
        .where(*failure_filter)
        .group_by(TestRun.failure_mode)
        .order_by(func.count().desc())
    )

    rows = (await db.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]
