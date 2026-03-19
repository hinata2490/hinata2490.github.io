import React from "react";
import { Composition } from "remotion";
import { SleepVideo } from "./SleepVideo";
import { CompositionData } from "./types";

// テスト用データ（後でPythonパイプラインから自動生成）
const TEST_DATA: CompositionData = {
  title: "睡眠の質を上げる3つの方法",
  audio: "audio/voice_v3.wav",
  duration_sec: 38.892,
  fps: 30,
  subtitles: [
    { start: 0.000,  end: 0.939,  text: "こんにちは。",                                                    emphasized: false, emotion: "normal" },
    { start: 1.239,  end: 5.111,  text: "今日は睡眠の質を上げる\n3つの方法をご紹介します。",                  emphasized: false, emotion: "normal" },
    { start: 5.411,  end: 8.973,  text: "1つ目は、毎日同じ時間に\n寝起きすることです。",                     emphasized: true,  emotion: "normal" },
    { start: 9.273,  end: 12.953, text: "体内時計が整い、\n自然と眠気がやってきます。",                       emphasized: false, emotion: "normal" },
    { start: 13.253, end: 17.733, text: "2つ目は、寝る1時間前に\nスマートフォンの使用をやめることです。",      emphasized: true,  emotion: "normal" },
    { start: 18.033, end: 21.031, text: "ブルーライトがメラトニンの\n分泌を妨げます。",                       emphasized: false, emotion: "normal" },
    { start: 21.331, end: 25.907, text: "3つ目は、寝室の温度を\n18度から22度に保つことです。",               emphasized: true,  emotion: "normal" },
    { start: 26.207, end: 29.716, text: "体温が下がることで\n深い眠りに入りやすくなります。",                  emphasized: false, emotion: "normal" },
    { start: 30.016, end: 33.600, text: "以上、睡眠の質を上げる\n3つの方法でした。",                          emphasized: false, emotion: "normal" },
    { start: 33.900, end: 38.892, text: "ぜひ今夜から試してみてください。\nチャンネル登録もよろしくお願いします。", emphasized: false, emotion: "normal" },
  ],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="SleepVideo"
      component={SleepVideo}
      durationInFrames={Math.ceil(TEST_DATA.duration_sec * TEST_DATA.fps)}
      fps={TEST_DATA.fps}
      width={1920}
      height={1080}
      defaultProps={{ data: TEST_DATA }}
    />
  );
};
