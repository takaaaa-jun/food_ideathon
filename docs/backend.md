# バックエンドについてのメモ
- 調べたことについてメモ

## 機能
- personalレシピ検索
- standardレシピ検索
- 栄養計算

## 各技術のメモ
- Flask
  - シンプルで軽量な構成
  - 開発者が手動で構築・選定する必要があるが，自由度が高い

## 参考サイト・ドキュメント
- [Flaskドキュメント][https://flask.palletsprojects.com/en/stable/]
- [Pythonフレームワーク一覧][https://syp.vn/jp/article/fastapi-flask-django-python-backend-framework-comparison]

## 設計
- バックエンドの設計についてまとめる

### 手順
1. Domain層完成
2. UseCase層作成
3. API層接続
4. Infrastructure層実装
5. テスト
6. GitHub Actions強化
7. AIレビュー

### domain層
- データの構造を定義