# Railway展開指示書（Claude Code向け）

## 前提条件

- ローカルでSlack botが動作済みであること
- GitHubアカウントがあること
- Railwayアカウントがあること（https://railway.app でGitHubアカウントでサインアップ可能）

---

## やること概要

1. コードをGitHubにpushする
2. RailwayにGitHubリポジトリを連携する
3. Railwayの管理画面で環境変数を設定する
4. 動作確認する

---

## Step 1: コードをGitHubにpushできる状態にする

以下のファイルが存在することを確認・作成してください。

### `.gitignore` の確認・更新

`.gitignore` に以下が含まれていることを確認し、なければ追記してください。

```
.env
conversations/
__pycache__/
*.pyc
```

`conversations/` をgitignoreに追加する理由：ローカルの会話データをGitHubに上げないようにするため。Railway上では空のディレクトリから始まります。

### `Procfile` を作成する

Railwayがアプリの起動方法を知るために必要です。

```
worker: python bot.py
```

※ Slack botはWebサーバーではなくSocket Modeで動くため、`worker` を使います。

### `requirements.txt` の確認

以下が含まれていることを確認してください。

```
slack-bolt
anthropic
python-dotenv
```

### `runtime.txt` を作成する（推奨）

Pythonのバージョンを明示します。

```
python-3.11.0
```

### `conversations/` ディレクトリの扱い

gitignoreしているため、Gitには含まれません。
Railway上で自動作成されるよう、`storage.py` の保存処理に以下を追加してください。

```python
import os
os.makedirs("conversations", exist_ok=True)
```

ファイル保存の直前に呼び出す形にしてください。

---

## Step 2: GitHubにpushする

以下のコマンドを順に実行してください。

```bash
git init
git add .
git commit -m "initial commit"
```

その後、GitHubで新しいリポジトリを作成し（Private推奨）、表示されるコマンドに従ってpushします。

```bash
git remote add origin https://github.com/あなたのユーザー名/リポジトリ名.git
git branch -M main
git push -u origin main
```

---

## Step 3: Railwayにデプロイする

1. https://railway.app にログイン
2. 「New Project」→「Deploy from GitHub repo」を選択
3. 連携するリポジトリを選択
4. デプロイが自動で始まります（この時点ではまだ動きません。環境変数が未設定のため）

---

## Step 4: 環境変数を設定する

Railwayの管理画面で以下を設定します。

1. デプロイしたプロジェクトを開く
2. 「Variables」タブを開く
3. 以下の3つを追加する

| Key | Value |
|-----|-------|
| `SLACK_BOT_TOKEN` | `xoxb-...`（ローカルの.envの値をそのまま） |
| `SLACK_APP_TOKEN` | `xapp-...`（ローカルの.envの値をそのまま） |
| `ANTHROPIC_API_KEY` | `sk-ant-...`（ローカルの.envの値をそのまま） |

4. 保存すると自動的に再デプロイが始まります

---

## Step 5: 動作確認

1. Railwayの「Deployments」タブでログを確認する
2. `⚡ Bolt app is running!` のようなメッセージが出ていればOK
3. Slackで `@bot こんにちは` とメンションして応答があれば成功

---

## トラブルシューティング

**ログの確認方法**
Railway管理画面の「Deployments」→ 最新のデプロイ → 「View Logs」

**よくあるエラー**

| エラー内容 | 原因 | 対処 |
|-----------|------|------|
| `ModuleNotFoundError` | requirements.txtに漏れ | 該当パッケージを追加してpush |
| `invalid_auth` | 環境変数のトークンが間違い | Railwayの Variables を再確認 |
| アプリが起動してすぐ落ちる | Procfileが間違い | `worker: python bot.py` を確認 |

---

## 今後の運用

### プロンプトを更新したいとき

```bash
# prompts/phase2.md などを編集後
git add .
git commit -m "プロンプト更新"
git push
```

pushするだけでRailwayが自動的に再デプロイします。

### 無料枠について

Railwayの無料プランは月500時間まで。
数人での検証利用であれば十分です。
超過しそうな場合は月5ドルのプランにアップグレードしてください。
