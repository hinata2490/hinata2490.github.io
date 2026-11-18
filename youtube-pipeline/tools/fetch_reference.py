#!/usr/bin/env python3
"""
お手本の取り込み（Claude Code が「学習して」のときに自動で使う）

YouTube の URL、または手元の動画ファイルから
  - 台本（字幕の原文をそのまま）→ learning/references/scripts/<名前>.txt
  - 画面のコマ（等間隔に数枚）  → learning/references/frames/<名前>_NN.jpg
を作る。要約や言語化はしない（原文・原画像のまま保存する）。

使い方:
  python tools/fetch_reference.py https://www.youtube.com/watch?v=xxxx
  python tools/fetch_reference.py C:\\Users\\user\\Videos\\sample.mp4
  python tools/fetch_reference.py <URL> --frames 8 --name お手本A
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from steps import learning  # noqa: E402

# Windows で FFmpeg が PATH に無い場合の既定インストール先（winget）
_WIN_FFMPEG_GLOB = "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin"


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for d in sorted(Path.home().glob(_WIN_FFMPEG_GLOB), reverse=True):
        exe = d / f"{name}.exe"
        if exe.exists():
            return str(exe)
    sys.exit(f"{name} が見つかりません。FFmpeg をインストールしてください。")


METRICS_DIR = learning.LEARNING_DIR / "references" / "metrics"


def run_ytdlp(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """yt-dlp を実行。YouTube 用の JS 実行環境として Node.js を使う（無い版では外して再実行）"""
    base = [sys.executable, "-m", "yt_dlp", "--no-warnings"]
    r = subprocess.run(base + ["--js-runtimes", "node"] + args, capture_output=True, text=True)
    if r.returncode != 0 and "js-runtimes" in (r.stderr or ""):
        r = subprocess.run(base + args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"yt-dlp 失敗: {(r.stderr or '').strip()[-500:]}")
    return r


def _ts(t: str) -> float:
    parts = t.replace(",", ".").split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(parts)))


def vtt_cues(vtt: str) -> list[tuple[float, float, str]]:
    cues, cur = [], None
    for line in vtt.splitlines():
        m = re.match(r"^\s*([\d:.,]+)\s*-->\s*([\d:.,]+)", line)
        if m:
            cur = [_ts(m.group(1)), _ts(m.group(2)), ""]
            cues.append(cur)
        elif cur is not None and line.strip():
            cur[2] += re.sub(r"<[^>]+>", "", line.strip())
    return [(a, b, t) for a, b, t in cues if t and b > a]


def edit_metrics(video: Path, vtt: str | None = None, max_sec: int = 300) -> dict:
    """編集テンポを数値で測る（言語化ではなく測定値）。冒頭 max_sec 秒が対象。"""
    dur = duration_sec(video)
    span = min(dur, max_sec)
    r = subprocess.run(
        [_tool("ffmpeg"), "-hide_banner", "-t", str(span), "-i", str(video),
         "-vf", "scale=320:-2,select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    gaps = [b - a for a, b in zip([0.0] + cuts, cuts + [span])]
    m = {
        "duration_sec": round(dur, 1),
        "measured_sec": round(span, 1),
        "screen_changes_per_min": round(len(cuts) / span * 60, 1) if span else 0,
        "median_sec_between_changes": round(sorted(gaps)[len(gaps) // 2], 2) if gaps else None,
    }
    if vtt:
        cues = vtt_cues(vtt)
        if cues:
            durs = sorted(b - a for a, b, _ in cues)
            chars = [len(t) for _, _, t in cues]
            m.update({
                "subtitle_cues": len(cues),
                "median_subtitle_sec": round(durs[len(durs) // 2], 2),
                "median_subtitle_chars": sorted(chars)[len(chars) // 2],
                "chars_per_sec": round(sum(chars) / max(sum(durs), 0.1), 1),
            })
    return m


def save_metrics(name: str, metrics: dict, extra: dict | None = None) -> Path:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    out = METRICS_DIR / f"{name}.json"
    out.write_text(json.dumps({**(extra or {}), **metrics}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")[:40] or "reference"


def vtt_to_text(vtt: str) -> str:
    """字幕ファイル(VTT)から時刻・タグを除き、重複行をまとめて原文に戻す"""
    lines, prev = [], None
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        if line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return "\n".join(lines)


def duration_sec(video: Path) -> float:
    out = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def extract_frames(video: Path, name: str, n: int) -> list[Path]:
    learning.REF_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    dur = duration_sec(video)
    outs = []
    for i in range(n):
        t = dur * (i + 1) / (n + 1)  # 冒頭・末尾を避けて等間隔
        out = learning.REF_FRAMES_DIR / f"{name}_{i + 1:02d}.jpg"
        subprocess.run(
            [_tool("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
             "-frames:v", "1", "-vf", "scale=1920:-2", "-q:v", "2", str(out)],
            check=True,
        )
        outs.append(out)
    return outs


def from_youtube(url: str, name: str | None, n_frames: int, info: dict | None = None) -> str:
    """URL の動画から 台本原文・画面コマ・編集テンポ を取り込む。保存名を返す。"""
    tmp = Path(tempfile.mkdtemp(prefix="ref_"))
    try:
        if info is None:
            info = json.loads(run_ytdlp(["-J", url]).stdout)
        name = name or safe_name(info.get("title", "reference"))

        # 字幕（手動字幕 → 自動字幕の順）
        run_ytdlp(["--skip-download", "--write-subs", "--write-auto-subs",
                   "--sub-langs", "ja.*,ja", "--sub-format", "vtt",
                   "-o", str(tmp / "sub"), url], check=False)
        vtts = sorted(tmp.glob("sub*.vtt"))
        vtt_raw = vtts[0].read_text(encoding="utf-8") if vtts else None
        if vtt_raw:
            text = vtt_to_text(vtt_raw)
            learning.REF_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
            out = learning.REF_SCRIPTS_DIR / f"{name}.txt"
            out.write_text(text + "\n", encoding="utf-8")
            print(f"  台本: {len(text)}文字")
        else:
            print("  日本語字幕なし（画面と編集テンポだけ取り込みます）")

        # 動画（720p 以下）→ 画面コマ + 編集テンポ
        run_ytdlp(["-f", "bv*[height<=720][ext=mp4]/bv*[height<=720]/b[height<=720]/b",
                   "-o", str(tmp / "video.%(ext)s"), url])
        video = next(p for p in tmp.glob("video.*") if p.suffix != ".part")
        frames = extract_frames(video, name, n_frames)
        metrics = edit_metrics(video, vtt_raw)
        save_metrics(name, metrics, {
            "url": url, "title": info.get("title"), "channel": info.get("channel"),
            "view_count": info.get("view_count"),
        })
        print(f"  画面: {len(frames)}枚 / 画面切替 {metrics['screen_changes_per_min']}回/分")
        return name
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def from_file(path: Path, name: str | None, n_frames: int) -> None:
    name = name or safe_name(path.stem)
    if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        learning.REF_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        dst = learning.REF_FRAMES_DIR / f"{name}{path.suffix.lower()}"
        shutil.copy(path, dst)
        print(f"画面を保存: {dst.relative_to(BASE_DIR)}")
    elif path.suffix.lower() in (".txt", ".srt", ".vtt"):
        raw = path.read_text(encoding="utf-8")
        text = vtt_to_text(raw) if path.suffix.lower() != ".txt" else raw
        learning.REF_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        dst = learning.REF_SCRIPTS_DIR / f"{name}.txt"
        dst.write_text(text.strip() + "\n", encoding="utf-8")
        print(f"台本を保存: {dst.relative_to(BASE_DIR)}")
    else:
        frames = extract_frames(path, name, n_frames)
        print(f"画面を保存: {len(frames)}枚")


def main():
    ap = argparse.ArgumentParser(description="お手本を取り込む")
    ap.add_argument("source", help="YouTube URL または ファイルパス")
    ap.add_argument("--metrics", action="store_true",
                    help="取り込まずに、その動画の編集テンポだけ測って表示（自分の動画の確認用）")
    ap.add_argument("--name", help="保存名")
    ap.add_argument("--frames", type=int, default=6, help="抜き出すコマ数")
    args = ap.parse_args()

    if args.metrics:
        print(json.dumps(edit_metrics(Path(args.source)), ensure_ascii=False, indent=2))
        return

    if re.match(r"https?://", args.source):
        from_youtube(args.source, args.name, args.frames)
    else:
        p = Path(args.source)
        if not p.exists():
            sys.exit(f"ファイルが見つかりません: {p}")
        from_file(p, args.name, args.frames)


if __name__ == "__main__":
    main()
