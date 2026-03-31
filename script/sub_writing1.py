#!/usr/bin/env python3

import os
import rospy
from std_msgs.msg import String
from base64 import b64decode

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

if __name__ == "__main__":
    rospy.init_node("subscribe_writing1")

    sub = rospy.Subscriber("/writing", String, callback)

    rospy.spin()
