#!/usr/bin/env python
import rospy
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

def joy_callback(msg):
    twist = Twist()
    twist.linear.x = msg.axes[1]  # 前後移動
    twist.linear.y = msg.axes[0]  # 左右移動
    twist.angular.z = msg.axes[2] # その場回転

    # ログ出力（変更されたら表示）
    if twist.linear.x != 0.0 or twist.linear.y != 0.0 or twist.angular.z != 0.0:
        rospy.loginfo(f"[joy_to_cmdvel] publish cmd_vel: "
                      f"linear=({twist.linear.x:.2f}, {twist.linear.y:.2f}), "
                      f"angular=({twist.angular.z:.2f})")

    pub.publish(twist)

rospy.init_node("joy_to_cmdvel")
pub = rospy.Publisher("cmd_vel", Twist, queue_size=10)
sub = rospy.Subscriber("webjoy", Joy, joy_callback)
rospy.spin()
