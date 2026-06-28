# Google Health API デモ

Google Health API（v4）で自分の Google アカウントの健康データを取得し、ターミナルに表示するサンプルです。

## できること

- Google OAuth 2.0 で認証
- **直近1週間**のデータを取得して表示
  - 日別歩数
  - 日別距離
  - 睡眠（就寝・起床・睡眠時間）

## 前提条件

1. [Google Cloud Console](https://console.cloud.google.com/) で
   **Google Health API** を有効化
2. OAuth 2.0 クライアント（Web アプリケーション）を作成
3. ルートの `.env` に認証情報を設定

```env
GOOGLE_CLIENT_ID="your-client-id"
GOOGLE_CLIENT_SECRET="your-client-secret"
```

### GCP の OAuth 設定

| 項目 | 設定値 |
| --- | --- |
| 承認済みリダイレクト URI | `http://127.0.0.1:8000/callback` |
| 承認済み JavaScript 生成元 | 不要（空でOK） |

GCP 側のリダイレクト URI と **完全一致** させてください。

## 実行方法

プロジェクトルートで:

```powershell
uv sync
uv run python -m demo.main
```

### 動作の流れ

```text
初回
  1. ローカルサーバー起動（:8000）
  2. ブラウザで Google ログイン
  3. /callback でトークン取得 → demo/.token.json に保存
  4. 健康データをターミナルに表示 → 自動終了

2回目以降
  1. 保存済みトークンを使用（再ログイン不要）
  2. データ取得 → 表示 → 自動終了
```

再認証したい場合:

```powershell
Remove-Item demo\.token.json
uv run python -m demo.main
```

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `main.py` | エントリポイント。FastAPI で OAuth、データ取得の起動 |
| `auth.py` | OAuth 認可 URL 生成、トークン交換・更新 |
| `config.py` | 環境変数、スコープ、API エンドポイント |
| `health_client.py` | Google Health API 呼び出し、ターミナル出力 |
| `.token.json` | 保存された OAuth トークン（自動生成・git 除外） |

## 使用している API

ベース URL: `https://health.googleapis.com/v4`

| データ | メソッド | データタイプ |
| --- | --- | --- |
| プロフィール | `GET /users/me/profile` | — |
| 日別歩数 | `POST .../steps/dataPoints:dailyRollUp` | `steps` |
| 日別距離 | `POST .../distance/dataPoints:dailyRollUp` | `distance` |
| 睡眠 | `GET .../sleep/dataPoints` | `sleep` |

### OAuth スコープ

- `googlehealth.activity_and_fitness.readonly` — 歩数・距離
- `googlehealth.sleep.readonly` — 睡眠
- `googlehealth.profile.readonly` — プロフィール

## 参考リンク

- [Google Health API セットアップ](https://developers.google.com/health/setup)
- [REST リファレンス](https://developers.google.com/health/reference/rest)
- [データタイプ一覧](https://developers.google.com/health/data-types)
