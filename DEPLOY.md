# デプロイ手順 (Deployment Guide)

このアプリケーションを別のマシンで起動するための手順書です。
Docker と Docker Compose がインストールされていることが前提です。

## 1. ファイルの準備

以下のディレクトリとファイルを、新しいマシンの任意のディレクトリ（例: `/srv/foodapp`）に配置してください。

- `gateway/` (ディレクトリごと: Nginx設定)
- `apps/` (ディレクトリごと: アプリ本体)
- `infra/` (ディレクトリごと: **特に schema, dumpファイルを含めること**)
- `compose.yaml` (アプリ用)
- `.env.example` -> `.env` にリネームして使用

## 2. ネットワークの作成

Gatewayとアプリが通信するための共通ネットワークを作成します。

```bash
docker network create shared-gateway-net
```

## 3. Gateway (Nginx) の起動

まず、サーバーの入り口となる Gateway を起動します。

```bash
cd gateway
docker compose up -d
```
これで Port 80 が開かれます。

## 4. アプリケーションの起動

次に、アプリケーション本体を起動します。

```bash
cd ..  # 元のディレクトリに戻る
cp .env.example .env  # 環境変数の設定（必要に応じて編集）
docker compose up -d --build
```

- `-d`: バックグラウンドで実行
- `--build`: コンテナイメージを再ビルド

> **注意**: もしシステム標準の Nginx などが Port 80 を使用している場合は、競合エラーになります。その場合は `sudo systemctl stop nginx` 等で停止してから Gateway を起動してください。

## 5. 起動確認

起動後、ブラウザで以下のURLにアクセスしてください。

- http://localhost/recipe_search

## 補足: 将来のアプリ追加

新しいアプリを追加する場合：
1. 別のディレクトリでアプリを作成し、`shared-gateway-net` に参加させます。
2. `gateway/conf.d/` に新しい設定ファイル（例: `new_app.conf`）を追加します。
3. `cd gateway && docker compose restart` で Nginx を再読み込みします。

## 補足: 将来のポータルページ化

将来、`/` (ルート) にポータルページ（目次など）を設置したい場合は、以下の手順を実施します。

1. `gateway/conf.d/portal.conf` (仮) を作成し、ルートへのアクセス設定を追加します。
2. `gateway/conf.d/recipe_search.conf` から `location = / { return 302 ... }` の記述を削除します。
3. ポータルページ用の HTML ファイル (`index.html`) を Gateway コンテナにマウントするか、別の静的サイト用コンテナを作成してプロキシします。

