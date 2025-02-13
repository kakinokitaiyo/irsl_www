async function main () {
  try {
    //// button
    const buttonStart = document.querySelector('#buttonStart');
    const buttonStop  = document.querySelector('#buttonStop');
    const audio = document.querySelector('#audio');

    const stream = await navigator.mediaDevices.getUserMedia({
      video: false,
      audio: true,
    });

    const [track]  = stream.getAudioTracks();
    const settings = track.getSettings();

    const audioContext = new AudioContext();
    await audioContext.audioWorklet.addModule('audio-recorder.js');

    const mediaStreamSource = audioContext.createMediaStreamSource(stream);
    const audioRecorder     = new AudioWorkletNode(audioContext, 'audio-recorder');
    const buffers = [];
    //
    audioRecorder.port.addEventListener('message', event => {
      buffers.push(event.data.buffer);
    });
    audioRecorder.port.start();
    //
    mediaStreamSource.connect(audioRecorder);
    audioRecorder.connect(audioContext.destination);
    ////
    buttonStart.addEventListener('click', event => {
      buttonStart.setAttribute('disabled', 'disabled');
      buttonStop.removeAttribute('disabled');

      //// start recording
      const parameter = audioRecorder.parameters.get('isRecording');
      parameter.setValueAtTime(1, audioContext.currentTime);

      buffers.splice(0, buffers.length);
    });

    ////
    buttonStop.addEventListener('click', event => {
      buttonStop.setAttribute('disabled', 'disabled');
      buttonStart.removeAttribute('disabled');

      //// stop recording
      const parameter = audioRecorder.parameters.get('isRecording');
      parameter.setValueAtTime(0, audioContext.currentTime);

      const blob = encodeWav(buffers, settings);
      //const url  = URL.createObjectURL(blob);

      callbackAudioBlob(blob);
      //// sending
      //audio.src = url
    });
  } catch (err) {
    console.error(err);
  }
}

main();
