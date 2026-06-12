# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "flask",
#   "faster-whisper",
#   "numpy",
#   "soundcard; sys_platform != 'linux'",
# ]
# ///
"""Meeting capture: live transcription + optional recording, cross-platform.

Captures the audio the user HEARS (system output / loopback), transcribes
fixed-size chunks with faster-whisper, serves a rolling transcript page, and
optionally tees the raw audio into an Opus recording via ffmpeg.

Capture backends:
  linux    pw-record against a PipeWire sink monitor (MEETING_SINK)
  windows  WASAPI loopback of the default speaker via the soundcard library
  darwin   records a loopback INPUT device (e.g. BlackHole) via soundcard;
           system audio must be routed through that device (MEETING_DEVICE)

Configuration via environment:
  MEETING_SINK    linux: PipeWire sink node name to capture (required on linux)
  MEETING_DEVICE  darwin: loopback device name substring (default "BlackHole")
  MEETING_PORT    HTTP port for the transcript app (default 8743)
  MEETING_MODEL   faster-whisper model (default base.en)
  MEETING_CHUNK   chunk length in seconds (default 10)
  MEETING_LOG     optional JSONL path; segments appended for crash persistence
  MEETING_RECORD  optional .opus output path; tees capture into ffmpeg
"""
import json
import os
import platform
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, request
from faster_whisper import WhisperModel

SYSTEM = platform.system().lower()
PORT = int(os.environ.get("MEETING_PORT", "8743"))
MODEL = os.environ.get("MEETING_MODEL", "base.en")
CHUNK_SECONDS = int(os.environ.get("MEETING_CHUNK", "10"))
LOG = os.environ.get("MEETING_LOG", "")
RECORD = os.environ.get("MEETING_RECORD", "")

RATE = 16000
SAMPLES_PER_CHUNK = RATE * CHUNK_SECONDS

app = Flask(__name__)
segments = []
lock = threading.Lock()
status = {"state": "loading model", "backend": SYSTEM}

if LOG and Path(LOG).exists():
    with open(LOG) as f:
        segments = [json.loads(line) for line in f if line.strip()]


def chunks_linux():
    """Yield int16 mono chunks from a PipeWire sink monitor."""
    sink = os.environ["MEETING_SINK"]
    proc = subprocess.Popen(
        ["pw-record", "-P", "stream.capture.sink=true", "--target", sink,
         "--rate", str(RATE), "--channels", "1", "--format", "s16", "-"],
        stdout=subprocess.PIPE,
    )
    nbytes = SAMPLES_PER_CHUNK * 2
    while True:
        buf = b""
        while len(buf) < nbytes:
            data = proc.stdout.read(nbytes - len(buf))
            if not data:
                return
            buf += data
        yield np.frombuffer(buf, np.int16)


def chunks_soundcard():
    """Yield int16 mono chunks via the soundcard library.

    windows: loopback of the default speaker (no driver needed).
    darwin: records the loopback input device (BlackHole or similar) that
    system audio is routed through.
    """
    import soundcard as sc

    if SYSTEM == "windows":
        spk = sc.default_speaker()
        mic = sc.get_microphone(spk.name, include_loopback=True)
    else:
        want = os.environ.get("MEETING_DEVICE", "BlackHole").lower()
        mics = [m for m in sc.all_microphones() if want in m.name.lower()]
        if not mics:
            raise RuntimeError(
                f"no input device matching '{want}' — install a loopback driver "
                "(e.g. BlackHole) and route meeting audio through it")
        mic = mics[0]

    block = RATE  # 1s blocks, assembled into chunks
    with mic.recorder(samplerate=RATE, channels=1) as rec:
        buf = np.empty(0, dtype=np.float32)
        while True:
            data = rec.record(numframes=block).flatten()
            buf = np.concatenate([buf, data])
            while len(buf) >= SAMPLES_PER_CHUNK:
                chunk, buf = buf[:SAMPLES_PER_CHUNK], buf[SAMPLES_PER_CHUNK:]
                yield (np.clip(chunk, -1, 1) * 32767).astype(np.int16)


def capture_loop():
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    recorder = None
    if RECORD:
        Path(RECORD).parent.mkdir(parents=True, exist_ok=True)
        recorder = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "s16le",
             "-ar", str(RATE), "-ac", "1", "-i", "-",
             "-c:a", "libopus", "-b:a", "32k", "-y", RECORD],
            stdin=subprocess.PIPE,
        )
    source = chunks_linux() if SYSTEM == "linux" else chunks_soundcard()
    status["state"] = "live"
    for chunk in source:
        if recorder:
            recorder.stdin.write(chunk.tobytes())
        audio = chunk.astype(np.float32) / 32768.0
        if np.abs(audio).max() < 0.01:
            continue  # silence: skip so whisper doesn't hallucinate text
        segs, _ = model.transcribe(audio, language="en", beam_size=1,
                                   condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        if text:
            seg = {"t": time.strftime("%H:%M:%S"), "text": text}
            with lock:
                segments.append(seg)
            if LOG:
                with open(LOG, "a") as f:
                    f.write(json.dumps(seg) + "\n")
    status["state"] = "capture ended"
    if recorder:
        recorder.stdin.close()
        recorder.wait(timeout=10)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live Transcript</title>
<style>
  body { background:#111; color:#ddd; font:16px/1.6 system-ui, sans-serif;
         max-width:760px; margin:0 auto; padding:24px; }
  h1 { font-size:18px; color:#fff; }
  #status { color:#888; font-size:13px; margin-bottom:16px; }
  .seg { margin-bottom:10px; }
  .ts { color:#6a9; font-size:12px; margin-right:8px; font-family:monospace; }
</style></head>
<body>
<h1>Live Meeting Transcript</h1>
<div id="status">connecting…</div>
<div id="log"></div>
<script>
let n = 0;
async function poll() {
  try {
    const r = await fetch('transcript?since=' + n);
    const d = await r.json();
    document.getElementById('status').textContent =
      d.status + ' — ' + (n + d.segments.length) + ' segments';
    for (const s of d.segments) {
      const div = document.createElement('div');
      div.className = 'seg';
      div.innerHTML = '<span class="ts">' + s.t + '</span>' + s.text;
      document.getElementById('log').appendChild(div);
      n++;
    }
    if (d.segments.length) window.scrollTo(0, document.body.scrollHeight);
  } catch (e) {
    document.getElementById('status').textContent = 'disconnected — retrying';
  }
  setTimeout(poll, 2000);
}
poll();
</script>
</body></html>"""


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/transcript")
def transcript():
    since = int(request.args.get("since", 0))
    with lock:
        return jsonify({"status": status["state"], "segments": segments[since:]})


threading.Thread(target=capture_loop, daemon=True).start()
app.run(host="0.0.0.0", port=PORT)
