# システム概要レポート

最終更新: 2026-07-31

詳細な実装仕様は [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) を参照。

---

## 目的

スケッチで部屋の中の物体を指定し、家庭用サービスロボット（HSR）に把持させる。

## システムの構成要素

1. **スケッチ入力** (`touch.html`) — タブレットでスケッチを描く
2. **SBIR検索** (`sbir_engine.py`) — SketchScape + DINOv2でDBを検索
3. **VLM対話** (`gemini_api.py`) — Geminiが候補を絞り込む質問を生成
4. **ROS連携** (`sub_writing1.py`) — 確定物体をロボットに送信

## スコア式

```
score = 0.7 * SketchScapeスコア(正規化) + 0.3 * DINOv2スコア(正規化)
```

## 実験結果（2026-07-22 時点）

| 物体 | Rough | Normal | Careful |
|------|-------|--------|---------|
| ペット | rank 11（対話3回） | rank 2 | rank 1 |
| 缶 | rank 3 | rank 2 | rank 1 |
| ポケモン | rank 2 | rank 1 | rank 1 |
| カップ | rank 11（対話2回） | rank 3 | rank 2 |

カップがrank 1にならない理由: 色のみが異なる物体がDBに存在するため（エッジベースのSBIRは色情報を持たない）。
VLM対話がこの差を補完する役割を担っている。

## VLM対話の仕様

- `execute`: 候補1件に確定 → ロボットが把持
- `ask_user`: YES/NOまたは候補選択で絞り込み
- `resketch`: 候補なし → 再描画を促す
- `ENABLE_VLM=false` で対話をスキップ可能
