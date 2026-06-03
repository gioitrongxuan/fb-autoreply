import os
import httpx

FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
GRAPH_API_URL = "https://graph.facebook.com/v19.0/me/messages"


async def send_message(recipient_id: str, text: str) -> None:
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    params = {"access_token": FB_PAGE_ACCESS_TOKEN}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(GRAPH_API_URL, json=payload, params=params)
        resp.raise_for_status()
