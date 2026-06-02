# Gemini VLM 逆質問統合 - 実装完了サマリー

> 2026-05-22 更新（重要）
>
> このファイルの下部には過去の記述も残っています。実運用で参照すべき最新仕様はこの更新セクションです。

## 追加更新サマリー（2026-06-02）

### 1) DINOv2 再ランキングの導入

- `run_sbir_once_from_db.py` に DINOv2 フュージョンを追加
  - `--enable_dinov2_fusion`
  - `--dinov2_weight`
  - `--dinov2_embeddings_path`
- 埋め込み参照の優先順を整理
  - `.npz` キャッシュ
  - DB `home_robot.photo_embeddings`
  - オンザフライ計算（候補のみ）
- `sub_writing1.py` からも環境変数 `ENABLE_DINOV2_FUSION=true` で有効化可能

### 2) DB 保存と運用確認

- DINOv2 埋め込みを PostgreSQL に保存済み
- `writing_1.png` で end-to-end テストを実施
  - `apple.jpeg`: rank 7 → 1
  - `peach.jpeg`: rank 9 → 5

### 3) 既存 VLM 仕様との共存

- VLM 逆質問フローはそのまま維持
- DINOv2 は SBIR の再ランキング層として動作
- `ENABLE_CLIP_FUSION=false` のままでも DINOv2 だけ有効化可能

## 最新変更サマリー（2026-05-22）

### 1) 逆質問フローの拡張

- `action_type` を 3 分岐化
  - `execute`: 候補1件に確定
  - `ask_user`: 追加質問で絞り込み
  - `resketch`: Top5に正解が無い可能性が高い
- `question_mode` を導入
  - `yes_no`: 候補2件
  - `multi_choice`: 候補3件以上（YES/NOでは選べない）

### 2) ユーザー操作（UI）

- `touch.html` で以下の入力をサポート
  - `yes`
  - `no`
  - `neither`（どちらでもない）
  - `resketch`（もう一度描く）
- 類似候補が3件以上ある場合は、候補ボタン選択式に切替
- ユーザー回答を `/vlm_user_feedback` に publish

### 3) VLM 応答正規化の強化（`gemini_api.py`）

- `candidate_analysis` から `remaining_candidates` を再構築
- 候補数と `action_type` の整合を強制
  - keep=0 → `resketch`
  - keep=1 → `execute`
  - keep>=2 → `ask_user`
- ID を UI 表示用に 1..5 へ正規化

### 4) モデル指定エラー対策

- `GEMINI_MODEL` が不正形式で失敗した場合、`gemini-2.5-pro` へ自動フォールバック
- `unexpected model name format` の復旧性を改善

### 5) 現在の実運用 JSON スキーマ（抜粋）

```json
{
  "action_type": "execute | ask_user | resketch",
  "question_mode": "null | yes_no | multi_choice",
  "binary_mapping": {"yes_candidate_id": 1, "no_candidate_id": 3},
  "user_options": ["yes", "no", "neither", "resketch"],
  "decision_schema_version": "2.0"
}
```

---

## 実装内容

### 0. **DINOv2 フュージョン** - SBIR 再ランキング層

**主な処理:**

1. スケッチに対して DINOv2 埋め込みを取得
2. 候補画像について DINOv2 埋め込みを取得
3. SketchScape スコアと正規化後に重み付き融合
4. Top-k を再ソートして JSON 出力

**運用優先順位:**
- DB 埋め込みがあればそれを使用
- なければ候補画像のみオンザフライで埋め込みを計算

**テスト結果:**
- `writing_1.png` で apple / peach が Top-5 に浮上

### 1. **gemini_api.py** - VLMコア機能モジュール

**主な関数:**

**処理フロー:**
1. スケッチ + Top5候補 計6枚を Base64 エンコード
2. Gemini 2.5-pro モデルへ送信
3. JSON形式の VLM 決定結果をパース
4. SBIR結果に `vlm_decision` フィールドを追加

**出力形式:**
```json
{
  "extracted_features": "抽出された特徴",
  "candidate_analysis": [...],
  "remaining_candidates": [0, 2, 4],
  "action_type": "execute" | "ask_user",
  "reasoning": "判断理由",
  "selected_id": 1,
  "robot_question": "（ask_userの場合のみ）"
}
```

### 2. **sub_writing1.py** - ROS統合

**修正内容:**

**処理順序:**
```
スケッチ受信 
  → SBIR 実行（Top5獲得）
    → Web用画像コピー
      → VLM 処理（Gemini API呼び出し）
        → 結果を JSON ファイルに保存
          → ROS Topic `/sbir_top5` に発行
```

**VLM失敗時:**

### 3. **touch.html** - フロントエンド拡張

**追加機能:**

**表示例:**

**決定確定時（execute）:**
```
✓ 決定: 候補#2を推奨
理由: 候補2だけがハンドルと円形のボディの両方を持っています。
```

**ユーザー質問時（ask_user）:**
```
❓ ユーザーへの質問:
候補1と3はどちらも円形のボディを持っていますが、
候補1は赤、候補3は青です。あなたが探しているのはどちらの色ですか？

残った候補: #1, #3
```

**スタイリング:**

### 4. **.env.example** - 環境変数テンプレート

**新規追加項目:**
```bash
# VLM (Vision Language Model) Reverse Questioning
GEMINI_API_KEY=your-gemini-api-key-here
ENABLE_VLM=true

# DB Connection Retry (for resilience)
DB_CONNECT_RETRIES=3
DB_CONNECT_RETRY_SECONDS=1.5
```

### 5. **VLM_INTEGRATION.md** - ドキュメント

詳細なセットアップガイド:

## VLM の動作メカニズム

### ステップ1: 意図の抽出
```
スケッチを観察
  ↓
特徴言語化: 「ハンドルがある」「突起がある」など
  ↓
extracted_features: "..."
```

### ステップ2: 候補の再評価
```
各候補 (ID 0-4) に対して
  ↓
特徴マッチング: ✓/✗
  ↓
candidate_analysis: [
  {"id": 0, "has_features": true, "reasoning": "..."},
  ...
]
```

### ステップ3: アクション決定
```
残った候補の数
  ├─ 1つ: execute (selected_id を出力)
  ├─ 2+確信: execute (confidence が高い方)
  └─ 2+不確定: ask_user (逆質問を生成)
```

## 使用方法

### セットアップ
```bash
# 1. 依存パッケージをインストール
pip install google-genai

# 2. API キーを取得
# → https://aistudio.google.com

# 3. 環境変数を設定
export GEMINI_API_KEY="your-key"
export ENABLE_VLM=true

# 4. sub_writing1.py を起動
python3 sub_writing1.py
```

### フロントエンド
```
1. touch.html にアクセス
2. キャンバスにスケッチを描画
3. "Send" ボタンをクリック
4. SBIR Top5 + VLM決定 が表示される
   - 決定確定時: 推奨候補が強調表示
   - 質問時: 逆質問が表示される
```

### CLI テスト
```bash
python3 gemini_api.py \
  --sketch /path/to/sketch.png \
  --candidate_dir /path/to/candidates/ \
  --api_key your-key
```

## エラーハンドリング

| シーン | 対応 |
|--------|------|
| `GEMINI_API_KEY` 未設定 | エラーログ + SBIR結果のみ返却 |
| Gemini API タイムアウト | ログ出力 + SBIR結果のみ返却 |
| JSON パースエラー | ログ出力 + SBIR結果のみ返却 |
| `ENABLE_VLM=false` | VLM処理をスキップ |

**重要:** VLM処理の失敗は SBIR パイプラインを中断しない設計

## パフォーマンス

| 処理 | 時間 | 備考 |
|------|------|------|
| SBIR（Top5取得） | 1-3秒 | GPU依存 |
| VLM（Gemini API） | 5-15秒 | ネットワーク依存 |
| 合計 | 6-18秒 | 非同期実行で短縮可能 |

**最適化:**

## 今後の拡張案

1. **非同期VLM処理**
   - SBIR結果を先に返して、VLM結果は後続通知

2. **対話メカニズム**
   - ユーザーが逆質問に回答
   → 追加情報でVLMを再実行
   → 確度の高い候補を絞り込み

3. **学習ループ**
   - ユーザーの選択を記録
   → 次回のVLM判定に学習データとして活用

4. **複数言語対応**
   - システムプロンプトを多言語化
   - ユーザー質問を母国語で生成

5. **キャッシング**
   - VLMの判定結果をキャッシュ
   - 同じスケッチに対する再実行を高速化

## ファイル一覧

| ファイル | 変更タイプ | 説明 |
|---------|----------|------|
| `gemini_api.py` | 新規 | VLMコアモジュール |
| `sub_writing1.py` | 修正 | VLM統合点 |
| `touch.html` | 修正 | フロントエンド拡張 |
| `CLIP_DB/.env.example` | 修正 | 環境変数テンプレート |
| `VLM_INTEGRATION.md` | 新規 | セットアップガイド |

## テスト手順

```bash
# 1. 単体テスト（VLMのみ）
python3 gemini_api.py \
  --sketch test_sketch.png \
  --candidate_dir test_candidates/ \
  --api_key your-key

# 2. 統合テスト（SBIR + VLM）
export GEMINI_API_KEY=your-key
export ENABLE_VLM=true
python3 sub_writing1.py

# 別ターミナル:
# touch.html にアクセスしてスケッチを描画して送信
```

## 注意事項

⚠️ **API 利用制限:**

⚠️ **画像処理:**

⚠️ **デバッグモード:**


**実装完了日:** 2026年5月18日  
**ステータス:** ✅ 本番運用可能
