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

from steps import learning

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# プロンプトテンプレート
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM = """\
あなたは睡眠特化 YouTube チャンネルの台本ライターです。

## チャンネルコンセプト
- 睡眠不足・眠りが浅い・疲れが取れない20〜30代がメインターゲット
- 語り手は夢乃レム（落ち着いていて、視聴者に寄り添う口調。煽り・強い言葉はNG）
- 科学的根拠に基づいた実践的な情報を提供
- 視聴者が「今夜から試せる」内容を必ず含める
- 親しみやすく、専門的すぎない語り口

## 台本の書き方ルール
- 話し言葉で書く（「〜です」「〜ますよね」等）
- 一文は短く（読み上げで1〜2秒程度）
- 【間】と書いた部分は音声合成で間を取る
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

COMPARE_PROMPT = """\
あなたが書いた台本と、お手本台本を並べて読み比べてください。

手順:
1. 「良い台本の条件」を一般論で考えるのではなく、お手本と自分の台本で
   実際に違っている箇所だけを最大10個挙げる（語り口・一文の長さ・テンポ・
   具体例の出し方・話の運び方など）。過去の修正と同じズレがあればそれも挙げる。
2. その違いを埋めるように台本を書き直す。内容（トピック・科学的事実）は変えない。

出力は次の JSON のみ:
{{
  "differences": ["違い1", "違い2", ...],
  "script": {{ 書き直した台本。元と同じ JSON 形式 }}
}}

## あなたが書いた台本
{draft}
"""


def _parse_json(text: str) -> dict | None:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def build_system_prompt(cfg: dict[str, Any]) -> list[dict]:
    """ルール + お手本の原文 + 過去の修正 を system に積む（キャッシュ対象）"""
    lcfg = learning.learning_cfg(cfg)
    refs = learning.load_reference_scripts(lcfg["max_reference_scripts"])
    corrections = learning.load_corrections(lcfg["max_corrections"])
    logger.info(f"学習データ: お手本台本 {len(refs)} 本 / 修正履歴 {len(corrections)} 件")

    parts = [SCRIPT_SYSTEM]
    persona = cfg.get("script", {}).get("persona")
    if persona:
        parts.append("## 語り手の人物像\n" + persona)
    for block in (learning.build_reference_block(refs), learning.build_corrections_block(corrections)):
        if block:
            parts.append(block)
    return [{"type": "text", "text": "\n\n".join(parts), "cache_control": {"type": "ephemeral"}}]


def generate_script(
    topic: dict,
    cfg: dict[str, Any],
    client: anthropic.Anthropic,
) -> dict:
    """台本を生成する。

    1. お手本台本の原文と過去の修正を見せて下書きを書かせる
    2. お手本と下書きを並べて「違い」だけを挙げさせ、書き直させる
    """
    script_cfg = cfg["script"]
    lcfg = learning.learning_cfg(cfg)
    model = lcfg["model"]
    duration = script_cfg["target_duration_minutes"]
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
    system = build_system_prompt(cfg)

    logger.info(f"台本生成中: {topic.get('title', '')}")
    text = learning.call_claude(client, model, system, user_prompt)
    script_data = _parse_json(text)

    if script_data is None:
        logger.error("台本 JSON のパースに失敗しました。生テキストを返します。")
        return {
            "video_title": topic.get("title", "untitled"),
            "video_description": "",
            "tags": [],
            "sections": [{"name": "full", "label": "全文", "duration_sec": total_sec, "text": text}],
            "total_chars": len(text),
            "estimated_duration_min": duration,
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
        }

    # お手本と並べて比べ、差分だけ埋める
    has_refs = bool(learning.load_reference_scripts(1) or learning.load_corrections(1))
    if lcfg["compare_and_revise"] and has_refs:
        logger.info("お手本と比較して書き直し中...")
        draft = json.dumps(script_data, ensure_ascii=False, indent=2)
        revised_text = learning.call_claude(
            client, model, system, COMPARE_PROMPT.format(draft=draft)
        )
        revised = _parse_json(revised_text)
        if revised and isinstance(revised.get("script"), dict) and revised["script"].get("sections"):
            script_data = revised["script"]
            script_data["revision_differences"] = revised.get("differences", [])
            for d in script_data["revision_differences"]:
                logger.info(f"  修正した違い: {d}")
        else:
            logger.warning("書き直し結果を読めなかったので下書きを使います")

    # メタ情報を付加
    script_data["topic"] = topic
    script_data["generated_at"] = datetime.now().isoformat()

    return script_data


def write_script_txt(script_data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {script_data.get('video_title', '')}\n\n")
        for section in script_data.get("sections", []):
            f.write(f"## {section.get('label', section.get('name', ''))} ({section.get('duration_sec', '?')}秒)\n\n")
            f.write(section["text"] + "\n\n")


def read_script_txt(path: Path) -> list[dict]:
    """write_script_txt で書いた（オーナーが手直しした）.txt を section リストに戻す"""
    sections: list[dict] = []
    current: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(.+?)\s*(?:\((\S+?)秒\))?\s*$", line)
        if m:
            current = {"label": m.group(1), "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    return [
        {"label": s["label"], "text": "\n".join(s["lines"]).strip()}
        for s in sections
    ]


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
    script_data = generate_script(topic, cfg, client)

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    # 台本テキストも別ファイルで保存（確認・手直し用）
    # オーナーはこの .txt を直接直す → tools/relearn.py で修正を学習データにする
    text_path = output_path.with_suffix(".txt")
    write_script_txt(script_data, text_path)

    logger.info(f"台本保存完了: {output_path}")
    return script_data
