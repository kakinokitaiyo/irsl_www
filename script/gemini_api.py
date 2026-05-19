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
ユーザーは、このスケッチの特徴に最も近い現実の物体を探しています。

【重要：人間のスケッチに対する許容（Tolerance）ルール】
人間のスケッチは抽象的であり、幾何学的に極めて不正確（線の途切れ、比率の狂い、歪み、細部の省略など）です。
ピクセルレベルの厳密な一致や、幾何学的な完全性（線が完全に閉じているか等）をロボットのように厳格に判定しないでください。
「ユーザーが何を表現したかったか（Semantic Intent）」を大らかに推測し、微細な形状の差異によって安易に候補を除外しないでください。
少しでも意図が合致する可能性がある候補はすべて残してください。

以下のステップで推論を行い、結果をJSON形式で出力してください。

ステップ1【意図の抽出】
スケッチから読み取れる最も特徴的な要素（全体の大まかなシルエット、特有の構造や付属パーツなど）を抽象化して言語化してください。

ステップ2【候補のフィルタリング】
ステップ1で抽出した特徴を「意味的」に満たしている候補を残してください。スケッチが示す「基本的な物体カテゴリ」や「全体の大まかな構造」と明らかに矛盾する候補のみを除外し、判断に迷うものは必ず残します。

ステップ3【アクション決定】
・フィルタリングの結果、候補が1つに確定できる場合は "action_type": "execute" としてください。
・候補が2つ以上残った場合は "action_type": "ask_user" とし、残った候補同士の「決定的な視覚的差異（色、質感、特定部位の有無、形状の微細な違い）」を分析して、ユーザーにどちらを意図したのか尋ねる「逆質問」を簡潔に生成してください。

出力形式（JSON）:
{
  "extracted_features": "スケッチから読み取れる特徴",
  "candidate_analysis": [
    {
      "id": 1, 
      "status": "keep" または "drop", 
      "reasoning": "許容ルールに基づき、なぜ残す/除外するかの理由"
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
  "action_type": "execute" または "ask_user",
  "selected_id": 1,
  "reasoning": "最終判断の理由",
  "robot_question": "（ask_userの場合）残った候補を特定するためのユーザーへの質問テキスト。executeの場合はnull"
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
    model_id: str = "gemini-2.5-pro"
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
        response = client.models.generate_content(
            model=model_id,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=0.2  # Lower temperature for more deterministic decisions
            )
        )
        
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
        vlm_decision = call_gemini_vlm(client, sketch_path, candidate_paths)
        
        # Validate response structure
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
    return """You are an expert visual understanding assistant helping a robot understand user sketches and make intelligent recommendations.

Your task is to analyze a user's sketch and a set of candidate images (Top 5 from visual search), then make a strategic decision:

1. **Feature Extraction (ステップ1)**: Examine the sketch carefully and identify the key geometric features, components, or visual characteristics that the user emphasized (e.g., protruding parts, handles, specific silhouette shapes, surface textures, color patterns).

2. **Candidate Filtering (ステップ2)**: Review each of the 5 candidate images and determine which ones actually possess the extracted features. Even if an image has a similar overall shape, exclude it if it lacks the key distinguishing features.

3. **Decision Making (ステップ3)**:
   - If exactly ONE candidate remains after filtering: Output that candidate's ID (0-4) and explain why it's the best match.
   - If multiple candidates remain AND you have high confidence in one: Output the most likely candidate.
   - If multiple candidates remain but you CANNOT confidently select one: Generate a clarifying "reverse question" (逆質問) asking the user to distinguish between the candidates by asking about specific visual differences (color, texture, fine details).

CRITICAL REQUIREMENTS:
- Always respond with valid JSON only (no markdown, no additional text).
- Images are labeled: 1=Candidate1, 2=Candidate2, 3=Candidate3, 4=Candidate4, 5=Candidate5
- The sketch is the first image in the set.
- Analyze ALL 6 images carefully (1 sketch + 5 candidates).
- Be conservative: only eliminate candidates that clearly DON'T match the extracted features.
- When uncertain, prefer asking for clarification rather than guessing wrong.

Response format (JSON):
{
  "extracted_features": "Description of key features extracted from the sketch",
  "candidate_analysis": [
        {"id": 1, "has_features": true/false, "reasoning": "Why this candidate does/doesn't match"},
        {"id": 2, "has_features": true/false, "reasoning": "..."},
    ...
  ],
    "remaining_candidates": [1, 3, 5],
  "action_type": "execute" or "ask_user",
  "reasoning": "Why you chose this action",
  "selected_id": 1,
  "robot_question": "Optional: If action_type='ask_user', ask a clarifying question"
}"""


def call_gemini_vlm(
    client: object,
    sketch_path: str,
    candidate_paths: List[str],
    model_id: str = "gemini-2.5-pro"
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
    if len(candidate_paths) != 5:
        raise ValueError(f"Expected 5 candidate images, got {len(candidate_paths)}")
    
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
        response = client.models.generate_content(
            model=model_id,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=0.2  # Lower temperature for more deterministic decisions
            )
        )
        
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
            rospy.logerr("Failed to parse Gemini response as JSON: %s", response_text[:200])
            raise ValueError(f"Invalid JSON from Gemini API: {e}")
    
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")


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
    if client is None:
        client = init_gemini_client(gemini_api_key)
    
    # Extract candidate image paths from SBIR result
    topk_results = sbir_result.get("topk", [])
    if len(topk_results) != 5:
        rospy.logwarn("Expected 5 SBIR candidates, got %d. Skipping VLM processing.", len(topk_results))
        sbir_result["vlm_decision"] = None
        return sbir_result
    
    candidate_paths = []
    for item in topk_results:
        photo_path = item.get("photo_source_path")
        if not photo_path or not os.path.isfile(photo_path):
            rospy.logwarn("Candidate image not found: %s", photo_path)
            sbir_result["vlm_decision"] = None
            return sbir_result
        candidate_paths.append(photo_path)
    
    # Call Gemini VLM
    try:
        vlm_decision = call_gemini_vlm(client, sketch_path, candidate_paths)

        # Normalize ID format to UI style (1-5).
        # If model returns 0-4 (or string), convert to 1-5.
        def _ui_id(v):
            if isinstance(v, int):
                return v + 1 if 0 <= v <= 4 else v
            if isinstance(v, str):
                s = v.strip().lstrip("#")
                if s.isdigit():
                    n = int(s)
                    return n + 1 if 0 <= n <= 4 else n
            return v

        if "selected_id" in vlm_decision:
            vlm_decision["selected_id"] = _ui_id(vlm_decision.get("selected_id"))

        remaining = vlm_decision.get("remaining_candidates")
        if isinstance(remaining, list):
            vlm_decision["remaining_candidates"] = [_ui_id(v) for v in remaining]

        analysis = vlm_decision.get("candidate_analysis")
        kept_ids = []
        if isinstance(analysis, list):
            # UI表示と一致するよう、candidate_analysis の id は常に 1..N の連番に揃える
            for idx, item in enumerate(analysis, start=1):
                if not isinstance(item, dict):
                    continue
                item["id"] = idx

                has_features = item.get("has_features") is True
                status_keep = str(item.get("status", "")).lower() == "keep"
                if has_features or status_keep:
                    kept_ids.append(idx)

        # Ensure consistency between analysis and final decision fields
        action_type = vlm_decision.get("action_type")
        if kept_ids:
            vlm_decision["remaining_candidates"] = kept_ids
            if action_type == "execute":
                vlm_decision["selected_id"] = kept_ids[0]
        elif action_type == "execute" and isinstance(vlm_decision.get("selected_id"), int):
            # keep selected_id as-is when no keep flags were returned
            pass
        
        # Validate response structure
        if "action_type" not in vlm_decision:
            raise ValueError("VLM response missing 'action_type'")
        
        sbir_result["vlm_decision"] = vlm_decision
        rospy.loginfo("VLM decision: action_type=%s", vlm_decision.get("action_type"))
        
        return sbir_result
    
    except Exception as e:
        rospy.logerr("VLM processing failed: %s", str(e))
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
    
    # Initialize ROS for logging
    try:
        rospy.init_node("gemini_api_test")
    except:
        pass
    
    # Load candidates
    candidate_dir = Path(args.candidate_dir)
    candidates = sorted(candidate_dir.glob("*.png"))[:5]
    
    if len(candidates) < 5:
        print(f"ERROR: Expected 5 candidate images, found {len(candidates)}")
        sys.exit(1)
    
    # Call VLM
    client = init_gemini_client(args.api_key)
    result = call_gemini_vlm(client, args.sketch, [str(c) for c in candidates])
    
    print(json.dumps(result, indent=2, ensure_ascii=False))