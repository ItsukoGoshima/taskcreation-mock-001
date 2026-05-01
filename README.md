# Task Creation Bot

## 概要

PigoutのAI依頼作成会話体験を、Slack bot上でモックアップするための実装。
Pigoutのバックエンドは使用せず、Anthropic APIを直接呼び出す。
**Railway上で常時稼働中**（Socket Mode使用、サーバーレスではなくWorkerプロセスとして動作）。

ユーザーがbotにメンションすると、AIがヒアリングを通じて業務依頼の内容を整理し、タスクとして作成する。

---

## 技術スタック

- **言語**: Python 3.11
- **Slack**: Slack Bolt for Python（Socket Mode）
- **AI**: Anthropic Python SDK（claude-sonnet-4-20250514）
- **コンテキスト保存**: ローカルJSONファイル（`conversations/` ディレクトリ）
- **ホスティング**: Railway（Workerプロセス）
- **環境変数**: Railway Variables（本番）/ python-dotenv（ローカル開発）

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
├── conversations/          # 自動生成（.gitignore済み・Railway再デプロイでリセット）
│   └── {thread_ts}.json
├── Procfile                # Railway起動コマンド（worker: python bot.py）
├── runtime.txt             # Pythonバージョン指定
├── .python-version         # Nixpacks向けPythonバージョン指定
├── requirements.txt
├── .env                    # ローカル開発用（gitignore済み）
└── .gitignore
```

---

## Slack Appの設定

[Slack API管理画面](https://api.slack.com/apps) で以下を設定する。

### 1. Socket Modeを有効化

**Settings > Socket Mode** を ON にする。

App-Level Tokenを発行し、スコープに `connections:write` を付与する。発行されたトークン（`xapp-...`）を Railway Variables の `SLACK_APP_TOKEN` に設定する。

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

### 5. 環境変数の設定

**Railway管理画面の「Variables」タブ**で以下の3つを設定する。

| Key | 取得元 |
|---|---|
| `SLACK_BOT_TOKEN` | OAuth & Permissions > Bot User OAuth Token（`xoxb-`で始まる） |
| `SLACK_APP_TOKEN` | Settings > Socket Mode > App-Level Tokens（`xapp-`で始まる） |
| `ANTHROPIC_API_KEY` | Anthropic Console |

> ローカル開発時は `.env` ファイルに同じ値を設定する。

---

## デプロイ（Railway）

### 初回デプロイ

1. [Railway](https://railway.app) にログイン
2. 「New Project」→「Deploy from GitHub repo」→ このリポジトリを選択
3. Railway Variables に環境変数3つを設定（上記参照）
4. 自動で再デプロイが始まり、起動する

### プロンプトの更新

`prompts/` 配下のファイルを編集して push するだけで自動再デプロイされる。

```bash
git add prompts/phase2.md
git commit -m "プロンプト更新"
git push
```

---

## ローカル開発

```bash
pip install -r requirements.txt
python bot.py
```

---

## 動作確認

1. botをSlackチャンネルにInviteする（`/invite @botの名前`）
2. `@bot 経費精算を依頼したい` と投稿する
3. Phase 1〜4 の流れを確認する

```
Phase 1: カテゴリ自動判定（ユーザーには非表示）
  ↓
Phase 2: ヒアリング（AIが1〜2問ずつ質問）
  ↓
Phase 3: タスク内容確認カード表示（✅ 承認する / ✏️ 修正する ボタン）
  ↓
Phase 4: 完了メッセージ投稿
```

---

## ログ出力

`bot.py` は Pythonの `logging` モジュールを使用してフェーズごとの処理内容を出力する。

### ログの確認方法

Railway管理画面の「Deployments」→ 最新のデプロイ →「View Logs」

### 出力内容

| タイミング | 出力内容 |
|---|---|
| 新規会話開始 | `thread_ts`・ユーザーID・最初のメッセージ |
| Phase 1 完了 | カテゴリ・サブカテゴリ・確信度・判断理由 |
| Phase 2 継続 | `thread_ts`・ユーザーメッセージ |
| Phase 2→3 遷移 | ヒアリング完了サマリー |
| Phase 3 カード表示 | タスクタイトル・説明文 |
| Phase 4 承認 | `task_content` の全内容（JSON形式） |
| 修正ボタン押下 | `thread_ts`・Phase 2への差し戻し |
| エラー発生時 | エラー内容（ERROR レベル） |

### ログ出力例

```
2026-05-01 12:00:00 [INFO] [新規会話] thread_ts=1234567890.123456 user=U0XXXXX message=経費精算を依頼したい
2026-05-01 12:00:01 [INFO] [Phase1] category=経理・財務 sub_category=経費精算 confidence=0.95 rationale=経費精算という明確なキーワードがあるため
2026-05-01 12:00:05 [INFO] [Phase2] thread_ts=1234567890.123456 user_message=3件分まとめてお願いします
2026-05-01 12:00:08 [INFO] [Phase2→3] ヒアリング完了 summary=交通費・宿泊費・接待費の3件、合計約5万円の経費精算
2026-05-01 12:00:09 [INFO] [Phase3] title=経費精算依頼（3件） description=交通費・宿泊費・接待費...
2026-05-01 12:00:15 [INFO] [Phase4 承認] thread_ts=1234567890.123456
{
  "title": "経費精算依頼（3件）",
  "description": "...",
  "final_reply": "..."
}
```
