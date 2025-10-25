-- Recreate RPCs to depend on the self-filtered auth view

CREATE OR REPLACE FUNCTION public.get_me_profile()
RETURNS TABLE (
    id UUID,
    email TEXT,
    nickname TEXT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT u.id, u.email, p.nickname
    FROM public.v_auth_user AS u
    LEFT JOIN public.profiles AS p ON p.id = u.id
    WHERE u.id = auth.uid()
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_me_profile IS 'auth.usersとprofilesの結合（view経由）: カレントユーザーのみ返す';

-- update_my_nickname keeps UPSERT behavior and joins via view for email
CREATE OR REPLACE FUNCTION public.update_my_nickname(new_nickname TEXT)
RETURNS TABLE (
    id UUID,
    email TEXT,
    nickname TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    -- 未認証（auth.uid() IS NULL）の場合はエラー
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'unauthenticated';
    END IF;
    -- プロフィールをUPSERT（RLSにより auth.uid() 本人に限定）
    INSERT INTO public.profiles (id, nickname)
    VALUES (auth.uid(), COALESCE(new_nickname, ''))
    ON CONFLICT (id) DO UPDATE SET nickname = EXCLUDED.nickname;

    RETURN QUERY
    SELECT u.id, u.email, p.nickname
    FROM public.v_auth_user AS u
    JOIN public.profiles AS p ON p.id = u.id
    WHERE u.id = auth.uid()
    LIMIT 1;
END;
$$;

COMMENT ON FUNCTION public.update_my_nickname IS 'ニックネーム更新＋結合（view経由）: カレントユーザーのみ返す';
