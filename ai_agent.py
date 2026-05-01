import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"


def _load_prompt(phase: int) -> str:
    with open(Path(f"prompts/phase{phase}.md"), "r", encoding="utf-8") as f:
        return f.read()


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def run_phase1(user_message: str) -> dict:
    system = _load_prompt(1)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return _parse_json(response.content[0].text)


def run_phase2(conversation: dict) -> dict:
    system = _load_prompt(2)
    system = system.replace("{category}", conversation.get("category") or "")
    system = system.replace("{sub_category}", conversation.get("sub_category") or "")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=conversation["messages"],
    )
    return _parse_json(response.content[0].text)


def run_phase3(conversation: dict, summary: str) -> dict:
    system = _load_prompt(3)
    messages = conversation["messages"] + [
        {"role": "user", "content": f"依頼内容の要約:\n{summary}"}
    ]
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return _parse_json(response.content[0].text)


def run_phase4(conversation: dict) -> dict:
    system = _load_prompt(4)
    task = conversation.get("task_content") or {}
    content = f"タイトル: {task.get('title', '')}\n依頼内容: {task.get('description', '')}"
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    return _parse_json(response.content[0].text)
