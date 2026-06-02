#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import rospy
from std_msgs.msg import String
from base64 import b64decode

# Import VLM module for reverse questioning
try:
    from gemini_api import (
        init_gemini_client,
        process_sbir_with_vlm,
        extract_search_query_from_sketch,
    )
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False
    rospy.logwarn("VLM module not available. Skipping VLM processing.")


result_pub = None
excluded_gallery_ids_by_sketch = {}
latest_result_by_sketch = {}
clip_query_by_sketch = {}


def enrich_result_for_web(parsed: dict, sketch_path: str) -> dict:
    """Add web-accessible image paths into SBIR result payload."""
    web_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'html', 'touch'))
    photo_web_dir = os.path.join(web_root, 'sbir_photos')
    sketch_web_dir = os.path.join(web_root, 'sbir_sketches')
    os.makedirs(photo_web_dir, exist_ok=True)
    os.makedirs(sketch_web_dir, exist_ok=True)

    # Copy sketch for display on web page
    sketch_base = os.path.basename(sketch_path)
    sketch_dst = os.path.join(sketch_web_dir, sketch_base)
    try:
        shutil.copy2(sketch_path, sketch_dst)
        parsed["sketch_web_path"] = f"/touch/sbir_sketches/{sketch_base}"
    except Exception as e:
        rospy.logwarn("Failed to copy sketch for web display: %s", str(e))

    # Copy top-k photos for display on web page
    topk = parsed.get("topk", [])
    for item in topk:
        src = item.get("photo_source_path")
        rank = item.get("rank", 0)
        if not src or not os.path.isfile(src):
            continue
        base = os.path.basename(src)
        dst_name = f"r{rank}_{base}"
        dst_path = os.path.join(photo_web_dir, dst_name)
        try:
            shutil.copy2(src, dst_path)
            item["photo_web_path"] = f"/touch/sbir_photos/{dst_name}"
        except Exception as e:
            rospy.logwarn("Failed to copy photo for web display (%s): %s", src, str(e))

    return parsed


def parse_json_from_mixed_output(output: str) -> dict:
    text = (output or "").strip()
    if not text:
        raise ValueError("SBIR output is empty")

    # まず全体を JSON として解釈
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ログ混在時は下から順に JSON 行を探索
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON found in SBIR output: {text[:300]}")


def run_sbir_once(sketch_path: str, exclude_gallery_ids=None, clip_text_query: str | None = None) -> str:
    clip_db_root = os.getenv("CLIP_DB_ROOT", "/home/irsl/workspace/CLIP_DB")
    sbir_script = os.path.join(clip_db_root, "src", "run_sbir_once_from_db.py")

    if not os.path.isfile(sbir_script):
        raise FileNotFoundError(f"SBIR script not found: {sbir_script}")

    cmd = [
        sys.executable,
        sbir_script,
        "--sketch_path",
        sketch_path,
        "--topk",
        os.getenv("SBIR_TOPK", "5"),
        "--host",
        os.getenv("PGHOST", "133.15.97.94"),
        "--port",
        os.getenv("PGPORT", "5432"),
        "--dbname",
        os.getenv("PGDATABASE", "kakinoki_db"),
        "--user",
        os.getenv("PGUSER", "kakinoki_taiyo"),
        "--password",
        os.getenv("PGPASSWORD", "irsl"),
        "--schema",
        os.getenv("SBIR_SCHEMA", "home_robot"),
        "--gallery_table",
        os.getenv("SBIR_GALLERY_TABLE", "photos_edge"),
        "--display_table",
        os.getenv("SBIR_DISPLAY_TABLE", "photos"),
        "--gallery_source_type",
        os.getenv("SBIR_GALLERY_SOURCE_TYPE", "photo_edge"),
        "--display_source_type",
        os.getenv("SBIR_DISPLAY_SOURCE_TYPE", "photo"),
        "--device",
        os.getenv("SBIR_DEVICE", "auto"),
        "--sketchscape_root",
        os.getenv("SKETCHSCAPE_ROOT", "/home/irsl/workspace/SketchScape"),
        "--model_path",
        os.getenv("SBIR_MODEL_PATH", "/home/irsl/workspace/SketchScape/models/fscoco_normal.pth"),
        "--coarse_topk",
        os.getenv("SBIR_COARSE_TOPK", "100"),
    ]

    if exclude_gallery_ids:
        ids = [str(int(v)) for v in exclude_gallery_ids if isinstance(v, int)]
        if ids:
            cmd.extend(["--exclude_gallery_ids", ",".join(ids)])

    if (os.getenv("ENABLE_CLIP_FUSION", "false").lower() == "true") and clip_text_query:
        cmd.extend(
            [
                "--enable_clip_fusion",
                "--clip_text_query",
                clip_text_query,
                "--clip_embeddings_path",
                os.getenv("CLIP_IMAGE_EMBEDDINGS_PATH", "/home/irsl/workspace/CLIP_DB/cache/clip_image_embeddings.npz"),
                "--scape_weight",
                os.getenv("SBIR_SCAPE_WEIGHT", "0.7"),
                "--clip_weight",
                os.getenv("SBIR_CLIP_WEIGHT", "0.3"),
                "--clip_model",
                os.getenv("CLIP_MODEL_NAME", "ViT-B-32"),
                "--clip_pretrained",
                os.getenv("CLIP_PRETRAINED", "laion2b_s34b_b79k"),
            ]
        )

    # DINOv2 fusion: enable if environment flag set
    if os.getenv("ENABLE_DINOV2_FUSION", "false").lower() == "true":
        cmd.extend(
            [
                "--enable_dinov2_fusion",
                "--dinov2_weight",
                os.getenv("SBIR_DINO_WEIGHT", "0.3"),
            ]
        )
        dinov2_npz = os.getenv("DINO_IMAGE_EMBEDDINGS_PATH", "")
        if dinov2_npz:
            cmd.extend(["--dinov2_embeddings_path", dinov2_npz])

    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return completed.stdout.strip()
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        raise RuntimeError(
            f"SBIR command failed (exit={e.returncode}) "
            f"stderr={stderr or '<empty>'} stdout={stdout or '<empty>'}"
        ) from e


def process_and_publish_sbir(sketch_path: str, exclude_gallery_ids=None) -> dict:
    sketch_file = os.path.basename(sketch_path)
    clip_text_query = None
    if os.getenv("ENABLE_CLIP_FUSION", "false").lower() == "true":
        clip_text_query = clip_query_by_sketch.get(sketch_file)
        if not clip_text_query and VLM_AVAILABLE:
            try:
                vlm_client = init_gemini_client(os.getenv("GEMINI_API_KEY"))
                clip_text_query = extract_search_query_from_sketch(sketch_path, client=vlm_client)
                if clip_text_query:
                    clip_query_by_sketch[sketch_file] = clip_text_query
                    rospy.loginfo("CLIP query extracted: %s", clip_text_query)
            except Exception as e:
                rospy.logwarn("Failed to extract CLIP query from sketch: %s", str(e))

    result_json = run_sbir_once(
        sketch_path,
        exclude_gallery_ids=exclude_gallery_ids,
        clip_text_query=clip_text_query,
    )
    parsed = parse_json_from_mixed_output(result_json)
    parsed = enrich_result_for_web(parsed, sketch_path)

    # VLM Post-processing: Reverse questioning for candidate filtering
    if VLM_AVAILABLE and os.getenv("ENABLE_VLM", "true").lower() == "true":
        try:
            rospy.loginfo("Initiating VLM reverse questioning...")
            vlm_client = init_gemini_client(os.getenv("GEMINI_API_KEY"))
            parsed = process_sbir_with_vlm(parsed, sketch_path, client=vlm_client)
            rospy.loginfo("VLM processing completed")
        except Exception as e:
            rospy.logerr("VLM processing failed, continuing with SBIR results only: %s", str(e))
    else:
        if not VLM_AVAILABLE:
            rospy.logwarn("VLM module not available, skipping reverse questioning")
        elif os.getenv("ENABLE_VLM", "true").lower() != "true":
            rospy.loginfo("VLM processing disabled by environment variable")

    result_dir = os.path.join(os.path.dirname(__file__), '..', 'sketch_result')
    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(
        result_dir,
        os.path.splitext(os.path.basename(sketch_path))[0] + '_top5.json'
    )
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    sketch_file = parsed.get("sketch_file") or sketch_file
    latest_result_by_sketch[sketch_file] = parsed

    if result_pub is not None:
        result_pub.publish(String(data=json.dumps(parsed, ensure_ascii=False)))

    rospy.loginfo("SBIR result saved to: %s", result_path)
    return parsed


def feedback_callback(msg):
    try:
        payload = json.loads(msg.data)
    except Exception as e:
        rospy.logwarn("Failed to parse /vlm_user_feedback payload: %s", str(e))
        return

    sketch_file = payload.get("sketch_file")
    answer = str(payload.get("answer", "")).strip().lower()

    if not sketch_file:
        rospy.logwarn("/vlm_user_feedback missing sketch_file")
        return

    # 決定操作（yes/no/choose）後は一時除外を解除して、次回はDB全体から探索できるようにする
    is_decision_answer = (
        answer in {"yes", "no", "confirm"}
        or answer.startswith("choose:")
    )
    if is_decision_answer:
        if sketch_file in excluded_gallery_ids_by_sketch:
            excluded_gallery_ids_by_sketch[sketch_file] = set()
            rospy.loginfo(
                "Decision answer '%s' received. Cleared temporary exclusions for %s",
                answer,
                sketch_file,
            )
        return

    # 再スケッチ選択時も除外を解除
    if answer == "resketch":
        if sketch_file in excluded_gallery_ids_by_sketch:
            excluded_gallery_ids_by_sketch[sketch_file] = set()
            rospy.loginfo("Resketch selected. Cleared temporary exclusions for %s", sketch_file)
        return

    if answer != "neither":
        return

    latest = latest_result_by_sketch.get(sketch_file)
    if not latest:
        rospy.logwarn("No cached SBIR result found for sketch_file=%s", sketch_file)
        return

    topk = latest.get("topk", []) if isinstance(latest, dict) else []
    current_gallery_ids = []
    for item in topk:
        if not isinstance(item, dict):
            continue
        gid = item.get("gallery_id")
        if isinstance(gid, int):
            current_gallery_ids.append(gid)
        elif isinstance(gid, str) and gid.isdigit():
            current_gallery_ids.append(int(gid))

    if not current_gallery_ids:
        rospy.logwarn("No gallery_id found in current Top5 for sketch_file=%s", sketch_file)
        return

    excluded = excluded_gallery_ids_by_sketch.setdefault(sketch_file, set())
    excluded.update(current_gallery_ids)

    sketch_path = os.path.join(os.path.dirname(__file__), '..', 'sketch', sketch_file)
    if not os.path.isfile(sketch_path):
        rospy.logwarn("Sketch file not found for re-search: %s", sketch_path)
        return

    try:
        rospy.loginfo(
            "'どれでもない' received. Re-running SBIR with temporary exclusion (count=%d) for %s",
            len(excluded),
            sketch_file,
        )
        process_and_publish_sbir(sketch_path, exclude_gallery_ids=sorted(excluded))
    except Exception as e:
        rospy.logerr("SBIR re-search after 'neither' failed: %s", str(e))

def callback(msg):
    data = msg.data
    header, encoded = data.split('base64,', 1)

    decoded = b64decode(encoded)

    # irsl_www/sketch/ ディレクトリに保存
    sketch_dir = os.path.join(os.path.dirname(__file__), '..', 'sketch')
    os.makedirs(sketch_dir, exist_ok=True)
    
    # 連番のファイル名を生成
    counter = 1
    while True:
        output_path = os.path.join(sketch_dir, f'writing_{counter}.png')
        if not os.path.exists(output_path):
            break
        counter += 1
    
    with open(output_path, 'wb') as f:
        f.write(decoded)
    
    rospy.loginfo("Saved image to: %s", output_path)

    try:
        sketch_file = os.path.basename(output_path)
        excluded_gallery_ids_by_sketch[sketch_file] = set()
        clip_query_by_sketch.pop(sketch_file, None)
        process_and_publish_sbir(output_path, exclude_gallery_ids=[])
    except Exception as e:
        rospy.logerr("SBIR failed: %s", str(e))

if __name__ == "__main__":
    rospy.init_node("subscribe_writing1")

    result_pub = rospy.Publisher("/sbir_top5", String, queue_size=10)

    sub = rospy.Subscriber("/writing", String, callback)
    feedback_sub = rospy.Subscriber("/vlm_user_feedback", String, feedback_callback)

    rospy.spin()
