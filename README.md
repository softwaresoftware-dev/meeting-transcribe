# meeting-transcribe

Record meeting audio output and transcribe it — live rolling transcript in the browser plus a high-quality final transcript. Captures what you **hear** (the meeting), not your microphone.

Install: `/softwaresoftware:install meeting-transcribe`

Skills: `/meeting-transcribe:record` (start/verify/stop capture + live transcript), `/meeting-transcribe:finalize` (large-v3 re-transcription), `/meeting-transcribe:distill` (transcript → knowledge base — mindframe vault aware).

| OS | Capture | Prerequisite |
|----|---------|--------------|
| Linux | PipeWire sink monitor (`pw-record`) | pipewire-utils |
| Windows | WASAPI loopback (no driver) | — |
| macOS | Loopback device via soundcard | BlackHole (`brew install blackhole-2ch`) + audio routing |

Tested on Linux. Windows and macOS paths are implemented but not yet CI-verified.
