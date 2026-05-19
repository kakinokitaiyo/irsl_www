Error Fix — 短いチェンジログ

日付: 2026-05-18

問題: Gemini API 呼び出しで "Budget 0 is invalid" エラーが発生しました（Gemini 2.5 Pro）。

原因: `GenerateContentConfig` に `thinking_config=types.ThinkingConfig(thinking_budget=0)` が含まれており、`thinking_budget=0` は無効でした。

対応:

- `gemini_api.py` の `GenerateContentConfig` から `thinking_config` を削除し、`temperature=0.2` のみを使用するよう修正しました。

検証: 修正後、VLM 呼び出しは成功し、期待される JSON 応答が得られることを確認しました。

生ログ（詳細・スニペット）はアーカイブに保存しています:

  `script/logs/error_fix_2026-05-18.log`

再現手順（短縮）:

```bash
python3 -m py_compile gemini_api.py
python3 sub_writing1.py
# スケッチを描いて Send をクリック
```

参照:

- プロンプト・仕様: `PROMPT_IMPROVEMENT.md`
- フルレポート: `FINAL_REPORT_APPENDIX.md`

---

このファイルは短いチェンジログとして運用し、詳細は上記ログファイルに保管します。
# Gemini API エラー修正 - 2026年5月18日

## エラー内容

```
[ERROR] VLM processing failed: Gemini API call failed: 400 INVALID_ARGUMENT. 
{'error': {'code': 400, 'message': 'Budget 0 is invalid. This model only works in thinking mode.', 'status': 'INVALID_ARGUMENT'}}
```

## 原因分析

Gemini 2.5 Pro モデルでは thinking mode の設定に問題がありました。

**問題点:**
```python
config=types.GenerateContentConfig(
    temperature=0.2,
    thinking_config=types.ThinkingConfig(thinking_budget=0)  # ❌ Budget 0 は無効
)
```

`thinking_budget=0` の設定は無効であり、Gemini APIが拒否しました。

## 修正内容

**修正ファイル:** `gemini_api.py`

**修正前:**
```python
config=types.GenerateContentConfig(
    temperature=0.2,
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)
```

**修正後:**
```python
config=types.GenerateContentConfig(
    temperature=0.2  # Thinking config を削除
)
```

## 修正の効果

- ✅ Gemini API エラーが解消
- ✅ VLM処理が正常に実行される
- ✅ JSON形式のVLM決定結果が取得できる

## テスト結果

修正後の実行ログ:
```
[INFO] [1779090252.930117]: Saved image to: writing_26.png
[INFO] [1779090257.774023]: Initiating VLM reverse questioning...
[INFO] [1779090261.606491]: VLM processing completed ✅ (エラーなし)
[INFO] [1779090261.609564]: SBIR result saved
```

## 再実行手順

```bash
# 1. スクリプトが修正されていることを確認
python3 -m py_compile gemini_api.py

# 2. 再度実行
python3 sub_writing1.py

# 3. スケッチを描いて Send をクリック
```

## 今後の確認事項

修正後のVLM結果を確認するには、生成されたJSONファイルを確認してください：

```bash
# 最新の結果ファイルを確認
cat ../sketch_result/writing_*.json | python3 -m json.tool | tail -50
```

期待される出力形式:
```json
{
  "vlm_decision": {
    "extracted_features": "スケッチから抽出された特徴",
    "action_type": "execute" or "ask_user",
    "selected_id": 0,
    "robot_question": "..."
  }
}
```

## 参考資料

- [Gemini API Documentation](https://ai.google.dev/docs)
- [VLM_SETUP_GUIDE.md](VLM_SETUP_GUIDE.md)
- [gemini_api.py](gemini_api.py)

---

**修正完了日:** 2026年5月18日  
**ステータス:** ✅ 本番運用可能
