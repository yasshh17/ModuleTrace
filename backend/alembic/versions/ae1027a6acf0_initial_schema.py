"""initial schema

Revision ID: ae1027a6acf0
Revises:
Create Date: 2025-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ae1027a6acf0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # products                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("hw_rev", sa.Text(), nullable=False, server_default="A"),
        sa.Column("fw_version", sa.Text(), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("uq_products_sku", "products", ["sku"], unique=True)

    # ------------------------------------------------------------------ #
    # operators                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "operators",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("employee_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("uq_operators_employee_code", "operators", ["employee_code"], unique=True)

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="operator"),
    )
    op.create_index("uq_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------ #
    # work_orders  (FK → products)                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "work_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wo_number", sa.Text(), nullable=False),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("products.id", name="fk_work_orders_product_id"),
            nullable=False,
        ),
        sa.Column("qty_planned", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("uq_work_orders_wo_number", "work_orders", ["wo_number"], unique=True)
    op.create_index("ix_work_orders_product_id", "work_orders", ["product_id"])

    # ------------------------------------------------------------------ #
    # modules  (FK → work_orders)                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "modules",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pcba_serial", sa.Text(), nullable=False),
        sa.Column("imei", sa.Text(), nullable=True),
        sa.Column(
            "work_order_id",
            sa.BigInteger(),
            sa.ForeignKey("work_orders.id", name="fk_modules_work_order_id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="in_progress"),
        sa.Column(
            "produced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("uq_modules_pcba_serial", "modules", ["pcba_serial"], unique=True)
    op.create_index("uq_modules_imei", "modules", ["imei"], unique=True)
    op.create_index("ix_modules_work_order_id", "modules", ["work_order_id"])
    op.create_index(
        "ix_modules_status_produced_at",
        "modules",
        ["status", sa.text("produced_at DESC")],
    )
    op.create_index(
        "ix_modules_imei_partial",
        "modules",
        ["imei"],
        postgresql_where=sa.text("imei IS NOT NULL"),
    )

    # ------------------------------------------------------------------ #
    # test_runs  (FK → modules, operators)                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "test_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "module_id",
            sa.BigInteger(),
            sa.ForeignKey("modules.id", name="fk_test_runs_module_id"),
            nullable=False,
        ),
        sa.Column(
            "operator_id",
            sa.BigInteger(),
            sa.ForeignKey("operators.id", name="fk_test_runs_operator_id"),
            nullable=True,
        ),
        sa.Column("station", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("failure_mode", sa.Text(), nullable=True),
        sa.Column("measurements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "tested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_test_runs_module_id", "test_runs", ["module_id"])
    op.create_index(
        "ix_test_runs_station_result_tested_at",
        "test_runs",
        ["station", "result", sa.text("tested_at DESC")],
    )
    op.create_index(
        "ix_test_runs_failure_mode_partial",
        "test_runs",
        ["failure_mode"],
        postgresql_where=sa.text("failure_mode IS NOT NULL"),
    )

    # ------------------------------------------------------------------ #
    # rmas  (FK → modules, unique on module_id → one RMA per module)     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "rmas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "module_id",
            sa.BigInteger(),
            sa.ForeignKey("modules.id", name="fk_rmas_module_id"),
            nullable=False,
        ),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("uq_rmas_module_id", "rmas", ["module_id"], unique=True)


def downgrade() -> None:
    op.drop_table("rmas")

    op.drop_index("ix_test_runs_failure_mode_partial", table_name="test_runs")
    op.drop_index("ix_test_runs_station_result_tested_at", table_name="test_runs")
    op.drop_index("ix_test_runs_module_id", table_name="test_runs")
    op.drop_table("test_runs")

    op.drop_index("ix_modules_imei_partial", table_name="modules")
    op.drop_index("ix_modules_status_produced_at", table_name="modules")
    op.drop_index("ix_modules_work_order_id", table_name="modules")
    op.drop_index("uq_modules_imei", table_name="modules")
    op.drop_index("uq_modules_pcba_serial", table_name="modules")
    op.drop_table("modules")

    op.drop_index("ix_work_orders_product_id", table_name="work_orders")
    op.drop_index("uq_work_orders_wo_number", table_name="work_orders")
    op.drop_table("work_orders")

    op.drop_index("uq_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("uq_operators_employee_code", table_name="operators")
    op.drop_table("operators")

    op.drop_index("uq_products_sku", table_name="products")
    op.drop_table("products")
