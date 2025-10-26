-- ============================================================
-- profiles テーブルのトリガー修正
-- 問題: handle_new_user() トリガーがRLSによってブロックされる
-- 解決: トリガー関数に適切な権限を付与
-- ============================================================

-- handle_new_user()関数を再定義（RLSをバイパスできるように）
-- SECURITY DEFINERで、OWNERをpostgres（スーパーユーザー）にする
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public, pg_temp
LANGUAGE plpgsql
AS $$
BEGIN
    -- profilesテーブルに新規レコードを挿入
    -- SECURITY DEFINERとpostgres OWNERにより、RLSをバイパス
    INSERT INTO public.profiles (id, nickname)
    VALUES (NEW.id, '')
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$;

-- 関数のOWNERをpostgres（スーパーユーザー）に設定
ALTER FUNCTION public.handle_new_user() OWNER TO postgres;

-- トリガーを再作成（既存のものを削除してから）
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user IS '新規ユーザー登録時にprofilesテーブルへレコードを自動作成（RLSバイパス付き）';
