# Python 3.12ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システム依存パッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート8080を公開（Cloud Runのデフォルト）
EXPOSE 8080

# 環境変数でポートを設定
ENV PORT=8080

# Uvicornでアプリケーションを起動
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
