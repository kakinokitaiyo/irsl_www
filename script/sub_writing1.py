#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import rospy
from std_msgs.msg import String
from base64 import b64decode


result_pub = None


def run_sbir_once(sketch_path: str) -> str:
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
        os.getenv("PGHOST", "localhost"),
        "--port",
        os.getenv("PGPORT", "5432"),
        "--dbname",
        os.getenv("PGDATABASE", "kakinoki_db"),
        "--user",
        os.getenv("PGUSER", ""),
        "--password",
        os.getenv("PGPASSWORD", ""),
        "--schema",
        os.getenv("SBIR_SCHEMA", "home_robot"),
        "--table",
        os.getenv("SBIR_TABLE", "sketch_images"),
        "--gallery_source_type",
        os.getenv("SBIR_GALLERY_SOURCE_TYPE", "output"),
        "--display_source_type",
        os.getenv("SBIR_DISPLAY_SOURCE_TYPE", "photo"),
        "--device",
        os.getenv("SBIR_DEVICE", "auto"),
        "--sketchscape_root",
        os.getenv("SKETCHSCAPE_ROOT", "/home/irsl/workspace/SketchScape"),
        "--model_path",
        os.getenv("SBIR_MODEL_PATH", "/home/irsl/workspace/SketchScape/models/fscoco_normal.pth"),
    ]

    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()

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
        result_json = run_sbir_once(output_path)

        result_dir = os.path.join(os.path.dirname(__file__), '..', 'sketch_result')
        os.makedirs(result_dir, exist_ok=True)
        result_path = os.path.join(
            result_dir,
            os.path.splitext(os.path.basename(output_path))[0] + '_top5.json'
        )
        with open(result_path, 'w', encoding='utf-8') as f:
            parsed = json.loads(result_json)
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        if result_pub is not None:
            result_pub.publish(String(data=result_json))

        rospy.loginfo("SBIR result saved to: %s", result_path)
    except Exception as e:
        rospy.logerr("SBIR failed: %s", str(e))

if __name__ == "__main__":
    rospy.init_node("subscribe_writing1")

    result_pub = rospy.Publisher("/sbir_top5", String, queue_size=10)

    sub = rospy.Subscriber("/writing", String, callback)

    rospy.spin()
