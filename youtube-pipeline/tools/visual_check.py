#!/usr/bin/env python3
"""
画面の比較チェック: 自分の動画とお手本動画のスクショを並べて「違い」だけを出す

テロップ・キャラ配置・余白などを言葉のルールで決めるのではなく、
お手本の画面そのものと見比べて直すためのツール。

使い方:
  1. お手本にしたい動画の画面スクショを learning/references/frames/ に入れる
     （Windows なら Win+Shift+S で撮って保存。3〜6枚くらい）
  2. python tools/visual_check.py
     → Remotion で自分の動画のコマを書き出し、お手本と並べて比較
     → 結果は output/visual_check/report.md に保存

オプション:
  --frames 30,300,900   書き出すコマ番号（30fps なら 30 = 1秒目）
  --images a.png b.png  Remotion を使わず、手元のスクショを比較する
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from steps import learning  # noqa: E402

REMOTION_DIR = BASE_DIR / "remotion"
OUT_DIR = BASE_DIR / "output" / "visual_check"

COMPARE_PROMPT = """\
最初の画像群が「お手本」、後の画像群が「自分の動画」の画面です（どちらも 1920x1080）。

一般的なデザイン論ではなく、お手本と自分の画面を並べたときに実際に違って見える点だけを、
目立つ順に最大8個挙げてください。対象はテロップ（大きさ・太さ・縁取り・位置・行数・帯の有無）、
キャラクター（大きさ・位置・切れ方）、背景、余白、色味です。

各項目は次の形式で書いてください:
- 違い: （何がどう違うか）
  直し方: （Remotion の数値で言うと、例: フォントサイズ 46px → 60px）

最後に「いちばん効く1手」を1行で書いてください。
"""


def render_stills(frames: list[int]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    paths = []
    for f in frames:
        out = OUT_DIR / f"mine_{f:05d}.png"
        print(f"  コマ {f} を書き出し中...")
        subprocess.run(
            [npx, "remotion", "still", "src/index.ts", "SleepVideo", str(out), f"--frame={f}"],
            cwd=REMOTION_DIR, check=True,
        )
        paths.append(out)
    return paths


def main():
    ap = argparse.ArgumentParser(description="お手本と画面を見比べる")
    ap.add_argument("--frames", type=str, default="30,300,900")
    ap.add_argument("--images", nargs="*", help="比較する自分のスクショ")
    args = ap.parse_args()

    refs = learning.load_reference_frames()
    if not refs:
        print("お手本スクショがありません。learning/references/frames/ に画像を入れてください。")
        sys.exit(1)

    if args.images:
        mine = [Path(p) for p in args.images]
    else:
        print("自分の動画のコマを書き出します（Remotion）")
        mine = render_stills([int(x) for x in args.frames.split(",") if x.strip()])

    content: list[dict] = [{"type": "text", "text": "【お手本】"}]
    content += [learning.image_block(p) for p in refs]
    content.append({"type": "text", "text": "【自分の動画】"})
    content += [learning.image_block(p) for p in mine[:6]]
    content.append({"type": "text", "text": COMPARE_PROMPT})

    import anthropic
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
    client = anthropic.Anthropic()
    print("お手本と見比べています...")
    report = learning.call_claude(
        client, learning.DEFAULT_MODEL,
        "あなたは YouTube 解説動画の画面を見比べる編集者です。", content,
        max_tokens=16000,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report.md"
    out.write_text(
        f"# 画面比較レポート ({datetime.now():%Y-%m-%d %H:%M})\n\n"
        f"お手本: {', '.join(p.name for p in refs)}\n"
        f"自分: {', '.join(p.name for p in mine)}\n\n{report}\n",
        encoding="utf-8",
    )
    print("\n" + report)
    print(f"\n保存しました: {out.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
