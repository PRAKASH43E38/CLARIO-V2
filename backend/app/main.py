from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from backend.app.api.routes import auth, health, onboarding, learner, sessions, learning, dashboard, roadmap, cala, research, orchestration


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    run_migrations(db_path)
    yield


app = FastAPI(
    title="CLARIO API",
    description="Adaptive Multi-Agent AI Learning Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
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