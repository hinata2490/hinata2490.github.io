# EP01「ハトムギ化粧水」制作ワークフロー（コピペ実行用）

上から順に実行。各ステップに **所要時間目安** と **コピペできる原稿/プロンプト** を全部入れた。

総所要時間目安: **4〜5時間**

---

## STEP 1: Geminiでキャラ画像生成（30分）

### やること

ハトムギ化粧水ボトルを擬人化した3DCGキャラ画像を作る。

### 準備

ハトムギ化粧水のボトル参照画像（スマホで撮影 or 公式サイトからダウンロード）

### Geminiにアップロードして渡すプロンプト

```
This is a Japanese skincare lotion bottle. Create a cute 3D Pixar-style anthropomorphized character based on this bottle.

Requirements:
- Keep the bottle's shape, color, and proportions recognizable (so viewers think "oh, that bottle")
- DO NOT include any text, logos, brand names, or labels on the bottle
- Add expressive cartoon eyes (large, glossy) and a small mouth
- Add cartoon arms and legs in a Pixar-style proportion
- The character is angry/frustrated, hands on hips or arms crossed
- Pure white or light gray background (for green-screen replacement later)
- High quality 3D rendering, soft studio lighting
- Vertical format (9:16) suitable for TikTok
- Full body visible, centered

Style reference: Pixar's "Cars" or "Toy Story" character design quality.
```

### リテイクのコツ

- ロゴ/文字が出てしまった → プロンプトに「`Absolutely no text, no Japanese characters, no labels`」を追記
- 表情が物足りない → 「`exaggerated angry expression, raised eyebrows, mouth open mid-shout`」追記
- 背景に色が出る → 「`pure white background #FFFFFF, no shadows touching the edges`」追記

### 成果物

- `character_base.png` （怒り顔・基本ポーズ） 1枚
- 必要なら表情違いも生成（呆れ顔・落ち着き顔・ドヤ顔）

---

## STEP 2: CapCutで音声生成（15分）

### やること

セリフをCapCutのAI音声で生成。1.2倍速処理。

### CapCut操作手順

1. CapCut起動 → 新規プロジェクト → 9:16
2. テキストツール → 「テキスト読み上げ」
3. 声: **若い女性 / 元気・感情豊か** 系を選ぶ（複数試して一番"キレ"が乗るやつ）
4. 各セリフを以下の通り入力 → 音声生成 → ダウンロード
5. ダウンロード後、Premiereで1.2倍速にする（CapCutで速度調整してもOK）

### セリフ分割（コピペ用）

#### 音声01.mp3
```
おいおいおいおい！叩くのやめてくれ〜！毎晩毎晩パンパンパンパン、お前の顔は太鼓かよ！
```

#### 音声02.mp3
```
いいか？叩いても浸透しないから。俺も痛いし。摩擦でシミとくすみ増えてんの、俺のせいにすんなよ
```

#### 音声03.mp3
```
あとさ、量。ケチんなって。500円玉って書いてあんだろ。いいか、正しくは手のひらに出して、顔を包み込む。叩くんじゃなくて押す。
```

#### 音声04.mp3
```
700円で500ml。せめて使い方くらいまともにしてくれ
```

### 命名規則

`ep01_voice_01.mp3` 〜 `ep01_voice_04.mp3` の形で保存推奨

---

## STEP 3: 秒数計測（5分）

各音声ファイルをWindowsエクスプローラーで右クリック → プロパティ → 詳細 → 長さを確認。

| ファイル | 想定秒数（1.2倍速後） | 実測 |
|---|---|---|
| voice_01 | 約10秒 | ___ |
| voice_02 | 約8秒 | ___ |
| voice_03 | 約7秒 | ___ |
| voice_04 | 約7秒 | ___ |

実測値が**10秒を超えるカットがあったら** → さらに速度上げる or セリフ削る（Klingリップシンク10秒制限のため）

---

## STEP 4: Klingでカット動画生成（60〜90分）

### やること

各カットの動画（キャラがリアクションしてるシーン）を4本生成。

### 共通設定

- 解像度: **720p**（1080pは240クレジット余分）
- 長さ: 各カットの音声秒数 + 0秒（余白なし）
- 開始フレーム: STEP1 で生成したキャラ画像をアップロード

### カット1（10秒）冒頭：ブチ切れ

```
The cosmetics bottle character explodes with anger.
Frame 1-3 sec: Character jumps and shakes fists in pure rage, mouth wide open shouting.
Frame 4-7 sec: Character points aggressively at the camera, wagging finger.
Frame 8-10 sec: Character throws hands up in disbelief.
Camera: static, full body shot, character centered.
Background: pure white.
Style: Pixar 3D animation, exaggerated motion, snappy timing.
```

### カット2（8秒）呆れ：怒りから呆れに転調

```
The cosmetics bottle character starts furious, then sighs in exhaustion.
Frame 1-3 sec: Character shakes head while waving hands in front.
Frame 4-6 sec: Character covers face with both hands ("oh my god" pose).
Frame 7-8 sec: Character points slowly at the viewer with tired expression.
Camera: static, medium shot, character centered.
Background: pure white.
Style: Pixar 3D animation, expressive, tired exasperation.
```

### カット3（7秒）解説：落ち着いて教える

```
The cosmetics bottle character calms down and explains carefully.
Frame 1-3 sec: Character holds up an open palm and demonstrates "place gently".
Frame 4-5 sec: Character mimes covering face with both hands gently (as if applying lotion).
Frame 6-7 sec: Character nods firmly, satisfied.
Camera: static, medium shot.
Background: pure white.
Style: Pixar 3D animation, calm but slightly stern teacher mode.
```

### カット4（7秒）誇り→言い切り：ドヤ→トドメ

```
The cosmetics bottle character poses with pride, then deadpan stare.
Frame 1-3 sec: Character strikes a confident hero pose, hands on hips, chest puffed out.
Frame 4-5 sec: Character winks and gives a thumbs up.
Frame 6-7 sec: Character drops the smile, gives a flat unimpressed stare directly at the camera.
Camera: static, full body shot.
Background: pure white.
Style: Pixar 3D animation, swagger to deadpan transition.
```

### リテイクのコツ

- 動きが地味 → プロンプトに「`exaggerated, snappy, energetic`」を強める
- ロゴが出ちゃう → 「`no text, no logos anywhere`」追記
- 背景が白くない → 「`pure solid white background, no gradient, no shadows`」強調

---

## STEP 5: Klingでリップシンク合成（30分）

### やること

STEP4で作った各カット動画 + STEP2の音声をKlingのリップシンク機能で合成。

### 操作手順

Kling管理画面 → リップシンク機能 → 動画とaudioをセット → 生成

### ペアリング

| カット動画 | 音声ファイル |
|---|---|
| cut01.mp4 | ep01_voice_01.mp3 |
| cut02.mp4 | ep01_voice_02.mp3 |
| cut03.mp4 | ep01_voice_03.mp3 |
| cut04.mp4 | ep01_voice_04.mp3 |

### チェック

- 口の動きと音声が合ってるか確認
- ズレてたらリテイク（Kling側で再生成）

---

## STEP 6: Premiere Proで仕上げ（60〜90分）

### プロジェクト設定

- 解像度: 1080×1920（縦型）
- フレームレート: 30fps
- 尺: 約32秒

### タイムライン構成

| 時刻 | カット | 内容 |
|---|---|---|
| 0:00〜0:10 | カット1 | 冒頭ブチ切れ |
| 0:10〜0:18 | カット2 | 呆れ |
| 0:18〜0:25 | カット3 | 解説 |
| 0:25〜0:32 | カット4 | ドヤ→トドメ |

### クロマキー合成

1. 各リップシンク動画を配置
2. エフェクト → キーイング → Ultra Key を適用
3. キーカラー: 白（#FFFFFF）
4. 背景レイヤー: 画面全体パステルピンク（#FFE4EC）or グラデーション

### テロップ原稿（タイムコード付き）

`*` 印は強調表示推奨（黄色 or 赤の縁取り）

| 時刻 | テロップ |
|---|---|
| 0:00 | おいおいおいおい！ |
| 0:01 | 叩くのやめてくれ〜！ |
| 0:03 | 毎晩毎晩パンパンパンパン |
| 0:06 | お前の顔 *太鼓かよ* |
| 0:10 | いいか？*叩いても浸透しない* から |
| 0:13 | 俺も痛いし |
| 0:14 | 摩擦で *シミとくすみ* 増えてんの |
| 0:17 | 俺のせいにすんなよ |
| 0:18 | あとさ、量。*ケチんなって* |
| 0:20 | 500円玉って書いてあんだろ |
| 0:22 | 正しくは手のひらに出して |
| 0:23 | 顔を *包み込む* |
| 0:24 | 叩くんじゃなくて *押す* |
| 0:25 | 700円で500ml |
| 0:28 | せめて使い方くらい |
| 0:30 | *まともにしてくれ* |

> **オーナーメモ**: テロップにフェードは不要。パッと切り替え。

### BGM

Envato Elements で以下キーワードで検索:
- `comedy upbeat`
- `playful tension`
- `ironic background`

**音量**: -24dB 〜 -20dB（セリフを邪魔しない範囲）

### SE

| 時刻 | SE | 用途 |
|---|---|---|
| 0:00 | パンチ・破裂音 | 冒頭インパクト |
| 0:03 | 太鼓ドン | 「太鼓かよ」とシンクロ |
| 0:06〜0:09 | 呆れため息 | カット2背景 |
| 0:18 | キラン | 「いいか」転調 |
| 0:30 | ピシッ | 「まともにしてくれ」決め |

### 編集ポイント

- **0.5秒で掴む**: 0:00〜0:00.5 の絵作りに最も時間をかける
- **テンポ**: 1セリフ終わったら即次のセリフ。間を空けすぎない
- **テロップサイズ**: 画面幅の70%以内、上下の安全領域（TikTok UIに被らない）を守る

### 書き出し

- フォーマット: H.264
- プリセット: TikTok 1080p 縦型
- ファイル名: `ep01_hatomugi_final.mp4`

---

## STEP 7: TikTok投稿（10分）

→ [docs/account-setup.md](../docs/account-setup.md) でアカウント開設済み前提

### 操作

1. TikTokアプリ → 「+」 → アップロード → `ep01_hatomugi_final.mp4` 選択
2. **AI生成コンテンツのラベル** を ON（必須）
3. キャプション貼り付け（下記）
4. ハッシュタグ追加
5. 公開

### キャプション（コピペ）

```
ハトムギさんがガチでキレてる件🥲
叩くのほんとやめてあげて、シミとくすみの原因です。
正しい使い方、コメントで補足あったら教えて💬
#コスメの事情 #ハトムギ化粧水 #スキンケア #美容初心者
```

### ハッシュタグ補足

固定 4つ + 動画ごと変動 4〜6つ目安。今回は:

```
#コスメの事情 #ハトムギ化粧水 #スキンケア #美容初心者 #コスメ豆知識 #正しい使い方 #擬人化
```

### TikTok Shopカートは付けない

→ フォロワー1,000人未到達のため。30日以内に1,000人到達したら後付けで追加可能。

---

## トラブル時の判断ルール

| 症状 | 対処 |
|---|---|
| Geminiでロゴが消えない | プロンプトに「no text, no logos」を3回入れる→ダメなら参照画像を別アングルに |
| Klingで動きが弱い | プロンプト「snappy, exaggerated, energetic」追記 |
| Klingリップシンクで口がズレる | 音声側を1.2倍速→1.1倍速に落として再合成 |
| カットが10秒超える | セリフを削るか、CapCut音声側で速度を上げる |
| 全部詰まる | カット数を4→3に減らして当日投稿優先 |
