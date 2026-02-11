from app.ollama_client import ollama_chat


SYSTEM_PROMPT = """你是聪明的AI，一个高效、可靠的个人助手。
回答要简洁、可执行；如果信息不足，先给出最可能的默认方案，再列出需要用户补充的1-2个问题。"""

async def generate_reply(user_id: str, text: str) -> str:
    return await ollama_chat(
        user_text=text,
        system_profile="wechat",
        user_id=user_id,
        context={
            "channel": "wechat_mp",
        },
        instructions=SYSTEM_PROMPT,
    )