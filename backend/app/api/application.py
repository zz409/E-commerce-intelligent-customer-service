from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.conversations import router as conversations_router

from app.api.routes.rag import router as rag_router

app = FastAPI()

app.include_router(conversations_router, prefix="/api")
app.include_router(rag_router, prefix="/api")