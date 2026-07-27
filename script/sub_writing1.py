#!/usr/bin/env python3

import csv
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime

# sbir_engine.py が同じディレクトリにあるため、スクリプトディレクトリを先頭に追加
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import rospy
from std_msgs.msg import String
from base64 import b64decode

try:
    from gemini_api import (
        init_gemini_client,
        generate_dialogue_question,
        extract_search_query_from_sketch,
    )
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False
    rospy.logwarn("VLM module not available. Dialogue will fall back to multi-choice.")

result_pub = None

# SBIR は最初の1回のみ実行。全候補をここに保存して対話で絞り込む。
# { sketch_file: { sketch_path, sketch_web_path, all_candidates,
#                  remaining_candidates, current_question, question_history } }
dialogue_state_by_sketch = {}

latest_result_by_sketch = {}
clip_query_by_sketch = {}

# 初回 SBIR で取得する候補数（対話の絞り込み対象）
DIALOGUE_INITIAL_TOPK = int(os.getenv("SBIR_DIALOGUE_TOPK", "30"))
# 1ターンで VLM に渡す候補の最大枚数（全残り候補をこの枚数以内で一括分類）
DIALOGUE_VLM_MAX_CANDIDATES = int(os.getenv("SBIR_VLM_MAX_CANDIDATES", "20"))

# ---------------------------------------------------------------------------
# 実験ログ
# ---------------------------------------------------------------------------

_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'experiment_log.csv')
_LOG_FIELDS = [
    'timestamp', 'sketch_file',
    'sbir_top1_file', 'sbir_top1_score', 'sbir_top1_sketchscape',
    'dialogue_turns', 'outcome', 'confirmed_file', 'confirmed_rank',
    'target_object', 'quality_level', 'score_formula',
]


def _log_experiment(row: dict) -> None:
    exists = os.path.isfile(_LOG_PATH)
    with open(_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, '') for k in _LOG_FIELDS})


# ---------------------------------------------------------------------------
# Web 用ファイルコピー
# ---------------------------------------------------------------------------

def _web_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'html', 'touch'))


def _copy_sketch_for_web(sketch_path: str) -> str | None:
    sketch_web_dir = os.path.join(_web_root(), 'sbir_sketches')
    os.makedirs(sketch_web_dir, exist_ok=True)
    try:
        base = os.path.basename(sketch_path)
        shutil.copy2(sketch_path, os.path.join(sketch_web_dir, base))
        return f"/touch/sbir_sketches/{base}"
    except Exception as e:
        rospy.logwarn("Failed to copy sketch for web: %s", e)
        return None


def _copy_candidates_for_web(candidates: list) -> list:
    photo_web_dir = os.path.join(_web_root(), 'sbir_photos')
    os.makedirs(photo_web_dir, exist_ok=True)
    for item in candidates:
        src = item.get("photo_source_path")
        rank = item.get("rank", 0)
        if not src or not os.path.isfile(src):
            continue
        base = os.path.basename(src)
        dst_name = f"r{rank}_{base}"
        try:
            shutil.copy2(src, os.path.join(photo_web_dir, dst_name))
            item["photo_web_path"] = f"/touch/sbir_photos/{dst_name}"
        except Exception as e:
            rospy.logwarn("Failed to copy photo (%s): %s", src, e)
    return candidates


# ---------------------------------------------------------------------------
# JSON パース
# ---------------------------------------------------------------------------

def parse_json_from_mixed_output(output: str) -> dict:
    text = (output or "").strip()
    if not text:
        raise ValueError("SBIR output is empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in SBIR output: {text[:300]}")


# ---------------------------------------------------------------------------
# SBIR 実行（エンジン常駐型）
# ---------------------------------------------------------------------------

try:
    from sbir_engine import get_engine
    _USE_ENGINE = True
except ImportError:
    _USE_ENGINE = False
    rospy.logwarn("sbir_engine not available. Falling back to subprocess.")


def run_sbir_once(sketch_path: str, topk: int | None = None) -> dict:
    """スケッチを検索して結果 dict を返す。エンジン常駐型（高速）。"""
    actual_topk = topk if topk is not None else int(os.getenv("SBIR_TOPK", str(DIALOGUE_INITIAL_TOPK)))
    scape_weight = float(os.getenv("SBIR_SCAPE_WEIGHT", "0.7"))
    dino_weight  = float(os.getenv("SBIR_DINO_WEIGHT",  "0.3"))

    if _USE_ENGINE:
        engine = get_engine()
        if not engine._loaded:
            raise RuntimeError("SBIREngine is not loaded yet.")
        return engine.search(sketch_path, topk=actual_topk,
                             scape_weight=scape_weight, dino_weight=dino_weight)

    # フォールバック: サブプロセス（エンジン未使用時）
    clip_db_root = os.getenv("CLIP_DB_ROOT", "/home/irsl/workspace/CLIP_DB")
    sbir_script  = os.path.join(clip_db_root, "src", "run_sbir_once_from_db.py")
    cmd = [
        sys.executable, sbir_script,
        "--sketch_path", sketch_path,
        "--topk", str(actual_topk),
        "--host",     os.getenv("PGHOST",     "133.15.97.94"),
        "--port",     os.getenv("PGPORT",     "5432"),
        "--dbname",   os.getenv("PGDATABASE", "kakinoki_db"),
        "--user",     os.getenv("PGUSER",     "kakinoki_taiyo"),
        "--password", os.getenv("PGPASSWORD", "irsl"),
        "--schema",   os.getenv("SBIR_SCHEMA", "home_robot"),
        "--gallery_table",       os.getenv("SBIR_GALLERY_TABLE",       "photos_edge"),
        "--display_table",       os.getenv("SBIR_DISPLAY_TABLE",       "photos"),
        "--gallery_source_type", os.getenv("SBIR_GALLERY_SOURCE_TYPE", "photo_edge"),
        "--display_source_type", os.getenv("SBIR_DISPLAY_SOURCE_TYPE", "photo"),
        "--device",           os.getenv("SBIR_DEVICE", "auto"),
        "--sketchscape_root", os.getenv("SKETCHSCAPE_ROOT", "/home/irsl/workspace/SketchScape"),
        "--model_path",       os.getenv("SBIR_MODEL_PATH",
                                        "/home/irsl/workspace/SketchScape/models/fscoco_normal.pth"),
        "--coarse_topk",      os.getenv("SBIR_COARSE_TOPK", "100"),
        "--enable_dinov2_fusion",
        "--scape_weight",  str(scape_weight),
        "--dinov2_weight", str(dino_weight),
    ]
    dinov2_npz = os.getenv("DINO_IMAGE_EMBEDDINGS_PATH", "")
    if dinov2_npz:
        cmd.extend(["--dinov2_embeddings_path", dinov2_npz])
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return parse_json_from_mixed_output(completed.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"SBIR subprocess failed (exit={e.returncode}) stderr={e.stderr or ''}"
        ) from e


# ---------------------------------------------------------------------------
# publish ヘルパー
# ---------------------------------------------------------------------------

def _save_and_publish(sketch_file: str, payload: dict) -> None:
    state = dialogue_state_by_sketch.get(sketch_file, {})
    if "score_formula" in state:
        payload["_score_formula"] = state["score_formula"]

    latest_result_by_sketch[sketch_file] = payload

    result_dir = os.path.join(os.path.dirname(__file__), '..', 'sketch_result')
    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(result_dir, os.path.splitext(sketch_file)[0] + '_top5.json')
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if result_pub is not None:
        result_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))

    rospy.loginfo("Published: action=%s remaining=%s for %s",
                  payload.get("action_type"), payload.get("remaining_count"), sketch_file)


def _publish_confirmed(sketch_file: str, candidate: dict) -> None:
    state = dialogue_state_by_sketch.get(sketch_file, {})

    # 確定物を先頭にした Top-5 を構成（touch.html は topk[0] を確定物として扱う）
    all_top5 = state.get("all_candidates", [])[:5]
    _copy_candidates_for_web(all_top5)
    confirmed_id = candidate.get("photo_id")
    for item in all_top5:
        item["confirmed"] = (item.get("photo_id") == confirmed_id)
    confirmed_items = [c for c in all_top5 if c.get("photo_id") == confirmed_id]
    other_items     = [c for c in all_top5 if c.get("photo_id") != confirmed_id]
    topk_ordered    = confirmed_items + other_items if confirmed_items else [candidate] + other_items

    dialogue_turns = len(state.get("question_history", []))
    payload = {
        "sketch_file": sketch_file,
        "action_type": "execute",
        "selected_id": candidate.get("photo_id"),
        "selected_file": candidate.get("photo_file"),
        "selected_path": candidate.get("photo_source_path"),
        "photo_web_path": topk_ordered[0].get("photo_web_path") if topk_ordered else None,
        "question_history": state.get("question_history", []),
        "topk": topk_ordered,
        "sketch_web_path": state.get("sketch_web_path"),
    }
    _save_and_publish(sketch_file, payload)
    rospy.loginfo("Confirmed: %s for %s", candidate.get("photo_file"), sketch_file)

    _log_experiment({
        "timestamp":              datetime.now().isoformat(timespec='seconds'),
        "sketch_file":            sketch_file,
        "sbir_top1_file":         state.get("sbir_top1_file", ""),
        "sbir_top1_score":        state.get("sbir_top1_score", ""),
        "sbir_top1_sketchscape":  state.get("sbir_top1_sketchscape", ""),
        "dialogue_turns":         dialogue_turns,
        "outcome":                "confirmed",
        "confirmed_file":         candidate.get("photo_file", ""),
        "confirmed_rank":         candidate.get("rank", ""),
        "target_object":          os.getenv("EXPERIMENT_TARGET", ""),
        "quality_level":          os.getenv("EXPERIMENT_QUALITY", ""),
        "score_formula":          state.get("score_formula", ""),
    })


def _publish_resketch_request(sketch_file: str) -> None:
    state = dialogue_state_by_sketch.get(sketch_file, {})
    dialogue_turns = len(state.get("question_history", []))
    payload = {
        "sketch_file": sketch_file,
        "action_type": "resketch",
        "robot_question": "候補が見つかりませんでした。もう一度スケッチを描いてください。",
        "question_history": state.get("question_history", []),
        "remaining_count": 0,
        "sketch_web_path": state.get("sketch_web_path"),
    }
    _save_and_publish(sketch_file, payload)

    _log_experiment({
        "timestamp":              datetime.now().isoformat(timespec='seconds'),
        "sketch_file":            sketch_file,
        "sbir_top1_file":         state.get("sbir_top1_file", ""),
        "sbir_top1_score":        state.get("sbir_top1_score", ""),
        "sbir_top1_sketchscape":  state.get("sbir_top1_sketchscape", ""),
        "dialogue_turns":         dialogue_turns,
        "outcome":                "resketch",
        "confirmed_file":         "",
        "target_object":          os.getenv("EXPERIMENT_TARGET", ""),
        "quality_level":          os.getenv("EXPERIMENT_QUALITY", ""),
        "score_formula":          state.get("score_formula", ""),
    })


# ---------------------------------------------------------------------------
# リアルタイム（インクリメンタル）検索
# ---------------------------------------------------------------------------

_PARTIAL_SKETCH_FILE = "writing_partial.png"
_partial_lock        = threading.Lock()
_partial_running     = False


def _run_partial_sbir(partial_path: str) -> None:
    global _partial_running
    try:
        sbir_result = run_sbir_once(partial_path, topk=5)
        candidates  = sbir_result.get("topk", [])
        _copy_candidates_for_web(candidates)
        sketch_web   = _copy_sketch_for_web(partial_path)

        # "choose:N" で即確定できるよう対話状態を保持
        dialogue_state_by_sketch[_PARTIAL_SKETCH_FILE] = {
            "sketch_path":          partial_path,
            "sketch_web_path":      sketch_web,
            "all_candidates":       candidates,
            "remaining_candidates": list(candidates),
            "current_question":     None,
            "question_history":     [],
            "score_formula":        "",
        }

        payload = {
            "action_type":     "realtime_update",
            "sketch_file":     _PARTIAL_SKETCH_FILE,
            "topk":            candidates,
            "sketch_web_path": sketch_web,
        }
        if result_pub is not None:
            result_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))
        rospy.loginfo("Partial SBIR: top1=%s",
                      candidates[0].get("gallery_file", "?") if candidates else "none")
    except Exception as e:
        rospy.logwarn("Partial SBIR failed: %s", e)
    finally:
        with _partial_lock:
            _partial_running = False


def partial_callback(msg: String) -> None:
    global _partial_running

    data = msg.data
    _, encoded = data.split('base64,', 1)
    decoded    = b64decode(encoded)

    sketch_dir   = os.path.join(os.path.dirname(__file__), '..', 'sketch')
    os.makedirs(sketch_dir, exist_ok=True)
    partial_path = os.path.join(sketch_dir, _PARTIAL_SKETCH_FILE)
    with open(partial_path, 'wb') as f:
        f.write(decoded)

    with _partial_lock:
        if _partial_running:
            return  # 前の推論実行中はスキップ（最新ファイルは上書き済み）
        _partial_running = True

    threading.Thread(target=_run_partial_sbir, args=(partial_path,), daemon=True).start()


# ---------------------------------------------------------------------------
# 対話ターン（メインループ）
# ---------------------------------------------------------------------------

def run_dialogue_turn(sketch_file: str) -> None:
    """残り候補を全件 VLM に渡して質問を生成・全候補を一括分類し publish する。"""
    state = dialogue_state_by_sketch.get(sketch_file)
    if not state:
        rospy.logwarn("run_dialogue_turn: no state for %s", sketch_file)
        return

    remaining = state["remaining_candidates"]
    sketch_path = state["sketch_path"]
    question_history = state.get("question_history", [])

    # UI 表示用は上位5件、VLM 分類対象は全残り候補（上限 DIALOGUE_VLM_MAX_CANDIDATES）
    show_candidates = remaining[:5]
    classify_candidates = remaining[:DIALOGUE_VLM_MAX_CANDIDATES]

    _copy_candidates_for_web(show_candidates)

    if not VLM_AVAILABLE or os.getenv("ENABLE_VLM", "true").lower() != "true":
        _publish_multi_choice(sketch_file, show_candidates, remaining)
        return

    candidate_paths = [c["photo_source_path"] for c in classify_candidates]
    missing = [p for p in candidate_paths if not os.path.isfile(p)]
    if missing:
        rospy.logwarn("Missing candidate images: %s", missing)

    try:
        vlm_client = init_gemini_client(os.getenv("GEMINI_API_KEY"))
        vlm_result = generate_dialogue_question(
            vlm_client,
            sketch_path,
            candidate_paths,
            question_history=question_history,
        )

        # 1-based ID → photo_id へのマッピング（classify_candidates 全体が対象）
        yes_photo_ids = [
            classify_candidates[i - 1]["photo_id"]
            for i in vlm_result.get("yes_ids", [])
            if 1 <= i <= len(classify_candidates)
        ]
        no_photo_ids = [
            classify_candidates[i - 1]["photo_id"]
            for i in vlm_result.get("no_ids", [])
            if 1 <= i <= len(classify_candidates)
        ]

        # DIALOGUE_VLM_MAX_CANDIDATES を超えた候補は未分類のまま残す
        classified_ids = set(yes_photo_ids) | set(no_photo_ids)
        unclassified_count = sum(
            1 for c in remaining[DIALOGUE_VLM_MAX_CANDIDATES:]
            if c["photo_id"] not in classified_ids
        )
        if unclassified_count:
            rospy.loginfo("Unclassified (beyond VLM limit): %d candidates", unclassified_count)

        state["current_question"] = {
            "question": vlm_result["question"],
            "yes_photo_ids": yes_photo_ids,
            "no_photo_ids": no_photo_ids,
        }

        payload = {
            "sketch_file": sketch_file,
            "action_type": "ask_user",
            "question_mode": "yes_no",
            "robot_question": vlm_result["question"],
            "user_options": ["yes", "no", "resketch"],
            "remaining_count": len(remaining),
            "classified_count": len(classify_candidates),
            "topk": show_candidates,
            "sketch_web_path": state.get("sketch_web_path"),
            "question_history": question_history,
        }
        state["last_ask_payload"] = payload  # 「戻る」用に保存
        _save_and_publish(sketch_file, payload)
        rospy.loginfo(
            "Dialogue Q: %s  yes=%d no=%d classified=%d remaining=%d",
            vlm_result["question"], len(yes_photo_ids), len(no_photo_ids),
            len(classify_candidates), len(remaining),
        )

    except Exception as e:
        rospy.logerr("run_dialogue_turn VLM failed for %s: %s", sketch_file, e)
        _publish_multi_choice(sketch_file, show_candidates, remaining, vlm_error=str(e))


def _publish_multi_choice(sketch_file: str, show_candidates: list,
                           remaining: list, vlm_error: str | None = None) -> None:
    """VLMが使えない場合のフォールバック: ユーザーに候補を直接選ばせる。"""
    state = dialogue_state_by_sketch.get(sketch_file, {})
    payload = {
        "sketch_file": sketch_file,
        "action_type": "ask_user",
        "question_mode": "multi_choice",
        "robot_question": "最も近い候補を選んでください。",
        "user_options": ["select_candidate", "resketch"],
        "remaining_count": len(remaining),
        "topk": show_candidates,
        "sketch_web_path": state.get("sketch_web_path"),
        "question_history": state.get("question_history", []),
    }
    if vlm_error:
        payload["vlm_error"] = vlm_error
    state["last_ask_payload"] = payload  # 「戻る」用に保存
    _save_and_publish(sketch_file, payload)


# ---------------------------------------------------------------------------
# 初回 SBIR 実行 & 対話状態の初期化
# ---------------------------------------------------------------------------

def process_and_publish_sbir(sketch_path: str) -> None:
    sketch_file = os.path.basename(sketch_path)

    # CLIP fusion 用クエリ抽出（有効時のみ）
    clip_text_query = None
    if os.getenv("ENABLE_CLIP_FUSION", "false").lower() == "true" and VLM_AVAILABLE:
        try:
            vlm_client = init_gemini_client(os.getenv("GEMINI_API_KEY"))
            clip_text_query = extract_search_query_from_sketch(sketch_path, client=vlm_client)
            if clip_text_query:
                clip_query_by_sketch[sketch_file] = clip_text_query
                rospy.loginfo("CLIP query: %s", clip_text_query)
        except Exception as e:
            rospy.logwarn("CLIP query extraction failed: %s", e)

    # SBIR を1回だけ実行（topk=DIALOGUE_INITIAL_TOPK）
    sbir_result = run_sbir_once(sketch_path, topk=DIALOGUE_INITIAL_TOPK)

    all_candidates = sbir_result.get("topk", [])
    rospy.loginfo("SBIR: %d candidates retrieved for %s", len(all_candidates), sketch_file)

    sketch_web_path = _copy_sketch_for_web(sketch_path)

    top1 = all_candidates[0] if all_candidates else {}
    fusion_weights = sbir_result.get("fusion_weights") or {}
    w_scape = fusion_weights.get("scape", 0.7)
    w_dino  = fusion_weights.get("dinov2", 0.3)
    score_formula = (
        f"score = {w_scape} * score_sketchscape_norm"
        f" + {w_dino} * score_dinov2_norm"
    )

    # 対話状態を初期化
    dialogue_state_by_sketch[sketch_file] = {
        "sketch_path":        sketch_path,
        "sketch_web_path":    sketch_web_path,
        "all_candidates":     all_candidates,
        "remaining_candidates": list(all_candidates),
        "current_question":   None,
        "question_history":   [],
        "sbir_top1_file":        top1.get("gallery_file", ""),
        "sbir_top1_score":       top1.get("score", ""),
        "sbir_top1_sketchscape": top1.get("score_sketchscape", ""),
        "score_formula":         score_formula,
    }

    if len(all_candidates) == 0:
        _publish_resketch_request(sketch_file)
        return
    if len(all_candidates) == 1:
        _publish_confirmed(sketch_file, all_candidates[0])
        return

    # 最初の対話ターン開始
    run_dialogue_turn(sketch_file)


# ---------------------------------------------------------------------------
# フィードバック受信（対話ループの核）
# ---------------------------------------------------------------------------

def feedback_callback(msg):
    try:
        payload = json.loads(msg.data)
    except Exception as e:
        rospy.logwarn("feedback_callback parse error: %s", e)
        return

    sketch_file = payload.get("sketch_file")
    answer = str(payload.get("answer", "")).strip().lower()

    if not sketch_file:
        rospy.logwarn("feedback missing sketch_file")
        return

    state = dialogue_state_by_sketch.get(sketch_file)
    if not state:
        rospy.logwarn("No dialogue state for sketch_file=%s", sketch_file)
        return

    rospy.loginfo("Feedback: sketch=%s answer=%s", sketch_file, answer)

    # --- リスケッチ: 状態をリセット ---
    if answer == "resketch":
        dialogue_state_by_sketch.pop(sketch_file, None)
        clip_query_by_sketch.pop(sketch_file, None)
        rospy.loginfo("Resketch: state cleared for %s", sketch_file)
        return

    # --- 戻る: 直前の質問画面に戻る（choose:N の誤タップ取り消し）---
    if answer == "back":
        last_payload = state.get("last_ask_payload")
        if last_payload:
            _save_and_publish(sketch_file, last_payload)
            rospy.loginfo("Back: re-published last question for %s", sketch_file)
        else:
            rospy.logwarn("Back: no last_ask_payload for %s, re-running dialogue", sketch_file)
            run_dialogue_turn(sketch_file)
        return

    # --- multi_choice での候補直接選択: "choose:N"（表示中の1-based順位）---
    if answer.startswith("choose:"):
        try:
            chosen_rank = int(answer.split(":", 1)[1])
            show_candidates = state["remaining_candidates"][:5]
            idx = chosen_rank - 1
            if 0 <= idx < len(show_candidates):
                _publish_confirmed(sketch_file, show_candidates[idx])
            else:
                rospy.logwarn("choose: invalid rank %d (shown=%d)", chosen_rank, len(show_candidates))
        except (ValueError, IndexError) as e:
            rospy.logwarn("choose parse error: %s", e)
        return

    # --- Yes / No 回答による候補絞り込み ---
    if answer not in ("yes", "no"):
        rospy.logwarn("Unknown answer '%s' for %s", answer, sketch_file)
        return

    current_q = state.get("current_question")
    if not current_q:
        rospy.logwarn("No current_question in state for %s", sketch_file)
        return

    # 回答と逆側の photo_id を remaining から除外する
    if answer == "yes":
        remove_ids = set(current_q["no_photo_ids"])
    else:
        remove_ids = set(current_q["yes_photo_ids"])

    before = len(state["remaining_candidates"])
    state["remaining_candidates"] = [
        c for c in state["remaining_candidates"]
        if c["photo_id"] not in remove_ids
    ]
    after = len(state["remaining_candidates"])

    state["question_history"].append({
        "question":       current_q["question"],
        "answer":         answer,
        "removed_count":  before - after,
        "remaining_count": after,
    })
    state["current_question"] = None

    rospy.loginfo("Filter: %d → %d candidates (removed %d) for %s",
                  before, after, before - after, sketch_file)

    remaining = state["remaining_candidates"]

    if len(remaining) == 0:
        _publish_resketch_request(sketch_file)
    elif len(remaining) == 1:
        _publish_confirmed(sketch_file, remaining[0])
    else:
        run_dialogue_turn(sketch_file)


# ---------------------------------------------------------------------------
# スケッチ受信（/writing トピック）
# ---------------------------------------------------------------------------

def callback(msg):
    data = msg.data
    _, encoded = data.split('base64,', 1)
    decoded = b64decode(encoded)

    sketch_dir = os.path.join(os.path.dirname(__file__), '..', 'sketch')
    os.makedirs(sketch_dir, exist_ok=True)

    counter = 1
    while True:
        output_path = os.path.join(sketch_dir, f'writing_{counter}.png')
        if not os.path.exists(output_path):
            break
        counter += 1

    with open(output_path, 'wb') as f:
        f.write(decoded)

    rospy.loginfo("Saved sketch: %s", output_path)

    sketch_file = os.path.basename(output_path)
    dialogue_state_by_sketch.pop(sketch_file, None)
    clip_query_by_sketch.pop(sketch_file, None)

    try:
        process_and_publish_sbir(output_path)
    except Exception as e:
        rospy.logerr("process_and_publish_sbir failed: %s", e)


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rospy.init_node("subscribe_writing1")

    # モデルとギャラリー特徴量を起動時に一度だけロード
    if _USE_ENGINE:
        rospy.loginfo("SBIREngine: loading model and gallery features...")
        try:
            get_engine().load()
            rospy.loginfo("SBIREngine: ready.")
        except Exception as _e:
            rospy.logerr("SBIREngine load failed: %s — falling back to subprocess", _e)

    result_pub = rospy.Publisher("/sbir_top5", String, queue_size=10)
    rospy.Subscriber("/writing",          String, callback)
    rospy.Subscriber("/writing_partial",  String, partial_callback)
    rospy.Subscriber("/vlm_user_feedback", String, feedback_callback)

    rospy.spin()
