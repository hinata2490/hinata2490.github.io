# 学習のしかた

**Claude Code に「学習して」と言うだけです。** URL もファイルも要りません。

Claude Code が自分で YouTube の人気ゆっくり系動画を何本も探して見て、
台本・画面・編集テンポを学び、レムの動画に反映して見比べて直します。
言うたびに新しい動画を見に行くので、言えば言うほど賢くなります。

- 「もっとたくさん見て学習して」 → 見る本数が増えます
- 「この台本のここ硬い」 → 直した結果も覚えます

## 中身（Claude Code 向けメモ）

- `references/scripts/` お手本台本の原文（要約しない）
- `references/frames/` お手本の画面
- `references/metrics/` 編集テンポの測定値
- `references/index.json` 見た動画の一覧
- `corrections/` オーナーの修正ペア（before → after）
- 手順の詳細は `.claude/skills/learn/SKILL.md`
