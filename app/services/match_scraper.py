"""
試合情報スクレイピングサービス

ギラヴァンツ北九州の公式サイトから試合情報を取得してDBを更新する
"""

from __future__ import annotations

import re
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

import httpx
from bs4 import BeautifulSoup
import googlemaps

from app.database import get_supabase_client

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 試合スケジュールURL
SCHEDULE_URL = "https://www.giravanz.jp/game/schedule.html"

# 会場名と位置情報のマッピング（フォールバック用）
VENUE_LOCATIONS = {
    "ミクスタ": {
        "name": "ミクニワールドスタジアム北九州",
        "latitude": 33.8850,
        "longitude": 130.8800,
    },
    "ミクニワールドスタジアム北九州": {
        "name": "ミクニワールドスタジアム北九州",
        "latitude": 33.8850,
        "longitude": 130.8800,
    },
}


def get_venue_location(venue_name: str) -> Optional[Dict[str, Any]]:
    """会場名から位置情報を取得

    Args:
        venue_name: 会場名

    Returns:
        位置情報の辞書 {name, latitude, longitude} または None
    """
    # フォールバックマッピングをチェック
    if venue_name in VENUE_LOCATIONS:
        return VENUE_LOCATIONS[venue_name]

    # Google Places APIで検索
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY not set, using fallback locations only")
        return None

    try:
        gmaps = googlemaps.Client(key=api_key)
        # 会場名に「スタジアム」または「競技場」を追加して検索精度を上げる
        search_query = f"{venue_name} スタジアム"
        result = gmaps.geocode(search_query, language="ja")

        if result and len(result) > 0:
            location = result[0]["geometry"]["location"]
            formatted_name = result[0]["formatted_address"]
            return {
                "name": formatted_name,
                "latitude": location["lat"],
                "longitude": location["lng"],
            }
    except Exception as e:
        logger.error(f"Error geocoding venue {venue_name}: {e}")

    return None


def parse_match_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """試合日時文字列をdatetimeに変換

    Args:
        date_str: 日付文字列（例: "2.22(土)"）
        time_str: 時刻文字列（例: "14:00"）

    Returns:
        datetime オブジェクト または None
    """
    try:
        # 年度を取得（現在の年を基準）
        current_year = datetime.now().year

        # 日付をパース（例: "2.22(土)" -> 2月22日）
        match = re.match(r"(\d+)\.(\d+)", date_str)
        if not match:
            return None

        month = int(match.group(1))
        day = int(match.group(2))

        # 時刻をパース（例: "14:00"）
        time_match = re.match(r"(\d+):(\d+)", time_str)
        if not time_match:
            return None

        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        # datetimeオブジェクトを構築
        match_datetime = datetime(current_year, month, day, hour, minute)

        return match_datetime
    except Exception as e:
        logger.error(f"Error parsing datetime from {date_str} {time_str}: {e}")
        return None


def scrape_matches() -> List[Dict[str, Any]]:
    """試合情報をスクレイピング

    Returns:
        試合情報の辞書のリスト
    """
    matches = []

    try:
        # ページを取得
        response = httpx.get(SCHEDULE_URL, timeout=30.0)
        response.raise_for_status()

        # BeautifulSoupでパース
        soup = BeautifulSoup(response.text, "lxml")

        # テーブルを探す
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue

                try:
                    # 各列から情報を抽出
                    # 節、日時、対戦カード、開催地、会場、放送予定
                    date_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    match_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    venue_cell = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                    # 日時を分割（例: "2.22(土) 14:00"）
                    datetime_parts = date_cell.split()
                    if len(datetime_parts) < 2:
                        continue

                    date_str = datetime_parts[0]
                    time_str = datetime_parts[1]

                    # 対戦相手を抽出（例: "北九州 2:0 長野" -> "長野"）
                    # または "vs 〇〇"形式
                    opponent = None
                    if "vs" in match_cell:
                        opponent_match = re.search(r"vs\s+(.+)", match_cell)
                        if opponent_match:
                            opponent = opponent_match.group(1).strip()
                    else:
                        # スコア形式から抽出
                        parts = re.split(r"\d+:\d+", match_cell)
                        if len(parts) >= 2:
                            teams = [p.strip() for p in parts if p.strip()]
                            # 北九州以外のチームを対戦相手とする
                            for team in teams:
                                if "北九州" not in team:
                                    opponent = team
                                    break

                    if not opponent:
                        # 対戦カードから直接抽出を試みる
                        if "北九州" in match_cell:
                            # "北九州" を除外して残りをopponentとする簡易処理
                            opponent = match_cell.replace("北九州", "").strip()
                            # スコアや記号を除去
                            opponent = re.sub(r"[0-9:\-\s]+", " ", opponent).strip()

                    if not opponent:
                        continue

                    # 会場名
                    venue_name = venue_cell
                    if not venue_name:
                        continue

                    # 日時をパース
                    match_datetime = parse_match_datetime(date_str, time_str)
                    if not match_datetime:
                        continue

                    # 会場の位置情報を取得
                    venue_info = get_venue_location(venue_name)
                    if not venue_info:
                        logger.warning(f"Could not get location for venue: {venue_name}")
                        # デフォルト値を使用（ミクスタ）
                        venue_info = VENUE_LOCATIONS.get("ミクスタ", {
                            "name": venue_name,
                            "latitude": 33.8850,
                            "longitude": 130.8800,
                        })

                    match_data = {
                        "match_datetime": match_datetime.isoformat(),
                        "opponent": opponent,
                        "venue_name": venue_info["name"],
                        "venue_latitude": venue_info["latitude"],
                        "venue_longitude": venue_info["longitude"],
                    }

                    matches.append(match_data)
                    logger.info(f"Scraped match: {opponent} on {match_datetime} at {venue_name}")

                except Exception as e:
                    logger.error(f"Error parsing row: {e}")
                    continue

        logger.info(f"Successfully scraped {len(matches)} matches")
        return matches

    except Exception as e:
        logger.error(f"Error scraping matches: {e}")
        return []


def update_matches_db(matches: List[Dict[str, Any]]) -> bool:
    """試合情報をDBに保存（全削除後に再挿入）

    Args:
        matches: 試合情報のリスト

    Returns:
        成功したかどうか
    """
    try:
        supabase = get_supabase_client()

        # 既存の試合情報をすべて削除
        logger.info("Deleting existing matches from database...")
        supabase.table("matches").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

        # 新しい試合情報を挿入
        if matches:
            logger.info(f"Inserting {len(matches)} matches into database...")
            supabase.table("matches").insert(matches).execute()

        logger.info("Database update completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating matches database: {e}")
        return False


def run_scraper():
    """スクレイパーを実行してDBを更新"""
    logger.info("Starting match scraper...")

    # 試合情報をスクレイピング
    matches = scrape_matches()

    if not matches:
        logger.warning("No matches scraped")
        return

    # DBを更新
    success = update_matches_db(matches)

    if success:
        logger.info(f"Successfully updated database with {len(matches)} matches")
    else:
        logger.error("Failed to update database")


if __name__ == "__main__":
    # スクリプトとして直接実行された場合
    from dotenv import load_dotenv
    load_dotenv()
    run_scraper()
