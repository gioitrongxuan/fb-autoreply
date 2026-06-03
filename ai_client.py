import os
import asyncio
from google import genai
from google.genai import types
from style_engine import build_system_prompt

SHOP_CONTEXT = ""

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
_system_instruction = build_system_prompt(SHOP_CONTEXT)

chat_sessions: dict = {}


async def generate_reply(sender_id: str, message: str) -> str:
    if sender_id not in chat_sessions:
        chat_sessions[sender_id] = _client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction,
            ),
        )

    session = chat_sessions[sender_id]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, session.send_message, message)
    return response.text
