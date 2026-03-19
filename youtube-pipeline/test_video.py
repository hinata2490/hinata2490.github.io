"""
テスト動画生成スクリプト
- APIキー不要
- VOICEVOXで文ごとに合成して正確な字幕タイミングを取得
- BudouXで意味のまとまりで改行
- けいふぉんとフォント使用
"""

import copy
import io
import logging
import os
import re
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import budoux
import requests

# FFmpegをPATHに追加
FFMPEG_DIR = r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from steps import video

VOICEVOX_EXE = r"C:\Users\user\AppData\Local\Programs\VOICEVOX\VOICEVOX.exe"
FONT_PATH = str(BASE_DIR / "assets" / "fonts" / "keifont.ttf")
FONTS_DIR = str(BASE_DIR / "assets" / "fonts")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# BudouXパーサー（日本語）
_budoux_parser = budoux.load_default_japanese_parser()

# ----------------------------------------------------------------
# テスト台本
# ----------------------------------------------------------------
TEST_SCRIPT = {
    "video_title": "テスト動画_睡眠の質を上げる3つの方法",
    "video_description": "テスト用動画です。",
    "tags": ["睡眠", "快眠", "テスト"],
    "estimated_duration_min": 1,
    "sections": [
        {
            "title": "イントロ",
            "text": "こんにちは。今日は睡眠の質を上げる3つの方法をご紹介します。",
            "duration_sec": 5,
        },
        {
            "title": "方法1",
            "text": "1つ目は、毎日同じ時間に寝起きすることです。体内時計が整い、自然と眠気がやってきます。",
            "duration_sec": 8,
        },
        {
            "title": "方法2",
            "text": "2つ目は、寝る1時間前にスマートフォンの使用をやめることです。ブルーライトがメラトニンの分泌を妨げます。",
            "duration_sec": 8,
        },
        {
            "title": "方法3",
            "text": "3つ目は、寝室の温度を18度から22度に保つことです。体温が下がることで深い眠りに入りやすくなります。",
            "duration_sec": 8,
        },
        {
            "title": "まとめ",
            "text": "以上、睡眠の質を上げる3つの方法でした。ぜひ今夜から試してみてください。チャンネル登録もよろしくお願いします。",
            "duration_sec": 7,
        },
    ],
}

VOICEVOX_CFG = {
    "host": "http://localhost:50021",
    "speaker_id": 3,
    "speed_scale": 1.15,
    "pitch_scale": 0.0,
    "intonation_scale": 1.2,
    "volume_scale": 1.0,
}

TEST_CONFIG = {
    "pipeline": {
        "output_base": "output",
        "skip_existing": False,
        "log_level": "INFO",
        "log_dir": "logs",
        "dry_run": False,
    },
    "video": {
        "resolution": "1920x1080",
        "fps": 30,
        "background": {
            "type": "gradient",
            "dir": "assets/backgrounds",
            "default_gradient": {"colors": ["#0a0a2e", "#1a1a4e"]},
        },
        "subtitle": {
            "enabled": True,
            "font": FONT_PATH,
            "font_size": 52,
            "color": "white",
            "outline_color": "black",
            "outline_width": 3,
            "position": "bottom",
            "max_chars_per_line": 20,
        },
        "logo": {"enabled": False, "path": "", "position": "top-right", "opacity": 0.7},
    },
}


# ----------------------------------------------------------------
# VOICEVOX起動確認
# ----------------------------------------------------------------
def ensure_voicevox() -> bool:
    try:
        r = requests.get(f"{VOICEVOX_CFG['host']}/version", timeout=2)
        if r.status_code == 200:
            print("VOICEVOX: 起動済み")
            return True
    except Exception:
        pass

    print("VOICEVOX を自動起動しています...")
    subprocess.Popen([VOICEVOX_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(25):
        time.sleep(1)
        try:
            r = requests.get(f"{VOICEVOX_CFG['host']}/version", timeout=2)
            if r.status_code == 200:
                print(f"VOICEVOX: 起動完了 ({i+1}秒)")
                return True
        except Exception:
            pass
    print("VOICEVOX の起動がタイムアウトしました。")
    return False


# ----------------------------------------------------------------
# BudouX による自然な改行
# ----------------------------------------------------------------
def smart_wrap(text: str, max_chars: int = 14) -> str:
    """BudouXで文脈を考慮した改行位置を決める"""
    chunks = _budoux_parser.parse(text)
    lines = []
    current = ""
    for chunk in chunks:
        if current and len(current) + len(chunk) > max_chars:
            lines.append(current)
            current = chunk
        else:
            current += chunk
    if current:
        lines.append(current)
    return "\n".join(lines)


# ----------------------------------------------------------------
# SRTタイムコード
# ----------------------------------------------------------------
def fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ----------------------------------------------------------------
# VOICEVOXで文ごとに合成してタイミング取得
# ----------------------------------------------------------------
def synthesize_with_timing(script_data: dict) -> tuple[Path, str]:
    """
    全セクションのテキストを文単位でVOICEVOXに投げ、
    正確なタイミング付きSRTと結合音声を生成する。
    Returns: (audio_path, srt_content)
    """
    host = VOICEVOX_CFG["host"]
    speaker_id = VOICEVOX_CFG["speaker_id"]
    speed_scale = VOICEVOX_CFG["speed_scale"]

    # 全テキストを句点・感嘆符・疑問符で文に分割
    full_text = " ".join(s["text"] for s in script_data["sections"])
    sentences = [s.strip() for s in re.split(r'(?<=[。！？])', full_text) if s.strip()]

    timings = []   # (表示テキスト, start_sec, end_sec)
    wav_parts = []
    cumulative = 0.0

    print(f"  {len(sentences)}文を合成します...")
    for i, sentence in enumerate(sentences):
        print(f"  [{i+1}/{len(sentences)}] {sentence[:20]}...")

        # audio_query
        q_resp = requests.post(
            f"{host}/audio_query",
            params={"text": sentence, "speaker": speaker_id},
            timeout=30,
        )
        q_resp.raise_for_status()
        query = q_resp.json()
        query["speedScale"] = speed_scale
        query["pitchScale"] = VOICEVOX_CFG["pitch_scale"]
        query["intonationScale"] = VOICEVOX_CFG["intonation_scale"]
        query["volumeScale"] = VOICEVOX_CFG["volume_scale"]

        # synthesis
        s_resp = requests.post(
            f"{host}/synthesis",
            params={"speaker": speaker_id},
            json=query,
            timeout=60,
        )
        s_resp.raise_for_status()
        wav_bytes = s_resp.content

        # WAVヘッダーから長さを読む
        with wave.open(io.BytesIO(wav_bytes), 'r') as wf:
            duration = wf.getnframes() / wf.getframerate()

        timings.append((sentence, cumulative, cumulative + duration))
        wav_parts.append(wav_bytes)
        cumulative += duration

    # WAVを結合
    output_dir = BASE_DIR / "output" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "test_timed_voice.wav"

    with wave.open(str(audio_path), 'w') as out_wf:
        for i, wb in enumerate(wav_parts):
            with wave.open(io.BytesIO(wb), 'r') as in_wf:
                if i == 0:
                    out_wf.setnchannels(in_wf.getnchannels())
                    out_wf.setsampwidth(in_wf.getsampwidth())
                    out_wf.setframerate(in_wf.getframerate())
                out_wf.writeframes(in_wf.readframes(in_wf.getnframes()))

    print(f"  音声結合完了: {cumulative:.1f}秒")

    # SRT生成（BudouX改行）
    srt_lines = []
    for idx, (sentence, start, end) in enumerate(timings, 1):
        display = smart_wrap(sentence)
        srt_lines.append(str(idx))
        srt_lines.append(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}")
        srt_lines.append(display)
        srt_lines.append("")

    srt_content = "\n".join(srt_lines)
    return audio_path, srt_content


# ----------------------------------------------------------------
# video.py の compose_video を直接呼び出してSRTを上書き
# ----------------------------------------------------------------
def run_video_with_custom_srt(script_data: dict, audio_path: Path, srt_content: str) -> Path:
    """SRTを外部から渡して動画を合成する"""
    import tempfile
    from steps.video import prepare_background, compose_video

    video_cfg = TEST_CONFIG["video"]
    output_dir = BASE_DIR / "output" / "video"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_timed_video.mp4"

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)

        # SRTファイル書き出し
        srt_path = tmp_dir / "subtitle.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        # 背景
        bg_path = prepare_background(video_cfg, audio_path, tmp_dir)

        # フォント付きsubtitleフィルター（FFmpeg）
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
        fonts_dir_escaped = FONTS_DIR.replace("\\", "/").replace(":", "\\:")
        font_size = video_cfg["subtitle"]["font_size"]

        subtitle_filter = (
            f"subtitles='{srt_escaped}'"
            f":fontsdir='{fonts_dir_escaped}'"
            f":force_style='FontName=Keifont"
            f",FontSize={font_size}"
            f",PrimaryColour=&H00FFFFFF"
            f",OutlineColour=&H00000000"
            f",Outline=3"
            f",Alignment=2'"
        )

        width, height = "1920", "1080"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-shortest",
            "-vf", f"scale={width}:{height},{subtitle_filter}",
            "-c:v", "libx264", "-b:v", "4000k",
            "-pix_fmt", "yuv420p",
            "-profile:v", "baseline", "-level", "3.1",
            "-c:a", "aac", "-b:a", "192k",
            "-r", "30",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logging.getLogger(__name__).info("FFmpeg 映像合成を開始...")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            print(f"FFmpegエラー:\n{result.stderr[-1000:]}")
            raise RuntimeError("動画合成失敗")

    return output_path


# ----------------------------------------------------------------
# メイン
# ----------------------------------------------------------------
def main():
    print("=" * 50)
    print("テスト動画生成を開始します")
    print("=" * 50)

    if not ensure_voicevox():
        print("VOICEVOXが起動できませんでした。終了します。")
        sys.exit(1)

    print("\n[Step 1] 音声合成 + タイミング取得（VOICEVOX・文ごと）...")
    audio_path, srt_content = synthesize_with_timing(TEST_SCRIPT)
    print(f"音声ファイル: {audio_path}")

    # SRTの中身を確認表示
    print("\n--- 生成されたSRT（先頭3エントリ）---")
    for line in srt_content.split("\n")[:15]:
        print(line)
    print("---")

    print("\n[Step 2] 動画合成中（FFmpeg + けいふぉんと）...")
    video_path = run_video_with_custom_srt(TEST_SCRIPT, audio_path, srt_content)

    print(f"\n{'=' * 50}")
    print(f"完成! 動画ファイル: {video_path}")
    print(f"{'=' * 50}")
    print("\nエクスプローラーで確認するには:")
    print(f'  explorer "{str(BASE_DIR / "output" / "video").replace("/", chr(92))}"')


if __name__ == "__main__":
    main()
