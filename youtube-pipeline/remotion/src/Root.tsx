import React from "react";
import { Composition } from "remotion";
import { SleepVideo } from "./SleepVideo";
import { CompositionData } from "./types";

// テスト用データ（後でPythonパイプラインから自動生成）
const TEST_DATA: CompositionData = {
  title: "睡眠の質を上げる3つの方法",
  audio: "audio/test_timed_voice.wav",
  duration_sec: 44.127,
  fps: 30,
  subtitles: [
    { start: 0.000,  end: 1.013,  text: "こんにちは。",                                         emphasized: false, emotion: "normal" },
    { start: 1.513,  end: 5.727,  text: "今日は睡眠の質を上げる\n3つの方法をご紹介します。",       emphasized: false, emotion: "normal" },
    { start: 6.227,  end: 10.141, text: "1つ目は、毎日同じ時間に\n寝起きすることです。",           emphasized: true,  emotion: "normal" },
    { start: 10.641, end: 14.695, text: "体内時計が整い、\n自然と眠気がやってきます。",             emphasized: false, emotion: "normal" },
    { start: 15.195, end: 20.123, text: "2つ目は、寝る1時間前に\nスマートフォンの使用をやめることです。", emphasized: true, emotion: "normal" },
    { start: 20.623, end: 23.951, text: "ブルーライトがメラトニンの\n分泌を妨げます。",             emphasized: false, emotion: "normal" },
    { start: 24.451, end: 29.411, text: "3つ目は、寝室の温度を\n18度から22度に保つことです。",    emphasized: true,  emotion: "normal" },
    { start: 29.911, end: 33.793, text: "体温が下がることで\n深い眠りに入りやすくなります。",       emphasized: false, emotion: "normal" },
    { start: 34.293, end: 38.176, text: "以上、睡眠の質を上げる\n3つの方法でした。",               emphasized: false, emotion: "normal" },
    { start: 38.676, end: 44.127, text: "ぜひ今夜から試してみてください。\nチャンネル登録もよろしくお願いします。", emphasized: false, emotion: "normal" },
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
