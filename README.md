# Sngm local demos

FastAPI + SQLite backend and TypeScript/Vite frontend for two isolated journeys: a fresh Diwali river and Avni’s returning Ahoi Ashtami river. SQLite owns profiles, Currents, drafts, confirmed Captures, depth evidence and command idempotency. Fonts are bundled with their licences.

## Run

Requires Python 3.14+ (tested on 3.14) and Node 20.19+ / 22.12+.

```sh
uv sync
cd frontend
npm install
npm run build
cd ..
uv run python main.py
```

Create `.env` from `.env.example` if you do not already have one; keep an existing API key. Open **http://127.0.0.1:8000/demo/diwali** for a fresh demo, or **http://127.0.0.1:8000/demo/avni** for the populated river. If that port is occupied, add `--port 8010`. The backend serves the built frontend from the same origin. Set `ELEVENLABS_API_KEY` in `.env` before connecting live voice. The key stays on the backend; the browser gets an ephemeral credential. `ELEVENLABS_MODEL` and `ELEVENLABS_VOICE` configure the enabled Neutral Reading voice, shown before entry. The default is `eleven_realtime_v1_mini` with **Viraj — Confident and Natural**, an Indian-English voice (`fPIfC3elMLbN9tNwMXkw`). Viraj is available in this workspace; the app uses his workspace voice ID. Other workspaces must add that library voice or configure their own accessible Indian-English voice ID.

Provider selection at backend startup:

```sh
# Default: ElevenLabs realtime speech, microphone and PCM24k playback
uv run python main.py --provider elevenlabs
# Optional local LFM3 Omni guide with audio input, using llama.cpp on port 9931
uv run python main.py --provider lfm3 --lfm3-url http://127.0.0.1:9931
```

`SNGM_PROVIDER`, `LFM3_BASE_URL`, `LFM3_MODEL` and optional `LFM3_API_KEY` can also be set in `.env`. The service on 9931 exposes `/v1/chat/completions` with audio-input support. The app sends automatically segmented spoken turns to it; the device’s speech voice reads the guide’s responses. It does not require a realtime WebSocket endpoint. No provider silently falls back to another.

For frontend development, run `npm run dev` in `frontend/` alongside the backend on port 8000; Vite proxies `/api`. Rebuild the frontend before using the single-server version.

## The product experience

The application is a full-height river beside a spoken guide. The only in-session control is **Start guide / Stop guide**. There are no chat boxes, profile forms, practice selectors or presenter controls on the product canvas. First entry confirms adult eligibility before a run is created. Avni’s entry has three Currents, five explicitly illustrative stored readings and two open threads; fresh entry starts empty.

After entering or resuming, the guide begins after a **five-second pause**. A first Start tap may be needed where the browser blocks automatic audio or microphone access. Stop cancels speech, releases the microphone and invalidates pending turns; it does not erase your river. Start resumes the saved context.

The guide asks for a name, current home, family roots and festivals one question at a time. Supplied facts and corrections are persisted immediately and appear as labelled tributaries. These setup facts do not create Captures or award practice depth. New facts fly from the guide into labelled river pebbles. Chosen practices and explicitly kept memories join it separately. Wheel, drag or arrow keys move a perspective camera downstream or upstream; hover, focus or tap a pebble to unfold its scrapbook card. Open cards pause the drift. Reduced-motion settings are respected. Context photographs are bundled with their source and licence attribution.

Keep is conversational: the guide reads back the exact draft and asks for confirmation. An explicit “yes”, “keep that” or equivalent confirms the current draft once; uncertain replies do not save it. A pending card shows exactly which source summary, family memory or own interpretation is being proposed; only the committed save appears in the Riverbed. Source readings retain citation snapshots. Setup facts remain separate. Old runs remain in SQLite, but a backend restart now starts a fresh entry instead of silently restoring an old tab. Ordinary `/app` reloads during the same backend boot resume the run; explicit `/app?resume=<run-id>` links can restore owned previous runs.

### Voice providers

- **ElevenLabs:** native realtime microphone capture and PCM24k playback. Backend tools record supplied facts and update the river as the guide listens. The API key stays on the backend.
- **LFM3:** microphone turns are segmented automatically and sent as WAV to the local Omni model. LFM3 transcribes and extracts supplied facts; the device’s `speechSynthesis` voice reads the next guide question. This is local audio input plus device speech output, not native Omni speech generation. No separate chat UI or manual submit action is required. Browser speech synthesis and microphone access must be available.

Local model proposals are constrained against the recognized utterance before recording facts or selecting a practice. A spoken-name/location fixture has been exercised against the running server. Both providers use the same durable river state and explicit Keep confirmation rules.

## Verification

```sh
uv run pytest -q
node --test tests/frontend/demo.test.mts
cd frontend
npm run build
```

Tests exercise isolated baselines, adult gating, transactional concurrent save retries, exact-word confirmation, restart persistence, discard depth, stale generations, terminal stops, agent-write restrictions, origin checks and missing live credentials. Data is stored in `data/sngm.sqlite3` by default (`SNGM_DB` overrides it); it is ignored by Git.

## Current limits

This is a local demo, bound to loopback with an HttpOnly owner cookie; it is not hosted authentication. The small Diwali corpus is `content/corpus/diwali.v1.json`: six source-checked demo accounts covering regional traditions, Lakshmi, Kali, their comparison, Shaktism/bhakti and devotional offerings. Source records include author/institution, locators, URLs and reuse notes. These are editorially checked demo selections, not independent scholarly review. Ahoi remains a genuine Corpus Unknown; private family readings are separate.

The [corpus and Keep contract](docs/corpus-and-keep.md) describes retrieval, spoken source-saving, exact citation snapshots, reset behavior and the versioned Avni fixture. The citation/draft renderer is `frontend/src/components/reading.ts`; pebble content and scrapbook cards are in `frontend/src/components/river-world.ts`, and the moving river camera is `frontend/src/river-journey.ts`.

The Guard is an explicitly labelled presenter stop, not an independent evaluated audio safety model. Live ElevenLabs speech needs workspace access, internet and microphone permission and its Indian-English credential flow has been verified in this workspace; microphone/playback still needs browser QA. LFM3 audio transcription and extraction were verified with generated speech against the running local model. Desktop/mobile visual and interaction checks now run in a headless browser. The fresh-save journey has also been verified with simulated realtime tool events against the real backend; live microphone recognition and playback still require a manual check.

The current slice implements the shared persistent demo journeys and minimal conversational product surface. Durable SSE replay, evaluated independent audio Guard, broader content review and ingestion and fixed Route-out playback remain future work. See [architecture](docs/webapp-architecture.md) and [scenarios](docs/demo-scenarios.md) for the target contract.

Provider implementation follows the [official ElevenLabs realtime compatibility guide](https://elevenlabs.io/docs/eleven-agents/guides/openai-realtime-compatibility).

### Optional browser regression checks

With Playwright available and an isolated rehearsal backend running on port 8024:

```sh
SNGM_DB=/tmp/sngm-browser.sqlite3 uv run python main.py --provider rehearsal --port 8024
# In another terminal:
node tests/browser/river.cjs
node tests/browser/voice-tools.cjs
```

Set `PLAYWRIGHT_MODULE` to an existing Playwright module path if it is outside this project, and `SNGM_TEST_URL` if using another preview port. The first check covers desktop/mobile camera movement, card hover, photographs and layout. The second substitutes the voice socket and microphone, then drives real API tool calls through the frontend to a confirmed memory and reload. Screenshots are written to `/tmp/sngm-journey-shots`; no live provider credentials are used by these checks.
