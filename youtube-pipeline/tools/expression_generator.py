#!/usr/bin/env python3
"""
夢乃レム 表情差分生成スクリプト

生成する差分:
- 目1/3閉じ  → 夢乃レム_瞬き1.png
- 目全閉じ   → 夢乃レム_瞬き2.png
- 口あき     → 夢乃レム_口あき.png

座標調整方法:
  目がずれている → EYES の cx/cy を変更
  まぶた厚さ    → BLINK1_RATIO / まぶた色 → EYELID_COLOR
  口の位置ずれ  → MOUTH の cx/cy を変更
"""

from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

# ── パス ──────────────────────────────────────────────────────────
BASE_DIR    = r'C:\Users\user\hinata2490.github.io\youtube-pipeline\assets\character'
INPUT_FILE  = os.path.join(BASE_DIR, '夢乃レム　背景透過.png')
OUT_BLINK1  = os.path.join(BASE_DIR, '夢乃レム_瞬き1.png')
OUT_BLINK2  = os.path.join(BASE_DIR, '夢乃レム_瞬き2.png')
OUT_MOUTH   = os.path.join(BASE_DIR, '夢乃レム_口あき.png')

# ── 目のパラメータ（メガネのレンズ内側）──────────────────────────
# スキャン確定値: 左レンズ x=315-445, 右レンズ x=451-605, y=130-222
EYES = [
    # (center_x, center_y, radius_x, radius_y)
    (380, 176, 65, 46),  # 左目（画像左）
    (528, 176, 77, 46),  # 右目（画像右）
]

# ── まぶたの色 ─────────────────────────────────────────────────────
# まぶた（上まぶた）: 顔の肌色に近いピンクベージュ
EYELID_COLOR = (228, 198, 188, 255)
# まつ毛ライン: 目の線と同系統の暗い色
LASH_COLOR   = (60, 45, 55, 255)

# ── 1/3瞬き（0.0〜1.0, 1.0=全閉じ）──────────────────────────────
BLINK1_RATIO = 0.55   # 約半閉じ（アニメ的な1/3閉じ）

# ── 口のパラメータ ─────────────────────────────────────────────────
# スキャン確定値: 唇輪郭 y=262-270, 顔中央 x=450付近
MOUTH = {
    'cx': 450, 'cy': 273,   # 口の中心
    'rx': 38,  'ry': 12,    # 開口部サイズ
}
MOUTH_INNER_COLOR = (90, 35, 40, 255)  # 口内の色（暗い赤茶）


# ── ヘルパー: まぶた用マスク付き楕円を生成 ─────────────────────────
def draw_eyelid(base_img: Image.Image, eye: tuple, close_ratio: float) -> Image.Image:
    """
    close_ratio: 1.0=全閉じ, 0.5=半閉じ
    アイリス楕円の内側だけを肌色で塗る。
    楕円外のピクセルは一切変更しない（メガネフレームが自然に残る）。
    """
    cx, cy, rx, ry = eye
    # アイリスのパラメータ
    iris_cx = cx
    iris_cy = cy + 10       # スキャン確定: 186
    iris_rx = rx - 12       # 左:53, 右:65
    iris_ry = 22            # アイリス縦半径

    iris_top = iris_cy - iris_ry   # ≈ 164
    iris_bot = iris_cy + iris_ry   # ≈ 208

    # まぶた底辺
    lid_bot = int(iris_top + (iris_bot - iris_top) * close_ratio)

    result = base_img.copy()
    arr    = np.array(result)
    orig   = np.array(base_img)

    # ── 1. アイリス楕円内かつ y<=lid_bot のピクセルのみ塗る ──────────
    for y in range(iris_top, lid_bot + 1):
        dy = y - iris_cy
        if abs(dy) > iris_ry:
            continue
        half_w = int(iris_rx * (1 - (dy / iris_ry) ** 2) ** 0.5)
        x0 = max(0, iris_cx - half_w)
        x1 = min(arr.shape[1] - 1, iris_cx + half_w)
        for x in range(x0, x1 + 1):
            # 楕円内かどうかを数式で確認（念のため）
            if ((x - iris_cx) / iris_rx) ** 2 + ((y - iris_cy) / iris_ry) ** 2 <= 1.0:
                arr[y, x] = EYELID_COLOR

    # ── 2. まつ毛ライン（lid_bot の楕円弧に沿って）─────────────────
    lash_y = lid_bot
    dy = lash_y - iris_cy
    if abs(dy) <= iris_ry and close_ratio > 0.1:
        half_w = int(iris_rx * (1 - (dy / iris_ry) ** 2) ** 0.5)
        for lx in range(max(0, iris_cx - half_w), min(arr.shape[1], iris_cx + half_w + 1)):
            for thick in range(3):
                yy = lash_y + thick
                if 0 <= yy < arr.shape[0]:
                    # まつ毛も楕円内のみ
                    if ((lx - iris_cx) / iris_rx) ** 2 + ((yy - iris_cy) / iris_ry) ** 2 <= 1.2:
                        arr[yy, lx] = LASH_COLOR

    return Image.fromarray(arr)


def draw_mouth_open(base_img: Image.Image, mouth: dict) -> Image.Image:
    """口を少し開いた状態にする"""
    cx = mouth['cx']
    cy = mouth['cy']
    rx = mouth['rx']
    ry = mouth['ry']

    result = base_img.copy()
    arr    = np.array(result)

    # 口の内側を暗い楕円で塗る
    for y in range(cy - ry, cy + ry + 1):
        dy = y - cy
        if abs(dy) > ry:
            continue
        dx = int(rx * (1 - (dy / ry) ** 2) ** 0.5)
        x0 = cx - dx
        x1 = cx + dx
        for x in range(x0, x1 + 1):
            if 0 <= x < arr.shape[1] and 0 <= y < arr.shape[0]:
                r, g, b, a = arr[y, x]
                if r > 248 and g > 248 and b > 248:
                    continue  # 背景は塗らない
                # 上唇部分は暗い口内色、下はほぼ消えるよう
                depth = abs(dy) / ry
                inner_r = int(MOUTH_INNER_COLOR[0] * (1 - depth) + r * depth)
                inner_g = int(MOUTH_INNER_COLOR[1] * (1 - depth) + g * depth)
                inner_b = int(MOUTH_INNER_COLOR[2] * (1 - depth) + b * depth)
                arr[y, x] = (inner_r, inner_g, inner_b, 255)

    return Image.fromarray(arr)


def main():
    print("画像を読み込み中...")
    img = Image.open(INPUT_FILE).convert('RGBA')
    print(f"サイズ: {img.size}")

    # ── 1. 目1/3閉じ ──────────────────────────────────────────────
    print("目1/3閉じ を生成中...")
    img1 = img.copy()
    for eye in EYES:
        img1 = draw_eyelid(img1, eye, BLINK1_RATIO)
    img1.save(OUT_BLINK1)
    print(f"  保存: {OUT_BLINK1}")

    # ── 2. 目全閉じ ───────────────────────────────────────────────
    print("目全閉じ を生成中...")
    img2 = img.copy()
    for eye in EYES:
        img2 = draw_eyelid(img2, eye, 1.0)
    img2.save(OUT_BLINK2)
    print(f"  保存: {OUT_BLINK2}")

    # ── 3. 口あき ─────────────────────────────────────────────────
    print("口あき を生成中...")
    img3 = img.copy()
    img3 = draw_mouth_open(img3, MOUTH)
    img3.save(OUT_MOUTH)
    print(f"  保存: {OUT_MOUTH}")

    print("\n完了！")
    print("見た目がずれている場合:")
    print("  目  → EYES の cx/cy/rx/ry を調整")
    print("  口  → MOUTH の cx/cy/rx/ry を調整")


if __name__ == '__main__':
    main()
