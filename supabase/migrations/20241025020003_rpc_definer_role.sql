-- Create a least-privilege definer role for RPCs and re-own functions

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_rpc') THEN
    CREATE ROLE app_rpc NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END$$;

-- Grant minimal privileges required by RPC functions
GRANT USAGE ON SCHEMA public TO app_rpc;
GRANT USAGE ON SCHEMA auth TO app_rpc;

-- Read auth.users.email and id (required for get_me_profile)
GRANT SELECT ON TABLE auth.users TO app_rpc;

-- Read/modify public.profiles (required for both RPCs)
GRANT SELECT, INSERT, UPDATE ON TABLE public.profiles TO app_rpc;

-- Re-own the RPC functions to the least-privilege role and harden settings
ALTER FUNCTION public.get_me_profile() OWNER TO app_rpc;
ALTER FUNCTION public.get_me_profile() SECURITY DEFINER;
ALTER FUNCTION public.get_me_profile() SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION public.get_me_profile() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_me_profile() TO authenticated;

ALTER FUNCTION public.update_my_nickname(text) OWNER TO app_rpc;
ALTER FUNCTION public.update_my_nickname(text) SECURITY DEFINER;
ALTER FUNCTION public.update_my_nickname(text) SET search_path = public, pg_temp;
REVOKE ALL ON FUNCTION public.update_my_nickname(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_my_nickname(text) TO authenticated;

