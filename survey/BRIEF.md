# Mass AI Atlas: Connections With Proof

**Track A (The Survey)** · Team TBTT · Chart the Common Wealth, 31 October 2026

## What we did

The Mass AI Atlas is a map of 197 AI organizations in Massachusetts. Founders use it to find
investors, programs and space. We built a tool that finds missing links between these
organizations on their own websites, keeps the exact sentence as proof, and lets a person
approve each link before it reaches the data. We also added a **heartbeat** check: for every
investor on the map, it looks for this year's filing with the SEC.

## The gap

- **104 of 197 entries show no connections.** A founder can't see that SBXi is backed by
  General Catalyst, or that StartUp Worcester is a joint program with WorcLab.
- **22 investors were last checked in June 2026.** The map shows the date, but nothing says
  whether they are still operating.
- **Links are typed in by hand**, and no tool finds them. Every fix waits on a maintainer's time.

## How it works

1. **Find:** read the homepage of every entry with no links (99 of 104 loaded).
2. **Prove:** look for other Atlas names in sentences like "backed by" or "a joint program of".
   Keep the page link and the exact sentence.
3. **Refuse:** drop sentences about people, links that already exist, and bare mentions.
4. **Approve:** a person says yes or no to each proposal.
5. **Apply:** approved links go on a separate `proposals` branch, and the Atlas's own validator must pass.
6. **Measure:** count again.

## Results

| Probe 2 | Before | After |
|---|---|---|
| Entries with no links | 104 | 100 |
| Entries with no links in either direction | 74 | 69 |

22 links proposed: 7 approved, 13 rejected, 2 waiting for review. 23 more were refused
automatically because they were about people.
**Heartbeat:** 12 of the 22 investors last checked in June have a 2026 SEC adviser filing from Massachusetts.

## Reliability: why you can trust it

- **Every link has a source.** Click the page and the sentence is there.
- **A person approves every link.** Nothing is written to the main data.
- **The validator passes** on the proposals branch.
- **No AI decides anything.** The same pages give the same proposals every time.
- **Confidence was checked against the human decisions:** high was approved 6 of 11 times,
  medium 1 of 3, low 0 of 6.
- **Organizations only.** Sentences about people are refused and not stored. LinkedIn and
  social sites are never fetched, and robots.txt is respected.
- **"Not found" never means "gone".** A firm that files from another state is marked "can't tell".

## Novelty: what's new

- **Questions point to the gaps.** Our team's chatbot records what founders' questions could not
  find, as a ranked list a maintainer could work from. Our pipeline proposes sourced links, a
  person decides, and once a link is approved, asking again shows it with the source sentence.
- **New evidence for "last verified".** VC firms update an SEC adviser filing every year, even
  between funds. That is a dated public record from a third party, where the map only had the
  date of the last human check.
- **Refusals are part of the output.** Every refused link is logged with its reason, so the
  system shows what it would not claim.

## Who it helps

- **Founders** see who backs whom and which program belongs to which, with the proof one click away.
- **The maintainer** gets a yes-or-no list instead of researching websites, and can start with
  what founders actually ask about.
- **The Atlas** stays accurate with less work from one person.

## Limits and next steps

- Homepages only for now. Next: About, Portfolio and Partners pages.
- One source per link (the organization's own site). Next: a second, independent source.
- Heartbeat covers investors only. Next: SEC fundraising filings for startups, IRS filings for
  nonprofits, and "SEC adviser filing 2026-03 (MA)" shown under the "last verified" warning in the chatbot.

*Data: Mass AI Atlas, The Open Accelerator (CC BY 4.0). Sources: the organizations' own websites
(`out/sources.json`) and SEC investment adviser data (sec.gov). Full method: `survey/README.md`.*
