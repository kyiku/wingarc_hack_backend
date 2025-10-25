-- ============================================================
-- auth.users と public.profiles の結合取得用 RPC
-- およびニックネーム更新用 RPC
-- ============================================================

-- 現在のユーザーの id, email, nickname を返す
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

-- ニックネーム更新＋結合情報を返す
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

