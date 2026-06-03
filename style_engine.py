import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_style_profile() -> dict:
    path = Path(__file__).parent / "style_profile.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt() -> str:
    profile = load_style_profile()
    shop_context = profile.get("shop_context", "")

    if not profile or all(
        not profile.get(k) for k in ("tone", "greeting_style", "raw_examples")
    ):
        base = "Bạn là nhân viên tư vấn bán hàng thân thiện, trả lời ngắn gọn và tự nhiên."
        if shop_context:
            base += f"\n\nThông tin shop:\n{shop_context}"
        return base

    tone = profile.get("tone", "")
    sentence_length = profile.get("sentence_length", "")
    punctuation = profile.get("punctuation", "")
    emoji_usage = profile.get("emoji_usage", "")
    filler_words = profile.get("filler_words", [])
    greeting_style = profile.get("greeting_style", "")
    response_patterns = profile.get("response_patterns", {})
    limits = profile.get("token_limits", {})
    max_examples = limits.get("max_examples_in_prompt", 10)
    raw_examples = profile.get("raw_examples", [])[:max_examples]
    avoid = profile.get("avoid", [])

    filler_str = ", ".join(filler_words) if filler_words else "không có"
    avoid_str = "\n".join(f"- {a}" for a in avoid) if avoid else "- Không có"

    patterns_str = ""
    for situation, pattern in response_patterns.items():
        patterns_str += f"\n- {situation}: {pattern}"

    examples_str = "\n".join(f'"{ex}"' for ex in raw_examples)

    prompt = f"""Bạn là nhân viên tư vấn bán hàng. Hãy trả lời đúng phong cách sau:

PHONG CÁCH VIẾT:
- Giọng điệu: {tone}
- Độ dài câu: {sentence_length}
- Dấu câu: {punctuation}
- Dùng emoji: {emoji_usage}
- Từ đệm hay dùng: {filler_str}
- Cách chào: {greeting_style}

CÁCH XỬ LÝ TÌNH HUỐNG:{patterns_str}

VÍ DỤ TIN NHẮN THỰC TẾ (học phong cách, không copy nguyên văn):
{examples_str}

TRÁNH:
{avoid_str}"""

    if shop_context:
        prompt += f"\n\nTHÔNG TIN SHOP:\n{shop_context}"

    return prompt


def get_token_limits() -> dict:
    profile = load_style_profile()
    limits = profile.get("token_limits", {})
    return {
        "max_output_tokens": int(limits.get("max_output_tokens", 200)),
        "max_history_turns": int(limits.get("max_history_turns", 8)),
        "max_examples_in_prompt": int(limits.get("max_examples_in_prompt", 10)),
    }
