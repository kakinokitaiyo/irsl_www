function encodeWav (buffers, settings) {
  const sampleCount = buffers.reduce((memo, buffer) => {
    return memo + buffer.length
  }, 0);
  //
  const bytesPerSample = settings.sampleSize / 8;
  const bitsPerByte    = 8;
  const dataLength     = sampleCount * bytesPerSample;
  const sampleRate     = settings.sampleRate;
  //
  const arrayBuffer = new ArrayBuffer(44 + dataLength);
  const dataView    = new DataView(arrayBuffer);
  //
  dataView.setUint8(0, 'R'.charCodeAt(0));
  dataView.setUint8(1, 'I'.charCodeAt(0));
  dataView.setUint8(2, 'F'.charCodeAt(0));
  dataView.setUint8(3, 'F'.charCodeAt(0));
  dataView.setUint32(4, 36 + dataLength, true);
  dataView.setUint8(8, 'W'.charCodeAt(0));
  dataView.setUint8(9, 'A'.charCodeAt(0));
  dataView.setUint8(10, 'V'.charCodeAt(0));
  dataView.setUint8(11, 'E'.charCodeAt(0));
  dataView.setUint8(12, 'f'.charCodeAt(0));
  dataView.setUint8(13, 'm'.charCodeAt(0));
  dataView.setUint8(14, 't'.charCodeAt(0));
  dataView.setUint8(15, ' '.charCodeAt(0));
  dataView.setUint32(16, 16, true);
  dataView.setUint16(20, 1, true);
  dataView.setUint16(22, 1, true);
  dataView.setUint32(24, sampleRate, true);
  dataView.setUint32(28, sampleRate * 2, true);
  dataView.setUint16(32, bytesPerSample, true);
  dataView.setUint16(34, bitsPerByte * bytesPerSample, true);
  dataView.setUint8(36, 'd'.charCodeAt(0));
  dataView.setUint8(37, 'a'.charCodeAt(0));
  dataView.setUint8(38, 't'.charCodeAt(0));
  dataView.setUint8(39, 'a'.charCodeAt(0));
  dataView.setUint32(40, dataLength, true);
  //
  let index = 44;
  for (const buffer of buffers) {
    for (const value of buffer) {
      dataView.setInt16(index, value * 0x7fff, true);
      index += 2;
    }
  }
  //
  return new Blob([dataView], {type: 'audio/wav'});
}

async function convertBlobToDataURL (blob) {
  return await new Promise((resolve, reject) => {
    const fileReader = new FileReader();
    const sub = () => {
      fileReader.addEventListener('abort', on_ab);
      fileReader.addEventListener('error', on_er);
      fileReader.addEventListener('load',  on_load);
    };
    const unsub = () => {
      fileReader.removeEventListener('abort', on_ab);
      fileReader.removeEventListener('error', on_er);
      fileReader.removeEventListener('load',  on_load);
    };
    const on_ab = () => { unsub(); reject(new Error('abort')); }
    const on_er = (ev) => { unsub(); reject(event.target.error); }
    const on_load = (ev) => { unsub(); resolve(event.target.result); }
    sub(); fileReader.readAsDataURL(blob);
  });
}
