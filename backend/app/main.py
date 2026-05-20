from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, modules, test_runs, analytics, rma
from app.core.logging import setup_logging

setup_logging()

_tags_metadata = [
    {
        "name": "auth",
        "description": "Login and current-user profile.",
    },
    {
        "name": "modules",
        "description": "Look up and list tracked hardware modules.",
    },
    {
        "name": "test-runs",
        "description": "Record test station results and drive module status transitions.",
    },
    {
        "name": "analytics",
        "description": "First-pass yield and failure-mode Pareto charts.",
    },
    {
        "name": "rma",
        "description": "Return Merchandise Authorization lifecycle management.",
    },
    {
        "name": "ops",
        "description": "Health and readiness probes.",
    },
]

app = FastAPI(
    title="ModuleTrace API",
    version="0.1.0",
    description=(
        "Manufacturing quality traceability platform. "
        "Tracks hardware modules through production, test, and field lifecycle stages."
    ),
    openapi_tags=_tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["auth"])
app.include_router(modules.router,    prefix="/api/v1/modules",    tags=["modules"])
app.include_router(test_runs.router,  prefix="/api/v1/test-runs",  tags=["test-runs"])
app.include_router(analytics.router,  prefix="/api/v1/analytics",  tags=["analytics"])
app.include_router(rma.router,        prefix="/api/v1/rma",        tags=["rma"])


@app.get("/healthz", tags=["ops"], summary="Health check")
async def health_check() -> dict:
    return {"status": "ok"}
