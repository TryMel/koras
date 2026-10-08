import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import init_db, get_db

# Import all routers
from app.api.auth.routes import router as auth_router
from app.api.users.routes import router as users_router
from app.api.devices.routes import router as devices_router
from app.api.conversations.routes import router as conversations_router
from app.api.agent.routes import router as agent_router
from app.api.tools.routes import router as tools_router
from app.api.actions.routes import router as actions_router
from app.api.admin.routes import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"KORAS {settings.VERSION} starting in {settings.ENVIRONMENT} mode")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("KORAS shutting down")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "KORAS — Agentique Mobile Core API. "
        "Intention → Compréhension → Planification → Politique → Autorisation → Action → Vérification → Audit"
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://admin.koras.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request correlation ID middleware (Section 44)
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    start_time = time.time()
    response: Response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"Unhandled exception [{correlation_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "SYSTEM_ERROR",
            "message": "Une erreur interne s'est produite. Veuillez réessayer.",
            "correlation_id": correlation_id,
            "retryable": True
        }
    )

# Register all routers under /api/v1
prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=prefix)
app.include_router(users_router, prefix=prefix)
app.include_router(devices_router, prefix=prefix)
app.include_router(conversations_router, prefix=prefix)
app.include_router(agent_router, prefix=prefix)
app.include_router(tools_router, prefix=prefix)
app.include_router(actions_router, prefix=prefix)
app.include_router(admin_router, prefix=prefix)

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "KORAS Agentic Core",
        "version": settings.VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health", tags=["Health"])
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness check failed: database unavailable", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable", "version": settings.VERSION},
        )
    return {"status": "ok", "database": "ok", "version": settings.VERSION}

@app.get("/health/live", tags=["Health"])
async def liveness():
    return {"status": "ok", "version": settings.VERSION}
