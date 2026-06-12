---
name: finalize
description: Produce a high-quality transcript from a finished meeting recording using a large Whisper model (GPU if available). Use when asked to "finalize the transcript", "re-transcribe the meeting", "high quality transcript", or after stopping a meeting recording. Also offers to correct names/numbers in notes taken from the rough live transcript.
---

# Finalize a Meeting Transcript

Re-transcribe the finished recording with a large model. Run the transcription in the background — never block the session on it.

## GPU path (NVIDIA)

ctranslate2 needs cudnn/cublas that usually aren't system-installed; use a scratch venv:

```bash
uv venv /tmp/wlarge -q
uv pip install -q --python /tmp/wlarge/bin/python whisper-ctranslate2 nvidia-cudnn-cu12 nvidia-cublas-cu12
export LD_LIBRARY_PATH=$(/tmp/wlarge/bin/python -c "import nvidia.cudnn.lib, nvidia.cublas.lib; print(nvidia.cudnn.lib.__path__[0]+':'+nvidia.cublas.lib.__path__[0])")
/tmp/wlarge/bin/whisper-ctranslate2 <recording.opus> --model large-v3 --device cuda \
  --language en --output_dir <tmpdir> --output_format txt --verbose False
```

Gotchas (these WILL bite):
- The nvidia packages are namespace packages — `__path__[0]`, never `__file__` (which is `None`).
- Without `LD_LIBRARY_PATH` it dies with "libcublas.so.12 not found".
- ~3.5 h of audio ≈ a few minutes on a modern GPU.
- On Windows, set the equivalent via `PATH` to the venv's `nvidia/cudnn/bin` and `nvidia/cublas/bin` directories.

## CPU fallback (no NVIDIA GPU, incl. macOS)

`uvx whisper-ctranslate2 <recording.opus> --model small.en --device cpu ...` — roughly real-time÷3 on a modern CPU; use `base.en` if speed matters more than accuracy. (On Apple Silicon, `mlx-whisper` is faster if installed, but small.en CPU is the dependable default.)

## After transcription

1. Copy the .txt next to the recording as `<name>-transcript.txt`.
2. Offer to correct any notes that were taken from the rough live transcript — proper nouns and numbers are where the live model fails and large-v3 shines. Grep the new transcript for the uncertain names before asserting corrections.
