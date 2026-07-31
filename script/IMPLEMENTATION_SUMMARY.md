# SBIR システム 実装サマリー

最終更新: 2026-07-31

---

## システム全体の流れ

```
ユーザーがスケッチを描く
  ↓ (ストローク終了ごと) /writing_partial → リアルタイム検索 → 候補を即時表示
  ↓ (Sendボタン)         /writing         → 確定検索 → VLM対話 → 把持
```

---

## アーキテクチャ

### スコア計算式
```
score = 0.7 * score_sketchscape_norm + 0.3 * score_dinov2_norm
```
環境変数 `SBIR_SCAPE_WEIGHT` / `SBIR_DINO_WEIGHT` で変更可能。

### 主要ファイル

| ファイル | 役割 |
|---------|------|
| `sub_writing1.py` | ROSノード本体。スケッチ受信 → 検索 → VLM対話 → publish |
| `sbir_engine.py` | モデル常駐エンジン。起動時に一括ロード、検索は ~0.3秒 |
| `gemini_api.py` | Gemini VLM対話モジュール |

---

## モデル常駐エンジン（sbir_engine.py）

起動時に1回だけロード、検索時はスケッチエンコードのみ実行。

| タイミング | 処理 | 時間 |
|-----------|------|------|
| 起動時（1回） | SketchScapeモデル + ギャラリー特徴量 + DINOv2埋め込みをロード | 20〜30秒 |
| 検索時（毎回） | スケッチエンコード + 行列積 | ~0.3秒 |

DINOv2埋め込みは `home_robot.photo_embeddings` テーブルから起動時に一括取得。`.npz` ファイルは不要。

---

## VLM対話フロー（gemini_api.py）

```
スケッチ + 候補画像 → Gemini API
  → action_type: execute   → 候補1件に確定 → 把持
  → action_type: ask_user  → YES/NOまたは候補選択でユーザーに質問
  → action_type: resketch  → 候補なし → 再描画を促す
```

`ENABLE_VLM=false` で VLM をスキップ（SBIRのみ動作）。

---

## リアルタイム検索と対話モードの競合対策

`touch.html` の `_dialogueMode` フラグで制御。

| イベント | `_dialogueMode` | 動作 |
|---------|-----------------|------|
| Send クリック | `true` | partial送信停止 |
| resketch / execute 受信 | `false` | partial送信再開 |
| Clear クリック | `false` | partial送信再開 |

---

## 表示画像の軽量化

`_copy_candidates_for_web()` でサムネイルに変換して配信。

- サイズ: 320px（`SBIR_THUMB_SIZE` で変更可）
- EXIF回転を自動補正（`ImageOps.exif_transpose`）
- JPEG quality=82

---

## 実験ログ

`irsl_www/experiment_log.csv` に自動記録。

| カラム | 内容 |
|-------|------|
| `sketch_file` | スケッチファイル名 |
| `sbir_top1_file` / `score` | SBIR上位1件 |
| `dialogue_turns` | VLM対話ターン数 |
| `confirmed_rank` | 確定物体のSBIR順位 |
| `target_object` / `quality_level` | 実験条件 |
| `score_formula` | 使用したスコア式 |

---

## 環境変数一覧

| 変数 | デフォルト | 説明 |
|-----|-----------|------|
| `ENABLE_VLM` | `true` | VLM対話の有効/無効 |
| `GEMINI_API_KEY` | — | Gemini APIキー（必須） |
| `ENABLE_DINOV2_FUSION` | `true` | DINOv2フュージョンの有効/無効 |
| `SBIR_SCAPE_WEIGHT` | `0.7` | SketchScapeスコアの重み |
| `SBIR_DINO_WEIGHT` | `0.3` | DINOv2スコアの重み |
| `SBIR_DIALOGUE_TOPK` | `30` | 初回SBIR取得候補数 |
| `SBIR_THUMB_SIZE` | `320` | サムネイル画像サイズ(px) |
| `EXPERIMENT_TARGET` | — | 実験対象物体名（ログ用） |
| `EXPERIMENT_QUALITY` | — | スケッチ品質（ログ用） |

---

## 写真をDBに追加するとき

```bash
python3 /home/irsl/workspace/CLIP_DB/src/register_photos_and_edges.py \
  --source_dir /path/to/new_photos \
  --enable_dinov2 \
  --host 133.15.97.94 --port 5432 \
  --dbname kakinoki_db \
  --user kakinoki_taiyo --password irsl \
  --schema home_robot
```

追加後にノードを再起動するだけでエンジンが新ギャラリーを自動ロード。
