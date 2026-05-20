from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Use native JSONB on PostgreSQL; fall back to JSON (TEXT) on SQLite for tests.
JSONB = _PG_JSONB().with_variant(JSON(), "sqlite")

# SQLite only auto-increments INTEGER PRIMARY KEY, not BIGINT PRIMARY KEY.
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    hw_rev: Mapped[str] = mapped_column(Text, nullable=False, server_default="A")
    fw_version: Mapped[str] = mapped_column(Text, nullable=False, server_default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku!r} hw_rev={self.hw_rev!r}>"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    wo_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    product_id: Mapped[int] = mapped_column(_BigInt, ForeignKey("products.id"), nullable=False)
    qty_planned: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="work_orders")
    modules: Mapped[list["Module"]] = relationship(back_populates="work_order")

    def __repr__(self) -> str:
        return f"<WorkOrder id={self.id} wo_number={self.wo_number!r} status={self.status!r}>"


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="operator")

    def __repr__(self) -> str:
        return f"<Operator id={self.id} employee_code={self.employee_code!r} name={self.name!r}>"


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        Index("ix_modules_work_order_id", "work_order_id"),
        Index("ix_modules_status_produced_at", "status", "produced_at"),
        Index(
            "ix_modules_imei_partial",
            "imei",
            postgresql_where="imei IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    pcba_serial: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    imei: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    work_order_id: Mapped[int] = mapped_column(
        _BigInt, ForeignKey("work_orders.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="in_progress")
    produced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    work_order: Mapped["WorkOrder"] = relationship(back_populates="modules")
    test_runs: Mapped[list["TestRun"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )
    rma: Mapped["RMA | None"] = relationship(back_populates="module", uselist=False)

    def __repr__(self) -> str:
        return f"<Module id={self.id} pcba_serial={self.pcba_serial!r} status={self.status!r}>"


class TestRun(Base):
    __tablename__ = "test_runs"
    __table_args__ = (
        Index("ix_test_runs_module_id", "module_id"),
        Index("ix_test_runs_station_result_tested_at", "station", "result", "tested_at"),
        Index(
            "ix_test_runs_failure_mode_partial",
            "failure_mode",
            postgresql_where="failure_mode IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        _BigInt, ForeignKey("modules.id"), nullable=False
    )
    operator_id: Mapped[int | None] = mapped_column(
        _BigInt, ForeignKey("operators.id"), nullable=True
    )
    station: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    failure_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    module: Mapped["Module"] = relationship(back_populates="test_runs")
    operator: Mapped["Operator | None"] = relationship(back_populates="test_runs")

    def __repr__(self) -> str:
        return (
            f"<TestRun id={self.id} module_id={self.module_id} "
            f"station={self.station!r} result={self.result!r}>"
        )


class RMA(Base):
    __tablename__ = "rmas"

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        _BigInt, ForeignKey("modules.id"), unique=True, nullable=False
    )
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    module: Mapped["Module"] = relationship(back_populates="rma")

    def __repr__(self) -> str:
        return f"<RMA id={self.id} module_id={self.module_id} status={self.status!r}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(_BigInt, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="operator")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
