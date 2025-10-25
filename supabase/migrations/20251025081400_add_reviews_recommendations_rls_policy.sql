-- reviewsとplayer_recommendationsテーブルのRLSポリシー

-- reviewsテーブル
DROP POLICY IF EXISTS "Allow anon insert reviews" ON public.reviews;
DROP POLICY IF EXISTS "Allow anon select reviews" ON public.reviews;

CREATE POLICY "Allow anon insert reviews" ON public.reviews
  FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anon select reviews" ON public.reviews
  FOR SELECT
  TO anon
  USING (true);

-- player_recommendationsテーブル
DROP POLICY IF EXISTS "Allow anon insert player_recommendations" ON public.player_recommendations;
DROP POLICY IF EXISTS "Allow anon select player_recommendations" ON public.player_recommendations;

CREATE POLICY "Allow anon insert player_recommendations" ON public.player_recommendations
  FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anon select player_recommendations" ON public.player_recommendations
  FOR SELECT
  TO anon
  USING (true);
