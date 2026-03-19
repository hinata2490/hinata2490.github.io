import React from "react";
import { Img, staticFile } from "remotion";

const IMAGES = {
  normal:       staticFile("character/rei_normal.png"),
  blink_half:   staticFile("character/rei_blink_half.png"),
  blink_closed: staticFile("character/rei_blink_closed.png"),
  mouth_open:   staticFile("character/rei_mouth_open.png"),
};

function getBlinkState(frame: number): "open" | "half" | "closed" {
  const INTERVAL = 130; // 約4.3秒ごと
  const pos = frame % INTERVAL;
  if (pos < 3) return "half";
  if (pos < 6) return "closed";
  if (pos < 9) return "half";
  return "open";
}

function getMouthState(frame: number, isTalking: boolean): "open" | "closed" {
  if (!isTalking) return "closed";
  return Math.floor(frame / 8) % 2 === 0 ? "open" : "closed";
}

interface Props {
  isTalking: boolean;
  frame: number;
}

export const Character: React.FC<Props> = ({ isTalking, frame }) => {
  const blink = getBlinkState(frame);
  const mouth = getMouthState(frame, isTalking);

  // 優先度: まばたき > 口パク > 通常
  let key: keyof typeof IMAGES = "normal";
  if (blink === "half") key = "blink_half";
  else if (blink === "closed") key = "blink_closed";
  else if (mouth === "open") key = "mouth_open";

  const bob = Math.sin((frame / 90) * Math.PI) * 5;

  return (
    <div
      style={{
        position: "absolute",
        right: -150,
        bottom: -300,       // 足首より下は画面外
        width: 1600,
        height: 1600,
        transform: `translateY(${bob}px)`,
      }}
    >
      <Img
        src={IMAGES[key]}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom center",
        }}
      />
    </div>
  );
};
