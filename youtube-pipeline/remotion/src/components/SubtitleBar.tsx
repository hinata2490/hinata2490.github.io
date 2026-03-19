import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Subtitle } from "../types";

interface Props {
  subtitles: Subtitle[];
  currentTimeSec: number;
}

export const SubtitleBar: React.FC<Props> = ({ subtitles, currentTimeSec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  void frame; void fps; // 将来のアニメーション用

  // 現在アクティブな字幕、なければ最後に表示されていた字幕を維持
  const current = subtitles.find(
    (s) => currentTimeSec >= s.start && currentTimeSec < s.end
  );
  const lastShown = [...subtitles].reverse().find(
    (s) => currentTimeSec >= s.start
  );
  const display = current ?? lastShown;

  if (!display) return null;

  const isEmphasized = display.emphasized;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        padding: "16px 60px",
        background: "rgba(0, 0, 30, 0.82)",
        borderTop: "2px solid rgba(255,255,255,0.15)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: 160,
      }}
    >
      <p
        style={{
          fontFamily: "'Keifont', sans-serif",
          fontSize: 46,
          color: "#ffffff",
          textShadow: "2px 2px 0 #000, -1px -1px 0 #000",
          margin: 0,
          lineHeight: 1.5,
          textAlign: "center",
          whiteSpace: "pre-wrap",
          letterSpacing: "0.05em",
        }}
      >
        {display.text}
      </p>
    </div>
  );
};
