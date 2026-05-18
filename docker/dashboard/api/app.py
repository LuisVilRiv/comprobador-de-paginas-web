"""app.py — FastAPI app entrypoint for dashboard API."""

# Ensure project root (containing `shared/`) is on sys.path so imports work
import sys
from pathlib import Path

root = Path(__file__).resolve()
for _ in range(8):
    root = root.parent
    if (root / "shared").is_dir():
        sys.path.insert(0, str(root))
        break

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    clients_router,
    health_router,
    runs_router,
    settings_router,
    summary_router,
    websites_router,
)

app = FastAPI(
    title="Web Auditor Dashboard API",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(clients_router)
app.include_router(websites_router)
app.include_router(summary_router)
app.include_router(runs_router)
app.include_router(settings_router)
