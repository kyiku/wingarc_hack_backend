-- Restrict access to auth.users via a self-filtered view

CREATE OR REPLACE VIEW public.v_auth_user AS
SELECT id, email
FROM auth.users
WHERE id = auth.uid();

COMMENT ON VIEW public.v_auth_user IS '現在のユーザー（auth.uid()）の id/email のみを公開するビュー';

-- Ensure least-privilege role uses the view instead of raw auth.users
REVOKE SELECT ON TABLE auth.users FROM app_rpc;
GRANT SELECT ON TABLE public.v_auth_user TO app_rpc;

