from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import uvicorn
from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.migrations import run_migrations
from backend.app.models import user, learner, curriculum, session, mind_profile, session_inputs
from backend.app.models import cala_plan, research_package
from backend.app.models import orchestration
from backend.app.models import teaching_result
from backend.app.models import thinking_result
from backend.app.models import practical_result
from backend.app.models import quiz_result
from backend.app.models import elara_evaluation
from backend.app.models import session_concept_performance, adaptive_decision
from backend.app.api.routes import auth, health, onboarding, learner, sessions, learning, dashboard, roadmap, cala, research, orchestration, submissions, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    if (
        settings.ENVIRONMENT.lower() == "production"
        and engine.dialect.name != "postgresql"
    ):
        raise RuntimeError("Production requires a PostgreSQL DATABASE_URL.")
    if engine.dialect.name == "sqlite":
        run_migrations(engine.url.database or "")
    elif engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    else:
        raise RuntimeError(
            f"Database migrations are not supported for dialect '{engine.dialect.name}'."
        )
    yield


app = FastAPI(
    title="CLARIO API",
    description="Adaptive Multi-Agent AI Learning Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(learner.router)
app.include_router(sessions.router)
app.include_router(learning.router)
app.include_router(dashboard.router)
app.include_router(roadmap.router)
app.include_router(cala.router)
app.include_router(research.router)
app.include_router(orchestration.router)
app.include_router(submissions.router)
app.include_router(reports.router)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.PORT,
    )