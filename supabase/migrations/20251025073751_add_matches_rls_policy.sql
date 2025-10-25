-- matchesテーブルへの匿名ユーザー（anon）のINSERT、DELETE、SELECTを許可するポリシー
-- スクレイパーがデータベースを更新できるようにするため

-- 既存のポリシーを削除（存在する場合）
DROP POLICY IF EXISTS "Allow anon insert matches" ON public.matches;
DROP POLICY IF EXISTS "Allow anon delete matches" ON public.matches;
DROP POLICY IF EXISTS "Allow anon select matches" ON public.matches;

-- 匿名ユーザーがmatchesテーブルにデータを挿入できるようにする
CREATE POLICY "Allow anon insert matches" ON public.matches
  FOR INSERT
  TO anon
  WITH CHECK (true);

-- 匿名ユーザーがmatchesテーブルからデータを削除できるようにする
-- スクレイパーが古いデータを削除してから新しいデータを挿入するため
CREATE POLICY "Allow anon delete matches" ON public.matches
  FOR DELETE
  TO anon
  USING (true);

-- 匿名ユーザーがmatchesテーブルを読み取れるようにする
CREATE POLICY "Allow anon select matches" ON public.matches
  FOR SELECT
  TO anon
  USING (true);
