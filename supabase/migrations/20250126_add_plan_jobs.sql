-- プラン生成ジョブ管理テーブル
CREATE TABLE IF NOT EXISTS plan_generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    current_latitude DECIMAL(10, 8) NOT NULL,
    current_longitude DECIMAL(11, 8) NOT NULL,
    transport_mode TEXT NOT NULL DEFAULT 'drive',
    plan_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_plan_jobs_user_id ON plan_generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_plan_jobs_status ON plan_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_plan_jobs_created_at ON plan_generation_jobs(created_at DESC);

-- RLS (Row Level Security) 有効化
ALTER TABLE plan_generation_jobs ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分のジョブのみ参照・作成可能
CREATE POLICY "Users can view own jobs"
    ON plan_generation_jobs
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own jobs"
    ON plan_generation_jobs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- updated_at自動更新トリガー
CREATE OR REPLACE FUNCTION update_plan_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER plan_jobs_updated_at
    BEFORE UPDATE ON plan_generation_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_plan_jobs_updated_at();
