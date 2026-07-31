# エラー修正ログ

---

## Gemini API エラー

### `Budget 0 is invalid`（2026-05-18）

**原因:** `thinking_config=ThinkingConfig(thinking_budget=0)` を設定していた。  
**対応:** `thinking_config` を削除、`temperature=0.2` のみで呼び出す。

---

### `unexpected model name format`（2026-05-22）

**原因:** `GEMINI_MODEL` の値が API の期待形式と不一致。  
**対応:** `gemini_api.py` にフォールバック処理を追加。形式不正時は `gemini-2.5-pro` で再試行。

---

## DINOv2 スコア重みのバグ（2026-07-22）

**原因:** 環境変数 `SBIR_DINO_WEIGHT=0.7` が残っていたため、
`scape_weight=0.7` + `dino_weight=0.7` → 正規化されて実質 0.5/0.5 になっていた。  
**対応:** `unset SBIR_DINO_WEIGHT` で環境変数を削除。
`sub_writing1.py` の `run_sbir_once()` で `--scape_weight` を明示的に渡すよう修正。  
現在のデフォルト: SketchScape=0.7, DINOv2=0.3。
