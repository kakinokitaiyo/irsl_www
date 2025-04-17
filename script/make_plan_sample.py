import rospy
from nav_msgs.srv import GetPlan
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped

class MakePlanSampleNode():
    def __init__(self):
        self.pub = rospy.Publisher('make_plan_path', Path, queue_size=1)
        try:
            rospy.wait_for_service('/move_base/make_plan', timeout=10.0)
            self.make_plan_srv = rospy.ServiceProxy('/move_base/make_plan', GetPlan)
        except Exception as e:
            rospy.logerr(f"error: {e}")
            exit(1)

    def make_plan(self):
        try:
            start = PoseStamped()
            start.header.stamp = rospy.Time.now()
            start.header.frame_id = "map"
            start.pose.position.x = 1.8
            start.pose.position.y = 2.0
            start.pose.position.z = 0.0

            goal = PoseStamped()
            goal.header.stamp = rospy.Time.now()
            goal.header.frame_id = "map"
            goal.pose.position.x = 1.8
            goal.pose.position.y = -2.0
            goal.pose.position.z = 0.0

            resp = self.make_plan_srv(start, goal, 1.0)

            msg = Path()
            msg.header.stamp = rospy.Time.now()
            msg.header.frame_id = "map"
            msg.poses = resp.plan.poses

            rospy.sleep(0.3)
            self.pub.publish(msg)
        except Exception as e:
            rospy.logerr(f"error: {e}")
        else:
            rospy.loginfo("make plan success")

if __name__ == "__main__":
    rospy.init_node("make_plan_sample")
    node = MakePlanSampleNode()
    node.make_plan()
