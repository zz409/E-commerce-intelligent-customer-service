from fastapi import FastAPI

from app.api.routes.conversations import router

app=FastAPI(title="电商智能客服系统")

app.include_router(router,prefix="/api")