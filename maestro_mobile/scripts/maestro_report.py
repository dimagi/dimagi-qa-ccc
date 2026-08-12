"""Maestro run report - JSON for CI to parse, HTML for people to read.

Layout follows the CommCare Mobile suite's report_generator.py so the two read the
same way: KPI cards and a pass-rate donut up top, a trend line across recent runs,
then a filterable table with failures first and each failure's step and screenshot
inline.

Kept separate from run_on_browserstack.py, which is about driving BrowserStack -
rendering is a different job and this is most of the code by volume.
"""

import datetime
import json
from pathlib import Path

HISTORY_LIMIT = 30  # older runs roll off so the trend stays readable
STATUS_ORDER = ("passed", "failed", "skipped")
ROW_SORT_ORDER = ("failed", "skipped", "passed")  # failures first - nobody opens a report for the passes
STATUS_COLORS = {"passed": "#15924d", "failed": "#d33030", "skipped": "#9aa3b5"}
STATUS_LABELS = {"passed": "Passed", "failed": "Failed", "skipped": "Skipped"}


def _escape(text):
    return (
        str(text if text is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def extract_failed_step(log):
    """The Maestro step that failed, from the flow's step log.

    Maestro logs each command twice - RUNNING then COMPLETED/FAILED/WARNED - so the
    last line ending in FAILED names the step that actually stopped the flow. Worth
    surfacing in the report: it is the one line anyone reading a failure wants, and
    finding it otherwise means scrolling a few thousand lines of log.
    """
    if not log:
        return None
    marker = "TestSuiteInteractor.invoke: "
    for line in reversed(log.splitlines()):
        if marker in line and line.rstrip().endswith("FAILED"):
            step = line.split(marker, 1)[1].rstrip()
            return step[: -len(" FAILED")].strip()
    return None


def counts_from(summary):
    counts = {key: summary.get(key, 0) or 0 for key in STATUS_ORDER}
    counts["total"] = sum(counts[key] for key in STATUS_ORDER)
    counts["pass_rate"] = round(counts["passed"] / counts["total"] * 100) if counts["total"] else 0
    return counts


def render_donut(counts, size=112, radius=46, stroke=14):
    total = counts["total"]
    if not total:
        return ""
    circumference = 2 * 3.14159265 * radius
    offset = 0.0
    arcs = []
    for key in STATUS_ORDER:
        value = counts[key]
        if not value:
            continue
        length = circumference * value / total
        arcs.append(
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" '
            f'stroke="{STATUS_COLORS[key]}" stroke-width="{stroke}" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {size / 2} {size / 2})"></circle>'
        )
        offset += length
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" '
        f'aria-label="{counts["pass_rate"]}% passed">'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" stroke="var(--line)" '
        f'stroke-width="{stroke}"></circle>'
        f"{''.join(arcs)}"
        f'<text class="donut-top" x="50%" y="50%" text-anchor="middle">{counts["pass_rate"]}%</text>'
        f'<text class="donut-sub" x="50%" y="50%" dy="16" text-anchor="middle">passed</text>'
        "</svg>"
    )


def render_trend(history, width=640, height=140):
    """Pass rate per run as a polyline. Needs two points to be a line at all."""
    if len(history) < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 34, 10, 12, 26
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    points = []
    for index, entry in enumerate(history):
        x = pad_l + (plot_w * index / max(len(history) - 1, 1))
        y = pad_t + plot_h * (1 - (entry.get("pass_rate", 0) / 100))
        points.append((x, y, entry))

    grid = "".join(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h * (1 - pct / 100):.1f}" x2="{width - pad_r}" '
        f'y2="{pad_t + plot_h * (1 - pct / 100):.1f}" stroke="var(--line)" stroke-width="1"></line>'
        f'<text class="trend-tick" x="{pad_l - 6}" y="{pad_t + plot_h * (1 - pct / 100) + 4:.1f}" '
        f'text-anchor="end">{pct}</text>'
        for pct in (0, 50, 100)
    )
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{STATUS_COLORS["failed"] if e.get("failed") else STATUS_COLORS["passed"]}">'
        f'<title>{_escape(e.get("at", ""))}: {e.get("pass_rate", 0)}% ({e.get("passed", 0)} passed, {e.get("failed", 0)} failed)</title>'
        f"</circle>"
        for x, y, e in points
    )
    return (
        f'<svg width="100%" viewBox="0 0 {width} {height}" role="img" aria-label="pass rate trend">'
        f"{grid}"
        f'<polyline fill="none" stroke="var(--series)" stroke-width="2" points="{line}"></polyline>'
        f"{dots}</svg>"
    )


def history_path(app_env):
    # Per environment: stage and prod are different systems, so one shared trend line
    # would average two unrelated pass rates into a number that describes neither.
    return Path(f"maestro_history_{app_env}.json")


def load_history(app_env):
    path = history_path(app_env)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        # A corrupt history must not fail the run - the report just loses its trend.
        return []


def append_history(app_env, counts, summary):
    history = load_history(app_env)
    history.append(
        {
            "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "build_id": summary.get("build_id"),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "pass_rate": counts["pass_rate"],
        }
    )
    history = history[-HISTORY_LIMIT:]
    history_path(app_env).write_text(json.dumps(history, indent=2), encoding="utf-8")
    return history


CSS = """
:root{--bg:#f5f7fb;--card:#fff;--ink:#16203a;--muted:#6b7689;--line:#dde3ee;--brand:#0e1b3a;--slate:#1f3a6e;--series:#2a78d6}
html[data-theme=dark]{--bg:#0b1220;--card:#131c2e;--ink:#e8eefc;--muted:#93a0b8;--line:#243149;--brand:#0a1326;--slate:#9fb6e6;--series:#3987e5}
*{box-sizing:border-box}
body{font:14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:var(--ink);background:var(--bg)}
header.top{background:var(--brand);color:#fff;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:5;gap:12px;flex-wrap:wrap}
header.top h1{margin:0;font-size:17px}
header.top .when{color:#aab8d8;font-size:12px;margin-right:10px}
.env-tag{background:rgba(255,255,255,.16);border-radius:6px;padding:2px 8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.theme-btn{background:rgba(255,255,255,.12);color:#fff;border:0;border-radius:7px;padding:6px 12px;cursor:pointer;font-size:13px}
.wrap{max-width:1080px;margin:0 auto;padding:18px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin-bottom:18px}
.card>h2{font-size:15px;margin:0 0 10px}
.exec{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;flex:1;min-width:320px}
.kpi{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi-num{font-size:28px;font-weight:800;line-height:1}
.kpi-cap{font-size:12px;color:var(--muted);margin-top:4px}
.kpi-passed .kpi-num{color:#15924d}.kpi-failed .kpi-num{color:#d33030}.kpi-skipped .kpi-num{color:#9aa3b5}
.donut-wrap{text-align:center}
.donut-top{font-size:20px;font-weight:800;fill:var(--ink)}.donut-sub{font-size:10px;fill:var(--muted)}
.donut-legend{font-size:11px;color:var(--muted);margin-top:6px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.donut-legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:3px;vertical-align:middle}
.trend-tick{font:11px system-ui,sans-serif;fill:var(--muted)}
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.toolbar input[type=search]{flex:1;min-width:160px;max-width:300px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
.chip{border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:20px;padding:5px 12px;cursor:pointer;font-size:12px;user-select:none}
.chip.on{background:var(--slate);color:#fff;border-color:var(--slate)}
.count{font-size:12px;color:var(--muted)}
.table-scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:600px}
td,th{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
th{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{font-size:10px;font-weight:700;text-transform:uppercase;border-radius:4px;padding:2px 7px;color:#fff}
.badge-passed{background:#15924d}.badge-failed{background:#d33030}.badge-skipped{background:#9aa3b5}
.muted{color:var(--muted)}
.fail-step{font-size:12px;margin-top:5px;color:var(--muted)}
.fail-step b{color:#d33030;font-weight:600}
.fail-shot{margin-top:6px}
.fail-shot img{max-width:220px;max-height:300px;border:1px solid var(--line);border-radius:6px;display:block}
details{margin-top:6px}
summary{cursor:pointer;font-size:12px;color:var(--muted)}
pre{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:8px;font-size:11px;max-height:320px;overflow:auto;white-space:pre-wrap}
.links a{font-size:12px;margin-right:10px}
@media(max-width:720px){.kpis{grid-template-columns:repeat(2,1fr)}}
"""

JS = """
function setTheme(t){document.documentElement.setAttribute('data-theme',t);localStorage.setItem('maestro-report-theme',t)}
setTheme(localStorage.getItem('maestro-report-theme')||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'))
function toggleTheme(){setTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark')}
function applyFilters(){
  var q=document.getElementById('search').value.toLowerCase();
  var chip=document.querySelector('.chip.on');
  var status=chip?chip.dataset.status:'all';
  var shown=0;
  document.querySelectorAll('tbody tr').forEach(function(row){
    var show=row.dataset.text.includes(q)&&(status==='all'||row.dataset.status===status);
    row.style.display=show?'':'none';
    if(show)shown++;
  });
  document.getElementById('count').textContent=shown+' shown';
}
document.getElementById('search').addEventListener('input',applyFilters);
document.querySelectorAll('.chip').forEach(function(c){
  c.addEventListener('click',function(){
    document.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on')});
    c.classList.add('on');applyFilters();
  });
});
applyFilters();
"""


def _flow_rows(summary):
    flows = [
        (flow, session)
        for session in summary.get("sessions", [])
        for flow in session.get("flows", [])
    ]

    def sort_key(pair):
        flow = pair[0]
        status = (flow.get("status") or "").lower()
        order = ROW_SORT_ORDER.index(status) if status in ROW_SORT_ORDER else len(ROW_SORT_ORDER)
        return (order, flow.get("name") or "")

    rows = []
    for flow, session in sorted(flows, key=sort_key):
        status = (flow.get("status") or "unknown").lower()
        name = flow.get("name") or "(unnamed)"
        device = session.get("device") or ""
        detail = []

        if status == "failed":
            step = extract_failed_step(flow.get("log"))
            if step:
                detail.append(f'<div class="fail-step">Failed at: <b>{_escape(step)}</b></div>')
            for shot in flow.get("screenshots", []):
                detail.append(
                    f'<div class="fail-shot"><img src="data:image/png;base64,{shot["base64"]}" '
                    f'alt="{_escape(shot.get("name"))}" loading="lazy"></div>'
                )

        log = flow.get("log")
        if log:
            detail.append(
                f"<details><summary>Maestro step log</summary><pre>{_escape(log)}</pre></details>"
            )

        rows.append(
            f'<tr data-status="{status}" data-text="{_escape((name + " " + device).lower())}">'
            f"<td>{_escape(name)}{''.join(detail)}</td>"
            f'<td><span class="badge badge-{status}">{status}</span></td>'
            f'<td class="n">{_escape(flow.get("duration_seconds"))}s</td>'
            f"<td>{_escape(device)}</td></tr>"
        )
    return "".join(rows)


def render_html(summary, counts, history, app_env):
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kpis = f'<div class="kpi"><div class="kpi-num">{counts["total"]}</div><div class="kpi-cap">Total</div></div>'
    kpis += "".join(
        f'<div class="kpi kpi-{key}"><div class="kpi-num">{counts[key]}</div>'
        f'<div class="kpi-cap">{STATUS_LABELS[key]}</div></div>'
        for key in STATUS_ORDER
    )
    legend = "".join(
        f'<span><i style="background:{STATUS_COLORS[key]}"></i>{STATUS_LABELS[key]}</span>'
        for key in STATUS_ORDER
    )
    trend = render_trend(history)
    trend_html = trend or (
        '<p class="muted">Not enough runs yet - the trend needs at least two entries, and history '
        "is kept per environment across CI runs.</p>"
    )
    links = []
    if summary.get("build_url"):
        links.append(
            f'<a href="{_escape(summary["build_url"])}" target="_blank" rel="noopener">'
            "BrowserStack build (device video and logs)</a>"
        )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maestro Mobile Report - {_escape(app_env)}</title>
<style>{CSS}</style></head><body>
<header class="top">
  <h1>Maestro Mobile Report <span class="env-tag">{_escape(app_env)}</span></h1>
  <div><span class="when">{_escape(generated_at)}</span>
  <button class="theme-btn" onclick="toggleTheme()">Toggle theme</button></div>
</header>
<div class="wrap">
<div class="card"><div class="exec">
  <div class="kpis">{kpis}</div>
  <div class="donut-wrap">{render_donut(counts)}<div class="donut-legend">{legend}</div></div>
</div>
<div class="links">{"".join(links)}</div></div>
<div class="card"><h2>Trend - pass rate over the last {len(history)} run(s) on {_escape(app_env)}</h2>{trend_html}</div>
<div class="card">
  <h2>Flows</h2>
  <div class="toolbar">
    <input type="search" id="search" placeholder="Filter by flow or device...">
    <span class="chip on" data-status="all">All</span>
    <span class="chip" data-status="failed">Failed</span>
    <span class="chip" data-status="passed">Passed</span>
    <span class="chip" data-status="skipped">Skipped</span>
    <span class="count" id="count"></span>
  </div>
  <div class="table-scroll"><table>
    <thead><tr><th>Flow</th><th>Status</th><th>Duration</th><th>Device</th></tr></thead>
    <tbody>{_flow_rows(summary)}</tbody></table></div>
</div>
</div>
<script>{JS}</script>
</body></html>"""


def write_reports(summary, app_env="stage"):
    """maestro_report.json for CI to parse, maestro_report.html for people.

    The JSON keeps its top-level status/passed/failed/skipped keys - the workflow's
    Parse Results step reads them - and drops per-flow logs and screenshots, which
    belong in the HTML and would bloat the JSON by megabytes.
    """
    json_summary = json.loads(json.dumps(summary))
    for session in json_summary.get("sessions", []):
        for flow in session.get("flows", []):
            flow.pop("screenshots", None)
            flow.pop("log", None)
    Path("maestro_report.json").write_text(json.dumps(json_summary, indent=2), encoding="utf-8")

    counts = counts_from(summary)
    history = append_history(app_env, counts, summary)
    Path("maestro_report.html").write_text(
        render_html(summary, counts, history, app_env), encoding="utf-8"
    )
    print("Reports written: maestro_report.json, maestro_report.html")
