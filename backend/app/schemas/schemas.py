"""
Pydantic v2 schemas for ModuleTrace API.

Naming convention:
  *Request / *Create / *Update  — inbound  (client → API)
  *Response / *ListItem          — outbound (API → client)

All response schemas carry ConfigDict(from_attributes=True) so they accept
SQLAlchemy ORM objects directly (e.g. ProductResponse.model_validate(orm_obj)).

Datetime fields use the IsoDatetime annotated type, which serialises to an
ISO 8601 string in both .model_dump() and .model_dump_json() — regardless of
whether the datetime is timezone-aware or naive.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

# ---------------------------------------------------------------------------
# Shared annotated types
# ---------------------------------------------------------------------------

# Always serialise datetime as an ISO 8601 string (both dict and JSON mode).
IsoDatetime = Annotated[
    datetime,
    PlainSerializer(lambda dt: dt.isoformat(), return_type=str, when_used="always"),
]

# Float rounded to 2 decimal places on validation.
Pct = Annotated[float, AfterValidator(lambda v: round(v, 2))]

# Constrained literals — drive both runtime validation and OpenAPI enum values.
StationType = Literal["FCT", "AOI", "RF_TX", "RF_RX", "GPS", "FLASH"]
ResultType = Literal["PASS", "FAIL", "RETEST"]
ModuleStatusType = Literal["in_progress", "pass", "fail", "scrapped", "shipped", "rma"]
WOStatusType = Literal["open", "in_progress", "closed"]
RMAStatusType = Literal["open", "investigating", "closed"]
UserRoleType = Literal["operator", "engineer", "quality", "admin"]


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(..., examples=["jane@acme.com"])
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRoleType


# ---------------------------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------------------------

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    hw_rev: str
    fw_version: str


# Internal brief used inside WorkOrderResponse / WorkOrderBrief.
# Not exposed directly in API routes.
class _ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    name: str


# ---------------------------------------------------------------------------
# WORK ORDERS
# ---------------------------------------------------------------------------

class WorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wo_number: str
    status: WOStatusType
    qty_planned: int
    opened_at: IsoDatetime
    product: ProductResponse  # ORM relationship: WorkOrder.product → Product


# Internal brief nested inside ModuleListItem / ModuleDetailResponse.
class _WorkOrderBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wo_number: str
    product: _ProductBrief  # ORM: WorkOrder.product → Product


# ---------------------------------------------------------------------------
# OPERATORS
# ---------------------------------------------------------------------------

class OperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    name: str


# ---------------------------------------------------------------------------
# MODULES
# ---------------------------------------------------------------------------

class ModuleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pcba_serial: str
    imei: str | None
    status: ModuleStatusType
    produced_at: IsoDatetime
    work_order: _WorkOrderBrief  # ORM: Module.work_order → WorkOrder (→ Product)


class TestRunSummary(BaseModel):
    """
    Flat representation of a TestRun row.

    operator_name is extracted from the TestRun.operator relationship at
    validation time so the caller never exposes a nested Operator object.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    station: StationType
    result: ResultType
    failure_mode: str | None
    measurements: dict | None
    tested_at: IsoDatetime
    operator_name: str | None

    @model_validator(mode="before")
    @classmethod
    def _flatten_operator(cls, data: object) -> object:
        # When data is an ORM TestRun object, pull operator.name → operator_name.
        # When data is already a plain dict (e.g. from tests), pass through unchanged.
        if not isinstance(data, dict):
            op = getattr(data, "operator", None)
            return {
                "id": data.id,
                "station": data.station,
                "result": data.result,
                "failure_mode": data.failure_mode,
                "measurements": data.measurements,
                "tested_at": data.tested_at,
                "operator_name": op.name if op is not None else None,
            }
        return data


class ModuleDetailResponse(BaseModel):
    """
    Full module detail including test history.

    test_history is aliased from the ORM relationship name test_runs so the
    API field name remains stable even if the ORM attribute is renamed.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pcba_serial: str
    imei: str | None
    status: ModuleStatusType
    produced_at: IsoDatetime
    work_order: _WorkOrderBrief
    # alias="test_runs" — Pydantic reads Module.test_runs from the ORM object
    # and validates each element through TestRunSummary (including its
    # _flatten_operator validator).
    test_history: list[TestRunSummary] = Field(default_factory=list, validation_alias="test_runs")


class ModuleListResponse(BaseModel):
    items: list[ModuleListItem]
    total: int
    page: int
    size: int


# ---------------------------------------------------------------------------
# TEST RUNS
# ---------------------------------------------------------------------------

class TestRunCreate(BaseModel):
    module_serial: str = Field(
        ...,
        description="pcba_serial of the module under test (e.g. 'EW2025B-004821')",
    )
    station: StationType
    result: ResultType
    failure_mode: str | None = None
    measurements: dict | None = None
    operator_id: int | None = None


class TestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station: StationType
    result: ResultType
    failure_mode: str | None
    measurements: dict | None
    tested_at: IsoDatetime


# ---------------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------------

class YieldByProduct(BaseModel):
    sku: str
    name: str
    total_tested: int
    total_passed: int
    fpy_pct: Pct  # first-pass yield %, rounded to 2 dp


class YieldResponse(BaseModel):
    items: list[YieldByProduct]
    from_date: str  # ISO 8601 date string, e.g. '2025-01-01'
    to_date: str


class FailureModeCount(BaseModel):
    failure_mode: str
    count: int
    pct: Pct  # share of total failures, rounded to 2 dp


class ParetoResponse(BaseModel):
    items: list[FailureModeCount]  # sorted descending by count
    total_failures: int


# ---------------------------------------------------------------------------
# RMA
# ---------------------------------------------------------------------------

class RMACreate(BaseModel):
    module_serial: str = Field(
        ...,
        description="pcba_serial of the module being returned (e.g. 'EW2025B-004821')",
    )
    issue: str = Field(..., min_length=5)


class RMAUpdate(BaseModel):
    root_cause: str | None = None
    status: RMAStatusType | None = None


class RMAResponse(BaseModel):
    """
    Flat RMA response.

    module_serial is extracted from the RMA.module relationship at validation
    time; the caller sees a plain string, not a nested Module object.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    module_serial: str
    issue: str
    root_cause: str | None
    status: RMAStatusType
    opened_at: IsoDatetime

    @model_validator(mode="before")
    @classmethod
    def _flatten_module_serial(cls, data: object) -> object:
        if not isinstance(data, dict):
            return {
                "id": data.id,
                "module_serial": data.module.pcba_serial,
                "issue": data.issue,
                "root_cause": data.root_cause,
                "status": data.status,
                "opened_at": data.opened_at,
            }
        return data


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRoleType
    # hashed_password is intentionally absent from this schema.
