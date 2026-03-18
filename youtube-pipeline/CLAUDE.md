# YouTube自動化パイプライン - プロジェクト概要

## プロジェクトの経緯と背景

### オーナーについて
- プログラミング初心者。API・コマンドライン・Git等の技術知識はほぼゼロからスタート
- 動画制作・VOICEVOXは経験豊富（バリバリ使っている）
- 技術的な部分はすべてClaude Codeが担当。オーナーの役割は動画クオリティの担保
- 操作手順はステップバイステップで、コピペで実行できる形で提示すること

### これまでの流れ
1. 最初にWeb版Claude Codeで「YouTubeの自動化パイプラインを作りたい」という相談からスタート
2. Web版でコード（pipeline.py, steps/配下の6ステップ）を全部書いた
3. しかしWeb版ではVOICEVOXやFFmpegなど「PCで動かすソフト」が使えないことが判明
4. CLI版Claude Codeに移行することを決定
5. オーナーのWindows PCに以下をインストール完了：
   - Python 3.14.3 ✓
   - Node.js v24.14.0 ✓
   - Git for Windows ✓
   - Claude Code CLI v2.1.78 ✓
   - VOICEVOX（元々入っていた）✓
6. GitHubからコードをcloneし、ブランチ `claude/youtube-automation-pipeline-KINiK` に切り替え済み
7. **まだ未完了**: requirements.txtのインストール、FFmpegインストール、APIキー設定、テスト動画生成

### 動画生成方式について（重要な経緯）
- 当初、動画生成にはRemotionAI（React/TypeScriptベースの動画生成フレームワーク）の使用も検討していた
- Remotionならアニメーション・トランジション・動くテロップなど凝った演出ができる
- しかし、まず最初はFFmpegでシンプルに始めることにした（背景+音声+字幕の合成）
- **理由**: 睡眠解説系は落ち着いた画面が合う。内容と投稿頻度の方がチャンネル成長に重要。セットアップも軽い
- **現在のコード（steps/video.py）はFFmpegベースで実装済み**
- **将来的にもっと凝った演出が必要になったらRemotionへの切り替えを検討する**
- この判断はオーナーと相談の上で決めたもの。FFmpegで1本テスト動画を作って見た目を確認し、物足りなければRemotionに移行する予定

## チャンネル情報
- **チャンネル名**: 睡眠改善ラボ（仮・変更可能）
- **ジャンル**: 睡眠解説系（科学的根拠ベース）
- **収益目標**: 6〜12ヶ月で月10〜30万円（広告+アフィリエイト含む）
- **動画の長さ**: 8分以上（8分以上で広告を複数挿入できるため）
- **TTS**: VOICEVOX（キャラはその時の流行に合わせて変更。ずんだもんに限定しない）
- **BGM動画**: たまには出してもいいかもね、という方針
- **動画構成**: まだ固まっていない。オーナーと一緒に決めていく

## パイプライン構成（6ステップ全自動）
1. **collect** - ネタ収集（RSS/YouTubeトレンド → Claudeで優先順位付け）
2. **script** - 台本生成（Claude APIで10分台本を自動生成）
3. **audio** - 音声合成（VOICEVOX → OpenAI TTS → gTTS のフォールバック）
4. **video** - 動画合成（FFmpegで背景+音声+字幕を合成）
5. **thumbnail** - サムネイル作成（Pillowで自動生成）
6. **upload** - YouTube投稿（OAuth認証で自動アップロード）

## 実行方法
```bash
# 全ステップ実行
python pipeline.py

# 特定トピックで実行
python pipeline.py --topic "睡眠の質を上げる方法"

# 特定ステップから再開
python pipeline.py --from-step audio

# テスト実行（API呼ばない）
python pipeline.py --dry-run
```

## 現在の状態（セットアップ進捗）
### 完了
- [x] Python 3.14.3 インストール済み
- [x] Node.js v24.14.0 インストール済み
- [x] Git for Windows インストール済み
- [x] Claude Code CLI インストール・ログイン済み
- [x] VOICEVOX インストール済み（元々あった）
- [x] GitHubからコードをclone済み
- [x] ブランチ切り替え済み

### 未完了（次にやること）
- [ ] `pip install -r requirements.txt` の実行
- [ ] FFmpegのインストール
- [ ] APIキー設定（.envファイル作成）
  - ANTHROPIC_API_KEY（Claude API）
  - YOUTUBE_API_KEY（YouTube Data API）
  - YouTube OAuth認証（client_secrets.json）
- [ ] VOICEVOXとの接続テスト
- [ ] テスト動画を1本生成して品質確認
- [ ] 品質確認後、FFmpegのままでいくかRemotionに切り替えるか判断

## 設定ファイル
- `config.yaml` - チャンネル・パイプライン設定（編集済み）
- `.env` - APIキー（**未作成**）
- `requirements.txt` - Pythonライブラリ一覧

## 重要な方針
- オーナーはAPIなどの技術面は詳しくない。操作手順はステップバイステップで丁寧に説明すること
- コマンドはコピペで実行できる形で提示すること
- 動画構成やチャンネル方針の変更はオーナーと相談して決めること
- キャラ（VOICEVOXスピーカー）はその時の流行に合わせて変更可能
- 動画の見た目が物足りなければRemotionへの移行を検討すること
- まずは「1本作って見てみる」を最優先にすること
