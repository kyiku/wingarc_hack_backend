"""
ギラヴァンツ北九州ファンアプリ バックエンドAPI
メインエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import re
from contextlib import asynccontextmanager
from app.api import users_router, stores_router, plans_router, matches_router, admin_router
from app.scheduler import start_scheduler, shutdown_scheduler, run_scraper_now

# 環境変数を読み込み
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時（Vercel環境ではスケジューラーを無効化）
    is_vercel = os.getenv("VERCEL", "").lower() == "1"
    if not is_vercel:
        start_scheduler()
    yield
    # シャットダウン時
    if not is_vercel:
        shutdown_scheduler()


# FastAPIアプリケーションのインスタンス化
app = FastAPI(
    title="ギラヴァンツ北九州ファンアプリ API",
    description="地元の店舗検索と試合日の旅行プラン生成を提供するバックエンドAPI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS設定
# 開発環境とVercelドメインの両方を許可
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターの登録
app.include_router(users_router)
app.include_router(stores_router)
app.include_router(plans_router)
app.include_router(matches_router)
app.include_router(admin_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    ヘルスチェックエンドポイント

    Returns:
        dict: APIの状態
    """
    return {
        "status": "healthy",
        "message": "API is running",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/", tags=["Root"])
async def root():
    """
    ルートエンドポイント

    Returns:
        dict: API情報
    """
    return {
        "name": "ギラヴァンツ北九州ファンアプリ API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/admin/env-check", tags=["Admin"])
async def check_environment():
    """
    環境変数の状態を確認する（デバッグ用）

    Returns:
        dict: 環境変数の状態
    """
    import googlemaps

    api_key_raw = os.getenv("GOOGLE_PLACES_API_KEY", "")
    api_key_stripped = api_key_raw.strip() if api_key_raw else ""

    return {
        "GOOGLE_PLACES_API_KEY_exists": bool(os.getenv("GOOGLE_PLACES_API_KEY")),
        "GOOGLE_PLACES_API_KEY_prefix_raw": api_key_raw[:10] + "..." if api_key_raw else None,
        "GOOGLE_PLACES_API_KEY_prefix_stripped": api_key_stripped[:10] + "..." if api_key_stripped else None,
        "GOOGLE_PLACES_API_KEY_length_raw": len(api_key_raw),
        "GOOGLE_PLACES_API_KEY_length_stripped": len(api_key_stripped),
        "SUPABASE_URL_exists": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_KEY_exists": bool(os.getenv("SUPABASE_KEY")),
        "GEMINI_API_KEY_exists": bool(os.getenv("GEMINI_API_KEY")),
        "googlemaps_module_available": googlemaps is not None,
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "not set"),
        "VERCEL": os.getenv("VERCEL", "not set"),
    }


@app.post("/admin/scrape-matches", tags=["Admin"])
async def trigger_match_scraper():
    """
    試合情報スクレイパーを手動で実行する（管理者用）

    Returns:
        dict: 実行結果
    """
    try:
        run_scraper_now()
        return {
            "status": "success",
            "message": "Match scraper executed successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run scraper: {str(e)}",
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
