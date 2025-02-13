//// https://qiita.com/shoichi4411/items/fcbe4b0fc2d98c72b55e
(function() {
    let ros = new ROSLIB.Ros({
      // url : 'ws://simserver.irsl.eiiris.tut.ac.jp:9090'
      url : 'wss://simserver.irsl.eiiris.tut.ac.jp:9990'
    });

    ros.on('connection', function() {
        console.log('Connected to websocket server.');
    });
    ros.on('error', function(error) {
        console.log('Error connecting to websocket server: ', error);
    });
    ros.on('close', function() {
        console.log('Connection to websocket server closed.');
    });

    let ros_topic00 = new ROSLIB.Topic({
        ros : ros,
        name : '/pubtest',
        messageType : 'std_msgs/String' // ROS1
    });

  var msg = new RORLIB.Message({ data : '' });
  ros_topic00.publish(msg);

})();
