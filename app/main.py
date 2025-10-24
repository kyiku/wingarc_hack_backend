"""
ギラヴァンツ北九州ファンアプリ バックエンドAPI
メインエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 環境変数を読み込み
load_dotenv()

# FastAPIアプリケーションのインスタンス化
app = FastAPI(
    title="ギラヴァンツ北九州ファンアプリ API",
    description="地元の店舗検索と試合日の旅行プラン生成を提供するバックエンドAPI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
