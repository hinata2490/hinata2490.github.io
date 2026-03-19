export type Emotion = "normal" | "happy" | "surprised" | "thinking" | "sleepy";

export interface Subtitle {
  start: number;    // 開始時刻（秒）
  end: number;      // 終了時刻（秒）
  text: string;
  emphasized: boolean;
  emotion: Emotion;
}

export interface CompositionData {
  title: string;
  audio: string;        // 音声ファイルパス（publicDir相対）
  duration_sec: number;
  fps: number;
  subtitles: Subtitle[];
}
