# 睡眠チャンネル YouTube 自動化パイプライン セットアップガイド

## フロー概要

```
ネタ収集 → 台本生成 → 音声生成 → 映像合成 → サムネ生成 → 自動アップロード
(RSS/YT)  (Claude)  (VOICEVOX) (FFmpeg)  (Pillow)   (YT Data API)
```

---

## 1. 必要なものを用意する

### 必須
| ツール | 用途 | 取得先 |
|--------|------|--------|
| Python 3.11+ | 実行環境 | https://python.org |
| FFmpeg | 映像合成 | https://ffmpeg.org |
| Anthropic API キー | 台本生成 | https://console.anthropic.com |

### 任意（より高品質な音声にしたい場合）
| ツール | 用途 | 取得先 |
|--------|------|--------|
| VOICEVOX | 日本語TTS（無料・ローカル）| https://voicevox.hiroshiba.jp |
| OpenAI API キー | TTS フォールバック | https://platform.openai.com |

### YouTube アップロード用
| 項目 | 説明 |
|------|------|
| Google Cloud プロジェクト | YouTube Data API v3 を有効化 |
| OAuth 2.0 クライアント ID | デスクトップアプリ用 |

---

## 2. インストール

```bash
cd youtube-pipeline

# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt

# FFmpeg インストール (Ubuntu/Debian)
sudo apt install ffmpeg

# FFmpeg インストール (macOS)
brew install ffmpeg
```

---

## 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集して API キーを設定:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx        # 任意
YOUTUBE_API_KEY=AIzaxxxxxxxxxxxx      # 任意
```

---

## 4. YouTube API の設定（アップロードしたい場合）

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. **YouTube Data API v3** を有効化
3. 認証情報 → **OAuth 2.0 クライアント ID** → デスクトップアプリ を作成
4. JSON をダウンロードして `.secrets/youtube_credentials.json` に配置

```bash
mkdir -p .secrets
mv ~/Downloads/client_secret_*.json .secrets/youtube_credentials.json
```

---

## 5. アセットを追加（任意）

```
assets/
├── bgm/
│   └── sleep_bgm.mp3       # 睡眠系BGM（著作権フリーのもの）
├── backgrounds/
│   └── night_sky.jpg       # 背景画像（1920x1080推奨）
└── fonts/
    ├── NotoSansJP-Regular.ttf
    └── NotoSansJP-Bold.ttf  # Google Fonts から無料DL可能
```

**Noto Sans JP のDL:**
```bash
# Google Fonts からダウンロード
# https://fonts.google.com/noto/specimen/Noto+Sans+JP
```

---

## 6. 実行

### 全ステップ一括実行
```bash
python pipeline.py
```

### ステップ確認しながら実行
```bash
# ネタ収集→台本生成まで実行して確認
python pipeline.py --stop-after script

# 台本を確認・編集してから音声生成以降を実行
python pipeline.py --from-step audio

# 特定のトピックを指定（0始まり）
python pipeline.py --topic 2

# 動作確認（APIを実際に呼ばない）
python pipeline.py --dry-run
```

### VOICEVOX を使う場合
```bash
# VOICEVOX を起動してからパイプラインを実行
./VOICEVOX.AppImage &
python pipeline.py
```

---

## 7. 生成ファイルの場所

```
output/
├── topics/          # 収集したネタ (JSON)
├── scripts/         # 生成した台本 (JSON + TXT)
├── audio/           # 合成音声 (MP3)
├── video/           # 完成動画 (MP4)
└── thumbnails/      # サムネイル (JPG)
```

---

## 8. 自動化（スケジュール実行）

### cron で毎日 AM3:00 に実行
```bash
crontab -e
# 追加:
0 3 * * * cd /path/to/youtube-pipeline && .venv/bin/python pipeline.py >> logs/cron.log 2>&1
```

### config.yaml で予約投稿を有効化
```yaml
upload:
  schedule:
    enabled: true
    days_ahead: 1       # 翌日
    publish_time: "19:00:00"  # 19時公開
  privacy: "private"
```

---

## トラブルシューティング

| エラー | 対処 |
|--------|------|
| `VOICEVOX が起動していません` | VOICEVOX アプリを先に起動する |
| `FFmpeg コマンドが見つかりません` | FFmpeg をインストールして PATH を通す |
| `YouTube 認証エラー` | `.secrets/youtube_credentials.json` を再配置 |
| `Pillow フォント読み込み失敗` | `assets/fonts/` にフォントを配置する |
| 台本が短い/長い | `config.yaml` の `target_duration_minutes` を調整 |
