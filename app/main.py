from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables on startup (swap for Alembic in prod)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Outbound Picking & Dispatch System",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}
