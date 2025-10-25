-- ============================================================
-- ギラヴァンツ北九州ファンアプリ データベーススキーマ
-- 初期マイグレーション
-- ============================================================

-- UUID拡張を有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- テーブル作成
-- ============================================================

-- ------------------------------------------------------------
-- profiles テーブル (ユーザープロフィール)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nickname TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.profiles IS 'ユーザープロフィール情報';
COMMENT ON COLUMN public.profiles.id IS 'auth.users.idへの外部キー';
COMMENT ON COLUMN public.profiles.nickname IS 'ユーザーが設定するニックネーム';

-- ------------------------------------------------------------
-- matches テーブル (試合情報)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_datetime TIMESTAMPTZ NOT NULL,
    opponent TEXT NOT NULL,
    venue_name TEXT NOT NULL,
    venue_latitude FLOAT8 NOT NULL,
    venue_longitude FLOAT8 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.matches IS 'ギラヴァンツ北九州の試合情報';
COMMENT ON COLUMN public.matches.match_datetime IS '試合日時（タイムゾーン付き）';
COMMENT ON COLUMN public.matches.opponent IS '対戦相手';
COMMENT ON COLUMN public.matches.venue_name IS '試合会場名';
COMMENT ON COLUMN public.matches.venue_latitude IS '会場の緯度';
COMMENT ON COLUMN public.matches.venue_longitude IS '会場の経度';

-- ------------------------------------------------------------
-- stores テーブル (店舗情報)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    google_place_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude FLOAT8 NOT NULL,
    longitude FLOAT8 NOT NULL,
    opening_hours JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.stores IS '店舗情報（Google Places APIから取得）';
COMMENT ON COLUMN public.stores.google_place_id IS 'Google PlaceのID（重複登録防止用）';
COMMENT ON COLUMN public.stores.name IS '店舗名';
COMMENT ON COLUMN public.stores.address IS '住所';
COMMENT ON COLUMN public.stores.latitude IS '緯度';
COMMENT ON COLUMN public.stores.longitude IS '経度';
COMMENT ON COLUMN public.stores.opening_hours IS '営業時間の構造化データ（JSON）';

-- ------------------------------------------------------------
-- chain_stores テーブル (チェーン店リスト)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chain_stores (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

COMMENT ON TABLE public.chain_stores IS 'フィルタリングで除外する大手チェーン店リスト';
COMMENT ON COLUMN public.chain_stores.name IS 'チェーン店名';

-- ------------------------------------------------------------
-- reviews テーブル (口コミ)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES public.stores(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.reviews IS 'ユーザーが投稿する口コミ情報';
COMMENT ON COLUMN public.reviews.store_id IS 'stores.idへの外部キー';
COMMENT ON COLUMN public.reviews.user_id IS 'auth.users.idへの外部キー';
COMMENT ON COLUMN public.reviews.rating IS '評価（1〜5）';
COMMENT ON COLUMN public.reviews.comment IS '口コミ本文';

-- ------------------------------------------------------------
-- player_recommendations テーブル (選手のおすすめ)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.player_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES public.stores(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.player_recommendations IS '運営が登録する選手のおすすめ情報';
COMMENT ON COLUMN public.player_recommendations.store_id IS 'stores.idへの外部キー';
COMMENT ON COLUMN public.player_recommendations.player_name IS '選手名';
COMMENT ON COLUMN public.player_recommendations.comment IS 'おすすめコメント';

-- ------------------------------------------------------------
-- plans テーブル (保存したプラン)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    plan_details TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE public.plans IS 'ユーザーが保存した旅行プラン';
COMMENT ON COLUMN public.plans.user_id IS 'auth.users.idへの外部キー';
COMMENT ON COLUMN public.plans.match_id IS 'matches.idへの外部キー';
COMMENT ON COLUMN public.plans.title IS 'プランのタイトル';
COMMENT ON COLUMN public.plans.plan_details IS 'Geminiが生成したプランの本文';

-- ============================================================
-- インデックスの作成（パフォーマンス最適化）
-- ============================================================

-- stores テーブル
CREATE INDEX IF NOT EXISTS idx_stores_google_place_id ON public.stores(google_place_id);
CREATE INDEX IF NOT EXISTS idx_stores_location ON public.stores(latitude, longitude);

-- reviews テーブル
CREATE INDEX IF NOT EXISTS idx_reviews_store_id ON public.reviews(store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON public.reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON public.reviews(created_at DESC);

-- player_recommendations テーブル
CREATE INDEX IF NOT EXISTS idx_player_recommendations_store_id ON public.player_recommendations(store_id);

-- plans テーブル
CREATE INDEX IF NOT EXISTS idx_plans_user_id ON public.plans(user_id);
CREATE INDEX IF NOT EXISTS idx_plans_match_id ON public.plans(match_id);
CREATE INDEX IF NOT EXISTS idx_plans_created_at ON public.plans(created_at DESC);

-- matches テーブル
CREATE INDEX IF NOT EXISTS idx_matches_datetime ON public.matches(match_datetime DESC);
CREATE INDEX IF NOT EXISTS idx_matches_location ON public.matches(venue_latitude, venue_longitude);

-- ============================================================
-- Row Level Security (RLS) ポリシーの設定
-- ============================================================

-- ------------------------------------------------------------
-- profiles テーブル
-- ------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分のプロフィールのみ閲覧可能
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

-- ユーザーは自分のプロフィールのみ更新可能
CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- ------------------------------------------------------------
-- matches テーブル
-- ------------------------------------------------------------
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- 試合情報は全ユーザーが閲覧可能（認証済み・未認証問わず）
CREATE POLICY "Anyone can view matches"
    ON public.matches FOR SELECT
    TO authenticated, anon
    USING (true);

-- ------------------------------------------------------------
-- stores テーブル
-- ------------------------------------------------------------
ALTER TABLE public.stores ENABLE ROW LEVEL SECURITY;

-- 店舗情報は全ユーザーが閲覧可能
CREATE POLICY "Anyone can view stores"
    ON public.stores FOR SELECT
    TO authenticated, anon
    USING (true);

-- ------------------------------------------------------------
-- chain_stores テーブル
-- ------------------------------------------------------------
ALTER TABLE public.chain_stores ENABLE ROW LEVEL SECURITY;

-- チェーン店リストは全ユーザーが閲覧可能
CREATE POLICY "Anyone can view chain stores"
    ON public.chain_stores FOR SELECT
    TO authenticated, anon
    USING (true);

-- ------------------------------------------------------------
-- reviews テーブル
-- ------------------------------------------------------------
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;

-- レビューは全ユーザーが閲覧可能
CREATE POLICY "Anyone can view reviews"
    ON public.reviews FOR SELECT
    TO authenticated, anon
    USING (true);

-- 認証済みユーザーのみレビューを投稿可能
CREATE POLICY "Authenticated users can create reviews"
    ON public.reviews FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- ユーザーは自分のレビューのみ更新可能
CREATE POLICY "Users can update their own reviews"
    ON public.reviews FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

-- ユーザーは自分のレビューのみ削除可能
CREATE POLICY "Users can delete their own reviews"
    ON public.reviews FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- ------------------------------------------------------------
-- player_recommendations テーブル
-- ------------------------------------------------------------
ALTER TABLE public.player_recommendations ENABLE ROW LEVEL SECURITY;

-- 選手のおすすめは全ユーザーが閲覧可能
CREATE POLICY "Anyone can view player recommendations"
    ON public.player_recommendations FOR SELECT
    TO authenticated, anon
    USING (true);

-- ------------------------------------------------------------
-- plans テーブル
-- ------------------------------------------------------------
ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分のプランのみ閲覧可能
CREATE POLICY "Users can view their own plans"
    ON public.plans FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- ユーザーは自分のプランのみ作成可能
CREATE POLICY "Users can create their own plans"
    ON public.plans FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- ユーザーは自分のプランのみ更新可能
CREATE POLICY "Users can update their own plans"
    ON public.plans FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

-- ユーザーは自分のプランのみ削除可能
CREATE POLICY "Users can delete their own plans"
    ON public.plans FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- ============================================================
-- トリガーとファンクション
-- ============================================================

-- ------------------------------------------------------------
-- プロフィール自動作成用のトリガー
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, nickname)
    VALUES (NEW.id, '');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 既存のトリガーを削除してから作成（冪等性のため）
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user IS 'auth.usersに新規ユーザーが追加されたら、自動的にprofilesテーブルにレコードを作成';

-- ------------------------------------------------------------
-- updated_at自動更新用のトリガー
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- profilesテーブルのupdated_at自動更新トリガー
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

COMMENT ON FUNCTION public.update_updated_at_column IS 'updated_atカラムを自動的に現在時刻に更新';

-- ============================================================
-- 完了メッセージ
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '===================================================';
    RAISE NOTICE 'データベーススキーマの初期化が完了しました！';
    RAISE NOTICE '===================================================';
    RAISE NOTICE '作成されたテーブル:';
    RAISE NOTICE '  - profiles (ユーザープロフィール)';
    RAISE NOTICE '  - matches (試合情報)';
    RAISE NOTICE '  - stores (店舗情報)';
    RAISE NOTICE '  - chain_stores (チェーン店リスト)';
    RAISE NOTICE '  - reviews (口コミ)';
    RAISE NOTICE '  - player_recommendations (選手のおすすめ)';
    RAISE NOTICE '  - plans (保存したプラン)';
    RAISE NOTICE '===================================================';
END $$;
