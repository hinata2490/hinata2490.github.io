#!/usr/bin/env python3
"""
睡眠チャンネル YouTube 自動化パイプライン
=========================================

使い方:
    # 全ステップを実行
    python pipeline.py

    # 特定ステップから再開 (例: 音声生成から)
    python pipeline.py --from-step audio

    # 特定トピックインデックスを指定
    python pipeline.py --topic 2

    # ドライランで動作確認
    python pipeline.py --dry-run

    # 台本のみ生成・確認してから続ける
    python pipeline.py --stop-after script
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# ステップモジュール
from steps import collect, script, audio, video, thumbnail, upload

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"

STEPS_ORDER = ["collect", "script", "audio", "video", "thumbnail", "upload"]
STEP_LABELS = {
    "collect": "Step 1: ネタ収集",
    "script": "Step 2: 台本生成",
    "audio": "Step 3: 音声生成",
    "video": "Step 4: 映像合成",
    "thumbnail": "Step 5: サムネイル生成",
    "upload": "Step 6: YouTube アップロード",
}


def load_config(dry_run: bool = False) -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if dry_run:
        cfg["pipeline"]["dry_run"] = True
    return cfg


def load_api_keys() -> dict[str, str]:
    load_dotenv(BASE_DIR / ".env")
    keys = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
    }
    if not keys["ANTHROPIC_API_KEY"]:
        raise ValueError(
            "ANTHROPIC_API_KEY が設定されていません。\n"
            ".env ファイルに ANTHROPIC_API_KEY=sk-ant-... を追加してください。"
        )
    return keys


def setup_logging(cfg: dict[str, Any]):
    log_dir = Path(cfg["pipeline"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    level = getattr(logging, cfg["pipeline"].get("log_level", "INFO"))
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# パイプライン実行
# ---------------------------------------------------------------------------

def run_pipeline(
    cfg: dict[str, Any],
    api_keys: dict[str, str],
    topic_index: int = 0,
    from_step: str = "collect",
    stop_after: str | None = None,
    state_path: Path | None = None,
) -> dict:
    """
    パイプライン全体を実行する。

    state_path を指定すると、途中状態を JSON で保存・再開できる。
    """
    logger = logging.getLogger("pipeline")

    # 状態の読み込み（再開時）
    state: dict = {}
    if state_path and state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
        logger.info(f"前回の状態を復元: {state_path}")

    def save_state():
        if state_path:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

    def should_run(step: str) -> bool:
        idx_from = STEPS_ORDER.index(from_step)
        idx_step = STEPS_ORDER.index(step)
        return idx_step >= idx_from

    # ---- Step 1: ネタ収集 ----
    if should_run("collect"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["collect"])
        logger.info('='*50)
        topics = collect.run(cfg, api_keys)
        state["topics"] = topics
        state["topic_index"] = topic_index
        save_state()
    else:
        topics = state.get("topics", [])

    if not topics:
        raise ValueError("トピックが収集できませんでした")

    selected_topic = topics[min(topic_index, len(topics) - 1)]
    logger.info(f"選択トピック: {selected_topic.get('title', '')}")

    if stop_after == "collect":
        logger.info("collect ステップで停止します")
        _print_topics(topics)
        return state

    # ---- Step 2: 台本生成 ----
    if should_run("script"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["script"])
        logger.info('='*50)
        script_data = script.run(topics, cfg, api_keys, topic_index)
        state["script_path"] = str(
            Path(cfg["pipeline"]["output_base"]) / "scripts" /
            f"{datetime.now().strftime('%Y%m%d')}_{selected_topic.get('title', 'untitled')[:40]}.json"
        )
        state["script_data"] = script_data
        save_state()
        logger.info(f"台本タイトル: {script_data.get('video_title', '')}")
    else:
        script_data = state.get("script_data", {})

    if stop_after == "script":
        logger.info("\n台本生成で停止します。台本を確認してから続行してください。")
        _print_script_summary(script_data)
        logger.info(f"\n続行するには: python pipeline.py --from-step audio")
        return state

    # ---- Step 3: 音声生成 ----
    if should_run("audio"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["audio"])
        logger.info('='*50)
        audio_path = audio.run(script_data, cfg, api_keys)
        state["audio_path"] = str(audio_path)
        save_state()
    else:
        audio_path = Path(state["audio_path"])

    if stop_after == "audio":
        logger.info("audio ステップで停止します")
        return state

    # ---- Step 4: 映像合成 ----
    if should_run("video"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["video"])
        logger.info('='*50)
        video_path = video.run(script_data, audio_path, cfg)
        state["video_path"] = str(video_path)
        save_state()
    else:
        video_path = Path(state["video_path"])

    if stop_after == "video":
        logger.info("video ステップで停止します")
        return state

    # ---- Step 5: サムネイル生成 ----
    if should_run("thumbnail"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["thumbnail"])
        logger.info('='*50)
        thumbnail_path = thumbnail.run(script_data, cfg)
        state["thumbnail_path"] = str(thumbnail_path)
        save_state()
    else:
        thumbnail_path = Path(state["thumbnail_path"])

    if stop_after == "thumbnail":
        logger.info("thumbnail ステップで停止します")
        return state

    # ---- Step 6: YouTube アップロード ----
    if should_run("upload"):
        logger.info(f"\n{'='*50}")
        logger.info(STEP_LABELS["upload"])
        logger.info('='*50)
        result = upload.run(script_data, video_path, thumbnail_path, cfg)
        state["upload_result"] = result
        save_state()
    else:
        result = state.get("upload_result", {})

    # 完了サマリー
    logger.info(f"\n{'='*50}")
    logger.info("パイプライン完了!")
    logger.info('='*50)
    if result:
        logger.info(f"動画 URL: {result.get('url', '')}")
        if result.get("publish_at"):
            logger.info(f"公開予定: {result['publish_at']}")

    return state


def _print_topics(topics: list[dict]):
    print("\n== 収集トピック一覧 ==")
    for i, t in enumerate(topics):
        demand = t.get("estimated_search_demand", "?")
        print(f"[{i}] ({demand}) {t.get('title', '')}")
        print(f"     {t.get('topic_summary', '')}")


def _print_script_summary(script_data: dict):
    print(f"\n== 台本サマリー ==")
    print(f"タイトル: {script_data.get('video_title', '')}")
    print(f"推定時間: {script_data.get('estimated_duration_min', '?')} 分")
    print(f"説明欄: {script_data.get('video_description', '')[:100]}...")
    print(f"タグ: {', '.join(script_data.get('tags', [])[:5])}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="睡眠チャンネル YouTube 自動化パイプライン",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--topic", type=int, default=0,
        help="処理するトピックのインデックス (デフォルト: 0)",
    )
    parser.add_argument(
        "--from-step",
        choices=STEPS_ORDER,
        default="collect",
        help="このステップから実行を開始する",
    )
    parser.add_argument(
        "--stop-after",
        choices=STEPS_ORDER,
        default=None,
        help="このステップの後に停止する",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="実際の API 呼び出しをスキップして動作確認",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="output/pipeline_state.json",
        help="ステート保存ファイルパス",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        cfg = load_config(dry_run=args.dry_run)
        setup_logging(cfg)
        api_keys = load_api_keys()
    except Exception as e:
        print(f"設定エラー: {e}", file=sys.stderr)
        sys.exit(1)

    state_path = BASE_DIR / args.state_file

    try:
        run_pipeline(
            cfg=cfg,
            api_keys=api_keys,
            topic_index=args.topic,
            from_step=args.from_step,
            stop_after=args.stop_after,
            state_path=state_path,
        )
    except KeyboardInterrupt:
        print("\n中断されました。--from-step オプションで再開できます。")
        sys.exit(0)
    except Exception as e:
        logging.getLogger("pipeline").error(f"パイプラインエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
