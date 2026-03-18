"""
Step 5: サムネイル生成 (Pillow)
台本データから YouTube サムネイル画像を生成する。
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 睡眠系絵文字マッピング（タイトルキーワード → 絵文字）
SLEEP_EMOJIS = {
    "不眠": "😴",
    "眠れ": "🌙",
    "快眠": "✨",
    "睡眠": "💤",
    "ぐっすり": "😪",
    "リラックス": "🧘",
    "朝": "🌅",
    "夜": "🌙",
    "ストレス": "😤",
    "呼吸": "🫁",
    "習慣": "📅",
    "方法": "💡",
    "改善": "⬆️",
    "科学": "🔬",
}

DEFAULT_EMOJI = "💤"


def pick_emoji(title: str) -> str:
    """タイトルに合う絵文字を選ぶ"""
    for keyword, emoji in SLEEP_EMOJIS.items():
        if keyword in title:
            return emoji
    return DEFAULT_EMOJI


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def draw_gradient_bg(draw, width: int, height: int, color1: tuple, color2: tuple):
    """縦グラデーション背景を描画"""
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def fit_text_to_width(
    draw,
    text: str,
    font,
    max_width: int,
    max_lines: int = 3,
) -> list[str]:
    """テキストを指定幅に収まるよう折り返す"""
    lines = []
    words = list(text)  # 日本語は1文字ずつ
    current_line = ""

    for char in words:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width and current_line:
            lines.append(current_line)
            current_line = char
            if len(lines) >= max_lines:
                break
        else:
            current_line = test_line

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    return lines


def generate_thumbnail(
    title: str,
    topic_summary: str,
    template_cfg: dict,
    size: tuple[int, int],
    emoji_overlay: bool,
    output_path: Path,
) -> Path:
    """サムネイル画像を生成して保存する"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("Pillow がインストールされていません: pip install Pillow")
        raise

    width, height = size
    img = Image.new("RGB", (width, height), color=tuple(template_cfg["bg_color"]))
    draw = ImageDraw.Draw(img)

    # グラデーション背景
    bg = template_cfg["bg_color"]
    bg2 = [max(0, c - 40) for c in bg]
    draw_gradient_bg(draw, width, height, tuple(bg), tuple(bg2))

    # アクセントライン（左端）
    accent = tuple(template_cfg["accent_color"])
    draw.rectangle([(0, 0), (12, height)], fill=accent)

    # 装飾的な円（右下）
    circle_r = 220
    draw.ellipse(
        [(width - circle_r, height - circle_r), (width + circle_r // 2, height + circle_r // 2)],
        fill=tuple([min(255, c + 30) for c in bg]),
    )

    # フォント読み込み
    font_path = template_cfg.get("font", "")
    title_size = template_cfg.get("title_font_size", 72)
    sub_size = template_cfg.get("subtitle_font_size", 40)

    try:
        if font_path and Path(font_path).exists():
            font_title = ImageFont.truetype(font_path, title_size)
            font_sub = ImageFont.truetype(font_path, sub_size)
            font_emoji = ImageFont.truetype(font_path, title_size + 20)
        else:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_emoji = font_title
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_emoji = font_title

    text_color = tuple(template_cfg.get("text_color", [255, 255, 255]))
    padding_x = 80
    max_text_width = width - padding_x * 2 - 30  # アクセントライン分

    # 絵文字
    if emoji_overlay:
        emoji = pick_emoji(title)
        try:
            draw.text((width - 180, 40), emoji, font=font_emoji, fill=text_color)
        except Exception:
            pass  # 絵文字フォント非対応の場合はスキップ

    # タイトルテキスト描画
    title_lines = fit_text_to_width(draw, title, font_title, max_text_width, max_lines=3)
    y = 120
    for line in title_lines:
        # 影
        draw.text((padding_x + 3, y + 3), line, font=font_title, fill=(0, 0, 0, 180))
        draw.text((padding_x, y), line, font=font_title, fill=text_color)
        bbox = draw.textbbox((0, 0), line, font=font_title)
        y += (bbox[3] - bbox[1]) + 15

    # サブタイトル（topic_summary）
    if topic_summary:
        y += 20
        # アクセントカラーの区切り線
        draw.rectangle([(padding_x, y), (padding_x + 200, y + 4)], fill=accent)
        y += 20

        sub_lines = fit_text_to_width(draw, topic_summary, font_sub, max_text_width, max_lines=2)
        for line in sub_lines:
            sub_color = tuple([min(255, c + 80) for c in template_cfg["accent_color"]])
            draw.text((padding_x + 2, y + 2), line, font=font_sub, fill=(0, 0, 0, 160))
            draw.text((padding_x, y), line, font=font_sub, fill=sub_color)
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            y += (bbox[3] - bbox[1]) + 8

    # チャンネルロゴ風テキスト（右下）
    channel_text = "睡眠改善ラボ"
    try:
        font_channel = ImageFont.truetype(font_path, 32) if font_path and Path(font_path).exists() else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), channel_text, font=font_channel)
        cw = bbox[2] - bbox[0]
        draw.text(
            (width - cw - padding_x, height - 60),
            channel_text,
            font=font_channel,
            fill=(*accent, 220),
        )
    except Exception:
        pass

    # 保存
    img.save(str(output_path), quality=95)
    logger.info(f"サムネイル生成完了: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(
    script_data: dict,
    cfg: dict[str, Any],
) -> Path:
    """
    サムネイルを生成して保存し、画像ファイルのパスを返す。

    Args:
        script_data: script.py が返した台本データ
        cfg: config.yaml の全体設定

    Returns:
        生成されたサムネイル画像のパス
    """
    thumb_cfg = cfg["thumbnail"]
    output_dir = Path(cfg["pipeline"]["output_base"]) / "thumbnails"
    output_dir.mkdir(parents=True, exist_ok=True)

    title = script_data.get("video_title", "untitled")
    topic = script_data.get("topic", {})
    topic_summary = topic.get("topic_summary", "")

    safe_title = re.sub(r'[^\w\-]', '_', title)[:40]
    today = datetime.now().strftime("%Y%m%d")
    ext = thumb_cfg.get("format", "jpg")
    output_path = output_dir / f"{today}_{safe_title}.{ext}"

    # skip_existing チェック
    if cfg["pipeline"]["skip_existing"] and output_path.exists():
        logger.info(f"既存サムネイルを使用: {output_path}")
        return output_path

    template_name = thumb_cfg.get("template", "sleep_dark")
    template_cfg = thumb_cfg["templates"][template_name]

    return generate_thumbnail(
        title=title,
        topic_summary=topic_summary,
        template_cfg=template_cfg,
        size=tuple(thumb_cfg["size"]),
        emoji_overlay=thumb_cfg.get("emoji_overlay", True),
        output_path=output_path,
    )
