"""Seed the ModuleTrace database with realistic test data.

Usage:
    cd backend
    python scripts/seed.py

Idempotent: safe to run multiple times. Modules already in the DB (by pcba_serial)
are skipped; their test runs and RMAs are also skipped.
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ENV_PATH = Path(__file__).parent.parent.parent / ".env"


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env(_ENV_PATH)

_RAW_URL = os.environ.get("DATABASE_URL", "")
if not _RAW_URL:
    sys.exit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")

# Convert asyncpg URL to psycopg2 DSN
_DSN = _RAW_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = random.Random(42)  # deterministic


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _luhn_check_digit(digits: str) -> int:
    """Return the Luhn check digit for the given digit string."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - (total % 10)) % 10


def _make_imei(tac: str, counter: int) -> str:
    body = f"{tac}{counter:06d}"  # 14 digits
    return body + str(_luhn_check_digit(body))


# Working-hours timestamp progression: 08:00–18:00, Mon–Fri.
# Each call advances the clock by `step_minutes`.
def _make_clock(start: datetime, step_minutes: int = 12):
    """Generator that yields successive working-hours datetimes."""
    current = start
    while True:
        # Skip weekends
        while current.weekday() >= 5:
            current += timedelta(days=1)
        hour = current.hour
        if hour < 8:
            current = current.replace(hour=8, minute=0, second=0, microsecond=0)
        elif hour >= 18:
            # Roll to next working day
            current = (current + timedelta(days=1)).replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            while current.weekday() >= 5:
                current += timedelta(days=1)
        yield current
        current += timedelta(minutes=step_minutes)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_PRODUCTS = [
    {
        "sku": "EW-5G-M100",
        "name": "Eagle 5G Module M100",
        "hw_revision": "C",
        "tac": "35829104",
    },
    {
        "sku": "EW-LTE-A200",
        "name": "Eagle LTE Advanced A200",
        "hw_revision": "B",
        "tac": "86110402",
    },
    {
        "sku": "EW-CAT1-S50",
        "name": "Eagle CAT-1 S50",
        "hw_revision": "A",
        "tac": "01324807",
    },
]

_OPERATORS = [
    {"name": "Maria Santos", "employee_code": "OP-1001"},
    {"name": "James Nguyen", "employee_code": "OP-1002"},
    {"name": "Priya Sharma", "employee_code": "OP-1003"},
    {"name": "Carlos Vega", "employee_code": "OP-1004"},
]

_USERS = [
    {"email": "operator@ew.com", "full_name": "Demo Operator", "role": "operator", "password": "demo1234"},
    {"email": "engineer@ew.com", "full_name": "Demo Engineer", "role": "engineer", "password": "demo1234"},
    {"email": "quality@ew.com",  "full_name": "Demo Quality",  "role": "quality",  "password": "demo1234"},
]

# Work orders: (wo_number, sku, planned_qty, base_date as Monday string, label)
_WORK_ORDERS = [
    ("WO-2025-0043", "EW-5G-M100",  200, "2025-01-06", "normal"),
    ("WO-2025-0044", "EW-LTE-A200", 150, "2025-01-13", "normal"),
    ("WO-2025-0045", "EW-CAT1-S50", 100, "2025-01-20", "normal"),
    ("WO-2025-0046", "EW-5G-M100",  250, "2025-02-03", "normal"),
    ("WO-2025-0047", "EW-5G-M100",   60, "2025-02-17", "special"),
]

_FAILURE_MODES = [
    ("GPS_FIX_TIMEOUT",   0.50),
    ("RF_TX_POWER_LOW",   0.25),
    ("CURRENT_DRAW_HIGH", 0.15),
    ("AOI_SOLDER_BRIDGE", 0.07),
    ("FLASH_VERIFY_FAIL", 0.03),
]


def _pick_failure_mode() -> str:
    r = _RNG.random()
    cumulative = 0.0
    for mode, prob in _FAILURE_MODES:
        cumulative += prob
        if r < cumulative:
            return mode
    return _FAILURE_MODES[-1][0]


# ---------------------------------------------------------------------------
# Core seed logic
# ---------------------------------------------------------------------------

def _upsert_products(cur) -> dict[str, int]:
    """Insert products if absent; return {sku: id}."""
    result = {}
    for p in _PRODUCTS:
        cur.execute("SELECT id FROM products WHERE sku = %s", (p["sku"],))
        row = cur.fetchone()
        if row:
            result[p["sku"]] = row[0]
            continue
        cur.execute(
            "INSERT INTO products (sku, name, hw_rev) VALUES (%s, %s, %s) RETURNING id",
            (p["sku"], p["name"], p["hw_revision"]),
        )
        result[p["sku"]] = cur.fetchone()[0]
    return result


def _upsert_operators(cur) -> list[int]:
    """Insert operators if absent; return list of ids in definition order."""
    ids = []
    for op in _OPERATORS:
        cur.execute("SELECT id FROM operators WHERE employee_code = %s", (op["employee_code"],))
        row = cur.fetchone()
        if row:
            ids.append(row[0])
            continue
        cur.execute(
            "INSERT INTO operators (name, employee_code) VALUES (%s, %s) RETURNING id",
            (op["name"], op["employee_code"]),
        )
        ids.append(cur.fetchone()[0])
    return ids


def _upsert_users(cur) -> None:
    for u in _USERS:
        cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO users (email, hashed_password, full_name, role) VALUES (%s, %s, %s, %s)",
            (u["email"], _hash(u["password"]), u["full_name"], u["role"]),
        )


def _upsert_work_orders(cur, product_ids: dict[str, int]) -> dict[str, int]:
    """Insert work orders if absent; return {wo_number: id}."""
    result = {}
    for wo_num, sku, planned_qty, base_date_str, _ in _WORK_ORDERS:
        cur.execute("SELECT id FROM work_orders WHERE wo_number = %s", (wo_num,))
        row = cur.fetchone()
        if row:
            result[wo_num] = row[0]
            continue
        base_dt = datetime.fromisoformat(base_date_str).replace(
            hour=8, minute=0, tzinfo=timezone.utc
        )
        cur.execute(
            "INSERT INTO work_orders (wo_number, product_id, qty_planned, opened_at)"
            " VALUES (%s, %s, %s, %s) RETURNING id",
            (wo_num, product_ids[sku], planned_qty, base_dt),
        )
        result[wo_num] = cur.fetchone()[0]
    return result


def _insert_test_runs_for_normal_module(
    cur,
    module_id: int,
    operator_ids: list[int],
    clock,
    *,
    force_fail: bool = False,
) -> tuple[int, str]:
    """Insert the standard AOI→FCT→RF_TX→FLASH station suite.

    Returns (number_of_runs_inserted, final_module_status).
    """
    runs = 0
    final_status = "in_progress"

    # AOI — always PASS
    op = _RNG.choice(operator_ids)
    ts = next(clock)
    cur.execute(
        "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (module_id, "AOI", "PASS", op, ts),
    )
    runs += 1

    # FCT — 90% PASS unless force_fail
    if force_fail or _RNG.random() < 0.10:
        fm = _pick_failure_mode()
        op = _RNG.choice(operator_ids)
        ts = next(clock)
        cur.execute(
            "INSERT INTO test_runs (module_id, station, result, failure_mode, operator_id, tested_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (module_id, "FCT", "FAIL", fm, op, ts),
        )
        runs += 1
        # Retest (RETEST) after fail
        op = _RNG.choice(operator_ids)
        ts = next(clock)
        cur.execute(
            "INSERT INTO test_runs (module_id, station, result, failure_mode, operator_id, tested_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (module_id, "FCT", "RETEST", fm, op, ts),
        )
        runs += 1
        final_status = "fail"
        return runs, final_status

    op = _RNG.choice(operator_ids)
    ts = next(clock)
    cur.execute(
        "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (module_id, "FCT", "PASS", op, ts),
    )
    runs += 1

    # RF_TX — always PASS
    op = _RNG.choice(operator_ids)
    ts = next(clock)
    cur.execute(
        "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (module_id, "RF_TX", "PASS", op, ts),
    )
    runs += 1

    # FLASH — always PASS
    op = _RNG.choice(operator_ids)
    ts = next(clock)
    cur.execute(
        "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (module_id, "FLASH", "PASS", op, ts),
    )
    runs += 1

    final_status = "pass"
    return runs, final_status


def _seed_normal_work_order(
    cur,
    wo_num: str,
    wo_id: int,
    sku: str,
    base_date_str: str,
    planned_qty: int,
    product_meta: dict,
    operator_ids: list[int],
    serial_counters: dict,
    imei_counters: dict,
    stats: dict,
) -> None:
    tac = product_meta["tac"]
    hw_rev = product_meta["hw_revision"]
    year = datetime.fromisoformat(base_date_str).year

    base_dt = datetime.fromisoformat(base_date_str).replace(
        hour=8, minute=0, tzinfo=timezone.utc
    )
    clock = _make_clock(base_dt, step_minutes=10)

    # Produce 80% of planned_qty for normal WOs
    qty = int(planned_qty * 0.80)

    for i in range(qty):
        serial_key = (year, hw_rev)
        serial_counters[serial_key] = serial_counters.get(serial_key, 0) + 1
        counter = serial_counters[serial_key]

        pcba_serial = f"EW{year}{hw_rev}-{counter:06d}"

        # Check for existing module
        cur.execute("SELECT id FROM modules WHERE pcba_serial = %s", (pcba_serial,))
        if cur.fetchone():
            stats["modules_skipped"] += 1
            # Advance clock anyway so subsequent serials use plausible timestamps
            next(clock)
            continue

        imei_counters[tac] = imei_counters.get(tac, 0) + 1
        imei = _make_imei(tac, imei_counters[tac])

        produced_ts = next(clock)
        cur.execute(
            "INSERT INTO modules (pcba_serial, imei, work_order_id, status, produced_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (pcba_serial, imei, wo_id, "in_progress", produced_ts),
        )
        module_id = cur.fetchone()[0]
        stats["modules_created"] += 1

        run_count, final_status = _insert_test_runs_for_normal_module(
            cur, module_id, operator_ids, clock
        )
        stats["test_runs_created"] += run_count

        # Update module status
        cur.execute("UPDATE modules SET status = %s WHERE id = %s", (final_status, module_id))

        if (i + 1) % 10 == 0 or (i + 1) == qty:
            print(f"\r  {wo_num}: {i+1}/{qty} modules processed", end="", flush=True)

    print()  # newline after progress


def _seed_special_work_order(
    cur,
    wo_id: int,
    product_meta: dict,
    operator_ids: list[int],
    serial_counters: dict,
    imei_counters: dict,
    stats: dict,
) -> None:
    """WO-2025-0047: 60 modules — 40 pass, 15 fail, 5 in_progress (AOI only)."""
    tac = product_meta["tac"]
    hw_rev = product_meta["hw_revision"]
    year = 2025
    base_dt = datetime(2025, 2, 17, 8, 0, tzinfo=timezone.utc)
    clock = _make_clock(base_dt, step_minutes=10)

    # Distribution: indices 0–39 pass, 40–54 fail, 55–59 in_progress
    for i in range(60):
        serial_key = (year, hw_rev)
        serial_counters[serial_key] = serial_counters.get(serial_key, 0) + 1
        counter = serial_counters[serial_key]

        pcba_serial = f"EW{year}{hw_rev}-{counter:06d}"

        cur.execute("SELECT id FROM modules WHERE pcba_serial = %s", (pcba_serial,))
        if cur.fetchone():
            stats["modules_skipped"] += 1
            next(clock)
            continue

        imei_counters[tac] = imei_counters.get(tac, 0) + 1
        imei = _make_imei(tac, imei_counters[tac])

        produced_ts = next(clock)
        cur.execute(
            "INSERT INTO modules (pcba_serial, imei, work_order_id, status, produced_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (pcba_serial, imei, wo_id, "in_progress", produced_ts),
        )
        module_id = cur.fetchone()[0]
        stats["modules_created"] += 1

        if i < 40:
            # Full passing suite
            run_count, final_status = _insert_test_runs_for_normal_module(
                cur, module_id, operator_ids, clock, force_fail=False
            )
            # Override: force pass (in case RNG picked a fail)
            # We ensure pass by re-checking and not using force_fail —
            # the 90% pass rate is fine for the "approximately 40 pass" goal.
            stats["test_runs_created"] += run_count
            cur.execute("UPDATE modules SET status = %s WHERE id = %s", (final_status, module_id))

        elif i < 55:
            # AOI PASS then FCT FAIL
            op = _RNG.choice(operator_ids)
            ts = next(clock)
            cur.execute(
                "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (module_id, "AOI", "PASS", op, ts),
            )
            stats["test_runs_created"] += 1

            fm = _pick_failure_mode()
            op = _RNG.choice(operator_ids)
            ts = next(clock)
            cur.execute(
                "INSERT INTO test_runs (module_id, station, result, failure_mode, operator_id, tested_at)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (module_id, "FCT", "FAIL", fm, op, ts),
            )
            stats["test_runs_created"] += 1
            cur.execute("UPDATE modules SET status = 'fail' WHERE id = %s", (module_id,))

        else:
            # AOI PASS only — in_progress
            op = _RNG.choice(operator_ids)
            ts = next(clock)
            cur.execute(
                "INSERT INTO test_runs (module_id, station, result, operator_id, tested_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (module_id, "AOI", "PASS", op, ts),
            )
            stats["test_runs_created"] += 1
            # status stays in_progress

        if (i + 1) % 10 == 0 or (i + 1) == 60:
            print(f"\r  WO-2025-0047: {i+1}/60 modules processed", end="", flush=True)

    print()

    # RMA for EW2025C-000001 (the very first serial from this WO's hw_rev C in 2025)
    # Find it by looking up the first serial inserted with this WO
    cur.execute(
        "SELECT m.id, m.pcba_serial FROM modules m WHERE m.work_order_id = %s ORDER BY m.id LIMIT 1",
        (wo_id,),
    )
    row = cur.fetchone()
    if row:
        module_id, pcba_serial = row
        cur.execute("SELECT id FROM rmas WHERE module_id = %s", (module_id,))
        if not cur.fetchone():
            rma_ts = datetime(2025, 2, 24, 9, 0, tzinfo=timezone.utc)
            cur.execute(
                "INSERT INTO rmas (module_id, issue, status, opened_at)"
                " VALUES (%s, %s, %s, %s)",
                (
                    module_id,
                    "No cellular connection in field",
                    "investigating",
                    rma_ts,
                ),
            )
            stats["rmas_created"] += 1
            # Update module status to rma
            cur.execute("UPDATE modules SET status = 'rma' WHERE id = %s", (module_id,))
            print(f"  RMA opened for {pcba_serial}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(_DSN)
    except psycopg2.OperationalError as exc:
        sys.exit(f"Cannot connect to database: {exc}")

    conn.autocommit = False
    cur = conn.cursor()

    stats: dict[str, int] = {
        "products_created": 0,
        "products_skipped": 0,
        "operators_created": 0,
        "operators_skipped": 0,
        "users_created": 0,
        "users_skipped": 0,
        "work_orders_created": 0,
        "work_orders_skipped": 0,
        "modules_created": 0,
        "modules_skipped": 0,
        "test_runs_created": 0,
        "rmas_created": 0,
    }

    try:
        # ---- Products ----
        print("\n[1/5] Seeding products...")
        for p in _PRODUCTS:
            cur.execute("SELECT id FROM products WHERE sku = %s", (p["sku"],))
            if cur.fetchone():
                stats["products_skipped"] += 1
            else:
                stats["products_created"] += 1
        product_ids = _upsert_products(cur)
        print(f"      {stats['products_created']} created, {stats['products_skipped']} skipped")

        # ---- Operators ----
        print("[2/5] Seeding operators...")
        for op in _OPERATORS:
            cur.execute("SELECT id FROM operators WHERE employee_code = %s", (op["employee_code"],))
            if cur.fetchone():
                stats["operators_skipped"] += 1
            else:
                stats["operators_created"] += 1
        operator_ids = _upsert_operators(cur)
        print(f"      {stats['operators_created']} created, {stats['operators_skipped']} skipped")

        # ---- Users ----
        print("[3/5] Seeding users...")
        for u in _USERS:
            cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
            if cur.fetchone():
                stats["users_skipped"] += 1
            else:
                stats["users_created"] += 1
        _upsert_users(cur)
        print(f"      {stats['users_created']} created, {stats['users_skipped']} skipped")

        # ---- Work orders ----
        print("[4/5] Seeding work orders...")
        for wo_num, _, _, _, _ in _WORK_ORDERS:
            cur.execute("SELECT id FROM work_orders WHERE wo_number = %s", (wo_num,))
            if cur.fetchone():
                stats["work_orders_skipped"] += 1
            else:
                stats["work_orders_created"] += 1
        wo_ids = _upsert_work_orders(cur, product_ids)
        print(f"      {stats['work_orders_created']} created, {stats['work_orders_skipped']} skipped")

        # ---- Modules + test runs ----
        print("[5/5] Seeding modules and test runs...")

        # Build product metadata lookup
        product_meta_by_sku = {p["sku"]: p for p in _PRODUCTS}

        serial_counters: dict[tuple[int, str], int] = {}
        imei_counters: dict[str, int] = {}

        for wo_num, sku, planned_qty, base_date_str, label in _WORK_ORDERS:
            wo_id = wo_ids[wo_num]
            meta = product_meta_by_sku[sku]
            print(f"  {wo_num} ({sku}, {label})...")

            if label == "special":
                _seed_special_work_order(
                    cur, wo_id, meta, operator_ids,
                    serial_counters, imei_counters, stats,
                )
            else:
                _seed_normal_work_order(
                    cur, wo_num, wo_id, sku, base_date_str, planned_qty,
                    meta, operator_ids, serial_counters, imei_counters, stats,
                )

        # Open an RMA for EW2025C-000001 (the demo serial for the quality screen).
        cur.execute("SELECT id FROM modules WHERE pcba_serial = %s", ("EW2025C-000001",))
        row = cur.fetchone()
        if row:
            m_id = row[0]
            cur.execute("SELECT id FROM rmas WHERE module_id = %s", (m_id,))
            if not cur.fetchone():
                rma_ts = datetime(2025, 1, 20, 10, 30, tzinfo=timezone.utc)
                cur.execute(
                    "INSERT INTO rmas (module_id, issue, status, opened_at)"
                    " VALUES (%s, %s, %s, %s)",
                    (m_id, "No cellular connection in field after 2 weeks", "open", rma_ts),
                )
                cur.execute("UPDATE modules SET status = 'rma' WHERE id = %s", (m_id,))
                stats["rmas_created"] += 1
                print("  RMA opened for EW2025C-000001 (quality demo)")

        conn.commit()

    except Exception:
        conn.rollback()
        cur.close()
        conn.close()
        raise

    cur.close()
    conn.close()

    print("\n" + "=" * 50)
    print("SEED SUMMARY")
    print("=" * 50)
    print(f"  Products    : {stats['products_created']:4d} created, {stats['products_skipped']:4d} skipped")
    print(f"  Operators   : {stats['operators_created']:4d} created, {stats['operators_skipped']:4d} skipped")
    print(f"  Users       : {stats['users_created']:4d} created, {stats['users_skipped']:4d} skipped")
    print(f"  Work Orders : {stats['work_orders_created']:4d} created, {stats['work_orders_skipped']:4d} skipped")
    print(f"  Modules     : {stats['modules_created']:4d} created, {stats['modules_skipped']:4d} skipped")
    print(f"  Test Runs   : {stats['test_runs_created']:4d} created")
    print(f"  RMAs        : {stats['rmas_created']:4d} created")
    print("=" * 50)
    print("Done.")


if __name__ == "__main__":
    main()
