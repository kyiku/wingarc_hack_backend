-- プランテーブルにルート情報を保存するカラムを追加
ALTER TABLE public.plans ADD COLUMN IF NOT EXISTS route_data JSONB;

COMMENT ON COLUMN public.plans.route_data IS 'ルート情報（waypoints、total_duration_minutes、stepsなど）をJSON形式で保存';
