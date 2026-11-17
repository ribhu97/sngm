# Demo corpus and spoken Keep

The versioned source of truth is `content/corpus/diwali.v1.json`. Each account has a fixed title, original summary, spoken explanation, retrieval tags, limits and source IDs. Source records distinguish primary literature, academic scholarship, university overviews and curatorial interpretation; they include author/institution, passage locator, URL and reuse notes. No runtime web search or vector service is needed.

The demo selection was checked against its linked material on 17 November 2026. This is editorial checking for a small demo, not independent scholarly or theological review. Sri Suktam, Devi Gita and Bhagavad Gita are literary contexts; none is represented as a universal Diwali ritual manual. Shaktism and bhakti are explained as overlapping categories. Sources cannot determine a user's family's affiliation or meaning.

The API `GET /api/corpus?query=Lakshmi%20versus%20Kali` previews the comparison without changing a river. The guide's `get_corpus_account` command creates the authoritative presentation context in the active run. It returns the same account to the guide and the frontend before the next explanation. Account IDs supplied by a model must exist in the allowlist; source metadata is never accepted from model arguments.

## Spoken confirmation

1. A sourced explanation appears in the reading component, with links, locators and evidence type.
2. “Keep this reading” calls `request_keep` and prepares a **source** draft. It does not save a Capture. The draft names the exact summary and citation snapshot to save. A family/own reading uses `draft_reading` with the person's own words instead.
3. A separate pending card says **Not saved yet**, distinguishes source summary from family memory or own interpretation, shows the proposed wording and explains “keep this source” / “keep that” or “leave it”. The guide reads back the proposal.
4. Explicit confirmation invokes `confirm_reading` bound to the current draft ID. Uncertain or negative words cannot confirm. A draft cannot be replaced accidentally without an explicit replacement reference.
5. The transaction saves the Capture, snapshot and depth evidence. Only the committed result renders as a new entry in the Riverbed and an additional river mark. Retries return the existing save. Loading seed data or resuming a run does not replay the success state.

The source-reading Capture stores the account ID/version, title, exact canonical summary and attached citation snapshot. A family memory may retain the sources shown beside it as context, but is labelled as private testimony rather than evidence supplied by those sources. Discard and terminal-session rules continue to apply.

## Entry and stored Avni river

- `/demo/diwali` (or `/demo`): fresh entry; no automatic restore.
- `/demo/avni`: a separate entry to a fresh isolated copy of `content/demo/avni.v2.json`, containing three Currents, five illustrative Captures and two open threads. It is written to SQLite on entry, then read from storage like other runs.
- `/app`: resumes a same-tab run only while the backend instance ID matches. Restarting the backend invalidates automatic restoration and shows fresh entry.
- `/app?resume=<run-id>`: explicitly resume an owned prior run, including across backend restarts. An ID alone never bypasses the owner cookie.

Old runs are retained instead of destroyed when starting fresh. Avni's seed clearly distinguishes research-inspired motifs from synthetic reflections. The Riverbed exposes the provenance of every illustrative reading.

### River presentation and conversational turns

The left pane is a fixed viewport into a perspective river, drawn on canvas. Wheel, drag, touch and arrow keys move a camera with inertia; a slow ambient drift follows the river when no memory is open. It has no document scrollbar. Browser zoom remains available. Reduced-motion mode removes drift and animation and moves directly between positions.

Setup facts and confirmed captures have separate pebbles anchored to the same river geometry. Setup changes animate from the guide's side into a named pebble and are announced as saved. They remain durable profile facts, not memory Captures or practice-depth evidence. Memories show their Current and season attachment. Distant labels recede to avoid crowding.

Hover or keyboard focus unfolds one pebble into a compact paper scrapbook card. Tap pins it open; tap outside or Escape closes it. The camera pauses while reading. Cards include contextual photographs from Wikimedia Commons with per-image attribution and licence links; they do not claim to depict the user's family. Originals and attribution are bundled under `frontend/public/assets/scrapbook/`. A new explanation is brought into view and opened automatically, with a primary quotation, separate editorial interpretation and expandable evidence.

Fresh visitors can draft a memory before choosing a festival; it belongs to a neutral Family stories Current. A direct Diwali corpus lookup can establish a Learn Current without requiring an extra setup tool call. A pending draft can be confirmed through either `confirm_reading` or a matching `request_keep`, using explicit spoken consent. An omitted draft ID binds to the current draft under the request's version/generation checks; an explicitly stale ID is rejected. Every commit remains idempotent and durable. The realtime tool schema describes the action arguments, and failures appear visibly instead of silently resembling a save.

Realtime function outputs are coordinated per response: all tool work finishes before one continuation is requested. Repeated identical calls and chains beyond four continuations stop until new speech arrives. Duplicate profile facts do not advance state. Prompts prohibit repeated thanks, skip reminders and onboarding restarts.

Validation includes backend fresh-memory/source save regressions, frontend perspective and pebble content checks, desktop/mobile headless browser interaction checks, and a simulated realtime-event journey through the real frontend and backend to a durable memory pebble and reload. Live microphone recognition is not simulated by those browser checks.
