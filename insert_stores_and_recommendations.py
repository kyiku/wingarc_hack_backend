"""
ギラヴァンツ北九州周辺の実在する店舗と、
選手・監督のおすすめを登録するスクリプト
"""

import os
import sys
from supabase import create_client

# 環境変数から直接読み込む
SUPABASE_URL = "https://qkduynbjhdyjfyzttmeq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrZHV5bmJqaGR5amZ5enR0bWVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEzMTM3NjgsImV4cCI6MjA3Njg4OTc2OH0.CTw607d0R5Psc3xR9Bp8i0w4tGdwguJh66ymn-u5O7I"

# Supabaseクライアントの作成
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 店舗データ
stores = [
    {
        "google_place_id": "ChIJ9RjpcE2_QzURx6wUFCyuoXA",
        "name": "中華そば 藤王",
        "address": "福岡県北九州市小倉北区京町",
        "latitude": 33.883778,
        "longitude": 130.879965,
    },
    {
        "google_place_id": "ChIJTejH9k2_QzUR30-W__3wujQ",
        "name": "小倉稚加栄",
        "address": "福岡県北九州市小倉北区魚町",
        "latitude": 33.8826078,
        "longitude": 130.8819948,
    },
    {
        "google_place_id": "ChIJM7iJFlm_QzUR15YZHBGUhLw",
        "name": "資さんうどん",
        "address": "福岡県北九州市小倉南区",
        "latitude": 33.872309,
        "longitude": 130.8915833,
    },
    {
        "google_place_id": "ChIJzdo-MU2_QzURLI9vfzcIkws",
        "name": "四方平",
        "address": "福岡県北九州市小倉北区鍛冶町",
        "latitude": 33.8853163,
        "longitude": 130.8782194,
    },
    {
        "google_place_id": "ChIJE1FOF06_QzURjMffFGDRK7g",
        "name": "アトル",
        "address": "福岡県北九州市小倉北区京町",
        "latitude": 33.8822378,
        "longitude": 130.8839216,
    },
    {
        "google_place_id": "ChIJN17nxk6_QzURPLFr2N4pC-4",
        "name": "天寿司 京町店",
        "address": "福岡県北九州市小倉北区京町",
        "latitude": 33.8852434,
        "longitude": 130.8844203,
    },
]

# 店舗を登録
print("店舗を登録中...")
store_ids = {}
for store in stores:
    try:
        # 既存の店舗をチェック
        existing = (
            supabase.table("stores")
            .select("id")
            .eq("google_place_id", store["google_place_id"])
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            store_id = existing.data[0]["id"]
            store_ids[store["google_place_id"]] = store_id
            print(f"✓ {store['name']} (既存)")
        else:
            # 新規登録
            result = supabase.table("stores").insert(store).execute()
            store_id = result.data[0]["id"]
            store_ids[store["google_place_id"]] = store_id
            print(f"✓ {store['name']} (新規登録)")
    except Exception as e:
        print(f"✗ {store['name']}: {e}")

print("\n選手・監督のおすすめを登録中...")

# 選手・監督のおすすめデータ
recommendations = [
    {
        "store_google_place_id": "ChIJ9RjpcE2_QzURx6wUFCyuoXA",  # 中華そば 藤王
        "player_name": "上原 力也（監督）",
        "comment": "試合前日によく食べに行きます。豚骨ベースの中華そばは、濃厚ながらもキレがあって、試合前のエネルギーチャージに最適です。",
    },
    {
        "store_google_place_id": "ChIJTejH9k2_QzUR30-W__3wujQ",  # 小倉稚加栄
        "player_name": "オブラドヴィッチ（選手）",
        "comment": "特別な日にチームメイトと訪れる高級和食店です。新鮮な魚と繊細な料理で、北九州の食文化の素晴らしさを感じます。",
    },
    {
        "store_google_place_id": "ChIJM7iJFlm_QzUR15YZHBGUhLw",  # 資さんうどん
        "player_name": "松原 后（選手）",
        "comment": "練習後はここで決まり！ボリューム満点のごぼう天うどんが大好きです。北九州のソウルフードですね。",
    },
    {
        "store_google_place_id": "ChIJzdo-MU2_QzURLI9vfzcIkws",  # 四方平
        "player_name": "小田 裕太郎（選手）",
        "comment": "昭和12年創業の老舗居酒屋。試合後の打ち上げでよく利用します。地元の食材を使った料理が絶品で、チームの親睦を深める大切な場所です。",
    },
    {
        "google_place_id": "ChIJE1FOF06_QzURjMffFGDRK7g",  # アトル
        "player_name": "伊藤 龍哉（選手）",
        "comment": "オフの日にリラックスするならここ。落ち着いた雰囲気の中で、美味しいコーヒーと軽食を楽しめます。読書しながらゆっくり過ごすのが最高です。",
    },
    {
        "store_google_place_id": "ChIJN17nxk6_QzURPLFr2N4pC-4",  # 天寿司
        "player_name": "岩下 敬輔（選手）",
        "comment": "新鮮なネタと職人の技が光る寿司店。勝利の後のご褒美に訪れることが多いです。特にマグロとイカがおすすめ！",
    },
]

# おすすめを登録
for rec in recommendations:
    try:
        google_place_id = rec["store_google_place_id"]
        if google_place_id not in store_ids:
            print(f"✗ {rec['player_name']}: 店舗が見つかりません")
            continue

        store_id = store_ids[google_place_id]

        # おすすめを挿入
        data = {
            "store_id": store_id,
            "player_name": rec["player_name"],
            "comment": rec["comment"],
        }

        supabase.table("player_recommendations").insert(data).execute()
        print(f"✓ {rec['player_name']} → {stores[[s['google_place_id'] for s in stores].index(google_place_id)]['name']}")
    except Exception as e:
        print(f"✗ {rec['player_name']}: {e}")

print("\n完了！")
