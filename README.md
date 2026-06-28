# google-health-api

Google Health API（v4）で健康データを取得し、Gemini と組み合わせて活用するプロジェクトです。

- **`demo/`** — ターミナルで過去1習慣の歩数・距離・睡眠データを表示する CLI デモ
- **`playground/`** — 健康データを Gemini に渡して会話するWeb UI

---

## 概要

| モード | 説明 |
| --- | --- |
| **demo** | OAuth 認証 → 直近 1 週間のデータをターミナルに表示して終了 |
| **playground** | FastAPI サーバーを起動し、日付範囲を選んで健康データを AI に質問 |

playground では取得した JSON をそのまま Gemini のシステムプロンプトに注入します。会話履歴は持たず、毎回独立した一問一答です。

---

## 必要なもの

| 項目 | 内容 |
| --- | --- |
| Python | 3.12 以上 |
| [uv](https://docs.astral.sh/uv/) | 依存関係管理・実行 |
| Google Cloud プロジェクト | Google Health API 有効化 + OAuth クライアント |
| Gemini API キー | playground 利用時のみ（[Google AI Studio](https://aistudio.google.com/apikey)） |

---

## 環境構築

### 1. リポジトリを取得

```powershell
git clone https://github.com/yuki-dev26/google-health-api.git
cd google-health-api
```

### 2. 依存関係をインストール

```powershell
uv sync
```

### 3. 環境変数を設定

プロジェクトルートに `.env` を作成します。

```env
# Google OAuth（demo / playground 共通）
GOOGLE_CLIENT_ID="your-client-id"
GOOGLE_CLIENT_SECRET="your-client-secret"

# Gemini（playground のみ）
GEMINI_API_KEY="your-gemini-api-key"

```

`.env` と `demo/.token.json` は git 管理外です。

---

## Google Cloud の設定

Google Health API の有効化・OAuth クライアント作成などは、以下の note を参照してください。

[Google Health API の設定手順（note）](https://note.com/yuki_tech/n/n7f31deaed7d4)

---

## 使い方

### demo（ターミナルデモ）

```powershell
uv run python -m demo.main
```

**初回:** ブラウザで Google ログイン → トークンを `demo/.token.json` に保存 → データ表示 → 終了  
**2回目以降:** 保存済みトークンで再認証なし

再認証する場合:

```powershell
Remove-Item demo\.token.json
uv run python -m demo.main
```

詳細は [demo/README.md](demo/README.md) を参照してください。

### playground（Web UI）

```powershell
uv run uvicorn playground.main:app --host 127.0.0.1 --port 8000
```

ブラウザで [http://127.0.0.1:8000](http://127.0.0.1:8000) を開きます。

1. 未接続の場合は **接続する** から Google Health を OAuth 連携
2. ヘッダーで期間を選び **取得** をクリック
3. 左サイドバーで取得データを確認し、下部の入力欄から質問

AI のキャラクター設定は `playground/system_prompt.md` を編集してください。

---

## プロジェクト構成

```text
google-health-api/
├── .env                    # 環境変数（要作成）
├── demo/                   # CLI デモ
│   ├── main.py             # エントリポイント
│   ├── auth.py             # OAuth
│   ├── config.py           # 設定・スコープ
│   ├── health_client.py    # Health API クライアント
│   └── .token.json         # OAuth トークン（自動生成）
└── playground/             # Web UI + Gemini
    ├── main.py             # FastAPI アプリ
    ├── health_context.py   # 健康データの取得・整形
    ├── gemini_service.py   # Gemini API 連携
    ├── system_prompt.md    # AI キャラクター設定
    └── static/             # フロントエンド（HTML / CSS / JS）
```

---

## playground API docs

FastAPI の自動ドキュメントで確認できます。playground 起動後、ブラウザで以下を開いてください。

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 取得できるデータ

Google Health API v4（`https://health.googleapis.com/v4`）から以下を取得します。

- プロフィール（年齢など）
- 日別歩数
- 日別距離（km）
- 睡眠（就寝・起床・睡眠時間）

---

## 参考リンク

- [Google Health API セットアップ](https://developers.google.com/health/setup)
- [REST リファレンス](https://developers.google.com/health/reference/rest)
- [データタイプ一覧](https://developers.google.com/health/data-types)

---

## Supporters

[![note メンバーシップ](https://img.shields.io/badge/note-Membership-41C9B4?style=for-the-badge&logo=note&logoColor=white)](https://note.com/yuki_tech/membership/members)

## License

Copyright (c) 2025 [yuki-P](https://x.com/yuki_p02)
Licensed under the [MIT License](LICENSE).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
