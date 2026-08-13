from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.api.routes import router as energy_router
from app.api.maintenance_routes import router as maintenance_router
from app.services import data_service, maintenance_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Auto-ingest on first boot so the dashboard has data immediately in dev.
    db = SessionLocal()
    try:
        if not data_service.has_data(db, "BLD-HQ-01"):
            data_service.ingest_from_csv(db)
        if not maintenance_service.has_data(db, "BLD-HQ-01"):
            try:
                maintenance_service.ingest_fleet(db)
            except FileNotFoundError:
                pass  # dataset not built yet; POST /api/maintenance/ingest once it is
    finally:
        db.close()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(energy_router, prefix=settings.API_V1_PREFIX)
app.include_router(maintenance_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"service": settings.PROJECT_NAME, "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
