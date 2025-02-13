function ros_start() {
  // xxx.html?wsport=9999&wsaddr=xxx.com&ssl=0
  const params = new URLSearchParams(window.location.search);
  const wsport = params.get('wsport');
  const wsaddr = params.get('wsaddr');
  const ssl    = params.get('ssl');

  if (!wsport && !wsaddr) {
    console.log('can not start with wsport=' + wsport + ', wsaddr=' + wsaddr);
    return null;
  }
  console.log('start with wsport=' + wsport + ', wsaddr=' + wsaddr);
  let url;
  if ( ssl ) {
    url = 'wss://' + wsaddr + ':' + wsport;
  } else {
    url = 'ws://' + wsaddr + ':' + wsport;
  }
  console.log('connecting to ' + url);
  let ros = new ROSLIB.Ros({
    url : url
  });
  ros.on('connection', function() {
    console.log('Connected to websocket server.');
    let content = document.getElementById("header-contents");
    if (content) {
      content.innerHTML = "<h3>Connected to websocket server : " +  url + "</h3>"
    }
  });
  ros.on('error', function(error) {
    console.log('Error connecting to websocket server: ', error);
    let content = document.getElementById("header-contents");
    if (content) {
      content.innerHTML = '<h3 style="color:red;">Connection Error : ' +  url + '</h3>'
    }
  });
  ros.on('close', function() {
    console.log('Connection to websocket server closed.');
    let content = document.getElementById("header-contents");
    if (content) {
      content.innerHTML = '<h3 style="color:red;">Connection Closed : ' +  url + '</h3>'
    }
  });
  return ros;
};
//ros_start();
