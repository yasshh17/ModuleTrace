from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.schemas.schemas import ModuleDetailResponse, ModuleListResponse
from app.services import module_service

router = APIRouter()


@router.get(
    "",
    response_model=ModuleListResponse,
    summary="List modules",
    dependencies=[Depends(require_role("engineer", "admin"))],
)
async def list_modules(
    db: AsyncSession = Depends(get_db),
    status: Annotated[str | None, Query(description="Filter by module status")] = None,
    product_sku: Annotated[str | None, Query(description="Filter by product SKU")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ModuleListResponse:
    return await module_service.list_modules(
        db,
        status=status,
        product_sku=product_sku,
        page=page,
        size=size,
    )


@router.get(
    "/{identifier}",
    response_model=ModuleDetailResponse,
    summary="Get module detail",
    dependencies=[Depends(get_current_user)],
)
async def get_module_detail(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> ModuleDetailResponse:
    """Look up a module by pcba_serial or IMEI and return its full test history."""
    return await module_service.get_module_detail(db, identifier)
