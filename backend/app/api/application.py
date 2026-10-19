from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.conversations import router as conversations_router

from backend.app.api.routes.rag import router as knowledge_router

app = FastAPI()

app.include_router(conversations_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")