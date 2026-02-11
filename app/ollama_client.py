# app/ollama_client.py
import os
from typing import Optional, Dict, Any, List
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:32b-instruct-q4_K_M")


def build_system_prompt(profile: str = "default") -> str:
    """
    系统提示词：尽量稳定、少变动，便于复用和评估效果。
    profile 可以让你未来扩展不同“人格/模式”。
    """
    if profile == "default":
        return (
            "你是 OpenClaw，一个高效、可靠、注重安全的个人助手。\n"
            "要求：\n"
            "1) 回答要简洁、可执行。\n"
            "2) 信息不足时，先给最可能的默认方案，再列出最多2个需要澄清的问题。\n"
            "3) 不要编造事实；不确定就说明不确定。\n"
        )
    if profile == "wechat":
        return (
            "你是 OpenClaw，在微信公众号中回复用户。\n"
            "要求：\n"
            "1) 回复要短，适合手机阅读（尽量 3-8 行）。\n"
            "2) 用中文回答，除非用户明确要求英文。\n"
            "3) 给步骤/清单优先。\n"
        )
    # fallback
    return "你是一个乐于助人的助手。"


def build_user_prompt(
    user_text: str,
    *,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    instructions: Optional[str] = None,
) -> str:
    """
    用户提示词：把用户原话放在最醒目的位置，其余上下文用“结构化块”包起来。
    这样模型更稳定，也方便你后续加记忆/RAG/工具状态。
    """
    context = context or {}

    header_lines = []
    if user_id:
        header_lines.append(f"UserID: {user_id}")
    for k, v in context.items():
        header_lines.append(f"{k}: {v}")

    header = "\n".join(header_lines).strip()
    extra = (instructions or "").strip()

    parts: List[str] = []
    if header:
        parts.append("【上下文】\n" + header)
    if extra:
        parts.append("【额外要求】\n" + extra)
    parts.append("【用户消息】\n" + user_text.strip())

    return "\n\n".join(parts).strip()


async def ollama_chat(
    *,
    user_text: str,
    system_profile: str = "wechat",
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    instructions: Optional[str] = None,
) -> str:
    """
    最终调用：内部组装 system/user，然后按你给的 payload 发给 Ollama。
    """
    system = build_system_prompt(system_profile)
    user = build_user_prompt(
        user_text,
        user_id=user_id,
        context=context,
        instructions=instructions,
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }

    url = f"{OLLAMA_BASE_URL}/api/chat"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    return (data.get("message") or {}).get("content", "").strip() or "（我刚刚没生成出有效回复，再试一次？）"
