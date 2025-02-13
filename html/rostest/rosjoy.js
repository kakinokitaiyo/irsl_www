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
};

main();
