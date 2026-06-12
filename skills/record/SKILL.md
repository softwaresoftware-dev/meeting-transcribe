---
name: record
description: Start, verify, spot-check, or stop meeting audio capture with a live rolling transcript. Use when asked to "record this meeting", "record the meeting audio", "transcribe my meeting", "start meeting capture", "live transcript", "is it capturing", "spot-check the recording", or "stop the meeting recording". Captures what the user HEARS (the meeting), not their microphone.
---

# Record a Meeting

Capture meeting audio (Meet/Zoom/Teams playing in any app), produce a compact Opus recording plus a live rolling transcript in the browser. One bundled script (`${CLAUDE_PLUGIN_ROOT}/scripts/live_transcribe.py`) does capture + transcription + recording on every platform; run it as a managed daemon via the daemon capability so it survives shell exits.

Read user config: `CLAUDE_PLUGIN_OPTION_RECORDINGS_DIR` (default `~/recordings`), `CLAUDE_PLUGIN_OPTION_LIVE_MODEL` (default `base.en`).

## Platform prerequisites (probe before starting)

| OS | Capture path | Probe | If missing |
|----|--------------|-------|------------|
| Linux | PipeWire sink monitor | `which pw-record` | apt/dnf `pipewire-utils`; PulseAudio-only systems are unsupported (the pulse shim delivers zero samples silently — do not fall back to it) |
| Windows | WASAPI loopback of default speaker | `python -c "import soundcard"` works after uv resolves; no driver needed | — |
| macOS | Loopback input device | a device matching "BlackHole" in input list | `brew install blackhole-2ch`, then route meeting audio: Audio MIDI Setup → Multi-Output Device (speakers + BlackHole) as system output |

Also everywhere: `uv` and `ffmpeg` on PATH (ffmpeg only needed for the Opus recording tee and finalize).

## Start

1. **Find the audio source:**
   - Linux: `pactl list sink-inputs` → match the meeting app (browser/zoom/teams) to its sink; `pactl list sinks short` for the node name → `MEETING_SINK`.
   - Windows: nothing to find — the script loopbacks the default speaker.
   - macOS: confirm a BlackHole-style device exists and the meeting audio is routed through it → `MEETING_DEVICE` (default "BlackHole").
2. **Start the capture daemon** via the daemon capability (daemon-manager `daemon_start`), or `systemd-run --user --collect` on Linux if no daemon provider is installed. Command:
   `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/live_transcribe.py`
   with env:
   - `MEETING_SINK` / `MEETING_DEVICE` per platform
   - `MEETING_PORT` (default 8743; pick another if busy)
   - `MEETING_MODEL` from user config
   - `MEETING_RECORD=<recordings_dir>/meeting-<YYYY-MM-DD>.opus`
   - `MEETING_LOG=<recordings_dir>/meeting-<YYYY-MM-DD>.segments.jsonl`
   First run downloads the model (~75 MB); allow 30–60 s.
3. **Verify before declaring success** — both of:
   - `curl -s localhost:<port>/transcript?since=0` until `"status":"live"`, then until a segment with real text appears (if the meeting is silent, segments lag — that's the anti-hallucination gate, say so).
   - After ~90 s, copy the .opus and decode-check: `ffmpeg -i copy.opus -af volumedetect -f null -` → mean_volume ≈ −20 dB is real audio; ≈ −90 dB means dead capture. **Never judge by file size** — Opus flushes in ~256 KB steps, up to a minute apart.
4. Give the user the transcript URL (`http://localhost:<port>`), plus a LAN/tailnet variant if available.
5. Warn once: the capture takes everything routed to that output device — music and notifications included.

## Spot-check ("is it actually capturing?")

Copy the in-progress .opus (it's streamable mid-write, lagging up to ~1 min), then: duration via ffprobe, volumedetect for liveness, and `ffmpeg -sseof -15 -i copy.opus -c copy /tmp/last15.opus` for an ear-check clip.

## Stop

Stop the daemon (daemon capability `daemon_stop`, or `systemctl --user stop <unit>`). The Opus file is valid even when killed mid-write; segments persist in the JSONL. Offer `/meeting-transcribe:finalize` for the high-quality transcript.

## Troubleshooting

- Live but no segments + meeting silent → normal (silence gate).
- Linux zero-byte capture → you used the PulseAudio shim; use pw-record (the script does).
- macOS records silence → meeting audio isn't routed through BlackHole; fix the Multi-Output Device.
- Port busy → restart with a different `MEETING_PORT` and tell the user the URL changed.
- Daemon died → check its logs via the daemon provider; first-run model download is a delay, not a failure.
