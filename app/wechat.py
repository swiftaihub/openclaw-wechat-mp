import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from wechatpy import create_reply, parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import check_signature

from app.llm_core import generate_reply
from app.wechat_token import get_access_token

router = APIRouter()
logger = logging.getLogger(__name__)
DEFAULT_REPLY_TIMEOUT_SECONDS = float(os.getenv("OPENCLAW_REPLY_TIMEOUT_SECONDS", "4.5"))


def _validate_wechat_signature(signature: str, timestamp: str, nonce: str) -> None:
    token = os.getenv("WECHAT_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=500, detail="WECHAT_TOKEN not set")

    try:
        check_signature(token, signature, timestamp, nonce)
    except InvalidSignatureException as exc:
        raise HTTPException(status_code=403, detail="Invalid signature") from exc


@router.post("/menu")
async def create_menu():
    token = await get_access_token()

    menu = {
        "button": [
            {"type": "click", "name": "帮助", "key": "HELP"},
            {"type": "click", "name": "设置", "key": "SETTINGS"},
        ]
    }

    url = "https://api.weixin.qq.com/cgi-bin/menu/create"
    params = {"access_token": token}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, params=params, json=menu)
        response.raise_for_status()
        data = response.json()

    return data


@router.get("")
async def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    _validate_wechat_signature(signature, timestamp, nonce)
    return Response(content=echostr, media_type="text/plain")


@router.post("")
async def wechat_message(request: Request, signature: str, timestamp: str, nonce: str):
    _validate_wechat_signature(signature, timestamp, nonce)

    body = await request.body()
    msg = parse_message(body)

    if msg.type != "text":
        return Response(content="success", media_type="text/plain")

    user_text = msg.content.strip()
    from_user = msg.source

    try:
        reply_text = await asyncio.wait_for(
            generate_reply(user_id=from_user, text=user_text),
            timeout=DEFAULT_REPLY_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("OpenClaw reply timeout")
        reply_text = "我在处理中，稍后再试一次会更稳。"
    except Exception as exc:
        logger.warning("Failed to generate OpenClaw reply: %s", exc)
        reply_text = "服务暂时繁忙，请稍后再试。"

    reply = create_reply(reply_text, msg)
    return Response(content=reply.render(), media_type="application/xml")
