"""
Module and test-run endpoint integration tests.

All tests share an in-memory SQLite database via the conftest fixtures.
Tests that mutate state (test 6) are designed not to break earlier assertions:
  - test_create_test_run_updates_module_status targets EW-TEST-000001
    (in_progress → pass after the POST), which no other test asserts on status.
"""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/v1/modules/{identifier}
# ---------------------------------------------------------------------------


async def test_get_module_by_serial_found(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    resp = await client.get(
        "/api/v1/modules/EW-TEST-000001", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pcba_serial"] == "EW-TEST-000001"
    assert isinstance(body["test_history"], list)


async def test_get_module_by_imei_found(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    resp = await client.get(
        "/api/v1/modules/358291046100001", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imei"] == "358291046100001"
    assert body["pcba_serial"] == "EW-TEST-000001"


async def test_get_module_not_found(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    resp = await client.get(
        "/api/v1/modules/DOESNOTEXIST", headers=engineer_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/modules  (list + pagination + filtering)
# ---------------------------------------------------------------------------


async def test_list_modules_paginated(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    resp = await client.get(
        "/api/v1/modules?page=1&size=3", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert len(body["items"]) <= 3
    assert body["total"] == 5  # 5 seeded modules


async def test_list_modules_filter_by_status(
    client: AsyncClient, engineer_headers: dict, seed_data
):
    resp = await client.get(
        "/api/v1/modules?status=pass", headers=engineer_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) > 0, "expected at least one pass module"
    for item in body["items"]:
        assert item["status"] == "pass", f"unexpected status {item['status']!r}"


# ---------------------------------------------------------------------------
# POST /api/v1/test-runs  →  module status transition
# ---------------------------------------------------------------------------


async def test_create_test_run_updates_module_status(
    client: AsyncClient,
    operator_headers: dict,
    engineer_headers: dict,
    seed_data,
):
    """
    Posting an FCT PASS for an in_progress module must flip its status to 'pass'.

    Uses EW-TEST-000001 which starts as 'in_progress' in the seed data.
    """
    # POST the test run
    post_resp = await client.post(
        "/api/v1/test-runs/",
        json={
            "module_serial": "EW-TEST-000001",
            "station": "FCT",
            "result": "PASS",
        },
        headers=operator_headers,
    )
    assert post_resp.status_code == 201

    # GET the module and confirm the status transition
    get_resp = await client.get(
        "/api/v1/modules/EW-TEST-000001", headers=engineer_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "pass"
