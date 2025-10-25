-- SECURITY NOTE:
--   SECURITY DEFINER のリスクを軽減するためのハードニングです。
--   - 関数の OWNER を特権の少ないロールに委譲（本リポジトリでは後続で app_rpc に変更）。
--   - 実行時の search_path を public, pg_temp に固定し、意図しないスキーマ参照を防止。
--   - PUBLIC からの実行権限を剥奪し、authenticated のみに限定。
--   以降、RPCの本文を変更する場合も、上記前提を崩さないでください。

-- Ensure functions run with controlled privileges and a safe search_path.

-- get_me_profile()
ALTER FUNCTION public.get_me_profile() OWNER TO postgres;
ALTER FUNCTION public.get_me_profile() SECURITY DEFINER;
ALTER FUNCTION public.get_me_profile() SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION public.get_me_profile() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_me_profile() TO authenticated;

-- update_my_nickname(new_nickname text)
ALTER FUNCTION public.update_my_nickname(text) OWNER TO postgres;
ALTER FUNCTION public.update_my_nickname(text) SECURITY DEFINER;
ALTER FUNCTION public.update_my_nickname(text) SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION public.update_my_nickname(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_my_nickname(text) TO authenticated;
