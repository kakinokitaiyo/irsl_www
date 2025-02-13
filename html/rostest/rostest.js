//// https://qiita.com/shoichi4411/items/fcbe4b0fc2d98c72b55e
function main() {
  // rosmain.js
  const ros = ros_start();

  let webtest_listener = new ROSLIB.Topic({
    ros : ros,
    name : '/webtest',
    // messageType : 'std_msgs/msg/String' ROS2
    messageType : 'std_msgs/String' // ROS1
  });

  function ros_webtest_topic_subscribe() {
    webtest_listener.subscribe( msg => {
      console.log(msg);
      let content = document.getElementById("main-contents");
      content.innerHTML += msg.data;
      content.innerHTML += "<br>"
    });
  }
  ros_webtest_topic_subscribe();
};

main();
