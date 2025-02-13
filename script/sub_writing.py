#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from base64 import b64decode

def callback(msg):
    data = msg.data
    header, encoded = data.split('base64,', 1)

    decoded = b64decode(encoded)

    with open('/tmp/writing.png', 'wb') as f:
        f.write(decoded)

if __name__ == "__main__":
    rospy.init_node("subscribe_audio")

    sub = rospy.Subscriber("/writing", String, callback)

    rospy.spin()
