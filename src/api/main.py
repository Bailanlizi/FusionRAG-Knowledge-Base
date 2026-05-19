"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import chunks, conversations, documents, health, kb

app = FastAPI(
    title="FusionRAG Knowledge Base API",
    version="0.2.0",
    description="Web API for chat and document management",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(kb.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(chunks.router, prefix=API_PREFIX)
app.include_router(conversations.router, prefix=API_PREFIX)
