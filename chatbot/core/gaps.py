"""Gap board (Contract 3, contracts/gaps.schema.md): what each submitted question couldn't find.

record() keeps, per question, only the day, the parsed needs (Atlas vocabulary labels), whether it
was a dead end, and each result's id with the doubts it showed. Never the question text, and
nothing about who asked. top() ranks today's gaps and marks each open, queued or repaired from
the links file.
"""
import json
from collections import Counter
from datetime import date

from chatbot.core.answer import CAT_NOUN, GAP_PLACES, OFFER_LABEL, PLACES, STAGE_NAME, TAGS, _path, atlas, links

# Doubts that say something is missing or wrong. "last verified", "applications rolling" and
# "apply by" are on most entries and describe them, so they aren't gaps.
GAP_DOUBTS = ("approximate pin", "no stage listed", "no connections", "no check size listed")
_STATUS_ORDER = {"open": 0, "queued": 1, "repaired": 2}


def _file():
    return _path("GAPS_PATH", "chatbot/data/gaps.jsonl")


def _labels():
    """Every label answer() can put in `needs`. Anything else is dropped, so no free text is stored."""
    places = [p.title() for p in list(PLACES) + list(GAP_PLACES)] + ["west of Worcester", "outside Boston"]
    return (set(OFFER_LABEL.values()) | set(TAGS) | {"seed", "open to apply now"} | set(CAT_NOUN.values())
            | {n + " stage" for n in STAGE_NAME.values()} | {"place: " + p for p in places})


def _gap_doubt(x):
    return isinstance(x, str) and (x in GAP_DOUBTS or x.startswith("deadline passed "))


def record(ans):
    """Append one question's gaps. Call once per submitted question, with the "before" answer."""
    try:
        if not isinstance(ans, dict) or ans.get("kind") == "chat":
            return
        by_id, allowed = atlas()["by_id"], _labels()
        row = {"date": date.today().isoformat(),
               "needs": [n for n in ans.get("needs") or [] if n in allowed][:6],
               "lacking": [n for n in ans.get("lacking") or [] if n in allowed][:6],
               "dead_end": bool(ans.get("dead_end")),
               "results": [{"id": r["id"], "doubts": [x for x in r.get("doubts") or [] if _gap_doubt(x)]}
                           for r in ans.get("results") or [] if isinstance(r, dict) and r.get("id") in by_id]}
        path = _file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def _today():
    path, today = _file(), date.today().isoformat()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("date") == today:
            rows.append(row)
    return rows


def _status(eid, doubt, link_rows):
    """Only "no connections" can be repaired by a link: approved means repaired, pending means queued."""
    if doubt != "no connections":
        return "open", None
    for status, label in (("approved", "repaired"), ("pending", "queued")):
        r = next((r for r in link_rows if r["from_id"] == eid and r["status"] == status), None)
        if r:
            return label, {k: r.get(k) for k in ("to_id", "relation", "source_url", "quote")}
    return "open", None


def top(n=10):
    """Today's gaps, most-hit first; on a tie the most recently hit first, so the gaps of the
    question just asked show at the top of their count."""
    try:
        by_id, allowed = atlas()["by_id"], _labels()
        doubts, dead, last = Counter(), Counter(), {}
        for i, row in enumerate(_today()):
            for r in row.get("results") or []:
                for x in set(r.get("doubts") or []):
                    if r.get("id") in by_id and _gap_doubt(x):
                        doubts[(r["id"], x)] += 1
                        last[(r["id"], x)] = i
            if row.get("dead_end"):
                for need in set(row.get("lacking") or []):
                    if need in allowed:
                        dead[need] += 1
                        last[need] = i
        link_rows = links()
        items = []
        for need, count in dead.items():
            what = "anything in " + need[7:] if need.startswith("place: ") else need
            items.append({"kind": "dead_end", "id": None, "doubt": None, "need": need,
                          "label": f"Couldn't find {what}", "count": count, "status": "open", "repair": None,
                          "_last": last[need]})
        for (eid, doubt), count in doubts.items():
            status, repair = _status(eid, doubt, link_rows)
            items.append({"kind": "doubt", "id": eid, "doubt": doubt, "need": None,
                          "label": f"{by_id[eid]['name']}: {doubt}", "count": count, "status": status,
                          "repair": repair, "_last": last[(eid, doubt)]})
        items.sort(key=lambda it: (-it["count"], -it["_last"], it["kind"] != "dead_end",
                                   _STATUS_ORDER[it["status"]], it["label"].lower()))
        return [{k: v for k, v in it.items() if k != "_last"} for it in items[:max(int(n), 0)]]
    except Exception:
        return []
