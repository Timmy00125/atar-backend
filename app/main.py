from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints import verification
from app.core.database import engine, Base

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include routers
app.include_router(
    verification.router,
    prefix=f"{settings.API_V1_STR}/verification",
    tags=["verification"],
)


@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    # Create tables on startup (for development simplicity)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown():
    pass
