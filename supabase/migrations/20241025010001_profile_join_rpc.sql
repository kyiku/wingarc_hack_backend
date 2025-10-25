-- ============================================================
-- auth.users と public.profiles の結合取得用 RPC
-- およびニックネーム更新用 RPC
-- ============================================================

-- SECURITY NOTE:
--   本関数は SECURITY DEFINER で実行されます。
--   - 必ず auth.uid() による本人限定の条件を維持してください。
--   - 返却カラムは最小限（id/email/nickname）に限定してください。
--   - search_path は後続のハードニングで public, pg_temp に固定しています。
--   - auth.users への参照は将来的にビュー経由（public.v_auth_user）に切替えています。
--     本ファイルを変更する場合も、その方針を踏襲してください。
CREATE OR REPLACE FUNCTION public.get_me_profile()
RETURNS TABLE (
    id UUID,
    email TEXT,
    nickname TEXT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT u.id, u.email, p.nickname
    FROM auth.users AS u
    LEFT JOIN public.profiles AS p ON p.id = u.id
    WHERE u.id = auth.uid()
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_me_profile IS 'auth.users と profiles を結合し、カレントユーザーの id/email/nickname を返す';

GRANT EXECUTE ON FUNCTION public.get_me_profile TO authenticated;

-- SECURITY NOTE:
--   本関数は SECURITY DEFINER で実行されます。
--   - profiles は RLS で auth.uid() によって本人行に限定されています。
--   - UPSERT 対象は auth.uid() の行のみとし、動的SQLは使用しないでください。
--   - 返却は最小限の列に限定してください。
CREATE OR REPLACE FUNCTION public.update_my_nickname(new_nickname TEXT)
RETURNS TABLE (
    id UUID,
    email TEXT,
    nickname TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- プロフィールをUPSERT
    INSERT INTO public.profiles (id, nickname)
    VALUES (auth.uid(), COALESCE(new_nickname, ''))
    ON CONFLICT (id) DO UPDATE SET nickname = EXCLUDED.nickname;

    RETURN QUERY
    SELECT u.id, u.email, p.nickname
    FROM auth.users AS u
    JOIN public.profiles AS p ON p.id = u.id
    WHERE u.id = auth.uid()
    LIMIT 1;
END;
$$;

COMMENT ON FUNCTION public.update_my_nickname IS 'ニックネームを更新し、auth.users と profiles の結合結果を返す';

GRANT EXECUTE ON FUNCTION public.update_my_nickname TO authenticated;
