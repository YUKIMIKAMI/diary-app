# 設計書 - AI日記マインドマップアプリケーション

## 1. システムアーキテクチャ

### 1.1 全体アーキテクチャ図

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser<br/>Next.js App]
        MOBILE[Mobile App<br/>React Native<br/>将来実装]
    end
    
    subgraph "CDN/Edge"
        CF[Cloudflare CDN]
        VERCEL[Vercel Edge Functions]
    end
    
    subgraph "Application Layer"
        subgraph "Frontend Hosting"
            NEXT[Next.js on Vercel<br/>- SSR/SSG<br/>- API Routes]
        end
        
        subgraph "Backend Services"
            API[FastAPI Server<br/>- REST API<br/>- WebSocket]
            WORKER[Background Workers<br/>- Celery<br/>- AI Processing]
        end
    end
    
    subgraph "Authentication & Payment"
        AUTH[Supabase Auth<br/>- OAuth 2.0<br/>- JWT]
        PAYMENT[Stripe<br/>- Subscription<br/>- Webhook]
    end
    
    subgraph "Data Layer"
        subgraph "Primary Database"
            PG[(PostgreSQL<br/>- User Data<br/>- Diary Entries<br/>- pgvector)]
        end
        
        subgraph "Cache & Session"
            REDIS[(Redis<br/>- Cache<br/>- Session<br/>- Queue)]
        end
        
        subgraph "Object Storage"
            S3[AWS S3<br/>- Images<br/>- Backups]
        end
    end
    
    subgraph "AI Services"
        OPENAI[OpenAI API<br/>- GPT-4<br/>- Embeddings]
        BERT[Self-hosted<br/>Japanese BERT<br/>- Emotion Analysis]
    end
    
    subgraph "Monitoring"
        SENTRY[Sentry<br/>Error Tracking]
        LOG[CloudWatch<br/>Logs & Metrics]
    end
    
    WEB --> CF
    CF --> NEXT
    NEXT --> API
    API --> AUTH
    API --> PAYMENT
    API --> PG
    API --> REDIS
    API --> S3
    API --> WORKER
    WORKER --> OPENAI
    WORKER --> BERT
    WORKER --> PG
    API --> SENTRY
    API --> LOG
```

### 1.2 データフロー

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant DB as Database
    participant AI as AI Service
    participant Q as Queue
    
    U->>F: 日記を書く
    F->>A: POST /api/diary/entries
    A->>DB: 日記を保存
    A->>Q: AI処理をキューに追加
    A-->>F: 日記ID返却
    F-->>U: マインドマップページへ遷移
    
    Q->>AI: 質問生成リクエスト
    AI-->>Q: 生成された質問
    Q->>DB: 質問を保存
    Q->>F: WebSocketで通知
    F->>A: GET /api/mindmap/{entry_id}
    A->>DB: マインドマップデータ取得
    A-->>F: マインドマップJSON
    F-->>U: マインドマップ表示
```

## 2. データベース設計

### 2.1 ER図

```mermaid
erDiagram
    users ||--o{ diary_entries : creates
    users ||--o{ subscriptions : has
    diary_entries ||--o{ questions : generates
    diary_entries ||--o{ images : contains
    diary_entries ||--o{ mindmap_nodes : has
    diary_entries ||--o{ emotion_analyses : has
    questions ||--o{ answers : has
    mindmap_nodes ||--o{ node_connections : connects
    users ||--o{ ai_conversations : has
    
    users {
        uuid id PK
        string email UK
        string username
        string password_hash
        enum subscription_type
        jsonb preferences
        timestamp created_at
        timestamp updated_at
    }
    
    diary_entries {
        uuid id PK
        uuid user_id FK
        text content
        jsonb metadata
        vector embedding
        timestamp created_at
        timestamp updated_at
    }
    
    questions {
        uuid id PK
        uuid entry_id FK
        text question_text
        enum question_type
        int display_order
        timestamp created_at
    }
    
    answers {
        uuid id PK
        uuid question_id FK
        text answer_text
        timestamp answered_at
    }
    
    images {
        uuid id PK
        uuid entry_id FK
        string storage_key
        string mime_type
        int file_size
        jsonb metadata
        timestamp uploaded_at
    }
    
    mindmap_nodes {
        uuid id PK
        uuid entry_id FK
        enum node_type
        jsonb position
        jsonb style
        text content
        jsonb metadata
        timestamp created_at
    }
    
    node_connections {
        uuid id PK
        uuid from_node_id FK
        uuid to_node_id FK
        jsonb style
        jsonb metadata
    }
    
    emotion_analyses {
        uuid id PK
        uuid entry_id FK
        jsonb emotion_scores
        vector emotion_vector
        string dominant_emotion
        float confidence
        timestamp analyzed_at
    }
    
    subscriptions {
        uuid id PK
        uuid user_id FK
        string stripe_customer_id
        string stripe_subscription_id
        enum status
        timestamp started_at
        timestamp expires_at
    }
    
    ai_conversations {
        uuid id PK
        uuid user_id FK
        jsonb messages
        jsonb context
        timestamp created_at
        timestamp updated_at
    }
```

### 2.2 テーブル定義詳細

#### users テーブル
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255),
    subscription_type VARCHAR(20) DEFAULT 'free',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_subscription ON users(subscription_type);
```

#### diary_entries テーブル
```sql
CREATE TABLE diary_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),  -- OpenAI embeddings dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diary_user ON diary_entries(user_id);
CREATE INDEX idx_diary_created ON diary_entries(created_at DESC);
CREATE INDEX idx_diary_embedding ON diary_entries USING ivfflat (embedding vector_cosine_ops);
```

## 3. API設計

### 3.1 RESTful API エンドポイント

#### 認証関連
```yaml
POST   /api/auth/register
  body: { email, password, username }
  response: { user, access_token, refresh_token }

POST   /api/auth/login
  body: { email, password }
  response: { user, access_token, refresh_token }

POST   /api/auth/refresh
  body: { refresh_token }
  response: { access_token }

POST   /api/auth/logout
  headers: { Authorization: Bearer <token> }
  response: { message }

GET    /api/auth/me
  headers: { Authorization: Bearer <token> }
  response: { user }
```

#### 日記関連
```yaml
POST   /api/diary/entries
  headers: { Authorization: Bearer <token> }
  body: { content, metadata? }
  response: { entry_id, created_at }

GET    /api/diary/entries
  headers: { Authorization: Bearer <token> }
  query: { page?, limit?, from_date?, to_date? }
  response: { entries[], pagination }

GET    /api/diary/entries/{entry_id}
  headers: { Authorization: Bearer <token> }
  response: { entry, questions[], answers[] }

PUT    /api/diary/entries/{entry_id}
  headers: { Authorization: Bearer <token> }
  body: { content }
  response: { entry }

DELETE /api/diary/entries/{entry_id}
  headers: { Authorization: Bearer <token> }
  response: { message }

POST   /api/diary/entries/{entry_id}/images
  headers: { Authorization: Bearer <token> }
  body: multipart/form-data
  response: { image_id, url }
```

#### 質問・回答関連
```yaml
POST   /api/diary/entries/{entry_id}/questions/generate
  headers: { Authorization: Bearer <token> }
  response: { questions[] }

GET    /api/questions/{question_id}
  headers: { Authorization: Bearer <token> }
  response: { question, answers[] }

POST   /api/questions/{question_id}/answers
  headers: { Authorization: Bearer <token> }
  body: { answer_text }
  response: { answer }

PUT    /api/answers/{answer_id}
  headers: { Authorization: Bearer <token> }
  body: { answer_text }
  response: { answer }
```

#### マインドマップ関連
```yaml
GET    /api/mindmap/{entry_id}
  headers: { Authorization: Bearer <token> }
  response: { nodes[], connections[], metadata }

POST   /api/mindmap/merge
  headers: { Authorization: Bearer <token> }
  body: { entry_ids[], period?, type? }
  response: { merged_mindmap }

PUT    /api/mindmap/nodes/{node_id}
  headers: { Authorization: Bearer <token> }
  body: { position?, style?, metadata? }
  response: { node }
```

#### 分析関連（有料プラン）
```yaml
POST   /api/analysis/emotion/{entry_id}
  headers: { Authorization: Bearer <token> }
  response: { emotions, dominant_emotion, confidence }

GET    /api/analysis/emotions/timeline
  headers: { Authorization: Bearer <token> }
  query: { from_date, to_date, granularity? }
  response: { timeline_data }

GET    /api/analysis/words/frequency
  headers: { Authorization: Bearer <token> }
  query: { from_date, to_date, limit? }
  response: { word_frequencies }

GET    /api/analysis/words/cloud
  headers: { Authorization: Bearer <token> }
  query: { from_date, to_date }
  response: { word_cloud_data }
```

#### AI相談関連（有料プラン）
```yaml
POST   /api/chat/consult
  headers: { Authorization: Bearer <token> }
  body: { message, conversation_id? }
  response: { response, conversation_id }

GET    /api/chat/conversations
  headers: { Authorization: Bearer <token> }
  response: { conversations[] }

GET    /api/chat/conversations/{conversation_id}
  headers: { Authorization: Bearer <token> }
  response: { messages[], context }
```

#### サブスクリプション関連
```yaml
POST   /api/subscription/checkout
  headers: { Authorization: Bearer <token> }
  body: { plan_type }
  response: { checkout_url }

POST   /api/subscription/webhook
  body: Stripe webhook payload
  response: { received: true }

GET    /api/subscription/status
  headers: { Authorization: Bearer <token> }
  response: { subscription }

DELETE /api/subscription/cancel
  headers: { Authorization: Bearer <token> }
  response: { message }
```

### 3.2 WebSocket API

```yaml
WebSocket /ws/mindmap
  認証: Query parameter ?token=<jwt_token>
  
  受信イベント:
    - node_update: ノードの位置更新
    - connection_add: 接続追加
    - connection_remove: 接続削除
  
  送信イベント:
    - mindmap_updated: マインドマップ更新通知
    - question_generated: 新しい質問生成通知
    - analysis_completed: 分析完了通知
```

## 4. フロントエンドコンポーネント設計

### 4.1 コンポーネント階層

```
src/
├── app/                          # Next.js App Router
│   ├── (auth)/                  # 認証関連ページ
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   ├── (dashboard)/             # ダッシュボード（認証必須）
│   │   ├── diary/
│   │   │   ├── new/            # 新規日記作成
│   │   │   ├── [id]/           # 日記詳細
│   │   │   └── page.tsx        # 日記一覧
│   │   ├── mindmap/
│   │   │   ├── [id]/           # 個別マインドマップ
│   │   │   └── merged/         # 結合マインドマップ
│   │   ├── analysis/           # 分析ページ（有料）
│   │   ├── chat/               # AI相談（有料）
│   │   └── settings/           # 設定
│   └── layout.tsx              # ルートレイアウト
│
├── components/
│   ├── common/                 # 共通コンポーネント
│   │   ├── Header/
│   │   ├── Footer/
│   │   ├── Navigation/
│   │   ├── LoadingSpinner/
│   │   └── ErrorBoundary/
│   │
│   ├── diary/                  # 日記関連
│   │   ├── DiaryEditor/       # 日記エディタ
│   │   ├── DiaryCard/         # 日記カード
│   │   ├── DiaryList/         # 日記リスト
│   │   └── InteractiveDiary/  # 対話型入力（有料）
│   │
│   ├── mindmap/                # マインドマップ関連
│   │   ├── MindMapCanvas/     # メインキャンバス
│   │   ├── MindMapNode/       # ノードコンポーネント
│   │   ├── MindMapEdge/       # エッジコンポーネント
│   │   ├── MindMapControls/   # コントロールパネル
│   │   └── MindMapSearch/     # 検索機能
│   │
│   ├── question/               # 質問関連
│   │   ├── QuestionNode/      # 質問ノード
│   │   ├── QuestionList/      # 質問リスト
│   │   └── AnswerForm/        # 回答フォーム
│   │
│   ├── analysis/               # 分析関連（有料）
│   │   ├── EmotionChart/      # 感情グラフ
│   │   ├── WordCloud/         # ワードクラウド
│   │   ├── FrequencyChart/    # 頻出単語グラフ
│   │   └── EmotionIndicator/  # 感情インジケータ
│   │
│   ├── chat/                   # AI相談（有料）
│   │   ├── ChatInterface/     # チャットUI
│   │   ├── MessageBubble/     # メッセージ表示
│   │   └── ChatHistory/       # 履歴表示
│   │
│   └── subscription/           # サブスクリプション
│       ├── PricingCard/       # 料金プラン
│       ├── UpgradeModal/      # アップグレードモーダル
│       └── PaymentForm/       # 決済フォーム
```

### 4.2 主要コンポーネント詳細設計

#### MindMapCanvas コンポーネント
```typescript
interface MindMapCanvasProps {
  entryId: string;
  editable?: boolean;
  onNodeClick?: (node: MindMapNode) => void;
  onNodeUpdate?: (node: MindMapNode) => void;
}

// 機能:
// - React Flowを使用した描画
// - ドラッグ&ドロップ対応
// - ズーム・パン機能
// - リアルタイム更新（WebSocket）
// - ノードの追加・削除
// - 接続の管理
```

#### DiaryEditor コンポーネント
```typescript
interface DiaryEditorProps {
  initialContent?: string;
  onSubmit: (content: string) => Promise<void>;
  mode: 'simple' | 'interactive';
}

// 機能:
// - リッチテキストエディタ（Tiptap使用）
// - 自動保存
// - 画像アップロード（有料）
// - 対話型モード（有料）
// - プレビュー機能
```

## 5. マインドマップライブラリの選定

### 5.1 候補ライブラリの比較

| 項目 | React Flow | vis.js | D3.js | Cytoscape.js |
|------|------------|--------|-------|--------------|
| **学習曲線** | 緩やか | 中程度 | 急 | 中程度 |
| **カスタマイズ性** | ◎ | ○ | ◎ | ○ |
| **パフォーマンス** | ◎ | ○ | ◎ | ◎ |
| **ドキュメント** | ◎ | ○ | ○ | ○ |
| **React統合** | ネイティブ | ラッパー必要 | ラッパー必要 | ラッパー必要 |
| **TypeScript対応** | ◎ | △ | △ | ○ |
| **ノード数対応** | 1000+ | 500+ | 無制限 | 1000+ |
| **アニメーション** | ◎ | ○ | ◎ | ○ |
| **モバイル対応** | ◎ | △ | ○ | ○ |
| **ライセンス** | MIT | MIT/Apache | BSD | MIT |
| **コミュニティ** | 活発 | 普通 | 活発 | 普通 |

### 5.2 選定結果: React Flow

**選定理由:**
1. **React専用設計**: Reactとの統合が最もスムーズ
2. **TypeScript完全対応**: 型安全な開発が可能
3. **豊富な機能**: ドラッグ&ドロップ、ズーム、パンが標準装備
4. **優れたパフォーマンス**: 仮想化により大量ノードでも高速
5. **活発な開発**: 定期的なアップデートとバグ修正
6. **商用利用可能**: MITライセンス

### 5.3 React Flow実装設計

```typescript
// カスタムノードタイプ定義
export const nodeTypes = {
  diaryNode: DiaryNode,          // 日記ノード
  questionNode: QuestionNode,    // 質問ノード
  answerNode: AnswerNode,        // 回答ノード
  categoryNode: CategoryNode,    // カテゴリノード（結合時）
};

// カスタムエッジタイプ定義
export const edgeTypes = {
  defaultEdge: DefaultEdge,      // 通常の接続
  emotionEdge: EmotionEdge,      // 感情を表現する接続
  temporalEdge: TemporalEdge,    // 時系列接続
};

// スタイル定義
export const nodeStyles = {
  diary: {
    background: '#ffffff',
    border: '2px solid #3b82f6',
    borderRadius: '8px',
    padding: '10px',
  },
  question: {
    background: '#fef3c7',
    border: '2px solid #f59e0b',
    borderRadius: '8px',
    padding: '8px',
  },
  answer: {
    background: '#dbeafe',
    border: '2px solid #60a5fa',
    borderRadius: '8px',
    padding: '8px',
  },
};
```

## 6. 認証・決済システムの設計

### 6.1 認証システム (Supabase Auth)

#### 6.1.1 認証フロー

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant S as Supabase Auth
    participant B as Backend API
    participant DB as Database
    
    U->>F: ログイン要求
    F->>S: signInWithPassword()
    S-->>F: JWT Token + User
    F->>B: API Request + Bearer Token
    B->>S: JWT検証
    S-->>B: User情報
    B->>DB: データ取得
    DB-->>B: レスポンス
    B-->>F: APIレスポンス
    F-->>U: 画面表示
```

#### 6.1.2 認証設定

```typescript
// supabase.config.ts
export const supabaseConfig = {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    providers: ['email', 'google', 'twitter'],
    redirectTo: process.env.NEXT_PUBLIC_APP_URL + '/auth/callback',
  },
  storage: {
    storageKey: 'diary-app-auth',
  },
};

// middleware.ts - 認証保護
export function middleware(request: NextRequest) {
  const session = await getSession(request);
  
  const protectedPaths = ['/diary', '/mindmap', '/analysis', '/chat'];
  const isProtectedPath = protectedPaths.some(path => 
    request.nextUrl.pathname.startsWith(path)
  );
  
  if (isProtectedPath && !session) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  return NextResponse.next();
}
```

### 6.2 決済システム (Stripe)

#### 6.2.1 サブスクリプションフロー

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant ST as Stripe
    participant DB as Database
    
    U->>F: プラン選択
    F->>B: POST /api/subscription/checkout
    B->>ST: Create Checkout Session
    ST-->>B: Checkout URL
    B-->>F: Redirect URL
    F->>U: Stripeページへリダイレクト
    
    U->>ST: 支払い情報入力
    ST->>B: Webhook (payment_intent.succeeded)
    B->>DB: サブスクリプション情報更新
    B-->>ST: 200 OK
    
    ST->>F: Success Redirect
    F->>B: GET /api/subscription/status
    B->>DB: ステータス確認
    B-->>F: Active Subscription
    F-->>U: 有料機能解放
```

#### 6.2.2 料金プラン設計

```typescript
// pricing.config.ts
export const pricingPlans = {
  free: {
    name: 'Free',
    price: 0,
    features: [
      '日記作成（無制限）',
      'マインドマップ自動生成',
      'AI質問生成',
      '基本検索機能',
    ],
    limits: {
      imagesPerEntry: 0,
      aiConsultations: 0,
      emotionAnalysis: false,
      wordAnalysis: false,
      mindmapMerge: false,
    },
  },
  premium: {
    name: 'Premium',
    price: 980, // 円/月
    stripePriceId: process.env.STRIPE_PREMIUM_PRICE_ID,
    features: [
      'Freeプランの全機能',
      '画像アップロード（10枚/日記）',
      'AI相談モード',
      '感情分析',
      '単語集計・ワードクラウド',
      'マインドマップ結合',
      '対話型日記入力',
    ],
    limits: {
      imagesPerEntry: 10,
      aiConsultations: 100, // 月間
      emotionAnalysis: true,
      wordAnalysis: true,
      mindmapMerge: true,
    },
  },
};
```

#### 6.2.3 Webhook処理

```typescript
// stripe.webhook.ts
export async function handleStripeWebhook(
  event: Stripe.Event,
  db: Database
) {
  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object as Stripe.Checkout.Session;
      await db.subscriptions.create({
        user_id: session.metadata.user_id,
        stripe_customer_id: session.customer,
        stripe_subscription_id: session.subscription,
        status: 'active',
        started_at: new Date(),
      });
      break;
      
    case 'customer.subscription.updated':
      const subscription = event.data.object as Stripe.Subscription;
      await db.subscriptions.update({
        stripe_subscription_id: subscription.id,
        status: subscription.status,
      });
      break;
      
    case 'customer.subscription.deleted':
      const deleted = event.data.object as Stripe.Subscription;
      await db.subscriptions.update({
        stripe_subscription_id: deleted.id,
        status: 'cancelled',
        expires_at: new Date(deleted.current_period_end * 1000),
      });
      break;
  }
}
```

### 6.3 セキュリティ設計

#### 6.3.1 データ暗号化

```typescript
// encryption.service.ts
export class EncryptionService {
  // 日記コンテンツの暗号化（AES-256-GCM）
  async encryptDiaryContent(content: string, userId: string): Promise<{
    encrypted: string;
    iv: string;
    tag: string;
  }> {
    const key = await this.deriveUserKey(userId);
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
    
    let encrypted = cipher.update(content, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    const tag = cipher.getAuthTag();
    
    return {
      encrypted,
      iv: iv.toString('hex'),
      tag: tag.toString('hex'),
    };
  }
  
  // ユーザー固有キーの導出
  private async deriveUserKey(userId: string): Promise<Buffer> {
    const masterKey = process.env.ENCRYPTION_MASTER_KEY;
    return crypto.pbkdf2Sync(
      userId,
      masterKey,
      100000,
      32,
      'sha256'
    );
  }
}
```

#### 6.3.2 アクセス制御

```typescript
// rbac.config.ts
export const accessControl = {
  free: {
    diary: ['create', 'read', 'update', 'delete'],
    questions: ['read'],
    answers: ['create', 'read', 'update'],
    mindmap: ['read'],
    search: ['basic'],
  },
  premium: {
    diary: ['create', 'read', 'update', 'delete'],
    questions: ['read'],
    answers: ['create', 'read', 'update'],
    mindmap: ['read', 'merge'],
    search: ['basic', 'advanced'],
    images: ['upload', 'read', 'delete'],
    analysis: ['emotion', 'words'],
    chat: ['consult'],
    interactive: ['diary_input'],
  },
};

// authorization.middleware.ts
export async function checkAccess(
  user: User,
  resource: string,
  action: string
): Promise<boolean> {
  const userPlan = user.subscription_type || 'free';
  const permissions = accessControl[userPlan][resource] || [];
  return permissions.includes(action);
}
```

## 7. 開発環境とデプロイメント

### 7.1 開発環境構成

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: diary_app
      POSTGRES_USER: diary_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://diary_user:${DB_PASSWORD}@postgres:5432/diary_app
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_SUPABASE_URL: ${SUPABASE_URL}
      NEXT_PUBLIC_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
    volumes:
      - ./frontend:/app
    ports:
      - "3000:3000"

volumes:
  postgres_data:
```

### 7.2 CI/CDパイプライン

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest
      
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm ci
          npm test
          npm run type-check

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Vercel
        run: |
          npm i -g vercel
          vercel --prod --token=${{ secrets.VERCEL_TOKEN }}

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        run: |
          railway up --service backend
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## 8. パフォーマンス最適化

### 8.1 フロントエンド最適化

```typescript
// 1. 画像最適化
import Image from 'next/image';

// 2. コード分割
const MindMapCanvas = dynamic(
  () => import('@/components/mindmap/MindMapCanvas'),
  { ssr: false, loading: () => <MindMapSkeleton /> }
);

// 3. データフェッチング最適化
const { data, error } = useSWR(
  `/api/diary/entries?page=${page}`,
  fetcher,
  {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 60000,
  }
);

// 4. メモ化
const expensiveComputation = useMemo(
  () => calculateMindMapLayout(nodes, edges),
  [nodes, edges]
);
```

### 8.2 バックエンド最適化

```python
# 1. データベースクエリ最適化
from sqlalchemy.orm import selectinload

entries = db.query(DiaryEntry)\
    .options(selectinload(DiaryEntry.questions))\
    .filter(DiaryEntry.user_id == user_id)\
    .limit(20)\
    .all()

# 2. キャッシング
from functools import lru_cache
import redis

@lru_cache(maxsize=128)
async def get_mindmap_data(entry_id: str):
    cache_key = f"mindmap:{entry_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    data = await generate_mindmap(entry_id)
    await redis.setex(cache_key, 3600, json.dumps(data))
    return data

# 3. 非同期処理
from celery import Celery

@celery.task
def generate_questions_async(entry_id: str):
    # AI処理を非同期で実行
    questions = openai_service.generate_questions(entry_id)
    save_questions(questions)
    notify_user(entry_id, questions)
```

## 9. 監視とログ

### 9.1 エラー監視 (Sentry)

```typescript
// sentry.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  beforeSend(event, hint) {
    // 個人情報をフィルタリング
    if (event.request?.cookies) {
      delete event.request.cookies;
    }
    return event;
  },
});
```

### 9.2 アプリケーションログ

```python
# logging.config.py
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# 使用例
logger.info("diary_created", extra={
    "user_id": user_id,
    "entry_id": entry_id,
    "word_count": len(content.split()),
})
```

## 10. テスト戦略

### 10.1 フロントエンドテスト

```typescript
// diary.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DiaryEditor } from '@/components/diary/DiaryEditor';

describe('DiaryEditor', () => {
  it('should submit diary entry', async () => {
    const handleSubmit = jest.fn();
    render(<DiaryEditor onSubmit={handleSubmit} />);
    
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Test diary' } });
    
    const submitButton = screen.getByText('送信');
    fireEvent.click(submitButton);
    
    expect(handleSubmit).toHaveBeenCalledWith('Test diary');
  });
});
```

### 10.2 バックエンドテスト

```python
# test_diary.py
import pytest
from fastapi.testclient import TestClient

def test_create_diary_entry(client: TestClient, auth_headers):
    response = client.post(
        "/api/diary/entries",
        json={"content": "Test diary"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert "entry_id" in response.json()

def test_generate_questions(client: TestClient, diary_entry, auth_headers):
    response = client.post(
        f"/api/diary/entries/{diary_entry.id}/questions/generate",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()["questions"]) > 0
```