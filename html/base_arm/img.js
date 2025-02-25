////
const base_img_listener = new ROSLIB.Topic({
  ros : ros,
  name : '/base_camera/image_raw/compressed',
  // messageType : 'std_msgs/msg/String' ROS2
  messageType : 'sensor_msgs/CompressedImage' // ROS1
});
const arm_img_listener = new ROSLIB.Topic({
  ros : ros,
  name : '/arm_camera/image_raw/compressed',
  // messageType : 'std_msgs/msg/String' ROS2
  messageType : 'sensor_msgs/CompressedImage' // ROS1
});
const hand_img_listener = new ROSLIB.Topic({
  ros : ros,
  name : '/hand_camera/image_raw/compressed',
  // messageType : 'std_msgs/msg/String' ROS2
  messageType : 'sensor_msgs/CompressedImage' // ROS1
});

////
var current_unsubscribe = undefined;

function ros_base_img_subscribe() {
  if (current_unsubscribe) {
    current_unsubscribe();
  }
  current_unsubscribe = ros_base_img_unsubscribe;
  base_img_listener.subscribe( msg => {
    //console.log('get base-img ');
    let content = document.getElementById("rosimg");
    content.src = "data:image/jpeg;base64," + msg.data;
  });
};
function ros_base_img_unsubscribe() {
  console.log('unsubscribe:base')
  base_img_listener.unsubscribe();
};
function ros_arm_img_subscribe() {
  if (current_unsubscribe) {
    current_unsubscribe();
  }
  current_unsubscribe = ros_arm_img_unsubscribe;
  arm_img_listener.subscribe( msg => {
    //console.log('get arm-img ');
    let content = document.getElementById("rosimg");
    content.src = "data:image/jpeg;base64," + msg.data;
  });
};
function ros_arm_img_unsubscribe() {
  console.log('unsubscribe:arm')
  arm_img_listener.unsubscribe();
};
function ros_hand_img_subscribe() {
  if (current_unsubscribe) {
    current_unsubscribe();
  }
  current_unsubscribe = ros_hand_img_unsubscribe;
  hand_img_listener.subscribe( msg => {
    //console.log('get hand-img ');
    let content = document.getElementById("rosimg");
    content.src = "data:image/jpeg;base64," + msg.data;
  });
};
function ros_hand_img_unsubscribe() {
  console.log('unsubscribe:hand')
  hand_img_listener.unsubscribe();
};

ros_base_img_subscribe();
