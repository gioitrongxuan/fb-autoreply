import os
import asyncio
import logging
from google import genai
from google.genai import types
from style_engine import build_system_prompt, get_token_limits
import deepseek_client

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
_system_instruction = build_system_prompt()

chat_sessions: dict = {}
_session_turn_counts: dict = {}  # sender_id -> number of turns used


def reload_model():
    global _system_instruction, chat_sessions, _session_turn_counts
    from style_engine import load_style_profile
    load_style_profile.cache_clear()
    _system_instruction = build_system_prompt()
    chat_sessions.clear()
    _session_turn_counts.clear()
    deepseek_client.reload_model()


def _new_gemini_session(max_output_tokens: int):
    return _client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=_system_instruction,
            max_output_tokens=max_output_tokens,
        ),
    )


async def _gemini_reply(sender_id: str, message: str) -> str:
    limits = get_token_limits()
    max_tokens = limits["max_output_tokens"]
    max_turns = limits["max_history_turns"]

    turns = _session_turn_counts.get(sender_id, 0)
    if sender_id not in chat_sessions or turns >= max_turns:
        chat_sessions[sender_id] = _new_gemini_session(max_tokens)
        _session_turn_counts[sender_id] = 0

    session = chat_sessions[sender_id]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, session.send_message, message)
    _session_turn_counts[sender_id] = _session_turn_counts.get(sender_id, 0) + 1
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
