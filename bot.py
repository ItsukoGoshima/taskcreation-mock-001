import os
import re

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import ai_agent
import storage

load_dotenv()

app = App(token=os.getenv("SLACK_BOT_TOKEN"))


def _strip_mention(text: str) -> str:
    return re.sub(r"^<@[A-Z0-9]+>\s*", "", text).strip()


def _post_phase3_card(client, channel: str, thread_ts: str, reply: str, title: str, description: str) -> None:
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": reply}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*タイトル*\n{title}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*依頼内容*\n{description}"}},
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"phase3_actions_{thread_ts}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ 承認する"},
                    "style": "primary",
                    "action_id": "approve",
                    "value": thread_ts,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️ 修正する"},
                    "action_id": "revise",
                    "value": thread_ts,
                },
            ],
        },
    ]
    client.chat_postMessage(channel=channel, thread_ts=thread_ts, blocks=blocks, text=reply)


@app.event("app_mention")
def handle_mention(event, say, client):
    if event.get("bot_id"):
        return

    thread_ts = event.get("thread_ts") or event["ts"]
    channel = event["channel"]
    user_id = event["user"]
    user_message = _strip_mention(event.get("text", ""))

    conv = storage.load_conversation(thread_ts)
    if conv is None:
        conv = storage.init_conversation(thread_ts, channel, user_id)

    say(text="回答を作成中です。お待ちください 🤔", thread_ts=thread_ts)

    try:
        phase = conv["phase"]

        if phase == 1:
            result1 = ai_agent.run_phase1(user_message)
            conv["category"] = result1.get("category")
            conv["sub_category"] = result1.get("sub_category")
            conv["category_confidence"] = result1.get("confidence")
            conv["category_rationale"] = result1.get("rationale")
            conv["messages"].append({"role": "user", "content": user_message})
            conv["phase"] = 2
            storage.save_conversation(conv)

            result2 = ai_agent.run_phase2(conv)
            reply = result2.get("reply", "")
            conv["messages"].append({"role": "assistant", "content": reply})
            storage.save_conversation(conv)
            say(text=reply, thread_ts=thread_ts)

        elif phase == 2:
            conv["messages"].append({"role": "user", "content": user_message})
            result2 = ai_agent.run_phase2(conv)
            reply = result2.get("reply", "")
            complete = result2.get("complete", False)
            summary = result2.get("summary", "")

            conv["messages"].append({"role": "assistant", "content": reply})

            if complete:
                conv["phase"] = 3
                storage.save_conversation(conv)

                result3 = ai_agent.run_phase3(conv, summary)
                p3_reply = result3.get("reply", "")
                title = result3.get("title", "")
                description = result3.get("description", "")

                conv["task_content"] = {"title": title, "description": description}
                storage.save_conversation(conv)

                _post_phase3_card(client, channel, thread_ts, p3_reply, title, description)
            else:
                storage.save_conversation(conv)
                say(text=reply, thread_ts=thread_ts)

        elif phase == 3:
            say(text="タスク内容をご確認の上、ボタンで操作してください。", thread_ts=thread_ts)

        else:
            say(text="この依頼はすでに完了しています。新しい依頼は新しいスレッドで投稿してください。", thread_ts=thread_ts)

    except Exception as e:
        say(text="エラーが発生しました。もう一度お試しください。", thread_ts=thread_ts)
        print(f"Error in phase {conv.get('phase')}: {e}")


@app.action("approve")
def handle_approve(ack, body, client):
    ack()

    thread_ts = body["actions"][0]["value"]
    channel = body["channel"]["id"]

    conv = storage.load_conversation(thread_ts)
    if conv is None:
        return

    try:
        conv["phase"] = 4
        storage.save_conversation(conv)

        result4 = ai_agent.run_phase4(conv)
        reply = result4.get("reply", "")

        if conv.get("task_content"):
            conv["task_content"]["final_reply"] = reply
            storage.save_conversation(conv)

        client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=reply)

    except Exception as e:
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="エラーが発生しました。もう一度お試しください。",
        )
        print(f"Error in approve: {e}")


@app.action("revise")
def handle_revise(ack, body, client):
    ack()

    thread_ts = body["actions"][0]["value"]
    channel = body["channel"]["id"]

    conv = storage.load_conversation(thread_ts)
    if conv is None:
        return

    conv["phase"] = 2
    storage.save_conversation(conv)

    client.chat_postMessage(channel=channel, thread_ts=thread_ts, text="修正内容を教えてください。")


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
