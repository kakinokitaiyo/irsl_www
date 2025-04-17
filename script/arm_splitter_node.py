#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class ArmSplitterNode:
    def __init__(self):
        rospy.init_node("arm_splitter_node")

        # Publisher
        self.arm_pub = rospy.Publisher("/arm_controller/command", JointTrajectory, queue_size=10)
        self.gripper_pub = rospy.Publisher("/gripper_controller/command", JointTrajectory, queue_size=10)

        # Subscriber
        rospy.Subscriber("/arm_controller/input", Float64MultiArray, self.callback)

        rospy.loginfo("✅ arm_splitter_node 起動完了")
        rospy.spin()

    def callback(self, msg):
        if len(msg.data) != 9:
            rospy.logwarn(f"⚠️ 無効なデータ受信: 必須9軸, 実際は {len(msg.data)} 軸 → {tuple(msg.data)}")
            return

        # ジョイント名
        arm_joint_names = ["BASE_Y", "BASE_P", "BASE_R", "ELBOW_Y", "ELBOW_P", "WRIST_Y", "WRIST_P"]
        gripper_joint_names = ["GRIPPER0", "GRIPPER1"]

        # --- Arm ---
        arm_msg = JointTrajectory()
        arm_msg.joint_names = arm_joint_names
        arm_point = JointTrajectoryPoint()
        arm_point.positions = msg.data[:7]
        arm_point.time_from_start = rospy.Duration(1.0)
        arm_msg.points.append(arm_point)

        # --- Gripper ---
        gripper_msg = JointTrajectory()
        gripper_msg.joint_names = gripper_joint_names
        gripper_point = JointTrajectoryPoint()
        gripper_point.positions = msg.data[7:]
        gripper_point.time_from_start = rospy.Duration(1.0)
        gripper_msg.points.append(gripper_point)

        self.arm_pub.publish(arm_msg)
        self.gripper_pub.publish(gripper_msg)

        rospy.loginfo(f"✅ スライダー入力: arm={arm_point.positions}, gripper={gripper_point.positions}")

if __name__ == "__main__":
    try:
        ArmSplitterNode()
    except rospy.ROSInterruptException:
        pass
