import json
import os
import glob
from pathlib import Path
import google.generativeai as genai

# ── Điền thông tin của bạn vào đây ──────────────────────────────────────────
INBOX_PATH = ""   # VD: "/Users/you/Downloads/messages/inbox"
MY_NAME = ""      # VD: "Nguyen Van A"
# ─────────────────────────────────────────────────────────────────────────────

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))


def load_my_messages(inbox_path: str, my_name: str) -> list[str]:
    messages = []
    pattern = str(Path(inbox_path) / "**" / "message_*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath, "rb") as f:
            raw = f.read().decode("latin1").encode("utf-8", errors="replace").decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for msg in data.get("messages", []):
            sender = msg.get("sender_name", "")
            # decode latin1→utf8 cho sender name
            try:
                sender = sender.encode("latin1").decode("utf-8")
            except Exception:
                pass
            content = msg.get("content", "")
            try:
                content = content.encode("latin1").decode("utf-8")
            except Exception:
                pass
            if sender == my_name and len(content.strip()) >= 3:
                messages.append(content.strip())
    return messages


def analyze_style(messages: list[str]) -> dict:
    sample = messages[:300]
    sample_text = "\n".join(f"- {m}" for m in sample)

    prompt = f"""Phân tích phong cách nhắn tin của người dùng qua các tin nhắn sau:

{sample_text}

Trả về JSON thuần (không markdown, không giải thích) với cấu trúc sau:
{{
  "greeting_style": "cách chào hỏi thường dùng",
  "tone": "giọng điệu tổng thể",
  "sentence_length": "độ dài câu trung bình",
  "punctuation": "cách dùng dấu câu",
  "emoji_usage": "cách dùng emoji",
  "filler_words": ["từ đệm 1", "từ đệm 2"],
  "response_patterns": {{
    "when_asked_price": "cách trả lời khi hỏi giá",
    "when_asked_availability": "cách trả lời khi hỏi còn hàng không",
    "when_customer_complaint": "cách xử lý phàn nàn",
    "general_inquiry": "cách trả lời câu hỏi chung"
  }},
  "example_messages": ["ví dụ 1", "ví dụ 2", "ví dụ 3"],
  "avoid": ["điều cần tránh 1", "điều cần tránh 2"]
}}"""

    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown fence nếu có
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(text)


if __name__ == "__main__":
    if not INBOX_PATH or not MY_NAME:
        print("Vui lòng điền INBOX_PATH và MY_NAME trong file này trước khi chạy.")
        exit(1)

    print(f"Đang tải tin nhắn của '{MY_NAME}' từ {INBOX_PATH}...")
    messages = load_my_messages(INBOX_PATH, MY_NAME)
    print(f"Tìm thấy {len(messages)} tin nhắn.")

    if not messages:
        print("Không tìm thấy tin nhắn nào. Kiểm tra lại INBOX_PATH và MY_NAME.")
        exit(1)

    print("Đang phân tích phong cách với Gemini...")
    style = analyze_style(messages)
    style["raw_examples"] = messages[:50]

    output_path = Path(__file__).parent / "style_profile.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(style, f, ensure_ascii=False, indent=2)

    print(f"Đã lưu style_profile.json tại {output_path}")
