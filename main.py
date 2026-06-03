import os
import json
import asyncio
import secrets
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fb_client import send_message
from ai_client import generate_reply
import style_engine
import ai_client as _ai
import log_store

app = FastAPI()

VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN", "")
DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.environ.get("DASHBOARD_PASS", "")

security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), DASHBOARD_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), DASHBOARD_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/")
async def dashboard(_: None = Depends(require_auth)):
    return FileResponse("static/dashboard.html")


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
    log_store.record(sender_id, "in", text)
    for attempt in range(3):
        try:
            reply = await generate_reply(sender_id, text)
            break
        except Exception as e:
            err = str(e)
            if "503" in err or "UNAVAILABLE" in err:
                if attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
            reply = "Dạ hiện tại em đang bận, anh/chị nhắn lại sau chút nhé ạ 🙏"
            break
    try:
        log_store.record(sender_id, "out", reply)
        await send_message(sender_id, reply)
    except Exception as e:
        import logging
        logging.error(f"send_message failed: {e}")


@app.get("/api/stats")
async def api_stats(_: None = Depends(require_auth)):
    return log_store.stats()


@app.get("/api/messages")
async def api_messages(_: None = Depends(require_auth)):
    return log_store.recent()


@app.get("/api/sessions")
async def api_sessions(_: None = Depends(require_auth)):
    return log_store.sessions()


@app.post("/api/chat")
async def api_chat(request: Request, _: None = Depends(require_auth)):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    reply = await generate_reply("__dashboard__", message)
    return {"reply": reply}


@app.get("/api/style")
async def get_style(_: None = Depends(require_auth)):
    path = Path("style_profile.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@app.post("/api/style")
async def save_style(request: Request, _: None = Depends(require_auth)):
    body = await request.json()
    path = Path("style_profile.json")
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    style_engine.load_style_profile.cache_clear()
    _ai.reload_model()
    return {"status": "ok"}
