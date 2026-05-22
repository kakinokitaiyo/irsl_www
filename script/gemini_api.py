#!/usr/bin/env python3
"""
Gemini API integration for VLM-based reverse questioning.
Processes SBIR Top 5 results with sketch to make intelligent candidate filtering decisions.

Requirements:
    pip install google-genai
"""

import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Conditional imports for graceful degradation
try:
    import rospy
except ImportError:
    rospy = None

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_AVAILABLE = False


def init_gemini_client(api_key: Optional[str] = None) -> Optional[object]:
    """Initialize Gemini API client with API key from environment or parameter."""
    if not GEMINI_AVAILABLE:
        raise ImportError("google-genai package not installed. Install with: pip install google-genai")
    
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not set. Please set it in environment variables "
            "or pass it to this function."
        )
    
    return genai.Client(api_key=api_key)


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    return base64.b64encode(image_bytes).decode('utf-8')


def get_image_mime_type(image_path: str) -> str:
    """Determine MIME type from file extension."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    return mime_types.get(ext, 'image/png')


def build_vlm_prompt() -> str:
    """Build the system prompt for VLM reverse questioning."""
    return """あなたは自律移動ロボットの視覚・推論エンジンです。
ユーザーが描いた「ラフスケッチ」と、検索システムが抽出した「候補画像（1〜5）」が与えられます。
ユーザーは、このスケッチと最も合致する現実の物体を特定する必要があります。

【重要：人間のスケッチに対する許容（Tolerance）ルール】
人間のスケッチは抽象的であり、幾何学的に極めて不正確（線の途切れ、比率の狂い、歪み、細部の省略など）です。
ピクセルレベルの厳密な一致や、幾何学的な完全性をロボットのように厳格に判定しないでください。
「ユーザーが何を表現したかったか（Semantic Intent）」を大らかに推測し、微細な形状の差異によって安易に候補を除外しないでください。

特徴量の抽象的な分析：
・基本的なシルエット（輪郭、全体的なプロポーション）
・構造的な組成（複数の主要な部分要素とその相対的配置）
・トポロジー的な特性（穴、凹凸、連結性など）
・表面の特性（質感、反射性、パターン）
・スケール感（相対的なサイズ関係）

候補の判定では、スケッチのこれらの特徴がどの程度合致しているかを評価してください。
スケッチが曖昧な場合や特定の特徴が不明な場合は、複数の可能性を残してください。

以下のステップで推論を行い、結果をJSON形式で出力してください。

ステップ1【特徴量の抽出】
スケッチから抽出可能な「カテゴリに依存しない抽象的な特徴」を列挙してください：
- 基本的なシルエット形状
- 識別可能な主要な構造要素とその配置
- スケッチに明確に表現されている視覚的な特性

ステップ2【候補のフィルタリングの絶対ルール】
ステップ1で抽出した特徴をもとに候補を評価しますが、以下のルールを厳守してください。
1. 除外（drop）が許されるのは、スケッチに描かれた「主要な構成要素（大きな突起、穴、大まかなシルエット）」が完全に欠落している場合のみです。
2. 【禁止事項】構成要素が共通している候補同士（例：両方に側面の突起がある等）を比較し、その「形状の詳細（閉じているか開いているか）」「接合位置（上からか、下からか）」「太さや角度」の違いを理由に除外することは【絶対に禁止】します。
3. ユーザーのスケッチにおける「パーツの詳細な形状」や「接合部」は最も不正確です。主要な構成要素を持つ候補は、デザインが異なって見えても全て「keep」にしてください。

ステップ3【アクション決定の強制と動的質問生成】
・候補が「1つだけ」になった場合のみ "action_type": "execute" としてください。
・「keep」が2つ以上ある場合は必ず "action_type": "ask_user" を選択してください。
・「keep」が0の場合は、Top5に正解がない可能性が高いため "action_type": "resketch" を選択してください。
・質問モードは以下に従ってください。
    - 残り候補が2つ: "question_mode": "yes_no"（YES/NOで答えられる質問を作る）
    - 残り候補が3つ以上: "question_mode": "multi_choice"（候補選択型。YES/NO質問は不可）

出力形式（JSON）:
{
  "extracted_features": "スケッチから抽出した特徴量（カテゴリに依存しない）",
  "candidate_analysis": [
    {
      "id": 1, 
      "status": "keep" または "drop", 
      "reasoning": "特徴量との合致度に基づき、なぜ残す/除外するかの理由"
    },
    {
      "id": 2, 
      "status": "keep" または "drop", 
      "reasoning": "..."
    },
    {
      "id": 3, 
      "status": "keep" または "drop", 
      "reasoning": "..."
    },
    {
      "id": 4, 
      "status": "keep" または "drop", 
      "reasoning": "..."
    },
    {
      "id": 5, 
      "status": "keep" または "drop", 
      "reasoning": "..."
    }
  ],
  "remaining_candidates": [残った候補のID],
    "action_type": "execute" または "ask_user" または "resketch",
    "question_mode": null または "yes_no" または "multi_choice",
    "binary_mapping": null または {"yes_candidate_id": 1, "no_candidate_id": 3},
    "selected_id": null または 1,
  "reasoning": "最終判断の理由（特徴量の観点から）",
    "robot_question": "ask_userの場合の質問。execute/resketchならnull可",
    "user_options": ["yes", "no", "neither", "resketch"]
}

重要：常に有効なJSONのみを返し、マークダウンやテキストは一切含めないでください。"""


def _log_info(msg: str):
    """Log info message (via rospy if available)."""
    if rospy:
        rospy.loginfo(msg)
    else:
        print(f"[INFO] {msg}")


def _log_warn(msg: str):
    """Log warning message (via rospy if available)."""
    if rospy:
        rospy.logwarn(msg)
    else:
        print(f"[WARN] {msg}")


def _log_error(msg: str):
    """Log error message (via rospy if available)."""
    if rospy:
        rospy.logerr(msg)
    else:
        print(f"[ERROR] {msg}")


def call_gemini_vlm(
    client: object,
    sketch_path: str,
    candidate_paths: List[str],
    model_id: str = "gemini-robotics-er-1.6-preview"
) -> Dict:
    """
    Call Gemini API with sketch and candidate images.
    
    Args:
        client: Initialized Gemini client
        sketch_path: Path to the query sketch image
        candidate_paths: List of 5 candidate image paths
        model_id: Gemini model to use
    
    Returns:
        Parsed JSON response from VLM
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("google-genai package not installed. Install with: pip install google-genai")
    
    if len(candidate_paths) != 5:
        raise ValueError(f"Expected 5 candidate images, got {len(candidate_paths)}")
    
    default_model = "gemini-robotics-er-1.6-preview"
    requested_model = os.getenv("GEMINI_MODEL", model_id).strip()
    if not requested_model:
        requested_model = default_model

    candidate_models = [requested_model]
    if requested_model != default_model:
        candidate_models.append(default_model)

    # Build the image parts: [sketch, candidate1, candidate2, candidate3, candidate4, candidate5]
    parts = [build_vlm_prompt()]
    
    # Add sketch image
    try:
        sketch_mime = get_image_mime_type(sketch_path)
        sketch_data = encode_image_to_base64(sketch_path)
        parts.append(
            types.Part.from_bytes(
                data=base64.b64decode(sketch_data),
                mime_type=sketch_mime,
            )
        )
    except Exception as e:
        raise RuntimeError(f"Failed to process sketch image: {e}")
    
    # Add candidate images
    for i, cand_path in enumerate(candidate_paths):
        try:
            cand_mime = get_image_mime_type(cand_path)
            cand_data = encode_image_to_base64(cand_path)
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(cand_data),
                    mime_type=cand_mime,
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process candidate {i}: {e}")
    
    # Call Gemini API
    try:
        response = None
        last_error = None
        for idx, mid in enumerate(candidate_models):
            try:
                response = client.models.generate_content(
                    model=mid,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        temperature=0.2  # Lower temperature for more deterministic decisions
                    )
                )
                if mid != requested_model:
                    _log_warn(f"Fallback model applied: {mid}")
                break
            except Exception as inner_e:
                last_error = inner_e
                msg = str(inner_e).lower()
                retryable_model_error = (
                    "unexpected model name format" in msg
                    or "model not found" in msg
                    or "invalid_argument" in msg
                )
                if idx < len(candidate_models) - 1 and retryable_model_error:
                    _log_warn(f"Model '{mid}' failed ({inner_e}). Retrying with fallback model.")
                    continue
                raise

        if response is None and last_error is not None:
            raise last_error
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present (```json ... ```)
        if response_text.startswith("```"):
            parts_split = response_text.split("```")
            if len(parts_split) >= 3:
                response_text = parts_split[1]
                # Remove 'json' language identifier if present
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            _log_error(f"Failed to parse Gemini response as JSON: {response_text[:200]}")
            raise ValueError(f"Invalid JSON from Gemini API: {e}")
    
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")


def _ui_id(v):
    """Convert 0-based IDs to 1-based IDs used by UI and keep existing 1-based IDs."""
    if isinstance(v, int):
        return v + 1 if 0 <= v <= 4 else v
    if isinstance(v, str):
        s = v.strip().lstrip("#")
        if s.isdigit():
            n = int(s)
            return n + 1 if 0 <= n <= 4 else n
    return v


def _normalize_vlm_decision(vlm_decision: Dict) -> Dict:
    """Normalize VLM output to support yes/no, multi-choice, and re-sketch flow."""
    if not isinstance(vlm_decision, dict):
        return {
            "action_type": "resketch",
            "question_mode": None,
            "remaining_candidates": [],
            "selected_id": None,
            "robot_question": "結果を解釈できませんでした。もう一度スケッチを描いてください。",
            "user_options": ["resketch"],
            "decision_schema_version": "2.0",
        }

    # Normalize basic fields
    action_type = str(vlm_decision.get("action_type", "")).strip().lower()
    if action_type in ("ask", "askuser", "ask-user"):
        action_type = "ask_user"
    if action_type not in ("execute", "ask_user", "resketch"):
        action_type = "ask_user"
    vlm_decision["action_type"] = action_type

    if "selected_id" in vlm_decision:
        vlm_decision["selected_id"] = _ui_id(vlm_decision.get("selected_id"))

    remaining = vlm_decision.get("remaining_candidates")
    if isinstance(remaining, list):
        vlm_decision["remaining_candidates"] = [
            _ui_id(v) for v in remaining if isinstance(_ui_id(v), int)
        ]
    else:
        vlm_decision["remaining_candidates"] = []

    # Rebuild from candidate_analysis if available
    analysis = vlm_decision.get("candidate_analysis")
    kept_ids = []
    if isinstance(analysis, list):
        for idx, item in enumerate(analysis, start=1):
            if not isinstance(item, dict):
                continue
            item["id"] = idx
            has_features = item.get("has_features") is True
            status_keep = str(item.get("status", "")).strip().lower() == "keep"
            if has_features or status_keep:
                kept_ids.append(idx)
    if kept_ids:
        vlm_decision["remaining_candidates"] = kept_ids

    remaining_ids = vlm_decision.get("remaining_candidates", [])

    # Force coherent action
    if len(remaining_ids) == 0:
        vlm_decision["action_type"] = "resketch"
        vlm_decision["selected_id"] = None
    elif len(remaining_ids) == 1:
        vlm_decision["action_type"] = "execute"
        vlm_decision["selected_id"] = remaining_ids[0]
    elif vlm_decision["action_type"] == "execute":
        # Ambiguous case: prevent auto decision
        vlm_decision["action_type"] = "ask_user"
        vlm_decision["selected_id"] = None

    # Build interaction mode
    if vlm_decision["action_type"] == "ask_user":
        if len(remaining_ids) == 2:
            vlm_decision["question_mode"] = "yes_no"
            if not isinstance(vlm_decision.get("binary_mapping"), dict):
                vlm_decision["binary_mapping"] = {
                    "yes_candidate_id": remaining_ids[0],
                    "no_candidate_id": remaining_ids[1],
                }
            if not vlm_decision.get("robot_question"):
                vlm_decision["robot_question"] = (
                    f"候補#{remaining_ids[0]}に近いですか？（YES/NOで回答してください）"
                )
            vlm_decision["user_options"] = ["yes", "no", "neither", "resketch"]
            vlm_decision["selected_id"] = None
        else:
            # 3つ以上残る場合は yes/no では選べないため multi_choice
            vlm_decision["question_mode"] = "multi_choice"
            vlm_decision["binary_mapping"] = None
            vlm_decision["choice_candidates"] = remaining_ids
            if not vlm_decision.get("robot_question"):
                vlm_decision["robot_question"] = "似た候補が複数あります。最も近い候補を選ぶか、どちらでもないを選択してください。"
            vlm_decision["user_options"] = ["select_candidate", "neither", "resketch"]
            vlm_decision["selected_id"] = None

    elif vlm_decision["action_type"] == "resketch":
        vlm_decision["question_mode"] = None
        vlm_decision["binary_mapping"] = None
        vlm_decision["selected_id"] = None
        if not vlm_decision.get("robot_question"):
            vlm_decision["robot_question"] = "Top5内に該当候補が無い可能性があります。もう一度スケッチを描いてください。"
        vlm_decision["user_options"] = ["resketch"]

    else:  # execute
        vlm_decision["question_mode"] = None
        vlm_decision["binary_mapping"] = None
        vlm_decision["robot_question"] = None
        vlm_decision["user_options"] = []

    vlm_decision.setdefault("decision_schema_version", "2.0")
    return vlm_decision


def process_sbir_with_vlm(
    sbir_result: Dict,
    sketch_path: str,
    client: Optional[object] = None,
    gemini_api_key: Optional[str] = None
) -> Dict:
    """
    Post-process SBIR results with VLM reverse questioning.
    
    Args:
        sbir_result: SBIR output dict with 'topk' array containing top 5 results
        sketch_path: Path to query sketch image
        client: Optional pre-initialized Gemini client
        gemini_api_key: Optional API key (used if client is None)
    
    Returns:
        Enhanced SBIR result dict with VLM decision added
    """
    if not GEMINI_AVAILABLE:
        _log_warn("google-genai not installed, skipping VLM processing")
        sbir_result["vlm_decision"] = None
        return sbir_result
    
    if client is None:
        client = init_gemini_client(gemini_api_key)
    
    # Extract candidate image paths from SBIR result
    topk_results = sbir_result.get("topk", [])
    if len(topk_results) != 5:
        _log_warn(f"Expected 5 SBIR candidates, got {len(topk_results)}. Skipping VLM processing.")
        sbir_result["vlm_decision"] = None
        return sbir_result
    
    candidate_paths = []
    for item in topk_results:
        photo_path = item.get("photo_source_path")
        if not photo_path or not os.path.isfile(photo_path):
            _log_warn(f"Candidate image not found: {photo_path}")
            sbir_result["vlm_decision"] = None
            return sbir_result
        candidate_paths.append(photo_path)
    
    # Call Gemini VLM
    try:
        raw_decision = call_gemini_vlm(client, sketch_path, candidate_paths)
        vlm_decision = _normalize_vlm_decision(raw_decision)

        if "action_type" not in vlm_decision:
            raise ValueError("VLM response missing 'action_type'")
        
        sbir_result["vlm_decision"] = vlm_decision
        _log_info(f"VLM decision: action_type={vlm_decision.get('action_type')}")
        
        return sbir_result
    
    except Exception as e:
        _log_error(f"VLM processing failed: {str(e)}")
        sbir_result["vlm_decision"] = None
        sbir_result["vlm_error"] = str(e)
        return sbir_result


if __name__ == "__main__":
    # Test the module if run directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Gemini VLM integration")
    parser.add_argument("--sketch", required=True, help="Path to sketch image")
    parser.add_argument("--candidate_dir", required=True, help="Directory containing 5 candidate images")
    parser.add_argument("--api_key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Load candidates
    candidate_dir = Path(args.candidate_dir)
    candidates = sorted(candidate_dir.glob("*.png"))[:5]
    
    if len(candidates) < 5:
        print(f"ERROR: Expected 5 candidate images, found {len(candidates)}")
        sys.exit(1)
    
    try:
        # Call VLM
        client = init_gemini_client(args.api_key)
        result = call_gemini_vlm(client, args.sketch, [str(c) for c in candidates])
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)