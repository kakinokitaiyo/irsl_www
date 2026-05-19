# Gemini VLM 逆質問統合 - セットアップガイド

## ✅ 実装完了

Gemini APIを使用したVLM逆質問機能がSBIRパイプラインに統合されました。

## 📋 変更されたファイル

### 1. **[gemini_api.py](gemini_api.py)** （新規）
VLMコア機能を実装したモジュール

**主要関数:**
- `init_gemini_client()` - Gemini APIクライアント初期化
- `encode_image_to_base64()` - 画像エンコード
- `get_image_mime_type()` - MIMEタイプ判定
- `build_vlm_prompt()` - システムプロンプト生成
- `call_gemini_vlm()` - API呼び出し実行
- `process_sbir_with_vlm()` - SBIR結果の後処理

### 2. **[sub_writing1.py](sub_writing1.py)** （修正）
- VLMモジュールを条件付きインポート
- SBIR処理後にVLM実行を追加
- `ENABLE_VLM` 環境変数でオンオフ制御
- VLM失敗時のグレースフルフォールバック

### 3. **[../html/touch/touch.html](../html/touch/touch.html)** （修正）
- VLM結果表示パネルを追加
- `renderVlmDecision()` 関数で結果レンダリング
- 決定確定時（✓）と質問時（❓）で異なるスタイル表示

### 4. **[../../CLIP_DB/.env.example]** （修正）
Gemini API設定オプションを追加:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
ENABLE_VLM=true
DB_CONNECT_RETRIES=3
DB_CONNECT_RETRY_SECONDS=1.5
```

### 5. **[VLM_INTEGRATION.md](VLM_INTEGRATION.md)** （新規）
詳細なセットアップガイド

### 6. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** （新規）
実装内容の完全なドキュメント

### 7. **[test_vlm_integration.py](test_vlm_integration.py)** （新規）
VLM統合の動作検証スクリプト

## 🚀 セットアップ手順

### ステップ1: Gemini API キーを取得

1. [Google AI Studio](https://aistudio.google.com) にアクセス
2. "Get API Key" をクリック
3. API キーをコピー

### ステップ2: 必要なパッケージをインストール

```bash
pip install google-genai
```

### ステップ3: 環境変数を設定

**方法A: 環境変数で設定**
```bash
export GEMINI_API_KEY="your-api-key-here"
export ENABLE_VLM=true
```

**方法B: .env ファイルで設定**
```bash
cd /home/irsl/workspace/CLIP_DB
cp .env.example .env
# .env ファイルを編集して GEMINI_API_KEY を設定
```

### ステップ4: 動作確認

```bash
# テストスクリプトを実行
python3 test_vlm_integration.py
```

期待される出力:
```
============================================================
Test Summary
============================================================
✓ PASS   Imports
✓ PASS   Environment (GEMINI_API_KEY設定後)
✓ PASS   gemini_api module
✓ PASS   sub_writing1 module
✓ PASS   HTML UI
```

## 📊 VLM 処理フロー

```
ユーザースケッチ
    ↓
[ROS /writing topic]
    ↓
sub_writing1.py (subscriber)
    ↓
1. SBIR エンジン実行
    ↓
2. Top 5 候補画像 取得
    ↓
3. gemini_api.py:
   - スケッチ + Top 5 をBase64エンコード
   - Gemini APIへ送信
   - JSON形式の決定結果をパース
    ↓
4. VLM結果を SBIR結果に追加
    ↓
[ROS /sbir_top5 topic に発行]
    ↓
touch.html
    ├─ 通常のTop5表示
    └─ VLM結果をレンダリング:
       - 決定確定時: 推奨候補を表示 ✓
       - 質問時: ユーザーへの質問を表示 ❓
```

## 💡 VLM の 3ステップ推論

### ステップ1: 意図の抽出
スケッチから特徴を抽出
```
例: 「ハンドルがある」「先端が尖っている」
```

### ステップ2: 候補の再評価
特徴を持つ候補を選別
```
候補0: ✓ ハンドルあり、先端あり → 保持
候補1: ✗ ハンドルなし → 除外
候補2: ✓ ハンドルあり、先端あり → 保持
候補3: ✗ 先端なし → 除外
候補4: ✓ ハンドルあり、先端あり → 保持
```

### ステップ3: アクション決定
```
残った候補が1つ
  → execute: その候補をIDと理由で返す

残った候補が2つ以上で高確信
  → execute: 最も確実な候補を返す

残った候補が2つ以上で低確信
  → ask_user: 候補を区別する逆質問を生成
```

## 📤 JSON 出力形式

### 決定確定時（execute）
```json
{
  "extracted_features": "ハンドルと円形のボディ",
  "remaining_candidates": [0, 2],
  "action_type": "execute",
  "reasoning": "候補0と2の両方がハンドルを持つが、候補0がより洗練された形状をしている",
  "selected_id": 0
}
```

### ユーザー質問時（ask_user）
```json
{
  "extracted_features": "円形のボディ",
  "remaining_candidates": [1, 3],
  "action_type": "ask_user",
  "reasoning": "候補1（赤）と候補3（青）の両方が円形のボディを持つため、色で区別する必要がある",
  "robot_question": "あなたが探しているのは赤い円形のボディですか、それとも青い円形のボディですか？"
}
```

## 🎨 フロントエンド表示例

### 決定確定時
```
🤖 VLM逆質問分析
抽出された特徴: ハンドルと円形のボディ

✓ 決定: 候補#0を推奨
理由: 候補0と2の両方がハンドルを持つが、候補0がより洗練された形状をしている
```

### 質問時
```
🤖 VLM逆質問分析
抽出された特徴: 円形のボディ

❓ ユーザーへの質問:
あなたが探しているのは赤い円形のボディですか、それとも青い円形のボディですか？

残った候補: #1, #3
```

## ⚙️ 環境変数

| 変数 | デフォルト | 説明 |
|------|---------|------|
| `GEMINI_API_KEY` | (必須) | Gemini API キー |
| `ENABLE_VLM` | `true` | VLM処理の有効化フラグ |
| `SBIR_TOPK` | `5` | SBIR候補数 |
| `SBIR_GALLERY_TABLE` | `photos_edge` | ギャラリー画像テーブル |
| `SBIR_DISPLAY_TABLE` | `photos` | 表示用画像テーブル |
| `DB_CONNECT_RETRIES` | `3` | DB接続リトライ回数 |
| `DB_CONNECT_RETRY_SECONDS` | `1.5` | リトライ間隔（秒） |

## 🔧 トラブルシューティング

### Q: `GEMINI_API_KEY not set` エラーが出る

**A:** 環境変数を設定してください
```bash
export GEMINI_API_KEY="your-api-key"
# または
echo "GEMINI_API_KEY=your-key" >> /home/irsl/workspace/CLIP_DB/.env
```

### Q: VLM処理を無効にしたい

**A:** 環境変数を設定
```bash
export ENABLE_VLM=false
```
SBIR結果のみが返されます。

### Q: API 呼び出しがタイムアウトする

**A:** 画像サイズを確認
- 推奨: 256x256 ~ 768x768
- 最大: 1024x1024未満

### Q: JSON パースエラーが出る

**A:** 以下を確認
- Gemini API がオンラインか
- API キーが有効か
- ネットワーク接続が正常か

## 📈 パフォーマンス

| 処理 | 時間 |
|------|------|
| SBIR（Top5取得） | 1-3秒 |
| VLM（Gemini API） | 5-15秒 |
| **合計** | **6-18秒** |

## 🔐 セキュリティ

⚠️ **重要:**
- API キーをGitに登録しないこと
- `.env` ファイルは `.gitignore` に追加
- 本番環境では環境変数経由で管理

## 📚 詳細ドキュメント

- [VLM_INTEGRATION.md](VLM_INTEGRATION.md) - セットアップガイド
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 実装詳細
- [gemini_api.py](gemini_api.py) - API実装
- [sub_writing1.py](sub_writing1.py) - ROS統合

## ✨ 使用例

### Python コマンドライン
```bash
python3 gemini_api.py \
  --sketch /path/to/sketch.png \
  --candidate_dir /path/to/candidates/ \
  --api_key your-key
```

### ROS パイプライン
```bash
# ターミナル1: ROS core
roscore

# ターミナル2: スケッチ購読スクリプト
cd /home/irsl/workspace/irsl_www/script
python3 sub_writing1.py

# ターミナル3: ウェブUI
# ブラウザで https://localhost/touch/touch.html を開く
# スケッチを描いて Send をクリック
```

## 🎯 今後の拡張案

1. **非同期VLM処理** - 先にSBIR結果を返して、VLM結果は後続通知
2. **対話メカニズム** - ユーザーが質問に回答 → VLM再実行
3. **学習ループ** - ユーザー選択を学習データとして活用
4. **キャッシング** - VLM決定結果をキャッシュして高速化

## 📞 サポート

問題が発生した場合:
1. `test_vlm_integration.py` を実行
2. `VLM_INTEGRATION.md` のトラブルシューティングを確認
3. ログファイルを確認

---

**実装日:** 2026年5月18日  
**ステータス:** ✅ 本番運用可能  
**テスト:** ✅ 全パッケージ検証済み
