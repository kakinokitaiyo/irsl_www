````markdown
# Gemini VLM 逆質問統合 - 実装完了レポート (Appendix - Full Detail)

The following file contains the full original FINAL_REPORT.md content (archived as appendix).

## 2026-06-02 追記: DINOv2 再ランキングの詳細

### アーキテクチャ

- SBIR 粗検索: SketchScape
- 再ランキング: DINOv2 + SketchScape の重み付き融合
- 埋め込みソース:
	1. `.npz` キャッシュ
	2. DB `home_robot.photo_embeddings`
	3. オンザフライ計算（候補のみ）

### 主要ファイル

- `CLIP_DB/src/run_sbir_once_from_db.py`
- `CLIP_DB/src/tools/compute_dinov2_embeddings_db.py`
- `irsl_www/script/sub_writing1.py`

### 代表的な実行例

```bash
export ENABLE_DINOV2_FUSION=true
export SBIR_DINO_WEIGHT=0.3
cd /home/irsl/workspace/irsl_www/script
python3 sub_writing1.py
```

### 検証結果

- `writing_1.png` で `apple.jpeg` が rank 1 へ上昇
- `peach.jpeg` が Top-5 へ上昇
- DINOv2 埋め込みは PostgreSQL に 74 件保存済み

---

Full technical report archived here. Refer to `FINAL_REPORT.md` for the executive summary and links to this appendix.

````
