# レシピ検索エンジンシステム（Recipe Search Engine System）
データベースに格納してあるレシピデータと，
典型的なレシピ情報を検索できるWebアプリケーションです．

## 特徴
- 栄養素表示: レシピ全体および各材料の栄養素を自動計算
- 基礎レシピ検索: 典型的なレシピを検索可能

## 技術スタック
- バックエンド: Python 3.11, Flask
- データベース: MySQL 8.0
- Webサーバー: Nginx
- コンテナ: Docker Compose

## 必要環境
- Docker
- Git
- MySQL
- Antigravity（推奨）

## セットアップ手順
### 1. リポジトリをクローン

```bash
git clone <your-repository-url>
cd foodapp
```

### 2. 環境変数を設定
`.env.example` をコピーして `.env` を作成：

```bash
cp .env.example .env
```

`.env` を編集してデータベース接続情報を設定してください。

### 3. データベース接続設定
`apps/web/db_connection.cofg.example` をコピー：

```bash
cp apps/web/db_connection.cofg.example apps/web/db_connection.cofg
```

`apps/web/db_connection.cofg` を編集してデータベース接続情報を設定してください。

### 4. Dockerコンテナを起動

```bash
docker compose up -d --build
```

### 5. アプリケーションにアクセス
ブラウザで以下のURLを開きます：

```
http://localhost:8080
```

## 開発
### コードを編集して反映させる
#### HTML/Pythonファイルを編集した場合

```bash
docker compose restart app
docker compose logs -f app
```

#### 依存関係を変更した場合

```bash
docker compose up -d --build app
```

### コンテナの状態確認

```bash
# 稼働中のコンテナを確認
docker compose ps

# ログをリアルタイム表示
docker compose logs -f app

# すべてのサービスのログ
docker compose logs -f
```

### コンテナの停止・削除

```bash
# コンテナを停止
docker compose down

# ボリュームも含めて完全削除（データベースのデータも削除されます）
docker compose down -v
```

## プロジェクト構成

```
foodapp/
├── apps/
│   └── web/
│       ├── app.py                    # Flaskアプリケーション本体
│       ├── Dockerfile                # Dockerイメージ定義
│       ├── requirements.txt          # Python依存関係
│       ├── db_connection.cofg        # DB接続設定（gitignore）
│       ├── templates/                # HTMLテンプレート
│       │   ├── index.html           # トップページ
│       │   ├── results.html         # 検索結果ページ
│       │   ├── basic_search_home.html
│       │   └── basic_recipes.html
│       └── *.json                   # レシピデータ(今後データベースに移行予定)
├── infra/
│   └── nginx/
│       └── app.conf                 # Nginx設定
├── compose.yaml                      # Docker Compose設定
├── .env                             # 環境変数（gitignore）
├── .gitignore
├── README.md                        # このファイル
└── CHANGELOG.md                     # 変更履歴

```

## 使い方
### 1. 材料検索
トップページで材料名を入力して検索できます。

- OR検索: いずれかの材料を含むレシピを検索
- AND検索: すべての材料を含むレシピを検索（スペース区切り）
- NOT検索: 含む材料と除外する材料を指定（スペース区切り）

### 2. 基礎レシピ検索
「基礎レシピを検索する」リンクから、よく使われる基本的なレシピを検索できます。

## トラブルシューティング
### データベースに接続できない
1. `.env` ファイルの設定を確認
2. `apps/web/db_connection.cofg` の設定を確認
3. データベースコンテナが起動しているか確認：`docker compose ps`

### ポート8080が既に使用されている
`compose.yaml` の `reverse-proxy` セクションのポート番号を変更：

```yaml
ports:
  - "8081:80"  # 8080 → 8081に変更
```

## ライセンス
Copyright (C) 2025 Jun Takahashi All Right Reserved.

## お問い合わせ
