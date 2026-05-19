# Gemini VLM 逆質問統合ガイド

## 概要

このドキュメントは、SBIR（Sketch-Based Image Retrieval）エンジンに Google Gemini APIを使用したVLM（Vision Language Model）逆質問機能を統合する手順をまとめています。

## アーキテクチャ

```
ユーザースケッチ
    ↓
[ROS /writing topic]
    ↓
sub_writing1.py (subscriber)
    ↓
SBIR エンジン実行
    ↓
Top 5 候補画像 取得
    ↓
gemini_api.py (VLM処理)
    ├─ 画像エンコード（スケッチ + Top 5）
    ├─ Gemini APIへ送信
    └─ JSON形式の決定結果パース
    ↓
結果を Web フロントエンドに送信
    ↓
[ROS /sbir_top5 topic]
    ↓
touch.html (VLM結果表示)
```

## セットアップ

### 1. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com) にアクセス
2. "Get API Key" をクリック
3. 新しいプロジェクトを作成またはプロジェクトを選択
4. API キーをコピー

### 2. 環境変数の設定

`.env` ファイルに以下を追加:

```bash
# Gemini API Key (required for VLM processing)
GEMINI_API_KEY="your-gemini-api-key-here"

# VLM 処理有効化フラグ (default: true)
ENABLE_VLM=true

# その他の既存設定
SBIR_TOPK=5
SBIR_GALLERY_TABLE=photos_edge
SBIR_DISPLAY_TABLE=photos
```

### 3. 必要なPythonパッケージのインストール

```bash
pip install google-genai
```

## VLM の動作フロー

### ステップ1：意図の抽出（Feature Extraction）

VLMがスケッチを分析し、ユーザーが強調して描いている幾何学的特徴やパーツを言語化します。

**例:** 
- 「ハンドルがある」
- 「先端が尖っている」
- 「円形のボディ」

### ステップ2：候補の再評価（Candidate Filtering）

抽出された特徴を実際に持っている候補画像を選別します。

**特徴マッチング:**
- ✓ 特徴がある → 候補として残す
- ✗ 特徴がない → 除外

### ステップ3：アクション決定（Decision Making）

- **決定確定（execute）**: 候補が1つに絞れた場合
  - 選択されたIDと理由を JSON で出力
  - フロントエンド: 推奨候補を強調表示

- **ユーザー質問（ask_user）**: 複数候補が残った場合
  - 候補の視覚的な違いを分析
  - ユーザーへの「逆質問」を生成
  - フロントエンド: 質問を表示 + 対話UI

## JSON 出力形式

```json
{
  "extracted_features": "スケッチから読み取れる特徴の説明",
  "candidate_analysis": [
    {
      "id": 0,
      "has_features": true,
      "reasoning": "このIDの画像が特徴を持つ理由"
    },
    {
      "id": 1,
      "has_features": false,
      "reasoning": "このIDの画像が特徴を持たない理由"
    }
  ],
  "remaining_candidates": [0, 2, 3],
  "action_type": "execute",
  "reasoning": "最終判断に至った理由",
  "selected_id": 0,
  "robot_question": null
}
```

**複数候補の場合:**
```json
{
  "extracted_features": "...",
  "candidate_analysis": [...],
  "remaining_candidates": [1, 3],
  "action_type": "ask_user",
  "reasoning": "複数の候補が同じ特徴を持つため、追加の質問が必要",
  "robot_question": "候補1と3の違いは色です。赤と青のどちらを探していますか？"
}
```

## フロントエンド表示

VLM結果は自動的に `touch.html` に表示されます。

### 決定確定時（execute）
```
🤖 VLM逆質問分析
抽出された特徴: ハンドルがある、円形のボディ

✓ 決定: 候補#2を推奨
理由: 候補2だけがハンドルと円形のボディの両方を持っています。
```

### ユーザー質問時（ask_user）
```
🤖 VLM逆質問分析
抽出された特徴: 円形のボディ

❓ ユーザーへの質問:
候補1と3はどちらも円形のボディを持っていますが、候補1は赤、候補3は青です。
あなたが探しているのはどちらの色ですか？

残った候補: #1, #3
```

## 使用例

### Python スクリプトでの直接使用

```python
from gemini_api import init_gemini_client, process_sbir_with_vlm
import json

# VLM クライアントを初期化
client = init_gemini_client(api_key="your-key-here")

# SBIR結果をVLMで処理
sbir_result = {
    "topk": [
        {"photo_source_path": "/path/to/candidate1.png", ...},
        {"photo_source_path": "/path/to/candidate2.png", ...},
        ...
    ]
}

result = process_sbir_with_vlm(sbir_result, sketch_path="/path/to/sketch.png", client=client)
print(json.dumps(result["vlm_decision"], indent=2))
```

### コマンドラインでのテスト

```bash
python gemini_api.py \
  --sketch /path/to/sketch.png \
  --candidate_dir /path/to/candidates/ \
  --api_key your-gemini-api-key
```

## トラブルシューティング

### 1. `GEMINI_API_KEY` が設定されていない

**エラー:**
```
ValueError: GEMINI_API_KEY not set
```

**解決方法:**
```bash
export GEMINI_API_KEY="your-key"
# または .env ファイルに追加
echo "GEMINI_API_KEY=your-key" >> .env
```

### 2. API 呼び出しがタイムアウト

**エラー:**
```
RuntimeError: Gemini API call failed: ...
```

**原因:** 画像ファイルが大きい、またはネットワーク遅延

**解決方法:**
- 画像サイズを確認（推奨: 1MB以下）
- ネットワーク接続を確認
- API クォータ制限を確認

### 3. VLM の返す JSON が形式に合わない

**エラー:**
```
ValueError: Invalid JSON from Gemini API
```

**解決方法:**
- プロンプトがJSON形式を強制しているか確認
- Gemini のモデルバージョンが最新か確認
- API レスポンスのログを確認

### 4. VLM 処理を無効化したい

`.env` で以下を設定:

```bash
ENABLE_VLM=false
```

VLMなしの通常の SBIR 結果のみが返されます。

## 環境変数一覧

| 変数 | デフォルト | 説明 |
|------|---------|------|
| `GEMINI_API_KEY` | (必須) | Google Gemini API キー |
| `ENABLE_VLM` | `true` | VLM処理の有効化フラグ |
| `SBIR_TOPK` | `5` | SBIR で返す候補数 |
| `SBIR_GALLERY_TABLE` | `photos_edge` | ギャラリー画像テーブル |
| `SBIR_DISPLAY_TABLE` | `photos` | 表示用画像テーブル |

## パフォーマンス

- **SBIR処理**: 1-3秒（GPUあり）
- **VLM処理**: 5-15秒（Gemini API呼び出し含む）
- **合計レイテンシ**: 6-18秒

**最適化のコツ:**
- 不要な場合は `ENABLE_VLM=false` に
- 画像解像度を下げる（推奨: 768x768以下）
- キャッシング機構を利用

## ライセンス

MIT License - 自由に使用・改変可能

## サポート

問題が発生した場合は以下を確認:
1. API キーが正しく設定されているか
2. Gemini API にアクセス権があるか
3. ネットワーク接続
4. Python バージョン（3.8以上推奨）
5. 必要なパッケージがインストール済みか
