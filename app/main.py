"""
ギラヴァンツ北九州ファンアプリ バックエンドAPI
メインエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from app.api import users_router, stores_router, plans_router, matches_router, admin_router
from app.scheduler import start_scheduler, shutdown_scheduler, run_scraper_now

# 環境変数を読み込み
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    start_scheduler()
    yield
    # シャットダウン時
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
origins = [
    "http://localhost:3000",  # ローカル開発用フロントエンド
    "http://localhost:8080",
    # 本番環境のドメインは後で追加
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
