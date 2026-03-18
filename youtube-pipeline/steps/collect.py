"""
Step 1: ネタ収集
RSSフィード・キーワードから睡眠コンテンツのネタを収集し、
Claude で要約・優先度付けして保存する。
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import feedparser
import requests
import anthropic

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RSS収集
# ---------------------------------------------------------------------------

def fetch_rss(url: str, label: str, max_items: int = 10) -> list[dict]:
    """RSSフィードを取得して記事リストを返す"""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "source": label,
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:500],
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        logger.info(f"RSS [{label}]: {len(items)} 件取得")
        return items
    except Exception as e:
        logger.warning(f"RSS取得失敗 [{label}]: {e}")
        return []


# ---------------------------------------------------------------------------
# YouTube トレンド収集 (YouTube Data API)
# ---------------------------------------------------------------------------

def fetch_youtube_trends(api_key: str, keywords: list[str], max_results: int = 10) -> list[dict]:
    """YouTube で睡眠系キーワードの人気動画を取得"""
    if not api_key:
        logger.warning("YOUTUBE_API_KEY が未設定のため YouTube トレンド収集をスキップ")
        return []

    items = []
    for kw in keywords[:3]:  # APIクォータ節約のため最大3キーワード
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": kw,
                "type": "video",
                "order": "viewCount",
                "regionCode": "JP",
                "relevanceLanguage": "ja",
                "maxResults": max_results // 3,
                "key": api_key,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                snippet = item["snippet"]
                items.append({
                    "source": f"YouTube [{kw}]",
                    "title": snippet.get("title", ""),
                    "summary": snippet.get("description", "")[:300],
                    "link": f"https://youtu.be/{item['id']['videoId']}",
                    "published": snippet.get("publishedAt", ""),
                })
        except Exception as e:
            logger.warning(f"YouTube トレンド取得失敗 [{kw}]: {e}")

    logger.info(f"YouTube トレンド: {len(items)} 件取得")
    return items


# ---------------------------------------------------------------------------
# Claude によるネタ優先度付け・アイデア化
# ---------------------------------------------------------------------------

PRIORITIZE_PROMPT = """\
あなたは睡眠特化YouTubeチャンネルのコンテンツプランナーです。

以下の収集した睡眠関連情報から、動画ネタとして優れた候補を選び、
**視聴者にとって価値が高い順**に最大 {max_topics} 件を JSON 形式で返してください。

## 評価基準
- 検索需要が高そうか（不眠・睡眠改善・快眠など）
- 視聴者の悩みに直結するか
- 具体的なTipsを含む動画にできるか
- 競合動画と差別化できるか

## 収集情報
{raw_items}

## 出力形式 (JSON配列のみ、コードブロック不要)
[
  {{
    "rank": 1,
    "title": "動画タイトル案（クリックされやすい）",
    "topic_summary": "このネタの概要（50字以内）",
    "target_pain": "ターゲットが抱える悩み",
    "key_points": ["ポイント1", "ポイント2", "ポイント3"],
    "estimated_search_demand": "高/中/低",
    "source_ref": "参考にした情報のタイトル"
  }}
]
"""


def prioritize_topics(
    raw_items: list[dict],
    max_topics: int,
    client: anthropic.Anthropic,
    model: str,
) -> list[dict]:
    """Claude でネタを評価・優先度付け"""
    if not raw_items:
        logger.warning("収集アイテムが空のためデフォルトネタを返します")
        return _default_topics()

    items_text = "\n".join(
        f"- [{i['source']}] {i['title']}: {i['summary']}"
        for i in raw_items[:30]  # トークン節約
    )

    prompt = PRIORITIZE_PROMPT.format(
        max_topics=max_topics,
        raw_items=items_text,
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # JSON 部分だけ抽出
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            topics = json.loads(match.group())
            logger.info(f"Claude によるネタ選定: {len(topics)} 件")
            return topics
    except Exception as e:
        logger.error(f"Claude ネタ選定失敗: {e}")

    return _default_topics()


def _default_topics() -> list[dict]:
    """API が使えない場合のデフォルトネタリスト"""
    return [
        {
            "rank": 1,
            "title": "【医師監修】不眠症を根本から治す7つの習慣",
            "topic_summary": "不眠の原因別対策と生活習慣改善",
            "target_pain": "何年も眠れなくて困っている",
            "key_points": ["睡眠衛生", "認知行動療法", "睡眠スケジュール"],
            "estimated_search_demand": "高",
            "source_ref": "default",
        },
        {
            "rank": 2,
            "title": "寝る前10分でぐっすり眠れる！最強リラックス法",
            "topic_summary": "就寝前ルーティンの科学的アプローチ",
            "target_pain": "なかなか寝付けない",
            "key_points": ["呼吸法", "ストレッチ", "デジタルデトックス"],
            "estimated_search_demand": "高",
            "source_ref": "default",
        },
    ]


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(cfg: dict[str, Any], api_keys: dict[str, str]) -> list[dict]:
    """
    ネタ収集を実行し、優先度付きトピックリストを返す。

    Args:
        cfg: config.yaml の全体設定
        api_keys: {"ANTHROPIC_API_KEY": "...", "YOUTUBE_API_KEY": "..."}

    Returns:
        優先度付きトピックリスト
    """
    collect_cfg = cfg["collect"]
    script_cfg = cfg["script"]
    output_dir = Path(cfg["pipeline"]["output_base"]) / "topics"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 既存ファイルを確認（skip_existing）
    today = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"topics_{today}.json"
    if cfg["pipeline"]["skip_existing"] and output_path.exists():
        logger.info(f"既存トピックファイルを使用: {output_path}")
        with open(output_path) as f:
            return json.load(f)

    # RSS収集
    raw_items: list[dict] = []
    for rss_src in collect_cfg["sources"].get("rss", []):
        raw_items.extend(fetch_rss(rss_src["url"], rss_src["label"]))

    # YouTube トレンド
    if collect_cfg["sources"]["youtube_trends"]["enabled"]:
        raw_items.extend(
            fetch_youtube_trends(
                api_key=api_keys.get("YOUTUBE_API_KEY", ""),
                keywords=collect_cfg["sources"]["keywords"],
                max_results=collect_cfg["sources"]["youtube_trends"]["max_results"],
            )
        )

    # Claude でネタ選定・優先度付け
    client = anthropic.Anthropic(api_key=api_keys["ANTHROPIC_API_KEY"])
    topics = prioritize_topics(
        raw_items=raw_items,
        max_topics=collect_cfg["max_topics_per_run"],
        client=client,
        model=script_cfg["model"],
    )

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    logger.info(f"トピック保存完了: {output_path}")

    return topics
