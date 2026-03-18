# YouTube自動化パイプライン - プロジェクト概要

## チャンネル情報
- **チャンネル名**: 睡眠改善ラボ（仮）
- **ジャンル**: 睡眠解説系（科学的根拠ベース）
- **収益目標**: 6〜12ヶ月で月10〜30万円（広告+アフィリエイト）
- **動画の長さ**: 8分以上（広告複数挿入のため）
- **TTS**: VOICEVOX（キャラは流行に合わせて変更）
- **BGM動画も検討中**

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

## 現在の状態
- コードは全ステップ実装済み
- **未設定**: APIキー（.envファイル）、FFmpeg、YouTube OAuth認証
- **オーナーの技術レベル**: プログラミング初心者。動画制作・VOICEVOXは経験豊富
- **オーナーの役割**: 動画クオリティの担保。技術的な部分はClaude Codeが担当

## 設定ファイル
- `config.yaml` - チャンネル・パイプライン設定
- `.env` - APIキー（未作成）
- `requirements.txt` - Pythonライブラリ

## 重要な方針
- オーナーはAPIなどの技術面は詳しくない。操作手順はステップバイステップで丁寧に説明すること
- コマンドはコピペで実行できる形で提示すること
- 動画構成やチャンネル方針の変更はオーナーと相談して決めること
- キャラ（VOICEVOXスピーカー）はその時の流行に合わせて変更可能
