#!/usr/bin/env python3
"""
巷の動画を自分で探して学習する（「学習して」のときに Claude Code が実行する）

YouTube を検索して、再生数の多いゆっくり系・合成音声系の解説動画を何本も選び、
それぞれの 台本原文・画面コマ・編集テンポ を learning/references/ に取り込む。
オーナーは何も渡さなくてよい。一度見た動画はスキップするので、何度実行しても新しい動画を学ぶ。

使い方:
  python tools/discover_references.py              # config の検索語で 8本
  python tools/discover_references.py --count 15
  python tools/discover_references.py --query "ゆっくり解説 雑学"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "tools"))

from steps import learning  # noqa: E402
from fetch_reference import run_ytdlp, from_youtube  # noqa: E402

INDEX_PATH = learning.LEARNING_DIR / "references" / "index.json"

DEFAULT_QUERIES = [
    "ゆっくり解説 睡眠",
    "ゆっくり解説 健康",
    "ずんだもん 解説 睡眠",
    "ゆっくり解説 雑学",
    "ずんだもん 解説",
]


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"videos": {}}


def save_index(idx: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def search(query: str, n: int) -> list[dict]:
    r = run_ytdlp(["--flat-playlist", "-J", f"ytsearch{n}:{query}"], check=False)
    if r.returncode != 0:
        print(f"  検索失敗: {query}")
        return []
    entries = json.loads(r.stdout).get("entries") or []
    return [e for e in entries if e and e.get("id")]


def main():
    cfg = yaml.safe_load((BASE_DIR / "config.yaml").read_text(encoding="utf-8"))
    dcfg = (cfg.get("learning") or {}).get("discover") or {}

    ap = argparse.ArgumentParser(description="巷の動画を探して学習する")
    ap.add_argument("--count", type=int, default=dcfg.get("count", 8), help="新しく学ぶ本数")
    ap.add_argument("--query", action="append", help="検索語（複数可。省略時は config）")
    ap.add_argument("--frames", type=int, default=6, help="1本あたりの画面コマ数")
    args = ap.parse_args()

    queries = args.query or dcfg.get("queries") or DEFAULT_QUERIES
    min_min, max_min = dcfg.get("min_minutes", 5), dcfg.get("max_minutes", 30)
    idx = load_index()

    # 候補を集めて再生数順に並べる
    print("YouTube を検索中...")
    candidates: dict[str, dict] = {}
    for q in queries:
        for e in search(q, dcfg.get("per_query", 20)):
            dur = e.get("duration") or 0
            if e["id"] in idx["videos"] or not (min_min * 60 <= dur <= max_min * 60):
                continue
            e["_query"] = q
            candidates.setdefault(e["id"], e)
    ranked = sorted(candidates.values(), key=lambda e: e.get("view_count") or 0, reverse=True)
    print(f"未学習の候補 {len(ranked)} 本 → 再生数の多い順に {args.count} 本を見ます\n")

    learned = 0
    for e in ranked:
        if learned >= args.count:
            break
        url = f"https://www.youtube.com/watch?v={e['id']}"
        views = e.get("view_count") or 0
        print(f"[{learned + 1}/{args.count}] {e.get('title', '')}（{views:,}回再生）")
        try:
            name = from_youtube(url, None, args.frames, info=e)
        except Exception as ex:  # 1本失敗しても続ける
            print(f"  スキップ: {ex}")
            continue
        idx["videos"][e["id"]] = {
            "name": name, "title": e.get("title"), "views": views,
            "query": e["_query"], "learned_at": datetime.now().isoformat(),
        }
        save_index(idx)
        learned += 1

    total = len(idx["videos"])
    print(f"\n完了: 今回 {learned} 本を学習（累計 {total} 本）")
    if learned == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
