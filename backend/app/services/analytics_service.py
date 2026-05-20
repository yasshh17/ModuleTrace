from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import test_run_repo
from app.schemas.schemas import (
    FailureModeCount,
    ParetoResponse,
    YieldByProduct,
    YieldResponse,
)

logger = structlog.get_logger(__name__)


async def get_yield(db: AsyncSession, days: int) -> YieldResponse:
    """
    First-pass yield by product for the last *days* calendar days.

    fpy_pct = total_passed / total_tested * 100, rounded to 2 dp.
    Defaults to 0.0 when total_tested is zero (no FCT runs in the window).
    """
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)

    rows = await test_run_repo.get_yield_by_product(db, from_date, to_date)

    items: list[YieldByProduct] = []
    for row in rows:
        total_tested: int = row["total_tested"]
        # SUM() returns Decimal or None when there are no rows; normalise to int.
        total_passed: int = int(row["total_passed"] or 0)
        fpy_pct = round(total_passed / total_tested * 100, 2) if total_tested > 0 else 0.0
        items.append(
            YieldByProduct(
                sku=row["sku"],
                name=row["name"],
                total_tested=total_tested,
                total_passed=total_passed,
                fpy_pct=fpy_pct,
            )
        )

    logger.info("yield_computed", days=days, product_count=len(items))

    return YieldResponse(
        items=items,
        from_date=from_date.date().isoformat(),
        to_date=to_date.date().isoformat(),
    )


async def get_failure_pareto(db: AsyncSession, days: int) -> ParetoResponse:
    """
    Pareto chart of failure modes for the last *days* calendar days.

    total_failures is the sum of all per-mode counts, so it equals the total
    number of FAIL rows with a non-null failure_mode in the date window.
    """
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)

    rows = await test_run_repo.get_failure_pareto(db, from_date, to_date)

    total_failures: int = sum(row["count"] for row in rows)

    items = [
        FailureModeCount(
            failure_mode=row["failure_mode"],
            count=row["count"],
            # pct is computed in the DB; normalise Decimal → float safely.
            pct=float(row["pct"] or 0.0),
        )
        for row in rows
    ]

    return ParetoResponse(items=items, total_failures=total_failures)
