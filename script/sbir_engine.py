"""sbir_engine.py — モデル常駐型 SBIR エンジン

起動時にモデルとギャラリー特徴量を一度だけロードし、
検索時はスケッチエンコードのみを実行する（サブプロセス不要）。

通常の run_sbir_once_from_db.py 実行:  ~4秒/回（モデルロード含む）
このエンジン使用時:                   ~0.3秒/回（スケッチエンコードのみ）
"""

from __future__ import annotations

import gc
import os
import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np
import torch

# run_sbir_once_from_db.py の場所
_CLIP_DB_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'CLIP_DB', 'src')
)


class SBIREngine:
    """起動時にモデルとギャラリー特徴量を保持するシングルトンエンジン。"""

    def __init__(self) -> None:
        self._loaded    = False
        self._lock      = threading.Lock()
        # モデル
        self._sbir_model       = None
        self._sketch_transform = None
        self._image_transform  = None
        # ギャラリー（不変）
        self._gallery_features = None  # (N, D) tensor on device
        self._gallery_images   = None  # list[dict]
        self._display_by_key   = None  # dict[str, dict]
        # DINOv2 グローバル埋め込み
        self._dino_model        = None
        self._dino_id_to_index  = None
        self._dino_embeddings   = None
        self._enable_dinov2     = False
        # DINOv2 パッチ埋め込み（部分スケッチマッチング用）
        self._patch_id_to_index = None
        self._patch_embeddings  = None  # (N, 256, 768)
        self._enable_patch      = False
        # CLIP（テキスト照合用）
        self._clip_model        = None
        self._clip_preprocess   = None
        self._clip_tokenizer    = None
        self._enable_clip_text  = False
        # Gemini VLM
        self._gemini_client     = None
        self._enable_gemini     = False
        # デバイス
        self._device = None

    # ------------------------------------------------------------------
    # 初期化
    # ------------------------------------------------------------------

    def load(self) -> None:
        """モデルとギャラリー特徴量をロードする（起動時に1回だけ呼ぶ）。"""
        import argparse

        if _CLIP_DB_SRC not in sys.path:
            sys.path.insert(0, _CLIP_DB_SRC)

        from run_sbir_once_from_db import (
            select_device, load_rgb_image_from_bytes,
            canonical_name_key, resolve_db_images_with_cache,
            fetch_images_from_db, fetch_dinov2_embeddings_from_db,
            fetch_patch_embeddings_from_db,
            load_dinov2_model,
        )

        # 環境変数から設定を読み込む（argparse の Namespace を流用）
        args = argparse.Namespace(
            host     = os.getenv('PGHOST',     '133.15.97.94'),
            port     = int(os.getenv('PGPORT', '5432')),
            dbname   = os.getenv('PGDATABASE', 'kakinoki_db'),
            user     = os.getenv('PGUSER',     'kakinoki_taiyo'),
            password = os.getenv('PGPASSWORD', 'irsl'),
            schema   = os.getenv('SBIR_SCHEMA', 'home_robot'),
            gallery_table       = os.getenv('SBIR_GALLERY_TABLE',       'photos_edge'),
            display_table       = os.getenv('SBIR_DISPLAY_TABLE',       'photos'),
            gallery_source_type = os.getenv('SBIR_GALLERY_SOURCE_TYPE', 'photo_edge'),
            display_source_type = os.getenv('SBIR_DISPLAY_SOURCE_TYPE', 'photo'),
            device      = os.getenv('SBIR_DEVICE', 'auto'),
            sketchscape_root = Path(os.getenv('SKETCHSCAPE_ROOT',
                                              '/home/irsl/workspace/SketchScape')),
            model_path = Path(os.getenv('SBIR_MODEL_PATH',
                                        '/home/irsl/workspace/SketchScape/models/fscoco_normal.pth')),
            coarse_topk = int(os.getenv('SBIR_COARSE_TOPK', '100')),
            exclude_gallery_ids = '',
            # DINOv2
            enable_dinov2_fusion = os.getenv('ENABLE_DINOV2_FUSION', 'true').lower() == 'true',
        )
        self._enable_dinov2 = args.enable_dinov2_fusion

        device = select_device(args.device)
        self._device = device

        # ---- DB からギャラリー・表示画像メタデータを取得 ----
        print('[SBIREngine] Fetching gallery metadata from DB...')
        gallery_meta = fetch_images_from_db(
            args, args.gallery_table, args.gallery_source_type,
            with_data=False, exclude_ids=[],
        )
        display_photos = fetch_images_from_db(
            args, args.display_table, args.display_source_type, with_data=True,
        )

        display_by_key: dict[str, dict] = {}
        for p in display_photos:
            key = canonical_name_key(p['file_name'])
            if key not in display_by_key:
                display_by_key[key] = p
        self._display_by_key = display_by_key

        # ---- SketchScape モデルをロード ----
        sketchscape_root = args.sketchscape_root.expanduser().resolve()
        model_path       = args.model_path.expanduser().resolve()
        if str(sketchscape_root) not in sys.path:
            sys.path.insert(0, str(sketchscape_root))
        from model import SBIRModel

        print(f'[SBIREngine] Loading SketchScape model from {model_path} ...')
        sbir_model = SBIRModel.load_module(
            str(model_path), strict=False, cuda=(device == 'cuda')
        )
        sbir_model = sbir_model.to(device)
        sbir_model.eval()

        self._sketch_transform = sbir_model.create_sketch_transforms()
        image_transform        = sbir_model.create_image_transforms()
        self._image_transform  = image_transform

        # ---- ギャラリー特徴量を一括計算（最も時間がかかる部分） ----
        print('[SBIREngine] Computing gallery features (one-time)...')
        gallery_images = resolve_db_images_with_cache(
            args, args.gallery_table, args.gallery_source_type, gallery_meta,
        )
        self._gallery_images = gallery_images

        with torch.no_grad():
            tensors = []
            for g in gallery_images:
                edge_pil = load_rgb_image_from_bytes(g['image_data'])
                tensors.append(image_transform(edge_pil).unsqueeze(0))
            gallery_batch    = torch.cat(tensors, dim=0).to(device)
            gallery_features = sbir_model(gallery_batch)
            gallery_features = gallery_features / gallery_features.norm(dim=-1, keepdim=True)

        self._gallery_features = gallery_features  # GPU に常駐
        self._sbir_model       = sbir_model

        # ---- DINOv2 グローバル埋め込みを DB から一括ロード ----
        if args.enable_dinov2_fusion:
            photo_ids = [p['id'] for p in display_photos]
            print(f'[SBIREngine] Loading DINOv2 embeddings from DB ({len(photo_ids)} photos)...')
            db_dino_map = fetch_dinov2_embeddings_from_db(args, photo_ids)
            if db_dino_map:
                ids_arr  = np.array(sorted(db_dino_map.keys()), dtype=np.int64)
                emb_arr  = np.stack([db_dino_map[i] for i in ids_arr], axis=0)
                self._dino_id_to_index = {int(pid): idx for idx, pid in enumerate(ids_arr)}
                self._dino_embeddings  = emb_arr
                print(f'[SBIREngine] DINOv2 embeddings loaded: {len(db_dino_map)} entries')
            else:
                print('[SBIREngine] WARNING: no DINOv2 embeddings found in DB')

            # ---- DINOv2 パッチ埋め込みを DB から一括ロード ----
            print(f'[SBIREngine] Loading DINOv2 patch embeddings from DB ({len(photo_ids)} photos)...')
            db_patch_map = fetch_patch_embeddings_from_db(args, photo_ids)
            if db_patch_map:
                p_ids_arr   = np.array(sorted(db_patch_map.keys()), dtype=np.int64)
                patch_arr   = np.stack([db_patch_map[i] for i in p_ids_arr], axis=0)
                self._patch_id_to_index = {int(pid): idx for idx, pid in enumerate(p_ids_arr)}
                self._patch_embeddings  = patch_arr   # (N, 256, 768)
                self._enable_patch      = True
                print(f'[SBIREngine] Patch embeddings loaded: {len(db_patch_map)} entries, shape={patch_arr.shape}')
            else:
                print('[SBIREngine] WARNING: no patch embeddings found in DB')

            print('[SBIREngine] Loading DINOv2 model for sketch encoding...')
            self._dino_model = load_dinov2_model(device)

        # ---- CLIP モデルをロード（テキスト照合用） ----
        try:
            import open_clip as _open_clip
            clip_model, _, clip_preprocess = _open_clip.create_model_and_transforms(
                'ViT-B-32', pretrained='laion2b_s34b_b79k')
            self._clip_model      = clip_model.to(device).eval()
            self._clip_preprocess = clip_preprocess
            self._clip_tokenizer  = _open_clip.get_tokenizer('ViT-B-32')
            self._enable_clip_text = True
            print('[SBIREngine] CLIP text model loaded.')
        except Exception as e:
            print(f'[SBIREngine] CLIP load failed (Gemini stage2 disabled): {e}')

        # ---- Gemini クライアントを初期化 ----
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            try:
                from google import genai as _genai
                self._gemini_client = _genai.Client(api_key=gemini_key)
                self._enable_gemini = True
                print('[SBIREngine] Gemini client initialized.')
            except Exception as e:
                print(f'[SBIREngine] Gemini init failed: {e}')
        else:
            print('[SBIREngine] GEMINI_API_KEY not set — Stage2 disabled.')

        self._loaded = True
        print(f'[SBIREngine] Ready. gallery={len(gallery_images)} images, device={device}')

    # ------------------------------------------------------------------
    # Gemini ヘルパー
    # ------------------------------------------------------------------

    def _describe_sketch_with_gemini(self, sketch_img) -> tuple[str | None, str | None]:
        """スケッチ画像からカテゴリ名と形状特徴を返す。
        Returns: (category, features)
          category: "T-shirt"  → CLIPハードフィルタ用
          features: "short sleeves, round neckline"  → インスタンスレベルソフトリランク用
        """
        import io
        from google.genai import types as _gtypes

        buf = io.BytesIO()
        sketch_img.save(buf, format='PNG')
        img_bytes = buf.getvalue()

        prompt = (
            'This is a hand-drawn sketch of an object.\n'
            'Provide exactly two lines:\n'
            'CATEGORY: <the object name in 1-2 words, e.g. "T-shirt">\n'
            'FEATURES: <shape and structure details only, no color, 5-8 words, '
            'e.g. "short sleeves, round neckline, rectangular body">\n'
            'Nothing else.'
        )
        try:
            response = self._gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    _gtypes.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                    _gtypes.Part.from_text(text=prompt),
                ],
            )
        except Exception:
            response = self._gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[
                    _gtypes.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                    _gtypes.Part.from_text(text=prompt),
                ],
            )

        category, features = None, None
        for line in response.text.strip().splitlines():
            line = line.strip()
            if line.upper().startswith('CATEGORY:'):
                category = line.split(':', 1)[1].strip().strip('"\'')
            elif line.upper().startswith('FEATURES:'):
                features = line.split(':', 1)[1].strip().strip('"\'')

        print(f'[SBIREngine] Gemini category="{category}" features="{features}"')
        return category, features

    # ------------------------------------------------------------------
    # 検索
    # ------------------------------------------------------------------

    def search(
        self,
        sketch_path: str | Path,
        topk: int = 30,
        scape_weight: float = 0.6,
        dino_weight:  float = 0.2,
        patch_weight: float = 0.2,
    ) -> dict[str, Any]:
        """スケッチをエンコードして検索結果 dict を返す（高速）。"""
        if not self._loaded:
            raise RuntimeError('SBIREngine is not loaded. Call load() first.')

        if _CLIP_DB_SRC not in sys.path:
            sys.path.insert(0, _CLIP_DB_SRC)

        from run_sbir_once_from_db import (
            load_rgb_image, canonical_name_key,
            minmax_normalize, encode_dinov2_both,
            get_active_patch_mask, compute_partial_patch_score,
        )

        sketch_path = Path(sketch_path)
        device      = self._device

        # ---- スケッチをエンコード（ここだけが毎回実行される）----
        sketch_img    = load_rgb_image(sketch_path)
        sketch_tensor = self._sketch_transform(sketch_img).unsqueeze(0).to(device)
        with torch.no_grad():
            sketch_feat = self._sbir_model(sketch_tensor)
            sketch_feat = sketch_feat / sketch_feat.norm(dim=-1, keepdim=True)

        # ---- ギャラリーとのコサイン類似度（行列積） ----
        sims = (sketch_feat @ self._gallery_features.T).squeeze(0).cpu()

        coarse_topk = max(topk, int(os.getenv('SBIR_COARSE_TOPK', '100')))
        actual_k    = min(coarse_topk, len(self._gallery_images))
        coarse_vals, coarse_idxs = torch.topk(sims, k=actual_k)

        final_scores   = coarse_vals.clone()
        dino_scores    = torch.zeros(len(coarse_vals), dtype=torch.float32)
        patch_scores   = torch.zeros(len(coarse_vals), dtype=torch.float32)
        scape_norm     = None
        dino_norm      = None
        patch_norm     = None
        fusion_weights = None
        fusion_applied = False

        # ---- DINOv2 グローバル + パッチ フュージョン ----
        if self._enable_dinov2 and self._dino_model is not None:
            try:
                # 1回のフォワードパスでグローバルとパッチ両方を取得
                sketch_dino_global, sketch_dino_patches = encode_dinov2_both(
                    sketch_img, self._dino_model, device
                )
                active_mask   = get_active_patch_mask(sketch_img)
                active_count  = int(active_mask.sum())
                dino_valid    = 0
                patch_valid   = 0

                for j, cand_i in enumerate(coarse_idxs.tolist()):
                    gallery  = self._gallery_images[cand_i]
                    key      = canonical_name_key(gallery['file_name'])
                    photo    = self._display_by_key.get(key)
                    if photo is None:
                        continue
                    photo_id = int(photo['id'])

                    # グローバル DINOv2 スコア
                    if self._dino_embeddings is not None:
                        idx = self._dino_id_to_index.get(photo_id)
                        if idx is not None:
                            dino_scores[j] = float(np.dot(sketch_dino_global, self._dino_embeddings[idx]))
                            dino_valid += 1

                    # パッチマッチングスコア
                    if self._enable_patch and self._patch_embeddings is not None:
                        pidx = self._patch_id_to_index.get(photo_id)
                        if pidx is not None:
                            patch_scores[j] = compute_partial_patch_score(
                                sketch_dino_patches,
                                self._patch_embeddings[pidx],
                                active_mask,
                            )
                            patch_valid += 1

                use_dino  = dino_valid  > 0
                use_patch = patch_valid > 0
                if use_dino or use_patch:
                    w_dino_eff  = dino_weight  if use_dino  else 0.0
                    w_patch_eff = patch_weight if use_patch else 0.0
                    w_sum = scape_weight + w_dino_eff + w_patch_eff
                    w_scape = scape_weight / w_sum
                    w_dino  = w_dino_eff   / w_sum
                    w_patch = w_patch_eff  / w_sum

                    scape_norm  = minmax_normalize(coarse_vals)
                    dino_norm   = minmax_normalize(dino_scores)
                    patch_norm  = minmax_normalize(patch_scores)

                    final_scores = w_scape * scape_norm + w_dino * dino_norm + w_patch * patch_norm
                    fusion_weights = {
                        'scape':   float(w_scape),
                        'dinov2':  float(w_dino),
                        'patch':   float(w_patch),
                    }
                    fusion_applied = True
                    print(
                        f'[SBIREngine] Fusion: scape={w_scape:.2f} dino={w_dino:.2f} patch={w_patch:.2f} '
                        f'active_patches={active_count}/256'
                    )
            except Exception as e:
                print(f'[SBIREngine] DINOv2/patch fusion failed: {e}')

        # ---- ランキング構築 ----
        sort_order = torch.argsort(final_scores, descending=True)
        selected   = sort_order[:min(topk, len(sort_order))].tolist()

        ranked = []
        for rank, pos in enumerate(selected, start=1):
            i       = int(coarse_idxs[pos].item())
            gallery = self._gallery_images[i]
            key     = canonical_name_key(gallery['file_name'])
            photo   = self._display_by_key.get(key)
            ranked.append({
                'rank':                   rank,
                'gallery_id':             int(gallery['id']),
                'gallery_file':           gallery['file_name'],
                'photo_id':               int(photo['id'])      if photo else None,
                'photo_file':             photo['file_name']    if photo else None,
                'photo_source_path':      photo['source_path']  if photo else None,
                'score':                  float(final_scores[pos].item()),
                'score_sketchscape':      float(coarse_vals[pos].item()),
                'score_clip_text':        None,
                'score_sketchscape_norm': float(scape_norm[pos].item())  if scape_norm  is not None else None,
                'score_clip_text_norm':   None,
                'score_dinov2':           float(dino_scores[pos].item()) if self._enable_dinov2 else None,
                'score_dinov2_norm':      float(dino_norm[pos].item())   if dino_norm   is not None else None,
                'score_patch':            float(patch_scores[pos].item()) if self._enable_patch else None,
                'score_patch_norm':       float(patch_norm[pos].item())  if patch_norm  is not None else None,
            })

        return {
            'sketch_file':           sketch_path.name,
            'device':                device,
            'coarse_topk':           actual_k,
            'dinov2_fusion_enabled': self._enable_dinov2,
            'patch_fusion_enabled':  self._enable_patch,
            'dinov2_fusion_applied': fusion_applied,
            'fusion_weights':        fusion_weights,
            'topk':                  ranked,
        }

    def reload_gallery(self) -> None:
        """DB に画像を追加した後に呼ぶと特徴量を再計算する。"""
        self._loaded = False
        self.load()


# ------------------------------------------------------------------
# グローバルシングルトン
# ------------------------------------------------------------------

_engine: SBIREngine | None = None


def get_engine() -> SBIREngine:
    global _engine
    if _engine is None:
        _engine = SBIREngine()
    return _engine
