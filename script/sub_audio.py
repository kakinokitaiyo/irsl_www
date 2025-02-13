#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from base64 import b64decode

from cog_speech import recognize_from_microphone

def callback(msg):
    print('callback')
    data = msg.data
    header, encoded = data.split('base64,', 1)

    decoded = b64decode(encoded)

    with open('/tmp/audio.wav', 'wb') as f:
        f.write(decoded)
        res = recognize_from_microphone('/tmp/audio.wav')
        print(res)
        pub.publish(String(res))

if __name__ == "__main__":
    rospy.init_node("subscribe_audio")

    sub = rospy.Subscriber("/audio", String, callback)
    pub = rospy.Publisher('/audio_result', String)
    rospy.spin()
