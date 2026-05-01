import json
from pathlib import Path

CONVERSATIONS_DIR = Path("conversations")


def load_conversation(thread_ts: str) -> dict | None:
    path = CONVERSATIONS_DIR / f"{thread_ts}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_conversation(data: dict) -> None:
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    path = CONVERSATIONS_DIR / f"{data['thread_ts']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_conversation(thread_ts: str, channel: str, user_id: str) -> dict:
    return {
        "thread_ts": thread_ts,
        "channel": channel,
        "user_id": user_id,
        "phase": 1,
        "category": None,
        "sub_category": None,
        "category_confidence": None,
        "category_rationale": None,
        "messages": [],
        "task_content": None,
    }
