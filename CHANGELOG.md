# Changelog

## 0.1.0
- Initial release: cross-platform capture script (PipeWire / WASAPI loopback / BlackHole), live transcript web page with JSONL persistence, Opus recording tee, record + finalize skills. Extracted from the 2026-06-11 live-meeting pipeline.

## 0.2.0
- distill skill: meeting transcript → knowledge-base entries (decisions, people, glossary, project requirements, problems). Writes schema-compliant entries into the mindframe vault when ~/.mindframe/vault exists, standalone notes otherwise. Live mode documents the incremental cursor loop for during-meeting KB updates.
