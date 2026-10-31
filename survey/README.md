# Survey: missing connections (Track A)

Many Atlas entries show no connections, so the map hides that a program grew out of another
org, or that a fund backs a startup. This pipeline finds those connections on the orgs' own
public pages, proves each one with the exact sentence, and lets a human approve it before
anything touches the data.

**Probe 2, entries with no links: `104` → `100`** (no links in either direction: `74` → `69`).
Approved links are written only on the `proposals` branch, where `node scripts/validate.js` passes
(`out/validator-output.txt`).

## How it works

| Step | Command | What it does |
|---|---|---|
| Before | `node survey/probes.js` | Counts entries with no links. Writes `out/probes.json` |
| Fetch | `node survey/fetch.js` | Downloads the homepage of every entry with no links: honest user agent, robots.txt, 1 request per second per site, cached, no headless browser |
| Match | `node survey/match.js` | Finds other Atlas entries named on each page. Keeps the exact sentence, labels the relation, scores confidence, skips pairs already linked |
| Review | `node survey/review.js` | The human gate: approve, reject, skip, or open the page |
| Apply | `node survey/apply.js ../mass-ai-atlas-proposals` | Writes only approved links, only on the `proposals` branch, only the `links` line |
| After | `node survey/probes.js` | Before/after, plus calibration |

No AI anywhere in the pipeline: the same pages give the same proposals every time.

## Output (`out/`)

- `proposed-links.json`: Contract 1, read by the chatbot. 7 approved, 13 rejected, 2 pending.
- `refusals.json`: links refused automatically, with no quote kept, so no names are stored.
- `probes.json`: before/after and calibration.
- `sources.json`: every host contacted (the declared sources).

## What it refuses

- **Sentences about people** (bios, speaker cards, "former VP of…"). Refused automatically, 23 of them. The pipeline is about organizations, not people.
- **Indirect links**: for example, "Akooda is backed by Founder Collective" on Two Lanterns' site is about a third company. Rejected in review.
- **Bare mentions**: a news blurb that names a company is scored low. No low-confidence link was approved.
- **A global company standing in for its local office**: "NVIDIA" alone is capped below high for the NVIDIA (Westford) entry.
- **Blocked sites**: LinkedIn, Meetup and social networks are never fetched.

## Calibration (human decisions per confidence level)

| Confidence | Approved / decided |
|---|---|
| high | 6 / 11 |
| medium | 1 / 3 |
| low | 0 / 6 |

## Heartbeat-lite (a new probe)

"Last verified 2026-06" only says when a person last looked. VC firms leave a dated record of
their own every year: an investment-adviser filing (Form ADV) with the SEC, made even between funds.
`node survey/heartbeat.js` downloads the SEC's monthly adviser data once, reads only
organization columns (never home addresses or phone numbers), and matches every Atlas `vc` and
`angel` entry by full name. Output: `out/heartbeat.json`, with one clickable
`adviserinfo.sec.gov` link per firm.

**New probe, investors last verified 2026-06 with a 2026 SEC adviser filing from Massachusetts: `12` of `22`.**
Across all Atlas investors: `25` of `55` with a recent filing from MA, `2` file only from outside MA, `28` not found.
("Active" in the data is the SEC registration status, not a claim that a firm is investing.)

| Heartbeat | Means |
|---|---|
| `active_in_MA` | Active SEC adviser, main office in MA, filed in the last 15 months |
| `filed_outside_MA` | Files from another state (Bessemer: Larchmont, NY). This source can't see a Boston office, so it's **not** counted as evidence |
| `old_or_inactive` | Found, but the filing is old or the status isn't active |
| `not_found` | No match. Angel groups and corporate funds don't file this form. **Not evidence the org is gone** |

This is evidence for a person to use when re-verifying. It never writes `lastVerified` itself.
Next step: the chatbot shows it under the "last verified 2026-06" doubt, e.g. "SEC adviser filing 2026-03 (MA)".
It sits under the doubt as evidence; it does not clear it.

## Limits and next steps

Homepages only for now. A few sites block automated requests, and a few render with JavaScript
and give no text. Next: read About, Portfolio and Partners pages, and the pages of
already-connected orgs that name isolated ones.

*Data: Mass AI Atlas, The Open Accelerator — the-open-accelerator.com/ecosystem (CC BY 4.0). Sources: the organizations' own public websites, listed in `out/sources.json`, and the SEC's investment adviser data (www.sec.gov, linked via adviserinfo.sec.gov).*
