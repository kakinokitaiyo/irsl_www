# script フォルダの読み方

このフォルダには、Gemini VLM 逆質問統合に関するコードと説明ファイルが入っています。  
どれを先に読めばよいか分かるように、目的別に整理しています。

## まずどこを見ればよいか

実行コマンドを探している場合は、次の順で読むと分かりやすいです。

1. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
	- いまの実装内容と、どの機能がどこで動くかをまとめています。
	- DINOv2、VLM、ROS 連携の関係もここで確認できます。
2. [FINAL_REPORT.md](FINAL_REPORT.md)
	- まず短く全体像をつかみたいときに向いています。
3. [FINAL_REPORT_APPENDIX.md](FINAL_REPORT_APPENDIX.md)
	- 実行例や技術詳細を見たいときに参照します。

迷ったら、次の 3 か所を見れば足ります。

- `sub_writing1.py` の起動方法 → このファイルの最下部「すぐ試すとき」
- VLM の動作確認 → [test_vlm_integration.py](test_vlm_integration.py)
- DINOv2 / SBIR の実行例 → [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) と [../README.md](../README.md)

## まず読むもの

### 1. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- まず全体像を知りたいときに読むファイルです。
- 何を実装したか
- どう動くか
- どのファイルが何を担当するか
- 実行方法や注意点
- **2026-05-22 の最新変更点**（`ask_user/execute/resketch`、`yes_no/multi_choice`）も先頭に追記済みです。

### 2. [PROMPT_IMPROVEMENT.md](PROMPT_IMPROVEMENT.md)
- VLM の判断方針を知りたいときに読むファイルです。
- どんな特徴を重視するか
- どんなときに候補を残すか
- 逆質問をどう作るか
- **最新追記:** 候補数に応じて `yes_no` と `multi_choice` を切り替える方針を追加。

## 次に読むもの

### 3. [FINAL_REPORT.md](FINAL_REPORT.md)
- 実装の成果を短くまとめた報告書です。
- 目的、成果、次の改善案を知りたいときに向いています。
- **最新追記:** 2026-05-22 の変更（UI選択肢追加・モデルフォールバック）を反映済み。

### 4. [FINAL_REPORT_APPENDIX.md](FINAL_REPORT_APPENDIX.md)
- 最終報告の詳細版です。
- 技術的な補足や長めの説明を確認したいときに読んでください。

## デバッグするときに読むもの

### 5. [ERROR_FIX_LOG.md](ERROR_FIX_LOG.md)
- エラー修正の履歴です。
- どんな問題が起きて、どう直したかを確認できます。
- 詳細な生ログは [logs/error_fix_2026-05-18.log](logs/error_fix_2026-05-18.log) にあります。

## コードを見たいとき

- [gemini_api.py](gemini_api.py): VLM の中心処理
- [sub_writing1.py](sub_writing1.py): ROS 連携の入口
- [test_vlm_integration.py](test_vlm_integration.py): 統合テスト用
- [sub_audio.py](sub_audio.py) / [cog_speech.py](cog_speech.py) / [text_to_speech.py](text_to_speech.py): 音声関連

## 現在の重要仕様（2026-05-22）

- `action_type`: `execute` / `ask_user` / `resketch`
- `question_mode`: `yes_no`（2候補）/ `multi_choice`（3候補以上）
- UI選択: `yes` / `no` / `neither` / `resketch`
- モデル名不正時: `gemini-2.5-pro` へのフォールバック

## CLIP_FUSION の設定

`ENABLE_CLIP_FUSION` は、SBIR の結果に CLIP テキスト再ランキングを追加するかどうかを切り替える環境変数です。

- `ENABLE_CLIP_FUSION=true`
	- `sub_writing1.py` が CLIP テキストクエリを作成し、`run_sbir_once_from_db.py` に `--enable_clip_fusion` を渡します。
	- `CLIP_IMAGE_EMBEDDINGS_PATH` があれば事前計算済み埋め込みを使います。
	- `SBIR_CLIP_WEIGHT` と `SBIR_SCAPE_WEIGHT` で重み付けします。
- `ENABLE_CLIP_FUSION=false`
	- CLIP 再ランキングを使いません。
	- SketchScape + DINOv2 だけで動かしたいときは、この設定を false にしておきます。

補足:
- CLIP フュージョンを使うには `clip_text_query` が必要です。
- DINOv2 を使うだけなら `ENABLE_CLIP_FUSION=false` のままで問題ありません。

## おすすめの読み順

1. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
2. [PROMPT_IMPROVEMENT.md](PROMPT_IMPROVEMENT.md)
3. [FINAL_REPORT.md](FINAL_REPORT.md)
4. 必要なら [FINAL_REPORT_APPENDIX.md](FINAL_REPORT_APPENDIX.md)
5. 問題があれば [ERROR_FIX_LOG.md](ERROR_FIX_LOG.md)

## 迷ったときの目安

- 「全体像を知りたい」→ [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- 「VLM の考え方を知りたい」→ [PROMPT_IMPROVEMENT.md](PROMPT_IMPROVEMENT.md)
- 「今までの結果を短く知りたい」→ [FINAL_REPORT.md](FINAL_REPORT.md)
- 「詳しい技術内容を見たい」→ [FINAL_REPORT_APPENDIX.md](FINAL_REPORT_APPENDIX.md)
- 「エラーの原因と修正を見たい」→ [ERROR_FIX_LOG.md](ERROR_FIX_LOG.md)

## すぐ試すとき（最小・最新）

```bash
cd /home/irsl/workspace/irsl_www/script
source /home/irsl/workspace/.venv.backup.1777612717/bin/activate
export GEMINI_API_KEY="your-key"
export ENABLE_VLM=true
python3 sub_writing1.py
# 起動ログに "[SBIREngine] Ready. gallery=73 images" が出れば成功
```

> **2026-07-31 以降:** `sbir_engine.py` により起動時にモデルとギャラリー特徴量を
> 一括ロードします（初回起動は20〜30秒かかりますが、検索は ~0.3秒/回 になります）。
> `ENABLE_DINOV2_FUSION` はデフォルト `true` になりました（DBに埋め込みがあるため）。

## 実行コマンド集（コピペ用）

### 1) 推奨: エンジン常駐 + DINOv2 + VLM対話

```bash
cd /home/irsl/workspace/irsl_www/script
source /home/irsl/workspace/.venv.backup.1777612717/bin/activate

export ENABLE_VLM=true
export GEMINI_API_KEY="your-key"
export ENABLE_DINOV2_FUSION=true   # デフォルトtrue。省略可
export SBIR_SCAPE_WEIGHT=0.7
export SBIR_DINO_WEIGHT=0.3

python3 sub_writing1.py
```

### 2) VLM なし（リアルタイム検索のみ）

```bash
cd /home/irsl/workspace/irsl_www/script
source /home/irsl/workspace/.venv.backup.1777612717/bin/activate

export ENABLE_VLM=false

python3 sub_writing1.py
```

### 3) 新規写真を追加するとき

```bash
# 写真撮影後、DBに登録（DINOv2埋め込みも同時に保存）
python3 /home/irsl/workspace/CLIP_DB/src/register_photos_and_edges.py \
  --source_dir /path/to/new_photos \
  --enable_dinov2 \
  --host 133.15.97.94 --port 5432 \
  --dbname kakinoki_db \
  --user kakinoki_taiyo --password irsl \
  --schema home_robot

# 登録後はノードを再起動するだけでエンジンが新ギャラリーを読み込む
```

### 4) サムネイルサイズを変更するとき

```bash
export SBIR_THUMB_SIZE=240   # 小さく（デフォルト: 320）
export SBIR_THUMB_SIZE=400   # 高画質
```

### 位置関係の補足

- `sub_writing1.py` の実行場所: `irsl_www/script/`
- `sbir_engine.py`: 同フォルダ。モデル常駐エンジン（2026-07-31 追加）
- 生成された結果 JSON: `irsl_www/sketch_result/`
- 実験ログ: `irsl_www/experiment_log.csv`
- 実装詳細: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

