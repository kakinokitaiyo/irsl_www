//// <!-- https://developer.mozilla.org/ja/docs/Web/API/Touch_events -->

////
let brushSize = 4;
let isEraser = false;
let drawingHistory = [];
let historyIndex = 0;

function startup() {
  const el = document.getElementById("canvas");
  el.addEventListener("touchstart",  handleStart);
  el.addEventListener("touchend",    handleEnd);
  el.addEventListener("touchcancel", handleCancel);
  el.addEventListener("touchmove",   handleMove);
  
  // 初期状態（空のキャンバス）を履歴に保存
  drawingHistory.push(el.toDataURL());
  
  // ペンの太さスライダー
  const brushSizeInput = document.getElementById("brushSize");
  const brushSizeDisplay = document.getElementById("brushSizeDisplay");
  brushSizeInput.addEventListener("input", (e) => {
    brushSize = parseInt(e.target.value);
    brushSizeDisplay.textContent = brushSize;
  });
  
  // 消しゴムボタン
  const buttonEraser = document.getElementById("buttonEraser");
  buttonEraser.addEventListener("click", () => {
    isEraser = !isEraser;
    buttonEraser.classList.toggle("active");
  });
  
  // 戻るボタン
  const buttonUndo = document.getElementById("buttonUndo");
  buttonUndo.addEventListener("click", () => {
    if (historyIndex > 0) {
      historyIndex--;
      redrawCanvasAtIndex(historyIndex);
    }
  });
  
  // 進むボタン
  const buttonRedo = document.getElementById("buttonRedo");
  buttonRedo.addEventListener("click", () => {
    if (historyIndex < drawingHistory.length - 1) {
      historyIndex++;
      redrawCanvasAtIndex(historyIndex);
    }
  });
  
  // クリアボタン
  const buttonClear = document.getElementById("buttonClear");
  buttonClear.addEventListener("click", () => {
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 履歴をリセット（クリア前の履歴は全て削除）
    drawingHistory = [canvas.toDataURL()];
    historyIndex = 0;
  });
  
  log("Initialized.");
}

const ongoingTouches = [];

function handleStart(evt) {
  evt.preventDefault();
  log("touchstart.");
  const el = document.getElementById("canvas");
  const ctx = el.getContext("2d");
  const touches = evt.changedTouches;

  for (let i = 0; i < touches.length; i++) {
    log(`touchstart: ${i}.`);
    ongoingTouches.push(copyTouch(touches[i]));
    const color = colorForTouch(touches[i]);
    log(`color of touch with id ${touches[i].identifier} = ${color}`);
    ctx.beginPath();
    ctx.arc(touches[i].pageX, touches[i].pageY, brushSize / 2, 0, 2 * Math.PI, false);
    if (isEraser) {
      ctx.clearRect(touches[i].pageX - brushSize / 2, touches[i].pageY - brushSize / 2, brushSize, brushSize);
    } else {
      ctx.fillStyle = color;
      ctx.fill();
    }
  }
}

function handleMove(evt) {
  evt.preventDefault();
  const el = document.getElementById("canvas");
  const ctx = el.getContext("2d");
  const touches = evt.changedTouches;

  for (let i = 0; i < touches.length; i++) {
    const color = colorForTouch(touches[i]);
    const idx = ongoingTouchIndexById(touches[i].identifier);

    if (idx >= 0) {
      log(`continuing touch ${idx}`);
      ctx.beginPath();
      log(
        `ctx.moveTo( ${ongoingTouches[idx].pageX}, ${ongoingTouches[idx].pageY} );`,
      );
      ctx.moveTo(ongoingTouches[idx].pageX, ongoingTouches[idx].pageY);
      log(`ctx.lineTo( ${touches[i].pageX}, ${touches[i].pageY} );`);
      ctx.lineTo(touches[i].pageX, touches[i].pageY);
      ctx.lineWidth = brushSize;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (isEraser) {
        ctx.clearRect(touches[i].pageX - brushSize / 2, touches[i].pageY - brushSize / 2, brushSize, brushSize);
      } else {
        ctx.strokeStyle = color;
        ctx.stroke();
      }

      ongoingTouches.splice(idx, 1, copyTouch(touches[i])); // swap in the new touch record
    } else {
      log("can't figure out which touch to continue");
    }
  }
}

function handleEnd(evt) {
  evt.preventDefault();
  log("touchend");
  const el = document.getElementById("canvas");
  const ctx = el.getContext("2d");
  const touches = evt.changedTouches;

  for (let i = 0; i < touches.length; i++) {
    const color = colorForTouch(touches[i]);
    let idx = ongoingTouchIndexById(touches[i].identifier);

    if (idx >= 0) {
      ctx.lineWidth = brushSize;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(ongoingTouches[idx].pageX, ongoingTouches[idx].pageY);
      ctx.lineTo(touches[i].pageX, touches[i].pageY);
      ctx.fillRect(touches[i].pageX - brushSize / 2, touches[i].pageY - brushSize / 2, brushSize, brushSize);
      ongoingTouches.splice(idx, 1); // remove it; we're done
    } else {
      log("can't figure out which touch to end");
    }
  }
  
  // 描画状態を履歴に保存
  const el2 = document.getElementById("canvas");
  if (historyIndex < drawingHistory.length - 1) {
    // 戻った後に新しく描画した場合は、未来の履歴を削除
    drawingHistory = drawingHistory.slice(0, historyIndex + 1);
  }
  historyIndex = drawingHistory.length;
  drawingHistory.push(el2.toDataURL());
}

function handleCancel(evt) {
  evt.preventDefault();
  log("touchcancel.");
  const touches = evt.changedTouches;

  for (let i = 0; i < touches.length; i++) {
    let idx = ongoingTouchIndexById(touches[i].identifier);
    ongoingTouches.splice(idx, 1); // remove it; we're done
  }
}

function redrawCanvasAtIndex(index) {
  const el = document.getElementById("canvas");
  const ctx = el.getContext("2d");
  ctx.clearRect(0, 0, el.width, el.height);
  
  if (index >= 0 && index < drawingHistory.length) {
    const img = new Image();
    img.src = drawingHistory[index];
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
    };
  }
}

function redrawCanvas() {
  const el = document.getElementById("canvas");
  const ctx = el.getContext("2d");
  ctx.clearRect(0, 0, el.width, el.height);
  
  if (drawingHistory.length > 0) {
    const img = new Image();
    img.src = drawingHistory[drawingHistory.length - 1];
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
    };
  }
}

function colorForTouch(touch) {
  let r = touch.identifier % 16;
  let g = Math.floor(touch.identifier / 3) % 16;
  let b = Math.floor(touch.identifier / 7) % 16;
  r = r.toString(16); // make it a hex digit
  g = g.toString(16); // make it a hex digit
  b = b.toString(16); // make it a hex digit
  const color = `#${r}${g}${b}`;
  return color;
}

function copyTouch({ identifier, pageX, pageY }) {
  return { identifier, pageX, pageY };
}

function ongoingTouchIndexById(idToFind) {
  for (let i = 0; i < ongoingTouches.length; i++) {
    const id = ongoingTouches[i].identifier;

    if (id === idToFind) {
      return i;
    }
  }
  return -1; // 見つからない
}

function log(msg) {
  // no log
  //const log_container = document.getElementById("log");
  //if (log_container) {
  //  container.textContent = `${msg} \n${container.textContent}`;
  //}
}

////
document.addEventListener("DOMContentLoaded", startup);
