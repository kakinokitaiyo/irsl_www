# script フォルダの読み方

このフォルダには、Gemini VLM 逆質問統合に関するコードと説明ファイルが入っています。  
どれを先に読めばよいか分かるように、目的別に整理しています。

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

## すぐ試すとき（最小）

```bash
export GEMINI_API_KEY="your-key"
export ENABLE_VLM=true
export GEMINI_MODEL="gemini-2.5-pro"
python3 sub_writing1.py
```

