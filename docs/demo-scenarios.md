# Sngm demo plan: two journeys, one product

Status: implementation plan. Both scenarios use the Python FastAPI backend, ElevenLabs Eleven Realtime live guide, reviewed Corpus service and transactional Family river storage described in the [architecture](webapp-architecture.md). Both persistent scenario baselines and typed Keep journeys are now implemented; see README for provider setup and content/safety limitations.

## What we are demonstrating

| Scenario | Starting point | Main question answered | End state |
|---|---|---|---|
| **Start my river / Diwali** | A fresh adult demo identity, no onboarding answers, no Currents or Captures | Can a conversation help me find a practice and begin a personal river? | Supplied setup details, a chosen Diwali practice, one explicitly kept reading with provenance. |
| **Return to Avni’s river / Ahoi Ashtami** | An isolated seeded identity, completed onboarding, three practice Currents and illustrative Riverbed entries | Does the product remember what matters and bring me back to the right thread? | Existing memories retained, the children’s-fast thread reopened, one new confirmed Capture on that Current. |

These are selectable entry points in one app, not two implementations or different backend stacks. Both use live conversation and real database writes. Content coverage is intentionally narrow and reviewed. Demonstrate new-user formation first, then continuity and seasonal return.

Use **Ahoi Ashtami** as the canonical festival name and `ahoi_ashtami` as its internal ID. Accept Hoi Ashtami and common spoken/transcription variants, including “hoi asthami,” as aliases to confirm in context. Preserve the person’s original wording; do not turn pronunciation into a correction exercise.

## Presenter entry and scenario isolation

A demo-only launcher offers two clear actions: **Start my river** and **Open Avni’s river**. Proposed route: `/demo`; the actual product surface remains `/app`. The launcher is presenter tooling, not a normal customer onboarding screen.

Starting a scenario creates a new `demo_run_id` and identity scope. It never repoints a live Session from one person’s river to another. Switching scenarios closes the active voice connection, stops all playback/Flow, invalidates pending effects and opens a separately authorized Session for the selected run.

| Launcher action | Behaviour |
|---|---|
| Start fresh Diwali run | Create an empty river and onboarding checkpoint. Adult gate occurs before the guide appears. Use the presenter’s supplied answers; do not invent personal background. |
| Open fresh Avni run | Clone the versioned Avni seed into a new isolated run. Skip onboarding; show her existing river before connecting the guide. |
| Resume run | Restore that run’s durable state. Reconnect ElevenLabs from the saved app context rather than reusing another run’s provider conversation. |
| Reset active run | Explicitly confirm resetting only this demo run; create a fresh baseline and close the old voice Session. Diwali returns to empty; Avni returns to the seed. Other runs and the shared Corpus remain untouched. |

Prefer a new run per rehearsal. Keep a completed run available for discussion instead of wiping it automatically when switching scenarios. Browser reload restores the run; returning through the launcher can explicitly choose resume or fresh start.

Proposed backend additions:

- `GET /api/demo/scenarios`: scenario names, versions, content readiness and voice availability.
- `POST /api/demo/runs`: instantiate a scenario using an idempotent creation request; return run-scoped identity and initial state.
- `POST /api/demo/runs/{id}/reset`: verify demo-run ownership and reset permission, terminate the old Session and create the replacement baseline transactionally.

Enable these only in explicit demo mode, with the intended local/presenter access restriction. Do not expose general seed/reset operations as ordinary production-user APIs. Every command, stream, event cursor and tool call is bound to the active identity/run/Session; the browser cannot select another identity by passing a name.

## Scenario A: start my river, follow Diwali

**Opening image:** an empty river canvas and a still calligraphic voice stroke. No placeholder family memories, fabricated progress or Avni data.

The lines below are proposed conversation prompts and rehearsal replies, not research quotes. The live guide can phrase connective talk naturally; Python owns the next eligible action and which texts can be shown.

| Beat | Guide / participant | Visible change and backend effect |
|---|---|---|
| 1. Enter and choose voice | Pass the adult gate. A Neutral setup welcome offers the enabled Reading voices. Select one, then begin the learning Session. | Voice selection is locked for the Session. If Neutral is the only available voice, say so and continue. |
| 2. Name and family beginnings | Guide asks what to call the person, where they live, and where their family comes from, one question at a time. Responses may skip or correct fields. | Persist only supplied setup facts and onboarding progress. The river remains empty. |
| 3. Notice a festival | “Which festivals do you celebrate at home?” Presenter mentions Diwali. | Confirm the festival mention and follow it immediately; do not finish an unrelated questionnaire first. No depth is awarded for mentioning a festival. |
| 4. Find the practice | “What part of Diwali would you like to understand?” A rehearsable answer is lighting the home/diyas. | Create the chosen practice Current, initially without earned depth. Offer Learn/Practice Intent conversationally or an explicit choice; do not invent an Intent from demographics. |
| 5. Bring the texts | Offer the prepared reviewed selection relevant to that question. Ask which reading resonates, without endorsing an interpretation. | Python returns the canonical account; render passages, attribution and Citations before the guide speaks about them. Show only actual reviewed material. |
| 6. Bring family beside it | “What does lighting the home look like in your family?” The person supplies their own memory or practice. | Hold a draft Family reading, or an Own reading if it is the person’s own meaning. It stays separate from what the texts say. |
| 7. Choose to Keep | Guide offers to keep the displayed draft. Person confirms “keep that,” or edits the wording before confirming. | Transaction commits Capture, citation snapshot and eligible depth evidence once. The same voice stroke becomes a stream in that Current and the Capture appears on the Riverbed. |
| 8. Show it remains | Pause speech, inspect the entry, then reload/resume or close and reopen. | The first river persists in SQLite and returns without duplicate onboarding, duplicate Capture or repeated Keep animation. |

**Successful ending:** “This is now something I chose to keep,” demonstrated by the actual saved reading. A good demo requires only one practice and one Keep. Declining Keep remains a valid product path; it must not prevent onboarding completion or force a family memory into storage.

If several festivals are mentioned, acknowledge them and ask which to explore first. The rehearsed path chooses Diwali. Unsupported festivals may be recorded as supplied setup data, but do not receive invented texts or a false claim of content coverage.

## Scenario B: return to Avni’s river, reopen Ahoi Ashtami

**Opening image:** a populated Family river, with several Currents and a Riverbed that has visible history. The guide does not ask Avni’s name, family origins or festivals again.

This seed is based on [the research notes](../../../01-research/notes.md), especially Interview 3, and the [earlier Avni runbook](../../../07-demo/README.md). It is an **interview-inspired reconstruction**, not an imported real product account, a transcript, or evidence that Avni previously consented to particular in-app Captures. Mark seeded entries as illustrative demo data. Use paraphrases unless quoting a verified research passage exactly.

### Seed specification

| Seed record | Starting contents | Boundary |
|---|---|---|
| Identity and profile | Avni; adult demo identity; research context: 31, Gurgaon, UP heritage, grew up in Ghaziabad via Kashipur/Allahabad. Onboarding completed. | Use only facts required for the scene; no real contact details, birthday or voice likeness. |
| Current: the children’s fast | Ahoi Ashtami context; Learn Intent; an illustrative prior why thread; modest pre-existing depth supported by explicitly seeded exploration evidence. | Do not claim an actual earlier app Session. Keep the meaning of her family’s observance unresolved. |
| Current: family recipes | Gulgule; Practice Intent; an illustrative Family reading about its link with Hoi Ashtami and Karwa Chauth, paraphrased from the interview. | Private family context, with no invented Corpus Citation or recipe instructions. |
| Current: the Diwali light | Practice Intent; an illustrative reading about repairing and hanging the old Allahabad light, with her father remembered. | Research-inspired family history, not evidence for a general teaching about Diwali. |
| Reopening threads | The children’s-fast why thread plus a more recent unrelated Diwali-light thread. | Ahoi Season must choose the relevant fast thread, demonstrating that relevance can outrank recency. |
| Voice preference | Neutral, or the same authorized Reading voice used elsewhere if available. | No cloned Avni or relative. Choose/validate the preference before opening the learning Session. |
| Scenario clock | A reviewed Ahoi Ashtami scenario day, configured independently from the actual machine date. | Clearly identified as a demo Season in presenter tooling. Do not infer a current festival date or build a full calendar service for this. |

Give each Current and Capture stable fixture IDs, explicit seed provenance, a fixture version, and internally consistent evidence/history. Seed event timestamps can be relative to the scenario clock; they are illustrative history, not research timestamps. Existing depth remains unchanged after a simulated gap. Loading the seed does not create new earned depth.

The first fixture should contain these three Currents, two illustrative Captures (gulgule and the repaired light), and two prior threads. The children’s-fast Current can have exploration evidence without a prior kept reading; the first new Keep then has a visible place to land.

### The returning-user journey

| Beat | Guide / participant | Visible change and backend effect |
|---|---|---|
| 1. Arrive at an existing river | Presenter opens Avni’s scenario. Guide names the Season and offers the children’s-fast thread. | Existing Currents and two seeded Captures are present before conversation; no onboarding form or reset of depth. |
| 2. Reopen the why | Proposed prompt: “You had a question about the children’s fast. Would you like to return to it?” Presenter asks why the fast is kept. | Python selects the Ahoi account and presentation context, not the more recent Diwali-light thread. The offer itself does not deepen the Current. |
| 3. Show what is held | Guide discusses the prepared reviewed account, with its Citation visible, and states what it cannot settle about her family. | Actual accepted sources only. The old promise of a verse and two scholars is not a requirement unless those materials are really supplied and reviewed. |
| 4. Bring back the family | Guide invites what she remembers about this day. Presenter supplies a memory or reading, for example about gulgule. | A memory draft is shown beside the account. It does not overwrite the seed or enter the Corpus. A gap in family-specific knowledge remains an Unknown. |
| 5. Keep a new reading | Presenter confirms the displayed draft. | Commit one new Capture on the children’s-fast Current; the voice stroke joins that branch. Its depth grows and the two other Currents remain unchanged. |
| 6. Open upstream | Guide invites her mother’s version, or a memory/artifact if the person she would ask is unavailable. | It is an optional invitation, not a required call or a gated task. Do not suggest contacting her deceased father. |
| 7. Show continuity | Inspect the new Capture and the older gulgule/light entries; optionally switch day/night, close/reopen, or demonstrate an unchanged river after a gap. | Persistence and continuity are real. New capture count is baseline two plus one; sources and original entries remain intact. |

**Successful ending:** a new layer has joined a river that already had a history. The scenario shows Season relevance, memory, honest sources and incremental growth, rather than repeating onboarding.

Mentioning loss while still able to converse must not automatically trigger Route-out. A present crisis remains a separate Guard path. A Tributary is optional after the golden path and only if a reviewed relevant account exists; it is the first extension to cut if time is tight. Sharing to family is not needed in either demo.

## Shared scenario configuration

Keep differences in data and entry state, not duplicated UI components or different guide implementations.

```text
content/demo/
  scenarios.yaml                   # versions, start mode, content readiness, clock
  diwali_onboarding.v1.yaml         # empty baseline and supported onboarding branch
  avni_ahoi_return.v1.yaml           # profile, Currents, Captures and threads
content/corpus/
  diwali/                          # accepted starter passages and citation metadata
  ahoi_ashtami/                    # accepted account and explicit limits
```

A scenario definition supplies `scenario_id`, `version`, `entry_mode`, seed reference, supported practice IDs, starter account IDs, voice policy, optional scenario clock, expected initial state and acceptance checkpoints. All mutable rows belong to the created run/identity. Read-only Corpus passages are shared and versioned. Resolve account and voice references before a run is marked ready.

The live prompt receives the active run’s authorized context and eligible next actions from Python. It must not treat fixture files or the research notes as an unbounded knowledge base. The Diwali branch may vary naturally in speech, but backend transitions and source selection remain constrained. The Avni branch uses her river snapshot, not hardcoded recollections in an agent prompt that bypass storage.

## Content and media readiness

| Material | Diwali | Avni / Ahoi |
|---|---|---|
| Reviewed content | A starter account for the chosen Diwali practice, with a small selection of exact passages and named interpretations only where genuinely available. | A reviewed general account of the fast and a clear family-specific Unknown; additional interpretations only when supplied. |
| Family material | Live presenter input, explicitly confirmed before Keep. | Labelled seed paraphrases plus a new reading supplied during the run. |
| Voice | ElevenLabs enabled Neutral mapping; authorized Partner mappings only if already available. | Same provider and voice policy; no actor impersonating Avni or her family. |
| Sound | Flow, Kept-sound and a fixed reviewed Route-out recording. | Same assets and stop behaviour. |
| Failure disclosure | Live voice needs internet; reviewed content breadth is limited. | Family history is reconstructed seed data; the new Keep is a real backend write. |

No full corpus ingestion UI, autonomous web search, unreviewed religious claims, or broad vector-index work is required to prove these two journeys. Both still exercise Python’s real Corpus contract; add vector retrieval behind it when the content set and evaluation justify it.

Before stage use, preview the supplied source cards independently of the live voice. Verify links, exact excerpts, review status and permission to show them. The existing atlas’s general Ahoi note is an input to review, not proof that all required demo content is ready. Do not turn an unavailable-content stub into a success state merely to finish the script.

## Build order

1. **Scenario foundation:** run-scoped identity, launcher, fixture loader, seed validation, explicit reset/resume and shared river view. Prove the empty Diwali baseline and populated Avni baseline without voice first.
2. **Shared live Session:** ElevenLabs credential flow, selected voice, microphone/playback, independent Guard interface, tool bridge and interruption. Keep data isolated during repeated starts and switches.
3. **Diwali vertical slice:** short adaptive onboarding, festival confirmation, practice selection, reviewed text presentation, drafted reading, confirmed transactional Keep and calligraphic stream.
4. **Avni return slice:** Ahoi clock, context-aware Reopening, account plus family-specific Unknown, family-memory draft, Keep on the right Current and optional upstream invitation.
5. **Presentation pass:** run each journey end to end, test reload/backend restart and failure cases, freeze content and record separate backup videos.

Both slices use the same `draft_reading`, `keep_reading`, `get_corpus_account`, Current-depth rules and event rendering. Implement `get_reopening` as a Python tool for the returning-user slice. Add no alternate write path in demo controls and no frontend-only fake Capture on either scenario.

## Rehearsal and acceptance

Plan **about 7–9 minutes total** as a provisional presentation budget: 4–5 minutes for Diwali, roughly 3 minutes for Avni, plus a short transition. This is a target to measure, not a claimed timing or an assumed booked slot length. Actual ElevenLabs turn latency and the presenter’s answers determine the final script. Keep the family-beginnings questions short rather than rushing the text-to-family-to-Keep moment.

| Check | Pass condition |
|---|---|
| New-person baseline | Diwali opens with zero Currents and zero Captures; no Avni context is sent to the provider. |
| Onboarding response | Mentioning Diwali triggers the follow-up before unrelated setup questions; skip/correction and ambiguous mentions work. |
| Returning-person baseline | Avni has three Currents, two labelled seed Captures and completed onboarding. The Season offers the fast despite the unrelated recent thread. |
| Content boundary | Both scenes show only returned reviewed accounts; missing evidence does not cause invented verses, scholars or family facts. |
| Keep and ownership | Spoken confirmation commits exactly once to the active identity and intended Current. Citation snapshot and confirmed wording match what was displayed. |
| Visual link | Only a new committed Capture animates the calligraphic stroke into a branch. Failure, duplicate result, replay and seed loading do not. |
| Persistence and absence | Reload and Python restart restore each run. Simulated absence preserves depth. Close/reopen does not repeat onboarding or invent memory. |
| Isolation and reset | Run A cannot read/write Run B. Reset restores only the selected baseline; switching closes old audio and rejects late events/tool calls. |
| Voice failures | Autoplay denial, microphone denial, provider drop and expired credential produce recoverable visible states, not a false live continuation. |
| Safety boundaries | Separate checks still apply in both scenarios; a prepared Guard test stops playback/Flow and closes the Session. Grief alone is not a crisis decision. |

Rehearse each fresh run twice, then rehearse the transition between them. Also rehearse resume without resetting so persistence is demonstrable. Keep a backup recording for each scene with the same fixture/content version as the live build.

If ElevenLabs fails on stage, say the live connection has dropped and switch explicitly to that scene’s recording or labelled rehearsal mode. Do not narrate a recorded exchange as live. If corpus content is not ready, cut the unsupported claim or narrow the scene; do not invent a source. Sending, payments, additional festivals and unreviewed Tributaries remain outside the required demo.
