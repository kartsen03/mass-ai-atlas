# Team TBTT: what we added to the Mass AI Atlas

Built on 31 October 2026 at the Chart the Common Wealth hackathon. The main `README.md` describes the
Atlas itself. This file covers only what our team added, for developers who want to run it, change it
or build on it.

We built two connected projects:

- **Track B: Ask the Atlas.** A chat assistant on top of the Atlas map that gives founders a ranked,
  sourced shortlist and shows every doubt about each entry. It includes a **gap board** that records
  what questions couldn't find.
- **Track A: Missing connections.** A pipeline that finds links between Atlas organizations on their
  own public websites, proves each one with the exact sentence, and lets a person approve it. It also
  adds a new probe, **heartbeat-lite**, based on SEC filings.

The two meet in the chatbot's **before/after toggle**: "after" adds Track A's approved links, so a
"no connections" doubt disappears and the source sentence is shown.

## What we built

| Feature | What it does | Code |
|---|---|---|
| Answer engine | `answer(query, mode)`: a ranked shortlist with reasons, sources and six doubt signals | `chatbot/core/answer.py` |
| Chat panel | The UI: doubt badges, sources, before/after toggle, honest dead ends | `chatbot/app/main.py` |
| Map widget | A chat icon and pop-up over the Atlas site; "Show on the map" opens the entry's drawer | `chatbot/app/demo.html`, `run_demo.sh` |
| Gap board | Records what each question couldn't find; marks each gap open, needs review or repaired | `chatbot/core/gaps.py`, panel tab |
| Missing connections | Finds sourced links for unconnected entries, with a human review gate | `survey/` |
| Heartbeat-lite | SEC adviser filings as evidence for investor entries that haven't been checked recently | `survey/heartbeat.js` |
| Contracts | The formats each piece reads and writes | `contracts/` |

## Results

- **Probe 2, entries with no links: 104 → 100.** Entries with no links in either direction: 74 → 69.
  The data validator passes on the `proposals` branch (`survey/out/validator-output.txt`).
- **Links:** 22 proposed: 7 approved, 13 rejected, 2 pending. Another 23 sentences about people were
  refused automatically.
- **Heartbeat-lite:** 12 of the 22 investors last verified in 2026-06 have a 2026 SEC adviser filing
  from Massachusetts.
- **Engine eval:** 235/235 checks pass (55 questions, keyword mode).

## Quick start

Needs Python 3.11+ for the chatbot, and Node 20 for the survey.

```bash
python3 -m venv .venv
.venv/bin/pip install -r chatbot/requirements.txt
cp .env.example .env        # optional: add ANTHROPIC_API_KEY to turn on the model reading
chatbot/app/run_demo.sh     # opens http://localhost:8000/chatbot/app/demo.html
```

`run_demo.sh` serves the repo's own `index.html` on port 8000 and the chatbot on port 8501. Stop it
with Ctrl+C.

| Task | Command |
|---|---|
| Chat page on its own (no map) | `.venv/bin/streamlit run chatbot/app/main.py` |
| Seed the gap board before a demo | `.venv/bin/python chatbot/app/seed_board.py` |
| Engine eval | `.venv/bin/python -m chatbot.core.eval_answer` (add `--model` to include the model) |
| Survey pipeline | See `survey/README.md` |

## How the pieces fit

```
data/entities.yml ── frozen copy ──> chatbot/data/atlas.json ───────────┐
survey/ (fetch → match → review) ──> survey/out/proposed-links.json ────┤
                                                                         ▼
                                                answer(query, mode)  chatbot/core/answer.py
                                                                         │
           map widget (demo.html over index.html) <── chat panel  chatbot/app/main.py
                                                                         │ once per question
                                                gaps.record() ──> chatbot/data/gaps.jsonl
                                                gaps.top()    ──> "What people couldn't find" tab

approved links ── survey/apply.js ──> data/entities.yml on the proposals branch (validated)
```

The chatbot reads a frozen copy of the Atlas (`chatbot/data/atlas.json`), so changes merged into the
Atlas during the event couldn't move the demo.

## 1. Ask the Atlas (Track B)

### Answer engine: `chatbot/core/answer.py`

- `answer(query, mode)`, where `mode` is `"before"` (Atlas only) or `"after"` (Atlas plus approved
  links). The ranking is the same in both modes. Only connections and doubts change.
- **Deterministic retrieval.** The question is matched against the Atlas's own vocabulary: offers,
  tags, founder stages, categories and Massachusetts places. Free text is ordered with BM25.
  Misspellings are tolerated, and named organizations come first. At most 8 results.
- **Optional model reading.** With `ANTHROPIC_API_KEY` set, a model (`CLAUDE_MODEL`, through the
  Anthropic API) maps unusual questions onto the same vocabulary, and each reading is cached. Without
  a key it runs on keywords only.
- **No invented organizations.** Every result id is checked against `atlas.json` in code. Names,
  reasons and doubts come only from Atlas fields.
- **Six doubt signals, computed in code:** approximate pin, last-verified month, startup with no stage,
  no connections, funder with no check size, and deadline (rolling, dated or passed).
- **Honest replies:**
  - a dead end says so and lists the nearest alternatives
  - out-of-state places get "Massachusetts only"
  - questions about people are refused
  - greetings and help get a normal reply
  - "who funded X" lists X's connections, with a note that the Atlas's own links don't say who funded whom
- It never raises. On an error it returns no results and "needs review".

### Chat panel: `chatbot/app/main.py` (Streamlit)

- **Result cards.** Each card shows its doubt badges first, then why it fits, with a link to the
  Atlas entry. Then come its connections:
  - links already in the Atlas
  - **new · reviewed link**, with the exact quote and a clickable source
  - **proposed, needs review**: shown, but not counted as a connection
- **Before/after toggle.** In "after", a doubt that an approved link resolves is struck through and
  marked "✓ resolved by a reviewed link".
- **Shows its reasoning openly:** "We read this as: … (our reading, not a fact)", a "trust this one
  less" line comparing the top two results, the `not_found` note, and a "Not in the Atlas:" line.
- **Safe output.** All Atlas text is HTML-escaped, and `$` is escaped so prices don't render as math.
  Only `http(s)` links are made clickable.

### Map widget: `chatbot/app/demo.html`

- Shows the repo's `index.html`, unchanged, full screen. The chatbot sits on top as a pop-up behind a
  chat icon.
- **Show on the map** sends a `postMessage` to the host page, which calls the Atlas's own
  `openDrawer(id)`. The pop-up then moves left so the drawer stays visible.
- Matches the Atlas's dark and yellow theme, skips the Atlas's first-visit tour, and fills the screen
  on phones. The × button closes it, and so does Esc when focus is outside the chat.
- **Local only.** The live site sends `X-Frame-Options: SAMEORIGIN`, so the widget can't frame it.
  Serving the repo's own copy works.

## 2. Gap board ("What people couldn't find")

A to-do list for the Atlas maintainers, built from real questions.

- `gaps.record(answer)` runs **once per submitted question**, with the "before" answer, so a gap that
  a link repaired shows as repaired instead of disappearing. It doesn't run on toggle flips, reruns
  or map clicks.
- **What's stored:** only the day, the parsed needs (Atlas vocabulary labels), what was lacking, and
  for the top 3 results, each id and its gap doubts. **Never the question text, and nothing about who
  asked.** Questions the vocabulary can't express (a person, a place outside Massachusetts,
  gibberish) store nothing.
- `gaps.top(n)` ranks today's gaps by how often they came up. Each gap's status comes from the links
  file:
  - **repaired:** an approved link exists
  - **needs review:** only a pending link exists
  - **open:** everything else
- The panel tab shows the totals, the top 10 gaps, a "← from your question" marker, and the link,
  source and quote for each repair.
- **Storage:** `chatbot/data/gaps.jsonl`, gitignored. `seed_board.py` lists the questions we seeded,
  and the board says its counts include our team's test questions. Counts are questions, not people.

## 3. Missing connections (Track A): `survey/`

Full details and commands are in `survey/README.md`. In short:

| Step | Command | What it does |
|---|---|---|
| Before | `node survey/probes.js` | Counts entries with no links |
| Fetch | `node survey/fetch.js` | Downloads each unconnected entry's homepage: honest user agent, robots.txt, 1 request per second per site, cached |
| Match | `node survey/match.js` | Finds other Atlas entries named on the page, keeps the exact sentence, labels the relation, scores confidence, skips existing links |
| Review | `node survey/review.js` | The human gate: approve, reject, skip, or open the page |
| Apply | `node survey/apply.js ../mass-ai-atlas-proposals` | Writes only approved links, only on the `proposals` branch |
| After | `node survey/probes.js` | Before/after numbers, plus calibration |

- **No AI in this pipeline.** The same pages always give the same proposals.
- **It refuses:**
  - sentences about people
  - indirect links (a page about a third company)
  - bare mentions
  - a global company standing in for its local office
  - LinkedIn, Meetup and social networks
- **Calibration:** approved / decided by confidence is high 6/11, medium 1/3, low 0/6.
- **Outputs, in `survey/out/`:**
  - `proposed-links.json`: Contract 1, read by the chatbot
  - `refusals.json`
  - `probes.json`
  - `sources.json`: every host contacted
  - `validator-output.txt`

## 4. Heartbeat-lite: `survey/heartbeat.js`

"Last verified 2026-06" only says when a person last looked. VC firms file an investment-adviser
filing (Form ADV) with the SEC every year, even between funds, so this script reads the SEC's monthly adviser data (organization columns only)
and matches each Atlas `vc` and `angel` entry by full name. It writes `survey/out/heartbeat.json`,
with an `adviserinfo.sec.gov` link per firm.

It's evidence for a person re-verifying an entry. It never writes `lastVerified` itself. "Active" is
the SEC's registration status, not a claim that a firm is investing. "Not found" is not evidence that
an organization is gone.

## Contracts: `contracts/`

| Contract | File | Between |
|---|---|---|
| 1. Proposed links | `proposed-links.schema.md` (+ `sample-proposed-links.json`) | survey → chatbot |
| 2. `answer()` output | `answer.schema.md` | engine → panel |
| 3. Gap board | `gaps.schema.md` | `gaps.py` → panel |

Optional fields can be ignored by older readers. Change a contract only by agreement, and update the
file first.

## Configuration (`.env`, never committed)

| Variable | Default in code | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | empty | Optional. Empty means keyword reading only |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | The model used for unusual questions |
| `ATLAS_PATH` | `chatbot/data/atlas.json` | The frozen Atlas copy |
| `LINKS_PATH` | `contracts/sample-proposed-links.json` | `.env.example` points it to `survey/out/proposed-links.json` |
| `GAPS_PATH` | `chatbot/data/gaps.jsonl` | The gap board file (gitignored) |

## Truth rules, enforced in code

- Only organizations in `atlas.json` appear, and ids are checked in code.
- Every claim has a source URL. Every new link shows its exact quote.
- A proposed link is labelled "proposed, needs review" until a person approves it. Rejected links
  are never shown.
- Organizations, not people. People questions are refused, Atlas sentences that name a person are
  skipped, and the survey refuses sentences about people.
- Massachusetts only.
- Public pages and documented APIs only.

## Testing

- **Engine eval:** `python -m chatbot.core.eval_answer` checks every answer against Contract 2, plus
  the gap board. 235/235 pass in keyword mode.
- **Data validator:** `node scripts/validate.js` passes on the `proposals` branch.
- **Browser tests:** the existing `npm run test:e2e` suite stayed green on GitHub Actions through the
  day.
- **End to end:** on the day we also drove the widget in Chrome. We checked keyboard-only use, phone
  width, all six doubts, the toggle, sources, dead ends and the gap board.

## Known limits and next steps

- **Keyboard:** the chat icon comes last in the page's tab order. Shift+Tab from the top of the page
  reaches it.
- **Phone:** the pop-up is 2px wider than the screen because of its border.
- **Names:** "Boston University" doesn't find the "BU Computing & Data Sciences" entry. It needs an
  alias.
- **Streamlit:** `st.components.v1.html` is deprecated in newer versions. Streamlit is pinned to
  1.66.1.
- **Gap board:** it counts only today's questions and lives in a local file. It belongs on a maintainer page, not in
  the founder chat.
- **Survey:** it reads homepages only, and JavaScript-only sites give no text. Next: read About,
  Portfolio and Partners pages.
- **Heartbeat-lite:** next, show its evidence in the chatbot under the "last verified" doubt.

## Team

- **Arsh**, Track A: `survey/`
- **Karthik**, Track B engine: `chatbot/core/`
- **Bhoomika**, Track B panel and map widget, contracts, repo setup: `chatbot/app/`, `contracts/`

*Data: Mass AI Atlas, The Open Accelerator, the-open-accelerator.com/ecosystem (CC BY 4.0).
Sources: the organizations' own public websites (listed in `survey/out/sources.json`) and the SEC's
investment adviser data (sec.gov, linked via adviserinfo.sec.gov).*
