"""
Build 5 per-QE portal view emulators + index.html landing page.
Each QE merges data from ALL patients in sample_patients/ so the emulator
pages contain a patient dropdown with every available person.

  - HixnyEmulator.html                HIXNY              (SMART on FHIR style)
  - HEALTHeLINKEmulator.html          HEALTHeLINK        (Fusion style)
  - HealthixEmulator.html              Healthix           (SMART on FHIR style)
  - HealtheConnectionsEmulator.html    HealtheConnections (SMART on FHIR style)
  - BronxEmulator.html                 Bronx RHIO         (IMAT style)
  - index.html                         landing page

Usage:
    python build_home.py                   # builds with ALL patients (default)
    python build_home.py marcus_evans      # builds for one patient only
"""
import os
import sys
import json
import shutil
import tempfile
import importlib
import html

E = html.escape

# ---- Patient selection ------------------------------------------------
SINGLE_PATIENT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('PATIENT_ID', '')

with open('patient_profiles.json', encoding='utf-8') as _pf:
    _all_profiles = json.load(_pf)['patients']
    _profiles = {p['id']: p for p in _all_profiles}

if SINGLE_PATIENT:
    _selected_patients = [SINGLE_PATIENT]
    _patient = _profiles.get(SINGLE_PATIENT, {})
    _patient_label = f"{_patient.get('first_name', '')} {_patient.get('last_name', '')}".strip() or SINGLE_PATIENT
else:
    _selected_patients = list(_profiles.keys())
    _patient_label = f"All {len(_selected_patients)} patients"

_patient_total = len(_profiles)
_tmp_dirs = []  # track temp dirs for cleanup


def _merge_qe_data(qe_folder):
    """Create a temp dir merging all selected patients' data for one QE."""
    tmp = tempfile.mkdtemp(prefix=f'qe_{qe_folder}_')
    _tmp_dirs.append(tmp)
    for sub in ('ccda', 'oru-hl7', 'trn'):
        os.makedirs(os.path.join(tmp, sub), exist_ok=True)

    for patient_id in _selected_patients:
        src_base = os.path.join('sample_patients', patient_id, qe_folder)
        if not os.path.isdir(src_base):
            continue
        for sub in ('ccda', 'oru-hl7', 'trn'):
            src_dir = os.path.join(src_base, sub)
            if os.path.isdir(src_dir):
                for f in os.listdir(src_dir):
                    shutil.copy2(os.path.join(src_dir, f), os.path.join(tmp, sub, f))
    return tmp


def _set_env(qe_folder, out_file, qe_name, title=''):
    """Set env vars for a per-QE build, merging all patients."""
    merged = _merge_qe_data(qe_folder)
    os.environ['CHART_CCD_DIR'] = os.path.join(merged, 'ccda')
    os.environ['CHART_ORU_HL7'] = os.path.join(merged, 'oru-hl7')
    os.environ['CHART_TRN_DIR'] = os.path.join(merged, 'trn')
    os.environ['CHART_OUT'] = out_file
    os.environ['CHART_QE'] = qe_name
    if title:
        os.environ['CHART_TITLE'] = title


# ---- HIXNY: SMART on FHIR style (first import) ----
_set_env('hixny', 'HixnyEmulator.html', 'HIXNY', 'SHIN-NY Community Health Record')
import build_smart  # noqa: E402,F401

# ---- HEALTHeLINK: Fusion style ----
_set_env('healthelink', 'HEALTHeLINKEmulator.html', 'HEALTHELINK')
import build_chart  # noqa: E402,F401

# ---- Healthix: SMART on FHIR style (reload) ----
_set_env('healthix', 'HealthixEmulator.html', 'HEALTHIX', 'SHIN-NY Community Health Record')
importlib.reload(build_smart)

# ---- HealtheConnections: dedicated HEC renderer ----
_set_env('healtheconn', 'HealtheConnectionsEmulator.html', 'HEALTHECONN')
import build_healtheconn  # noqa: E402,F401

# ---- Bronx RHIO: IMAT style ----
_set_env('bronx', 'BronxEmulator.html', 'BRONX')
import build_bronx  # noqa: E402,F401

n_people = len(build_smart.patients)

# Clean up temp dirs
for d in _tmp_dirs:
    shutil.rmtree(d, ignore_errors=True)

# ---- home screen: one view per NY Qualified Entity (QE); some live, rest coming soon ----
QES = [
    {'name': 'Hixny', 'region': 'Capital Region', 'color': '#0e7490',
     'site': 'https://hixny.org', 'href': 'HixnyEmulator.html', 'live': True},
    {'name': 'HEALTHeLINK', 'region': 'Western New York', 'color': '#1d4ed8',
     'site': 'https://wnyhealthelink.com', 'href': 'HEALTHeLINKEmulator.html', 'live': True},
    {'name': 'Healthix', 'region': 'NYC & Long Island', 'color': '#059669',
     'site': 'https://healthix.org', 'href': 'HealthixEmulator.html', 'live': True},
    {'name': 'HealtheConnections', 'region': 'Central NY, North Country & more', 'color': '#ea580c',
     'site': 'https://www.healtheconnections.org', 'href': 'HealtheConnectionsEmulator.html', 'live': True},
    {'name': 'Bronx RHIO', 'region': 'The Bronx (IMAT Solutions)', 'color': '#b91c1c',
     'site': 'https://bronxrhio.org', 'href': 'BronxEmulator.html', 'live': True},
]


def _qe_card(q):
    dom = q['site'].replace('https://', '').replace('http://', '').rstrip('/')
    logo = f'<div class="qe-logo">{E(q["name"])}</div>'
    region = f'<div class="qe-region">{E(q["region"])}</div>'
    site = f'<a class="qe-site" href="{q["site"]}" target="_blank" rel="noopener">{E(dom)}</a>'
    if q['live']:
        action = f'<a class="qe-open" href="{q["href"]}">Open the {E(q["name"])} view &rarr;</a>'
        cls = 'qe-card live'
    else:
        action = '<span class="qe-badge">Coming soon</span>'
        cls = 'qe-card soon'
    return f'<div class="{cls}" style="--c:{q["color"]}">{logo}{region}{action}{site}</div>'


cards_html = '\n      '.join(_qe_card(q) for q in QES)
live_n = sum(1 for q in QES if q['live'])

# ============================================================
# Extra CSS â€” plain string so CSS braces need no escaping
# ============================================================
EXTRA_CSS = """
  /* â”€â”€ Understand Volume section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  .report-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px; }
  .report-card { background:#fff; border:1px solid var(--line); border-radius:14px;
    padding:20px 22px; box-shadow:0 6px 20px rgba(16,24,40,.08); }
  .report-card.full { grid-column:1/-1; }
  .report-card.soon { opacity:.72; }
  .report-title { font-weight:700; font-size:15.5px; color:var(--ink); }
  .report-sub { font-size:12px; color:var(--muted); }
  .vol-row { display:flex; align-items:center; gap:10px; margin-bottom:9px; }
  .vol-name { width:155px; flex-shrink:0; font-size:12.5px; font-weight:600; color:var(--ink); }
  .vol-bar-wrap { flex:1; height:18px; background:#f1f5f9; border-radius:4px; overflow:hidden; display:flex; }
  .vol-bar-seg { height:100%; transition:width .4s; }
  .vol-total { width:76px; text-align:right; font-size:11.5px; color:var(--muted); flex-shrink:0;
    font-variant-numeric:tabular-nums; }
  .vol-legend { display:flex; gap:16px; margin-top:14px; padding-top:12px;
    border-top:1px solid var(--line); flex-wrap:wrap; }
  .vol-legend-item { display:flex; align-items:center; gap:5px; font-size:11.5px; color:var(--muted); }
  .vol-legend-dot { width:10px; height:10px; border-radius:2px; flex-shrink:0; }
  .report-meta { margin-top:12px; font-size:11px; color:#98a2b3; line-height:1.5; }
  .report-soon-title { font-size:14px; font-weight:600; color:var(--muted); }
  .report-badge { display:inline-block; margin-top:10px; background:#f2f4f7; color:#667085;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px;
    padding:4px 10px; border-radius:999px; }

  /* â”€â”€ Hospital report (Report 2) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  .qe-tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }
  .qe-tab { border:1px solid var(--line); background:#fff; color:var(--muted); font-size:12px;
    font-weight:600; padding:5px 14px; border-radius:999px; cursor:pointer;
    transition:background .12s,color .12s,border-color .12s; }
  .qe-tab:hover { border-color:var(--brand); color:var(--brand); }
  .qe-tab.active { color:#fff; }
  .hosp-badge { display:inline-block; background:#ecfdf5; color:#059669; font-size:12px;
    font-weight:700; padding:3px 10px; border-radius:999px; margin-bottom:12px; }
  .hosp-wrap { overflow-x:auto; max-height:460px; overflow-y:auto;
    border:1px solid var(--line); border-radius:8px; }
  .hosp-tbl { width:100%; border-collapse:collapse; font-size:12.5px; }
  .hosp-tbl th { position:sticky; top:0; background:#f8fafc; text-align:left;
    color:var(--muted); font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:.5px; padding:8px 12px 6px; border-bottom:2px solid var(--line); }
  .hosp-tbl th.r { text-align:right; }
  .hosp-tbl td { padding:7px 12px; border-bottom:1px solid var(--line); }
  .hosp-tbl td.r { text-align:right; font-variant-numeric:tabular-nums; }
  .hosp-tbl td.code { font-family:ui-monospace,monospace; font-size:11px; color:var(--muted); }
  .hosp-tbl td.tot { font-weight:700; }
  .hosp-tbl tbody tr:hover td { background:#f8fafc; }
  /* AA group header (multiple hospitals share one AA) */
  .hosp-tbl tr.aa-grp td { background:#f1f5f9; border-top:2px solid var(--line); }
  .hosp-tbl tr.aa-grp .aa-label { font-family:ui-monospace,monospace; font-size:11.5px;
    font-weight:700; color:var(--brand-2); }
  .hosp-tbl tr.aa-grp .aa-count { font-size:11px; color:var(--muted); margin-left:8px; font-weight:400; }
  /* Sub-rows under a grouped AA */
  .hosp-tbl tr.aa-sub td { border-bottom:1px solid #f3f4f6; }
  .hosp-tbl td.sub-name { padding-left:26px; color:var(--muted); font-size:12px; }

  /* ── Non-hospital report (Report 3) ─────────────────────────────── */
  .hosp-tbl td.typ { font-size:11.5px; color:var(--muted); }
  .nosfdc { display:inline-block; background:#fff7ed; color:#c2410c; border:1px solid #fed7aa;
    font-size:10.5px; font-weight:700; padding:1px 8px; border-radius:999px; }
  .more { color:var(--muted); font-size:11.5px; }
  /* polish */
  .hosp-tbl td.hname { font-size:11.5px; }
  .hosp-tbl td.hname .fid { color:#98a2b3; font-size:10px; margin-left:6px; }
  .hosp-tbl tr.aa-grp td.aa-head { font-size:11.5px; }
  .hosp-tbl tr.aa-grp .aa-count { font-size:10.5px; color:var(--muted); margin-left:8px; font-weight:400; }
  .hosp-tbl tr.aa-sub td.sub-name { padding-left:26px; color:var(--ink); font-size:11px;
    border-left:3px solid var(--line); }
  .hosp-tbl tr.aa-sub:nth-child(even) td { background:#fafbfc; }
  .hosp-tbl td.bar-cell { position:relative; }
  .hosp-tbl td.bar-cell .bar-bg { position:absolute; left:0; top:3px; bottom:3px;
    background:#e0f2fe; border-radius:2px; z-index:0; }
  .hosp-tbl td.bar-cell span { position:relative; z-index:1; }

  /* expand to fullscreen */
  .expand-btn { position:absolute; top:16px; right:16px; width:30px; height:30px;
    border-radius:8px; border:1px solid var(--line); background:#fff; color:var(--muted);
    cursor:pointer; display:flex; align-items:center; justify-content:center;
    font-size:16px; transition:background .12s, color .12s, box-shadow .12s; z-index:2; }
  .expand-btn:hover { background:var(--brand); color:#fff; box-shadow:0 2px 8px rgba(14,122,144,.3); }
  .report-card { position:relative; }
  .report-card.fullscreen { position:fixed; top:0; left:0; right:0; bottom:0;
    z-index:9999; border-radius:0; margin:0; max-width:none;
    overflow-y:auto; border:none; box-shadow:none; }
  .report-card.fullscreen .hosp-wrap { max-height:calc(100vh - 200px); }
  .report-card.fullscreen .expand-btn { top:18px; right:24px; }
  body.has-fullscreen { overflow:hidden; }"""

# ============================================================
# "Understand Volume" section HTML â€” plain string
# ============================================================
VOLUME_SECTION = """
    <div class="sec-h" id="volume-reports" style="margin-top:36px">Understand Volume</div>
    <div class="report-grid">

      <!-- Report 1: Volume by QE \u2013 Highest Level (hardcoded from Athena run) -->
      <div class="report-card full">
        <div class="report-title">Volume by QE &mdash; Highest Level</div>
        <div class="report-sub" style="margin:3px 0 16px">
          28-day total &middot; Oct&nbsp;18&nbsp;&ndash;&nbsp;Nov&nbsp;14,&nbsp;2026 &middot; Verato-matched sources only
        </div>
        <div id="vol-chart"></div>
        <div class="vol-legend">
          <div class="vol-legend-item"><div class="vol-legend-dot" style="background:#0ea5a4"></div>CCD</div>
          <div class="vol-legend-item"><div class="vol-legend-dot" style="background:#3b82f6"></div>TRN</div>
          <div class="vol-legend-item"><div class="vol-legend-dot" style="background:#94a3b8"></div>LAB</div>
          <div class="vol-legend-item"><div class="vol-legend-dot" style="background:#f59e0b"></div>ADT</div>
        </div>
        <div class="report-meta">
          Source: <code>DailyVolumeByQE-28Day-SingleSnapshot-ExcludeOrphans.sql</code>
          &middot; 47.24&nbsp;GB scanned &middot; excludes backload &amp; orphan sources
        </div>
      </div>

      <!-- Report 2: Hospital Volume \u2013 Last 10 Days -->
      <div class="report-card full" id="hosp-report">
        <div class="report-title">Hospital Volume &mdash; Last 10 Days</div>
        <div class="report-sub" style="margin:3px 0 16px">
          Nov&nbsp;4&nbsp;&ndash;&nbsp;Nov&nbsp;13,&nbsp;2026 &middot; Article&nbsp;28 hospitals &middot; CCD&nbsp;+&nbsp;TRN&nbsp;+&nbsp;LAB&nbsp;+&nbsp;ADT &middot; filter by QE
        </div>
        <div class="qe-tabs" id="hosp-tabs"></div>
        <div id="hosp-badge" style="margin-bottom:10px"></div>
        <div class="hosp-wrap">
          <table class="hosp-tbl">
            <thead><tr>
              <th>Hospital</th><th>AA&nbsp;Code</th>
              <th class="r">CCD</th><th class="r">TRN</th><th class="r">LAB</th><th class="r">ADT</th><th class="r">Total</th>
            </tr></thead>
            <tbody id="hosp-tbody"></tbody>
          </table>
        </div>
        <div class="report-meta" style="margin-top:14px">
          Source: <code>reportonhospitals.sql</code>
          &middot; 47.23&nbsp;GB scanned &middot; SFDC registry (Article&nbsp;28 only)
          &middot; hospitals with no recent activity shown at bottom
        </div>
      </div>

      <!-- Report 3: Non-Hospital Sources - Last 10 Days -->
      <div class="report-card full" id="nonhosp-report">
        <div class="report-title">Non-Hospital Sources &mdash; Last 10 Days</div>
        <div class="report-sub" style="margin:3px 0 16px">
          Nov&nbsp;4&nbsp;&ndash;&nbsp;Nov&nbsp;13,&nbsp;2026 &middot; every non-hospital assigning authority with data in PDR &middot; CCD&nbsp;+&nbsp;TRN&nbsp;+&nbsp;LAB&nbsp;+&nbsp;ADT &middot; filter by QE
        </div>
        <div class="qe-tabs" id="nonhosp-tabs"></div>
        <div id="nonhosp-badge"></div>
        <div class="hosp-wrap">
          <table class="hosp-tbl">
            <thead><tr>
              <th>Source</th><th>AA&nbsp;Code</th><th>Type</th>
              <th class="r">CCD</th><th class="r">TRN</th><th class="r">LAB</th><th class="r">ADT</th><th class="r">Total</th>
            </tr></thead>
            <tbody id="nonhosp-tbody"></tbody>
          </table>
        </div>
        <div class="report-meta" style="margin-top:14px">
          Source: <code>reportonnonhospitals.sql</code>
          &middot; 47.23&nbsp;GB scanned &middot; starts from data in PDR, name/type from the SFDC registry
          &middot; hospitals excluded &middot; <b>Not in SFDC</b> = data in PDR with no SFDC record
        </div>
      </div>


      <!-- Report 4: ADT Volume by Facility (snapshot) -->
      <div class="report-card full" id="adt-report">
        <div class="report-title">ADT Volume by Facility</div>
        <div class="report-sub" style="margin:3px 0 16px">
          Aug&nbsp;&ndash;&nbsp;Oct&nbsp;2026 (3-month snapshot) &middot; filter by QE
        </div>
        <div class="qe-tabs" id="adt-tabs"></div>
        <div id="adt-badge"></div>
        <div class="hosp-wrap">
          <table class="hosp-tbl">
            <thead><tr>
              <th>Facility</th><th>AA&nbsp;Code</th><th>Facility&nbsp;ID</th>
              <th class="r">ADT&nbsp;Messages</th>
            </tr></thead>
            <tbody id="adt-tbody"></tbody>
          </table>
        </div>
        <div class="report-meta" style="margin-top:14px">
          Source: <code>lookup_adt_counts</code> (static snapshot)
          &middot; 31.6M ADT messages across 6 QEs &middot; per-facility counts summed over 3 months
        </div>
      </div>

      <!-- Placeholder 3 -->
      <div class="report-card soon">
        <div class="report-soon-title">Doc-Type Mix by QE</div>
        <div style="color:var(--muted);font-size:13px;margin-top:6px;line-height:1.5">
          CCD vs TRN vs LAB share per QE with week-over-week change &mdash; surfaces shifts in submission patterns.
        </div>
        <span class="report-badge">Coming soon</span>
      </div>

    </div><!-- /report-grid -->"""

# ============================================================
# Report 1 render script â€” plain string (JS braces safe here)
# ============================================================
REPORT1_SCRIPT = """
  <script>
  (function () {
    var rows = [
      { qe: "Healthix",           ccd: 6856187, trn: 3691902, lab: 5822179, adt: 11822038 },
      { qe: "HealtheConnections", ccd: 4064234, trn: 2946189, lab: 4940467, adt: 5814192 },
      { qe: "HEALTHeLINK",        ccd: 1001590, trn:  989702, lab: 1857966, adt: 4992149 },
      { qe: "Hixny",              ccd: 2497901, trn:   86968, lab: 1177507, adt: 1442585 },
      { qe: "Bronx RHIO",         ccd:  832486, trn: 1191999, lab: 1209660, adt: 1882379 }
    ];
    rows.sort(function(a, b) {
      return (b.ccd + b.trn + b.lab + b.adt) - (a.ccd + a.trn + a.lab + a.adt);
    });
    var maxTotal = Math.max.apply(null, rows.map(function(r) { return r.ccd + r.trn + r.lab + r.adt; }));
    function fmt(n) { return n.toLocaleString(); }
    function pct(v) { return (v / maxTotal * 100).toFixed(2) + '%'; }
    var container = document.getElementById('vol-chart');
    rows.forEach(function(r) {
      var total = r.ccd + r.trn + r.lab + r.adt;
      var div = document.createElement('div');
      div.className = 'vol-row';
      div.innerHTML =
        '<div class="vol-name">' + r.qe + '</div>' +
        '<div class="vol-bar-wrap">' +
          '<div class="vol-bar-seg" style="width:' + pct(r.ccd) + ';background:#0ea5a4" title="CCD: ' + fmt(r.ccd) + '"></div>' +
          '<div class="vol-bar-seg" style="width:' + pct(r.trn) + ';background:#3b82f6" title="TRN: ' + fmt(r.trn) + '"></div>' +
          '<div class="vol-bar-seg" style="width:' + pct(r.lab) + ';background:#94a3b8" title="LAB: ' + fmt(r.lab) + '"></div>' +
          '<div class="vol-bar-seg" style="width:' + pct(r.adt) + ';background:#f59e0b" title="ADT: ' + fmt(r.adt) + '"></div>' +
        '</div>' +
        '<div class="vol-total">' + fmt(total) + '</div>';
      container.appendChild(div);
    });
  })();
  </script>"""

# ============================================================
# Report 2 render script â€” plain string
# ============================================================
REPORT2_SCRIPT = """
  <script src="./hosp_data.js"></script>
  <script>
  /* Report 2: Hospital Volume render */
  (function () {
    if (!window.HOSP) return;
    var HOSP = window.HOSP;
    var QE_COLORS = {
      'HealtheConnections':'#ea580c', 'Healthix':'#059669', 'Bronx RHIO':'#b91c1c',
      'HEALTHeLINK':'#1d4ed8', 'Hixny':'#0e7490'
    };
    var current = HOSP.qes[0];

    function fmt(n) { return n > 0 ? n.toLocaleString() : '\u2014'; }

    function titleCase(s) {
      return s.replace(/\\w\\S*/g, function(t) {
        if (t.length <= 2 && t === t.toUpperCase()) return t; // keep "OF", "AT" etc short
        return t.charAt(0).toUpperCase() + t.substr(1).toLowerCase();
      });
    }

    function fmtC(n) {
      if (n <= 0) return '\u2014';
      if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
      if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
      return n.toLocaleString();
    }

    function render(qe) {
      var rows = HOSP.rows.filter(function(r) { return r[0] === qe; });

      // Group by AA code, preserving SQL order (total DESC, aa ASC, org ASC)
      var seen = {}, groups = [];
      rows.forEach(function(r) {
        var aa = r[2];
        if (!seen[aa]) {
          seen[aa] = { aa: aa, ccd: r[3], trn: r[4], lab: r[5], adt: r[6], chain: r[8] || '', items: [] };
          groups.push(seen[aa]);
        }
        seen[aa].items.push({ name: r[1], fid: r[7] || '' });
      });

      // Sort groups: AA total DESC, then AA name ASC
      groups.sort(function(a, b) {
        var ta = a.ccd + a.trn + a.lab + a.adt, tb = b.ccd + b.trn + b.lab + b.adt;
        return tb !== ta ? tb - ta : a.aa.localeCompare(b.aa);
      });

      var maxTot = Math.max.apply(null, groups.map(function(g) { return g.ccd + g.trn + g.lab + g.adt; }));
      var n = groups.length;
      var ccdN = groups.filter(function(g) { return g.ccd > 0; }).length;
      var trnN = groups.filter(function(g) { return g.trn > 0; }).length;
      var labN = groups.filter(function(g) { return g.lab > 0; }).length;
      var adtN = groups.filter(function(g) { return g.adt > 0; }).length;
      function pct(v) { return n > 0 ? Math.round(v / n * 100) + '%' : '0%'; }
      document.getElementById('hosp-badge').innerHTML =
        '<span class="hosp-badge">CCD: ' + ccdN + '/' + n + ' (' + pct(ccdN) + ')</span> ' +
        '<span class="hosp-badge">TRN: ' + trnN + '/' + n + ' (' + pct(trnN) + ')</span> ' +
        '<span class="hosp-badge">LAB: ' + labN + '/' + n + ' (' + pct(labN) + ')</span> ' +
        '<span class="hosp-badge">ADT: ' + adtN + '/' + n + ' (' + pct(adtN) + ')</span>';

      var html = '';
      groups.forEach(function(g) {
        var tot = g.ccd + g.trn + g.lab + g.adt;

        if (g.items.length === 1) {
          // Single hospital â€” clean flat row
          var it = g.items[0];
          var pct = maxTot > 0 ? (tot / maxTot * 100).toFixed(1) : 0;
          html += '<tr>'
            + '<td class="hname">' + titleCase(it.name) + (it.fid ? '<span class="fid">#' + it.fid + '</span>' : '') + '</td>'
            + '<td class="code">' + g.aa + '</td>'
            + '<td class="r">' + fmtC(g.ccd) + '</td>'
            + '<td class="r">' + fmtC(g.trn) + '</td>'
            + '<td class="r">' + fmtC(g.lab) + '</td>'
            + '<td class="r">' + fmtC(g.adt) + '</td>'
            + '<td class="r tot bar-cell"><div class="bar-bg" style="width:' + pct + '%"></div><span>' + fmt(tot) + '</span></td>'
            + '</tr>';
        } else {
          // Multiple hospitals share this AA â€” group header + sub-rows
          var pctG = maxTot > 0 ? (tot / maxTot * 100).toFixed(1) : 0;
          html += '<tr class="aa-grp">'
            + '<td class="aa-head">' + (g.chain ? '<b>' + g.chain + '</b> ' : '') + '<span class="aa-count">' + g.items.length + ' hospitals</span></td>'
            + '<td class="code"><span class="aa-label">' + g.aa + '</span></td>'
            + '<td class="r">' + fmtC(g.ccd) + '</td>'
            + '<td class="r">' + fmtC(g.trn) + '</td>'
            + '<td class="r">' + fmtC(g.lab) + '</td>'
            + '<td class="r">' + fmtC(g.adt) + '</td>'
            + '<td class="r tot bar-cell"><div class="bar-bg" style="width:' + pctG + '%"></div><span>' + fmt(tot) + '</span></td>'
            + '</tr>';
          g.items.forEach(function(it, idx) {
            html += '<tr class="aa-sub">'
              + '<td class="sub-name">' + titleCase(it.name) + (it.fid ? '<span class="fid">#' + it.fid + '</span>' : '') + '</td>'
              + '<td colspan="6"></td>'
              + '</tr>';
          });
        }
      });
      document.getElementById('hosp-tbody').innerHTML = html;

      var color = QE_COLORS[qe] || 'var(--brand)';
      document.querySelectorAll('#hosp-tabs .qe-tab').forEach(function(btn) {
        var on = btn.dataset.qe === qe;
        btn.classList.toggle('active', on);
        btn.style.background  = on ? color : '';
        btn.style.borderColor = on ? color : '';
      });
    }

    var tabs = document.getElementById('hosp-tabs');
    HOSP.qes.forEach(function(qe) {
      var btn = document.createElement('button');
      btn.className = 'qe-tab';
      btn.dataset.qe = qe;
      btn.textContent = qe;
      btn.addEventListener('click', function() { current = qe; render(qe); });
      tabs.appendChild(btn);
    });

    render(current);
  })();
  </script>"""

# ============================================================
# Report 3 render script - non-hospital sources
# ============================================================
REPORT3_SCRIPT = """
  <script src="./nonhosp_data.js"></script>
  <script>
  /* Report 3: Non-Hospital Sources render */
  (function () {
    if (!window.NONHOSP) return;
    var D = window.NONHOSP;
    var QE_COLORS = {
      'HealtheConnections':'#ea580c', 'Healthix':'#059669', 'Bronx RHIO':'#b91c1c',
      'HEALTHeLINK':'#1d4ed8', 'Hixny':'#0e7490'
    };
    var current = D.qes[0];

    function fmt(n) { return n > 0 ? n.toLocaleString() : '\\u2014'; }
    function esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function render(qe) {
      // row: [qe, name, aa, type, inSfdc, orgCount, ccd, trn, lab, adt]
      var rows = D.rows.filter(function(r) { return r[0] === qe; });
      rows.sort(function(a, b) {
        var ta = a[6] + a[7] + a[8] + a[9], tb = b[6] + b[7] + b[8] + b[9];
        return tb !== ta ? tb - ta : a[2].localeCompare(b[2]);
      });
      var notIn = rows.filter(function(r) { return !r[4]; }).length;
      document.getElementById('nonhosp-badge').innerHTML =
        '<span class="hosp-badge">' + rows.length.toLocaleString() + ' sources with data</span> ' +
        '<span class="nosfdc" style="margin-left:6px">' + notIn.toLocaleString() + ' not in SFDC</span>';

      var html = '';
      rows.forEach(function(r) {
        var tot = r[6] + r[7] + r[8] + r[9];
        var name = r[4]
          ? esc(r[1]) + (r[5] > 1 ? ' <span class="more">+' + (r[5] - 1) + ' more</span>' : '')
          : '<span class="nosfdc">Not in SFDC</span>';
        var typ = r[4] ? esc(r[3]) : '\\u2014';
        html += '<tr>'
          + '<td>' + name + '</td>'
          + '<td class="code">' + esc(r[2]) + '</td>'
          + '<td class="typ">' + typ + '</td>'
          + '<td class="r">' + fmt(r[6]) + '</td>'
          + '<td class="r">' + fmt(r[7]) + '</td>'
          + '<td class="r">' + fmt(r[8]) + '</td>'
          + '<td class="r">' + fmt(r[9]) + '</td>'
          + '<td class="r tot">' + fmt(tot) + '</td>'
          + '</tr>';
      });
      document.getElementById('nonhosp-tbody').innerHTML = html;

      var color = QE_COLORS[qe] || 'var(--brand)';
      document.querySelectorAll('#nonhosp-tabs .qe-tab').forEach(function(btn) {
        var on = btn.dataset.qe === qe;
        btn.classList.toggle('active', on);
        btn.style.background  = on ? color : '';
        btn.style.borderColor = on ? color : '';
      });
    }

    var tabs = document.getElementById('nonhosp-tabs');
    D.qes.forEach(function(qe) {
      var btn = document.createElement('button');
      btn.className = 'qe-tab';
      btn.dataset.qe = qe;
      btn.textContent = qe;
      btn.addEventListener('click', function() { current = qe; render(qe); });
      tabs.appendChild(btn);
    });

    render(current);
  })();
  </script>"""


# ============================================================
# Report 4 render script - ADT volume
# ============================================================
REPORT4_SCRIPT = """
  <script src="./adt_data.js"></script>
  <script>
  /* Report 4: ADT Volume render */
  (function () {
    if (!window.ADT) return;
    var D = window.ADT;
    var QE_COLORS = {
      'HealtheConnections':'#ea580c', 'Healthix':'#059669', 'Bronx RHIO':'#b91c1c',
      'HEALTHeLINK':'#1d4ed8', 'Hixny':'#0e7490'
    };
    var current = D.qes[0];

    function fmt(n) { return n > 0 ? n.toLocaleString() : '\u2014'; }
    function esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function render(qe) {
      // row: [qe, aa, facility_id, facility_name, adt_count]
      var rows = D.rows.filter(function(r) { return r[0] === qe; });
      rows.sort(function(a, b) { return b[4] - a[4] || a[3].localeCompare(b[3]); });

      var total = rows.reduce(function(s, r) { return s + r[4]; }, 0);
      document.getElementById('adt-badge').innerHTML =
        '<span class="hosp-badge">' + rows.length + ' facilities &middot; ' +
        total.toLocaleString() + ' ADT messages</span>';

      var html = '';
      rows.forEach(function(r) {
        html += '<tr>'
          + '<td>' + esc(r[3]) + '</td>'
          + '<td class="code">' + esc(r[1]) + '</td>'
          + '<td class="code">' + esc(r[2]) + '</td>'
          + '<td class="r tot">' + fmt(r[4]) + '</td>'
          + '</tr>';
      });
      document.getElementById('adt-tbody').innerHTML = html;

      var color = QE_COLORS[qe] || 'var(--brand)';
      document.querySelectorAll('#adt-tabs .qe-tab').forEach(function(btn) {
        var on = btn.dataset.qe === qe;
        btn.classList.toggle('active', on);
        btn.style.background  = on ? color : '';
        btn.style.borderColor = on ? color : '';
      });
    }

    var tabs = document.getElementById('adt-tabs');
    D.qes.forEach(function(qe) {
      var btn = document.createElement('button');
      btn.className = 'qe-tab';
      btn.dataset.qe = qe;
      btn.textContent = qe;
      btn.addEventListener('click', function() { current = qe; render(qe); });
      tabs.appendChild(btn);
    });

    render(current);
  })();
  </script>"""

# ============================================================
# Expand-to-fullscreen script
# ============================================================
EXPAND_SCRIPT = """
  <script>
  /* Expand any report card to fullscreen */
  (function () {
    document.querySelectorAll('.report-card').forEach(function(card) {
      if (card.classList.contains('soon')) return;
      var btn = document.createElement('button');
      btn.className = 'expand-btn';
      btn.setAttribute('aria-label', 'Toggle fullscreen');
      btn.setAttribute('title', 'Expand / collapse');
      btn.innerHTML = '&#x26F6;';
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var isFS = card.classList.toggle('fullscreen');
        document.body.classList.toggle('has-fullscreen', isFS);
        btn.innerHTML = isFS ? '&#x2716;' : '&#x26F6;';
        if (isFS) {
          card._scrollY = window.scrollY;
          window.scrollTo(0, 0);
        } else {
          window.scrollTo(0, card._scrollY || 0);
        }
      });
      card.appendChild(btn);
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        var fs = document.querySelector('.report-card.fullscreen');
        if (fs) {
          fs.classList.remove('fullscreen');
          document.body.classList.remove('has-fullscreen');
          fs.querySelector('.expand-btn').innerHTML = '&#x26F6;';
          window.scrollTo(0, fs._scrollY || 0);
        }
      }
    });
  })();
  </script>"""

# ============================================================
# Assemble index.html
# ============================================================
INDEX = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHIN-NY Record Viewer &mdash; Demo Home</title>
<style>
  :root {{ --brand:#0ea5a4; --brand-2:#0e7490; --ink:#1f2a37; --muted:#5b6774; --line:#e5e9ee; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; min-height:100vh; color:var(--ink); background:#eef2f6;
    font-family:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
    display:flex; flex-direction:column; }}
  .top {{ background:linear-gradient(90deg,var(--brand-2),var(--brand)); color:#fff;
    padding:28px 24px 32px; text-align:center; }}
  .top h1 {{ margin:0; font-size:24px; letter-spacing:.2px; font-weight:700; }}

  .wrap {{ max-width:1000px; margin:24px auto 0; padding:0 20px 30px; width:100%; }}
  .sec-h {{ font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:.6px;
    color:var(--muted); margin:4px 2px 14px; }}
  .qe-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:18px; }}
  .qe-card {{ background:#fff; border:1px solid var(--line); border-top:4px solid var(--c);
    border-radius:14px; padding:18px; box-shadow:0 6px 20px rgba(16,24,40,.08);
    display:flex; flex-direction:column; min-height:154px; transition:transform .12s, box-shadow .12s; }}
  .qe-card.live:hover {{ transform:translateY(-3px); box-shadow:0 12px 28px rgba(16,24,40,.14); }}
  .qe-card.soon {{ opacity:.72; }}
  .qe-logo {{ font-weight:800; font-size:21px; letter-spacing:-.4px; color:var(--c); }}
  .qe-region {{ color:var(--muted); font-size:12.5px; margin-top:4px; }}
  .qe-open {{ margin-top:14px; font-weight:700; color:var(--c); text-decoration:none; }}
  .qe-open:hover {{ text-decoration:underline; }}
  .qe-badge {{ margin-top:14px; align-self:flex-start; background:#f2f4f7; color:#667085;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px;
    padding:4px 10px; border-radius:999px; }}
  .qe-site {{ margin-top:auto; padding-top:12px; font-size:11.5px; color:#98a2b3; text-decoration:none; }}
  .qe-site:hover {{ color:var(--c); text-decoration:underline; }}

  .note {{ margin:22px 0 40px; padding:16px 20px; background:#fff;
    border:1px solid var(--line); border-radius:12px; color:var(--muted); font-size:13px; line-height:1.6; }}
  .note b {{ color:var(--ink); }}
  .foot {{ text-align:center; color:var(--muted); font-size:11.5px; padding:0 0 26px; }}
  .mark svg {{ width:26px; height:26px; }}

  /* â”€â”€ Page nav â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  .page-nav {{ display:flex; justify-content:center; gap:8px; padding:0 20px 16px;
    background:linear-gradient(90deg,var(--brand-2),var(--brand)); flex-wrap:wrap; }}
  .page-nav a {{ color:rgba(255,255,255,.75); text-decoration:none; font-size:12.5px;
    font-weight:600; padding:6px 18px; border-radius:999px;
    border:1px solid rgba(255,255,255,.3);
    transition:color .12s, background .12s, border-color .12s; }}
  .page-nav a:hover {{ color:#fff; background:rgba(255,255,255,.18); border-color:rgba(255,255,255,.5); }}
  .page-nav a.on {{ color:#fff; background:rgba(255,255,255,.22); border-color:rgba(255,255,255,.5); }}
{EXTRA_CSS}
</style>
</head>
<body>
  <div class="top">
    <h1>QE PDR Viewer</h1>
  </div>
  <nav class="page-nav">
    <a class="on" href="#qe-portals">QE Portals</a>
    <a href="#volume-reports">Volume Reports</a>
  </nav>

  <div class="wrap">
    <div class="sec-h" id="qe-portals">Choose a Qualified Entity (QE)</div>
    <div class="qe-grid">
      {cards_html}
    </div>

    <div class="note">
      Viewing: <b>{E(_patient_label)}</b> ({_patient_total} in patient_profiles.json).
      Run <code>python build_home.py</code> for all patients or
      <code>python build_home.py &lt;patient_id&gt;</code> for one.<br>
      Each QE renders the selected patient in its own look &amp; feel using <b>only that QE&rsquo;s data</b>.
      Every QE folder contains C-CDA documents, HL7&nbsp;v2.5.1 ORU lab feeds, and TRN
      (discharge summary) encounter records. The same
      parser and de-duplication rules apply everywhere: an ORU result matching a CCD lab on
      LOINC&nbsp;+&nbsp;date is shown as <b>preferred</b> and the duplicate CCD value is
      <b>crossed off, never deleted</b>.
    </div>
{VOLUME_SECTION}
  </div>

  <div class="foot">Synthetic demonstration data only. QE names and links belong to their
    respective organizations; styled wordmarks are shown in place of official logos.
    FHIR&reg; is an HL7 trademark.</div>
{REPORT1_SCRIPT}
{REPORT2_SCRIPT}
{REPORT3_SCRIPT}
{REPORT4_SCRIPT}
{EXPAND_SCRIPT}
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(INDEX)

print(f'Wrote: index.html, HixnyEmulator.html, HEALTHeLINKEmulator.html, HealthixEmulator.html, HealtheConnectionsEmulator.html, BronxEmulator.html')
print(f'Patients: {_patient_label}')
print(f'Patients per QE view: {n_people}')
