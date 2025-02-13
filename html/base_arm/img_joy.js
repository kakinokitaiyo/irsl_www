//// https://qiita.com/shoichi4411/items/fcbe4b0fc2d98c72b55e
function main() {
  // rosmain.js
  const ros = ros_start();

  let joytopic = new ROSLIB.Topic({
    ros : ros,
    name : '/webjoy',
    messageType : 'sensor_msgs/Joy' // ROS1
  });
  ////
  var update_count = 0;
  var prev_stamp = 0;

  function update_pads() {
    //var rAF = window.requestAnimationFrame;
    var pads = navigator.getGamepads ? navigator.getGamepads() :
        (navigator.webkitGetGamepads ? navigator.webkitGetGamepads : []);
    // use first gamepad...
    pads = pads[0];
    var btn  = [];
    var axes = [];
    var update_flag = false;
    if (pads) {
      var stamp = pads.timestamp;
      if (stamp > prev_stamp) {
        update_flag = true;
        for (var i = 0; i < pads.buttons.length; i++) {
          var val = pads.buttons[i];
          var pressed = val == 1.0;
          if (typeof (val) == "object") {
            pressed = val.pressed;
            val = val.value;
          }
          btn[i] = val;
        }
        axes = pads.axes;
      }
      prev_stamp = stamp;
    }
    if (update_flag) {
      var frame_str = "webjoy"
      var msg = new ROSLIB.Message({
        header: { frame_id: frame_str },
        axes: axes,
        buttons: btn
      });
      joytopic.publish(msg);
    }
    update_count += 1;
    window.requestAnimationFrame(update_pads);
  }

  window.requestAnimationFrame(update_pads);

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
  function ros_base_img_subscribe() {
    base_img_listener.subscribe( msg => {
      console.log('get base-img ');
      let content = document.getElementById("base-img");
      content.src = "data:image/jpeg;base64," + msg.data;
    });
  }
  function ros_base_img_unsbscribe() {
    ////
  }
  function ros_arm_img_subscribe() {
    arm_img_listener.subscribe( msg => {
      console.log('get arm-img ');
      let content = document.getElementById("arm-img");
      content.src = "data:image/jpeg;base64," + msg.data;
    });
  }
  function ros_arm_img_unsbscribe() {
  }
  function ros_hand_img_subscribe() {
    hand_img_listener.subscribe( msg => {
      console.log('get hand-img ');
      let content = document.getElementById("hand-img");
      content.src = "data:image/jpeg;base64," + msg.data;
    });
  }
  function ros_hand_img_unsbscribe() {
  }
  ros_base_img_subscribe();

};

main();
