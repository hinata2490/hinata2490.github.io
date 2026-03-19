"""
Step 4: 映像合成 (FFmpeg)
音声ファイル + 背景画像/動画 + 字幕 を FFmpeg で合成して MP4 を生成する。
"""

import json
import logging
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 字幕ファイル生成 (SRT 形式)
# ---------------------------------------------------------------------------

def text_to_srt(sections: list[dict], max_chars: int = 25) -> str:
    """台本セクションから SRT 字幕ファイルを生成"""
    srt_lines = []
    index = 1
    elapsed = 0.0

    for section in sections:
        text = section["text"]
        duration = float(section.get("duration_sec", 30))

        # テキストを句点・改行で分割して字幕カードに分ける
        sentences = re.split(r'(?<=[。！？\n])', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            continue

        sec_per_sent = duration / max(len(sentences), 1)

        for sent in sentences:
            start = elapsed
            end = elapsed + sec_per_sent

            # 長い文は折り返し
            display = _wrap_text(sent, max_chars)

            srt_lines.append(f"{index}")
            srt_lines.append(f"{_fmt_time(start)} --> {_fmt_time(end)}")
            srt_lines.append(display)
            srt_lines.append("")

            index += 1
            elapsed = end

    return "\n".join(srt_lines)


def _fmt_time(seconds: float) -> str:
    """秒 → SRT タイムコード (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap_text(text: str, max_chars: int) -> str:
    """長いテキストを改行で折り返す"""
    if len(text) <= max_chars:
        return text
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 背景の準備
# ---------------------------------------------------------------------------

def prepare_background(video_cfg: dict, audio_path: Path, tmp_dir: Path) -> Path:
    """背景画像/動画を準備して一時パスを返す"""
    bg_cfg = video_cfg["background"]
    bg_type = bg_cfg.get("type", "gradient")

    if bg_type == "image":
        bg_dir = Path(bg_cfg["dir"])
        imgs = list(bg_dir.glob("*.jpg")) + list(bg_dir.glob("*.png"))
        if imgs:
            return imgs[0]

    if bg_type == "video":
        bg_dir = Path(bg_cfg["dir"])
        vids = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mov"))
        if vids:
            return vids[0]

    # グラデーション背景を生成
    return _generate_gradient_bg(
        colors=bg_cfg.get("default_gradient", {}).get("colors", ["#0a0a2e", "#1a1a4e"]),
        resolution=video_cfg["resolution"],
        tmp_dir=tmp_dir,
    )


def _generate_gradient_bg(colors: list[str], resolution: str, tmp_dir: Path) -> Path:
    """FFmpeg で縦グラデーション背景画像を生成"""
    width, height = resolution.split("x")
    out_path = tmp_dir / "background.png"

    # 2色グラデーション: lavfi の geq フィルタで生成
    c1 = colors[0].lstrip("#")
    c2 = colors[-1].lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)

    geq = (
        f"r='lerp({r1},{r2},Y/{height})':"
        f"g='lerp({g1},{g2},Y/{height})':"
        f"b='lerp({b1},{b2},Y/{height})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=black:size={width}x{height}:rate=1",
        "-vf", f"geq={geq}",
        "-frames:v", "1",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # フォールバック: 単色背景
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=0x0a0a2e:size={width}x{height}:rate=1",
            "-frames:v", "1",
            str(out_path),
        ]
        subprocess.run(cmd, capture_output=True)

    return out_path


# ---------------------------------------------------------------------------
# 映像合成
# ---------------------------------------------------------------------------

def compose_video(
    audio_path: Path,
    bg_path: Path,
    srt_path: Path,
    output_path: Path,
    video_cfg: dict,
) -> Path:
    """FFmpeg で映像を合成する"""
    resolution = video_cfg["resolution"]
    width, height = resolution.split("x")
    fps = video_cfg.get("fps", 30)
    sub_cfg = video_cfg["subtitle"]
    codec = video_cfg.get("codec", "libx264")
    bitrate = video_cfg.get("bitrate", "4000k")

    bg_suffix = bg_path.suffix.lower()
    is_video_bg = bg_suffix in (".mp4", ".mov", ".avi")

    # 字幕フィルタ
    font_path = sub_cfg.get("font", "")
    font_size = sub_cfg.get("font_size", 48)
    text_color = sub_cfg.get("color", "white")
    outline_color = sub_cfg.get("outline_color", "black")
    outline_width = sub_cfg.get("outline_width", 3)

    # SRT パスのエスケープ (Windows 対応)
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    subtitle_filter = (
        f"subtitles='{srt_escaped}'"
        f":force_style='FontSize={font_size}"
        f",PrimaryColour=&H00FFFFFF"
        f",OutlineColour=&H00000000"
        f",Outline={outline_width}"
        f",Alignment=2'"
    )
    if font_path and Path(font_path).exists():
        subtitle_filter += f":fontsdir='{Path(font_path).parent}'"

    if is_video_bg:
        # ループ背景動画
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-shortest",
            "-vf", f"scale={width}:{height},{subtitle_filter}",
            "-c:v", codec, "-b:v", bitrate,
            "-pix_fmt", "yuv420p",
            "-profile:v", "baseline", "-level", "3.1",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            "-movflags", "+faststart",
            str(output_path),
        ]
    else:
        # 静止画背景
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-shortest",
            "-vf", f"scale={width}:{height},{subtitle_filter}",
            "-c:v", codec, "-b:v", bitrate,
            "-pix_fmt", "yuv420p",
            "-profile:v", "baseline", "-level", "3.1",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            "-movflags", "+faststart",
            str(output_path),
        ]

    logger.info("FFmpeg 映像合成を開始...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg エラー:\n{result.stderr[-2000:]}")
        # 字幕なしで再試行
        logger.info("字幕なしで再試行します...")
        cmd_nosub = [c for c in cmd if not c.startswith("subtitles")]
        # vf フィルタから字幕部分を除去
        vf_idx = cmd.index("-vf")
        cmd_nosub = cmd.copy()
        cmd_nosub[vf_idx + 1] = f"scale={width}:{height}"
        result2 = subprocess.run(cmd_nosub, capture_output=True, text=True)
        if result2.returncode != 0:
            raise RuntimeError(f"映像合成失敗: {result2.stderr[-500:]}")

    logger.info(f"映像合成完了: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(
    script_data: dict,
    audio_path: Path,
    cfg: dict[str, Any],
) -> Path:
    """
    映像を合成して保存し、動画ファイルのパスを返す。

    Args:
        script_data: script.py が返した台本データ
        audio_path: audio.py が返した音声ファイルパス
        cfg: config.yaml の全体設定

    Returns:
        生成された動画ファイルのパス
    """
    video_cfg = cfg["video"]
    output_dir = Path(cfg["pipeline"]["output_base"]) / "video"
    output_dir.mkdir(parents=True, exist_ok=True)

    title = script_data.get("video_title", "untitled")
    safe_title = re.sub(r'[^\w\-]', '_', title)[:40]
    today = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"{today}_{safe_title}.mp4"

    # skip_existing チェック
    if cfg["pipeline"]["skip_existing"] and output_path.exists():
        logger.info(f"既存動画ファイルを使用: {output_path}")
        return output_path

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)

        # SRT 字幕生成
        srt_content = text_to_srt(
            sections=script_data.get("sections", []),
            max_chars=video_cfg["subtitle"].get("max_chars_per_line", 25),
        )
        srt_path = tmp_dir / "subtitle.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # 背景準備
        bg_path = prepare_background(video_cfg, audio_path, tmp_dir)

        # 映像合成
        compose_video(
            audio_path=audio_path,
            bg_path=bg_path,
            srt_path=srt_path,
            output_path=output_path,
            video_cfg=video_cfg,
        )

    # 動画メタデータを JSON で保存
    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "video_title": script_data.get("video_title", ""),
            "video_description": script_data.get("video_description", ""),
            "tags": script_data.get("tags", []),
            "video_path": str(output_path),
            "created_at": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    return output_path
