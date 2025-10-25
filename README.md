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

Supabase CLIを使ってデータベーススキーマを作成します。

#### 前提条件

Supabase CLIがインストールされていること（まだの場合）:

```bash
# macOS / Linux
brew install supabase/tap/supabase

# npm経由
npm install -g supabase
```

#### 手順

**プロジェクトは既にリンク済みです。**以下のコマンドでマイグレーションをプッシュできます：

```bash
# マイグレーションをリモートデータベースに適用
supabase db push
```

**新しい開発者がセットアップする場合**:

```bash
# 1. リモートプロジェクトにリンク
supabase link --project-ref qkduynbjhdyjfyzttmeq

# 2. マイグレーションを適用
supabase db push
```

#### テーブル作成の確認

以下のテーブルが作成されます：
- `profiles` - ユーザープロフィール
- `matches` - 試合情報
- `stores` - 店舗情報
- `chain_stores` - チェーン店リスト
- `reviews` - 口コミ
- `player_recommendations` - 選手のおすすめ
- `plans` - 保存したプラン

確認方法：
```bash
# データベース状態を確認
supabase db diff

# または、Supabaseダッシュボードで確認
# https://supabase.com/dashboard/project/qkduynbjhdyjfyzttmeq
```

#### マイグレーションに含まれる設定

- **外部キー制約**: テーブル間のリレーションシップを保証
- **CHECK制約**: reviews.ratingを1〜5に制限
- **UNIQUE制約**: stores.google_place_id、chain_stores.nameの重複を防止
- **Row Level Security (RLS)**: テーブルごとのアクセス制御
  - profiles: ユーザー自身のみ閲覧・更新可能
  - reviews: 認証済みユーザーのみ投稿可能
  - plans: ユーザー自身のプランのみ閲覧・作成可能
- **インデックス**: 緯度経度検索、日時ソートなどのパフォーマンス最適化
- **トリガー**:
  - 新規ユーザー登録時に自動的にprofilesレコードを作成
  - profiles.updated_atの自動更新

#### 新しいマイグレーションの作成

今後、スキーマを変更する場合:

```bash
# 新しいマイグレーションファイルを作成
supabase migration new your_migration_name

# マイグレーションを適用
supabase db push
```

### 7. アプリケーションの起動

#### A. 標準の起動（既存のvenv使用）

```bash
# 開発モード（ホットリロード有効）
python app/main.py

# または uvicornコマンドで直接起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

APIは `http://localhost:8000` で起動します。

#### B. uvを使った起動（お好みで）

uv を使うと、依存解決と実行を簡潔に行えます。既存の `venv` を使う方法と、uv 管理の仮想環境を使う方法の2通りがあります。

- 既存の `venv` を使って実行（依存は `pip install -r requirements.txt` 済みを想定）

  - Windows:
    ```bash
    uv run --python venv/Scripts/python.exe app/main.py
    ```

  - macOS/Linux:
    ```bash
    uv run --python venv/bin/python app/main.py
    ```

- uv 管理の仮想環境で実行（venv 未作成でも可）

  ```bash
  # 必要に応じて環境を作成
  uv venv
  # requirements を同期
  uv pip sync -r requirements.txt
  # 実行（ホットリロード含むエントリポイントは app/main.py）
  uv run app/main.py
  ```

  直接 uvicorn を使いたい場合は以下でもOKです：

  ```bash
  uv run -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

ポートは `.env` の `PORT`（未設定時は 8000）を使用します。

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
│   ├── api/                 # APIエンドポイント（今後実装）
│   │   └── __init__.py
│   ├── models/              # Pydanticモデル（今後実装）
│   │   └── __init__.py
│   ├── services/            # 外部API連携サービス（今後実装）
│   │   └── __init__.py
│   └── database/            # データベース接続とクエリ（今後実装）
│       └── __init__.py
├── supabase/                # Supabase CLI設定
│   ├── config.toml         # Supabase設定ファイル
│   └── migrations/         # データベースマイグレーション
│       └── 20241025000000_initial_schema.sql  # 初期スキーマ
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

## 試合情報の自動更新

### 概要

アプリケーションは起動時に自動的にスケジューラーを開始し、毎日午前3時にギラヴァンツ北九州の公式サイトから試合情報をスクレイピングしてデータベースを更新します。

### 仕組み

1. **自動実行**: アプリケーション起動時にスケジューラーが開始され、毎日午前3時に実行
2. **スクレイピング**: https://www.giravanz.jp/game/schedule.html から試合情報を取得
3. **位置情報取得**: Google Places APIで会場の緯度経度を取得
4. **DB更新**: 既存の試合情報をすべて削除し、新しいデータで上書き

### 手動実行

スクレイパーを今すぐ実行したい場合、以下のエンドポイントにPOSTリクエストを送信します：

```bash
curl -X POST http://localhost:8000/admin/scrape-matches
```

または、Swagger UI (http://localhost:8000/docs) の Admin セクションから実行できます。

### スクリプトとして実行

コマンドラインから直接実行することもできます：

```bash
python -m app.services.match_scraper
```

### ログ

スクレイパーの実行ログは標準出力に出力されます。以下の情報が含まれます：

- スクレイピングした試合数
- 会場の位置情報取得の成功/失敗
- データベース更新の結果

### 注意事項

- `GOOGLE_PLACES_API_KEY` が設定されていない場合、会場の位置情報は既知の会場のフォールバックデータを使用します
- スクレイピングに失敗してもアプリケーションは停止しません
- データは毎回上書きされるため、古い試合情報は削除されます

### テスト実行（今後実装予定）

```bash
pytest
```

## ライセンス

（ライセンスを追加してください）
