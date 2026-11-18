#!/usr/bin/env python3
"""
再学習コマンド: オーナーが直した台本から「修正の差分」を学習データにする

使い方:
  1. python pipeline.py --stop-after script で台本を作る
  2. output/scripts/ にできた .txt をメモ帳などで直接直して保存
  3. python tools/relearn.py
     → 直した箇所（before → after）が learning/corrections/ に保存され、
       次回の台本生成から自動でAIに見せられる

オプション:
  --file output/scripts/xxx.json   特定の台本だけ学習する（省略時はすべて）
  --promote                        直した台本を丸ごと「お手本台本」にも登録する
  --no-lessons                     差分の要約（気づきの言語化）をAIに頼まない
  --add-pair "直す前" "直した後"    チャットで受けた指摘を修正ペアとして直接保存する
                                   （Claude Code が「学習して」のときに使う）
"""

import argparse
import difflib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from steps import learning  # noqa: E402
from steps.script import read_script_txt  # noqa: E402

SCRIPTS_DIR = BASE_DIR / "output" / "scripts"


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?\n])", text)
    return [p.strip() for p in parts if p.strip()]


def sentence_diffs(before: str, after: str) -> list[dict]:
    """文単位で、変わった箇所だけを before/after のペアにする"""
    a, b = split_sentences(before), split_sentences(after)
    diffs = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        diffs.append({
            "before": "".join(a[i1:i2]) or "（なし）",
            "after": "".join(b[j1:j2]) or "（削除）",
        })
    return diffs


def ask_lessons(diffs: list[dict]) -> list[str]:
    """差分だけを見せて、繰り返し出ている傾向を短く言語化してもらう"""
    import anthropic
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
    client = anthropic.Anthropic()
    listing = "\n".join(f"- before: {d['before']}\n  after: {d['after']}" for d in diffs[:40])
    prompt = (
        "YouTube台本で、AIが書いた文(before)を動画編集者が直した結果(after)の一覧です。\n"
        "一般論ではなく、この差分から実際に読み取れる直し方の傾向だけを、"
        "最大5個、各40字以内の箇条書きで挙げてください。箇条書き以外は出力しないでください。\n\n"
        + listing
    )
    text = learning.call_claude(
        client, learning.DEFAULT_MODEL, "あなたは台本の編集傾向を分析するアシスタントです。",
        prompt, max_tokens=8000, effort="medium",
    )
    return [re.sub(r"^[-・*\d.\s]+", "", line).strip() for line in text.splitlines() if line.strip()][:5]


def relearn_one(json_path: Path, promote: bool, with_lessons: bool) -> bool:
    txt_path = json_path.with_suffix(".txt")
    if not txt_path.exists():
        print(f"  スキップ（.txt がない）: {json_path.name}")
        return False

    original = json.loads(json_path.read_text(encoding="utf-8"))
    edited_sections = read_script_txt(txt_path)
    orig_sections = original.get("sections", [])

    before_all = "\n".join(s["text"] for s in orig_sections)
    after_all = "\n".join(s["text"] for s in edited_sections)
    diffs = sentence_diffs(before_all, after_all)

    if not diffs:
        print(f"  変更なし: {txt_path.name}")
        return False

    lessons = []
    if with_lessons:
        try:
            lessons = ask_lessons(diffs)
        except Exception as e:  # APIキーなしでも差分自体は保存する
            print(f"  （気づきの要約はスキップ: {e}）")

    learning.CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = learning.CORRECTIONS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{json_path.stem}.json"
    out.write_text(json.dumps({
        "source": json_path.name,
        "title": original.get("video_title", ""),
        "learned_at": datetime.now().isoformat(),
        "diffs": diffs,
        "lessons": lessons,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  学習しました: 修正 {len(diffs)} 箇所 → {out.relative_to(BASE_DIR)}")
    for l in lessons:
        print(f"    気づき: {l}")

    if promote:
        learning.REF_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        ref = learning.REF_SCRIPTS_DIR / f"{json_path.stem}.txt"
        ref.write_text(after_all + "\n", encoding="utf-8")
        print(f"  お手本台本に登録: {ref.relative_to(BASE_DIR)}")

    # 直した内容を JSON 側にも反映（音声生成で使われるのは JSON のため）
    if len(edited_sections) == len(orig_sections):
        for o, e in zip(orig_sections, edited_sections):
            o["text"] = e["text"]
        original["owner_edited"] = True
        json_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  台本 JSON にも修正を反映しました（このまま --from-step audio で続行できます）")
    else:
        print("  ※ 見出し(##)の数が変わったため JSON には反映していません")
    return True


def main():
    ap = argparse.ArgumentParser(description="直した台本から再学習する")
    ap.add_argument("--file", type=str, help="対象の台本 JSON")
    ap.add_argument("--promote", action="store_true", help="直した台本をお手本にも登録")
    ap.add_argument("--no-lessons", action="store_true", help="気づきの要約をしない")
    ap.add_argument("--add-pair", nargs=2, metavar=("BEFORE", "AFTER"), action="append",
                    help="修正ペアを直接保存（複数回指定可）")
    ap.add_argument("--source", default="chat", help="--add-pair の出どころメモ")
    args = ap.parse_args()

    if args.add_pair:
        learning.CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
        out = learning.CORRECTIONS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.source}.json"
        out.write_text(json.dumps({
            "source": args.source,
            "learned_at": datetime.now().isoformat(),
            "diffs": [{"before": b, "after": a} for b, a in args.add_pair],
            "lessons": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"修正ペア {len(args.add_pair)} 件を保存: {out.relative_to(BASE_DIR)}")
        return

    targets = [Path(args.file)] if args.file else sorted(SCRIPTS_DIR.glob("*.json"))
    learned_sources = {
        c.get("source") for c in learning.load_corrections(max_items=10_000)
    }
    if not args.file:
        targets = [t for t in targets if t.name not in learned_sources]

    if not targets:
        print("新しく学習する台本はありません。")
        return

    print(f"再学習を開始します（{len(targets)} 本）")
    n = sum(relearn_one(t, args.promote, not args.no_lessons) for t in targets)
    print(f"\n完了: {n} 本から学習しました。次回の台本生成から反映されます。")


if __name__ == "__main__":
    main()
