"""
Step 2: 台本生成 (Claude API)
トピック情報を元に YouTube 動画の台本を生成する。
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# プロンプトテンプレート
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM = """\
あなたは睡眠特化 YouTube チャンネルの台本ライターです。

## チャンネルコンセプト
- 睡眠の悩みを持つ30〜50代をメインターゲット
- 科学的根拠に基づいた実践的な情報を提供
- 視聴者が「今夜から試せる」内容を必ず含める
- 親しみやすく、専門的すぎない語り口

## 台本の書き方ルール
- 話し言葉で書く（「〜です」「〜ますよね」等）
- 一文は短く（読み上げで1〜2秒程度）
- 【間】と書いた部分は音声合成で間を取る
- (SE: 効果音名) で効果音指示を入れる
- 数字は読み方も括弧内に書く (例: 8時間(はちじかん))
"""

SCRIPT_USER = """\
以下のトピックで約 {duration} 分の YouTube 動画台本を作成してください。

## トピック情報
- タイトル案: {title}
- 概要: {topic_summary}
- ターゲットの悩み: {target_pain}
- 盛り込むポイント: {key_points}

## 構成（目安の秒数）
1. フック (30秒): 視聴者の悩みに共感し「この動画で解決できる」と示す
2. 自己紹介 (20秒): チャンネル紹介
3. 本編 ({main_seconds}秒): ポイントを1〜3個に分けて解説
4. まとめ (30秒): 今夜からできるアクションを提示
5. アウトロ (20秒): 高評価・チャンネル登録・次回予告

## 出力形式 (JSON)
{{
  "video_title": "実際に使う動画タイトル（30字以内）",
  "video_description": "YouTube説明欄テキスト（500字以内）",
  "tags": ["タグ1", "タグ2", ...],
  "sections": [
    {{
      "name": "hook",
      "label": "フック",
      "duration_sec": 30,
      "text": "台本テキスト..."
    }},
    ...
  ],
  "total_chars": 推定文字数(int),
  "estimated_duration_min": 推定再生時間(float)
}}
"""


# ---------------------------------------------------------------------------
# 台本生成
# ---------------------------------------------------------------------------

def generate_script(
    topic: dict,
    cfg: dict[str, Any],
    client: anthropic.Anthropic,
) -> dict:
    """Claude API を使って台本を生成する"""
    duration = cfg["target_duration_minutes"]
    total_sec = duration * 60
    main_seconds = total_sec - 30 - 20 - 30 - 20  # フック+自己紹介+まとめ+アウトロ除く

    user_prompt = SCRIPT_USER.format(
        duration=duration,
        title=topic.get("title", ""),
        topic_summary=topic.get("topic_summary", ""),
        target_pain=topic.get("target_pain", ""),
        key_points="、".join(topic.get("key_points", [])),
        main_seconds=main_seconds,
    )

    logger.info(f"台本生成中: {topic.get('title', '')}")

    response = client.messages.create(
        model=cfg["model"],
        max_tokens=4000,
        system=SCRIPT_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()

    # JSON 抽出
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        script_data = json.loads(match.group())
    else:
        logger.error("台本 JSON のパースに失敗しました。生テキストを返します。")
        script_data = {
            "video_title": topic.get("title", "untitled"),
            "video_description": "",
            "tags": [],
            "sections": [{"name": "full", "label": "全文", "duration_sec": total_sec, "text": text}],
            "total_chars": len(text),
            "estimated_duration_min": duration,
        }

    # メタ情報を付加
    script_data["topic"] = topic
    script_data["generated_at"] = datetime.now().isoformat()

    return script_data


def extract_full_text(script_data: dict) -> str:
    """台本データからナレーション全文を抽出（音声合成用）"""
    lines = []
    for section in script_data.get("sections", []):
        lines.append(section["text"])
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(
    topics: list[dict],
    cfg: dict[str, Any],
    api_keys: dict[str, str],
    topic_index: int = 0,
) -> dict:
    """
    台本を生成して保存し、台本データを返す。

    Args:
        topics: collect.py が返したトピックリスト
        cfg: config.yaml の全体設定
        api_keys: {"ANTHROPIC_API_KEY": "..."}
        topic_index: 処理するトピックのインデックス

    Returns:
        台本データ (dict)
    """
    script_cfg = cfg["script"]
    output_dir = Path(cfg["pipeline"]["output_base"]) / "scripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    topic = topics[topic_index]
    safe_title = re.sub(r'[^\w\-]', '_', topic.get("title", "untitled"))[:40]
    today = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"{today}_{safe_title}.json"

    # skip_existing チェック
    if cfg["pipeline"]["skip_existing"] and output_path.exists():
        logger.info(f"既存台本ファイルを使用: {output_path}")
        with open(output_path, encoding="utf-8") as f:
            return json.load(f)

    client = anthropic.Anthropic(api_key=api_keys["ANTHROPIC_API_KEY"])
    script_data = generate_script(topic, script_cfg, client)

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    # 台本テキストも別ファイルで保存（確認用）
    text_path = output_path.with_suffix(".txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"# {script_data.get('video_title', '')}\n\n")
        for section in script_data.get("sections", []):
            f.write(f"## {section['label']} ({section['duration_sec']}秒)\n\n")
            f.write(section["text"] + "\n\n")

    logger.info(f"台本保存完了: {output_path}")
    return script_data
