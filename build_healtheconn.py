"""
HealtheConnections (HEC) patient portal renderer.
Reads C-CDA/ORU data via ccda_parse.py, emits a standalone HTML page styled
after portal.prod.healtheconnections.org — dark navy sidebar, teal brand,
category pills, two-column clinical layout.

Config via env (set by build_home.py):
  CHART_CCD_DIR, CHART_ORU_HL7, CHART_OUT, CHART_TRN_DIR, CHART_QE.
Output default: patient_chart_healtheconn.html.
"""
import os
import glob
import html
import json
from datetime import datetime

from ccda_parse import parse_ccd, load_oru, load_oru_hl7, merge_by_person
from ccda_parse import med_extra, lab_extra, oru_extra
from bug_widget import inject as inject_bug

CCD_DIR = os.environ.get('CHART_CCD_DIR', 'ccds')
OUT = os.environ.get('CHART_OUT', 'patient_chart_healtheconn.html')
ORU_HL7_DIR = os.environ.get('CHART_ORU_HL7', '')
TRN_DIR = os.environ.get('CHART_TRN_DIR', '')
VIEW_QE = os.environ.get('CHART_QE', 'HEALTHECONN')
E = html.escape


# ---------- helpers ----------
def source_name(item, qe_label):
    """Extract a Source string for any clinical item (HEC-specific)."""
    if item.get('facility'):
        return item['facility']
    if item.get('source') == 'CCD':
        return qe_label
    return qe_label


def patient_source_label(P):
    """Derive the primary source label from the patient's mrn_list."""
    if P.get('mrn_list'):
        first = P['mrn_list'][0]
        return first.get('source') or first.get('qe') or VIEW_QE
    return VIEW_QE


def _tbl(headers, rows_html, table_id=''):
    """Render a clean HEC-style table."""
    tid = f' id="{table_id}"' if table_id else ''
    head = ''.join(f'<th>{E(h)}</th>' for h in headers)
    return (f'<table class="hec-tbl"{tid}><thead><tr>{head}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table>')


def _row(cells, cls='', extra=None):
    tds = ''.join(f'<td>{c}</td>' for c in cells)
    attr = ''
    pairs = [[k, v] for k, v in (extra or []) if v]
    if pairs:
        attr = f' data-extra="{E(json.dumps(pairs))}"'
    return f'<tr class="{cls}"{attr}>{tds}</tr>'


def _empty(msg):
    return f'<div class="hec-empty">{E(msg)}</div>'


def _dot(color='green'):
    colors = {'green': '#22c55e', 'red': '#ef4444', 'yellow': '#eab308'}
    c = colors.get(color, color)
    return f'<span style="color:{c};font-size:16px">&#9679;</span>'


# ---------- section table functions ----------

def demo_panel(P):
    """Three-panel demographics row."""
    sex = 'Male' if P['gender'] == 'M' else ('Female' if P['gender'] == 'F' else P['gender'])
    demos = [
        ('Name', f"{P.get('last', P.get('family',''))}, {P['given']}"),
        ('Date of Birth', P['dob']),
        ('Age', f"{P['age']} years"),
        ('Gender', sex),
        ('Address', P['addr'] or '&mdash;'),
        ('Phone', '&mdash;'),
    ]
    demo_html = ''.join(
        f'<div class="demo-kv"><span class="dk">{k}</span><span class="dv">{v}</span></div>'
        for k, v in demos)

    # MRN table
    mrn_rows = ''
    name_str = f"{P.get('last', P.get('family',''))}, {P['given']}"
    for m in P.get('mrn_list', []):
        org = m.get('source') or m.get('qe') or VIEW_QE
        mrn_rows += (f'<tr><td>{E(org)}</td><td>{E(m["mrn"])}</td>'
                     f'<td>{E(name_str)}</td><td>{E(P["dob"])}</td>'
                     f'<td class="exp-icon">&#9654;</td></tr>')
    if not mrn_rows:
        mrn_rows = (f'<tr><td>{E(VIEW_QE)}</td><td>{E(P["mrn"])}</td>'
                    f'<td>{E(name_str)}</td><td>{E(P["dob"])}</td>'
                    f'<td class="exp-icon">&#9654;</td></tr>')
    mrn_tbl = ('<table class="hec-tbl mini"><thead><tr>'
               '<th>Organization</th><th>MRN</th><th>Name</th><th>DOB</th><th></th>'
               f'</tr></thead><tbody>{mrn_rows}</tbody></table>')

    return f"""<div class="demo-panels">
      <div class="demo-box"><div class="demo-title">Demographics</div>{demo_html}</div>
      <div class="demo-box"><div class="demo-title">Patients</div>{mrn_tbl}</div>
      <div class="demo-box"><div class="demo-title">Related Person</div>
        <div class="hec-empty">No related persons on file.</div></div>
    </div>"""


def enc_tbl(P):
    """Encounters table + summary."""
    ql = patient_source_label(P)
    r = ''
    for e in P['encs']:
        fac = e.get('facility') or ql
        r += _row([E(e['start']), _dot('green'), '&#127973;',
                   E(e['name']), E(fac), E(source_name(e, ql))],
                  extra=[('Encounter type', e.get('etype', '')),
                         ('Facility', e.get('facility', '')),
                         ('Attending', e.get('attending', '')),
                         ('Discharge date', e.get('stop', '')),
                         ('Discharge disposition', e.get('disposition', '')),
                         ('Reason', e.get('reason', ''))])
    table = _tbl(['Date', 'Status', 'Type', 'Admit Reason', 'Encounter Location', 'Source'], r) \
        if r else _empty('No encounters on file.')

    # summary: last 6 months + most recent 3
    summary_icons = ''
    for e in P['encs'][:6]:
        summary_icons += '<span class="enc-icon" title="Encounter">&#127973;</span> '
    recent_rows = ''
    for e in P['encs'][:3]:
        fac = e.get('facility') or ql
        recent_rows += f'<tr><td>{E(e["start"])}</td><td>{E(e["name"])}</td><td>{E(fac)}</td></tr>'
    recent_tbl = ''
    if recent_rows:
        recent_tbl = ('<table class="hec-tbl mini"><thead><tr>'
                      '<th>Date</th><th>Encounter</th><th>Location</th></tr></thead>'
                      f'<tbody>{recent_rows}</tbody></table>')
    summary = f"""<div class="enc-summary">
      <div class="enc-sum-left">
        <div class="sec-subtitle">Encounters &ndash; Last 6 months</div>
        <div class="enc-icons">{summary_icons if summary_icons else '<span class="hec-empty">None</span>'}</div>
        <div class="enc-count">{min(len(P['encs']), 6)} encounter(s)</div>
      </div>
      <div class="enc-sum-right">
        <div class="sec-subtitle">Most Recent Encounters</div>
        {recent_tbl if recent_tbl else '<div class="hec-empty">None</div>'}
      </div>
    </div>"""
    return table + summary


def allergy_tbl(P):
    """Allergies table."""
    ql = patient_source_label(P)
    r = ''
    for a in P['allergies']:
        r += _row(['', E(a['name']), '&mdash;', '&mdash;', _dot('green'), E(ql)])
    return _tbl(['Onset Date', 'Allergen', 'Reaction', 'Severity', 'Status', 'Source'], r) \
        if r else _empty('No allergies on file.')


def labs_tbl(P):
    """Laboratory Results with CCD/ORU dedup rendering."""
    ql = patient_source_label(P)
    ccd_badge = '<span class="src ccd">CCD</span>'
    oru_badge = '<span class="src oru">ORU</span>'
    r = ''

    # ORU results first
    if P.get('oru'):
        r += ('<tr class="grp oru-grp"><td colspan="7">Laboratory Feed &middot; ORU '
              f'(Health Information Exchange) &mdash; {len(P["oru"])} results</td></tr>')
        for o in sorted(P['oru'], key=lambda x: x['test']):
            tag = ('<span class="tag pref">preferred</span>' if o['dup']
                   else '<span class="tag new">new</span>')
            abn = o.get('flag', '') in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            flag_cell = (f'<span class="abn">{E(o.get("flag",""))}</span>' if abn
                         else E(o.get('flag', '')) or '&ndash;')
            status_dot = _dot('red') if abn else _dot('green')
            r += _row([f'{oru_badge} <b>{E(o["test"])}</b> {tag}', E(o['date']),
                       status_dot, '&#128196;', 'ORU Feed (HIE)',
                       '&#128229;'],
                      'oru-row', extra=oru_extra(o))

    # CCD panels
    for p in P['labs']:
        r += (f'<tr class="grp grouphdr"><td colspan="7">{E(p["panel"])}'
              f'<span class="gdate">{E(p["date"])}</span></td></tr>')
        for c in p['comps']:
            abn = c['flag'] in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            sup = c.get('superseded')
            note = '<span class="tag sup">superseded by ORU</span>' if sup else ''
            status_dot = _dot('red') if abn else _dot('green')
            r += _row([f'{ccd_badge} <span>{E(c["test"])}</span> {note}', E(c['date']),
                       status_dot, '&#128196;', E(ql),
                       '&#128229;'],
                      'sup' if sup else '', extra=lab_extra(c))

    legend = ''
    if P.get('oru'):
        legend = (f'<div class="hec-legend">{ccd_badge} C-CDA &nbsp; {oru_badge} ORU feed (HIE) &nbsp; '
                  '<span class="sup-ex">strikethrough</span> = CCD result superseded by a duplicate ORU result</div>')
    table = _tbl(['Description', 'Date', 'Status', 'Clinical Notes', 'Source', 'Actions'], r)
    return legend + table


def proc_tbl(P):
    """Procedures table."""
    ql = patient_source_label(P)
    r = ''.join(_row([E(p['date']), E(p['name']), '&mdash;', E(ql)]) for p in P['procs'])
    return _tbl(['Date', 'Procedure Name', 'Associated Diagnosis', 'Source'], r) \
        if r else _empty('No procedures on file.')


def vitals_tbl(P):
    """Vitals table."""
    ql = patient_source_label(P)
    r = ''.join(
        _row([E(v['date']), E(v['test']),
              f"{E(str(v['value']))} {E(v['unit'])}".strip(), E(ql)])
        for v in P['vitals'])
    return _tbl(['Date Recorded', 'Vital Sign', 'Result', 'Source'], r) \
        if r else _empty('No vitals on file.')


def problems_tbl(P):
    """Problem List table with tab headers."""
    ql = patient_source_label(P)
    r = ''
    for x in sorted(P['problems'], key=lambda c: c['status'] != 'Active'):
        r += _row([E(x['onset']), '&mdash;', E(x['name']), _dot('green'), E(ql)])
    table = _tbl(['Date', 'Code', 'Code Description', 'Status', 'Source'], r) \
        if r else _empty('No problems on file.')
    return f"""<div class="tab-group" data-tabgroup="problems">
      <div class="tab-bar">
        <span class="tab active" data-tab="problist">Problem List</span>
        <span class="tab" data-tab="encdiag">Encounter Diagnosis</span>
      </div>
      <div class="tab-content active" data-tab="problist">{table}</div>
      <div class="tab-content" data-tab="encdiag">{_empty('No encounter diagnoses on file.')}</div>
    </div>"""


def source_ccds_tbl(P):
    """Source CCDs panel."""
    ql = patient_source_label(P)
    r = ''
    seen = set()
    for m in P.get('mrn_list', []):
        src = m.get('source') or m.get('qe') or VIEW_QE
        if src in seen:
            continue
        seen.add(src)
        title = f"CCD Document &mdash; {src}"
        date_str = P.get('doc_date', '')
        r += _row([E(title), E(date_str), E(src), '&#128229;'])
    if not r:
        r = _row([f'CCD Document &mdash; {E(ql)}', E(P.get('doc_date', '')), E(ql), '&#128229;'])
    table = _tbl(['Title', 'Date Recorded', 'Source', 'Actions'], r)
    return f"""<div class="tab-group" data-tabgroup="sources">
      <div class="tab-bar">
        <span class="tab" data-tab="diagrpt">Diagnostic Reports</span>
        <span class="tab" data-tab="clinnotes">Clinical Notes</span>
        <span class="tab active" data-tab="srcccds">Source CCDs &#9757;</span>
      </div>
      <div class="tab-content" data-tab="diagrpt">{_empty('No diagnostic reports on file.')}</div>
      <div class="tab-content" data-tab="clinnotes">{_empty('No clinical notes on file.')}</div>
      <div class="tab-content active" data-tab="srcccds">{table}</div>
    </div>"""


def meds_tbl(P):
    """Medications table."""
    ql = patient_source_label(P)
    r = ''
    for m in P['meds']:
        status = 'Active' if not m['stop'] else 'Completed'
        r += _row([E(m['name']), E(m['start']), E(m['stop']) or '&ndash;',
                   status, E(ql)], extra=med_extra(m))
    return _tbl(['Medication', 'Start', 'Stop', 'Status', 'Source'], r) \
        if r else _empty('No medications on file.')


def imm_tbl(P):
    """Immunizations table."""
    ql = patient_source_label(P)
    r = ''.join(
        _row([E(i['name']), E(i['date']), 'Completed', E(ql)])
        for i in P['imms'])
    return _tbl(['Immunization', 'Date', 'Status', 'Source'], r) \
        if r else _empty('No immunizations on file.')


# ---------- category pills ----------
def category_pills(P):
    """Row of colored pill/badge buttons with counts."""
    cats = [
        ('Allergy', len(P['allergies']), 'sec-allergies'),
        ('CCD Results', sum(len(p['comps']) for p in P['labs']), 'sec-labs'),
        ('Clinical-Notes', 0, 'sec-sources'),
        ('Encounter', len(P['encs']), 'sec-encounters'),
        ('Encounter Diagnosis', 0, 'sec-problems'),
        ('Immunization', len(P['imms']), 'sec-immunizations'),
        ('Laboratory', len(P.get('oru', [])) + sum(len(p['comps']) for p in P['labs']), 'sec-labs'),
        ('Medication', len(P['meds']), 'sec-medications'),
        ('Problem List', len(P['problems']), 'sec-problems'),
        ('Procedure', len(P['procs']), 'sec-procedures'),
        ('Social History', 0, 'sec-demographics'),
        ('Vitals', len(P['vitals']), 'sec-vitals'),
    ]
    pills = ''
    for name, count, target in cats:
        pills += (f'<button class="cat-pill" data-scroll="{target}">'
                  f'{E(name)}<span class="pill-badge">{count}</span></button>')
    return f'<div class="cat-pills-row">{pills}</div>'


# ---------- render patient ----------
def render_patient(P, idx):
    """Full patient div block matching build_bronx.py attribute contract."""
    _aa = P.get('mrn_aa') or ''
    _qe = _aa.split('|')[0] if _aa else ''
    _src = _aa.split('|')[1] if '|' in _aa else ''
    _mrns = ';'.join(f"{m['qe']}|{m['source']}:{m['mrn']}" for m in P.get('mrn_list', []))
    name_str = f"{P.get('last', P.get('family','')).title()}, {P['given']}"
    style = '' if idx == 0 else ' style="display:none"'

    sections = f"""
      <!-- Patient tab bar -->
      <div class="patient-tab-bar">
        <span class="pt-arrow pt-prev">&#9664;</span>
        <span class="pt-tab active">{E(name_str)}</span>
        <span class="pt-arrow pt-next">&#9654;</span>
      </div>

      <!-- Patient Synopsis heading -->
      <div class="synopsis-bar">
        <span class="synopsis-title">Patient Synopsis</span>
        <span class="org-dropdown">Organizations &#9662;</span>
      </div>

      <!-- Clinical Timeline accordion -->
      <div class="timeline-acc">
        <span class="acc-toggle">&#9654;</span> Clinical Timeline
      </div>

      <!-- Category pills -->
      {category_pills(P)}

      <!-- Demographics -->
      <div id="sec-demographics-{idx}" class="hec-section">
        {demo_panel(P)}
      </div>

      <!-- Encounters -->
      <div id="sec-encounters-{idx}" class="hec-section full-width">
        <div class="sec-header">Encounters</div>
        {enc_tbl(P)}
      </div>

      <!-- Two-column: Allergies + Labs -->
      <div class="two-col">
        <div id="sec-allergies-{idx}" class="hec-section">
          <div class="sec-header">Allergies</div>
          {allergy_tbl(P)}
        </div>
        <div id="sec-labs-{idx}" class="hec-section">
          <div class="sec-header">Laboratory Results</div>
          {labs_tbl(P)}
        </div>
      </div>

      <!-- Two-column: Procedures + Vitals -->
      <div class="two-col">
        <div id="sec-procedures-{idx}" class="hec-section">
          <div class="sec-header">Procedures</div>
          {proc_tbl(P)}
        </div>
        <div id="sec-vitals-{idx}" class="hec-section">
          <div class="sec-header">Vitals</div>
          {vitals_tbl(P)}
        </div>
      </div>

      <!-- Two-column: Problems + Source CCDs -->
      <div class="two-col">
        <div id="sec-problems-{idx}" class="hec-section">
          <div class="sec-header">Problems</div>
          {problems_tbl(P)}
        </div>
        <div id="sec-sources-{idx}" class="hec-section">
          <div class="sec-header">Source CCDs</div>
          {source_ccds_tbl(P)}
        </div>
      </div>

      <!-- Medications -->
      <div id="sec-medications-{idx}" class="hec-section full-width">
        <div class="sec-header">Medications</div>
        {meds_tbl(P)}
      </div>

      <!-- Immunizations -->
      <div id="sec-immunizations-{idx}" class="hec-section full-width">
        <div class="sec-header">Immunizations</div>
        {imm_tbl(P)}
      </div>

      <!-- Footer -->
      <div class="hec-footer">&copy; 2026, All Rights Reserved. v2.0.1</div>
    """

    return f"""
    <div class="patient" data-idx="{idx}" data-first="{E(P['given'])}" data-last="{E(P.get('last', P.get('family','')))}" data-dob="{E(P['dob'])}" data-qe="{E(_qe)}" data-source="{E(_src)}" data-mrn="{E(P['mrn'])}" data-mrns="{E(_mrns)}"{style}>
      <div class="hec-content">
        {sections}
      </div>
    </div>"""


# ---------- CSS ----------
CSS = """
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:"Segoe UI",system-ui,Arial,sans-serif; color:#333; background:#f4f5f7;
    font-size:13.5px; display:flex; min-height:100vh; }

  /* ----- Sidebar ----- */
  .hec-sidebar { width:90px; min-height:100vh; background:#1a2332; position:fixed; left:0; top:0;
    z-index:100; display:flex; flex-direction:column; align-items:center; padding-top:10px;
    transition:width .2s; overflow:hidden; }
  .hec-sidebar.collapsed { width:0; padding:0; }
  .sidebar-collapse { position:absolute; top:8px; right:6px; color:#fff; cursor:pointer;
    font-size:14px; background:rgba(255,255,255,.1); border:none; border-radius:4px;
    width:22px; height:22px; display:flex; align-items:center; justify-content:center; }
  .sidebar-collapse:hover { background:rgba(255,255,255,.2); }
  .nav-icon { display:flex; flex-direction:column; align-items:center; padding:14px 6px;
    color:rgba(255,255,255,.7); cursor:pointer; font-size:10px; text-align:center;
    width:100%; text-decoration:none; transition:background .15s; }
  .nav-icon:hover { background:rgba(255,255,255,.08); color:#fff; }
  .nav-icon.active { background:rgba(255,255,255,.12); color:#fff; }
  .nav-icon .ni-emoji { font-size:20px; margin-bottom:3px; }
  .nav-icon .ni-label { font-size:9.5px; letter-spacing:.3px; }

  /* ----- Main wrapper ----- */
  .hec-main { margin-left:90px; flex:1; min-width:0; transition:margin-left .2s; }
  body.sidebar-hidden .hec-main { margin-left:0; }

  /* ----- Top header bar ----- */
  .hec-header { background:#fff; height:56px; display:flex; align-items:center;
    padding:0 24px; border-bottom:1px solid #e0e0e0; position:sticky; top:0; z-index:90; }
  .hec-logo { font-size:19px; font-weight:300; color:#5fb8b8; letter-spacing:-.3px; }
  .hec-logo b { font-weight:700; color:#008B8B; }
  .hec-logo .dot { color:#e8792b; }
  .hec-header .spacer { flex:1; }
  .hec-practitioner { display:flex; align-items:center; gap:8px; color:#555; font-size:12.5px; }
  .prac-dot { width:10px; height:10px; border-radius:50%; background:#22c55e; }
  .picker select { font-size:13px; padding:6px 10px; border:1px solid #ccc; border-radius:4px;
    min-width:230px; background:#fff; }

  /* ----- Patient tab bar ----- */
  .patient-tab-bar { display:flex; align-items:center; background:#fff; border-bottom:2px solid #eee;
    padding:0 18px; }
  .pt-tab { padding:12px 18px; font-weight:600; color:#333; font-size:14px; cursor:pointer;
    border-bottom:3px solid transparent; margin-bottom:-2px; }
  .pt-tab.active { border-bottom-color:#ea580c; color:#1a2332; }
  .pt-arrow { padding:8px 12px; cursor:pointer; color:#666; font-size:14px; user-select:none; }
  .pt-arrow:hover { color:#008B8B; }

  /* ----- Synopsis bar ----- */
  .synopsis-bar { display:flex; align-items:center; justify-content:space-between;
    padding:14px 22px; background:#fff; border-bottom:1px solid #eee; }
  .synopsis-title { font-size:18px; font-weight:700; color:#1a2332; }
  .org-dropdown { font-size:12.5px; color:#008B8B; cursor:pointer; padding:6px 12px;
    border:1px solid #d0d5dd; border-radius:6px; background:#fff; }

  /* ----- Timeline accordion ----- */
  .timeline-acc { padding:10px 22px; background:#f8f9fb; border-bottom:1px solid #e5e7eb;
    font-weight:600; color:#1a2332; font-size:13.5px; cursor:pointer; user-select:none; }
  .acc-toggle { font-size:11px; margin-right:6px; display:inline-block; transition:transform .2s; }
  .timeline-acc.open .acc-toggle { transform:rotate(90deg); }

  /* ----- Category pills ----- */
  .cat-pills-row { display:flex; flex-wrap:wrap; gap:8px; padding:12px 22px; background:#fff;
    border-bottom:1px solid #eee; }
  .cat-pill { display:inline-flex; align-items:center; gap:6px; background:#2a7d8b; color:#fff;
    border:none; border-radius:20px; padding:6px 14px; font-size:12px; font-weight:600;
    cursor:pointer; font-family:inherit; transition:background .15s; }
  .cat-pill:hover { background:#1a5f6b; }
  .pill-badge { background:rgba(255,255,255,.25); color:#fff; font-size:10px; font-weight:700;
    min-width:20px; height:20px; border-radius:50%; display:inline-flex; align-items:center;
    justify-content:center; padding:0 5px; }

  /* ----- Demographics panels ----- */
  .demo-panels { display:grid; grid-template-columns:1fr 1.5fr 1fr; gap:16px; padding:16px 22px; }
  .demo-box { background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:14px; }
  .demo-title { font-weight:700; color:#1a2332; font-size:13.5px; margin-bottom:10px;
    padding-bottom:8px; border-bottom:1px solid #eee; }
  .demo-kv { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f3f4f6; }
  .dk { color:#6b7280; font-size:12.5px; }
  .dv { font-weight:600; font-size:12.5px; }

  /* ----- Section layout ----- */
  .hec-content { padding:0 0 20px; }
  .hec-section { margin:0 22px 16px; }
  .hec-section.full-width { margin:0 22px 16px; }
  .sec-header { font-size:15px; font-weight:700; color:#1a2332; padding:10px 0 8px;
    border-bottom:2px solid #e5e7eb; margin-bottom:8px; }
  .sec-subtitle { font-size:13px; font-weight:600; color:#475467; margin-bottom:6px; }
  .two-col { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin:0 22px 16px; }
  .two-col .hec-section { margin:0; }

  /* ----- Encounters summary ----- */
  .enc-summary { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px; }
  .enc-icons { font-size:20px; margin:6px 0; }
  .enc-icon { margin-right:4px; }
  .enc-count { font-size:12px; color:#6b7280; }

  /* ----- Tables ----- */
  table.hec-tbl { width:100%; border-collapse:collapse; background:#fff; border-radius:8px;
    overflow:hidden; }
  .hec-tbl thead th { text-align:left; background:#f8f9fa; color:#475467; font-weight:600;
    font-size:12px; padding:10px 12px; border-bottom:1px solid #e5e7eb; white-space:nowrap; }
  .hec-tbl tbody td { padding:9px 12px; border-bottom:1px solid #f3f4f6; vertical-align:top;
    font-size:13px; }
  .hec-tbl tbody tr:hover { background:#f8fffe; }
  .hec-tbl.mini { font-size:12px; }
  .hec-tbl.mini td, .hec-tbl.mini th { padding:6px 8px; }
  .exp-icon { color:#008B8B; cursor:pointer; }
  tr.grp td { background:#e8ecef !important; font-weight:700; color:#37474f; }
  tr.grp.oru-grp td { background:#e3f2fd !important; color:#0d47a1; }
  tr.grp .gdate { float:right; font-weight:500; color:#607d8b; }
  tr.oru-row td { background:#f3f9ff !important; }
  tr.sup td span:not(.src):not(.tag) { text-decoration:line-through; color:#9aa7ad; }
  .abn, .abnval { color:#c62828; font-weight:700; }

  .src { display:inline-block; font-size:9.5px; font-weight:800; padding:1px 5px;
    border-radius:4px; margin-right:5px; }
  .src.ccd { background:#eceff1; color:#607d8b; border:1px solid #cfd8dc; }
  .src.oru { background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }
  .tag { font-size:10px; padding:1px 6px; border-radius:8px; margin-left:5px; }
  .tag.pref { background:#e3f2fd; color:#1565c0; }
  .tag.new { background:#e8f5e9; color:#2e7d32; }
  .tag.sup { background:#fdecea; color:#b0431f; border:1px solid #f3c0b6; }
  .hec-legend { font-size:12px; color:#666; padding:9px 12px; background:#fafbfc;
    border:1px solid #e0e0e0; border-radius:6px; margin-bottom:8px; }
  .hec-legend .sup-ex { text-decoration:line-through; color:#9aa7ad; }
  .hec-empty { padding:16px; color:#888; font-style:italic; }

  /* ----- Tab groups ----- */
  .tab-bar { display:flex; gap:0; border-bottom:2px solid #e5e7eb; margin-bottom:8px; }
  .tab { padding:8px 16px; font-size:12.5px; font-weight:600; color:#6b7280; cursor:pointer;
    border-bottom:2px solid transparent; margin-bottom:-2px; }
  .tab.active { color:#3b82f6; border-bottom-color:#3b82f6; }
  .tab:hover { color:#1a2332; }
  .tab-content { display:none; }
  .tab-content.active { display:block; }

  /* ----- Footer ----- */
  .hec-footer { text-align:center; color:#9ca3af; font-size:12px; padding:20px 22px 12px;
    border-top:1px solid #e5e7eb; margin-top:16px; }

  /* ----- Scroll-to-top ----- */
  .scroll-top { position:fixed; bottom:24px; right:24px; width:40px; height:40px;
    border-radius:50%; background:#008B8B; color:#fff; border:none; font-size:18px;
    cursor:pointer; display:none; align-items:center; justify-content:center;
    box-shadow:0 2px 8px rgba(0,0,0,.2); z-index:80; }
  .scroll-top:hover { background:#006d6d; }

  /* ----- Pagination ----- */
  .hec-pager { display:flex; align-items:center; justify-content:center; gap:6px;
    padding:10px; color:#6b7280; font-size:12px; }
  .hec-pager span { cursor:pointer; padding:2px 6px; }

  /* ----- Responsive ----- */
  @media (max-width:900px) {
    .two-col { grid-template-columns:1fr; }
    .demo-panels { grid-template-columns:1fr; }
    .enc-summary { grid-template-columns:1fr; }
  }
"""

# ---------- JavaScript ----------
JS = """
(function(){
  // Patient switcher
  var sel=document.getElementById('psel');
  function switchPatient(idx){
    document.querySelectorAll('.patient').forEach(function(p){
      p.style.display=(p.getAttribute('data-idx')===String(idx))?'':'none';
    });
    if(sel) sel.value=idx;
    window.scrollTo(0,0);
  }
  if(sel) sel.addEventListener('change',function(){ switchPatient(sel.value); });

  // Sidebar collapse
  var sidebar=document.querySelector('.hec-sidebar');
  var colBtn=document.getElementById('sidebarToggle');
  if(colBtn) colBtn.addEventListener('click',function(){
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-hidden');
  });

  // Arrow navigation
  document.querySelectorAll('.pt-prev').forEach(function(btn){
    btn.addEventListener('click',function(){
      if(!sel) return;
      var cur=parseInt(sel.value)||0;
      if(cur>0) switchPatient(cur-1);
    });
  });
  document.querySelectorAll('.pt-next').forEach(function(btn){
    btn.addEventListener('click',function(){
      if(!sel) return;
      var cur=parseInt(sel.value)||0;
      if(cur<sel.options.length-1) switchPatient(cur+1);
    });
  });

  // Category pill click -> scroll to section
  document.querySelectorAll('.cat-pill').forEach(function(pill){
    pill.addEventListener('click',function(){
      var target=pill.getAttribute('data-scroll');
      var pat=pill.closest('.patient');
      if(!pat) return;
      var idx=pat.getAttribute('data-idx');
      var el=document.getElementById(target+'-'+idx);
      if(el) el.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });

  // Tab switching within sections
  document.querySelectorAll('.tab-group').forEach(function(group){
    group.querySelectorAll('.tab').forEach(function(tab){
      tab.addEventListener('click',function(){
        var tabId=tab.getAttribute('data-tab');
        group.querySelectorAll('.tab').forEach(function(t){ t.classList.toggle('active',t.getAttribute('data-tab')===tabId); });
        group.querySelectorAll('.tab-content').forEach(function(c){ c.classList.toggle('active',c.getAttribute('data-tab')===tabId); });
      });
    });
  });

  // Clinical Timeline accordion toggle
  document.querySelectorAll('.timeline-acc').forEach(function(acc){
    acc.addEventListener('click',function(){ acc.classList.toggle('open'); });
  });

  // Scroll-to-top button
  var topBtn=document.getElementById('scrollTop');
  if(topBtn){
    window.addEventListener('scroll',function(){
      topBtn.style.display=window.scrollY>300?'flex':'none';
    });
    topBtn.addEventListener('click',function(){ window.scrollTo({top:0,behavior:'smooth'}); });
  }
})();
"""


# ---------- module-level data loading (build_bronx.py pattern) ----------
files = sorted(glob.glob(os.path.join(CCD_DIR, '*.xml')))
if TRN_DIR:
    files += sorted(glob.glob(os.path.join(TRN_DIR, '*.xml')))
patients = [parse_ccd(f) for f in files]
for P in patients:
    P['oru'] = []
load_oru(patients)
if ORU_HL7_DIR:
    load_oru_hl7(patients, os.path.join(ORU_HL7_DIR, '*.hl7'))
patients = merge_by_person(patients)

# Add 'last' alias for family (build_bronx.py compat)
for P in patients:
    if 'last' not in P:
        P['last'] = P.get('family', '')

# ---------- build HTML ----------
options = ''.join(
    f'<option value="{i}">{E(P["last"].title())}, {E(P["given"])}  ({P["age"]}y)</option>'
    for i, P in enumerate(patients))
blocks = '\n'.join(render_patient(P, i) for i, P in enumerate(patients))

# Sidebar nav items
sidebar_items = [
    ('&#127968;', 'User Home', True),
    ('&#128202;', 'Dashboard', False),
    ('&#128203;', 'Logs', False),
    ('&#128300;', 'Results', True),
    ('&#128196;', 'Reports', False),
    ('&#9993;', 'Secure Messaging', False),
    ('&#128682;', 'Logout', False),
]
sidebar_html = ''
for emoji, label, is_active in sidebar_items:
    cls = 'nav-icon active' if is_active and label == 'Results' else 'nav-icon'
    sidebar_html += (f'<a class="{cls}"><span class="ni-emoji">{emoji}</span>'
                     f'<span class="ni-label">{label}</span></a>')

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HealtheConnections &mdash; Patient Synopsis</title>
<style>{CSS}</style>
</head>
<body data-view-qe="{E(VIEW_QE)}">
  <!-- Sidebar -->
  <nav class="hec-sidebar" id="hecSidebar">
    <button class="sidebar-collapse" id="sidebarToggle" title="Collapse sidebar">&lt;</button>
    {sidebar_html}
  </nav>

  <!-- Main area -->
  <div class="hec-main">
    <!-- Top header bar -->
    <div class="hec-header">
      <div class="hec-logo healtheconnections-brand">healthe<span class="dot">&bull;</span><b>connections</b></div>
      <div class="spacer"></div>
      <div class="picker"><select id="psel">{options}</select></div>
      <div class="hec-practitioner">
        <span class="prac-dot"></span>
        SIR LANCELOT &middot; Last Logged on {datetime.now().strftime('%m/%d/%Y %I:%M %p')}
      </div>
    </div>

    <!-- Patient blocks -->
    {blocks}
  </div>

  <button class="scroll-top" id="scrollTop" title="Back to top">&#8679;</button>

<script>{JS}</script>
</body>
</html>"""

HTML = inject_bug(HTML)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f"Wrote {OUT} with {len(patients)} patient(s)")
