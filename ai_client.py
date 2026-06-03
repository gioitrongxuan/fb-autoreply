import os
import asyncio
import logging
from google import genai
from google.genai import types
from style_engine import build_system_prompt
import deepseek_client

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
_system_instruction = build_system_prompt()

chat_sessions: dict = {}


def reload_model():
    global _system_instruction, chat_sessions
    from style_engine import load_style_profile
    load_style_profile.cache_clear()
    _system_instruction = build_system_prompt()
    chat_sessions.clear()
    deepseek_client.reload_model()


async def _gemini_reply(sender_id: str, message: str) -> str:
    if sender_id not in chat_sessions:
        chat_sessions[sender_id] = _client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction,
            ),
        )
    session = chat_sessions[sender_id]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, session.send_message, message)
    return response.text


async def generate_reply(sender_id: str, message: str) -> str:
    try:
        return await _gemini_reply(sender_id, message)
    except Exception as e:
        err = str(e)
        if any(code in err for code in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
            logging.warning(f"Gemini unavailable ({err[:60]}...), switching to DeepSeek")
            return await deepseek_client.generate_reply(sender_id, message)
        raise
