from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, models, projects, resources
from app.db.database import init_db


app = FastAPI(title="臆想创作 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "name": "臆想创作"}


app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
