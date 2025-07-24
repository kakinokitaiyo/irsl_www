//// https://qiita.com/shoichi4411/items/fcbe4b0fc2d98c72b55e
(function() {
  // rosmain.js
  const ros = ros_start();

  let ros_topic00 = new ROSLIB.Topic({
    ros : ros,
    name : '/pubtest',
    messageType : 'std_msgs/String' // ROS1
  });

  var cntr = 0;
  function publish () {
    console.log('publish: ' + cntr)
    var msg = new ROSLIB.Message({ data : 'pubtest' + cntr });
    ros_topic00.publish(msg);
    setTimeout(publish, 1000);
    cntr += 1;
  }

  publish();

})();
