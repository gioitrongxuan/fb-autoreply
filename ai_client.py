import os
import asyncio
import google.generativeai as genai
from style_engine import build_system_prompt

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

SHOP_CONTEXT = ""

_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=build_system_prompt(SHOP_CONTEXT),
)

chat_sessions: dict = {}


async def generate_reply(sender_id: str, message: str) -> str:
    if sender_id not in chat_sessions:
        chat_sessions[sender_id] = _model.start_chat(history=[])

    session = chat_sessions[sender_id]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, session.send_message, message)
    return response.text
