#!/usr/bin/env python3
"""
HSR Action Bridge  –  TF + RGB-D カメラ把持
----------------------------------------------
1. DB の座標でおおよそのナビゲーション（精度不要）
2. ヘッドカメラで物体を検出 → base_link 座標を TF 変換
3. 横方向補正（オムニドライブ）
4. arm_lift を検出 z から IK 計算
5. グリッパー開 → アーム伸展 → 前進 → グリッパー閉 → 持ち上げ

DB への物体追加は position だけ粗く設定すればよく、
x/y の精密なキャリブレーションは不要。
"""

import os
import math
import threading
import yaml

import rospy
import actionlib
import numpy as np
import cv2

from std_msgs.msg import String
from geometry_msgs.msg import Twist, PointStamped
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from control_msgs.msg import FollowJointTrajectoryAction, FollowJointTrajectoryGoal
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import tf2_ros
import tf2_geometry_msgs   # PointStamped の transform を有効化

try:
    from tmc_control_msgs.msg import GripperApplyEffortAction
    _HAS_GRASP_ACTION = True
except ImportError:
    _HAS_GRASP_ACTION = False

# ── パス ────────────────────────────────────────────────────
OBJECT_DB_PATH = os.getenv(
    'OBJECT_DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'object_positions.yaml'))
EXECUTE_TOPIC = '/sbir_execute_object'

# ── アクションサーバー ───────────────────────────────────
NAV_SERVER   = '/move_base/move'
ARM_SERVER   = '/hsrb/arm_trajectory_controller/follow_joint_trajectory'
GRIP_SERVER  = '/hsrb/gripper_controller/follow_joint_trajectory'
GRASP_SERVER = '/hsrb/gripper_controller/grasp'
HEAD_SERVER  = '/hsrb/head_trajectory_controller/follow_joint_trajectory'

# ── 関節名 ───────────────────────────────────────────────
ARM_JOINTS  = ['arm_lift_joint', 'arm_flex_joint', 'arm_roll_joint',
               'wrist_flex_joint', 'wrist_roll_joint']
GRIP_JOINTS = ['hand_motor_joint']
HEAD_JOINTS = ['head_pan_joint', 'head_tilt_joint']

# ── ナビゲーション ───────────────────────────────────────
NAV_MAX_RETRY   = 3
NAV_TIMEOUT_SEC = 60.0

# ── カメラトピック ─────────────────────────────────────
RGB_TOPIC      = '/hsrb/head_rgbd_sensor/rgb/image_rect_color'
DEPTH_TOPIC    = '/hsrb/head_rgbd_sensor/depth_registered/image_rect_raw'
CAM_INFO_TOPIC = '/hsrb/head_rgbd_sensor/depth_registered/camera_info'

# ── 物体 → 色マッピング（HSV 検出用）──────────────────
OBJECT_COLOR_MAP = {
    'apple':      'red',
    'apple01':    'red',
    'orange':     'orange',
    'hsr_orange': 'orange',
}

HSV_RANGES = {
    'red': [
        (np.array([  0,  80,  80]), np.array([ 12, 255, 255])),
        (np.array([158,  80,  80]), np.array([180, 255, 255])),
    ],
    'orange': [
        (np.array([ 10, 100, 100]), np.array([ 30, 255, 255])),
    ],
}

# ── 把持パラメータ ───────────────────────────────────
ARM_BASE_HEIGHT  = 0.34   # アーム基部の高さ [m]
GRASP_FORWARD_M  = 0.25   # 前進距離フォールバック [m]
TARGET_GRASP_DIST = 0.57  # グリッパーを閉じる時点の base_link-物体間距離 [m]
                           # ≒ アーム水平リーチ(0.65) − 把持深さ(0.08)
LATERAL_THRESH   = 0.008  # 横補正を行う閾値 [m]（8mm：グリッパー余裕を考慮）
MIN_BLOB_AREA    = 100    # 有効な検出最小面積 [px²]
GRASP_Z_OFFSET   = 0.04   # 深度カメラは物体の上面付近を計測するため
                           # 物体中心に合わせるためのオフセット（≒ 物体半径）[m]


# ────────────────────────────────────────────────────────────
# ユーティリティ
# ────────────────────────────────────────────────────────────

def load_object_db():
    with open(OBJECT_DB_PATH, 'r') as f:
        data = yaml.safe_load(f)
    return data.get('objects', {})


def make_nav_goal(x, y, theta):
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id = 'map'
    goal.target_pose.header.stamp = rospy.Time.now()
    goal.target_pose.pose.position.x = x
    goal.target_pose.pose.position.y = y
    goal.target_pose.pose.orientation.z = math.sin(theta / 2.0)
    goal.target_pose.pose.orientation.w = math.cos(theta / 2.0)
    return goal


def make_traj_goal(joint_names, positions, duration_sec):
    goal = FollowJointTrajectoryGoal()
    traj = JointTrajectory()
    traj.joint_names = joint_names
    pt = JointTrajectoryPoint()
    pt.positions = list(positions)
    pt.time_from_start = rospy.Duration(duration_sec)
    traj.points = [pt]
    goal.trajectory = traj
    return goal


# ────────────────────────────────────────────────────────────
# メインクラス
# ────────────────────────────────────────────────────────────

class HSRActionBridge:

    def __init__(self):
        rospy.init_node('hsr_action_bridge')
        self.object_db = load_object_db()
        rospy.loginfo("Loaded %d objects", len(self.object_db))

        self._initialized = False
        self._cv_bridge   = CvBridge()

        # TF リスナー（__init__ 内で早めに作成してバッファを蓄積）
        self.tf_buffer   = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        rospy.Subscriber(EXECUTE_TOPIC, String, self._on_execute)
        rospy.loginfo("Listening on %s", EXECUTE_TOPIC)

        # アクションクライアント
        self.nav_client  = actionlib.SimpleActionClient(NAV_SERVER,  MoveBaseAction)
        self.arm_client  = actionlib.SimpleActionClient(ARM_SERVER,  FollowJointTrajectoryAction)
        self.grip_client = actionlib.SimpleActionClient(GRIP_SERVER, FollowJointTrajectoryAction)
        self.head_client = actionlib.SimpleActionClient(HEAD_SERVER, FollowJointTrajectoryAction)

        rospy.loginfo("Waiting for servers ...")
        nav_ok  = self.nav_client.wait_for_server(rospy.Duration(15.0))
        arm_ok  = self.arm_client.wait_for_server(rospy.Duration(10.0))
        grip_ok = self.grip_client.wait_for_server(rospy.Duration(10.0))
        head_ok = self.head_client.wait_for_server(rospy.Duration(10.0))
        self._arm_ready  = arm_ok
        self._grip_ready = grip_ok
        self._head_ready = head_ok
        rospy.loginfo("nav=%s  arm=%s  grip=%s  head=%s", nav_ok, arm_ok, grip_ok, head_ok)

        self._grasp_ready = False
        if _HAS_GRASP_ACTION:
            self.grasp_client = actionlib.SimpleActionClient(GRASP_SERVER, GripperApplyEffortAction)
            self._grasp_ready = self.grasp_client.wait_for_server(rospy.Duration(5.0))

        self._initialized = True
        rospy.loginfo("Bridge ready")

    # ── キー解決 ──────────────────────────────────────────

    def _lookup_entry(self, msg_data):
        base = os.path.splitext(msg_data.strip())[0].replace('_edge', '')
        entry = self.object_db.get(base)
        if entry is None:
            matches = [k for k in self.object_db
                       if k.startswith(base) or base.startswith(k)]
            if matches:
                base  = matches[0]
                entry = self.object_db[base]
                rospy.loginfo("Key: '%s' → '%s'", msg_data, base)
        return base, entry

    # ── ナビゲーション ──────────────────────────────────

    def _navigate(self, pos):
        x, y, theta = pos['x'], pos['y'], pos['theta']
        for attempt in range(1, NAV_MAX_RETRY + 1):
            rospy.loginfo("Nav %d/%d → (%.2f, %.2f, %.2f)", attempt, NAV_MAX_RETRY, x, y, theta)
            self.nav_client.send_goal(make_nav_goal(x, y, theta))
            ok = self.nav_client.wait_for_result(rospy.Duration(NAV_TIMEOUT_SEC))
            if not ok:
                rospy.logwarn("Nav timeout (attempt %d)", attempt)
                self.nav_client.cancel_goal()
                y += 0.3
                continue
            if self.nav_client.get_state() == actionlib.GoalStatus.SUCCEEDED:
                rospy.loginfo("Navigation succeeded")
                return True
            rospy.logwarn("Nav failed state=%d", self.nav_client.get_state())
            y += 0.3
        rospy.logerr("Navigation failed after %d attempts", NAV_MAX_RETRY)
        return False

    # ── 腕・グリッパー・頭 ──────────────────────────────

    def _arm_move(self, positions, duration=3.0):
        if not self._arm_ready:
            rospy.logwarn("Arm not ready")
            return False
        self.arm_client.send_goal(make_traj_goal(ARM_JOINTS, positions, duration))
        ok = self.arm_client.wait_for_result(rospy.Duration(duration + 5.0))
        if not ok:
            rospy.logwarn("Arm timeout")
        return ok

    def _grip_open(self):
        if not self._grip_ready:
            return
        rospy.loginfo("Opening gripper")
        self.grip_client.send_goal(make_traj_goal(GRIP_JOINTS, [1.2], 2.0))
        self.grip_client.wait_for_result(rospy.Duration(5.0))

    def _grip_close(self):
        if not self._grip_ready:
            return
        rospy.loginfo("Closing gripper")
        self.grip_client.send_goal(make_traj_goal(GRIP_JOINTS, [0.0], 2.0))
        self.grip_client.wait_for_result(rospy.Duration(5.0))

    def _head_move(self, pan, tilt, duration=2.0):
        if not self._head_ready:
            rospy.logwarn("Head not ready — skipping")
            return
        self.head_client.send_goal(make_traj_goal(HEAD_JOINTS, [pan, tilt], duration))
        self.head_client.wait_for_result(rospy.Duration(duration + 3.0))

    # ── ベース速度制御 ──────────────────────────────────

    def _ensure_base_pub(self):
        if not hasattr(self, '_base_vel_pub'):
            self._base_vel_pub = rospy.Publisher(
                '/hsrb/command_velocity_teleop', Twist, queue_size=1)
            rospy.sleep(1.0)

    def _drive_velocity(self, vx, vy, duration_s):
        """vx/vy はロボット座標系 [m/s]"""
        self._ensure_base_pub()
        msg = Twist()
        msg.linear.x = vx
        msg.linear.y = vy
        end_time = rospy.Time.now() + rospy.Duration(duration_s)
        rate = rospy.Rate(10)
        while rospy.Time.now() < end_time and not rospy.is_shutdown():
            self._base_vel_pub.publish(msg)
            rate.sleep()
        self._base_vel_pub.publish(Twist())
        rospy.sleep(0.3)

    def _drive_forward(self, dist_m, speed=0.15):
        rospy.loginfo("Drive forward %.3f m", dist_m)
        self._drive_velocity(speed, 0.0, dist_m / speed)

    def _drive_lateral(self, dist_m, speed=0.10):
        """正 = ロボット左方向（base_link +y）
        小さい距離ほど実際の移動量が少なくなるため、最小drive時間を確保する。
        """
        MIN_DRIVE_TIME = 0.40   # これより短いと慣性で実移動量が不足する
        t = abs(dist_m) / speed
        if t < MIN_DRIVE_TIME:
            # 速度を下げて最小時間を確保（正確な距離を維持）
            speed = abs(dist_m) / MIN_DRIVE_TIME
        rospy.loginfo("Drive lateral %.3f m @ %.3f m/s", dist_m, speed)
        self._drive_velocity(0.0, math.copysign(speed, dist_m), abs(dist_m) / speed)

    # ── RGB-D 物体検出 ──────────────────────────────────

    @staticmethod
    def _valid_depth(depth, u, v, radius=5):
        """(u, v) 近傍で NaN でない最初の深度値を返す"""
        h, w = depth.shape
        for r in range(radius + 1):
            for du in range(-r, r + 1):
                for dv in range(-r, r + 1):
                    pu, pv = u + du, v + dv
                    if 0 <= pu < w and 0 <= pv < h:
                        val = float(depth[pv, pu])
                        if not math.isnan(val) and val > 0.05:
                            return val
        return None

    def _detect_object_3d(self, object_key):
        """
        RGB-D カメラで object_key の色をもつ物体を検出し、
        base_link 座標系での (x, y, z) [m] を返す。
        検出できない場合は None を返す。
        """
        color = OBJECT_COLOR_MAP.get(object_key)
        if color is None:
            rospy.logwarn("No color mapping for '%s' — skip detection", object_key)
            return None
        if color not in HSV_RANGES:
            return None

        try:
            rgb_msg   = rospy.wait_for_message(RGB_TOPIC,      Image,      timeout=5.0)
            depth_msg = rospy.wait_for_message(DEPTH_TOPIC,    Image,      timeout=5.0)
            cam_info  = rospy.wait_for_message(CAM_INFO_TOPIC, CameraInfo, timeout=5.0)
        except rospy.ROSException as e:
            rospy.logwarn("Camera data unavailable: %s", e)
            return None

        rgb = self._cv_bridge.imgmsg_to_cv2(rgb_msg, 'bgr8')
        # 16UC1 (mm) → float32 (m)
        depth_raw = self._cv_bridge.imgmsg_to_cv2(depth_msg, '16UC1')
        depth = depth_raw.astype(np.float32) / 1000.0
        depth[depth_raw == 0] = np.nan   # 無効深度を NaN に
        fx, fy = cam_info.K[0], cam_info.K[4]
        cx, cy = cam_info.K[2], cam_info.K[5]

        # カラーマスク生成
        hsv  = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in HSV_RANGES[color]:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
        k    = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        # 最大輪郭の重心
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            rospy.logwarn("No %s blob detected", color)
            return None
        largest = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < MIN_BLOB_AREA:
            rospy.logwarn("Blob too small (%.0f px²)", area)
            return None

        M  = cv2.moments(largest)
        pu = int(M['m10'] / M['m00'])
        pv = int(M['m01'] / M['m00'])
        rospy.loginfo("Blob centroid (%d, %d)  area=%.0f", pu, pv, area)

        # 深度取得
        z = self._valid_depth(depth, pu, pv)
        if z is None or z > 3.0:
            rospy.logwarn("Invalid depth at centroid: %s", z)
            return None
        rospy.loginfo("Depth = %.3f m", z)

        # カメラ座標系での 3D 点
        pt = PointStamped()
        pt.header.frame_id = depth_msg.header.frame_id
        pt.header.stamp    = rospy.Time(0)   # 最新の TF を使用
        pt.point.x = (pu - cx) * z / fx
        pt.point.y = (pv - cy) * z / fy
        pt.point.z = z

        # TF 変換: カメラフレーム → base_link
        try:
            pt_base = self.tf_buffer.transform(pt, 'base_link', rospy.Duration(1.0))
        except Exception as e:
            rospy.logerr("TF transform failed: %s", e)
            return None

        ox, oy, oz = pt_base.point.x, pt_base.point.y, pt_base.point.z
        rospy.loginfo("Object in base_link: (%.3f, %.3f, %.3f)", ox, oy, oz)
        return ox, oy, oz

    # ── 把持シーケンス ──────────────────────────────────

    def _grasp(self, object_key, pick_height_fallback):
        """
        TF + hsrb_interface 逆運動学による把持シーケンス:
          1. ヘッドをテーブルへ向ける
          2. RGB-D で物体の 3D 座標を検出 (TF → base_link)
          3. 横方向補正（オムニドライブ）
          4. hsrb_interface whole_body IK で手先を物体位置へ
          5. 力制御で把持 → 持ち上げ → 運搬姿勢
        """
        if not (self._arm_ready and self._grip_ready):
            rospy.logwarn("Controllers not ready — skipping grasp")
            return

        # --- hsrb_interface の初期化 ---
        try:
            import hsrb_interface
            from hsrb_interface import geometry as hsr_geom
            _ri    = hsrb_interface.Robot()
            _wb    = _ri.get('whole_body')
            _hgrip = _ri.get('gripper')
            use_ik = True
            rospy.loginfo("[grasp] hsrb_interface OK → IK mode")
        except Exception as _e:
            rospy.logwarn("[grasp] hsrb_interface unavailable (%s) → manual mode", _e)
            use_ik = False

        # 1. ヘッドをテーブル方向へ
        rospy.loginfo("[grasp] 1: head → table")
        self._head_move(0.0, -0.8, 2.0)
        rospy.sleep(0.8)

        # 2. 物体検出
        rospy.loginfo("[grasp] 2: detect '%s'", object_key)
        detected = self._detect_object_3d(object_key)

        ox = GRASP_FORWARD_M + TARGET_GRASP_DIST
        oy = 0.0
        oz = pick_height_fallback
        if detected is not None:
            ox, oy, oz = detected
            rospy.loginfo("[grasp]   ox=%.3f oy=%.3f oz=%.3f", ox, oy, oz)
        else:
            rospy.logwarn("[grasp]   detection failed → fallback")

        # 3. 横方向補正（最大5回）
        for _iter in range(5):
            if not (detected is not None and abs(oy) > LATERAL_THRESH):
                break
            rospy.loginfo("[grasp] 3.%d: lateral correction %.3f m", _iter + 1, oy)
            self._drive_lateral(oy)
            rospy.sleep(0.3)
            detected = self._detect_object_3d(object_key)
            if detected is None:
                break
            ox, oy, oz = detected
            rospy.loginfo("[grasp]   ox=%.3f oy=%.3f oz=%.3f", ox, oy, oz)
        rospy.loginfo("[grasp] 3: lateral final oy=%.3f m", oy)

        oz_center = oz - GRASP_Z_OFFSET   # カメラは上面計測 → 中心に補正

        # ── IK モード（hsrb_interface whole_body） ──────────────
        if use_ik:
            try:
                # 4. グリッパーを開く
                rospy.loginfo("[grasp] 4: open gripper")
                _hgrip.command(1.0)
                rospy.sleep(0.5)

                # 5. アームを水平方向に事前配置（wrist_roll=0 の正しい向きを確立）
                lift_approx = float(np.clip(oz_center - ARM_BASE_HEIGHT, 0.0, 0.69))
                rospy.loginfo("[grasp] 5: pre-position arm (lift=%.3f)", lift_approx)
                self._arm_move([lift_approx, -1.57, 0.0, 0.0, 0.0], 3.0)
                rospy.sleep(0.5)

                # 6. 現在の手先位置を TF で取得し、hand_palm_link 基準の相対移動を計算
                #    → 向き指定なし = wrist_roll が変わらない（180° 回転を防止）
                import tf.transformations as _tft
                _t = self.tf_buffer.lookup_transform(
                    'base_link', 'hand_palm_link', rospy.Time(0), rospy.Duration(2.0))
                _hx = _t.transform.translation.x
                _hy = _t.transform.translation.y
                _hz = _t.transform.translation.z
                _q  = _t.transform.rotation
                # base_link → hand_palm_link への回転行列（TF は hand→base なので転置）
                _R  = _tft.quaternion_matrix([_q.x, _q.y, _q.z, _q.w])[:3, :3]
                _delta_bl   = np.array([ox - _hx, oy - _hy, oz_center - _hz])
                _delta_hand = _R.T @ _delta_bl   # hand フレームへ変換
                _dx, _dy, _dz = float(_delta_hand[0]), float(_delta_hand[1]), float(_delta_hand[2])
                rospy.loginfo("[grasp] 6: hand→target delta (hand frame): "
                              "%.3f %.3f %.3f", _dx, _dy, _dz)
                # 向き指定なし → 事前配置した向き（wrist_roll=0）を維持したまま位置だけ移動
                target = hsr_geom.pose(x=_dx, y=_dy, z=_dz)
                _wb.move_end_effector_pose(target, 'hand_palm_link')

                # 7. 力制御で把持（正の値 = 閉じる方向）
                rospy.loginfo("[grasp] 7: apply_force grasp")
                _hgrip.apply_force(0.8)
                rospy.sleep(2.0)

                # 8. 運搬姿勢（move_to_go で安全に収納）
                rospy.loginfo("[grasp] 8: move_to_go")
                _wb.move_to_go()

                rospy.loginfo("[grasp] complete (IK)")
                return

            except Exception as _e:
                rospy.logerr("[grasp] IK failed: %s → manual fallback", _e)

        # ── マニュアルモード（フォールバック） ───────────────────
        lift_grasp = float(np.clip(oz_center - ARM_BASE_HEIGHT, 0.0, 0.69))
        lift_carry = float(np.clip(oz + 0.10,                  0.0, 0.69))

        rospy.loginfo("[grasp] 4: open gripper (manual)")
        self._grip_open()
        rospy.sleep(0.5)

        rospy.loginfo("[grasp] 5: extend arm (lift=%.3f)", lift_grasp)
        self._arm_move([lift_grasp, -1.57, 0.0, 0.0, 0.0], 3.0)
        rospy.sleep(0.5)

        ARM_REACH_M   = 0.65
        EXTRA_DRIVE_M = 0.05
        forward_drive = max(0.05, ox - TARGET_GRASP_DIST + EXTRA_DRIVE_M)
        arm_to_apple  = max(0.0, ox - ARM_REACH_M)
        fast_dist     = max(0.0, arm_to_apple - 0.12)
        slow_dist     = forward_drive - fast_dist

        rospy.loginfo("[grasp] 6: forward_drive=%.3f m", forward_drive)
        if fast_dist > 0.01:
            self._drive_forward(fast_dist, speed=0.15)
            rospy.sleep(0.1)
        self._drive_forward(slow_dist, speed=0.06)

        rospy.loginfo("[grasp] 7: close gripper")
        self._grip_close()
        rospy.sleep(1.0)

        rospy.loginfo("[grasp] 8: lift (lift=%.3f)", lift_carry)
        self._arm_move([lift_carry, -1.57, 0.0, 0.0, 0.0], 2.5)
        rospy.sleep(0.3)

        rospy.loginfo("[grasp] 9: carry pose")
        self._arm_move([lift_carry, -2.0, -1.57, -1.5, 0.0], 3.0)
        rospy.loginfo("[grasp] complete (manual)")

    # ── コールバック ───────────────────────────────────

    def _on_execute(self, msg):
        threading.Thread(target=self._execute_task, args=(msg.data,), daemon=True).start()

    def _execute_task(self, object_key):
        rospy.loginfo("Execute: %s", object_key)
        while not self._initialized and not rospy.is_shutdown():
            rospy.sleep(0.5)

        base, entry = self._lookup_entry(object_key)
        if entry is None:
            rospy.logwarn("'%s' not found in DB", object_key)
            rospy.logwarn("Available: %s", list(self.object_db.keys()))
            return

        pos            = entry['position']
        pick_up_height = entry.get('pick_up_height', 0.44)
        rospy.loginfo("Target: %s  nav=(%.2f, %.2f, %.2f)  fallback_height=%.3f",
                      base, pos['x'], pos['y'], pos['theta'], pick_up_height)

        if not self._navigate(pos):
            rospy.logerr("Navigation failed — abort")
            return

        # move_base を解放してから速度コマンドを使えるようにする
        self.nav_client.cancel_all_goals()
        rospy.sleep(0.5)

        self._grasp(base, pick_up_height)

    def spin(self):
        rospy.spin()


if __name__ == '__main__':
    try:
        bridge = HSRActionBridge()
        bridge.spin()
    except rospy.ROSInterruptException:
        pass
