import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "./components/Background";
import { Character } from "./components/Character";
import { SubtitleBar } from "./components/SubtitleBar";
import { CompositionData } from "./types";

// フォント読み込み
const fontFace = `
  @font-face {
    font-family: 'Keifont';
    src: url('${staticFile("fonts/keifont.ttf")}') format('truetype');
  }
`;

export const SleepVideo: React.FC<{ data: CompositionData }> = ({ data }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const currentTimeSec = frame / fps;

  // 現在の字幕を取得
  const currentSub = data.subtitles.find(
    (s) => currentTimeSec >= s.start && currentTimeSec < s.end
  );

  const emotion = currentSub?.emotion ?? "normal";
  const isTalking = currentSub !== undefined;

  return (
    <AbsoluteFill>
      {/* フォント */}
      <style>{fontFace}</style>

      {/* 背景 */}
      <Background />

      {/* キャラクター（右下） */}
      <Character isTalking={isTalking} frame={frame} />

      {/* メイン音声 */}
      <Audio src={staticFile(data.audio)} />

      {/* 強調字幕のピコン音（読み上げと同時） */}
      {data.subtitles
        .filter((s) => s.emphasized)
        .map((s, i) => (
          <Sequence key={i} from={Math.round(s.start * fps)} durationInFrames={30}>
            <Audio src={staticFile("audio/pikon.wav")} volume={0.316} />
          </Sequence>
        ))}

      {/* 字幕バー（最前面） */}
      <SubtitleBar subtitles={data.subtitles} currentTimeSec={currentTimeSec} />
    </AbsoluteFill>
  );
};
