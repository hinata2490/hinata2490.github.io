# アカウント開設手順

@cosme_no_jijou を今日中に立ち上げる。所要時間 約10分（画像生成除く）。

## 1. アイコン画像（Geminiで生成）

先行者 @biyouhin_honne のアイコン（複数キャラ集合＋暖色ボケ背景）を参考に、主役＝ep01ハトムギキャラで作る。動画との認知を繋げる狙い。

### Geminiプロンプト

```
A cute 3D Pixar-style cosmetics character group portrait, TikTok profile icon.
Main character in the center front: a white cosmetics bottle with purple cap and purple gloves, with an angry sassy expression, hands on hips.
Behind the main character (slightly blurred), 3-4 other cute cosmetics characters stylized the same way: a small skincare jar, a lipstick tube, a cream tube, a serum dropper bottle — all with cute faces peeking over the main character's shoulders.
Warm bokeh background with soft golden-pink glow, dreamy cosmetics shop atmosphere.
Square format (1:1), centered composition, character fills about 70% of the frame.
No text, no logos, no brand names anywhere.
High quality Pixar-quality 3D render.
```

### 生成後の調整

- 1:1にトリミング
- TikTokは中央に表示されるので、円形マスクされても顔が切れない構図を選ぶ

## 2. ユーザー名 / 表示名

| 項目 | 値 |
|---|---|
| ユーザー名 | `cosme_no_jijou` |
| 表示名 | `コスメの事情` |

予備候補（取られていた場合）:
- `cosmeno_jijou`
- `cosme.no.jijou`
- `cosmenojijou_official`

## 3. プロフィール文

**方針: AIは書かない。** 先行者 @biyouhin_honne もプロフィールでAI表記なし。動画投稿時の「AI生成コンテンツ」ラベルON だけで法務対応は十分。プロフィールに書くと逆に身構えられて離脱率上がる懸念あり。

### メイン推奨

```
💄コスメたちの本音💢
使い方間違えると全員ブチギレます
正しい使い方・宣伝の裏側を暴露
📩お仕事のご依頼はDMまで
```

### 予備A（より攻めめ）

```
💢コスメが本音でキレる場所💢
「その使い方、間違ってるから」
週5本で使い方・買い物の勘違いを暴露
📩お仕事DMどうぞ
```

### 予備B（柔らかめ）

```
💄化粧品たちの本音、聞いてみない？
擬人化コスメが使い方を解説します
週5本投稿予定📅
📩お仕事DM受付中
```

### 予備C（短め・シャープ）

```
💢コスメがブチギレ解説💢
使い方の勘違い・宣伝の裏側
週5本｜📩お仕事DM
```

## AI表記の方針（まとめ）

| 場所 | AI表記 |
|---|---|
| 動画投稿時のラベル | **ON（必須）** - TikTok規約 |
| プロフィール文 | **書かない** - 先行者踏襲 |
| ハッシュタグ | **入れない** |

## 4. ヘッダー画像（任意・後回し可）

TikTokプロフィールにはヘッダー画像欄がない。アイコンで完結するのでスキップでOK。

## 5. リンク欄

- フォロワー1,000人到達まではリンクなしでOK
- 1,000人到達後、TikTok Shop 連携リンクを設定

## 6. 設定でやること

| 設定 | 値 | 理由 |
|---|---|---|
| アカウント種別 | クリエイターアカウント | 分析データが見られる |
| プライバシー | 公開 | バズらせるため必須 |
| コメント | 全員許可 | エンゲージメント確保 |
| ダイレクトメッセージ | フォロワーのみ | スパム対策 |
| ダウンロード | 許可 | 拡散効果（保存=エンゲージメントシグナル） |

## ⚠️ デバイスペナルティの罠（2026-04-19 学び）

ep01投稿時、9時間で0再生という事象が発生。原因は**スマホ単位のデバイスフィンガープリント**による「多重アカウント運用者」フラグの可能性が高い。

### TikTokは何を見ているか
- 端末ID（IMEI / Android ID / iOS識別子）
- WiFi/IPアドレス
- 広告ID
- 過去のログイン履歴

→ **GmailやTikTokアカウントを変えても「同じスマホ＝同じ人」と判定される**。

### 過去にアカウントを作りすぎたデバイスの場合
- 「多重アカウント運用者」フラグ → スパム業者と同類扱い
- 新アカウントの初期リーチを大幅に絞る
- 投稿しても **おすすめフィードに一切流さない**（事実上のシャドウバン）

### 対処法
1. **新規スマホで運用が理想**（家族のスマホ、サブ機）
2. それが無理なら: アプリ完全削除 → 広告IDリセット → 別WiFi → 数時間待機 → 再インストール
3. それでもダメなら: 1〜3ヶ月の長期戦覚悟。健全ユーザー演出で評価回復を待つ
4. 並行して Instagram Reels / YouTube Shorts にも同じ動画を投稿（保険）

### 教訓
- 旧アカウント再活用 vs 新規作成 → **デバイスがクリーンなら新規ベスト**
- すでに多重作成歴があるスマホでは、新規作っても同じペナルティ食らう
- TikTok運用前に **デバイスのアカウント作成歴をリセット** するのが理想

## 7. 開設チェックリスト

- [ ] Geminiでアイコン生成（プロンプト上記）
- [ ] TikTokアプリでアカウント作成
- [ ] ユーザー名 `cosme_no_jijou` 取得
- [ ] 表示名 `コスメの事情` 設定
- [ ] アイコンアップロード
- [ ] プロフィール文設定（メイン案コピペ）
- [ ] クリエイターアカウントに切替
- [ ] 各設定を上記の値に
