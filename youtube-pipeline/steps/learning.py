"""
学習データ（体験ライブラリ）の読み込み

方針: 「良い動画とは何か」を言葉のルールで教えるのではなく、
  1. お手本の実物（台本の原文・画面のスクショ）をそのまま見せる
  2. 生成物とお手本を並べて「違い」だけを言わせる
  3. オーナーが直した差分（修正前 → 修正後）を貯めて、次回の生成に見せる
ことで、圧縮（言語化）でこぼれる部分を残したまま学習させる。

ディレクトリ構成 (youtube-pipeline/learning/):
  references/scripts/*.txt   お手本台本（原文そのまま。要約しない）
  references/frames/*.png    お手本動画の画面スクショ（jpg/png）
  corrections/*.json         オーナーの修正ペア（tools/relearn.py が自動で作る）
"""

import base64
import json
import logging
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
LEARNING_DIR = BASE_DIR / "learning"
REF_SCRIPTS_DIR = LEARNING_DIR / "references" / "scripts"
REF_FRAMES_DIR = LEARNING_DIR / "references" / "frames"
CORRECTIONS_DIR = LEARNING_DIR / "corrections"

DEFAULT_MODEL = "claude-opus-5-5"


# ---------------------------------------------------------------------------
# 読み込み
# ---------------------------------------------------------------------------

def load_reference_scripts(max_items: int = 5) -> list[dict]:
    """お手本台本を原文のまま読み込む（README.md 等は除外）"""
    if not REF_SCRIPTS_DIR.exists():
        return []
    # オーナーの手直し済み台本 → 再生数の多い巷の動画 の順に優先
    views = {}
    index_path = LEARNING_DIR / "references" / "index.json"
    if index_path.exists():
        for v in json.loads(index_path.read_text(encoding="utf-8")).get("videos", {}).values():
            views[v.get("name")] = v.get("views") or 0
    files = sorted(
        REF_SCRIPTS_DIR.glob("*.txt"),
        key=lambda p: (p.stem in views, -views.get(p.stem, 0)),
    )
    items = []
    for p in files[:max_items]:
        text = p.read_text(encoding="utf-8").strip()
        if text:
            items.append({"name": p.stem, "text": text})
    return items


def load_reference_frames(max_items: int = 6) -> list[Path]:
    if not REF_FRAMES_DIR.exists():
        return []
    frames = [
        p for p in sorted(REF_FRAMES_DIR.iterdir())
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    ]
    return frames[:max_items]


def load_corrections(max_items: int = 8) -> list[dict]:
    """新しい順に修正ペアを読み込む"""
    if not CORRECTIONS_DIR.exists():
        return []
    files = sorted(CORRECTIONS_DIR.glob("*.json"), reverse=True)[:max_items]
    out = []
    for p in files:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            logger.warning(f"修正データを読めませんでした: {p}")
    return out


# ---------------------------------------------------------------------------
# プロンプト用ブロック
# ---------------------------------------------------------------------------

def build_reference_block(refs: list[dict]) -> str:
    if not refs:
        return ""
    parts = [
        "## お手本台本（原文）",
        "以下はオーナーが「良い」と判断した台本の原文です。ルールに要約せず、"
        "語り口・テンポ・一文の長さ・話の運び方を、そのまま体に入れるつもりで読んでください。",
    ]
    for r in refs:
        parts.append(f'<reference name="{r["name"]}">\n{r["text"]}\n</reference>')
    return "\n\n".join(parts)


def build_corrections_block(corrections: list[dict]) -> str:
    if not corrections:
        return ""
    parts = [
        "## 過去の修正（オーナーが直した箇所）",
        "AIが書いた文（before）をオーナーが直した結果（after）です。"
        "同じ種類のズレを繰り返さないでください。",
    ]
    for c in corrections:
        for d in c.get("diffs", [])[:10]:
            parts.append(
                f"<correction>\nbefore: {d['before']}\nafter: {d['after']}\n</correction>"
            )
        if c.get("lessons"):
            parts.append("この時の気づき: " + " / ".join(c["lessons"]))
    return "\n\n".join(parts)


def image_block(path: Path) -> dict:
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


# ---------------------------------------------------------------------------
# Claude 呼び出し共通
# ---------------------------------------------------------------------------

def call_claude(
    client: anthropic.Anthropic,
    model: str,
    system: list[dict] | str,
    content: list[dict] | str,
    max_tokens: int = 32000,
    effort: str = "high",
) -> str:
    """テキスト部分だけを返す。拒否されたときは例外にする。

    長い入出力になるのでストリーミングで受け取る。
    拒否時は別モデルで自動再実行されるよう server-side fallback を有効化している。
    """
    with client.beta.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude がこのリクエストを処理できませんでした（refusal）")
    if response.stop_reason == "max_tokens":
        logger.warning("出力が max_tokens で切れました")

    return "".join(b.text for b in response.content if b.type == "text").strip()


def learning_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": DEFAULT_MODEL,
        "compare_and_revise": True,
        "max_reference_scripts": 5,
        "max_corrections": 8,
        **(cfg.get("learning") or {}),
    }
