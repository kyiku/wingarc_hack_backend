-- ギラヴァンツ北九州周辺の実在する店舗を登録

-- 1. 中華そば 藤王（ラーメン）
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJ9RjpcE2_QzURx6wUFCyuoXA',
  '中華そば 藤王',
  '福岡県北九州市小倉北区',
  33.883778,
  130.879965,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;

-- 2. 小倉稚加栄（高級和食）
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJTejH9k2_QzUR30-W__3wujQ',
  '小倉稚加栄',
  '福岡県北九州市小倉北区',
  33.8826078,
  130.8819948,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;

-- 3. 資さんうどん（Sukesan Udon）
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJM7iJFlm_QzUR15YZHBGUhLw',
  '資さんうどん',
  '福岡県北九州市小倉南区',
  33.872309,
  130.8915833,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;

-- 4. 四方平（よもへい）（居酒屋）
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJzdo-MU2_QzURLI9vfzcIkws',
  '四方平',
  '福岡県北九州市小倉北区',
  33.8853163,
  130.8782194,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;

-- 5. アトル（カフェ・洋食）
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJE1FOF06_QzURjMffFGDRK7g',
  'アトル',
  '福岡県北九州市小倉北区',
  33.8822378,
  130.8839216,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;

-- 6. 天寿司 京町店
INSERT INTO stores (google_place_id, name, address, latitude, longitude, opening_hours)
VALUES (
  'ChIJN17nxk6_QzURPLFr2N4pC-4',
  '天寿司 京町店',
  '福岡県北九州市小倉北区京町',
  33.8852434,
  130.8844203,
  '[]'::jsonb
) ON CONFLICT (google_place_id) DO NOTHING;
