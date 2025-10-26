"""
Vercel Serverless Functions用のエントリーポイント
"""

from app.main import app

# Vercel の Python ランタイムは ASGI を直接サポート
#app = app
