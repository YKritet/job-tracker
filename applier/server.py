from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import db
from .search.base import (
    DOMAIN_KEYWORDS,
    POSTE_KEYWORDS,
    TAG_NAMES,
    skill_description,
)

app = FastAPI(title="Job Tracker")


@app.on_event("startup")
def _startup():
    db.init_db()
    jobs_json = db._DB_PATH.parent / "jobs.json"
    existing = db.get_all_jobs()
    if not existing and jobs_json.exists():
        n = db.import_from_json(jobs_json)
        print(f"  Auto-imported {n} jobs from {jobs_json}")


# ── API ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    return db.get_all_jobs(max_age_days=30)


@app.get("/api/skills")
def list_skills():
    return [
        {"label": s, "description": skill_description(s)}
        for s in db.get_distinct_skills()
    ]


class TrackingUpdate(BaseModel):
    url: str
    status: str | None = None
    applied_date: str | None = None


@app.patch("/api/tracking")
def patch_tracking(body: TrackingUpdate):
    db.update_tracking(body.url, body.status, body.applied_date, None)
    return {"ok": True}


# ── UI ───────────────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<title>Job Tracker</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#07090d;--s1:#0d1117;--s2:#161b22;--s3:#21262d;
  --b1:rgba(255,255,255,.06);--b2:rgba(255,255,255,.11);--b3:rgba(255,255,255,.18);
  --t1:#e6edf3;--t2:#8b949e;--t3:#484f58;
  --acc:#388bfd;--acc-d:rgba(56,139,253,.1);--acc-g:rgba(56,139,253,.18);
  --green:#3fb950;--green-d:rgba(63,185,80,.11);
  --teal:#2dd4bf;--teal-d:rgba(45,212,191,.11);
  --amber:#d29922;--amber-d:rgba(210,153,34,.11);
  --red:#f85149;--red-d:rgba(248,81,73,.11);
  --r:8px;--r-sm:5px;--r-lg:12px;
  --ease:cubic-bezier(.4,0,.2,1);
  --spring:cubic-bezier(.34,1.56,.64,1);
  --sb:238px;
  --nav-bg:rgba(7,9,13,.95);
  --row-hover:rgba(255,255,255,.022);
}
[data-theme="light"]{
  --bg:#f6f8fa;--s1:#ffffff;--s2:#f6f8fa;--s3:#eaeef2;
  --b1:rgba(0,0,0,.07);--b2:rgba(0,0,0,.13);--b3:rgba(0,0,0,.22);
  --t1:#1f2328;--t2:#57606a;--t3:#8c959f;
  --acc:#0969da;--acc-d:rgba(9,105,218,.1);--acc-g:rgba(9,105,218,.15);
  --green:#1a7f37;--green-d:rgba(26,127,55,.1);
  --teal:#0d7377;--teal-d:rgba(13,115,119,.1);
  --amber:#9a6700;--amber-d:rgba(154,103,0,.1);
  --red:#cf222e;--red-d:rgba(207,34,46,.1);
  --nav-bg:rgba(255,255,255,.95);
  --row-hover:rgba(0,0,0,.03);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--t1);
  min-height:100vh;font-size:13px;line-height:1.5;-webkit-font-smoothing:antialiased;
  font-feature-settings:"cv02","cv03","cv04","cv11"}

/* ── NAV ── */
nav{position:sticky;top:0;z-index:200;height:48px;
  display:flex;align-items:center;gap:10px;padding:0 16px;
  background:var(--nav-bg);backdrop-filter:blur(20px) saturate(1.8);
  border-bottom:1px solid var(--b1)}
.logo{width:26px;height:26px;border-radius:7px;flex-shrink:0;
  background:linear-gradient(145deg,#388bfd 0%,#6e40c9 100%);
  display:grid;place-items:center;
  box-shadow:0 0 0 1px rgba(56,139,253,.4),0 2px 12px rgba(56,139,253,.25)}
.logo svg{color:#fff}
.nav-title{font-size:13px;font-weight:600;letter-spacing:-.2px;color:var(--t1)}
.nav-sep{width:1px;height:16px;background:var(--b2);margin:0 2px}
.nav-r{margin-left:auto;display:flex;align-items:center;gap:6px}
.pill{font-size:11px;font-weight:600;color:var(--acc);
  background:var(--acc-d);border:1px solid rgba(56,139,253,.2);
  padding:2px 9px;border-radius:100px;letter-spacing:.1px;font-variant-numeric:tabular-nums}
.btn{display:flex;align-items:center;gap:5px;padding:5px 10px;
  background:var(--s2);border:1px solid var(--b1);border-radius:var(--r-sm);
  font:inherit;font-size:12px;color:var(--t2);cursor:pointer;
  transition:all 100ms var(--ease)}
.btn:hover{background:var(--s3);color:var(--t1);border-color:var(--b2)}
.btn-primary{background:rgba(56,139,253,.12);color:var(--acc);border-color:rgba(56,139,253,.22)}
.btn-primary:hover{background:rgba(56,139,253,.2);color:#79b8ff}

/* ── LAYOUT ── */
.layout{display:flex;height:calc(100vh - 48px);overflow:hidden}

/* ── SIDEBAR ── */
.sidebar{width:var(--sb);flex-shrink:0;background:var(--s1);
  border-right:1px solid var(--b1);display:flex;flex-direction:column;overflow:hidden}
.sb-top{display:flex;align-items:center;padding:10px 12px 8px;
  border-bottom:1px solid var(--b1);gap:8px}
.sb-top-title{font-size:10.5px;font-weight:600;color:var(--t3);
  text-transform:uppercase;letter-spacing:.8px;flex:1}
.sb-clear{font-size:11px;color:var(--t3);background:none;border:none;
  cursor:pointer;padding:2px 5px;border-radius:4px;font:inherit;transition:color 100ms}
.sb-clear:hover{color:var(--acc)}
.sb-scroll{flex:1;overflow-y:auto;padding-bottom:20px}
.sb-scroll::-webkit-scrollbar{width:2px}
.sb-scroll::-webkit-scrollbar-thumb{background:var(--b2);border-radius:2px}

/* ── DIM SECTIONS ── */
.dim{border-bottom:1px solid var(--b1)}
.dim-hdr{display:flex;align-items:center;gap:6px;padding:8px 12px;
  cursor:pointer;user-select:none;transition:background 80ms;position:relative}
.dim-hdr:hover{background:var(--row-hover)}
.dim-title{font-size:11px;font-weight:600;flex:1;color:var(--t2);letter-spacing:.05px}
.dim-count{font-size:9.5px;color:var(--t3);background:var(--s3);
  padding:1px 5px;border-radius:100px;flex-shrink:0;font-variant-numeric:tabular-nums}
.dim-icon{display:flex;align-items:center;flex-shrink:0}
.dim-badge{font-size:9px;font-weight:700;color:#fff;background:var(--acc);
  padding:0 5px;height:16px;display:inline-flex;align-items:center;
  border-radius:100px;margin-left:2px}
.dim-arrow{color:var(--t3);flex-shrink:0;transition:transform 150ms var(--ease)}
.dim-arrow.rotated{transform:rotate(-90deg)}
.dim-body{display:grid;grid-template-rows:1fr;transition:grid-template-rows 180ms var(--ease)}
.dim-body.collapsed{grid-template-rows:0fr}
.dim-body-inner{overflow:hidden;min-height:0}

/* company mini-search */
.co-search{padding:5px 8px 3px}
.co-si{width:100%;padding:4px 8px;background:var(--s2);border:1px solid var(--b1);
  border-radius:var(--r-sm);font:inherit;font-size:11px;color:var(--t1);outline:none}
.co-si::placeholder{color:var(--t3)}
.co-si:focus{border-color:var(--acc);box-shadow:0 0 0 2px var(--acc-g)}

/* checkbox rows */
.cb-list{padding:2px 4px 4px}
.cb-row{display:flex;align-items:center;gap:6px;padding:3.5px 8px;border-radius:5px;
  cursor:pointer;transition:background 60ms;user-select:none}
.cb-row:hover{background:rgba(255,255,255,.04)}
.cb-row input[type=checkbox]{width:12px;height:12px;accent-color:var(--acc);
  cursor:pointer;flex-shrink:0}
.pdot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.cb-label{font-size:11.5px;flex:1;color:var(--t2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.cb-row:has(input:checked) .cb-label{color:var(--t1)}
.cb-n{font-size:9.5px;color:var(--t3);flex-shrink:0;font-variant-numeric:tabular-nums}

/* location filter */
.loc-postal{padding:5px 8px 3px;display:flex;gap:4px}
.loc-cp-clear{background:none;border:none;color:var(--t3);cursor:pointer;font-size:16px;padding:0 3px;line-height:1;flex-shrink:0}
.loc-radius{padding:3px 8px 4px;display:flex;align-items:center;gap:6px}
.loc-radius-label{font-size:10px;color:var(--t3);white-space:nowrap;flex-shrink:0}
.loc-slider{flex:1;accent-color:var(--acc);cursor:pointer;height:3px}
.loc-km{font-size:10px;color:var(--t2);white-space:nowrap;min-width:42px;text-align:right;font-variant-numeric:tabular-nums}
.loc-geocoding{font-size:10px;color:var(--t3);padding:0 8px 4px;font-style:italic}

/* ── MAIN ── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.main-scroll{flex:1;overflow-y:auto}

/* ── STATS ── */
.stats{background:var(--s1);border-bottom:1px solid var(--b1);
  padding:0;display:flex;overflow-x:auto}
.stats::-webkit-scrollbar{display:none}
.sc{display:flex;flex-direction:column;gap:2px;padding:11px 18px;
  cursor:pointer;transition:background 100ms var(--ease);user-select:none;
  border-right:1px solid var(--b1);position:relative;flex-shrink:0;min-width:90px}
.sc:last-child{border-right:none}
.sc::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:transparent;transition:background 120ms var(--ease)}
.sc:hover{background:var(--row-hover)}
.sc.on{background:var(--row-hover)}
.sc-n{font-size:20px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}
.sc-l{font-size:10px;font-weight:500;color:var(--t3);text-transform:uppercase;
  letter-spacing:.6px;margin-top:1px}
.c-all .sc-n{color:var(--t1)}
.c-all.on::after{background:var(--t2)}
.c-todo .sc-n{color:var(--acc)}
.c-todo.on::after{background:var(--acc)}
.c-app .sc-n{color:var(--teal)}
.c-app.on::after{background:var(--teal)}
.c-int .sc-n{color:var(--green)}
.c-int.on::after{background:var(--green)}
.c-off .sc-n{color:var(--amber)}
.c-off.on::after{background:var(--amber)}
.c-rej .sc-n{color:var(--red)}
.c-rej.on::after{background:var(--red)}

/* ── TOOLBAR ── */
.toolbar{background:var(--s1);border-bottom:1px solid var(--b1);
  padding:8px 16px;display:flex;gap:7px;align-items:center}
.sw{position:relative;flex:1;min-width:160px}
.sw svg{position:absolute;left:9px;top:50%;transform:translateY(-50%);
  color:var(--t3);pointer-events:none;transition:color 100ms var(--ease)}
.sw:focus-within svg{color:var(--acc)}
.si{width:100%;padding:6px 11px 6px 30px;background:var(--s2);
  border:1px solid var(--b1);border-radius:var(--r);font:inherit;font-size:12.5px;
  color:var(--t1);outline:none;transition:100ms var(--ease)}
.si::placeholder{color:var(--t3)}
.si:focus{border-color:rgba(56,139,253,.5);box-shadow:0 0 0 3px var(--acc-g)}
.fb{padding:6px 26px 6px 9px;background:var(--s2);border:1px solid var(--b1);
  border-radius:var(--r);font:inherit;font-size:11.5px;color:var(--t2);
  cursor:pointer;outline:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%23484f58' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 7px center;transition:100ms var(--ease)}
.fb:focus{border-color:rgba(56,139,253,.5);box-shadow:0 0 0 3px var(--acc-g);color:var(--t1)}
.fb option{background:var(--s2)}
.ct{font-size:11px;color:var(--t3);white-space:nowrap;font-variant-numeric:tabular-nums}

/* ── TABLE ── */
.tw{padding:14px 16px 48px}
.tc{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r-lg);
  overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3)}
table{width:100%;border-collapse:collapse}
thead tr{background:var(--s2);border-bottom:1px solid var(--b1)}
th{padding:9px 12px;text-align:left;font-size:9.5px;font-weight:700;
  color:var(--t3);text-transform:uppercase;letter-spacing:.8px;
  white-space:nowrap;cursor:pointer;user-select:none;transition:color 100ms var(--ease)}
th:hover{color:var(--t2)}
th.asc::after{content:" ↑";color:var(--acc)}
th.desc::after{content:" ↓";color:var(--acc)}
tbody tr{border-bottom:1px solid var(--b1);transition:background 80ms var(--ease)}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:var(--row-hover)}
tbody tr.r-Applied{
  border-left:2px solid var(--teal);
  background:linear-gradient(90deg,rgba(45,212,191,.05) 0%,transparent 60%)}
tbody tr.r-Interview{
  border-left:2px solid var(--green);
  background:linear-gradient(90deg,rgba(63,185,80,.05) 0%,transparent 60%)}
tbody tr.r-Offer{
  border-left:2px solid var(--amber);
  background:linear-gradient(90deg,rgba(210,153,34,.06) 0%,transparent 60%)}
tbody tr.r-Rejected{opacity:.3;filter:saturate(0)}
tbody tr.r-Ignore{opacity:.18}
td{padding:9px 12px;vertical-align:middle}

/* Position cell */
.tt{max-width:160px;min-width:120px}
.tt a{color:var(--t1);text-decoration:none;font-weight:500;font-size:13px;
  display:block;line-height:1.4;transition:color 100ms var(--ease);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tt a:hover{color:var(--acc)}

.plat{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;
  border-radius:100px;font-size:10px;font-weight:600;white-space:nowrap;
  letter-spacing:.05px}
.plat-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}

/* Applied checkbox */
.acb{display:inline-grid;place-items:center;width:20px;height:20px;
  border-radius:5px;border:1.5px solid var(--b2);background:var(--s3);
  cursor:pointer;position:relative;transition:all 130ms var(--ease);
  vertical-align:middle}
.acb input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.acb svg{opacity:0;transform:scale(.35);
  transition:opacity 100ms var(--ease),transform 140ms var(--spring)}
.acb:has(input:checked){
  background:var(--teal);border-color:var(--teal);
  box-shadow:0 0 0 3px rgba(45,212,191,.15),0 1px 6px rgba(45,212,191,.3)}
.acb:has(input:checked) svg{opacity:1;transform:scale(1)}
.acb:hover:not(:has(input:checked)){border-color:rgba(56,139,253,.5);background:var(--s2)}

/* Date input */
.ci{padding:3px 6px;background:transparent;border:1px solid transparent;
  border-radius:var(--r-sm);font:inherit;font-size:11.5px;color:var(--t2);
  outline:none;transition:100ms var(--ease)}
.ci::-webkit-calendar-picker-indicator{filter:invert(.3);cursor:pointer;opacity:.6}
.ci:hover{border-color:var(--b2);background:var(--s2)}
.ci:focus{border-color:rgba(56,139,253,.5);background:var(--s2);
  box-shadow:0 0 0 3px var(--acc-g);color:var(--t1)}

.chip{display:inline-block;padding:2px 6px;border-radius:3px;
  font-size:10px;font-weight:600;margin:1px 2px 1px 0;white-space:nowrap;
  background:var(--s3);color:var(--t2);border:1px solid var(--b1);letter-spacing:.05px}
.chip-IT{background:rgba(56,139,253,.12);color:#79b8ff;border-color:rgba(56,139,253,.2)}
.chip-Security{background:rgba(248,81,73,.1);color:#ffa198;border-color:rgba(248,81,73,.18)}
.chip-Sales{background:rgba(45,212,191,.1);color:var(--teal);border-color:rgba(45,212,191,.18)}
.chip-Marketing{background:rgba(210,153,34,.1);color:var(--amber);border-color:rgba(210,153,34,.18)}
.chip-Finance{background:rgba(63,185,80,.1);color:var(--green);border-color:rgba(63,185,80,.18)}
.chip-Consulting{background:rgba(139,94,249,.12);color:#c9b1ff;border-color:rgba(139,94,249,.2)}
.chip-Remote{background:rgba(63,185,80,.1);color:#56d364;border-color:rgba(63,185,80,.18)}
.chip-Other{background:rgba(72,79,88,.2);color:#484f58;border-color:var(--b1)}
.chip-poste{background:rgba(210,153,34,.1);color:var(--amber);border-color:rgba(210,153,34,.18)}
.chip-domain{background:rgba(45,212,191,.1);color:var(--teal);border-color:rgba(45,212,191,.18)}
.chip-skill{background:rgba(139,94,249,.12);color:#c9b1ff;border-color:rgba(139,94,249,.2);cursor:help}

/* Thin table columns */
.tc2{max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:12px;color:var(--t2)}
.tl{max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:12px;color:var(--t2)}
.tk{white-space:nowrap;font-size:11.5px;color:var(--t3)}
.td-date{white-space:nowrap;font-size:11px;color:var(--t3);
  font-variant-numeric:tabular-nums;letter-spacing:.01em}

/* Tags cell */
.tg-cell{white-space:nowrap}
.tags-btn{font-size:10px;font-weight:600;color:var(--t3);
  background:var(--b1);border:1px solid var(--b2);border-radius:3px;
  padding:2px 7px;cursor:pointer;transition:all 100ms var(--ease);font-family:inherit}
.tags-btn:hover{color:var(--t1);background:var(--b2)}
.tags-panel{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}
.tags-panel[hidden]{display:none!important}

/* Theme toggle */
.theme-btn{display:grid;place-items:center;width:30px;height:30px;
  background:transparent;border:1px solid var(--b1);border-radius:var(--r-sm);
  cursor:pointer;color:var(--t2);transition:all 100ms var(--ease)}
.theme-btn:hover{background:var(--s3);color:var(--t1);border-color:var(--b2)}

.empty{display:none;flex-direction:column;align-items:center;
  gap:10px;padding:72px 24px;color:var(--t3)}
.empty svg{opacity:.18}
.empty p{font-size:14px;font-weight:500;color:var(--t2)}
.empty span{font-size:12.5px}

#toast{position:fixed;bottom:20px;right:20px;display:flex;align-items:center;gap:8px;
  background:var(--s2);border:1px solid var(--b2);color:var(--t1);
  padding:8px 14px;border-radius:var(--r);font-size:12.5px;font-weight:500;
  box-shadow:0 8px 24px rgba(0,0,0,.6);transform:translateY(8px) scale(.96);
  opacity:0;transition:opacity 160ms var(--ease),transform 160ms var(--ease);
  pointer-events:none;z-index:999}
#toast.on{opacity:1;transform:translateY(0) scale(1)}
.tdot{width:6px;height:6px;border-radius:50%;background:var(--green);
  box-shadow:0 0 5px var(--green);flex-shrink:0}

.loading{display:flex;align-items:center;justify-content:center;height:200px;
  color:var(--t3);font-size:12.5px;gap:10px}
.spin{width:16px;height:16px;border:1.5px solid var(--b2);border-top-color:var(--acc);
  border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.hidden{display:none!important}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:var(--s3);border-radius:3px}
::-webkit-scrollbar-track{background:transparent}
</style>
</head>
<body>

<nav>
  <div class="logo">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/>
    </svg>
  </div>
  <span class="nav-title">Job Tracker</span>
  <div class="nav-sep"></div>
  <span style="font-size:11px;color:var(--t3)">Hamza</span>
  <div class="nav-r">
    <span class="pill" id="total-pill">…</span>
    <button class="theme-btn" onclick="toggleTheme()" title="Toggle light/dark">
      <svg id="theme-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
    </button>
    <button class="btn" onclick="exportCSV()">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
      </svg>
      Export
    </button>
    <button class="btn btn-primary" onclick="loadJobs()">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
      </svg>
      Refresh
    </button>
  </div>
</nav>

<div class="layout">

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="sb-top">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--t3);flex-shrink:0">
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
      </svg>
      <span class="sb-top-title">Filters</span>
      <button class="sb-clear" onclick="clearAll()">Clear</button>
    </div>
    <div class="sb-scroll">
      <div id="dims"></div>
    </div>
  </aside>

  <!-- MAIN -->
  <main class="main">
    <div class="main-scroll">

      <!-- Stats bar -->
      <div class="stats">
        <div class="sc c-all on" onclick="statFilter('')" id="sc-all">
          <div class="sc-n" id="s-all">0</div><div class="sc-l">All</div>
        </div>
        <div class="sc c-todo" onclick="statFilter('not-applied')" id="sc-todo">
          <div class="sc-n" id="s-todo">0</div><div class="sc-l">Not Applied</div>
        </div>
        <div class="sc c-app" onclick="statFilter('Applied')" id="sc-app">
          <div class="sc-n" id="s-app">0</div><div class="sc-l">Applied</div>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar">
        <div class="sw">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input class="si" type="text" id="q" placeholder="Search title, company, location…" oninput="filter()">
        </div>
        <span class="ct" id="ct"></span>
      </div>

      <!-- Table -->
      <div class="tw">
        <div class="tc">
          <div id="loading" class="loading"><div class="spin"></div> Loading jobs…</div>
          <div style="overflow-x:auto;display:none" id="table-wrap">
            <table>
              <thead><tr>
                <th onclick="sort(0)">Position</th>
                <th onclick="sort(1)" style="width:130px">Company</th>
                <th onclick="sort(2)" style="width:110px">Location</th>
                <th onclick="sort(3)" style="width:74px">Type</th>
                <th onclick="sort(4)" style="width:100px">Platform</th>
                <th style="width:62px;cursor:default">Tags</th>
                <th style="text-align:center;width:38px;cursor:default"></th>
                <th onclick="sort(7)" style="width:58px">Date</th>
              </tr></thead>
              <tbody id="tbody"></tbody>
            </table>
          </div>
          <div class="empty" id="empty">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            </svg>
            <p>No results</p>
            <span>Try a different search or clear the filters</span>
          </div>
        </div>
      </div>

    </div><!-- main-scroll -->
  </main>

</div><!-- layout -->

<div id="toast"><span class="tdot"></span><span id="tmsg">Saved</span></div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
const AF = {
  q: '', status: '',
  postes:    new Set(),
  domains:   new Set(),
  platforms: new Set(),
  depts:     new Set(),
  regions:   new Set(),
  companies: new Set(),
  skills:    new Set(),
  tags:      new Set(),
};

const PLAT_COLORS = {
  'LinkedIn':     '#58a6ff',
  'FranceTravail':'#ffa657',
  'RemoteOK':     '#3fb950',
  'Indeed':       '#58c8ff',
  'WTTJ':         '#c9b1ff',
  'HelloWork':    '#f9826c',
  'APEC':         '#d2a679',
  'Keljob':       '#73b1d4',
  'AeroEmploi':   '#a0d4ff',
  'Adecco':       '#e05c5c',
  'Manpower':     '#e07c5c',
  'Randstad':     '#cc4444',
  'Synergie':     '#5c9de0',
  'Hays':         '#b44d4d',
  'Michael Page': '#2ecc71',
  'Cadremploi':   '#9b59b6',
  'Malt':         '#e74c3c',
  'JobEtudiant':  '#3498db',
  'Side':         '#1abc9c',
  'Meteojob':     '#4fc3f7',
  'Jobijoba':     '#81c784',
  'Monster':      '#6d4c41',
  'OptionCarriere':'#ff7043',
  'Staffme':      '#ab47bc',
};

const DIM_ICONS = {
  postes:    `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>`,
  domains:   `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  platforms: `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>`,
  locations: `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
  companies: `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>`,
  skills:    `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>`,
  tags:      `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`,
};
const DIMS = [
  { id:'postes',    title:'Postes',    key:'poste',    isArr:false },
  { id:'domains',   title:'Domains',   key:'domain',   isArr:false },
  { id:'platforms', title:'Platforms', key:'platform', isArr:false },
  { id:'companies', title:'Companies', key:'company',  isArr:false },
  { id:'skills',    title:'Skills',    key:'skills',   isArr:true  },
  { id:'tags',      title:'Tags',      key:'tags',     isArr:true  },
];

let SKILL_DESCS = {};
let jobs = [];
let activeStatus = '', sortCol = -1, sortDir = 1;

// ── Location helpers ──────────────────────────────────────────────────────────
const DEPT_NAMES = {
  '01':'Ain','02':'Aisne','03':'Allier','04':'Alpes-de-Haute-Provence','05':'Hautes-Alpes',
  '06':'Alpes-Maritimes','07':'Ardèche','08':'Ardennes','09':'Ariège','10':'Aube',
  '11':'Aude','12':'Aveyron','13':'Bouches-du-Rhône','14':'Calvados','15':'Cantal',
  '16':'Charente','17':'Charente-Maritime','18':'Cher','19':'Corrèze','2A':'Corse-du-Sud',
  '2B':'Haute-Corse','21':"Côte-d'Or",'22':"Côtes-d'Armor",'23':'Creuse','24':'Dordogne',
  '25':'Doubs','26':'Drôme','27':'Eure','28':'Eure-et-Loir','29':'Finistère',
  '30':'Gard','31':'Haute-Garonne','32':'Gers','33':'Gironde','34':'Hérault',
  '35':'Ille-et-Vilaine','36':'Indre','37':'Indre-et-Loire','38':'Isère','39':'Jura',
  '40':'Landes','41':'Loir-et-Cher','42':'Loire','43':'Haute-Loire','44':'Loire-Atlantique',
  '45':'Loiret','46':'Lot','47':'Lot-et-Garonne','48':'Lozère','49':'Maine-et-Loire',
  '50':'Manche','51':'Marne','52':'Haute-Marne','53':'Mayenne','54':'Meurthe-et-Moselle',
  '55':'Meuse','56':'Morbihan','57':'Moselle','58':'Nièvre','59':'Nord',
  '60':'Oise','61':'Orne','62':'Pas-de-Calais','63':'Puy-de-Dôme','64':'Pyrénées-Atlantiques',
  '65':'Hautes-Pyrénées','66':'Pyrénées-Orientales','67':'Bas-Rhin','68':'Haut-Rhin','69':'Rhône',
  '70':'Haute-Saône','71':'Saône-et-Loire','72':'Sarthe','73':'Savoie','74':'Haute-Savoie',
  '75':'Paris','76':'Seine-Maritime','77':'Seine-et-Marne','78':'Yvelines','79':'Deux-Sèvres',
  '80':'Somme','81':'Tarn','82':'Tarn-et-Garonne','83':'Var','84':'Vaucluse',
  '85':'Vendée','86':'Vienne','87':'Haute-Vienne','88':'Vosges','89':'Yonne',
  '90':'Territoire de Belfort','91':'Essonne','92':'Hauts-de-Seine','93':'Seine-Saint-Denis',
  '94':'Val-de-Marne','95':"Val-d'Oise",
  '971':'Guadeloupe','972':'Martinique','973':'Guyane','974':'La Réunion','976':'Mayotte'
};
const DEPT_COORDS = {
  '01':[46.17,5.28],'02':[49.54,3.63],'03':[46.34,3.00],'04':[44.14,6.23],'05':[44.66,6.29],
  '06':[43.94,7.18],'07':[44.81,4.44],'08':[49.77,4.71],'09':[42.93,1.48],'10':[48.29,4.08],
  '11':[43.21,2.35],'12':[44.36,2.57],'13':[43.53,5.45],'14':[49.07,-0.35],'15':[45.05,2.63],
  '16':[45.69,0.16],'17':[45.75,-0.69],'18':[47.08,2.40],'19':[45.34,1.88],'2A':[41.86,9.03],
  '2B':[42.37,9.28],'21':[47.32,4.83],'22':[48.44,-2.77],'23':[46.08,2.03],'24':[45.15,0.74],
  '25':[47.24,6.02],'26':[44.73,5.23],'27':[49.10,1.22],'28':[48.44,1.49],'29':[48.26,-4.06],
  '30':[43.96,4.23],'31':[43.60,1.44],'32':[43.64,0.58],'33':[44.84,-0.58],'34':[43.61,3.88],
  '35':[48.11,-1.68],'36':[46.81,1.62],'37':[47.39,0.69],'38':[45.19,5.72],'39':[46.67,5.56],
  '40':[43.96,-0.60],'41':[47.63,1.33],'42':[45.44,4.39],'43':[45.04,3.89],'44':[47.27,-1.51],
  '45':[47.90,2.00],'46':[44.61,1.67],'47':[44.36,0.46],'48':[44.50,3.50],'49':[47.37,-0.55],
  '50':[49.13,-1.39],'51':[49.05,4.06],'52':[48.11,5.14],'53':[48.07,-0.76],'54':[48.69,6.18],
  '55':[49.02,5.38],'56':[47.84,-2.75],'57':[49.12,6.77],'58':[47.11,3.52],'59':[50.39,3.23],
  '60':[49.41,2.40],'61':[48.56,0.07],'62':[50.52,2.61],'63':[45.77,3.08],'64':[43.29,-0.37],
  '65':[43.09,0.17],'66':[42.60,2.48],'67':[48.57,7.68],'68':[47.85,7.35],'69':[45.75,4.85],
  '70':[47.62,6.16],'71':[46.78,4.64],'72':[48.00,0.20],'73':[45.47,6.43],'74':[45.90,6.43],
  '75':[48.86,2.35],'76':[49.65,1.02],'77':[48.73,2.99],'78':[48.79,1.86],'79':[46.52,-0.33],
  '80':[49.92,2.30],'81':[43.91,2.15],'82':[44.02,1.36],'83':[43.46,6.24],'84':[43.95,5.36],
  '85':[46.67,-1.43],'86':[46.64,0.34],'87':[45.83,1.26],'88':[48.17,6.37],'89':[47.80,3.57],
  '90':[47.64,6.86],'91':[48.53,2.27],'92':[48.86,2.25],'93':[48.91,2.47],'94':[48.77,2.47],
  '95':[49.08,2.15],
  '971':[16.17,-61.58],'972':[14.64,-61.02],'973':[4.00,-53.00],'974':[-21.12,55.53],'976':[-12.82,45.17]
};
const REGION_DEPTS = {
  'Île-de-France':              ['75','77','78','91','92','93','94','95'],
  'Hauts-de-France':            ['02','59','60','62','80'],
  'Grand Est':                  ['08','10','51','52','54','55','57','67','68','88'],
  'Normandie':                  ['14','27','50','61','76'],
  'Bretagne':                   ['22','29','35','56'],
  'Pays de la Loire':           ['44','49','53','72','85'],
  'Centre-Val de Loire':        ['18','28','36','37','41','45'],
  'Bourgogne-Franche-Comté':    ['21','25','39','58','70','71','89','90'],
  'Auvergne-Rhône-Alpes':       ['01','03','07','15','26','38','42','43','63','69','73','74'],
  'Nouvelle-Aquitaine':         ['16','17','19','23','24','33','40','47','64','79','86','87'],
  'Occitanie':                  ['09','11','12','30','31','32','34','46','48','65','66','81','82'],
  'PACA':                       ['04','05','06','13','83','84'],
  'Corse':                      ['2A','2B'],
  'DOM-TOM':                    ['971','972','973','974','976'],
};
const DEPT_TO_REGION = {};
Object.entries(REGION_DEPTS).forEach(([r,ds]) => ds.forEach(d => DEPT_TO_REGION[d] = r));
let locFilter = { lat: null, lng: null, km: 50 };
let _postalTimer = null;

function parseDept(loc) {
  const m = (loc || '').match(/^(\\d{2,3}|2[AB])\\s*-/i);
  return m ? m[1].toUpperCase() : null;
}
function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371, r = Math.PI / 180;
  const dLat = (lat2 - lat1) * r, dLng = (lng2 - lng1) * r;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*r)*Math.cos(lat2*r)*Math.sin(dLng/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// ── Escape helpers ────────────────────────────────────────────────────────────
function ea(s){ return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
function eh(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── Utilities ─────────────────────────────────────────────────────────────────
function fmtDate(s) {
  if (!s) return '';
  const d = new Date(s + 'T00:00:00');
  return d.toLocaleDateString('en-GB', {day:'numeric', month:'short'});
}
function toggleTags(btn) {
  const panel = btn.nextElementSibling;
  panel.hidden = !panel.hidden;
  const n = btn.textContent.replace(/[+−]/,'');
  btn.textContent = (panel.hidden ? '+' : '−') + n;
}
function toggleTheme() {
  const html = document.documentElement;
  const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
  html.dataset.theme = next;
  localStorage.setItem('theme', next);
  const icon = document.getElementById('theme-icon');
  if (next === 'light') {
    icon.innerHTML = '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>';
  } else {
    icon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function countField(key, isArr) {
  const map = new Map();
  jobs.forEach(j => {
    const raw = j[key];
    const vals = isArr ? (Array.isArray(raw) ? raw : []) : (raw ? [raw] : []);
    vals.forEach(v => { if(v) map.set(v, (map.get(v)||0)+1); });
  });
  return [...map.entries()].sort((a,b) => b[1]-a[1]);
}

function buildSidebar() {
  const dims = document.getElementById('dims');
  dims.innerHTML = '';
  DIMS.forEach(d => {
    const counts = countField(d.key, d.isArr);
    if (!counts.length) return;
    const needSearch = counts.length > 6;
    const rows = counts.map(([v,n]) => {
      const dot = d.id === 'platforms'
        ? `<span class="pdot" style="background:${PLAT_COLORS[v]||'#6e7681'}"></span>`
        : '';
      return `<label class="cb-row" data-val="${ea(v.toLowerCase())}">
        <input type="checkbox" data-dim="${ea(d.id)}" data-v="${ea(v)}" onchange="toggleFilter(this.dataset.dim,this.dataset.v,this.checked)">
        ${dot}
        <span class="cb-label" title="${ea(v)}">${eh(v)}</span>
        <span class="cb-n">${n}</span>
      </label>`;
    }).join('');
    const search = needSearch
      ? `<div class="co-search"><input type="text" class="co-si" placeholder="Filter ${d.title.toLowerCase()}…" oninput="filterDim('${d.id}',this.value)"></div>`
      : '';
    const sec = document.createElement('div');
    sec.className = 'dim';
    sec.id = 'dim-' + d.id;
    sec.innerHTML = `
      <div class="dim-hdr" onclick="toggleDim('${d.id}')">
        <span class="dim-icon" style="color:var(--t3)">${DIM_ICONS[d.id]||''}</span>
        <span class="dim-title">${d.title}</span>
        <span class="dim-count">${counts.length}</span>
        <svg class="dim-arrow rotated" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg>
      </div>
      <div class="dim-body collapsed" id="db-${d.id}">
        <div class="dim-body-inner">
          ${search}
          <div class="cb-list" id="cl-${d.id}">${rows}</div>
        </div>
      </div>`;
    dims.appendChild(sec);
    if (d.id === 'platforms') dims.appendChild(buildLocationSection());
  });
}

function buildLocationSection() {
  // Count jobs per dept and region
  const deptCounts = new Map();
  jobs.forEach(j => {
    const dept = parseDept(j.location || '');
    if (dept) deptCounts.set(dept, (deptCounts.get(dept) || 0) + 1);
  });
  if (!deptCounts.size) return document.createDocumentFragment();

  // Region rows — only show regions that have matching jobs
  const regionRows = Object.entries(REGION_DEPTS).map(([name, depts]) => {
    const n = depts.reduce((s,d) => s + (deptCounts.get(d)||0), 0);
    if (!n) return '';
    return `<label class="cb-row" data-val="${ea(name.toLowerCase())}">
      <input type="checkbox" data-region="${ea(name)}" ${AF.regions.has(name)?'checked':''} onchange="toggleRegion(this.dataset.region,this.checked)">
      <span class="cb-label" title="${ea(name)}">${eh(name)}</span>
      <span class="cb-n">${n}</span>
    </label>`;
  }).filter(Boolean).join('');

  // Dept rows
  const sorted = [...deptCounts.entries()].sort((a,b) => b[1]-a[1]);
  const deptRows = sorted.map(([code, n]) => {
    const name = DEPT_NAMES[code] || '';
    const label = name ? `${code} – ${name}` : code;
    return `<label class="cb-row" data-val="${ea((code+' '+name).toLowerCase())}">
      <input type="checkbox" data-dept="${ea(code)}" ${AF.depts.has(code)?'checked':''} onchange="toggleDept(this.dataset.dept,this.checked)">
      <span class="cb-label" title="${ea(label)}">${eh(label)}</span>
      <span class="cb-n">${n}</span>
    </label>`;
  }).join('');

  const sec = document.createElement('div');
  sec.className = 'dim';
  sec.id = 'dim-locations';
  sec.innerHTML = `
    <div class="dim-hdr" onclick="toggleDim('locations')">
      <span class="dim-icon" style="color:var(--t3)">${DIM_ICONS.locations}</span>
      <span class="dim-title">Locations</span>
      <span class="dim-count">${sorted.length}</span>
      <svg class="dim-arrow rotated" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg>
    </div>
    <div class="dim-body collapsed" id="db-locations">
      <div class="dim-body-inner">
        <div class="loc-postal">
          <input id="loc-cp" type="text" class="co-si" placeholder="Code postal (rayon)…" maxlength="5" oninput="onPostalInput(this.value)" value="${locFilter._raw||''}">
          <button class="loc-cp-clear" id="loc-cp-clear" style="display:${locFilter.lat!==null?'':'none'}" onclick="clearPostal()">&#x00D7;</button>
        </div>
        <div class="loc-radius" id="loc-radius-row" style="display:${locFilter.lat!==null?'flex':'none'}">
          <span class="loc-radius-label">Rayon :</span>
          <input type="range" class="loc-slider" min="5" max="300" step="5" value="${locFilter.km}" id="loc-slider" oninput="onRadiusChange(this.value)">
          <span class="loc-km" id="loc-km">${locFilter.km} km</span>
        </div>
        <div id="loc-geocoding" class="loc-geocoding" style="display:none">Localisation…</div>
        <div class="loc-section-lbl">Régions</div>
        <div class="cb-list" id="cl-regions">${regionRows}</div>
        <div class="loc-section-lbl">Départements</div>
        <div class="co-search"><input type="text" class="co-si" placeholder="Département…" oninput="filterLocDim(this.value)"></div>
        <div class="cb-list" id="cl-locations">${deptRows}</div>
      </div>
    </div>`;
  return sec;
}

function toggleDim(id) {
  const body  = document.getElementById('db-' + id);
  const arrow = document.querySelector('#dim-' + id + ' .dim-arrow');
  body.classList.toggle('collapsed');
  if (arrow) arrow.classList.toggle('rotated');
}

function filterDim(id, q) {
  const list = document.getElementById('cl-' + id);
  if (!list) return;
  const lq = q.toLowerCase();
  list.querySelectorAll('.cb-row').forEach(row => {
    row.classList.toggle('hidden', !!lq && !row.dataset.val.includes(lq));
  });
}

function filterLocDim(q) {
  const list = document.getElementById('cl-locations');
  if (!list) return;
  const lq = q.toLowerCase();
  list.querySelectorAll('.cb-row').forEach(row => {
    row.classList.toggle('hidden', !!lq && !row.dataset.val.includes(lq));
  });
}

function toggleDept(code, checked) {
  if (checked) AF.depts.add(code); else AF.depts.delete(code);
  updateDimBadges();
  filter();
}

function onPostalInput(val) {
  clearTimeout(_postalTimer);
  const clean = val.replace(/\D/g,'');
  if (clean.length === 5) {
    _postalTimer = setTimeout(() => geocodePostal(clean), 600);
  } else if (!clean) {
    clearPostal();
  }
}

async function geocodePostal(code) {
  const geo = document.getElementById('loc-geocoding');
  const btn = document.getElementById('loc-cp-clear');
  if (geo) geo.style.display = 'block';
  try {
    const url = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(code)}&countrycodes=fr&format=json&limit=1`;
    const res = await fetch(url, { headers: { 'Accept-Language': 'fr' } });
    const data = await res.json();
    if (data && data.length) {
      locFilter.lat = parseFloat(data[0].lat);
      locFilter.lng = parseFloat(data[0].lon);
      locFilter._raw = code;
      const radRow = document.getElementById('loc-radius-row');
      if (radRow) radRow.style.display = 'flex';
      if (btn) btn.style.display = '';
      updateDimBadges();
      filter();
    }
  } catch(_) {}
  if (geo) geo.style.display = 'none';
}

function onRadiusChange(val) {
  locFilter.km = parseInt(val, 10);
  const lbl = document.getElementById('loc-km');
  if (lbl) lbl.textContent = locFilter.km + ' km';
  filter();
}

function clearPostal() {
  locFilter.lat = null;
  locFilter.lng = null;
  locFilter._raw = '';
  const inp = document.getElementById('loc-cp');
  if (inp) inp.value = '';
  const radRow = document.getElementById('loc-radius-row');
  if (radRow) radRow.style.display = 'none';
  const btn = document.getElementById('loc-cp-clear');
  if (btn) btn.style.display = 'none';
  updateDimBadges();
  filter();
}

function toggleFilter(dim, value, checked) {
  if (checked) AF[dim].add(value); else AF[dim].delete(value);
  updateDimBadges();
  filter();
}

function updateDimBadges() {
  DIMS.forEach(d => {
    const hdr = document.querySelector('#dim-' + d.id + ' .dim-hdr');
    if (!hdr) return;
    const old = hdr.querySelector('.dim-badge');
    if (old) old.remove();
    if (AF[d.id].size > 0) {
      const b = document.createElement('span');
      b.className = 'dim-badge';
      b.textContent = AF[d.id].size;
      hdr.insertBefore(b, hdr.querySelector('.dim-arrow'));
    }
  });
  // Location dim badge
  const locHdr = document.querySelector('#dim-locations .dim-hdr');
  if (locHdr) {
    const old = locHdr.querySelector('.dim-badge');
    if (old) old.remove();
    const n = AF.depts.size + (locFilter.lat !== null ? 1 : 0);
    if (n > 0) {
      const b = document.createElement('span');
      b.className = 'dim-badge'; b.textContent = n;
      locHdr.insertBefore(b, locHdr.querySelector('.dim-arrow'));
    }
  }
}

function clearAll() {
  DIMS.forEach(d => AF[d.id].clear());
  AF.depts.clear();
  clearPostal();
  AF.q = ''; AF.status = '';
  document.getElementById('q').value = '';
  document.querySelectorAll('.cb-row input[type=checkbox]').forEach(cb => cb.checked = false);
  updateDimBadges();
  activeStatus = '';
  document.querySelectorAll('.sc').forEach(c => c.classList.remove('on'));
  document.getElementById('sc-all').classList.add('on');
  filter();
}

// ── Skills ────────────────────────────────────────────────────────────────────
async function loadSkills() {
  try {
    const skills = await (await fetch('/api/skills')).json();
    SKILL_DESCS = Object.fromEntries(skills.map(s => [s.label, s.description]));
  } catch(e) { /* no skills yet */ }
}

// ── Jobs ──────────────────────────────────────────────────────────────────────
async function loadJobs() {
  document.getElementById('loading').style.display = 'flex';
  document.getElementById('table-wrap').style.display = 'none';
  try {
    const res = await fetch('/api/jobs');
    jobs = await res.json();
    jobs.sort((a,b) => (b.pulled_at||'') > (a.pulled_at||'') ? 1 : (b.pulled_at||'') < (a.pulled_at||'') ? -1 : 0);
    document.getElementById('total-pill').textContent = jobs.length + ' jobs';
    buildSidebar();
    renderRows();
    document.getElementById('loading').style.display = 'none';
    document.getElementById('table-wrap').style.display = 'block';
  } catch(e) {
    document.getElementById('loading').innerHTML = '<span style="color:var(--red)">Failed to load — is the server running?</span>';
  }
}

function renderRows() {
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = jobs.map((j,i) => {
    const st    = j.status || '';
    const tags  = Array.isArray(j.tags)   ? j.tags   : [];
    const skills= Array.isArray(j.skills) ? j.skills : [];
    const poste = j.poste  || '';
    const domain= j.domain || '';
    const platColor  = PLAT_COLORS[j.platform] || '#6e7681';
    const platStyle  = `background:${platColor}1a;color:${platColor};border:1px solid ${platColor}33`;
    const allTags = [
      ...(poste  ? [{cls:'chip-poste',  v:poste}]  : []),
      ...(domain ? [{cls:'chip-domain', v:domain}] : []),
      ...skills.map(s => ({cls:'chip-skill', v:s, title:SKILL_DESCS[s]||s})),
      ...tags.map(t => ({cls:`chip-${t}`, v:t})),
    ];
    const tagsCell = allTags.length === 0 ? '' :
      `<button class="tags-btn" onclick="toggleTags(this)">+${allTags.length}</button>` +
      `<div class="tags-panel" hidden>${allTags.map(c =>
        `<span class="chip ${c.cls}"${c.title?` title="${ea(c.title)}"`:''}>${eh(c.v)}</span>`
      ).join('')}</div>`;
    const dateStr = j.pulled_at ? fmtDate(j.pulled_at) : '';
    return `<tr class="jr r-${ea(st)}"
      data-i="${i}"
      data-title="${ea(j.title.toLowerCase())}"
      data-company="${ea((j.company||'').toLowerCase())}"
      data-co="${ea(j.company||'')}"
      data-loc="${ea(j.location||'')}"
      data-location="${ea((j.location||'').toLowerCase())}"
      data-platform="${ea(j.platform)}"
      data-tags="${ea(tags.join(','))}"
      data-poste="${ea(poste)}"
      data-domain="${ea(domain)}"
      data-skills="${ea(skills.join('|'))}"
      data-status="${ea(st)}"
      data-pulled="${ea(j.pulled_at||'')}"
      data-url="${ea(j.url)}">
      <td class="tt"><a href="${ea(j.url)}" target="_blank" rel="noopener">${eh(j.title)}</a></td>
      <td class="tc2">${eh(j.company||'')}</td>
      <td class="tl">${eh(j.location||'')}</td>
      <td class="tk">${eh(j.contract||'')}</td>
      <td><span class="plat" style="${platStyle}">
        <span class="plat-dot" style="background:${platColor}"></span>${eh(j.platform)}
      </span></td>
      <td class="tg-cell">${tagsCell}</td>
      <td style="text-align:center">
        <label class="acb" title="${st==='Applied'?'Applied — click to undo':'Mark as applied'}">
          <input type="checkbox" ${st==='Applied'?' checked':''} onchange="updateStatus(this)">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>
        </label>
      </td>
      <td class="td-date">${dateStr}</td>
    </tr>`;
  }).join('');
  filter();
}

// ── Filter ────────────────────────────────────────────────────────────────────
function filter() {
  const q   = document.getElementById('q').value.toLowerCase();
  const rows= document.querySelectorAll('.jr');
  let v = 0;
  rows.forEach(r => {
    const txt= r.dataset.title + ' ' + r.dataset.company + ' ' + r.dataset.location;
    const applied = r.dataset.status === 'Applied';
    const ok =
      (!q                    || txt.includes(q))
      && (activeStatus === ''|| (activeStatus === 'Applied' && applied) || (activeStatus === 'not-applied' && !applied))
      && (AF.postes.size   === 0 || AF.postes.has(r.dataset.poste))
      && (AF.domains.size  === 0 || AF.domains.has(r.dataset.domain))
      && (AF.platforms.size=== 0 || AF.platforms.has(r.dataset.platform))
      && (() => {
          const dept = parseDept(r.dataset.loc);
          if (AF.depts.size > 0 && !AF.depts.has(dept)) return false;
          if (locFilter.lat !== null && locFilter.km > 0) {
            if (!dept) return false;
            const c = DEPT_COORDS[dept]; if (!c) return false;
            if (haversine(locFilter.lat, locFilter.lng, c[0], c[1]) > locFilter.km) return false;
          }
          return true;
        })()
      && (AF.companies.size=== 0 || AF.companies.has(r.dataset.co))
      && (AF.skills.size   === 0 || r.dataset.skills.split('|').some(s => AF.skills.has(s)))
      && (AF.tags.size     === 0 || r.dataset.tags.split(',').some(t => AF.tags.has(t)));
    r.classList.toggle('hidden', !ok);
    if (ok) v++;
  });
  document.getElementById('ct').textContent = v === rows.length
    ? `${rows.length} results` : `${v} of ${rows.length}`;
  document.getElementById('empty').style.display = v===0 ? 'flex' : 'none';
  updateStats();
}

function updateStats() {
  const rows = document.querySelectorAll('.jr:not(.hidden)');
  let applied = 0;
  rows.forEach(r => { if (r.dataset.status === 'Applied') applied++; });
  document.getElementById('s-all').textContent  = rows.length;
  document.getElementById('s-todo').textContent = rows.length - applied;
  document.getElementById('s-app').textContent  = applied;
}

function statFilter(s) {
  activeStatus = s;
  document.querySelectorAll('.sc').forEach(c => c.classList.remove('on'));
  const map = {'':'sc-all','not-applied':'sc-todo','Applied':'sc-app'};
  document.getElementById(map[s] || 'sc-all')?.classList.add('on');
  filter();
}

// ── Sort ──────────────────────────────────────────────────────────────────────
function sort(col) {
  const tbody = document.getElementById('tbody');
  const rows  = [...tbody.querySelectorAll('tr.jr')];
  sortDir = sortCol===col ? sortDir*-1 : 1; sortCol=col;
  rows.sort((a,b) => {
    const av=col===7 ? (a.dataset.pulled||'') : (a.cells[col]?.textContent.trim().toLowerCase()||'');
    const bv=col===7 ? (b.dataset.pulled||'') : (b.cells[col]?.textContent.trim().toLowerCase()||'');
    return av<bv?-sortDir:av>bv?sortDir:0;
  });
  rows.forEach(r=>tbody.appendChild(r));
  document.querySelectorAll('th').forEach((th,i)=>{
    th.classList.remove('asc','desc');
    if(i===col) th.classList.add(sortDir===1?'asc':'desc');
  });
}

// ── Tracking ──────────────────────────────────────────────────────────────────
async function updateStatus(cb) {
  const row   = cb.closest('tr');
  const url   = row.dataset.url;
  const value = cb.checked ? 'Applied' : '';
  const idx   = parseInt(row.dataset.i);
  jobs[idx].status = value;
  row.className = [...row.classList].filter(c => !c.startsWith('r-')).join(' ')
                + (value ? ' r-' + value : '');
  row.dataset.status = value;
  cb.closest('label').title = value === 'Applied' ? 'Applied — click to undo' : 'Mark as applied';
  filter();
  try {
    await fetch('/api/tracking', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, status: value}),
    });
    toast(value === 'Applied' ? '✓ Applied' : 'Marked to apply');
  } catch { toast('Save failed'); }
}

async function update(el, field) {
  const row   = el.closest('tr');
  const url   = row.dataset.url;
  const value = el.value;
  const idx   = parseInt(row.dataset.i);
  jobs[idx][field] = value;
  try {
    await fetch('/api/tracking', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, [field]: value}),
    });
    toast('Saved');
  } catch { toast('Save failed'); }
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportCSV() {
  const rows = document.querySelectorAll('.jr:not(.hidden)');
  const lines = [['Title','Company','Location','Contract','Platform','Tags','Skills','URL','Applied','Applied Date'].join(',')];
  rows.forEach(r => {
    const i = parseInt(r.dataset.i);
    const j = jobs[i];
    lines.push([j.title,j.company,j.location,j.contract,j.platform,
                (j.tags||[]).join('|'),(j.skills||[]).join('|'),
                j.url,j.status==='Applied'?'Yes':'',j.applied_date]
      .map(v=>`"${String(v||'').replace(/"/g,'""')}"`)
      .join(','));
  });
  const blob = new Blob([lines.join('\\n')], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'jobs_export.csv';
  a.click();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let _tt;
function toast(msg) {
  const t=document.getElementById('toast');
  document.getElementById('tmsg').textContent=msg;
  t.classList.add('on');
  clearTimeout(_tt);
  _tt=setTimeout(()=>t.classList.remove('on'),1800);
}

// Restore theme from localStorage before first paint
(function(){const t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t;})();
loadSkills();
loadJobs();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return _HTML
