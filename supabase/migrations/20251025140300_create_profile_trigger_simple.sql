-- ============================================================
-- profiles テーブルの自動作成トリガー（シンプル版）
-- ============================================================

-- トリガー関数を作成
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- profilesテーブルに新規レコードを挿入
    INSERT INTO public.profiles (id, nickname)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'nickname', ''))
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$;

-- 既存のトリガーを削除
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- トリガーを作成
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 既存ユーザーのprofilesレコードを作成
INSERT INTO public.profiles (id, nickname)
SELECT
    id,
    COALESCE(raw_user_meta_data->>'nickname', '') as nickname
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.profiles)
ON CONFLICT (id) DO NOTHING;
