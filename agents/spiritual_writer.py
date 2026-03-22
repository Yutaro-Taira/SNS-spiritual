#!/usr/bin/env python3
"""
LunaVeil_7th (@LunaVeil_7th) 週次投稿スケジュール生成スクリプト

使い方:
  python agents/spiritual_writer.py --week 2026-W14

出力:
  schedules/schedule_2026-W14.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import anthropic

# ------------------------------------------------------------------ #
# スケジュールスロット定義                                            #
# A×9, B×8, C×5 = 合計22件/週                                       #
# (day_offset, time, type, suffix)  day_offset: 0=月〜6=日           #
# ------------------------------------------------------------------ #
SLOT_DEFS = [
    (0, "07:00", "A", 1),   # 月
    (0, "12:00", "B", 2),
    (0, "21:00", "C", 3),
    (1, "07:00", "A", 1),   # 火
    (1, "12:00", "B", 2),
    (1, "21:00", "A", 3),
    (2, "07:00", "A", 1),   # 水
    (2, "12:00", "B", 2),
    (2, "15:00", "C", 3),
    (2, "21:00", "B", 4),
    (3, "07:00", "A", 1),   # 木
    (3, "12:00", "B", 2),
    (3, "21:00", "C", 3),
    (4, "07:00", "A", 1),   # 金
    (4, "12:00", "B", 2),
    (4, "21:00", "A", 3),
    (5, "12:00", "A", 1),   # 土
    (5, "15:00", "B", 2),
    (5, "21:00", "C", 3),
    (6, "07:00", "A", 1),   # 日
    (6, "12:00", "B", 2),
    (6, "21:00", "C", 3),
]

DAY_ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# 週間テーマ: タロット大アルカナ22枚 → 週番号 % 22 で循環
WEEKLY_THEMES = [
    "「愚者（The Fool）」新しい始まり・勇気・自由",
    "「魔術師（The Magician）」意志力・実現・スキル",
    "「女教皇（The High Priestess）」直感・内なる知恵・神秘",
    "「女帝（The Empress）」豊かさ・愛・創造",
    "「皇帝（The Emperor）」安定・権威・構造",
    "「法王（The Hierophant）」伝統・信念・導き",
    "「恋人（The Lovers）」選択・調和・パートナーシップ",
    "「戦車（The Chariot）」勝利・意志・前進",
    "「力（Strength）」内なる強さ・忍耐・勇気",
    "「隠者（The Hermit）」内省・孤独・知恵",
    "「運命の輪（Wheel of Fortune）」転機・サイクル・流れ",
    "「正義（Justice）」バランス・真実・公正",
    "「吊られた男（The Hanged Man）」視点転換・待機・受容",
    "「死神（Death）」変容・終わりと始まり・再生",
    "「節制（Temperance）」調和・バランス・癒し",
    "「悪魔（The Devil）」執着からの解放・物質・束縛",
    "「塔（The Tower）」急変・解放・気づき",
    "「星（The Star）」希望・信頼・癒し",
    "「月（The Moon）」潜在意識・夢・直感",
    "「太陽（The Sun）」喜び・活力・成功",
    "「審判（Judgement）」覚醒・再生・使命",
    "「世界（The World）」完成・統合・達成",
]

SYSTEM_PROMPT = """あなたはスピリチュアル系Xアカウント「@LunaVeil_7th」の投稿ライターです。

## アカウントコンセプト
- ターゲット: 20〜30代女性
- ジャンル: タロット・星座・数秘術・スピリチュアル
- トーン: 温かみがある・友達みたいな親しみやすさ・励まし・ポジティブ
- 特徴: ひらがな多め、絵文字あり、#ハッシュタグあり、140文字以内

## 投稿タイプ別ガイドライン
- タイプA（情報提供・占い）: タロット解説、今日の星読み、数秘術、パワーストーン、恋愛占い、開運アクション。知識を親しみやすく伝える。
- タイプB（共感・あるある）: 星座あるある、数秘術あるある、引き寄せ習慣。「わかるー！」と思わせる共感コンテンツ。
- タイプC（参加型）: 朝・夜の問いかけ、読者へのコメント誘導。「コメントで教えてね」などの呼びかけを含める。

## 制約
- 各投稿は必ず140文字以内（ハッシュタグ込み）
- 投稿タイプ（A/B/C）の特性を守る
- 同じ表現・絵文字の繰り返しを避け、バリエーションをつける
- 週間テーマとの関連性を意識しつつも、自然な流れで"""


def parse_week(week_str: str) -> date:
    """'2026-W14' → その週の月曜日の date を返す"""
    try:
        year_part, week_part = week_str.split("-W")
        monday = date.fromisocalendar(int(year_part), int(week_part), 1)
        return monday
    except Exception:
        print(f"[ERROR] 週の形式が無効です: {week_str}（例: 2026-W14）")
        sys.exit(1)


def build_slots(monday: date) -> list[dict]:
    """スロット定義から id・date・time・type を確定したリストを返す"""
    slots = []
    for day_offset, time_str, post_type, suffix in SLOT_DEFS:
        d = monday + timedelta(days=day_offset)
        date_str = d.strftime("%Y-%m-%d")
        day_abbr = DAY_ABBR[day_offset]
        slots.append({
            "id": f"{date_str}-{day_abbr}-{suffix}",
            "date": date_str,
            "time": time_str,
            "type": post_type,
        })
    return slots


def get_weekly_theme(monday: date) -> str:
    """週番号を使ってタロットテーマを循環選択する"""
    week_num = monday.isocalendar()[1]
    return WEEKLY_THEMES[(week_num - 1) % len(WEEKLY_THEMES)]


def build_prompt(weekly_theme: str, slots: list[dict]) -> str:
    slot_lines = "\n".join(
        f"  {i+1:2d}. id={s['id']}  {s['date']} {s['time']}  タイプ{s['type']}"
        for i, s in enumerate(slots)
    )
    return f"""今週のタロット週間テーマ: {weekly_theme}

以下の22件のスロットについて、テーマと本文を生成してください。

{slot_lines}

## 出力ルール
- 必ずJSON配列のみ出力してください（説明文・マークダウン不要）
- 各オブジェクトのキー: id, date, time, type, theme, text
- id/date/time/type は上記の値をそのまま使用
- theme: 投稿テーマ名（例: 「今日の星読み」「牡羊座あるある」など）
- text: 本文（140文字以内、絵文字・ハッシュタグ含む）
- タイプA×9件、タイプB×8件、タイプC×5件になるように生成

出力例:
[
  {{
    "id": "2026-04-06-mon-1",
    "date": "2026-04-06",
    "time": "07:00",
    "type": "A",
    "theme": "週間タロット",
    "text": "今週のカードは「星（The Star）」✨\\n希望と癒しのエネルギーが満ちる週。\\nうまくいかなかったことも、きっと次につながってるよ🌟\\n#タロット #スピリチュアル"
  }}
]"""


def call_claude_api(
    client: anthropic.Anthropic, prompt: str, max_retries: int = 2
) -> str:
    """Claude API を呼び出す。失敗時は最大 max_retries 回リトライする。"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            last_error = e
            if attempt < max_retries:
                wait_sec = 2 ** attempt
                print(
                    f"[WARN] API エラー（試行 {attempt + 1}/{max_retries + 1}）: {e}"
                    f"  → {wait_sec}秒後にリトライ..."
                )
                time.sleep(wait_sec)
    print(f"[ERROR] Claude API の呼び出しに失敗しました: {last_error}")
    sys.exit(1)


def extract_json_array(text: str) -> list[dict]:
    """レスポンステキストから JSON 配列を取り出す"""
    # ```json ... ``` フェンスがある場合は除去
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    json_str = m.group(1) if m else text.strip()

    try:
        data = json.loads(json_str)
        if not isinstance(data, list):
            raise ValueError("JSON のルートが配列ではありません")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] JSON のパースに失敗しました: {e}")
        print(f"[DEBUG] レスポンス先頭 500 文字:\n{text[:500]}")
        sys.exit(1)


def merge_with_slots(slots: list[dict], generated: list[dict]) -> list[dict]:
    """
    生成結果をスロット定義と照合し、id/date/time/type はスロット定義を優先する。
    IDが一致しない場合は位置（インデックス）でフォールバックする。
    """
    gen_by_id = {item.get("id", ""): item for item in generated}
    result = []
    for i, slot in enumerate(slots):
        if slot["id"] in gen_by_id:
            merged = {**gen_by_id[slot["id"]], **slot}
        elif i < len(generated):
            print(f"[WARN] ID '{slot['id']}' が見当たりません。インデックス {i} の生成結果を使用します。")
            merged = {**generated[i], **slot}
        else:
            print(f"[WARN] スロット '{slot['id']}' に対応する生成結果がありません。")
            merged = {**slot, "theme": "（未生成）", "text": "（未生成）"}

        # 必須フィールドの確認
        for key in ("theme", "text"):
            if key not in merged or not merged[key]:
                merged[key] = "（未生成）"

        result.append(merged)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LunaVeil_7th 週次投稿スケジュール生成"
    )
    parser.add_argument(
        "--week",
        required=True,
        metavar="YYYY-Www",
        help="対象週（例: 2026-W14）",
    )
    args = parser.parse_args()

    # 環境変数チェック
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] 環境変数 ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # 週の計算
    monday = parse_week(args.week)
    sunday = monday + timedelta(days=6)
    print(f"[INFO] 対象週: {args.week}  （{monday} 〜 {sunday}）")

    # スロット構築
    slots = build_slots(monday)

    # 週間テーマ選択
    weekly_theme = get_weekly_theme(monday)
    print(f"[INFO] 週間テーマ: {weekly_theme}")

    # Claude API で投稿テキスト生成
    print(f"[INFO] Claude API で {len(slots)} 件の投稿テキストを生成中...")
    prompt = build_prompt(weekly_theme, slots)
    raw_response = call_claude_api(client, prompt)

    # JSON 抽出・マージ
    generated = extract_json_array(raw_response)
    print(f"[INFO] {len(generated)} 件の投稿テキストを受信")
    schedule = merge_with_slots(slots, generated)

    # 出力先
    repo_root = Path(__file__).parent.parent
    output_dir = repo_root / "schedules"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"schedule_{args.week}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f"✅ {output_path.name} を生成しました")


if __name__ == "__main__":
    main()
