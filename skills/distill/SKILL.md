---
name: distill
description: Turn a meeting transcript into knowledge-base entries — decisions, people, glossary terms, project requirements, problems raised. Use when asked to "distill the meeting", "update the knowledge base from the meeting", "extract decisions from the transcript", "fold the meeting into the vault", or after finalizing a meeting transcript. Supports a live mode that updates the KB every few minutes while the meeting is still running.
---

# Distill a Meeting into the Knowledge Base

Extract durable knowledge from a meeting transcript and write it where the user's knowledge base lives. Works post-meeting (one pass over the final transcript) or live (incremental loop during the meeting).

## Where to write

1. **Mindframe vault** — if `~/.mindframe/vault` exists, write there. It is a schema'd KB: **read `schema.yaml` and `CLAUDE.md` at the vault root first** and follow their contract exactly (entity types, directories, frontmatter, name/slug rules, the catalog index). Update `CATALOG.md` for every new entity. If the vault is a git repo, commit after each pass (lowercase imperative message).
2. **No vault** — write a single `<recording>-notes.md` next to the transcript with the same sections (decisions, people, terms, requirements, problems, action items).

## What to extract

Work from the transcript with healthy skepticism — auto-transcription mangles names and numbers; mark uncertain ones `[sp?]` and keep a "confirm spellings" list.

- **Decisions** — only things actually decided in the room, as dated event entries (`YYYY-MM-DD-<topic>`); capture the why and any later refinement of the same decision (amend the entry, don't duplicate).
- **People** — who attended, roles, affiliations; new people get entries, known people get corrections.
- **Domain terms** — jargon the meeting relied on, defined the way the room used it.
- **Project material** — vision statements, requirements, constraints, architecture — folded into the relevant project note with approximate `~HH:MM` timestamps so claims stay traceable to the recording.
- **Problems raised and action items** — with owners where stated.

Quote sparingly but keep the speaker's signature phrasings — they carry intent that paraphrase loses.

## Live mode (during the meeting)

If a live transcript is running (the record skill's web app), set up an incremental loop instead of waiting for the end:

1. Keep a cursor file of the last processed segment index.
2. Every ~10 minutes: `curl localhost:<port>/transcript?since=<cursor>`, extract from only the new segments, fold into the KB, advance the cursor, commit.
3. If the transcript stops growing, check whether the capture daemon is still alive before assuming the meeting ended — and treat known breaks (lunch) as pauses, not endings.
4. On meeting end, write a session summary into the project note (attendees, outcome, workstreams/action items) and stop the loop.

Use the session's recurring-task mechanism (cron/loop tooling) for the cadence; each iteration must be self-contained (read cursor → fetch → extract → write → commit).

## After distilling

If the live pass used a fast model, re-run name/number verification once the finalized (large-model) transcript exists: grep it for every `[sp?]` name and correct the KB in one pass. Today's live models reliably fumble proper nouns; the final model reliably fixes them.
