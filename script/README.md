# script フォルダの読み方

最終更新: 2026-07-31

## ファイル構成

| ファイル | 内容 |
|---------|------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 現在の実装仕様・環境変数一覧（メインドキュメント） |
| [FINAL_REPORT.md](FINAL_REPORT.md) | システム概要と実験結果 |
| [PROMPT_IMPROVEMENT.md](PROMPT_IMPROVEMENT.md) | Gemini VLMのプロンプト方針 |
| [ERROR_FIX_LOG.md](ERROR_FIX_LOG.md) | 過去のエラーと修正内容 |

## コードファイル

| ファイル | 役割 |
|---------|------|
| `sub_writing1.py` | ROSノード本体 |
| `sbir_engine.py` | モデル常駐エンジン（2026-07-31追加） |
| `gemini_api.py` | Gemini VLM対話モジュール |
| `test_vlm_integration.py` | VLM統合テスト用 |
| `sub_audio.py` / `cog_speech.py` / `text_to_speech.py` | 音声関連 |

## 起動コマンド

### 通常起動（推奨）

```bash
cd /home/irsl/workspace/irsl_www/script
source /home/irsl/workspace/.venv.backup.1777612717/bin/activate

export ENABLE_VLM=true
export GEMINI_API_KEY="your-key"

python3 sub_writing1.py
# "[SBIREngine] Ready. gallery=XX images" が出れば成功
```

### VLM なし（SBIRのみ）

```bash
export ENABLE_VLM=false
python3 sub_writing1.py
```

### 写真をDBに追加するとき

```bash
python3 /home/irsl/workspace/CLIP_DB/src/register_photos_and_edges.py \
  --source_dir /path/to/new_photos \
  --enable_dinov2 \
  --host *** --port *** \
  --dbname *** \
  --user *** --password *** \
  --schema home_robot
# 追加後はノードを再起動するだけ
```

## 主な環境変数

| 変数 | デフォルト | 説明 |
|-----|-----------|------|
| `ENABLE_VLM` | `true` | VLM対話の有効/無効 |
| `GEMINI_API_KEY` | — | Gemini APIキー |
| `SBIR_SCAPE_WEIGHT` | `0.7` | SketchScapeの重み |
| `SBIR_DINO_WEIGHT` | `0.3` | DINOv2の重み |
| `SBIR_THUMB_SIZE` | `320` | サムネイル画像サイズ(px) |
| `EXPERIMENT_TARGET` | — | 実験対象物体名（ログ用） |
| `EXPERIMENT_QUALITY` | — | スケッチ品質（ログ用） |
