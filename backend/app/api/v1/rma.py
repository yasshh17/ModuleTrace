from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.schemas.schemas import RMACreate, RMAResponse, RMAUpdate
from app.services import rma_service

router = APIRouter()


@router.post(
    "/",
    response_model=RMAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open an RMA",
    dependencies=[Depends(require_role("quality", "admin"))],
)
async def create_rma(
    body: RMACreate,
    db: AsyncSession = Depends(get_db),
) -> RMAResponse:
    """
    Open a Return Merchandise Authorization for the given module.

    - **404** if the module (pcba_serial) does not exist.
    - **409** if the module already has an open RMA.
    """
    return await rma_service.create_rma(db, body)


@router.get(
    "/{module_serial}",
    response_model=RMAResponse,
    summary="Get RMA by module serial",
    dependencies=[Depends(require_role("quality", "engineer", "admin"))],
)
async def get_rma(
    module_serial: str,
    db: AsyncSession = Depends(get_db),
) -> RMAResponse:
    """Return the RMA record associated with *module_serial*."""
    return await rma_service.get_rma_by_module(db, module_serial)


@router.patch(
    "/{module_serial}",
    response_model=RMAResponse,
    summary="Update an RMA",
    dependencies=[Depends(require_role("quality", "admin"))],
)
async def update_rma(
    module_serial: str,
    body: RMAUpdate,
    db: AsyncSession = Depends(get_db),
) -> RMAResponse:
    """
    Partially update an RMA.  Only fields explicitly included in the request body
    are written; omitted or null fields are left unchanged.
    """
    return await rma_service.update_rma(db, module_serial, body)
