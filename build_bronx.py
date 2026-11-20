"""
Bronx RHIO / IMAT Solutions-style view of the same merged-Marcus data.
Same data + same functionality (section nav, CCD/ORU dedup, MRN Array,
Missing data logging) as the Hixny and HEALTHeLINK views — IMAT look & feel.

Config via env (set by build_home.py): CHART_CCD_DIR, CHART_ORU_HL7, CHART_OUT,
CHART_QE. Output default: patient_chart_bronx.html.
"""
import os
import glob
import html
import json
from datetime import datetime

from ccda_parse import parse_ccd, load_oru, load_oru_hl7, merge_by_person
from bug_widget import inject as inject_bug
from ccda_parse import med_extra, lab_extra, oru_extra

CCD_DIR = os.environ.get('CHART_CCD_DIR', 'ccds')
OUT = os.environ.get('CHART_OUT', 'patient_chart_bronx.html')
ORU_HL7_DIR = os.environ.get('CHART_ORU_HL7', '')
VIEW_QE = os.environ.get('CHART_QE', 'BRONX')
E = html.escape


def dob_long(d):  # MM/DD/YYYY -> "Mon D, YYYY"
    try:
        return datetime.strptime(d, '%m/%d/%Y').strftime('%b %-d, %Y')
    except (ValueError, TypeError):
        try:
            return datetime.strptime(d, '%m/%d/%Y').strftime('%b %#d, %Y')
        except (ValueError, TypeError):
            return d


# ---------- table helpers (IMAT zebra, leading magnifier column) ----------
def tbl(headers, rows_html):
    head = '<th class="ic"></th>' + ''.join(f'<th>{E(h)}</th>' for h in headers)
    return f'<table class="bx-tbl"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table>'


def row(cells, cls='', extra=None):
    tds = '<td class="ic">&#128269;</td>' + ''.join(f'<td>{c}</td>' for c in cells)
    attr = ''
    pairs = [[k, v] for k, v in (extra or []) if v]
    if pairs:
        attr = f' data-extra="{E(json.dumps(pairs))}"'
    return f'<tr class="{cls}"{attr}>{tds}</tr>'


def empty(msg):
    return f'<div class="bx-empty">{E(msg)}</div>'


def conditions_tbl(P):
    r = ''
    for x in sorted(P['problems'], key=lambda c: c['status'] != 'Active'):
        r += row([E(x['name']), E(x['onset']), E(x['resolved']) or '&ndash;', E(x['status'])])
    return tbl(['Problem', 'Onset', 'Resolved', 'Status'], r) if r else empty('No problems on file.')


def meds_tbl(P):
    r = ''
    for m in P['meds']:
        status = 'Active' if not m['stop'] else 'Completed'
        r += row([E(m['name']), E(m['start']), E(m['stop']) or '&ndash;', status], extra=med_extra(m))
    return tbl(['Medication', 'Start', 'Stop', 'Status'], r) if r else empty('No medications on file.')


def vitals_tbl(P):
    r = ''.join(row([E(v['test']), E(str(v['value'])), E(v['unit']), E(v['date'])]) for v in P['vitals'])
    return tbl(['Observation', 'Value', 'Units', 'Date'], r) if r else empty('No observations on file.')


def imm_tbl(P):
    r = ''.join(row([E(i['name']), E(i['date']), 'Completed']) for i in P['imms'])
    return tbl(['Immunization', 'Date', 'Status'], r) if r else empty('No immunizations on file.')


def proc_tbl(P):
    r = ''.join(row([E(p['name']), E(p['date'])]) for p in P['procs'])
    return tbl(['Procedure', 'Date'], r) if r else empty('No procedures on file.')


def enc_tbl(P):
    r = ''.join(row([E(e['name']), E(e.get('facility', '')) or 'Bronx RHIO', E(e['start']),
                     E(e['stop']) or '&ndash;', E(e.get('attending', '')) or '&ndash;',
                     E(e.get('pcp', '')) or '&ndash;'],
                    extra=[('Discharge disposition', e.get('disposition', '')),
                           ('Reason for visit', e.get('reason', '')),
                           ('Encounter type', e.get('etype', ''))])
                for e in P['encs'])
    return tbl(['ADT / Encounter', 'Facility', 'Admit Date', 'Discharge Date', 'Attending', 'PCP'], r) \
        if r else empty('No admits/discharges/registrations on file.')


def labs_tbl(P):
    ccd = '<span class="src ccd">CCD</span>'
    oru = '<span class="src oru">ORU</span>'
    r = ''
    if P.get('oru'):
        r += ('<tr class="grp oru"><td class="ic"></td><td colspan="6">Laboratory Feed &middot; ORU '
              f'(Health Information Exchange) &mdash; {len(P["oru"])} results</td></tr>')
        for o in sorted(P['oru'], key=lambda x: x['test']):
            tag = '<span class="tag pref">preferred</span>' if o['dup'] else '<span class="tag new">new</span>'
            abn = o.get('flag', '') in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            r += row([f'{oru} <b>{E(o["test"])}</b> {tag}', f'<b>{E(str(o["value"]))}</b>', E(o['unit']),
                      E(o.get('range', '')) or '&ndash;',
                      (f'<span class="abn">{E(o.get("flag",""))}</span>' if abn else E(o.get('flag', '')) or '&ndash;'),
                      E(o['date'])], 'oru-row', extra=oru_extra(o))
    for p in P['labs']:
        r += (f'<tr class="grp"><td class="ic"></td><td colspan="6">{E(p["panel"])}'
              f'<span class="gdate">{E(p["date"])}</span></td></tr>')
        for c in p['comps']:
            abn = c['flag'] in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            sup = c.get('superseded')
            note = '<span class="tag sup">superseded by ORU</span>' if sup else ''
            r += row([f'{ccd} <span>{E(c["test"])}</span> {note}',
                      f'<span class="{"abnval" if abn else ""}">{E(c["value"])}</span>', E(c['unit']),
                      E(c['range']) or '&ndash;', (f'<span class="abn">{E(c["flag"])}</span>' if abn else E(c['flag']) or '&ndash;'),
                      E(c['date'])], 'sup' if sup else '', extra=lab_extra(c))
    legend = (f'<div class="bx-legend">{ccd} C-CDA &nbsp; {oru} ORU feed (HIE) &nbsp; '
              '<span class="sup-ex">strikethrough</span> = CCD result superseded by a duplicate ORU result</div>'
              if P.get('oru') else '')
    return legend + tbl(['Observation', 'Value', 'Units', 'Reference Range', 'Abnormal', 'Date'], r)


def demo_tbl(P):
    rows = [
        ('MPID', P['mpiid']), ('Name', f"{P['last']}, {P['given']}" if P.get('last') else f"{P['family']}, {P['given']}"),
        ('Date of Birth', P['dob']), ('Age', f"{P['age']} years"), ('Gender', 'Male' if P['gender'] == 'M' else ('Female' if P['gender'] == 'F' else P['gender'])),
        ('Address', P['addr']), ('Race', P['race']), ('Ethnicity', P['eth']), ('Language', P['lang']),
    ]
    body = ''.join(f'<div class="kv"><span class="k">{E(k)}</span><span class="v">{E(str(v))}</span></div>'
                   for k, v in rows if v)
    return f'<div class="bx-demo">{body}</div>'


def summary_cards(P):
    def mini(items, emptymsg):
        if not items:
            return f'<div class="mini-empty">{E(emptymsg)}</div>'
        return '<ul class="mini">' + ''.join(f'<li>{it}</li>' for it in items) + '</ul>'
    active = [p for p in P['problems'] if p['status'] == 'Active']
    prob = [f'{E(p["name"])} <span class="muted">&middot; {E(p["onset"])}</span>' for p in active[:8]]
    meds = [f'{E(m["name"])}' for m in (P['meds'][:8])]
    labs = []
    for o in P.get('oru', [])[:4]:
        labs.append(f'<span class="src oru">ORU</span> {E(o["test"])}: <b>{E(str(o["value"]))} {E(o["unit"])}</b>')
    if P['labs']:
        for c in P['labs'][-1]['comps'][:4]:
            labs.append(f'<span class="src ccd">CCD</span> {E(c["test"])}: {E(c["value"])} {E(c["unit"])}')
    vit = [f'{E(v["test"])}: <b>{E(v["value"])} {E(v["unit"])}</b>' for v in P['vitals'][:6]]
    im = [f'{E(i["name"])} <span class="muted">&middot; {E(i["date"])}</span>' for i in P['imms'][:6]]

    def card(title, body):
        return f'<div class="bx-card"><div class="bx-card-h">{E(title)}</div><div class="bx-card-b">{body}</div></div>'
    return ('<div class="bx-cards">'
            + card('Problems', mini(prob, 'No active problems'))
            + card('Medications', mini(meds, 'No medications'))
            + card('Recent Labs', mini(labs, 'No labs'))
            + card('Observations / Vitals', mini(vit, 'No vitals'))
            + card('Immunizations', mini(im, 'No immunizations'))
            + '</div>')


NAV = [
    ('Patient Info', 'patient-info', True),
    ('Advance Directives', '', False),
    ('Summary', 'summary', True),
    ('Admits/Discharges/Registrations', 'adt', True),
    ('Labs', 'labs', True),
    ('Observations/Vitals', 'vitals', True),
    ('Transcribed Reports', '', False),
    ('Radiology', '', False),
    ('Medications - Administered', '', False),
    ('Medications - Prescribed', 'medications', True),
    ('Problems', 'problems', True),
    ('Immunizations', 'immunizations', True),
    ('Procedures', 'procedures', True),
    ('eHealth Exchange2', '', False),
    ('Links', '', False),
    ('All', '', False),
]


def render_patient(P, idx):
    panes = {
        'patient-info': demo_tbl(P),
        'summary': summary_cards(P),
        'adt': enc_tbl(P),
        'labs': labs_tbl(P),
        'vitals': vitals_tbl(P),
        'medications': meds_tbl(P),
        'problems': conditions_tbl(P),
        'immunizations': imm_tbl(P),
        'procedures': proc_tbl(P),
    }
    navhtml = ''
    for label, target, data in NAV:
        cls = 'nav-item'
        if target == 'summary':
            cls += ' sel'
        if not data:
            cls += ' disabled'
        attr = f' data-target="{target}"' if target else ''
        navhtml += f'<a class="{cls}"{attr}>{E(label)}</a>'
    paneshtml = ''.join(
        f'<div class="bx-pane{" active" if t == "summary" else ""}" data-pane="{t}">{html_}</div>'
        for t, html_ in panes.items())

    _aa = P.get('mrn_aa') or ''
    _qe = _aa.split('|')[0] if _aa else ''
    _src = _aa.split('|')[1] if '|' in _aa else ''
    _mrns = ';'.join(f"{m['qe']}|{m['source']}:{m['mrn']}" for m in P.get('mrn_list', []))
    sex = 'Male' if P['gender'] == 'M' else ('Female' if P['gender'] == 'F' else P['gender'])
    banner = f"{P['family'].title()}, {P['given']}&nbsp;&nbsp;{E(dob_long(P['dob']))}&nbsp;&nbsp;({P['age']} years)&nbsp;&nbsp;{sex}"
    style = '' if idx == 0 else ' style="display:none"'
    return f"""
    <div class="patient" data-idx="{idx}" data-first="{E(P['given'])}" data-last="{E(P['family'])}" data-dob="{E(P['dob'])}" data-qe="{E(_qe)}" data-source="{E(_src)}" data-mrn="{E(P['mrn'])}" data-mrns="{E(_mrns)}"{style}>
      <div class="bx-cols">
        <nav class="bx-nav">
          {navhtml}
        </nav>
        <div class="bx-main">
          <div class="bx-banner">{banner}<span class="bx-help">?</span></div>
          <div class="bx-toolbar">
            <span class="t-ic" title="Refresh">&#8635;</span>
            <span class="t-ic" title="Filter">&#9660;&#9650;</span>
            <span class="t-btn">&#128269; VIEW RECORDS</span>
            <span class="t-sel">&#10003; SELECT TO PRINT</span>
            <span class="t-print" title="Print">&#128424;</span>
          </div>
          <div class="bx-panes">{paneshtml}</div>
          <div class="bx-pager">
            <span>&#8676; &#9664; <input value="1" readonly> / 1 &#9654; &#8677;</span>
            <span class="pp">250 items per page</span>
            <span class="cnt">1 &ndash; 1 of 1 items</span>
          </div>
          <div class="bx-foot">Data as of {datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')}</div>
        </div>
      </div>
    </div>"""


# ---------- build ----------
TRN_DIR = os.environ.get('CHART_TRN_DIR', '')
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

options = ''.join(f'<option value="{i}">{E(P["family"].title())}, {E(P["given"])}  ({P["age"]}y)</option>'
                  for i, P in enumerate(patients))
blocks = '\n'.join(render_patient(P, i) for i, P in enumerate(patients))

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMAT Solutions &mdash; Bronx RHIO</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Segoe UI",Arial,sans-serif; color:#333; background:#fff; font-size:13.5px; }}
  a {{ color:inherit; text-decoration:none; }}
  .muted {{ color:#888; }}

  .appbar {{ display:flex; align-items:center; gap:14px; padding:12px 18px; background:#fff;
    border-bottom:3px solid #00acc1; }}
  .brand {{ font-size:17px; font-weight:600; color:#333; }}
  .appbar .spacer {{ flex:1; }}
  .picker select {{ font-size:13px; padding:6px 10px; border:1px solid #ccc; border-radius:3px; min-width:230px; }}
  .user {{ color:#555; font-weight:600; }}

  .bx-cols {{ display:flex; min-height:calc(100vh - 52px); }}
  .bx-nav {{ width:232px; flex:none; background:#fff; border-right:1px solid #e0e0e0; padding:6px 0; }}
  .bx-lookup {{ color:#555; padding:12px 18px; border-bottom:1px solid #eee; margin-bottom:6px; }}
  .nav-item {{ display:block; padding:9px 18px; color:#333; cursor:pointer; font-size:13.5px; }}
  .nav-item:hover {{ background:#f2f6f8; }}
  .nav-item.sel {{ font-weight:700; color:#000; background:#eef4f7; border-left:3px solid #00acc1; padding-left:15px; }}
  .nav-item.disabled {{ color:#bbb; cursor:default; }}
  .nav-item.disabled:hover {{ background:none; }}

  .bx-main {{ flex:1; min-width:0; padding:14px 16px 0; background:#fafafa; }}
  .bx-banner {{ background:#5f6368; color:#fff; padding:12px 16px; font-size:15px; display:flex; align-items:center; }}
  .bx-banner .bx-help {{ margin-left:auto; width:22px; height:22px; border-radius:50%; border:1px solid #cfd8dc;
    display:flex; align-items:center; justify-content:center; font-size:12px; }}
  .bx-toolbar {{ display:flex; align-items:center; gap:16px; background:#eceff1; border:1px solid #e0e0e0; border-top:none;
    padding:8px 14px; }}
  .t-ic {{ color:#555; cursor:default; }}
  .t-btn {{ background:#2196f3; color:#fff; font-weight:600; font-size:12px; padding:6px 12px; border-radius:3px; }}
  .t-sel {{ color:#2196f3; font-weight:600; font-size:12px; }}
  .t-print {{ margin-left:auto; width:30px; height:30px; border-radius:50%; background:#2196f3; color:#fff;
    display:flex; align-items:center; justify-content:center; }}

  .bx-panes {{ background:#fff; border:1px solid #e0e0e0; border-top:none; }}
  .bx-pane {{ display:none; }}
  .bx-pane.active {{ display:block; }}

  table.bx-tbl {{ width:100%; border-collapse:collapse; }}
  .bx-tbl thead th {{ text-align:left; background:#e6eaed; color:#444; font-weight:600; font-size:12.5px;
    padding:8px 10px; border-bottom:1px solid #d5dadd; white-space:nowrap; }}
  .bx-tbl th.ic, .bx-tbl td.ic {{ width:30px; text-align:center; color:#90a4ae; }}
  .bx-tbl tbody td {{ padding:7px 10px; border-bottom:1px solid #eee; vertical-align:top; }}
  .bx-tbl tbody tr:nth-child(even) {{ background:#f5f7f8; }}
  .bx-tbl tbody tr:hover {{ background:#eef4f7; }}
  tr.grp td {{ background:#dfe6ea !important; font-weight:700; color:#37474f; }}
  tr.grp.oru td {{ background:#e3f2fd !important; color:#0d47a1; }}
  tr.grp .gdate {{ float:right; font-weight:500; color:#607d8b; }}
  tr.oru-row td {{ background:#f3f9ff !important; }}
  .abn, .abnval {{ color:#c62828; font-weight:700; }}
  tr.sup td span:not(.src):not(.tag) {{ text-decoration:line-through; color:#9aa7ad; }}

  .src {{ display:inline-block; font-size:9.5px; font-weight:800; padding:1px 5px; border-radius:4px; margin-right:5px; }}
  .src.ccd {{ background:#eceff1; color:#607d8b; border:1px solid #cfd8dc; }}
  .src.oru {{ background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }}
  .tag {{ font-size:10px; padding:1px 6px; border-radius:8px; margin-left:5px; }}
  .tag.pref {{ background:#e3f2fd; color:#1565c0; }}
  .tag.new {{ background:#e8f5e9; color:#2e7d32; }}
  .tag.sup {{ background:#fdecea; color:#b0431f; border:1px solid #f3c0b6; }}
  .bx-legend {{ font-size:12px; color:#666; padding:9px 12px; background:#fafbfc; border:1px solid #e0e0e0; border-top:none; }}
  .bx-legend .sup-ex {{ text-decoration:line-through; color:#9aa7ad; }}
  .bx-empty {{ padding:16px; color:#888; font-style:italic; }}

  .bx-demo {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:2px 24px; padding:14px 16px; }}
  .kv {{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #eee; }}
  .kv .k {{ color:#888; }} .kv .v {{ font-weight:600; text-align:right; }}

  .bx-cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; padding:14px; }}
  .bx-card {{ border:1px solid #e0e0e0; border-radius:4px; background:#fff; }}
  .bx-card-h {{ background:#eceff1; padding:9px 12px; font-weight:700; color:#37474f; border-bottom:1px solid #e0e0e0; }}
  .bx-card-b {{ padding:10px 12px; }}
  ul.mini {{ list-style:none; margin:0; padding:0; }}
  ul.mini li {{ padding:5px 0; border-bottom:1px dashed #eef1f2; font-size:13px; }}
  ul.mini li:last-child {{ border-bottom:none; }}
  .mini-empty {{ color:#888; font-style:italic; }}

  .bx-pager {{ display:flex; align-items:center; gap:18px; background:#f3f3f3; border:1px solid #e0e0e0; border-top:none;
    padding:7px 14px; color:#555; font-size:12.5px; }}
  .bx-pager input {{ width:34px; text-align:center; border:1px solid #ccc; border-radius:3px; }}
  .bx-pager .cnt {{ margin-left:auto; }}
  .bx-foot {{ text-align:center; color:#888; font-style:italic; font-size:12px; padding:12px; }}
</style>
</head>
<body data-view-qe="{E(VIEW_QE)}">
  <div class="appbar">
    <div class="spacer"></div>
    <div class="picker"><select id="psel">{options}</select></div>
    <div class="user">SIR LANCELOT &#9662;</div>
  </div>
  {blocks}
<script>
(function(){{
  function show(pat, target){{
    pat.querySelectorAll('.bx-pane').forEach(function(p){{ p.classList.toggle('active', p.getAttribute('data-pane')===target); }});
    pat.querySelectorAll('.nav-item[data-target]').forEach(function(n){{ n.classList.toggle('sel', n.getAttribute('data-target')===target); }});
    window.scrollTo(0,0);
  }}
  document.querySelectorAll('.patient').forEach(function(pat){{
    pat.querySelectorAll('.nav-item[data-target]').forEach(function(n){{
      n.addEventListener('click', function(){{ show(pat, n.getAttribute('data-target')); }});
    }});
  }});
  var sel=document.getElementById('psel');
  if(sel) sel.addEventListener('change', function(){{
    document.querySelectorAll('.patient').forEach(function(pat){{ pat.style.display = (pat.getAttribute('data-idx')===sel.value)?'':'none'; }});
    window.scrollTo(0,0);
  }});
}})();
</script>
</body>
</html>"""

HTML = inject_bug(HTML)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f"Wrote {OUT} with {len(patients)} patient(s)")
