import os
from fastapi import FastAPI
from app.wechat import router as wechat_router

app = FastAPI(title="OpenClaw WeChat MP Gateway")

app.include_router(wechat_router, prefix="/wechat")

@app.get("/health")
def health():
    return {"ok": True}
