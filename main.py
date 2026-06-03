import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fb_client import send_message
from ai_client import generate_reply

app = FastAPI()

VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN", "")


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    if body.get("object") != "page":
        return {"status": "ignored"}

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            if event.get("message", {}).get("is_echo"):
                continue
            text = event.get("message", {}).get("text")
            if not text:
                continue
            sender_id = event["sender"]["id"]
            asyncio.create_task(handle_reply(sender_id, text))

    return {"status": "ok"}


async def handle_reply(sender_id: str, text: str):
    reply = await generate_reply(sender_id, text)
    await send_message(sender_id, reply)
