import os
import httpx
from style_engine import build_system_prompt

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

_system_instruction = build_system_prompt()
_chat_histories: dict = {}


def reload_model():
    global _system_instruction, _chat_histories
    from style_engine import load_style_profile
    load_style_profile.cache_clear()
    _system_instruction = build_system_prompt()
    _chat_histories.clear()


async def generate_reply(sender_id: str, message: str) -> str:
    if sender_id not in _chat_histories:
        _chat_histories[sender_id] = []

    history = _chat_histories[sender_id]
    history.append({"role": "user", "content": message})

    messages = [{"role": "system", "content": _system_instruction}] + history[-20:]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={"model": "deepseek-chat", "messages": messages},
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]

    history.append({"role": "assistant", "content": reply})
    return reply
