# レシピ検索エンジンシステム（Recipe Search Engine System）

データベースに格納された膨大なレシピデータから、目的のレシピを効率的に検索・分析し、栄養計算まで行える多機能Webアプリケーションです。

## 特徴 (Features)

### 1. 高度なレシピ検索機能
このシステムは、利用者の目的に応じた複数の検索モードを備えています。

*   **パーソナルレシピ検索 (Personal Recipe Search)**
    *   **AND検索**: すべての材料を含むレシピを表示
    *   **NOT検索**: 特定の材料以外を除外

*   **基準レシピ検索 (Standard Recipe Search)**
    *   レシピ開発やアイデア出し（Ideation）を支援する検索モードです。
    *   **Random Page Jump**: 検索結果からランダムなページへジャンプし、予期せぬレシピとの出会い（セレンディピティ）を創出します。
    *   **Expandable List View**: 一覧性を高めるため、最初はタイトルのみを表示し、クリックで詳細を展開するUIを採用。

### 2. 栄養計算ツール (Nutrition Calculation Tool)
*   レシピの材料を入力するだけで、エネルギー、タンパク質、脂質、炭水化物、食物繊維、食塩相当量を自動計算します。
*   **主食クイック追加**: ご飯や食パンなどの主食をワンクリックで追加可能。
*   **充足率表示**: 基準値に対する栄養素の充足率をリアルタイムで可視化します。

### 3. 詳細なログ・分析基盤
*   **Access Log**: ユーザーの行動（検索クエリ、滞在時間）に加え、CPU使用率やレスポンスタイムなどのシステムパフォーマンスも記録。
*   **User Tracking**: Cookieを用いた匿名IDにより、セッションを超えたユーザー行動の分析が可能です。

## 技術スタック (Tech Stack)

### Backend
*   **Language**: Python 3.11
*   **Framework**: Flask (Microframework)
*   **Server Gateway**: WSGI (Gunicorn等での運用を想定), Nginx (Reverse Proxy)

### Frontend
*   **Template Engine**: Jinja2
*   **Scripting**: JavaScript (jQuery), DataTables
*   **Styling**: CSS3 (Responsive Design)

### Database
*   **RDBMS**: MySQL 8.0
*   **Search Index**: Ngram Parser (日本語全文検索の高速化)

### Infrastructure
*   **Containerization**: Docker, Docker Compose
*   **Monitoring**: `psutil` によるリソース監視

## プロジェクト構成 (Folder Structure)

```
foodapp/
├── apps/
│   └── web/
│       ├── app.py                # アプリケーションエントリーポイント
│       ├── core/                 # 共通ユーティリティ (Timezone処理など)
│       ├── routes/               # ルーティング定義 (Blueprint)
│       │   ├── api.py            # APIエンドポイント
│       │   ├── nutrition.py      # 栄養計算機能
│       │   ├── personal.py       # 個人レシピ検索
│       │   └── standard.py       # 基礎レシピ検索
│       ├── services/             # ビジネスロジック・検索処理
│       │   └── search.py
│       ├── templates/            # フロントエンドテンプレート (HTML)
│       ├── logs/                 # アプリケーションログ出力先
│       ├── scripts/              # スクリプト
│       ├── tests/                # テスト
│       ├── Dockerfile
│       ├── requirements.txt
│       └── db_connection.cofg    # DB接続設定
├── infra/
│   └── nginx/                    # Webサーバー設定
├── compose.yaml                  # Docker Compose構成定義
├── .env                          # 環境変数設定
└── README.md                     # 本ファイル
```

## 必要環境

*   Docker Desktop (または Docker Engine)
*   Git
*   Antigravity (推奨開発環境)

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <your-repository-url>
cd foodapp
```

### 2. 設定ファイルの準備

`.env` ファイルを作成し、環境変数を設定します。

```bash
cp .env.example .env
```

データベース接続設定用のファイルを作成します。

```bash
cp apps/web/db_connection.cofg.example apps/web/db_connection.cofg
```

### 3. アプリケーションの起動

Docker Composeを使用してコンテナをビルド・起動します。

```bash
docker compose up -d --build
```

### 4. アクセス

ブラウザで以下のURLにアクセスしてください。

```
http://localhost:8080
```

## 開発・運用コマンド

### ログの確認

```bash
# アプリケーションログのリアルタイム監視
docker compose logs -f app
```

### コンテナの再起動 (コード変更の反映)

```bash
docker compose restart app
```

### コンテナの完全停止

```bash
docker compose down
```

## ライセンス

Copyright (C) 2025 Jun Takahashi All Right Reserved.
