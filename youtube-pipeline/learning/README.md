# 学習のしかた

**Claude Code に「学習して」と言うだけです。** あとは全部 Claude Code がやります。

お手本にしたい動画があれば、URLを一緒に貼ってください:

```
学習して https://www.youtube.com/watch?v=xxxx
```

ほかにもこんな言い方でOK:

- 「この台本のここ硬い。もっと柔らかく」 → 直した結果をClaudeが覚えます
- 「テロップをこの動画みたいにして」＋URL → 画面を見比べて直します
- （台本の .txt を自分で直した後に）「学習して」 → 直した箇所を覚えます

## 中身（Claude Code 向けメモ）

- `references/scripts/` お手本台本の原文（要約しない）
- `references/frames/` お手本の画面
- `corrections/` オーナーの修正ペア（before → after）
- 手順の詳細は `.claude/skills/learn/SKILL.md`
