/**
 * WebRTC measurement page: PeerJS DataChannel client for the aiortc echo peer.
 */

import { Peer } from "https://esm.sh/peerjs@1.5.4";
import { parseServerMessage, splitFrame } from "./frame_codec.js";

const WIDTH = 640;
const HEIGHT = 480;
const MIN_FRAME_INTERVAL_MS = 1000 / 30;
const ECHO_TIMEOUT_MS = 2000;
const RUN_DRAIN_MS = 2000;
const RUN_ID_RE = /^[A-Za-z0-9_-]{1,64}$/;

const MATRIX = [];
for (const quality of [0.6, 0.8]) {
  for (const inFlight of [1, 2]) {
    for (const chunkBytes of [16_384, 61_440]) {
      MATRIX.push({
        mode: "synthetic",
        quality,
        in_flight: inFlight,
        chunk_bytes: chunkBytes,
      });
    }
  }
}
const PROBE = {
  mode: "synthetic",
  quality: 0.8,
  in_flight: 1,
  chunk_bytes: 0,
  probe: true,
};

/** @type {import("https://esm.sh/peerjs@1.5.4").Peer | null} */
let peer = null;
/** @type {import("https://esm.sh/peerjs@1.5.4").DataConnection | null} */
let conn = null;
let connectMs = null;
let iceInfo = { local_type: "", remote_type: "", protocol: "" };

const state = {
  signaling: "idle",
  connection: "closed",
  running: false,
  runSummaries: [],
};

const ui = {
  signaling: document.getElementById("signaling-state"),
  connection: document.getElementById("connection-state"),
  ice: document.getElementById("ice-state"),
  fps: document.getElementById("fps-live"),
  rttMedian: document.getElementById("rtt-median"),
  counters: document.getElementById("frame-counters"),
  summaryBody: document.querySelector("#summary-table tbody"),
  log: document.getElementById("error-log"),
  btnMatrix: document.getElementById("btn-matrix"),
  btnSingle: document.getElementById("btn-single"),
  cameraMode: document.getElementById("mode-camera"),
  cameraNote: document.getElementById("camera-note"),
  formMode: document.getElementById("form-mode"),
  formQuality: document.getElementById("form-quality"),
  formInFlight: document.getElementById("form-in-flight"),
  formChunk: document.getElementById("form-chunk-bytes"),
};

const canvas = document.createElement("canvas");
canvas.width = WIDTH;
canvas.height = HEIGHT;
const ctx = canvas.getContext("2d", { willReadFrequently: true });

let cameraStream = null;
let animPhase = 0;
let runIndex = 0;
let liveRtts = [];
let fpsWindow = { frames: 0, windowStart: performance.now() };
let sentTotal = 0;
let echoedTotal = 0;

/**
 * Read hash parameters from the location bar.
 *
 * @returns {object} Parsed configuration.
 */
function parseHashParams() {
  const raw = location.hash.startsWith("#") ? location.hash.slice(1) : location.hash;
  const params = new URLSearchParams(raw);
  const peerId = params.get("peer");
  if (!peerId) {
    throw new Error("Missing required hash parameter: peer");
  }
  return {
    peerId,
    host: params.get("host") ?? undefined,
    port: params.get("port") ? Number(params.get("port")) : undefined,
    path: params.get("path") ?? undefined,
    key: params.get("key") ?? undefined,
    duration: params.get("duration") ? Number(params.get("duration")) : 20,
  };
}

/**
 * @param {string} runId
 */
function assertRunId(runId) {
  if (!RUN_ID_RE.test(runId)) {
    throw new Error(`invalid run_id: ${runId}`);
  }
}

/**
 * @returns {string} `r<YYYYMMDDTHHMMSS>-<NN>`
 */
function makeRunId() {
  runIndex += 1;
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const stamp =
    String(d.getFullYear()) +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    "T" +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds());
  const suffix = String(runIndex).padStart(2, "0");
  const runId = `r${stamp}-${suffix}`;
  assertRunId(runId);
  return runId;
}

function logError(message) {
  const line = document.createElement("div");
  line.className = "log-line";
  line.textContent = `[${new Date().toISOString()}] ${message}`;
  ui.log.prepend(line);
}

function setSignaling(text) {
  state.signaling = text;
  ui.signaling.textContent = text;
}

function setConnection(text) {
  state.connection = text;
  ui.connection.textContent = text;
}

function updateIceDisplay() {
  ui.ice.textContent = `${iceInfo.local_type || "?"}/${iceInfo.remote_type || "?"} ${iceInfo.protocol || ""}`.trim();
}

function updateCounters() {
  ui.counters.textContent = `sent ${sentTotal} / echoed ${echoedTotal}`;
}

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

function tickFps() {
  const now = performance.now();
  const elapsed = now - fpsWindow.windowStart;
  if (elapsed >= 1000) {
    const fps = (fpsWindow.frames * 1000) / elapsed;
    ui.fps.textContent = fps.toFixed(1);
    fpsWindow.frames = 0;
    fpsWindow.windowStart = now;
  }
}

/**
 * Draw a synthetic 640×480 frame with motion and JPEG-friendly entropy.
 *
 * @param {number} frameId
 */
function drawSynthetic(frameId) {
  animPhase += 0.03;
  const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT);
  gradient.addColorStop(0, `hsl(${(animPhase * 40) % 360}, 70%, 45%)`);
  gradient.addColorStop(1, `hsl(${(animPhase * 40 + 120) % 360}, 70%, 55%)`);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  for (let i = 0; i < 20; i += 1) {
    const x = ((frameId * 3 + i * 47 + animPhase * 80) % (WIDTH - 60));
    const y = ((frameId * 5 + i * 29 + animPhase * 50) % (HEIGHT - 40));
    ctx.fillStyle = `hsl(${(i * 37 + frameId) % 360}, 80%, 60%)`;
    ctx.fillRect(x, y, 48, 32);
  }

  ctx.fillStyle = "#fff";
  ctx.font = "20px monospace";
  ctx.fillText(`frame ${frameId}`, 12, 28);
  ctx.fillText(new Date().toISOString(), 12, 52);

  const nx = 480;
  const ny = 340;
  for (let y = 0; y < 120; y += 4) {
    for (let x = 0; x < 160; x += 4) {
      const v = ((frameId + x + y) * 17) % 256;
      ctx.fillStyle = `rgb(${v}, ${255 - v}, ${(v * 3) % 256})`;
      ctx.fillRect(nx + x, ny + y, 4, 4);
    }
  }
}

/**
 * @param {"synthetic"|"camera"} mode
 * @param {number} frameId
 */
function renderFrame(mode, frameId) {
  if (mode === "camera" && cameraStream) {
    const track = cameraStream.getVideoTracks()[0];
    const settings = track.getSettings();
    const video = document.createElement("video");
    video.srcObject = cameraStream;
    video.muted = true;
    video.playsInline = true;
    return new Promise((resolve, reject) => {
      video.onloadeddata = () => {
        video.play().then(() => {
          ctx.drawImage(video, 0, 0, WIDTH, HEIGHT);
          video.srcObject = null;
          resolve();
        }).catch(reject);
      };
      video.onerror = () => reject(new Error("video frame failed"));
      void settings;
    });
  }
  drawSynthetic(frameId);
  return Promise.resolve();
}

/**
 * @param {number} quality JPEG quality 0..1
 * @returns {Promise<Uint8Array>}
 */
function canvasToJpeg(quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("toBlob failed"));
          return;
        }
        blob.arrayBuffer().then((buf) => resolve(new Uint8Array(buf))).catch(reject);
      },
      "image/jpeg",
      quality,
    );
  });
}

/**
 * @param {RTCPeerConnection} pc
 */
async function readIceTypes(pc) {
  const stats = await pc.getStats();
  let selectedId = null;
  for (const report of stats.values()) {
    if (report.type === "transport" && report.selectedCandidatePairId) {
      selectedId = report.selectedCandidatePairId;
      break;
    }
  }
  let pair = null;
  if (selectedId) {
    pair = stats.get(selectedId);
  }
  if (!pair) {
    for (const report of stats.values()) {
      if (report.type === "candidate-pair" && report.nominated && report.state === "succeeded") {
        pair = report;
        break;
      }
    }
  }
  if (!pair) {
    return { local_type: "unknown", remote_type: "unknown", protocol: "" };
  }
  const local = stats.get(pair.localCandidateId);
  const remote = stats.get(pair.remoteCandidateId);
  return {
    local_type: local?.candidateType ?? "unknown",
    remote_type: remote?.candidateType ?? "unknown",
    protocol: (local?.protocol ?? remote?.protocol ?? "").toLowerCase(),
  };
}

/**
 * @param {object} message Serializable JSON object.
 */
function sendJson(message) {
  if (!conn?.open) {
    throw new Error("connection not open");
  }
  conn.send(JSON.stringify(message));
}

/**
 * @param {Uint8Array} data
 */
function sendBinary(data) {
  if (!conn?.open) {
    throw new Error("connection not open");
  }
  conn.send(data);
}

/**
 * @param {object} row Summary row for the results table.
 */
function appendSummaryRow(row) {
  state.runSummaries.push(row);
  const tr = document.createElement("tr");
  if (row.error) {
    tr.className = "row-error";
  }
  const cells = [
    row.run_id,
    row.mode,
    row.quality,
    row.in_flight,
    row.chunk_bytes,
    row.frames_sent,
    row.frames_echoed,
    row.median_rtt_ms?.toFixed(1) ?? "—",
    row.connect_ms?.toFixed(0) ?? "—",
    row.ice,
    row.status,
  ];
  for (const text of cells) {
    const td = document.createElement("td");
    td.textContent = String(text);
    tr.appendChild(td);
  }
  ui.summaryBody.appendChild(tr);
}

/**
 * Run one measurement configuration.
 *
 * @param {object} cfg
 */
async function runOnce(cfg) {
  const durationS = cfg.duration_s ?? hashParams.duration;
  const runId = makeRunId();
  const inFlight = cfg.in_flight;
  const chunkBytes = cfg.chunk_bytes;
  const quality = cfg.quality;
  const mode = cfg.mode;

  let framesSent = 0;
  let framesEchoed = 0;
  const pending = new Map();
  const runRtts = [];
  let runConnectMs = connectMs;
  let runIce = `${iceInfo.local_type}/${iceInfo.remote_type} ${iceInfo.protocol}`.trim();
  let runError = null;
  let runStatus = "ok";

  const onData = (data) => {
    if (typeof data !== "string") {
      return;
    }
    let msg;
    try {
      msg = parseServerMessage(data);
    } catch (err) {
      logError(`parse error: ${err.message}`);
      return;
    }
    if (msg.t === "error") {
      logError(`server error: ${msg.reason}`);
      return;
    }
    if (msg.t !== "echo") {
      return;
    }
    const key = `${msg.run_id}:${msg.frame_id}`;
    const sentAt = pending.get(key);
    if (sentAt === undefined) {
      return;
    }
    pending.delete(key);
    const rtt = performance.now() - sentAt;
    runRtts.push(rtt);
    liveRtts.push(rtt);
    if (liveRtts.length > 120) {
      liveRtts.shift();
    }
    ui.rttMedian.textContent = median(liveRtts).toFixed(1);
    framesEchoed += 1;
    echoedTotal += 1;
    updateCounters();
    fpsWindow.frames += 1;
    tickFps();
    try {
      sendJson({ t: "rtt", run_id: msg.run_id, frame_id: msg.frame_id, rtt_ms: rtt });
    } catch (err) {
      logError(`rtt send failed: ${err.message}`);
    }
  };

  conn.on("data", onData);

  const pc = conn.peerConnection;
  if (pc) {
    runIce = Object.values(await readIceTypes(pc))
      .filter(Boolean)
      .join("/");
    iceInfo = await readIceTypes(pc);
    updateIceDisplay();
  }

  sendJson({
    t: "run_start",
    run_id: runId,
    config: {
      mode,
      width: WIDTH,
      height: HEIGHT,
      quality,
      in_flight: inFlight,
      chunk_bytes: chunkBytes,
      duration_s: durationS,
    },
    device_ua: navigator.userAgent,
    connect_ms: runConnectMs,
    ice: {
      local_type: iceInfo.local_type,
      remote_type: iceInfo.remote_type,
      protocol: iceInfo.protocol,
    },
  });

  const endAt = performance.now() + durationS * 1000;
  let frameId = 0;
  let lastSendAt = 0;

  /**
   * Drop frames that never received an echo within the spike timeout.
   */
  const pruneLostFrames = () => {
    const now = performance.now();
    for (const [key, sentAt] of pending.entries()) {
      if (now - sentAt > ECHO_TIMEOUT_MS) {
        pending.delete(key);
      }
    }
  };

  while (performance.now() < endAt && conn.open) {
    pruneLostFrames();
    const now = performance.now();
    if (pending.size >= inFlight) {
      await sleep(5);
      continue;
    }
    if (now - lastSendAt < MIN_FRAME_INTERVAL_MS) {
      await sleep(5);
      continue;
    }
    await renderFrame(mode, frameId);
    let jpeg;
    try {
      jpeg = await canvasToJpeg(quality);
    } catch (err) {
      logError(`jpeg encode failed: ${err.message}`);
      break;
    }
    const chunks = splitFrame({ runId, frameId, jpeg, chunkBytes });
    const firstPartAt = performance.now();
    try {
      for (const chunk of chunks) {
        sendBinary(chunk);
      }
    } catch (err) {
      runError = err.message;
      runStatus = cfg.probe ? "probe_failed" : "send_failed";
      logError(`send failed: ${err.message}`);
      break;
    }
    pending.set(`${runId}:${frameId}`, firstPartAt);
    framesSent += 1;
    sentTotal += 1;
    updateCounters();
    frameId += 1;
    lastSendAt = now;
    await sleep(1);
  }

  const drainUntil = performance.now() + RUN_DRAIN_MS;
  while (performance.now() < drainUntil && pending.size > 0 && conn.open) {
    await sleep(20);
  }

  if (conn.open) {
    try {
      sendJson({
        t: "run_end",
        run_id: runId,
        frames_sent: framesSent,
        frames_echoed: framesEchoed,
      });
    } catch (err) {
      if (!runError) {
        runError = err.message;
        runStatus = "run_end_failed";
      }
      logError(`run_end failed: ${err.message}`);
    }
  } else if (!runError) {
    runError = "connection closed";
    runStatus = cfg.probe ? "probe_closed" : "closed";
  }

  conn.off("data", onData);

  appendSummaryRow({
    run_id: runId,
    mode,
    quality,
    in_flight: inFlight,
    chunk_bytes: chunkBytes,
    frames_sent: framesSent,
    frames_echoed: framesEchoed,
    median_rtt_ms: median(runRtts),
    connect_ms: runConnectMs,
    ice: runIce,
    status: runError ? `${runStatus}: ${runError}` : runStatus,
    error: Boolean(runError),
  });

  return { ok: !runError || cfg.probe, runError };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Ensure a live DataConnection to the Python peer.
 */
async function ensureConnection() {
  if (conn?.open) {
    return;
  }
  setConnection("connecting");
  const opts = {
    host: hashParams.host,
    port: hashParams.port,
    path: hashParams.path,
    key: hashParams.key,
    debug: 1,
  };
  Object.keys(opts).forEach((k) => opts[k] === undefined && delete opts[k]);

  peer = new Peer(opts);
  peer.on("error", (err) => {
    logError(`peer error: ${err.type || err.message}`);
    setSignaling("error");
  });
  peer.on("disconnected", () => setSignaling("disconnected"));
  peer.on("close", () => setSignaling("closed"));

  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("peer open timeout")), 30_000);
    peer.once("open", () => {
      clearTimeout(timeout);
      setSignaling("open");
      resolve();
    });
    peer.once("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });

  const connectStarted = performance.now();
  conn = peer.connect(hashParams.peerId, {
    reliable: true,
    serialization: "raw",
  });

  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("data connection timeout")), 45_000);
    conn.once("open", () => {
      clearTimeout(timeout);
      if (conn.dataChannel) {
        conn.dataChannel.binaryType = "arraybuffer";
      }
      connectMs = performance.now() - connectStarted;
      setConnection("open");
      resolve();
    });
    conn.once("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });
    conn.once("close", () => setConnection("closed"));
  });

  const pc = conn.peerConnection;
  if (pc) {
    iceInfo = await readIceTypes(pc);
    updateIceDisplay();
    pc.addEventListener("connectionstatechange", async () => {
      setConnection(pc.connectionState);
      if (pc.connectionState === "connected") {
        iceInfo = await readIceTypes(pc);
        updateIceDisplay();
      }
    });
  }
}

async function runMatrix() {
  if (state.running) return;
  state.running = true;
  ui.btnMatrix.disabled = true;
  ui.btnSingle.disabled = true;
  try {
    await ensureConnection();
    for (const cfg of MATRIX) {
      if (!conn?.open) {
        await ensureConnection();
      }
      await runOnce({ ...cfg, duration_s: hashParams.duration });
    }
    if (!conn?.open) {
      try {
        await ensureConnection();
      } catch (err) {
        appendSummaryRow({
          run_id: "probe",
          mode: PROBE.mode,
          quality: PROBE.quality,
          in_flight: PROBE.in_flight,
          chunk_bytes: 0,
          frames_sent: 0,
          frames_echoed: 0,
          median_rtt_ms: 0,
          connect_ms: connectMs,
          ice: ui.ice.textContent,
          status: `probe_skipped: ${err.message}`,
          error: true,
        });
        return;
      }
    }
    await runOnce({ ...PROBE, duration_s: hashParams.duration });
  } catch (err) {
    logError(`matrix aborted: ${err.message}`);
  } finally {
    state.running = false;
    ui.btnMatrix.disabled = false;
    ui.btnSingle.disabled = false;
  }
}

async function runSingle() {
  if (state.running) return;
  state.running = true;
  ui.btnMatrix.disabled = true;
  ui.btnSingle.disabled = true;
  try {
    await ensureConnection();
    await runOnce({
      mode: ui.formMode.value,
      quality: Number(ui.formQuality.value),
      in_flight: Number(ui.formInFlight.value),
      chunk_bytes: Number(ui.formChunk.value),
      duration_s: hashParams.duration,
    });
  } catch (err) {
    logError(`single run failed: ${err.message}`);
  } finally {
    state.running = false;
    ui.btnMatrix.disabled = false;
    ui.btnSingle.disabled = false;
  }
}

function setupCameraToggle() {
  const canCamera =
    window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === "function";
  ui.cameraMode.disabled = !canCamera;
  if (!canCamera) {
    ui.cameraNote.textContent =
      "Camera mode needs a secure context (HTTPS or chrome://flags unsafe-origin).";
    return;
  }
  ui.cameraNote.textContent = "Camera uses getUserMedia when mode is camera.";
}

async function warmCameraIfNeeded(mode) {
  if (mode !== "camera") return;
  if (!cameraStream) {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: WIDTH, height: HEIGHT },
      audio: false,
    });
  }
}

/** Parsed once at startup. */
let hashParams;

function init() {
  try {
    hashParams = parseHashParams();
  } catch (err) {
    setSignaling("error");
    logError(err.message);
    ui.btnMatrix.disabled = true;
    ui.btnSingle.disabled = true;
    return;
  }

  setupCameraToggle();
  ui.btnMatrix.addEventListener("click", () => runMatrix());
  ui.btnSingle.addEventListener("click", async () => {
    try {
      await warmCameraIfNeeded(ui.formMode.value);
      await runSingle();
    } catch (err) {
      logError(`camera: ${err.message}`);
    }
  });
  ui.formMode.addEventListener("change", async () => {
    if (ui.formMode.value === "camera") {
      try {
        await warmCameraIfNeeded("camera");
      } catch (err) {
        logError(`camera: ${err.message}`);
        ui.formMode.value = "synthetic";
      }
    }
  });

  setSignaling("idle");
  setConnection("closed");
  updateCounters();
  ui.fps.textContent = "0";
  ui.rttMedian.textContent = "0";
}

init();