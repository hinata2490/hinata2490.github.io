import React from "react";

export const Background: React.FC = () => {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "linear-gradient(160deg, #0d1b3e 0%, #1a1a4e 50%, #0a0a2e 100%)",
      }}
    >
      {/* 星のパーティクル（静的） */}
      {STARS.map((s, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
            borderRadius: "50%",
            backgroundColor: "rgba(255,255,255,0.7)",
            opacity: s.opacity,
          }}
        />
      ))}
    </div>
  );
};

// 固定の星データ（毎フレーム再計算しないよう定数化）
const STARS = Array.from({ length: 60 }, (_, i) => ({
  x: ((i * 137.5) % 100),
  y: ((i * 97.3) % 100),
  size: i % 3 === 0 ? 3 : i % 3 === 1 ? 2 : 1,
  opacity: 0.3 + (i % 5) * 0.1,
}));
