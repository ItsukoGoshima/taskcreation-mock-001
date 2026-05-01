# Task Creation Bot

## 概要

PigoutのAI依頼作成会話体験を、Slack bot上でモックアップするためのローカル実装。
Pigoutのバックエンドは使用せず、Anthropic APIを直接呼び出す。

ユーザーがbotにメンションすると、AIがヒアリングを通じて業務依頼の内容を整理し、タスクとして作成する。

---

## 技術スタック

- **言語**: Python 3.11+
- **Slack**: Slack Bolt for Python（Socket Mode、ngrok不要）
- **AI**: Anthropic Python SDK（claude-sonnet-4-20250514）
- **コンテキスト保存**: ローカルJSONファイル
- **環境変数**: python-dotenv

---

## ディレクトリ構成

```
task-creation-bot/
├── bot.py                  # Slackイベント受信・メイン処理
├── ai_agent.py             # Anthropic API呼び出し・Phase管理
├── storage.py              # 会話コンテキストのJSON永続化
├── prompts/
│   ├── phase1.md           # Phase 1 システムプロンプト（カテゴリ判定）
│   ├── phase2.md           # Phase 2 システムプロンプト（ヒアリング）
│   ├── phase3.md           # Phase 3 システムプロンプト（タスク整理）
│   └── phase4.md           # Phase 4 システムプロンプト（完了）
├── conversations/          # 自動生成（.gitignore済み）
│   └── {thread_ts}.json
├── requirements.txt
├── .env
└── .gitignore
```

---

## Slack Appの設定

[Slack API管理画面](https://api.slack.com/apps) で以下を設定する。

### 1. Socket Modeを有効化

**Settings > Socket Mode** を ON にする。

App-Level Tokenを発行し、スコープに `connections:write` を付与する。発行されたトークン（`xapp-...`）を `.env` の `SLACK_APP_TOKEN` に設定する。

### 2. Event Subscriptionsを設定

**Features > Event Subscriptions** を ON にし、**Subscribe to bot events** に `app_mention` を追加する。

### 3. Interactivityを有効化

**Features > Interactivity & Shortcuts** を ON にする（ボタンアクション受信のため必須）。

### 4. Bot Token Scopesを設定

**OAuth & Permissions > Scopes > Bot Token Scopes** に以下を追加する。

| スコープ | 用途 |
|---|---|
| `chat:write` | メッセージ投稿 |
| `app_mentions:read` | メンション受信 |

### 5. トークンを.envに設定

```env
SLACK_BOT_TOKEN=xoxb-...   # OAuth & Permissions > Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...   # Settings > Socket Mode > App-Level Tokens
ANTHROPIC_API_KEY=sk-ant-... # Anthropic Console
```

---

## 実装完了後の動作確認手順

### セットアップ

```bash
pip install -r requirements.txt
```

### 起動

```bash
python bot.py
```

### 動作確認

1. botをSlackチャンネルにInviteする
2. チャンネルで `@bot 経費精算を依頼したい` と投稿する
3. Phase 1〜4 の流れを確認する

```
Phase 1: カテゴリ自動判定（ユーザーには非表示）
  ↓
Phase 2: ヒアリング（AIが1〜2問ずつ質問）
  ↓
Phase 3: タスク内容確認カード表示（承認 / 修正ボタン）
  ↓
Phase 4: 完了メッセージ投稿
```

4. `prompts/phase2.md` を編集して、bot再起動なしにプロンプト変更が反映されることを確認する
