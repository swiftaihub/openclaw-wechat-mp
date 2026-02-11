from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.wechat import router as wechat_router

app = FastAPI(title="Ollama WeChat MP Gateway")

app.include_router(wechat_router, prefix="/wechat")

@app.get("/health")
def health():
    return {"ok": True}
