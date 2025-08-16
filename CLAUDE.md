# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)へのガイダンスを提供します。

## プロジェクト概要

AI機能を備えた日記マインドマップアプリケーション。日記を自動的にマインドマップ化し、AIが生成する質問により自己理解を深める革新的なサービス。

## 技術スタック

### フロントエンド
- **フレームワーク**: Next.js 14 (App Router)
- **言語**: TypeScript
- **UIライブラリ**: React 18 + Tailwind CSS + shadcn/ui
- **マインドマップ**: React Flow
- **状態管理**: Zustand
- **データフェッチング**: TanStack Query

### バックエンド
- **フレームワーク**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0
- **バリデーション**: Pydantic v2

### データベース・インフラ
- **メインDB**: PostgreSQL 15 + pgvector
- **画像ストレージ**: AWS S3 or Cloudflare R2
- **キャッシュ**: Redis
- **認証**: Supabase Auth or Auth0

### AI/ML
- **LLM**: OpenAI GPT-4 API
- **感情分析**: Transformers (Japanese BERT)
- **自然言語処理**: spaCy (GiNZA)

## プロジェクト構造

```
diary-app/
├── frontend/                # Next.jsフロントエンド
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # Reactコンポーネント
│   │   ├── lib/           # ユーティリティ
│   │   ├── hooks/         # カスタムフック
│   │   └── stores/        # Zustand stores
│   ├── public/            # 静的ファイル
│   └── package.json
├── backend/               # FastAPIバックエンド
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── core/         # 設定、セキュリティ
│   │   ├── models/       # SQLAlchemyモデル
│   │   ├── schemas/      # Pydanticスキーマ
│   │   ├── services/     # ビジネスロジック
│   │   └── ai/          # AI関連機能
│   ├── tests/           # テスト
│   └── requirements.txt
└── docs/               # ドキュメント
```

### 開発規約
.gitignoreファイルから、以下に対応する準備が整っています：
- 仮想環境の使用（.venv、venv/、env/）
- 複数のPythonパッケージマネージャー（pip、pipenv、poetry、pdm）
- pytestとカバレッジツールによるテスト
- mypyなどによる型チェック
- ruffによるコードフォーマット
- AI開発に必要な場合のJupyterノートブックのサポート

## 開発コマンド

### フロントエンド (frontend/)
```bash
npm install          # 依存関係のインストール
npm run dev         # 開発サーバー起動 (localhost:3000)
npm run build       # プロダクションビルド
npm run lint        # ESLintチェック
npm run type-check  # TypeScriptチェック
npm test           # テスト実行
```

### バックエンド (backend/)
```bash
python -m venv .venv            # 仮想環境作成
source .venv/bin/activate       # 仮想環境有効化 (Linux/Mac)
.venv\Scripts\activate          # 仮想環境有効化 (Windows)
pip install -r requirements.txt # 依存関係インストール
uvicorn app.main:app --reload  # 開発サーバー起動 (localhost:8000)
pytest                         # テスト実行
ruff check .                   # リンティング
mypy app                       # 型チェック
```

## 主要APIエンドポイント

- `POST /api/diary/entries` - 日記作成
- `GET /api/diary/entries` - 日記一覧取得
- `POST /api/diary/entries/{id}/questions` - AI質問生成
- `GET /api/mindmap/{entry_id}` - マインドマップデータ取得
- `POST /api/analysis/emotion` - 感情分析（有料）
- `POST /api/chat/consult` - AI相談モード（有料）

## 重要事項

- **要件定義書**: `requirements.md`に詳細な要件と仕様が記載されています
- **フリーミアムモデル**: 無料プランと有料プランの機能区分に注意
- **マインドマップ**: React Flowを使用した高度なインタラクティブ表示が必要
- **AI統合**: OpenAI APIキーの設定が必要（環境変数: `OPENAI_API_KEY`）
- **データベース**: PostgreSQLとpgvectorエクステンションのセットアップが必要
- **認証**: Supabase AuthまたはAuth0の設定が必要