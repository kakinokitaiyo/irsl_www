# 8.1.1. ROS Interface

**目次**
- 頭部関節制御
- 腕部関節制御
- ハンド制御
- 台車制御
- 全身協調手先インピーダンス制御
- 手先カメラ
- 頭部広角カメラ
- 頭部ステレオカメラ（左）
- 頭部ステレオカメラ（右）
- 頭部3次元距離センサ
- IMU
- レーザースキャナー
- 6軸力覚センサー
- 関節状態
- マルチファンクションスイッチ
- デジタルI/O
- 電源管理
- ControllerManager制御

---

## 8.1.1.1. 頭部関節制御

`ros_controllers/JointTrajectoryController`に準じます。

制御対象関節:
- `head_pan_joint`
- `head_tilt_joint`

### Provided Actions
- `/hsrb/head_trajectory_controller/follow_joint_trajectory`  
  - type: `control_msgs/FollowJointTrajectory`  
  - description: 軌道再生のためのアクションインターフェース

### Published Topics
- `/hsrb/head_trajectory_controller/state`  
  - type: `control_msgs/JointTrajectoryControllerState`  
  - description: コントローラの現在状態

### Subscribed Topics
- `/hsrb/head_trajectory_controller/command`  
  - type: `trajectory_msgs/JointTrajectory`  
  - description: 目標軌道を設定するトピックインターフェース

### Provided Services
- `/hsrb/head_trajectory_controller/query_state`  
  - type: `control_msgs/QueryTrajectoryState`  
  - description: コントローラの状態を問い合わせる

### Parameters
- `/hsrb/head_trajectory_controller/joints`  
  - type: `String[]`  
  - description: 制御対象関節のリスト
- `/hsrb/head_trajectory_controller/constraints/goal_time`  
  - type: `Double`  
  - description: 目標軌道のタイムスタンプが t の時、t+/-goal_time 以内にゴールすれば成功とみなす。
- `/hsrb/head_trajectory_controller/constraints/stopped_velocity_tolerance`  
  - type: `Double`  
  - description: この値より小さい速度はゼロとみなす。
- `/hsrb/head_trajectory_controller/constraints/<joint>/goal`  
  - type: `Double`  
  - description: 各関節のゴールでの位置誤差許容値
- `/hsrb/head_trajectory_controller/constraints/<joint>/trajectory`  
  - type: `Double`  
  - description: 各関節の軌道中の位置誤差許容値
- `/hsrb/head_trajectory_controller/stop_trajectory_duration`  
  - type: `Double`  
  - description: 軌道キャンセル時、停止するまでの時間
- `/hsrb/head_trajectory_controller/state_publish_rate`  
  - type: `Double`  
  - description: コントローラ状態の出版周期［Hz］
- `/hsrb/head_trajectory_controller/action_monitor_rate`  
  - type: `Double`  
  - description: ゴール判定周期［Hz］

---

## 8.1.1.2. 腕部関節制御

`ros_controllers/JointTrajectoryController`に準じます。

制御対象関節:
- `arm_lift_joint`
- `arm_flex_joint`
- `arm_roll_joint`
- `wrist_flex_joint`
- `wrist_roll_joint`

### Provided Actions
- `/hsrb/arm_trajectory_controller/follow_joint_trajectory`  
  - type: `control_msgs/FollowJointTrajectory`  
  - description: 軌道再生のためのアクションインターフェース

### Published Topics
- `/hsrb/arm_trajectory_controller/state`  
  - type: `control_msgs/JointTrajectoryControllerState`  
  - description: コントローラの現在状態

### Subscribe Topics
- `/hsrb/arm_trajectory_controller/command`  
  - type: `trajectory_msgs/JointTrajectory`  
  - description: 目標軌道を設定するトピックインターフェース

### Provided Services
- `/hsrb/arm_trajectory_controller/query_state`  
  - type: `control_msgs/QueryTrajectoryState`  
  - description: コントローラの状態を問い合わせる

### Parameters
- `/hsrb/arm_trajectory_controller/joints`  
  - type: `String[]`  
  - description: 制御対象関節のリスト
- `/hsrb/arm_trajectory_controller/constraints/goal_time`  
  - type: `Double`  
  - description: 目標軌道のタイムスタンプが t の時、t+/-goal_time 以内にゴールすれば成功とみなす。
- `/hsrb/arm_trajectory_controller/constraints/stopped_velocity_tolerance`  
  - type: `Double`  
  - description: この値より小さい速度はゼロとみなす。
- `/hsrb/arm_trajectory_controller/constraints/<joint>/goal`  
  - type: `Double`  
  - description: 各関節のゴールでの位置誤差許容値
- `/hsrb/arm_trajectory_controller/constraints/<joint>/trajectory`  
  - type: `Double`  
  - description: 各関節の軌道中の位置誤差許容値
- `/hsrb/arm_trajectory_controller/stop_trajectory_duration`  
  - type: `Double`  
  - description: 軌道キャンセル時、停止するまでの時間
- `/hsrb/arm_trajectory_controller/state_publish_rate`  
  - type: `Double`  
  - description: コントローラ状態の出版周期［Hz］
- `/hsrb/arm_trajectory_controller/action_monitor_rate`  
  - type: `Double`  
  - description: ゴール判定周期［Hz］

---

## 8.1.1.3. ハンド制御

ハンド部を制御します。

### Provided Actions
- `/hsrb/gripper_controller/follow_joint_trajectory`  
  - type: `control_msgs/FollowJointTrajectory`  
  - description: 指関節軌道再生のアクションインターフェース
- `/hsrb/gripper_controller/grasp`  
  - type: `tmc_control_msgs/GripperApplyEffort`  
  - description: 握りこみ動作のためのアクションインターフェース
- `/hsrb/gripper_controller/apply_force`  
  - type: `tmc_control_msgs/GripperApplyEffort`  
  - description: 指定した力で把持するアクションインターフェース
- `/hsrb/suction_control`  
  - type: `tmc_suction/SuctionControl`  
  - description: 吸引機構の制御を行うアクションインターフェース

### Subscribe Topics
- `/hsrb/gripper_controller/command`  
  - type: `trajectory_msgs/JointTrajectory`  
  - description: 目標軌道を設定するトピックインターフェース

---

## 8.1.1.4. 台車制御

制御対象関節:
- `base_roll_joint`
- `base_l_drive_wheel_joint`
- `base_r_drive_wheel_joint`

ただし、`JointTrajectoryController`は `/odom` での位置・方位を仮想的に関節とみなした以下を制御:
- `odom_x`
- `odom_y`
- `odom_t`

### Provide Actions
- `/hsrb/omni_base_controller/follow_joint_trajectory`  
  - type: `control_msgs/FollowJointTrajectory`  
  - description: 台車軌道再生を行うアクションインターフェース

### Published Topics
- `/hsrb/omni_base_controller/state`  
  - type: `control_msgs/JointTrajectoryControllerState`  
  - description: コントローラの現在状態
- `/hsrb/odom`  
  - type: `nav_msgs/Odometry`  
  - description: ロボット起動時からのオドメトリ
- `/hsrb/wheel_odom`  
  - type: `nav_msgs/Odometry`  
  - description: ロボット起動時からのホイールオドメトリ
- `/hsrb/odom_ground_truth`  
  - type: `nav_msgs/Odometry`  
  - description: オドメトリ真値（Gazeboシミュレータのみ）

### Subscribed Topics
- `/hsrb/omni_base_controller/command`  
  - type: `trajectory_msgs/JointTrajectory`  
  - description: 目標軌道を設定するトピックインターフェース
- `/hsrb/command_velocity`  
  - type: `geometry_msgs/Twist`  
  - description: 目標速度を設定するトピックインターフェース

### Parameters
- `/hsrb/omni_base_controller/base_coordinates`  
  - type: `String[]`  
  - description: 制御対象関節のリスト
- `/hsrb/omni_base_controller/joints/l_wheel`  
  - type: `String`  
  - description: 左駆動輪の関節名
- `/hsrb/omni_base_controller/joints/r_wheel`  
  - type: `String`  
  - description: 右駆動輪の関節名
- `/hsrb/omni_base_controller/joints/steer`  
  - type: `String`  
  - description: 台車旋回軸の関節名
- `/hsrb/omni_base_controller/constraints/<joint>/trajectory`  
  - type: `Double`  
  - description: 各関節の軌道中の位置誤差許容値
- `/hsrb/omni_base_controller/stop_trajectory_duration`  
  - type: `Double`  
  - description: 軌道キャンセル時、停止するまでの時間［s］
- `/hsrb/omni_base_controller/state_publish_rate`  
  - type: `Double`  
  - description: コントローラ状態の出版周期［Hz］
- `/hsrb/omni_base_controller/action_monitor_rate`  
  - type: `Double`  
  - description: ゴール判定周期［Hz］
- `/hsrb/omni_base_controller/command_timeout`  
  - type: `Double`  
  - description: 目標速度入力の途絶判定時間［s］ (デフォルト: 0.5)
- `/hsrb/omni_base_controller/odometry_publish_rate`  
  - type: `Double`  
  - description: オドメトリの出版周期［Hz］ (デフォルト: 30.0)
- `/hsrb/omni_base_controller/transform_publish_rate`  
  - type: `Double`  
  - description: オドメトリのTF出版周期［Hz］ (デフォルト: 30.0)
- `/hsrb/omni_base_controller/use_laser_odom`  
  - type: `Boolean`  
  - description: レーザーオドメトリ入力の On/Off
- `/hsrb/omni_base_controller/wheel_odom_map_frame`  
  - type: `String`  
  - description: ホイールオドメトリ入力の基準フレーム名
- `/hsrb/omni_base_controller/wheel_odom_base_frame`  
  - type: `String`  
  - description: ホイールオドメトリ入力のオドメトリフレーム名

---

## 8.1.1.5. 全身協調手先インピーダンス制御

以下の関節で手先のインピーダンス（剛性、粘性）を所望値に制御します。`/odom_*` は `/odom` 基準での仮想関節です。

対象関節:
- `arm_lift_joint`
- `arm_flex_joint`
- `arm_roll_joint`
- `wrist_flex_joint`
- `wrist_roll_joint`
- `odom_x`
- `odom_y`
- `odom_t`

### Provide Actions
- `/hsrb/impedance_control/follow_joint_trajectory`  
  - type: `control_msgs/FollowJointTrajectory`  
  - description: インピーダンス制御で軌道再生を行うアクション。パラメータセットを `/hsrb/impedance_control/select_config` で選択
- `/hsrb/impedance_control/follow_joint_trajectory_with_config`  
  - type: `tmc_manipulation_msgs/FollowJointTrajectory`  
  - description: パラメータセットと軌道を同時に設定してインピーダンス制御で軌道再生

### Provided Services
- `/hsrb/impedance_control/select_config`  
  - type: `tmc_manipulation_msgs/SelectConfig`  
  - description: `/hsrb/impedance_control/follow_joint_trajectory` のためにパラメータを設定するサービス

### Parameters
- `/hsrb/impedance_control/config_names`  
  - type: `String[]`  
  - description: 利用可能なパラメータセット名（例: ["very_flexible", "for_grasping", "stiff"]）

---

## 8.1.1.6. 手先カメラ

`image_transport/ImageTransport` の仕様に準じます。

### Published Topics
- `/hsrb/hand_camera/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: カメラ情報
- `/hsrb/hand_camera/image_raw`  
  - type: `sensor_msgs/Image`  
  - description: "raw"伝送方式による画像

---

## 8.1.1.7. 頭部広角カメラ

`image_transport/ImageTransport` の仕様に準じます。HSRBのみ利用可能。

### Published Topics
- `/hsrb/head_center_camera/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: カメラ情報
- `/hsrb/head_center_camera/image_raw`  
  - type: `sensor_msgs/Image`  
  - description: "raw"伝送方式による画像

---

## 8.1.1.8. 頭部ステレオカメラ（左）

`image_transport/ImageTransport` の仕様に準じます。

### Published Topics
- `/hsrb/head_l_stereo_camera/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: カメラ情報
- `/hsrb/head_l_stereo_camera/image_rect_color`  
  - type: `sensor_msgs/Image`  
  - description: ひずみ補正済みの画像（"raw"伝送方式, rectified color）

---

## 8.1.1.9. 頭部ステレオカメラ（右）

### Published Topics
- `/hsrb/head_r_stereo_camera/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: カメラ情報
- `/hsrb/head_r_stereo_camera/image_rect_color`  
  - type: `sensor_msgs/Image`  
  - description: ひずみ補正済みの画像（"raw"伝送方式, rectified color）

---

## 8.1.1.10. 頭部3次元距離センサ

### Published Topics
- `/hsrb/head_rgbd_sensor/rgb/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: RGBカメラ情報
- `/hsrb/head_rgbd_sensor/rgb/image_raw`  
  - type: `sensor_msgs/Image`  
  - description: RGB画像
- `/hsrb/head_rgbd_sensor/rgb/image_rect_color`  
  - type: `sensor_msgs/Image`  
  - description: 歪み補正されたRGB画像
- `/hsrb/head_rgbd_sensor/depth_registered/camera_info`  
  - type: `sensor_msgs/CameraInfo`  
  - description: RGBカメラ情報
- `/hsrb/head_rgbd_sensor/depth_registered/image`  
  - type: `sensor_msgs/Image`  
  - description: RGBカメラ座標系に投影された深度画像（単位: m, 32FC1）
- `/hsrb/head_rgbd_sensor/depth_registered/image_raw`  
  - type: `sensor_msgs/Image`  
  - description: RGBカメラ座標系に投影された深度画像（単位: mm, 16UC1）
- `/hsrb/head_rgbd_sensor/depth_registered/image_rect_raw`  
  - type: `sensor_msgs/Image`  
  - description: 歪み補正された深度画像（単位: mm, 16UC1）
- `/hsrb/head_rgbd_sensor/depth_registered/rectified_points`  
  - type: `sensor_msgs/PointCloud2`  
  - description: 歪み補正された色付きポイントクラウド

---

## 8.1.1.11. IMU

### Published Topics
- `/hsrb/base_imu/data`  
  - type: `sensor_msgs/Imu`  
  - description: 台車胴部に搭載されたIMUの出力

### Provided Services
- `/hsrb/base_imu/calibrate`  
  - type: `std_srvs/Empty`  
  - description: IMUをキャリブレーションする

---

## 8.1.1.12. レーザースキャナー

### Published Topics
- `/hsrb/base_scan`  
  - type: `sensor_msgs/LaserScan`  
  - description: 台車部レーザースキャナーの出力

---

## 8.1.1.13. 6軸力覚センサー

### Published Topics
- `/hsrb/wrist_wrench/raw`  
  - type: `geometry_msgs/WrenchStamped`  
  - description: 手首の力覚センサーからの出力（力: N、モーメント: Nm）
- `/hsrb/wrist_wrench/compensated`  
  - type: `geometry_msgs/WrenchStamped`  
  - description: 自重補償済みの出力（力: N、モーメント: Nm）
- `/hsrb/wrist_wrench`（廃止）  
  - note: 廃止。`/hsrb/wrist_wrench/raw` を利用してください。

### Provided Services
- `/hsrb/wrist_wrench/readjust_offset`  
  - type: `std_srvs/Empty`  
  - description: 自重補償のオフセットを再設定する（温度による出力変化等をリセット）

### Parameters
- `/hsrb/wrist_wrench/compensation_node/filter_names`  
  - type: `String[]`  
  - description: 出力に作用させるフィルタ名のリスト（順序通りに適用）。例:
    - `tmc_force_torque_sensor_compensation/DeadZoneWithLinearInterpolation`
    - `tmc_force_torque_sensor_compensation/BiQuadLowPassFilter`
- `/hsrb/wrist_wrench/dead_zone/threshold`  
  - type: `Double`  
  - description: 不感帯閾値（N）。DeadZoneWithLinearInterpolation 利用時に有効。閾値以下は `/hsrb/wrist_wrench/compensated` で 0 を出力。
- `/hsrb/wrist_wrench/dead_zone/interpolation_width`  
  - type: `Double`  
  - description: 前後を線形補間する幅（N）。DeadZoneWithLinearInterpolation 利用時に有効。
- `/hsrb/wrist_wrench/compensation_node/biquad_lowpass_filter/cutoff_rate`  
  - type: `Double`  
  - description: ローパスフィルタのカットオフ周波数（力覚センサ取得周期100Hzに対する割合）。BiQuadLowPassFilter 利用時に有効。

---

## 8.1.1.14. 関節状態

### Published Topics
- `/hsrb/joint_states`  
  - type: `sensor_msgs/JointState`  
  - description: 各関節（能動関節のみ）の現在状態
- `/hsrb/robot_state/joint_states`  
  - type: `sensor_msgs/JointState`  
  - description: 受動関節を含むすべての関節状態

### Parameters
- `/hsrb/joint_state_controller/publish_rate`  
  - type: `Double`  
  - description: 各関節の現在状態の発行周期
- `/hsrb/joint_state_controller/type`  
  - type: `String`  
  - description: ControllerManager プラグインとしての型名
- `/hsrb/robot_state/joint_state_pub/source_list`  
  - type: `String[]`  
  - description: 読み出し専用（値は `[/hsrb/joint_states]` で固定）
- `/robot_description`  
  - type: `String`  
  - description: HSR の URDF ロボットモデル

---

## 8.1.1.15. マルチファンクションスイッチ

### Published Topics
- `/hsrb/switch_input`  
  - type: `std_msgs/Bool`  
  - description: マルチファンクションスイッチの On/Off（HSRCのみ利用可能）

### Subscribed Topics
- `/hsrb/switch_led`  
  - type: `std_msgs/Bool`  
  - description: マルチファンクションスイッチの LED の On/Off を切り替える（HSRCのみ利用可能）

---

## 8.1.1.16. デジタルI/O

### Published Topics
- `/hsrb/runstop_button`  
  - type: `std_msgs/Bool`  
  - description: 非常停止ボタンの On/Off
- `/hsrb/base_f_bumper_sensor`  
  - type: `std_msgs/Bool`  
  - description: 前部バンパーセンサーの On/Off
- `/hsrb/base_b_bumper_sensor`  
  - type: `std_msgs/Bool`  
  - description: 後部バンパーセンサーの On/Off
- `/hsrb/pressure_sensor`  
  - type: `std_msgs/Bool`  
  - description: 吸引圧力センサーの On/Off
- `/hsrb/base_magnetic_sensor_1`  
  - type: `std_msgs/Bool`  
  - description: 台車の磁気センサ1の On/Off
- `/hsrb/base_magnetic_sensor_2`  
  - type: `std_msgs/Bool`  
  - description: 台車の磁気センサ2の On/Off

### Subscribed Topics
- `/hsrb/command_suction`  
  - type: `std_msgs/Bool`  
  - description: 吸引機構の On/Off コマンド
- `/hsrb/command_status_led_rgb`  
  - type: `std_msgs/ColorRGBA`  
  - description: 状態表示 LED の色設定（r,g,b は [0.0,1.0]、a は未実装）  
    - HSRB-PHASE4 以前: 有効入力は 8 種類の組合せのみ  
    - HSRB-PHASE5 以降: 256 階調（ファームウェア要更新）

---

## 8.1.1.17. 電源管理

### Published Topics
- `/hsrb/battery_state`  
  - type: `tmc_msgs/BatteryState`  
  - description: バッテリ残量、エラーなど

---

## 8.1.1.18. ControllerManager制御

`controller_manager/ControllerManager` の仕様に準じます。

### Provided Services
- `/hsrb/controller_manager/list_controller_types`  
  - type: `controller_manager_msgs/ListControllerTypes`  
  - description: ロード可能なコントローラを列挙する
- `/hsrb/controller_manager/list_controllers`  
  - type: `controller_manager_msgs/ListControllers`  
  - description: 現在ロードされているコントローラを列挙する
- `/hsrb/controller_manager/load_controller`  
  - type: `controller_manager_msgs/LoadController`  
  - description: 指定したコントローラをロードする
- `/hsrb/controller_manager/reload_controller_libraries`  
  - type: `controller_manager_msgs/ReloadControllerLibraries`  
  - description: コントローラプラグインを再ロードする
- `/hsrb/controller_manager/switch_controller`  
  - type: `controller_manager_msgs/SwitchController`  
  - description: コントローラを切り替える
- `/hsrb/controller_manager/unload_controller`  
  - type: `controller_manager_msgs/UnloadController`  
  - description: コントローラを取り外す

---


