# Slack Bot 実装指示書（Claude Code向け）

## 概要

PigoutのAI依頼作成会話体験を、Slack bot上でモックアップするためのローカル実装。
Pigoutのバックエンドは使用せず、Anthropic APIを直接呼び出す。

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
slack-bot/
├── bot.py                  # Slackイベント受信・メイン処理
├── ai_agent.py             # Anthropic API呼び出し・Phase管理
├── storage.py              # 会話コンテキストのJSON永続化
├── prompts/
│   ├── phase1.md           # Phase 1 システムプロンプト
│   ├── phase2.md           # Phase 2 システムプロンプト
│   ├── phase3.md           # Phase 3 システムプロンプト
│   └── phase4.md           # Phase 4 システムプロンプト
├── conversations/          # 自動生成（gitignore推奨）
│   └── {thread_ts}.json
├── requirements.txt
└── .env
```

---

## 環境変数（.env）

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## requirements.txt

```
slack-bolt
anthropic
python-dotenv
```

---

## 会話データ設計（conversations/{thread_ts}.json）

```json
{
  "thread_ts": "1234567890.123456",
  "channel": "C0XXXXXXX",
  "user_id": "U0XXXXXXX",
  "phase": 2,
  "category": "経理・財務",
  "sub_category": "経費精算",
  "category_confidence": 0.92,
  "category_rationale": "経費精算という明確なキーワードがあるため",
  "messages": [
    {"role": "user", "content": "経費精算を依頼したい"},
    {"role": "assistant", "content": "承知しました。いくつか確認させてください。"}
  ],
  "task_content": null
}
```

---

## Phase設計

### Phase 1: カテゴリ自動判定

- `prompts/phase1.md` を読み込みシステムプロンプトとして使用
- AIにユーザーの最初のメッセージを渡す
- AIは必ず以下のJSON形式のみで返答する

```json
{
  "category": "string",
  "sub_category": "string",
  "confidence": 0.95,
  "rationale": "string"
}
```

- 結果をJSONファイルに保存（ユーザーには表示しない）
- 即座にPhase 2へ遷移し、Phase 2のヒアリングを開始する

### Phase 2: ヒアリング

- `prompts/phase2.md` を読み込みシステムプロンプトとして使用
- コンテキストとして `category`, `sub_category`, `messages`（会話履歴）を渡す
- AIは必ず以下のJSON形式のみで返答する

```json
{
  "reply": "string",
  "complete": false,
  "summary": "string"
}
```

- `complete: false` → `reply` をSlackに投稿してヒアリング継続
- `complete: true` → Phase 3へ遷移

### Phase 3: タスク内容確認

- `prompts/phase3.md` を読み込みシステムプロンプトとして使用
- コンテキストとして `summary`, `messages` を渡す
- AIは必ず以下のJSON形式のみで返答する

```json
{
  "reply": "string",
  "title": "string",
  "description": "string"
}
```

- Slack Block Kit でタスク内容カードを表示する
  - `reply`（確認メッセージ）
  - `title`（タスクタイトル）
  - `description`（タスク説明）
  - 「✅ 承認する」「✏️ 修正する」の2ボタン
- 「承認する」ボタン押下 → Phase 4へ遷移
- 「修正する」ボタン押下 → Phase 2に戻す（ヒアリング再開）

### Phase 4: 完了

- `prompts/phase4.md` を読み込みシステムプロンプトとして使用
- タスクのタイトルと説明文をSlackにシンプルに投稿する
- JSONの `task_content` に最終内容を保存して終了

---

## Slackイベントの処理フロー

### メンション受信時（`@bot メッセージ`）

```
1. botへのメンションか確認（メンションでなければ無視）
2. thread_ts を取得
   - スレッド内メンション → thread_ts = event["thread_ts"]
   - チャンネルへの直接投稿（新規）→ thread_ts = event["ts"]
3. conversations/{thread_ts}.json を確認
   - ファイルあり → 既存会話の続き（現在のphaseを読み込む）
   - ファイルなし → 新規会話（phase=1 で初期化）
4. 「回答を作成中です。お待ちください 🤔」をスレッドに投稿
5. 現在のphaseに応じてai_agent.pyを呼び出す
6. 結果をSlackに投稿
7. conversations/{thread_ts}.json を更新
```

### ボタンアクション受信時

```
1. action_id で「approve」か「revise」かを判定
2. thread_ts からJSONを読み込む
3. 「承認する」→ Phase 4 の処理を実行
4. 「修正する」→ phase=2 に戻し「修正内容を教えてください」と投稿
```

---

## プロンプトファイルの仕様

### `prompts/phase1.md`

```markdown
あなたはユーザーの業務依頼を分類するAIアシスタントです。
ユーザーのメッセージからカテゴリを推定してください。

## 出力形式
必ず以下のJSON形式のみで返答してください。前置きや説明は不要です。

{
  "category": "カテゴリ名",
  "sub_category": "サブカテゴリ名",
  "confidence": 0.0〜1.0の数値,
  "rationale": "判断理由"
}

## カテゴリ一覧
- 経理・財務（例: 経費精算、請求書処理、仕訳）
- 人事・労務（例: 勤怠管理、給与計算、採用）
- 総務・庶務（例: 備品発注、施設管理、郵便）
- 営業サポート（例: 資料作成、顧客対応、データ整理）
- ITサポート（例: システム設定、ツール導入、データ管理）
- その他
```

### `prompts/phase2.md`

```markdown
あなたはユーザーの業務依頼をヒアリングするAIアシスタントです。
カテゴリ情報と会話履歴をもとに、依頼内容を明確化するための質問を行ってください。

## コンテキスト
- カテゴリ: {category}
- サブカテゴリ: {sub_category}

## ルール
- 一度に質問するのは1〜2個まで
- 依頼内容が十分に明確になったら complete: true を返す
- 明確化に必要な情報: 作業内容の詳細、期待する成果物、締切や頻度など

## 出力形式
必ず以下のJSON形式のみで返答してください。

{
  "reply": "ユーザーへの返答メッセージ",
  "complete": true or false,
  "summary": "これまでの依頼内容の要約（complete: trueのときのみ記入）"
}
```

### `prompts/phase3.md`

```markdown
あなたはユーザーの業務依頼をタスクとして整理するAIアシスタントです。
ヒアリング内容をもとに、タスクのタイトルと説明文を作成してください。

## ルール
- タイトルは簡潔に（30文字以内）
- 説明文は依頼内容を具体的に記載する（誰が読んでも作業できる粒度）

## 出力形式
必ず以下のJSON形式のみで返答してください。

{
  "reply": "タスク内容の確認メッセージ",
  "title": "タスクのタイトル",
  "description": "タスクの説明文"
}
```

### `prompts/phase4.md`

```markdown
あなたはユーザーの業務依頼の受付を完了するAIアシスタントです。
タスクが正式に受け付けられたことを、丁寧に伝えてください。

## 出力形式
必ず以下のJSON形式のみで返答してください。

{
  "reply": "完了メッセージ（タイトルと依頼内容への言及を含める）"
}
```

---

## Phase 3 Block Kit メッセージ構造（参考）

```python
blocks = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": reply}
    },
    {"type": "divider"},
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*タイトル*\n{title}"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*依頼内容*\n{description}"}
    },
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
                "value": thread_ts
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ 修正する"},
                "action_id": "revise",
                "value": thread_ts
            }
        ]
    }
]
```

---

## 実装上の注意事項

1. **AIのレスポンスは必ずJSONパースする**。パース失敗時はユーザーに「エラーが発生しました。もう一度お試しください」と返す。

2. **プロンプトは毎回ファイルから読み込む**。モジュールキャッシュを使わず、`open()`で都度読み込むことでbot再起動なしにプロンプト変更が反映される。

3. **スレッドへの返信は必ず `thread_ts` を指定する**。チャンネルに直接投稿しないこと。

4. **ボタンのアクション受信後は必ず `ack()` を呼ぶ**。3秒以内に呼ばないとSlack側でタイムアウトエラーになる。

5. **自分自身（bot）のメッセージには反応しない**。`event.get("bot_id")` が存在する場合はスキップする。

---

## Slack App の設定（Slack管理画面）

Socket Modeを使うため、以下を有効化すること。

- **Socket Mode**: ON
- **Event Subscriptions**: `app_mention`
- **Interactivity**: ON（ボタンアクション受信のため）
- **Bot Token Scopes**: `chat:write`, `app_mentions:read`

---

## 実装完了後の動作確認手順

1. `python bot.py` でbot起動
2. SlackでbotをチャンネルにInvite
3. `@bot 経費精算を依頼したい` と投稿
4. Phase 1→2→3→4 の流れを確認
5. `prompts/phase2.md` を編集して、bot再起動なしに反映されることを確認
