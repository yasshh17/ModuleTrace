"""
Test fixtures for ModuleTrace backend.

Database strategy
-----------------
Tests run against an in-memory SQLite database (aiosqlite driver).
A StaticPool forces all async connections to share the same underlying
connection, which is required for in-memory SQLite to work across multiple
sessions/requests within one test.

JSONB columns fall back to JSON/TEXT on SQLite — see models.py for the
with_variant() call that makes this transparent.

Auth strategy
-------------
We create real User rows and generate valid JWTs with create_access_token
so that the full auth dependency chain is exercised without hitting a real DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.models import Base, Module, Operator, Product, TestRun, User, WorkOrder

# ---------------------------------------------------------------------------
# Constants shared across fixtures
# ---------------------------------------------------------------------------

_DUMMY_HASH = bcrypt.hashpw(b"test_password_123", bcrypt.gensalt()).decode()

_NOW = datetime.now(timezone.utc)
_T = _NOW - timedelta(days=10)  # 10 days ago — inside any 30-day analytics window
_T_RUN = _T + timedelta(hours=2)  # test runs happen 2 h after production

# ---------------------------------------------------------------------------
# Engine — single in-memory SQLite shared via StaticPool
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    """
    Fresh in-memory SQLite engine per test.

    StaticPool makes every engine.connect() call reuse the same physical
    connection, so the in-memory database is visible to all sessions created
    from this engine during one test.
    """
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


# ---------------------------------------------------------------------------
# HTTP test client with get_db overridden to use the test engine
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(engine):
    """
    httpx AsyncClient wired to the FastAPI app with get_db overridden to
    produce sessions from the test engine.
    """
    TestSession = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _test_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _test_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seed_data(engine):
    """
    Insert one complete fixture dataset and return a plain dict of the key
    ORM objects so individual tests can reference IDs, serials, etc.

    Dataset
    -------
    Products   : 1  (TEST-SKU-001)
    Work orders: 1  (WO-TEST-001)
    Operators  : 2
    Users      : 3  (operator / engineer / quality)
    Modules    : 5  — 3 pass, 1 fail, 1 in_progress
    Test runs  : 8  — 3 FCT PASS, 1 FCT FAIL, 4 AOI PASS
    """
    TestSession = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestSession() as session:
        # ── Product ───────────────────────────────────────────────────────
        product = Product(
            sku="TEST-SKU-001",
            name="Test Module",
            hw_rev="A",
            fw_version="1.0.0",
            created_at=_T,
        )
        session.add(product)
        await session.flush()

        # ── Work order ────────────────────────────────────────────────────
        wo = WorkOrder(
            wo_number="WO-TEST-001",
            product_id=product.id,
            qty_planned=10,
            opened_at=_T,
        )
        session.add(wo)
        await session.flush()

        # ── Operators ─────────────────────────────────────────────────────
        op1 = Operator(employee_code="OP-T01", name="Test Op 1", active=True)
        op2 = Operator(employee_code="OP-T02", name="Test Op 2", active=True)
        session.add_all([op1, op2])
        await session.flush()

        # ── Users (for JWT auth) ──────────────────────────────────────────
        u_op = User(
            email="op@test.com",
            hashed_password=_DUMMY_HASH,
            full_name="Test Operator",
            role="operator",
        )
        u_eng = User(
            email="eng@test.com",
            hashed_password=_DUMMY_HASH,
            full_name="Test Engineer",
            role="engineer",
        )
        u_qual = User(
            email="qual@test.com",
            hashed_password=_DUMMY_HASH,
            full_name="Test Quality",
            role="quality",
        )
        session.add_all([u_op, u_eng, u_qual])
        await session.flush()

        # ── Modules ───────────────────────────────────────────────────────
        m1 = Module(
            pcba_serial="EW-TEST-000001",
            imei="358291046100001",
            work_order_id=wo.id,
            status="in_progress",
            produced_at=_T,
        )
        m2 = Module(
            pcba_serial="EW-TEST-000002",
            work_order_id=wo.id,
            status="pass",
            produced_at=_T,
        )
        m3 = Module(
            pcba_serial="EW-TEST-000003",
            work_order_id=wo.id,
            status="pass",
            produced_at=_T,
        )
        m4 = Module(
            pcba_serial="EW-TEST-000004",
            work_order_id=wo.id,
            status="pass",
            produced_at=_T,
        )
        m5 = Module(
            pcba_serial="EW-TEST-000005",
            work_order_id=wo.id,
            status="fail",
            produced_at=_T,
        )
        session.add_all([m1, m2, m3, m4, m5])
        await session.flush()

        # ── Test runs (8 total) ───────────────────────────────────────────
        # FCT runs drive FPY analytics: 3 PASS + 1 FAIL = 75.0 %
        # AOI runs are structural filler (not counted in FPY).
        session.add_all(
            [
                # FCT
                TestRun(module_id=m2.id, station="FCT", result="PASS",
                        operator_id=op1.id, tested_at=_T_RUN),
                TestRun(module_id=m3.id, station="FCT", result="PASS",
                        operator_id=op1.id, tested_at=_T_RUN),
                TestRun(module_id=m4.id, station="FCT", result="PASS",
                        operator_id=op2.id, tested_at=_T_RUN),
                TestRun(module_id=m5.id, station="FCT", result="FAIL",
                        failure_mode="GPS_FIX_TIMEOUT",
                        operator_id=op2.id, tested_at=_T_RUN),
                # AOI
                TestRun(module_id=m1.id, station="AOI", result="PASS",
                        operator_id=op1.id, tested_at=_T_RUN),
                TestRun(module_id=m2.id, station="AOI", result="PASS",
                        operator_id=op2.id, tested_at=_T_RUN),
                TestRun(module_id=m3.id, station="AOI", result="PASS",
                        operator_id=op1.id, tested_at=_T_RUN),
                TestRun(module_id=m4.id, station="AOI", result="PASS",
                        operator_id=op2.id, tested_at=_T_RUN),
            ]
        )
        await session.commit()

        # expire_on_commit=False means IDs are still readable after commit.
        return {
            "users": {"operator": u_op, "engineer": u_eng, "quality": u_qual},
            "product": product,
            "work_order": wo,
            "operators": [op1, op2],
            "modules": [m1, m2, m3, m4, m5],
        }


# ---------------------------------------------------------------------------
# Auth header fixtures
# ---------------------------------------------------------------------------

def _make_token(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id), "role": user.role},
        timedelta(minutes=30),
    )


@pytest_asyncio.fixture
async def operator_headers(seed_data):
    return {"Authorization": f"Bearer {_make_token(seed_data['users']['operator'])}"}


@pytest_asyncio.fixture
async def engineer_headers(seed_data):
    return {"Authorization": f"Bearer {_make_token(seed_data['users']['engineer'])}"}


@pytest_asyncio.fixture
async def quality_headers(seed_data):
    return {"Authorization": f"Bearer {_make_token(seed_data['users']['quality'])}"}
