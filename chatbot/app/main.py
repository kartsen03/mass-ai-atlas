"""Ask the Atlas: the founder-facing panel. Reads answer() output exactly as Contract 2 defines it."""

import html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

from chatbot.core.answer import answer  # noqa: E402  (also loads .env)

try:  # gap board (Contract 3). The panel works without it.
    from chatbot.core.gaps import record as gaps_record, top as gaps_top  # noqa: E402
except Exception:
    gaps_record = gaps_top = None

st.set_page_config(page_title="Ask the Atlas", page_icon="🧭", layout="centered")

EXAMPLES = [
    "tell me about SBXi",
    "AI investors in Springfield",
    "I'm a solo founder and I need people to bounce ideas off",
    "lab space for a biotech startup in Cambridge",
]

CSS = """
<style>
.badges{display:flex;flex-wrap:wrap;gap:.35rem;margin:.25rem 0 .6rem}
.badge{display:inline-block;padding:.12rem .55rem;border-radius:999px;font-size:.82rem;
  line-height:1.4;border:1px solid;white-space:nowrap}
.b-warn{background:rgba(245,158,11,.14);border-color:rgba(245,158,11,.55)}
.b-bad{background:rgba(239,68,68,.14);border-color:rgba(239,68,68,.6)}
.b-info{background:rgba(59,130,246,.12);border-color:rgba(59,130,246,.5)}
.b-ok{background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.5)}
.b-muted{background:rgba(127,127,127,.10);border-color:rgba(127,127,127,.45)}
.b-gone{text-decoration:line-through;opacity:.75;background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.5)}
.conn{margin:.35rem 0 .2rem;padding:.45rem .7rem;border-left:3px solid rgba(127,127,127,.45);border-radius:4px}
.conn.new{border-left-color:rgba(34,197,94,.8);background:rgba(34,197,94,.07)}
.conn.pending{border-left-color:rgba(245,158,11,.8);background:rgba(245,158,11,.06)}
.conn q{font-style:italic}
.small{font-size:.85rem;opacity:.85}
.acts{display:flex;flex-wrap:wrap;gap:.5rem;margin:.5rem 0 .1rem}
.act{display:inline-block;padding:.35rem .8rem;border-radius:8px;border:1px solid rgba(127,127,127,.45);
  text-decoration:none!important;font-size:.9rem}
button[kind^="primary"]{color:#111827!important}
a:focus-visible,button:focus-visible{outline:3px solid #3b82f6;outline-offset:2px}
</style>
"""


# ---------- data the panel needs beyond answer(): org names for connection targets ----------

@st.cache_data
def atlas_names(path: str) -> dict:
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))["data"]
        return {r["id"]: r.get("name", r["id"]) for r in rows}
    except Exception:
        return {}


def env_path(var: str, default: str) -> Path:
    p = Path(os.environ.get(var) or default)
    return p if p.is_absolute() else REPO / p


NAMES = atlas_names(str(env_path("ATLAS_PATH", "chatbot/data/atlas.json")))
LINKS_FILE = env_path("LINKS_PATH", "contracts/sample-proposed-links.json")

# Set by demo.html when the panel floats over the local Atlas site. Local hosts only.
SITE = st.query_params.get("site")
if not (isinstance(SITE, str) and re.match(r"^http://(localhost|127\.0\.0\.1)(:\d+)?/", SITE)):
    SITE = None


@st.cache_data(show_spinner=False)
def ask(query: str, mode: str) -> dict:
    return answer(query, mode)


# ---------- rendering helpers ----------

def e(s) -> str:
    # Escape HTML, and "$" so Streamlit doesn't render "$10K–$100K" as LaTeX math.
    return html.escape(str(s or "")).replace("$", "&#36;")


def md_text(s) -> str:
    """For plain st.info / st.warning text: keep dollar signs literal."""
    return str(s or "").replace("$", "\\$")


def safe_url(u) -> str | None:
    return u if isinstance(u, str) and re.match(r"^https?://", u) else None


def link(url, text) -> str:
    u = safe_url(url)
    return f'<a href="{e(u)}" target="_blank" rel="noopener">{e(text)}</a>' if u else e(text)


def months_old(yyyy_mm: str) -> int | None:
    m = re.match(r"(\d{4})-(\d{2})", yyyy_mm)
    if not m:
        return None
    t = date.today()
    return (t.year - int(m[1])) * 12 + (t.month - int(m[2]))


def badge_class(doubt: str) -> str:
    if doubt.startswith("deadline passed"):
        return "b-bad"
    if doubt.startswith("last verified"):
        age = months_old(doubt.removeprefix("last verified ").strip())
        return "b-warn" if age is not None and age >= 3 else "b-muted"
    if doubt.startswith("apply by"):
        return "b-info"
    if doubt == "applications rolling":
        return "b-ok"
    return "b-warn"  # approximate pin, no stage listed, no connections, no check size listed


HELP = {
    "approximate pin": "The map pin is approximate. Confirm the address before you visit.",
    "no stage listed": "The Atlas doesn't say what stage this startup is at.",
    "no connections": "No links to other Atlas organizations are recorded.",
    "no check size listed": "Offers funding, but no check size is listed. Ask before you pitch.",
    "applications rolling": "Applications are rolling, so there's no fixed deadline.",
}


def badge_help(doubt: str) -> str:
    if doubt.startswith("last verified"):
        return "The last month someone checked this entry."
    if doubt.startswith("apply by"):
        return "Application deadline."
    if doubt.startswith("deadline passed"):
        return "The listed deadline has passed. Check for the next round."
    return HELP.get(doubt, "")


def badges_html(doubts: list, resolved: list) -> str:
    parts = [f'<span class="badge {badge_class(d)}" title="{e(badge_help(d))}">{e(d)}</span>' for d in doubts]
    parts += [f'<span class="badge b-gone" title="Resolved by a reviewed link">{e(d)}</span>'
              f'<span class="badge b-ok">✓ resolved by a reviewed link</span>' for d in resolved]
    if not parts:
        return ""
    return f'<div class="badges" role="list" aria-label="Doubt signals">{"".join(parts)}</div>'


def connection_html(c: dict) -> str:
    to = NAMES.get(c.get("to_id"), c.get("to_id"))
    rel = (c.get("relation") or "").replace("_", " ")
    status = c.get("status")
    src = link(c.get("source_url"), "source")
    if status == "atlas":
        return f'<div class="conn">Connected to <b>{e(to)}</b> <span class="small">· listed in the Atlas · {src}</span></div>'
    quote = f'<br><q>{e(c.get("quote"))}</q>' if c.get("quote") else ""
    if status == "approved":
        return (f'<div class="conn new"><span class="badge b-ok">new · reviewed link</span> '
                f'<b>{e(to)}</b> <span class="small">({e(rel)}) · {src}</span>{quote}</div>')
    if status == "pending":
        return (f'<div class="conn pending"><span class="badge b-warn">proposed, needs review</span> '
                f'<b>{e(to)}</b> <span class="small">({e(rel)}) · {src} · not counted as a connection yet</span>{quote}</div>')
    return ""  # rejected or unknown: never shown


def show_on_map(entry_id: str):
    """Ask demo.html (the page hosting this panel) to open the entry on the Atlas map behind us."""
    origin = re.match(r"^https?://[^/]+", SITE)[0]
    msg = json.dumps({"type": "atlas-open", "id": entry_id})
    components.html(f"<script>window.top.postMessage({msg}, {json.dumps(origin)});</script>", height=0)


def render_result(rank: int, r: dict, before: dict | None, trust: dict | None):
    resolved = [d for d in (before or {}).get("doubts", []) if d not in r.get("doubts", [])]
    with st.container(border=True):
        st.markdown(f"#### {rank}. {e(r.get('name'))}", unsafe_allow_html=True)
        if trust and trust.get("id") == r.get("id"):
            st.markdown(f'<span class="badge b-warn">trust this one less</span> '
                        f'<span class="small">{e(trust.get("reason"))}</span>', unsafe_allow_html=True)
        # Doubts first: before the founder reads the pitch or clicks through.
        st.markdown(badges_html(r.get("doubts", []), resolved) or
                    '<div class="badges"><span class="badge b-ok">no doubt signals</span></div>',
                    unsafe_allow_html=True)
        st.markdown(f'{e(r.get("why"))}<br><span class="small">Source: {link(r.get("atlas_url"), "Atlas entry")}</span>',
                    unsafe_allow_html=True)
        conns = [c for c in r.get("connections", []) if c.get("status") in ("atlas", "approved", "pending")]
        if conns:
            st.markdown("".join(connection_html(c) for c in conns), unsafe_allow_html=True)
        entry_link = (f'<a class="act" href="{e(r["atlas_url"])}" target="_blank" rel="noopener">'
                      f'Open the Atlas entry ↗</a>') if safe_url(r.get("atlas_url")) else ""
        if SITE and r.get("id") in NAMES:
            c1, c2 = st.columns(2)
            if c1.button("📍 Show on the map", key=f"map-{rank}-{r['id']}", type="primary", use_container_width=True):
                show_on_map(r["id"])
            c2.markdown(f'<div class="acts">{entry_link}</div>', unsafe_allow_html=True)
        elif entry_link:
            st.markdown(f'<div class="acts">{entry_link}</div>', unsafe_allow_html=True)


# ---------- page ----------

st.markdown(CSS, unsafe_allow_html=True)
if SITE:  # embedded: demo.html already shows the title bar, so tighten the page
    st.markdown("<style>.block-container{padding:.9rem 1rem 2rem!important}"
                "h4{font-size:1.05rem!important;padding:.1rem 0!important}</style>", unsafe_allow_html=True)
    st.caption("A ranked shortlist from the Atlas. Every result has a source, and we show what we're unsure about.")
else:
    st.title("Ask the Atlas")
    st.caption("A shortlist of Massachusetts AI organizations, taken only from the Mass AI Atlas. "
               "Every result links to its source and shows what we're unsure about.")

if "query" not in st.session_state:
    st.session_state.query = ""


def submit(text: str):
    """A question was submitted (Ask, Enter or an example). Only here do we record it on the gap board."""
    st.session_state.query = text.strip()
    st.session_state.to_record = bool(st.session_state.query)


def pick_example(ex: str):
    # Runs as a callback (before the rerun), so it may set the text box's value.
    st.session_state.q_input = ex
    submit(ex)


def ask_view():
    # The text box has a fixed key. Passing value= instead gives it a new identity whenever the last
    # question changes, and Streamlit then drops what was just typed (every second question was lost).
    st.session_state.setdefault("q_input", "")
    with st.form("ask", clear_on_submit=False, border=False):
        q = st.text_input("What are you looking for?", key="q_input",
                          placeholder="e.g. pre-seed AI fund for MIT alumni")
        if st.form_submit_button("Ask", type="primary"):
            submit(q)

    if not st.session_state.query:  # examples only until the first question, to keep the panel short
        st.markdown('<span class="small">Try one:</span>', unsafe_allow_html=True)
        for i, ex in enumerate(EXAMPLES):
            st.button(ex, key=f"ex{i}", use_container_width=True, on_click=pick_example, args=(ex,))

    mode_label = st.radio(
        "Connections",
        ["Before: Atlas only", "After: + reviewed links"],
        index=1, horizontal=True,
        help="'After' adds links a person on our team reviewed and approved, each with its source sentence.",
    )
    mode = "after" if mode_label.startswith("After") else "before"

    query = st.session_state.query
    if not query:
        return
    with st.spinner("Searching the Atlas…"):
        res = ask(query, mode)
        before = ask(query, "before") if mode == "after" else res

    # Gap board: once per submitted question, always the "before" answer (Contract 3).
    # Chat replies (greetings, thanks, help, off-topic) carry no needs, so they're never recorded.
    is_chat = "chat" in (res.get("kind"), before.get("kind"))
    if st.session_state.pop("to_record", False):
        if gaps_record and not is_chat:
            try:
                gaps_record(before)
            except Exception:
                pass
        # Remember what this question hit, so the board can mark "from your question".
        st.session_state.last_hit = {"doubts": set(), "needs": set()} if is_chat else {
            "doubts": {(r.get("id"), d) for r in before.get("results", []) for d in r.get("doubts", [])},
            "needs": set(before.get("lacking") or []) if before.get("dead_end") else set(),
        }

    if is_chat:  # a normal bot reply, not a dead end
        with st.chat_message("assistant", avatar="🧭"):
            st.markdown(md_text(res.get("not_found")))
        return

    before_by_id = {r["id"]: r for r in before.get("results", [])} if mode == "after" else {}

    if res.get("understood"):
        st.markdown(f'**We read this as:** {e(res["understood"])} '
                    f'<span class="small">(our reading, not a fact)</span>', unsafe_allow_html=True)

    results = res.get("results", [])
    if res.get("not_found"):
        (st.warning if not results else st.info)(md_text(res["not_found"]))

    trust = res.get("trust")
    top_ids = [r.get("id") for r in results[:2]]
    if not (isinstance(trust, dict) and trust.get("id") in top_ids):
        trust = None

    for i, r in enumerate(results, 1):
        render_result(i, r, before_by_id.get(r.get("id")), trust)

    lacking = [x for x in res.get("lacking") or [] if isinstance(x, str)]
    if lacking:
        shown = " · ".join(e("anything in " + x[7:] if x.startswith("place: ") else x) for x in lacking)
        st.markdown(f'<span class="small"><b>Not in the Atlas:</b> {shown}</span>', unsafe_allow_html=True)

    if results:
        st.caption("Next step: open the Atlas entry, check the doubt signals with the organization, then reach out "
                   "through the contact route on their own site.")


MINE_TAG = ' <span class="badge b-info">← from your question</span>'

STATUS = {  # status -> (badge class, label)
    "repaired": ("b-ok", "repaired by a reviewed link"),
    "queued": ("b-info", "proposed, needs review"),
    "open": ("b-warn", "open"),
}


def gaps_view():
    st.markdown("Each question asked here records the gaps it hit: dead ends, and doubt signals on results. "
                "Some already have a repair: a reviewed link our survey found independently of this board.")
    st.caption("We store only the parsed needs and the Atlas ids, never the question text or anything about who asked. "
               "Counts include questions our team asked while testing today.")
    if not gaps_top:
        st.info("The gap board isn't connected yet (waiting for `chatbot/core/gaps.py`).")
        return
    try:
        everything = gaps_top(1000) or []
    except Exception:
        everything = []
    if not everything:
        st.info("No gaps recorded yet today. Ask a question in the Ask tab and it will show up here.")
        return
    items = everything[:10]  # the list shows the top 10; the totals count every gap today
    counts = {s: sum(1 for it in everything if it.get("status") == s) for s in STATUS}
    st.markdown(f'<div class="badges" aria-label="Totals for today">'
                f'<span class="badge b-warn">{counts["open"]} open</span>'
                f'<span class="badge b-info">{counts["queued"]} needs review</span>'
                f'<span class="badge b-ok">{counts["repaired"]} repaired</span></div>', unsafe_allow_html=True)
    hit = st.session_state.get("last_hit") or {"doubts": set(), "needs": set()}
    for it in items:
        mine = ((it.get("id"), it.get("doubt")) in hit["doubts"]) if it.get("kind") == "doubt" \
            else (it.get("need") in hit["needs"])
        cls, status_label = STATUS.get(it.get("status"), STATUS["open"])
        n = int(it.get("count") or 0)
        kind = "dead end" if it.get("kind") == "dead_end" else "doubt"
        head = (f'<div class="conn{" new" if it.get("status") == "repaired" else ""}">'
                f'<b>{e(it.get("label"))}</b> <span class="small">· {kind}</span>'
                f'{MINE_TAG if mine else ""}<br>'
                f'<span class="badge {cls}">{e(status_label)}</span> '
                f'<span class="small">{n} question{"s" if n != 1 else ""} asked today</span>')
        rep = it.get("repair") if it.get("status") in ("repaired", "queued") else None
        if isinstance(rep, dict) and rep.get("to_id") in NAMES:
            head += (f'<br><span class="small">→ {e(NAMES[rep["to_id"]])} '
                     f'({e((rep.get("relation") or "").replace("_", " "))}) · {link(rep.get("source_url"), "source")}</span>')
            if rep.get("quote"):
                head += f'<br><q>{e(rep["quote"])}</q>'
        st.markdown(head + "</div>", unsafe_allow_html=True)


tab_ask, tab_gaps = st.tabs(["Ask", "What people couldn't find"])
with tab_ask:
    ask_view()
with tab_gaps:
    gaps_view()

sample = "sample" in LINKS_FILE.name
st.divider()
st.caption(f"Data: frozen copy of the Mass AI Atlas ({len(NAMES)} organizations). "
           f"Reviewed links: `{LINKS_FILE.relative_to(REPO) if LINKS_FILE.is_relative_to(REPO) else LINKS_FILE.name}`"
           f"{' (sample file)' if sample else ''}. Pending links are shown as proposals and never counted.")
