# Repository Guidelines

必ず日本語で応答すること


## プロジェクト構成 / モジュール整理

- エントリポイント: `app/main.py`（FastAPI起動・CORS設定）。
- パッケージ: `app/api/`（ルート）, `app/models/`（Pydanticモデル）, `app/services/`（外部API/業務ロジック）, `app/database/`（DBアクセス）。
- ルート: `requirements.txt`, `.env.example`, `API_specification`, `DB_specification`, `README.md`。
- 例: ルート追加は`app/api/`に実装し、`app/main.py`でルータをincludeします。

## ビルド・テスト・開発コマンド

- 仮想環境: `python -m venv venv` → Windows: `venv\Scripts\activate` / macOS/Linux: `source venv/bin/activate`。
- 依存関係: `pip install -r requirements.txt`。
- 開発起動: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` または `python app/main.py`。
- 動作確認: `curl http://localhost:8000/health`。

## コーディング規約・命名

- PEP 8遵守、インデント4スペース、行長100目安。型ヒント必須、要点を押さえたDocstring（Google/NumPyスタイル推奨）。
- 命名: ファイル/関数は`snake_case`、クラスは`PascalCase`、定数は`UPPER_SNAKE_CASE`。
- Pydanticモデルは`app/models/`、外部連携やビジネス処理は`app/services/`に配置。

## テスト指針

- フレームワーク: pytest（導入予定）。`tests/`配下にアプリ構成を反映して配置。
- 命名: ファイル`test_*.py`、関数`test_*`。実行: `pytest -q`。
- 目標: 新規コードは概ね80%以上のカバレッジを目指す。

## コミット / PR ガイドライン

- Conventional Commits推奨: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`。例: `feat(api): add /stores/nearby endpoint`。
- サブジェクト72文字以内、本文で背景と意図、破壊的変更は`BREAKING CHANGE:`を明記。
- PRには概要、関連Issue、スクリーンショットや`curl`/`/docs`の出力例、仕様変更時は`API_specification`/`README.md`更新を含める。

## セキュリティ / 設定

- `.env.example`をコピーして`.env`を作成し、`SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_PLACES_API_KEY`, `GEMINI_API_KEY`, `PORT`を設定。
- 秘密情報はコミット禁止（`.env`は`.gitignore`対象）。入力はPydanticで必ず検証。

## アーキテクチャ概要

- FastAPI（HTTP）、Supabase/PostgreSQL（データ）、Google Places/Gemini（外部機能）。
- エンドポイントは薄く（検証+オーケストレーション）、ドメインロジックは`app/services/`、DBは`app/database/`に分離。

## エージェント向け注意

- `venv/`や`.idea/`は変更しないこと。
- 新規モジュール追加時は`app/main.py`への配線とドキュメント更新を忘れずに。
