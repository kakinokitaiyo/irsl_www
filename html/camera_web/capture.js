(function() {
  // The width and height of the captured photo. We will set the
  // width to the value defined here, but the height will be
  // calculated based on the aspect ratio of the input stream.

  //var width = 320;    // We will scale the photo width to this
  var width = 640;    // We will scale the photo width to this
  var height = 0;     // This will be computed based on the input stream

  // |streaming| indicates whether or not we're currently streaming
  // video from the camera. Obviously, we start at false.

  var streaming = false;

  // The various HTML elements we need to configure or control. These
  // will be set by the startup() function.

  var video = null;
  var canvas = null;
  var photo = null;
  var startbutton = null;
  // xxxx.html?host=localhost&port=9999
  const url = new URL(window.location);
  const params = url.searchParams;
  const wshost = (() => {
    let res = params.get('host');
    if (res) {
      return res;
    } else {
      return 'localhost';
    }
  })();
  const wsport = (() => {
    let res = params.get('port');
    if (res) {
      return res;
    } else {
      return '5001';
    }
  })();

  const addr = 'ws://' + wshost + ':' + wsport;
  console.log('server address: ' + addr);

  var ws_client = null;
  function ws_connect() {
    ws_client = new WebSocket(addr);
    //// 接続
    ws_client.onopen = (e) => {
      console.log('Socket 接続成功');
      //document.getElementById("console_text").innerHTML="";
      //document.getElementById("message_text").innerHTML="Socket is connected.";
    };
    ws_client.onerror = (e) => {
      console.log('Socket error');
      console.log(e)
    };
    // サーバーからデータを受け取る
    ws_client.onmessage = (e) => {
      console.log('recv message');
      console.log(e.data);
      //document.getElementById("console_text").innerHTML='message received: ' + e.data;
    };
  };

  function startup() {
    video  = document.getElementById('video');
    canvas = document.getElementById('canvas');
    photo  = document.getElementById('photo');
    startbutton = document.getElementById('startbutton');

    navigator.mediaDevices.getUserMedia({video: true, audio: false})
    .then(function(stream) {
      video.srcObject = stream;
      video.play();
    })
    .catch(function(err) {
      console.log("An error occurred: " + err);
    });

    video.addEventListener('canplay', function(ev){
      if (!streaming) {
        console.log("v_height: " + video.videoHeight)
        console.log("v_width: " + video.videoWidth)
        height = video.videoHeight / (video.videoWidth/width);
        // Firefox currently has a bug where the height can't be read from
        // the video, so we will make assumptions if this happens.
        if (isNaN(height)) {
          height = width / (4/3);
        }
        video.setAttribute('width', width);
        video.setAttribute('height', height);
        canvas.setAttribute('width', width);
        canvas.setAttribute('height', height);
        streaming = true;
      }
    }, false);

    startbutton.addEventListener('click', function(ev){
      takepicture();
      ev.preventDefault();
    }, false);

    ws_connect();//// websocket
    clearphoto();
  }

  // Fill the photo with an indication that none has been
  // captured.

  function clearphoto() {
    var context = canvas.getContext('2d');
    context.fillStyle = "#AAA";
    context.fillRect(0, 0, canvas.width, canvas.height);

    var data = canvas.toDataURL('image/png');
    photo.setAttribute('src', data);
  }
  // Capture a photo by fetching the current contents of the video
  // and drawing it into a canvas, then converting that to a PNG
  // format data URL. By drawing it on an offscreen canvas and then
  // drawing that to the screen, we can change its size and/or apply
  // other changes before drawing it.
  function takepicture() {
    var context = canvas.getContext('2d');
    if (width && height) {
      canvas.width  = width;
      canvas.height = height;
      context.drawImage(video, 0, 0, width, height);
      console.log('data conv')
      var data = canvas.toDataURL('image/png');
      //// sending data
      ws_client.send(data);
      console.log('data sent')
      photo.setAttribute('src', data);
    } else {
      clearphoto();
    }
  }
  // Set up our event listener to run the startup process
  // once loading is complete.
  window.addEventListener('load', startup, false);
})();
