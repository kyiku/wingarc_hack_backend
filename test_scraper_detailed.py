"""
詳細なHTML構造確認
"""

import urllib.request

url = "https://www.giravanz.jp/game/schedule.html"
print(f"Fetching {url}...")

try:
    with urllib.request.urlopen(url, timeout=30) as response:
        html = response.read().decode('utf-8')

    print(f"✓ Page fetched successfully ({len(html)} bytes)\n")

    # divやtableなどの要素を数える
    print("HTML Structure Analysis:")
    print(f"  <table> tags: {html.count('<table')}")
    print(f"  <div> tags: {html.count('<div')}")
    print(f"  <ul> tags: {html.count('<ul')}")
    print(f"  <li> tags: {html.count('<li')}")
    print(f"  'schedule' mentions: {html.lower().count('schedule')}")
    print(f"  'match' mentions: {html.lower().count('match')}")
    print(f"  '試合' mentions: {html.count('試合')}")

    # JavaScriptがあるかチェック
    if '<script' in html:
        print(f"\n  JavaScript detected: {html.count('<script')} script tags")

    # 試合情報がありそうな部分を探す
    print("\n\nSearching for match-related content...")

    # "vs"や対戦相手っぽいキーワードを探す
    import re
    vs_matches = re.findall(r'vs\s+\S+', html, re.IGNORECASE)
    if vs_matches:
        print(f"\n  Found 'vs' patterns: {len(vs_matches)}")
        for i, match in enumerate(vs_matches[:5]):
            print(f"    {i+1}. {match}")

    # クラス名やIDで試合情報っぽいものを探す
    schedule_divs = re.findall(r'<div[^>]*class="[^"]*schedule[^"]*"[^>]*>', html, re.IGNORECASE)
    if schedule_divs:
        print(f"\n  Found schedule-related divs: {len(schedule_divs)}")

    match_divs = re.findall(r'<div[^>]*class="[^"]*match[^"]*"[^>]*>', html, re.IGNORECASE)
    if match_divs:
        print(f"\n  Found match-related divs: {len(match_divs)}")

    # HTMLの中身を一部表示（試合情報がありそうな部分）
    print("\n\nHTML Sample (first 3000 chars after body tag):")
    body_start = html.find('<body')
    if body_start > 0:
        body_content = html[body_start:body_start+3000]
        print(body_content)
    else:
        print(html[:3000])

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
