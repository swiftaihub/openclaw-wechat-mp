import os
from fastapi import APIRouter, Request, Response, HTTPException
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from app.wechat_token import get_access_token
import httpx

from app.openclaw_core import generate_reply

router = APIRouter()

@router.post("/menu")
async def create_menu():
    token = await get_access_token()

    # 你可以按需改菜单
    menu = {
        "button": [
            {"type": "click", "name": "帮助", "key": "HELP"},
            {"type": "click", "name": "设置", "key": "SETTINGS"},
        ]
    }

    url = "https://api.weixin.qq.com/cgi-bin/menu/create"
    params = {"access_token": token}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, params=params, json=menu)
        r.raise_for_status()
        data = r.json()

    # errcode=0 代表成功
    return data

@router.get("")
async def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    """
    微信服务器会发 GET 请求校验 URL：
    校验 signature 成功后，必须原样返回 echostr 才算接入成功。:contentReference[oaicite:3]{index=3}
    """
    if not WECHAT_TOKEN:
        raise HTTPException(status_code=500, detail="WECHAT_TOKEN not set")

    if check_signature(WECHAT_TOKEN, signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid signature")

@router.post("")
async def wechat_message(request: Request, signature: str, timestamp: str, nonce: str):
    """
    明文模式：POST body 是 XML。
    这里先实现：收到文本 -> 交给 OpenClaw -> 回复文本
    """
    if not check_signature(WECHAT_TOKEN, signature, timestamp, nonce):
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.body()
    msg = parse_message(body)

    # 只处理文本消息，其他类型先简单返回 "success"（微信要求快速响应）
    if msg.type != "text":
        return Response(content="success", media_type="text/plain")

    user_text = msg.content.strip()
    from_user = msg.source  # 用户 openid
    to_user = msg.target    # 公众号原始 id

    reply_text = await generate_reply(user_id=from_user, text=user_text)

    reply = create_reply(reply_text, msg)
    return Response(content=reply.render(), media_type="application/xml")
