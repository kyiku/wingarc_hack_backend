"""
簡易スクレイピングテスト（依存関係最小）
"""

import urllib.request
import re
from datetime import datetime

# ページを取得
url = "https://www.giravanz.jp/game/schedule.html"
print(f"Fetching {url}...")

try:
    with urllib.request.urlopen(url, timeout=30) as response:
        html = response.read().decode('utf-8')

    print(f"✓ Page fetched successfully ({len(html)} bytes)")

    # 簡易的なHTMLパース（tableタグを探す）
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    print(f"✓ Found {len(tables)} table(s)")

    # 試合データっぽい行を探す（td要素が複数ある行）
    match_count = 0
    for table in tables[:3]:  # 最初の3つのテーブルだけチェック
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 4:
                # セルの内容を表示（HTMLタグを除去）
                cell_texts = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]

                # 日付らしき文字列があるかチェック（例: "2.22(土)"）
                if any(re.search(r'\d+\.\d+', text) for text in cell_texts):
                    match_count += 1
                    if match_count <= 3:  # 最初の3試合だけ表示
                        print(f"\nMatch {match_count}:")
                        for i, text in enumerate(cell_texts[:6]):  # 最初の6列
                            if text:
                                print(f"  Column {i}: {text[:100]}")  # 最大100文字

    print(f"\n✓ Found approximately {match_count} match rows")

    if match_count == 0:
        print("\n⚠️  No matches found. HTML structure may have changed.")
        print("\nFirst 1000 characters of HTML:")
        print(html[:1000])
    else:
        print("\n✓ Scraping structure looks OK!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
