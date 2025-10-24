# ギラヴァンツ北九州ファンアプリ バックエンドAPI

ギラヴァンツ北九州のサポーターが地元の店舗を発見し、試合日の旅行プランを立てるためのバックエンドAPIです。

## 機能

- ユーザー認証（Supabase）
- 試合情報の取得
- 周辺店舗の検索（Google Places API）
- レビュー投稿
- AI旅行プラン生成（Gemini API）

## 技術スタック

- **フレームワーク**: FastAPI
- **データベース**: Supabase (PostgreSQL)
- **外部API**:
  - Google Places API（店舗情報）
  - Gemini API（旅行プラン生成）

## セットアップ

### 1. 前提条件

- Python 3.9以上
- Supabaseプロジェクト
- Google Places APIキー
- Gemini APIキー

### 2. リポジトリのクローン

```bash
git clone <repository-url>
cd backend
```

### 3. 仮想環境の作成と有効化

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 5. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成します。

```bash
cp .env.example .env
```

`.env`ファイルを編集して、必要な値を設定します：

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_PLACES_API_KEY=your_google_places_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 6. Supabaseデータベースのセットアップ

`DB_specification`ファイルに記載されているスキーマに従って、Supabaseでテーブルを作成してください。

### 7. アプリケーションの起動

```bash
# 開発モード（ホットリロード有効）
python app/main.py

# または uvicornコマンドで直接起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

APIは `http://localhost:8000` で起動します。

### 8. APIドキュメントの確認

ブラウザで以下のURLにアクセスしてAPIドキュメントを確認できます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 9. ヘルスチェック

APIが正常に動作しているか確認します：

```bash
curl http://localhost:8000/health
```

期待される応答：
```json
{
  "status": "healthy",
  "message": "API is running",
  "environment": "development"
}
```

## プロジェクト構造

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIアプリケーションのエントリーポイント
│   ├── api/                 # APIエンドポイント
│   │   └── __init__.py
│   ├── models/              # Pydanticモデル
│   │   └── __init__.py
│   ├── services/            # 外部API連携サービス
│   │   └── __init__.py
│   └── database/            # データベース接続とクエリ
│       └── __init__.py
├── requirements.txt         # 依存パッケージ
├── .env.example            # 環境変数テンプレート
├── .env                    # 環境変数（gitignore対象）
├── API_specification       # API仕様書
├── DB_specification        # データベース仕様書
└── README.md              # このファイル
```

## API仕様

詳細は`API_specification`ファイルを参照してください。

主なエンドポイント：
- `GET /health` - ヘルスチェック
- `GET /users/me` - ユーザープロフィール取得
- `GET /matches` - 試合一覧
- `GET /stores/nearby` - 周辺店舗検索
- `POST /stores/{store_id}/reviews` - レビュー投稿
- `POST /plans/generate` - AI旅行プラン生成
- `GET /plans` - 保存済みプラン一覧

## 開発

### コーディング規約

- 日本語でコメントとドキュメントを記述
- PEP 8に準拠
- 型ヒントを使用

### テスト実行（今後実装予定）

```bash
pytest
```

## ライセンス

（ライセンスを追加してください）
