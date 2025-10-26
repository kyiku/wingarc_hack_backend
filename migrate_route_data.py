"""
route_dataカラムを追加するマイグレーションを実行
"""
import os
from supabase import create_client

# 環境変数から接続情報を取得
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qkduynbjhdyjfyzttmeq.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    print("エラー: SUPABASE_SERVICE_ROLE_KEYが設定されていません")
    print("環境変数を設定してください")
    exit(1)

# Supabaseクライアントを作成（service roleキーを使用）
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# SQLを実行
sql = """
ALTER TABLE public.plans ADD COLUMN IF NOT EXISTS route_data JSONB;
COMMENT ON COLUMN public.plans.route_data IS 'ルート情報（waypoints、total_duration_minutes、stepsなど）をJSON形式で保存';
"""

try:
    result = supabase.rpc("exec_sql", {"sql": sql}).execute()
    print("✅ マイグレーション成功: route_dataカラムを追加しました")
except Exception as e:
    print(f"❌ エラー: {e}")
    print("\n別の方法を試します...")

    # PostgRESTのRPC機能が使えない場合、管理者として直接実行する必要があります
    print("\nSupabaseダッシュボードのSQL Editorで以下のSQLを実行してください:")
    print("https://supabase.com/dashboard/project/qkduynbjhdyjfyzttmeq/sql")
    print("\n" + sql)
