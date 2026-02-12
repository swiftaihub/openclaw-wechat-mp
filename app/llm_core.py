import os
from functools import lru_cache

from app.guardrail import GuardrailEngine
from app.ollama_client import ollama_chat
from app.prompt_runtime import get_prompt_runtime

PROMPT_PROFILE = os.getenv("PROMPT_PROFILE", "wechat")


@lru_cache(maxsize=1)
def _get_guardrail_engine() -> GuardrailEngine:
    runtime = get_prompt_runtime()
    return GuardrailEngine(runtime.guardrail_settings)


async def generate_reply(user_id: str, text: str) -> str:
    runtime = get_prompt_runtime()
    guardrail = _get_guardrail_engine()

    input_result = guardrail.check_input(text)
    if input_result.blocked:
        return input_result.text

    system_prompt = runtime.system_prompt(PROMPT_PROFILE)
    user_prompt = runtime.render_user_prompt(
        profile=PROMPT_PROFILE,
        user_text=input_result.text,
        user_id=user_id,
        context={"channel": "wechat_mp"},
    )

    raw_output = await ollama_chat(system_prompt=system_prompt, user_prompt=user_prompt)
    return guardrail.sanitize_output(raw_output)
