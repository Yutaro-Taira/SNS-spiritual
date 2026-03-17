#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト
使い方:
  python post.py                  # 今日・今の時間に該当する投稿を実行
  python post.py --dry-run        # 投稿せず内容だけ確認
  python post.py --id 2026-03-16-mon  # 特定の投稿IDを今すぐ投稿
  python post.py --list           # 今週のスケジュール一覧を表示
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tweepy
from dotenv import load_dotenv

# .env 読み込み（このスクリプトの2つ上の階層）
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

CONSUMER_KEY        = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET     = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN        = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

SCHEDULE_DIR = Path(__file__).parent


def detect_schedule_file() -> str:
    """今週の月曜日に対応するスケジュールファイルを自動判別する"""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    filename = f"schedule_week_{monday}.json"
    if (SCHEDULE_DIR / filename).exists():
        return filename
    # 対応ファイルがなければ最新のファイルを使う
    files = sorted(SCHEDULE_DIR.glob("schedule_week_*.json"), reverse=True)
    if files:
        return files[0].name
    return "schedule_week_2026-03-16.json"


def load_schedule(schedule_file: str) -> list[dict]:
    path = SCHEDULE_DIR / schedule_file
    if not path.exists():
        print(f"[ERROR] スケジュールファイルが見つかりません: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_client() -> tweepy.Client:
    missing = [k for k, v in {
        "CONSUMER_KEY": CONSUMER_KEY,
        "CONSUMER_SECRET": CONSUMER_SECRET,
        "ACCESS_TOKEN": ACCESS_TOKEN,
        "ACCESS_TOKEN_SECRET": ACCESS_TOKEN_SECRET,
    }.items() if not v]
    if missing:
        print(f"[ERROR] .env に以下のキーが設定されていません: {', '.join(missing)}")
        sys.exit(1)
    return tweepy.Client(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )


def post_tweet(client: tweepy.Client, text: str, dry_run: bool = False) -> None:
    if dry_run:
        print("[DRY-RUN] 以下の内容を投稿します（実際には送信しません）:")
        print("-" * 50)
        print(text)
        print("-" * 50)
        print(f"文字数: {len(text)} 文字")
        return

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        print(f"[OK] 投稿成功！ Tweet ID: {tweet_id}")
        print(f"     URL: https://x.com/i/web/status/{tweet_id}")
    except tweepy.TweepyException as e:
        print(f"[ERROR] 投稿に失敗しました: {e}")
        sys.exit(1)


def find_todays_posts(schedule: list[dict], window_minutes: int = 30) -> list[dict]:
    """現在時刻 ±window_minutes 分以内の投稿を返す"""
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST).replace(tzinfo=None)
    results = []
    for item in schedule:
        scheduled_dt = datetime.strptime(f"{item['date']} {item['time']}", "%Y-%m-%d %H:%M")
        diff = abs((now - scheduled_dt).total_seconds() / 60)
        if diff <= window_minutes:
            results.append(item)
    return results


def list_schedule(schedule: list[dict]) -> None:
    print(f"{'ID':<25} {'日時':<20} {'テーマ'}")
    print("-" * 65)
    for item in schedule:
        dt_str = f"{item['date']} {item['time']}"
        print(f"{item['id']:<25} {dt_str:<20} {item['theme']}")


def main():
    parser = argparse.ArgumentParser(description="X自動投稿スクリプト")
    parser.add_argument("--schedule", default=None,
                        help="使用するスケジュールファイル名（省略時は今週の日付で自動判別）")
    parser.add_argument("--dry-run", action="store_true",
                        help="投稿せずに内容を確認するだけ")
    parser.add_argument("--id", metavar="POST_ID",
                        help="特定の投稿IDを今すぐ投稿")
    parser.add_argument("--list", action="store_true",
                        help="スケジュール一覧を表示")
    parser.add_argument("--window", type=int, default=30,
                        help="時刻一致の許容範囲（分）。デフォルト30分")
    args = parser.parse_args()

    schedule_file = args.schedule or detect_schedule_file()
    print(f"[INFO] スケジュールファイル: {schedule_file}")
    schedule = load_schedule(schedule_file)

    if args.list:
        list_schedule(schedule)
        return

    client = get_client()

    # 特定IDを指定された場合
    if args.id:
        matches = [item for item in schedule if item["id"] == args.id]
        if not matches:
            print(f"[ERROR] ID '{args.id}' が見つかりません")
            list_schedule(schedule)
            sys.exit(1)
        for item in matches:
            print(f"[INFO] 投稿: {item['theme']} ({item['date']} {item['time']})")
            post_tweet(client, item["text"], dry_run=args.dry_run)
        return

    # 今の時刻に該当する投稿を自動実行
    todays = find_todays_posts(schedule, window_minutes=args.window)
    if not todays:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"[INFO] {now_str} 時点で投稿予定なし（±{args.window}分以内）")
        print("       --list でスケジュールを確認できます")
        return

    for item in todays:
        print(f"[INFO] 投稿: {item['theme']} ({item['date']} {item['time']})")
        post_tweet(client, item["text"], dry_run=args.dry_run)


if __name__ == "__main__":
    main()
