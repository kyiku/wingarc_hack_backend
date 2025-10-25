-- storesテーブルへの匿名ユーザー（anon）のINSERT、DELETE、SELECTを許可するポリシー
-- Google Places APIから取得した店舗情報をDBに保存できるようにするため

-- 既存のポリシーを削除（存在する場合）
DROP POLICY IF EXISTS "Allow anon insert stores" ON public.stores;
DROP POLICY IF EXISTS "Allow anon delete stores" ON public.stores;
DROP POLICY IF EXISTS "Allow anon select stores" ON public.stores;
DROP POLICY IF EXISTS "Allow anon update stores" ON public.stores;

-- 匿名ユーザーがstoresテーブルにデータを挿入できるようにする
CREATE POLICY "Allow anon insert stores" ON public.stores
  FOR INSERT
  TO anon
  WITH CHECK (true);

-- 匿名ユーザーがstoresテーブルからデータを削除できるようにする
CREATE POLICY "Allow anon delete stores" ON public.stores
  FOR DELETE
  TO anon
  USING (true);

-- 匿名ユーザーがstoresテーブルを読み取れるようにする
CREATE POLICY "Allow anon select stores" ON public.stores
  FOR SELECT
  TO anon
  USING (true);

-- 匿名ユーザーがstoresテーブルを更新できるようにする
CREATE POLICY "Allow anon update stores" ON public.stores
  FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);
