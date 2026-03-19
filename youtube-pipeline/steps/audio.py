"""
Step 3: 音声生成
台本テキストから音声ファイルを生成する。
優先順位: VOICEVOX (ローカル) → OpenAI TTS → gTTS (fallback)
"""

import io
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# 間・効果音指示を除去するパターン
_CLEAN_PATTERNS = [
    (r'【間】', '、'),         # 間指示 → 読点で代替
    (r'\(SE:[^)]*\)', ''),    # 効果音指示を除去
    (r'\([^)]*\)', ''),       # 読み仮名括弧を除去（例: 8時間(はちじかん) → 8時間）
    (r'#+ ', ''),             # Markdown 見出し記号
    (r'\*+([^*]+)\*+', r'\1'),# Bold/italic 記号
]


def clean_text_for_tts(text: str) -> str:
    """TTS用にテキストをクリーニング"""
    for pattern, replacement in _CLEAN_PATTERNS:
        text = re.sub(pattern, replacement, text)
    # 連続する空白・改行を整理
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# VOICEVOX エンジン
# ---------------------------------------------------------------------------

class VoicevoxEngine:
    """VOICEVOX HTTP API を使った音声生成"""

    def __init__(self, host: str, speaker_id: int, params: dict):
        self.host = host.rstrip('/')
        self.speaker_id = speaker_id
        self.params = params

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.host}/version", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def synthesize(self, text: str) -> bytes:
        """テキスト → WAV bytes"""
        # 音声クエリ生成
        query_resp = requests.post(
            f"{self.host}/audio_query",
            params={"text": text, "speaker": self.speaker_id},
            timeout=30,
        )
        query_resp.raise_for_status()
        query = query_resp.json()

        # パラメータ適用
        query["speedScale"] = self.params.get("speed_scale", 1.0)
        query["pitchScale"] = self.params.get("pitch_scale", 0.0)
        query["intonationScale"] = self.params.get("intonation_scale", 1.2)
        query["volumeScale"] = self.params.get("volume_scale", 1.0)

        # 音声合成
        synth_resp = requests.post(
            f"{self.host}/synthesis",
            params={"speaker": self.speaker_id},
            json=query,
            timeout=60,
        )
        synth_resp.raise_for_status()
        return synth_resp.content  # WAV bytes


# ---------------------------------------------------------------------------
# OpenAI TTS エンジン
# ---------------------------------------------------------------------------

class OpenAITTSEngine:
    """OpenAI TTS API を使った音声生成"""

    MAX_CHARS = 4096  # OpenAI の1回あたり上限

    def __init__(self, api_key: str, model: str, voice: str, speed: float):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.voice = voice
        self.speed = speed

    def synthesize(self, text: str) -> bytes:
        """テキスト → MP3 bytes (長文は分割して結合)"""
        chunks = self._split_text(text)
        audio_parts = []

        for chunk in chunks:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=chunk,
                speed=self.speed,
            )
            audio_parts.append(response.content)

        return b"".join(audio_parts)

    def _split_text(self, text: str) -> list[str]:
        """長文を文節単位で分割"""
        if len(text) <= self.MAX_CHARS:
            return [text]

        sentences = re.split(r'(?<=[。！？\n])', text)
        chunks, current = [], ""
        for sent in sentences:
            if len(current) + len(sent) > self.MAX_CHARS:
                if current:
                    chunks.append(current.strip())
                current = sent
            else:
                current += sent
        if current.strip():
            chunks.append(current.strip())
        return chunks


# ---------------------------------------------------------------------------
# gTTS フォールバック
# ---------------------------------------------------------------------------

class GTTSEngine:
    """Google TTS (無料 fallback)"""

    def synthesize(self, text: str) -> bytes:
        from gtts import gTTS
        buf = io.BytesIO()
        tts = gTTS(text=text, lang="ja", slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()


# ---------------------------------------------------------------------------
# BGM ミキシング (FFmpeg)
# ---------------------------------------------------------------------------

def mix_bgm(voice_path: Path, bgm_dir: Path, output_path: Path, audio_cfg: dict) -> Path:
    """ナレーション音声に BGM を重ねる"""
    bgm_files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
    if not bgm_files:
        logger.warning("BGM ファイルが見つかりません。BGM なしで出力します。")
        return voice_path

    bgm_path = bgm_files[0]  # 最初の BGM を使用
    vol = audio_cfg.get("volume", 0.08)
    fade_in = audio_cfg.get("fade_in_sec", 3.0)
    fade_out = audio_cfg.get("fade_out_sec", 5.0)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(voice_path),
        "-stream_loop", "-1", "-i", str(bgm_path),
        "-filter_complex",
        (
            f"[1:a]volume={vol},"
            f"afade=t=in:st=0:d={fade_in},"
            f"afade=t=out:st=0:d={fade_out}[bgm];"
            "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[out]"
        ),
        "-map", "[out]",
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"BGM ミックス失敗: {result.stderr}")
        return voice_path

    logger.info(f"BGM ミックス完了: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(
    script_data: dict,
    cfg: dict[str, Any],
    api_keys: dict[str, str],
) -> Path:
    """
    台本データから音声ファイルを生成して保存し、ファイルパスを返す。

    Args:
        script_data: script.py が返した台本データ
        cfg: config.yaml の全体設定
        api_keys: {"OPENAI_API_KEY": "..."}

    Returns:
        生成された音声ファイルのパス
    """
    audio_cfg = cfg["audio"]
    output_dir = Path(cfg["pipeline"]["output_base"]) / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    title = script_data.get("video_title", "untitled")
    safe_title = re.sub(r'[^\w\-]', '_', title)[:40]
    today = datetime.now().strftime("%Y%m%d")

    # skip_existing チェック
    final_path = output_dir / f"{today}_{safe_title}_mixed.mp3"
    if cfg["pipeline"]["skip_existing"] and final_path.exists():
        logger.info(f"既存音声ファイルを使用: {final_path}")
        return final_path

    # 台本テキストを結合・クリーニング
    full_text = "\n\n".join(
        s["text"] for s in script_data.get("sections", [])
    )
    full_text = clean_text_for_tts(full_text)
    logger.info(f"音声合成: {len(full_text)} 文字")

    # エンジン選択
    engine_name = audio_cfg["engine"]
    audio_bytes: bytes = b""

    if engine_name == "voicevox":
        engine = VoicevoxEngine(
            host=audio_cfg["voicevox"]["host"],
            speaker_id=audio_cfg["voicevox"]["speaker_id"],
            params=audio_cfg["voicevox"],
        )
        if engine.is_available():
            logger.info("VOICEVOX エンジンを使用")
            audio_bytes = engine.synthesize(full_text)
        else:
            logger.warning("VOICEVOX が起動していません。OpenAI TTS へフォールバック")
            engine_name = "openai"

    if engine_name == "openai":
        openai_key = api_keys.get("OPENAI_API_KEY", "")
        if not openai_key:
            logger.warning("OPENAI_API_KEY 未設定。gTTS へフォールバック")
            engine_name = "gtts"
        else:
            oai_cfg = audio_cfg["openai"]
            engine = OpenAITTSEngine(
                api_key=openai_key,
                model=oai_cfg["model"],
                voice=oai_cfg["voice"],
                speed=oai_cfg["speed"],
            )
            logger.info("OpenAI TTS エンジンを使用")
            audio_bytes = engine.synthesize(full_text)

    if engine_name == "gtts" or not audio_bytes:
        logger.info("gTTS エンジンを使用")
        engine = GTTSEngine()
        audio_bytes = engine.synthesize(full_text)

    # 音声ファイル保存
    voice_ext = "wav" if engine_name == "voicevox" else "mp3"
    voice_path = output_dir / f"{today}_{safe_title}_voice.{voice_ext}"
    with open(voice_path, "wb") as f:
        f.write(audio_bytes)
    logger.info(f"音声保存: {voice_path}")

    # BGM ミックス
    if audio_cfg["bgm"]["enabled"]:
        bgm_dir = Path(audio_cfg["bgm"]["dir"])
        final_path = mix_bgm(voice_path, bgm_dir, final_path, audio_cfg["bgm"])
    else:
        import shutil
        shutil.copy(voice_path, final_path)

    logger.info(f"音声生成完了: {final_path}")
    return final_path
