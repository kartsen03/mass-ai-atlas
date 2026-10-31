# Contract 3: the gap board (`chatbot/core/gaps.py` → `chatbot/app`)

Writer: Karthik (`chatbot/core/gaps.py`). Reader: Bhoomika (`chatbot/app/`).
The chatbot is the sensor: each submitted question records what it couldn't find. Arsh's
links (Contract 1) are the repairs. Changes go through the team, and Bhoomika commits them.

## Functions

```python
from chatbot.core.gaps import record, top

record(ans: dict) -> None      # ans = an answer() result in "before" mode
top(n: int = 10) -> list[dict] # today's gaps, most-hit first
```

- **The app calls `record()` once per submitted question** (Ask button, Enter, or an example).
  It never calls it on reruns, toggle flips or "Show on the map" clicks.
- The app passes the **`before`** answer, so the doubts are the original Atlas's. A gap that
  Arsh's links repaired then shows as `repaired` instead of disappearing.
- Neither function ever raises to the app. On any error, `record` does nothing and `top` returns `[]`.

## What is stored (privacy)

Per question, only: the date (`YYYY-MM-DD`), `needs`, `lacking`, `dead_end`, and for each result its `id`
plus the gap doubts it showed (`approximate pin`, `no stage listed`, `no connections`,
`no check size listed`, `deadline passed …`; "last verified" and open deadlines describe an entry, so they aren't gaps).
Labels outside the Atlas vocabulary are dropped. `kind: "chat"` answers are never recorded. **Never the raw query text**, and nothing about the person asking
(no IP, session id or timestamp finer than the day).

Stored at `GAPS_PATH` (default `chatbot/data/gaps.jsonl`). The file is gitignored, so it's never committed.

## `top(n)` item

```json
{"kind":"doubt","id":"sbxi","doubt":"no connections","need":null,
 "label":"SBXi: no connections","count":3,"status":"repaired",
 "repair":{"to_id":"glasswing","relation":"funded_by","source_url":"https://...","quote":"..."}}
```

| Field | Type | Notes |
|---|---|---|
| `kind` | string | `"doubt"` (a result showed a doubt signal) or `"dead_end"` (the Atlas had nothing for a need) |
| `id` | string or `null` | Atlas id for `doubt` items, and must exist in `atlas.json`. `null` for `dead_end` |
| `doubt` | string or `null` | One of the six doubt strings (Contract 2) for `doubt` items, else `null` |
| `need` | string or `null` | For `dead_end` items: a `lacking` label (Contract 2) from a question with `dead_end: true`. Else `null` |
| `label` | string | Short display text, built from the fields above |
| `count` | int | Questions asked **today** that hit this gap. The app labels it "questions asked today", **never "founders" or "people"** |
| `status` | string | `"open"`, `"queued"` or `"repaired"`, computed by core from `LINKS_PATH` (below) |
| `repair` | object or `null` | For `repaired`: the approved link (`to_id`, `relation`, `source_url`, `quote`). For `queued`: the pending one. Else `null` |

### Status rules

| Status | When |
|---|---|
| `repaired` | `doubt == "no connections"` and the links file has an **approved** link from `id` |
| `queued` | `doubt == "no connections"` and the links file has only a **pending** link from `id`. The app labels it "proposed, needs review" |
| `open` | Everything else, including every `dead_end` and the other five doubts, which links can't repair |

A repair is labelled "repaired by a reviewed link", never "verified". Rejected links never count.
Don't say the board chose Arsh's targets. It didn't: the board and Arsh's survey are independent.
