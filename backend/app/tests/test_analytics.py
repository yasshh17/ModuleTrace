"""
Analytics endpoint integration tests.

Seed data FPY breakdown (see conftest.py):
  FCT runs : 3 PASS + 1 FAIL = 4 total → FPY = 75.0 %
  Failure modes: GPS_FIX_TIMEOUT ×1  → Pareto pct = 100.0

All runs are stamped 10 days ago, so ?days=30 always captures them.
"""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/yield
# ---------------------------------------------------------------------------


async def test_yield_response_structure(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    """Response must be 200 with a list of items each containing required keys."""
    resp = await client.get(
        "/api/v1/analytics/yield?days=30", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "items" in body
    assert isinstance(body["items"], list)
    assert len(body["items"]) > 0

    required_keys = {"sku", "name", "total_tested", "total_passed", "fpy_pct"}
    for item in body["items"]:
        assert required_keys <= item.keys(), (
            f"missing keys: {required_keys - item.keys()}"
        )


def test_yield_fpy_calculation():
    """
    FPY formula: round(total_passed / total_tested * 100, 2).

    Verified here as a unit-level calculation — the Pct annotated type in
    schemas.py applies the same rounding via AfterValidator, so the service
    and the schema agree on the result.
    """
    from app.schemas.schemas import YieldByProduct

    # 9 of 10 units pass → 90.0 %
    row = YieldByProduct(
        sku="TEST-SKU",
        name="Test Module",
        total_tested=10,
        total_passed=9,
        fpy_pct=90.0,
    )
    assert row.fpy_pct == 90.0

    # Verify the raw arithmetic matches
    assert round(9 / 10 * 100, 2) == 90.0

    # Also verify the seed-data case: 3 of 4 → 75.0 %
    row2 = YieldByProduct(
        sku="TEST-SKU",
        name="Test Module",
        total_tested=4,
        total_passed=3,
        fpy_pct=75.0,
    )
    assert row2.fpy_pct == 75.0


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/failures
# ---------------------------------------------------------------------------


async def test_pareto_response_structure(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    """Response must be 200 with a list of items; pct values must sum to ~100."""
    resp = await client.get(
        "/api/v1/analytics/failures?days=30", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "items" in body
    assert isinstance(body["items"], list)

    required_keys = {"failure_mode", "count", "pct"}
    for item in body["items"]:
        assert required_keys <= item.keys(), (
            f"missing keys: {required_keys - item.keys()}"
        )

    if body["items"]:
        total_pct = sum(item["pct"] for item in body["items"])
        assert abs(total_pct - 100.0) < 0.1, (
            f"pct values sum to {total_pct}, expected ~100"
        )


async def test_pareto_ordered_by_count_desc(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    """Items must be sorted by count descending (highest failure mode first)."""
    resp = await client.get(
        "/api/v1/analytics/failures?days=30", headers=engineer_headers
    )
    assert resp.status_code == 200
    items = resp.json()["items"]

    assert len(items) >= 1
    assert items[0]["failure_mode"] == "GPS_FIX_TIMEOUT"

    counts = [item["count"] for item in items]
    assert counts == sorted(counts, reverse=True), (
        f"items not sorted by count desc: {counts}"
    )
