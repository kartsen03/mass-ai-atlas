#!/usr/bin/env node
/* Heartbeat-lite: is each Atlas investor still filing with the SEC, from Massachusetts?
 *
 * VC firms file Form ADV with the SEC every year, even between funds. The SEC publishes all
 * of it monthly as two zip files (registered and exempt reporting advisers). We download them
 * once, read only organization columns, and match the Atlas vc and angel entries by name.
 *
 *   node survey/heartbeat.js          -> uses the cached files when present
 *   node survey/heartbeat.js --live   -> downloads the latest files again
 *
 * Writes survey/out/heartbeat.json. No AI, no people: home addresses and phone numbers are never read.
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { DATA } = require("../scripts/load-data").loadData();

const PAGE = "https://www.sec.gov/data-research/sec-markets-data/information-about-registered-investment-advisers-exempt-reporting-advisers";
const UA = "mass-ai-atlas-survey/1.0 kaur.arsh@northeastern.edu";   // the SEC asks for a contact email
const CACHE = path.join(__dirname, "cache", "sec-adviser");
const OUT = path.join(__dirname, "out", "heartbeat.json");
const LIVE = process.argv.includes("--live");
const RECENT_DAYS = 456;   // about 15 months: the annual filing is due within 90 days of a firm's year end

async function get(url) {
  const res = await fetch(url, { headers: { "user-agent": UA }, signal: AbortSignal.timeout(60000) });
  if (!res.ok) throw new Error(`${res.status} for ${url}`);
  return res;
}

// The first exempt zip on the page is the newest; its registered twin has the same date ("ia100226-exempt" -> "ia100226")
async function download() {
  fs.mkdirSync(CACHE, { recursive: true });
  const have = fs.readdirSync(CACHE).filter(f => f.endsWith(".zip"));
  if (!LIVE && have.length >= 2) return have.map(f => path.join(CACHE, f));
  const html = await (await get(PAGE)).text();
  const zips = [...html.matchAll(/href="([^"]+\/ia[^"\/]+\.zip)"/g)].map(m => new URL(m[1], PAGE).href);
  const exempt = zips.find(u => /-exempt\.zip$/.test(u));
  const twin = exempt && zips.find(u => path.basename(u) === path.basename(exempt).replace("-exempt", ""));
  const pick = [exempt, twin].filter(Boolean);
  if (pick.length < 2) throw new Error("could not find this month's two adviser files on " + PAGE);
  for (const u of pick) {
    await new Promise(r => setTimeout(r, 500));
    fs.writeFileSync(path.join(CACHE, path.basename(u)), Buffer.from(await (await get(u)).arrayBuffer()));
  }
  return pick.map(u => path.join(CACHE, path.basename(u)));
}

// RFC 4180 CSV: quoted fields may hold commas, doubled quotes and newlines
function parseCsv(text) {
  const rows = [];
  let row = [], field = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') q = false;
      else field += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

const KEEP = {   // the only columns we read
  name: "Primary Business Name", legal: "Legal Name", crd: "Organization CRD#",
  city: "Main Office City", state: "Main Office State", status: "SEC Current Status",
  filed: "Latest ADV Filing Date", other: "Total number of offices, other than your Principal Office and place of business",
  home: "Main Office Private Residence Flag",
};

function readAdvisers(zip) {
  const rows = parseCsv(execFileSync("unzip", ["-p", zip], { maxBuffer: 512 * 1024 * 1024 }).toString("latin1"));
  const head = rows[0].map(h => h.trim());
  const col = Object.fromEntries(Object.entries(KEEP).map(([k, h]) => [k, head.indexOf(h)]));
  return rows.slice(1).filter(r => r.length > 5).map(r => {
    const o = Object.fromEntries(Object.entries(col).map(([k, i]) => [k, (r[i] || "").trim()]));
    o.file = path.basename(zip);
    return o;
  }).filter(o => o.home.toUpperCase() !== "Y");   // a home address is a person's data: never used
}

const norm = s => " " + s.toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim() + " ";
// "Bessemer Venture Partners (Boston)" -> BESSEMER VENTURE PARTNERS; "Matrix (fka Matrix Partners)" -> also MATRIX PARTNERS
function variants(name) {
  const m = name.match(/^(.*?)\s*\((?:fka\s+)?([^)]*)\)$/);
  const out = [m ? m[1] : name];
  if (m && m[2].includes(" ")) out.push(m[2]);
  // one generic word ("Matrix", "Pillar") would match strangers; require two words or a distinctive token
  return out.map(norm).filter(v => v.trim().split(" ").length >= 2 || v.trim().length >= 8);
}

const toIso = d => { const m = d.match(/^(\d{2})\/(\d{2})\/(\d{4})$/); return m ? `${m[3]}-${m[1]}-${m[2]}` : null; };
const active = s => /active|approved/i.test(s);

function heartbeat(d, advisers, today) {
  const vs = variants(d.name);
  const hits = advisers.filter(a => [a.name, a.legal].some(n => vs.some(v => norm(n).startsWith(v))));
  if (!hits.length) return { heartbeat: "not_found" };
  const score = a => (a.state === "MA" ? 2 : 0) + (active(a.status) ? 1 : 0);
  const best = hits.sort((a, b) => score(b) - score(a) || (toIso(b.filed) || "").localeCompare(toIso(a.filed) || ""))[0];
  const filed = toIso(best.filed);
  const recent = filed && (today - new Date(filed)) / 864e5 <= RECENT_DAYS;
  return {
    heartbeat: best.state !== "MA" ? "filed_outside_MA" : !active(best.status) || !recent ? "old_or_inactive" : "active_in_MA",
    record_name: best.name, city: best.city, state: best.state, sec_status: best.status, latest_filing: filed,
    other_offices: +best.other || 0,
    url: `https://adviserinfo.sec.gov/firm/summary/${best.crd}`,
    source: `SEC investment adviser data (${best.file})`,
  };
}

async function main() {
  const advisers = (await download()).flatMap(readAdvisers);
  const today = new Date();
  const rows = DATA.filter(d => d.cat === "vc" || d.cat === "angel")
    .map(d => ({ id: d.id, name: d.name, cat: d.cat, lastVerified: d.lastVerified, ...heartbeat(d, advisers, today) }));
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, "[\n" + rows.map(r => " " + JSON.stringify(r)).join(",\n") + "\n]\n");

  const count = (list, hb) => list.filter(r => r.heartbeat === hb).length;
  const stale = rows.filter(r => r.lastVerified === "2026-06");
  for (const r of stale) console.log(`  ${r.id.padEnd(14)} ${r.heartbeat.padEnd(17)} ${(r.record_name || "").padEnd(40)} ${r.city ? r.city + ", " + r.state : ""}  ${r.latest_filing || ""}`);
  console.log(`\nread ${advisers.length} SEC adviser records -> survey/out/heartbeat.json`);
  console.log(`Heartbeat · stale investors (last verified 2026-06) with an active SEC filing from MA: ${count(stale, "active_in_MA")} of ${stale.length}`);
  console.log(`           all Atlas investors: ${count(rows, "active_in_MA")} of ${rows.length} active in MA · ${count(rows, "filed_outside_MA")} file from outside MA · ${count(rows, "not_found")} not found`);
}

main().catch(e => { console.error(e.message); process.exit(1); });
