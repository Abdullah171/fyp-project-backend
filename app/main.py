# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import search, stats, settings as settings_router
from .routers import media  # NEW

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NetSentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(media.router, prefix="/api")  # NEW


@app.get("/health")
def health():
    return {"status": "ok"}
