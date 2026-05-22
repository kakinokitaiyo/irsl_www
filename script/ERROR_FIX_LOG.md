# ERROR_FIX_LOG

最終更新: 2026-05-22

このファイルは VLM 統合で発生した主要エラーと修正内容の要約です。

## 現在の使用モデル

- ✅ 採用モデル: `gemini-robotics-er-1.6-preview`

## エラー履歴と修正

### 1) `Budget 0 is invalid` エラー（2026-05-18）

**症状**
- Gemini API 呼び出し時に `400 INVALID_ARGUMENT` が発生。
- メッセージ: `Budget 0 is invalid. This model only works in thinking mode.`

**原因**
- `GenerateContentConfig` に `thinking_config=types.ThinkingConfig(thinking_budget=0)` を設定していた。

**対応**
- `thinking_config` を削除し、`temperature=0.2` のみで呼び出すよう変更。

---

### 2) `unexpected model name format` エラー（2026-05-22）

**症状**
- Gemini API 呼び出し時に `400 INVALID_ARGUMENT`。
- メッセージ: `GenerateContentRequest.model: unexpected model name format`

**原因**
- `GEMINI_MODEL` の値（またはコード内モデル名）が API 期待形式と不一致。

**対応**
- モデルIDを `gemini-robotics-er-1.6-preview` に統一。
- `gemini_api.py` にモデル呼び出し失敗時のフォールバック処理を追加。
  - 形式不正/未対応モデル時に既定モデルへ再試行。

---

## 検証結果

- `python3 -m py_compile gemini_api.py` は通過。
- `sub_writing1.py` 実行時、VLM 失敗時も SBIR パイプラインは継続（設計どおり）。

## 参照

- 実装概要: `IMPLEMENTATION_SUMMARY.md`
- プロンプト方針: `PROMPT_IMPROVEMENT.md`
- 最終報告: `FINAL_REPORT.md`
- 旧生ログアーカイブ: `logs/error_fix_2026-05-18.log`
