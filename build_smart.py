"""
Render a SMART on FHIR-style Community Health Record from the same C-CDA + ORU
data, as its own document (patient_chart_smart.html). Card dashboard + tabs,
patient context banner, FHIR resource tags, CCD/ORU provenance with dedup.
Look & feel inspired by HIE portals (CRISP, Hixny) and SMART on FHIR apps.
"""
import glob
import os
import html
import json
from datetime import datetime

from ccda_parse import parse_ccd, load_oru, load_oru_hl7, merge_by_person
from bug_widget import inject as inject_bug
from ccda_parse import med_extra, lab_extra, oru_extra, extra_attr


def dextra(pairs):
    """Render a data-extra attribute (JSON [label,value] pairs) for drill-in."""
    p = [[k, v] for k, v in pairs if v]
    return f' data-extra="{html.escape(json.dumps(p))}"' if p else ''

# Data source is configurable so the same renderer can build either the base
# demo (ccds/ + FHIR ORU) or the patient cohort (sample_patients + HL7 ORU).
CCD_DIR = os.environ.get('CHART_CCD_DIR', 'ccds')
OUT = os.environ.get('CHART_OUT', 'patient_chart_smart.html')
ORU_HL7_DIR = os.environ.get('CHART_ORU_HL7', '')   # if set, load HL7 ORU from here
TITLE = os.environ.get('CHART_TITLE', 'Community Health Record')
VIEW_QE = os.environ.get('CHART_QE', '')            # the QE whose portal this view represents
E = html.escape


def icon(name):
    paths = {
        'alert': '<path d="M12 2L1 21h22L12 2zm0 15h-1v-2h2v2h-1zm0-4h-1V9h2v4h-1z"/>',
        'pulse': '<path d="M3 12h4l2 6 4-14 2 8h6"/>',
        'pill': '<path d="M10.5 3a6 6 0 00-6 6v6a6 6 0 0012 0V9a6 6 0 00-6-6zm-4 6a4 4 0 118 0v2h-8V9z"/>',
        'lab': '<path d="M9 2v6l-5 9a2 2 0 002 3h12a2 2 0 002-3l-5-9V2"/>',
        'heart': '<path d="M12 21s-7-4.5-9.5-9A5 5 0 0112 6a5 5 0 019.5 6C19 16.5 12 21 12 21z"/>',
        'shield': '<path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/>',
        'doc': '<path d="M6 2h8l4 4v16H6zM14 2v4h4"/>',
        'cal': '<path d="M4 5h16v16H4zM4 9h16M8 3v4M16 3v4"/>',
        'user': '<path d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 9a7 7 0 0114 0z"/>',
    }
    p = paths.get(name, '')
    stroke = name in ('pulse', 'cal')
    if stroke:
        return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{p}</svg>')
    return f'<svg viewBox="0 0 24 24" fill="currentColor">{p}</svg>'


def chip(text, cls=''):
    return f'<span class="chip {cls}">{E(str(text))}</span>'


def fhir_tag(t):
    return f'<span class="fhir">{E(t)}</span>'


# ---------- detail tables ----------
def tbl(headers, rows_html, cls=''):
    head = ''.join(f'<th>{E(h)}</th>' for h in headers)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table>'


def conditions_rows(P):
    out = ''
    for r in sorted(P['problems'], key=lambda x: x['status'] != 'Active'):
        active = r['status'] == 'Active'
        out += (f'<tr><td class="strong">{E(r["name"])}</td><td>{E(r["onset"])}</td>'
                f'<td>{E(r["resolved"]) or "&ndash;"}</td>'
                f'<td>{chip(r["status"], "ok" if active else "mut")}</td></tr>')
    return out


def meds_rows(P):
    out = ''
    for m in P['meds']:
        active = not m['stop']
        out += (f'<tr{extra_attr(med_extra(m))}><td class="strong">{E(m["name"])}</td><td>{E(m["start"])}</td>'
                f'<td>{E(m["stop"]) or "&ndash;"}</td>'
                f'<td>{chip("Active" if active else "Completed", "ok" if active else "mut")}</td></tr>')
    return out


def labs_section(P):
    ccd_badge = '<span class="prov ccd" title="C-CDA document">CCD</span>'
    oru_badge = '<span class="prov oru" title="ORU lab feed (HIE)">ORU</span>'
    rows = ''
    if P.get('oru'):
        rows += ('<tr class="grp oru-grp"><td colspan="6">Laboratory Feed &middot; ORU '
                 f'(Health Information Exchange) &mdash; {len(P["oru"])} results</td></tr>')
        for o in sorted(P['oru'], key=lambda x: x['test']):
            tag = (chip('preferred', 'oru') if o['dup'] else chip('new', 'ok'))
            oflag = o.get('flag', '')
            oabn = oflag in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            rows += (f'<tr class="oru-row"{extra_attr(oru_extra(o))}><td>{oru_badge} <span class="strong blue">{E(o["test"])}</span> {tag}</td>'
                     f'<td class="strong {"abnval" if oabn else "blue"}">{E(str(o["value"]))}</td><td>{E(o["unit"])}</td>'
                     f'<td>{E(oflag) or "&ndash;"}</td><td>{E(o.get("range", "")) or "&ndash;"}</td>'
                     f'<td>{E(o["date"])}</td></tr>')
    for p in P['labs']:
        rows += (f'<tr class="grp"><td colspan="6">{E(p["panel"])}'
                 f'<span class="grpdate">{E(p["date"])}</span></td></tr>')
        for c in p['comps']:
            abn = c['flag'] in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            sup = c.get('superseded')
            cls = ' '.join(x for x in [('abn' if abn else ''), ('sup' if sup else '')] if x)
            supnote = chip('superseded by ORU', 'warn') if sup else ''
            rows += (f'<tr class="{cls}"{extra_attr(lab_extra(c))}><td>{ccd_badge} <span>{E(c["test"])}</span> {supnote}</td>'
                     f'<td class="{"abnval" if abn else ""}">{E(c["value"])}</td><td>{E(c["unit"])}</td>'
                     f'<td>{E(c["flag"]) or "&ndash;"}</td><td>{E(c["range"]) or "&ndash;"}</td>'
                     f'<td>{E(c["date"])}</td></tr>')
    legend = ''
    if P.get('oru'):
        legend = (f'<div class="legend">{ccd_badge} C-CDA &nbsp; {oru_badge} ORU feed (HIE) &nbsp; '
                  '<span class="sup-ex">strikethrough</span> = CCD result superseded by a duplicate ORU result</div>')
    return legend + tbl(['Test', 'Result', 'Units', 'Flag', 'Reference Range', 'Date'], rows, 'labs')


def vitals_rows(P):
    return ''.join(f'<tr><td class="strong">{E(v["test"])}</td><td>{E(v["value"])}</td>'
                   f'<td>{E(v["unit"])}</td><td>{E(v["date"])}</td></tr>' for v in P['vitals'])


def imm_rows(P):
    return ''.join(f'<tr><td class="strong">{E(i["name"])}</td><td>{E(i["date"])}</td>'
                   f'<td>{chip("Completed", "ok")}</td></tr>' for i in P['imms'])


def proc_rows(P):
    return ''.join(f'<tr><td class="strong">{E(p["name"])}</td><td>{E(p["date"])}</td></tr>'
                   for p in P['procs'])


def enc_rows(P):
    return ''.join(f'<tr{dextra([("Facility", e.get("facility", "")), ("Attending", e.get("attending", "")), ("PCP", e.get("pcp", "")), ("Discharge disposition", e.get("disposition", "")), ("Reason for visit", e.get("reason", "")), ("Encounter type", e.get("etype", ""))])}>'
                   f'<td class="strong">{E(e["name"])}</td><td>{E(e["start"])}</td>'
                   f'<td>{E(e["stop"]) or "&ndash;"}</td></tr>' for e in P['encs'])


def allergy_block(P):
    if P['allergies']:
        rows = ''.join(f'<tr><td class="strong">{E(a["name"])}</td></tr>' for a in P['allergies'])
        return tbl(['Allergen / Substance'], rows)
    return '<div class="empty ok-empty">No known allergies recorded.</div>'


def demo_block(P):
    rows = [
        ('Full name', f'{P["given"]} {P["family"]}'), ('Date of birth', P['dob']),
        ('Age', f'{P["age"]} years'), ('Administrative sex', P['gender']),
        ('Address', P['addr']), ('Race', P['race']), ('Ethnicity', P['eth']),
        ('Preferred language', P['lang']),
        ('MRN', f'{P["mrn"]}' + (f' ({P["mrn_aa"]})' if P['mrn_aa'] else '')),
        ('Enterprise / MPI id', P['mpiid']), ('Source MPID', P['mpid_tag']),
    ]
    body = ''.join(f'<div class="kv"><span class="k">{E(k)}</span>'
                   f'<span class="v">{E(str(v))}</span></div>' for k, v in rows if v)
    return f'<div class="demo-grid">{body}</div>'


# ---------- summary cards ----------
def card(title, ic, fhir, count, tab, body, accent=''):
    return f"""
    <div class="card {accent}">
      <div class="c-head">
        <span class="c-ic">{icon(ic)}</span>
        <span class="c-title">{E(title)}</span>
        {fhir_tag(fhir)}
        <span class="c-count">{count}</span>
        <a class="c-all" data-go="{tab}">View all &rarr;</a>
      </div>
      <div class="c-body">{body}</div>
    </div>"""


def mini_list(items, empty='No data'):
    if not items:
        return f'<div class="mini-empty">{E(empty)}</div>'
    lis = ''.join(f'<li><span class="dot"></span>{it}</li>' for it in items)
    return f'<ul class="mini">{lis}</ul>'


def summary_cards(P):
    has = P['has']
    # allergies
    al = ([E(a['name']) for a in P['allergies']] if P['allergies']
          else ['<span class="good">No known allergies</span>'])
    allergy_accent = 'danger' if P['allergies'] else 'good'
    allergy_card = card('Allergies', 'alert', 'AllergyIntolerance', has['Allergies'] or '0',
                        'allergies', mini_list(al[:6]), allergy_accent)

    # active problems
    active = [p for p in P['problems'] if p['status'] == 'Active']
    prob = [f'{E(p["name"])} <span class="muted">· {E(p["onset"])}</span>' for p in active[:6]]
    cond_card = card('Active Problems', 'pulse', 'Condition', len(active),
                     'conditions', mini_list(prob, 'No active problems'))

    # meds
    actmeds = [m for m in P['meds'] if not m['stop']]
    show = actmeds if actmeds else P['meds']
    med = [f'{E(m["name"])} <span class="muted">· from {E(m["start"])}</span>' for m in show[:6]]
    med_card = card('Medications', 'pill', 'MedicationRequest', has['Medications'] or '0',
                    'medications', mini_list(med, 'No medications'))

    # recent labs: ORU preferred + latest CCD panel
    lab_items = []
    for o in P.get('oru', [])[:4]:
        lab_items.append(f'<span class="prov oru">ORU</span> {E(o["test"])}: '
                         f'<b class="blue">{E(str(o["value"]))} {E(o["unit"])}</b>')
    if P['labs']:
        last = P['labs'][-1]
        for c in last['comps'][:4]:
            cls = 'strike' if c.get('superseded') else ''
            lab_items.append(f'<span class="prov ccd">CCD</span> '
                             f'<span class="{cls}">{E(c["test"])}: {E(c["value"])} {E(c["unit"])}</span>')
    lab_card = card('Recent Lab Results', 'lab', 'Observation', has['Lab Results'] or '0',
                    'labs', mini_list(lab_items, 'No lab results'))

    # vitals (latest few)
    vit = [f'{E(v["test"])}: <b>{E(v["value"])} {E(v["unit"])}</b> '
           f'<span class="muted">· {E(v["date"])}</span>' for v in P['vitals'][:6]]
    vit_card = card('Vital Signs', 'heart', 'Observation', has['Vital Signs'] or '0',
                    'vitals', mini_list(vit, 'No vitals'))

    # immunizations
    im = [f'{E(i["name"])} <span class="muted">· {E(i["date"])}</span>' for i in P['imms'][:6]]
    im_card = card('Immunizations', 'shield', 'Immunization', has['Immunizations'] or '0',
                   'immunizations', mini_list(im, 'No immunizations'))

    return f'<div class="cards">{allergy_card}{cond_card}{med_card}{lab_card}{vit_card}{im_card}</div>'


# ---------- tabs ----------
TABS = [
    ('summary', 'Summary'), ('conditions', 'Conditions'), ('medications', 'Medications'),
    ('labs', 'Lab Results'), ('vitals', 'Vitals'), ('immunizations', 'Immunizations'),
    ('procedures', 'Procedures'), ('encounters', 'Encounters'), ('demographics', 'Demographics'),
]


def section_panel(title, fhir, inner):
    return (f'<div class="panel"><div class="p-head"><h3>{E(title)}</h3>{fhir_tag(fhir)}</div>'
            f'<div class="p-body">{inner}</div></div>')


def render_patient(P, idx):
    has = P['has']
    tabnav = ''.join(
        f'<button class="tab{" active" if t == "summary" else ""}" data-tab="{t}">{E(label)}</button>'
        for t, label in TABS)

    panes = {
        'summary': summary_cards(P),
        'conditions': section_panel('Conditions', 'Condition',
                                    tbl(['Condition', 'Onset', 'Resolved', 'Status'], conditions_rows(P))),
        'medications': section_panel('Medications', 'MedicationRequest',
                                     tbl(['Medication', 'Start', 'Stop', 'Status'], meds_rows(P))),
        'labs': section_panel('Lab Results', 'Observation (laboratory)', labs_section(P)),
        'vitals': section_panel('Vital Signs', 'Observation (vital-signs)',
                                tbl(['Vital', 'Value', 'Units', 'Date'], vitals_rows(P))),
        'immunizations': section_panel('Immunizations', 'Immunization',
                                       tbl(['Immunization', 'Date', 'Status'], imm_rows(P))),
        'procedures': section_panel('Procedures', 'Procedure',
                                    tbl(['Procedure', 'Date'], proc_rows(P))),
        'encounters': section_panel('Encounters', 'Encounter',
                                    tbl(['Encounter', 'Start', 'End'], enc_rows(P))),
        'demographics': section_panel('Demographics', 'Patient', demo_block(P)),
        'allergies': section_panel('Allergies', 'AllergyIntolerance', allergy_block(P)),
    }
    panes_html = ''.join(
        f'<div class="tabpane{" active" if t == "summary" else ""}" data-pane="{t}">{panes[t]}</div>'
        for t, _ in TABS)
    panes_html += f'<div class="tabpane" data-pane="allergies">{panes["allergies"]}</div>'

    initials = (P['given'][:1] + P['family'][:1]).upper()
    sex = P['gender']
    allergy_flag = (chip(f'{has["Allergies"]} allergies', 'danger') if has['Allergies']
                    else chip('No known allergies', 'good'))
    style = '' if idx == 0 else ' style="display:none"'
    _aa = P.get('mrn_aa') or ''
    _qe = _aa.split('|')[0] if _aa else ''
    _src = _aa.split('|')[1] if '|' in _aa else ''
    _mrns = ';'.join(f"{m['qe']}|{m['source']}:{m['mrn']}" for m in P.get('mrn_list', []))
    return f"""
    <div class="patient" data-idx="{idx}" data-first="{E(P['given'])}" data-last="{E(P['family'])}" data-dob="{E(P['dob'])}" data-qe="{E(_qe)}" data-source="{E(_src)}" data-mrn="{E(P['mrn'])}" data-mrns="{E(_mrns)}"{style}>
      <div class="pt-banner">
        <div class="avatar">{E(initials)}</div>
        <div class="pt-id">
          <div class="pt-name">{E(P['given'])} {E(P['family'])}</div>
          <div class="pt-meta">{E(sex)} &middot; {P['age']} yrs &middot; DOB {E(P['dob'])}
            &middot; MRN {E(P['mrn'] or 'n/a')}</div>
        </div>
        <div class="pt-flags">
          {allergy_flag}
          {chip(f'{has["Conditions"]} problems')}
          {chip(f'{has["Medications"]} meds')}
          {chip(f'{has["Lab Results"]} labs')}
        </div>
        <div class="pt-mpi"><span class="k">MPI</span><span class="v">{E(P['mpiid'][:18])}&hellip;</span></div>
      </div>
      <div class="tabbar">{tabnav}</div>
      <div class="panes">{panes_html}</div>
    </div>"""


# ---------- build ----------
TRN_DIR = os.environ.get('CHART_TRN_DIR', '')
files = sorted(glob.glob(os.path.join(CCD_DIR, '*.xml')))
if TRN_DIR:
    files += sorted(glob.glob(os.path.join(TRN_DIR, '*.xml')))
patients = [parse_ccd(f) for f in files]
for P in patients:
    P['oru'] = []
load_oru(patients)                                   # FHIR Observation ndjson (if any)
if ORU_HL7_DIR:
    load_oru_hl7(patients, os.path.join(ORU_HL7_DIR, '*.hl7'))   # genuine HL7 ORU
patients = merge_by_person(patients)                 # one virtual record per person

options = ''
for i, P in enumerate(patients):
    options += (f'<option value="{i}">{E(P["given"])} {E(P["family"])} '
                f'&nbsp;({E(P["gender"])} {P["age"]}y)</option>')

blocks = '\n'.join(render_patient(P, i) for i, P in enumerate(patients))
now_str = datetime.now().strftime('%b %d, %Y %I:%M %p')

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(TITLE)} &mdash; {E(VIEW_QE)}</title>
<style>
  :root {{
    --brand:#0ea5a4; --brand-d:#0b7c7b; --brand-2:#0e7490; --accent:#f97316;
    --bg:#eef2f6; --card:#ffffff; --ink:#1f2a37; --muted:#6b7280; --line:#e5e9ee;
    --blue:#1d4ed8; --danger:#dc2626; --ok:#16a34a; --warn:#b45309;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif; font-size:14px; }}
  h3 {{ margin:0; font-size:15px; }}
  .blue {{ color:var(--blue); }} .good {{ color:var(--ok); }} .muted {{ color:var(--muted); }}
  .strong {{ font-weight:600; }}

  /* header */
  .appbar {{ background:linear-gradient(90deg,var(--brand-2),var(--brand));
    color:#fff; padding:12px 22px; display:flex; align-items:center; gap:16px;
    box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .brand {{ display:flex; align-items:center; gap:11px; }}
  .brand .mark {{ width:34px; height:34px; border-radius:9px; background:rgba(255,255,255,.18);
    display:flex; align-items:center; justify-content:center; }}
  .brand .mark svg {{ width:20px; height:20px; color:#fff; }}
  .brand .name {{ font-size:16px; font-weight:700; letter-spacing:.2px; line-height:1.1; }}
  .brand .sub {{ font-size:11px; opacity:.85; }}
  .appbar .spacer {{ flex:1; }}
  .conn {{ font-size:11px; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28);
    padding:5px 10px; border-radius:999px; display:flex; align-items:center; gap:7px; }}
  .conn .live {{ width:7px; height:7px; border-radius:50%; background:#34d399;
    box-shadow:0 0 0 3px rgba(52,211,153,.3); }}
  .picker {{ display:flex; align-items:center; gap:8px; }}
  .picker label {{ font-size:11px; opacity:.85; text-transform:uppercase; letter-spacing:.6px; }}
  .picker select {{ font-size:13px; padding:7px 12px; border-radius:8px; border:none;
    min-width:280px; color:var(--ink); background:#fff; }}

  .wrap {{ max-width:1180px; margin:20px auto; padding:0 18px 60px; }}

  /* patient banner */
  .pt-banner {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:16px 18px; display:flex; align-items:center; gap:16px;
    box-shadow:0 1px 3px rgba(16,24,40,.06); }}
  .avatar {{ width:52px; height:52px; border-radius:50%; flex:none; color:#fff; font-weight:700;
    font-size:18px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,var(--brand),var(--brand-2)); }}
  .pt-id {{ min-width:230px; }}
  .pt-name {{ font-size:20px; font-weight:700; }}
  .pt-meta {{ color:var(--muted); font-size:12.5px; margin-top:2px; }}
  .pt-flags {{ display:flex; gap:7px; flex-wrap:wrap; flex:1; }}
  .pt-mpi {{ text-align:right; font-size:11px; color:var(--muted); }}
  .pt-mpi .k {{ display:block; text-transform:uppercase; letter-spacing:.5px; font-size:10px; }}
  .pt-mpi .v {{ font-family:ui-monospace,Menlo,Consolas,monospace; color:var(--ink); }}

  .chip {{ display:inline-flex; align-items:center; font-size:11.5px; font-weight:600;
    padding:3px 10px; border-radius:999px; background:#eef2f6; color:#475467; border:1px solid var(--line); }}
  .chip.ok {{ background:#ecfdf3; color:#067647; border-color:#abefc6; }}
  .chip.danger {{ background:#fef3f2; color:#b42318; border-color:#fecdca; }}
  .chip.good {{ background:#ecfdf3; color:#067647; border-color:#abefc6; }}
  .chip.mut {{ background:#f2f4f7; color:#667085; }}
  .chip.oru {{ background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe; }}
  .chip.warn {{ background:#fffaeb; color:var(--warn); border-color:#fedf89; }}

  /* tabs */
  .tabbar {{ display:flex; gap:4px; margin:16px 0 14px; flex-wrap:wrap;
    border-bottom:1px solid var(--line); }}
  .tab {{ background:none; border:none; padding:10px 14px; font-size:13.5px; cursor:pointer;
    color:var(--muted); border-bottom:2.5px solid transparent; font-weight:600;
    font-family:inherit; }}
  .tab:hover {{ color:var(--ink); }}
  .tab.active {{ color:var(--brand-d); border-bottom-color:var(--brand); }}

  .tabpane {{ display:none; }}
  .tabpane.active {{ display:block; }}

  /* cards grid */
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:16px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    box-shadow:0 1px 3px rgba(16,24,40,.06); overflow:hidden; }}
  .card .c-head {{ display:flex; align-items:center; gap:9px; padding:13px 15px;
    border-bottom:1px solid var(--line); }}
  .c-ic {{ width:30px; height:30px; border-radius:8px; background:#e6f6f5; color:var(--brand-d);
    display:flex; align-items:center; justify-content:center; flex:none; }}
  .c-ic svg {{ width:17px; height:17px; }}
  .card.danger .c-ic {{ background:#fef3f2; color:#d92d20; }}
  .card.good .c-ic {{ background:#ecfdf3; color:#067647; }}
  .c-title {{ font-weight:700; font-size:14px; }}
  .fhir {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:10.5px; color:#8a94a6;
    background:#f5f7fa; border:1px solid var(--line); padding:1px 6px; border-radius:5px; }}
  .c-count {{ margin-left:auto; font-weight:700; color:var(--brand-d); background:#e6f6f5;
    min-width:24px; text-align:center; border-radius:999px; padding:1px 8px; font-size:12px; }}
  .c-all {{ font-size:12px; color:var(--brand-d); cursor:pointer; font-weight:600; margin-left:10px; white-space:nowrap; }}
  .c-all:hover {{ text-decoration:underline; }}
  .c-body {{ padding:12px 15px; }}
  ul.mini {{ list-style:none; margin:0; padding:0; }}
  ul.mini li {{ padding:6px 0; border-bottom:1px dashed #eef1f4; font-size:13px; display:flex;
    align-items:flex-start; gap:8px; }}
  ul.mini li:last-child {{ border-bottom:none; }}
  ul.mini .dot {{ width:6px; height:6px; border-radius:50%; background:var(--brand); margin-top:6px; flex:none; }}
  .mini-empty {{ color:var(--muted); font-style:italic; padding:6px 0; }}

  /* panels & tables */
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    box-shadow:0 1px 3px rgba(16,24,40,.06); overflow:hidden; }}
  .p-head {{ display:flex; align-items:center; gap:10px; padding:14px 16px; border-bottom:1px solid var(--line); }}
  .p-body {{ padding:4px 2px; overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; }}
  thead th {{ text-align:left; font-size:11px; letter-spacing:.4px; text-transform:uppercase;
    color:#8a94a6; font-weight:700; padding:10px 16px; border-bottom:1px solid var(--line); white-space:nowrap; }}
  tbody td {{ padding:10px 16px; border-bottom:1px solid #f1f3f6; vertical-align:top; font-size:13px; }}
  tbody tr:hover {{ background:#fafcfc; }}
  .abnval {{ color:var(--danger); font-weight:700; }}

  .labs .grp td {{ background:#f6f8fa; font-weight:700; color:#344054; font-size:12.5px; }}
  .labs .grp .grpdate {{ float:right; color:var(--muted); font-weight:500; }}
  .labs .oru-grp td {{ background:#eff6ff; color:#1d4ed8; border-top:2px solid var(--blue); }}
  tr.oru-row td {{ background:#f7faff; }}
  tr.sup td {{ background:#fcfcfd; }}
  tr.sup td:nth-child(1) span:not(.prov):not(.chip), tr.sup td:nth-child(2) {{
    text-decoration:line-through; color:#98a2b3; }}
  .strike {{ text-decoration:line-through; color:#98a2b3; }}

  .prov {{ display:inline-block; font-size:9.5px; font-weight:800; letter-spacing:.4px;
    padding:1px 5px; border-radius:5px; margin-right:6px; vertical-align:middle; }}
  .prov.ccd {{ background:#f2f4f7; color:#667085; border:1px solid #e4e7ec; }}
  .prov.oru {{ background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; }}

  .legend {{ font-size:12px; color:var(--muted); padding:10px 16px; background:#fafbfc;
    border-bottom:1px solid var(--line); }}
  .legend .sup-ex {{ text-decoration:line-through; color:#98a2b3; }}
  .empty {{ padding:16px; color:var(--muted); font-style:italic; }}
  .ok-empty {{ color:#067647; font-style:normal; font-weight:600; }}

  .demo-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:2px 24px; padding:14px 16px; }}
  .kv {{ display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid #f1f3f6; }}
  .kv .k {{ color:var(--muted); }}
  .kv .v {{ font-weight:600; text-align:right; }}

  .foot {{ color:var(--muted); font-size:11.5px; text-align:center; margin-top:22px; }}
</style>
</head>
<body data-view-qe="{E(VIEW_QE)}">

  <div class="appbar">
    <div class="brand">
      <div class="mark">{icon('pulse')}</div>
      <div>
        <div class="name">{E(TITLE)}</div>
        <div class="sub">{E(VIEW_QE)} &middot; demonstration</div>
      </div>
    </div>
    <div class="spacer"></div>
    <div class="conn"><span class="live"></span> FHIR R4 &middot; SHIN-NY connected</div>
    <div class="picker">
      <label for="psel">Patient</label>
      <select id="psel">{options}</select>
    </div>
  </div>

  <div class="wrap">
    {blocks}
    <div class="foot">
      Rendered {E(now_str)} from C-CDA + ORU (FHIR R4) synthetic data &middot; demonstration only.
      FHIR&reg; is a registered trademark of HL7. Not affiliated with CRISP or Hixny.
    </div>
  </div>

<script>
(function() {{
  function activateTab(pat, tab) {{
    pat.querySelectorAll('.tab').forEach(function(b) {{ b.classList.toggle('active', b.dataset.tab === tab); }});
    pat.querySelectorAll('.tabpane').forEach(function(p) {{ p.classList.toggle('active', p.dataset.pane === tab); }});
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }}
  document.querySelectorAll('.patient').forEach(function(pat) {{
    pat.querySelectorAll('.tab').forEach(function(b) {{
      b.addEventListener('click', function() {{ activateTab(pat, b.dataset.tab); }});
    }});
    pat.querySelectorAll('.c-all').forEach(function(a) {{
      a.addEventListener('click', function() {{ activateTab(pat, a.dataset.go); }});
    }});
  }});
  var sel = document.getElementById('psel');
  sel.addEventListener('change', function() {{
    document.querySelectorAll('.patient').forEach(function(pat) {{
      pat.style.display = (pat.dataset.idx === sel.value) ? '' : 'none';
    }});
    window.scrollTo({{ top: 0 }});
  }});
}})();
</script>
</body>
</html>"""

HTML = inject_bug(HTML)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Wrote {OUT} with {len(patients)} patients")
