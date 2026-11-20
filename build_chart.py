"""
Parse Synthea C-CDA files (in ./ccds) and render a multi-patient chart summary
as a single HTML page styled after the HEALTHeLINK Fusion clinical viewer.
A dropdown at the top switches between patients; the Chartbook shows one
section at a time.
"""
import os
import glob
import json
import xml.etree.ElementTree as ET
from datetime import datetime, date
import html

from ccda_parse import load_oru_hl7   # shared HL7 ORU loader + dedup rules
from bug_widget import inject as inject_bug
from ccda_parse import med_extra, lab_extra, oru_extra, extra_attr

V3 = 'urn:hl7-org:v3'
ns = {'v3': V3}
CCD_DIR = os.environ.get('CHART_CCD_DIR', 'ccds')
OUT = os.environ.get('CHART_OUT', 'patient_chart.html')
ORU_HL7_DIR = os.environ.get('CHART_ORU_HL7', '')
VIEW_QE = os.environ.get('CHART_QE', '')            # the QE whose portal this view represents
E = html.escape


def fmt_date(v):
    if not v:
        return ''
    v = v.strip()
    for n in (14, 12, 8):
        if len(v) >= n:
            try:
                fmt = {14: '%Y%m%d%H%M%S', 12: '%Y%m%d%H%M', 8: '%Y%m%d'}[n]
                return datetime.strptime(v[:n], fmt).strftime('%m/%d/%Y')
            except ValueError:
                continue
    return v


def parse_ccd(path):
    tree = ET.parse(path)
    root = tree.getroot()

    id_text = {}
    for el in root.iter():
        idv = el.get('ID')
        if idv:
            id_text[idv] = ' '.join(''.join(el.itertext()).split())

    def deref(el):
        if el is None:
            return ''
        ref = el.find('v3:reference', ns)
        if ref is not None:
            val = (ref.get('value') or '').lstrip('#')
            return id_text.get(val, '')
        return ' '.join(''.join(el.itertext()).split())

    def code_name(code_el):
        if code_el is None:
            return ''
        if code_el.get('displayName'):
            return code_el.get('displayName')
        tr = code_el.find('v3:translation', ns)
        if tr is not None and tr.get('displayName'):
            return tr.get('displayName')
        txt = deref(code_el.find('v3:originalText', ns))
        if txt:
            return txt
        return code_el.get('code', '') or ''

    def eff_low_high(parent):
        et_el = parent.find('v3:effectiveTime', ns)
        low = high = single = ''
        if et_el is not None:
            if et_el.get('value'):
                single = et_el.get('value')
            lo = et_el.find('v3:low', ns)
            hi = et_el.find('v3:high', ns)
            if lo is not None:
                low = lo.get('value', '')
            if hi is not None:
                high = hi.get('value', '')
        return low or single, high

    SEC = {}
    for s in root.findall('.//v3:section', ns):
        t = s.find('v3:title', ns)
        if t is not None and t.text:
            SEC[t.text.strip()] = s

    # ---- demographics ----
    pr = root.find('.//v3:recordTarget/v3:patientRole', ns)
    pat = pr.find('v3:patient', ns)
    nm = pat.find('v3:name', ns)
    given = ' '.join((g.text or '') for g in nm.findall('v3:given', ns)).strip()
    family = (nm.findtext('v3:family', default='', namespaces=ns) or '').strip()
    gender = pat.find('v3:administrativeGenderCode', ns).get('code', '')
    dob_raw = pat.find('v3:birthTime', ns).get('value', '')
    dob = fmt_date(dob_raw)
    age = ''
    if len(dob_raw) >= 8:
        b = datetime.strptime(dob_raw[:8], '%Y%m%d').date()
        t = date.today()
        age = t.year - b.year - ((t.month, t.day) < (b.month, b.day))

    addr_el = pr.find('v3:addr', ns)
    addr = ''
    if addr_el is not None:
        p = [addr_el.findtext('v3:streetAddressLine', default='', namespaces=ns),
             addr_el.findtext('v3:city', default='', namespaces=ns),
             addr_el.findtext('v3:state', default='', namespaces=ns),
             addr_el.findtext('v3:postalCode', default='', namespaces=ns)]
        p = [x for x in p if x]
        if len(p) >= 3:
            addr = f"{p[0]}, {p[1]}, {p[2]} {p[3] if len(p) > 3 else ''}".strip()
        else:
            addr = ', '.join(p)

    mrn = mrn_aa = mpiid = ''
    for idel in pr.findall('v3:id', ns):
        aa = idel.get('assigningAuthorityName', '')
        idroot = idel.get('root', '')
        if 'synthea' in aa.lower():
            mpiid = idel.get('extension', '')
            continue
        if idroot.endswith('.eid') or idroot.endswith('.mpid'):
            continue
        if aa and not mrn:
            mrn, mrn_aa = idel.get('extension', ''), aa
    if not mpiid:
        mpiid = pr.findall('v3:id', ns)[0].get('root', '')

    race = (pat.find('v3:raceCode', ns).get('displayName', '')
            if pat.find('v3:raceCode', ns) is not None else '')
    eth = (pat.find('v3:ethnicGroupCode', ns).get('displayName', '')
           if pat.find('v3:ethnicGroupCode', ns) is not None else '')
    lc = pat.find('.//v3:languageCommunication/v3:languageCode', ns)
    lang = lc.get('code', '') if lc is not None else ''

    doc_time = root.find('v3:effectiveTime', ns)
    doc_date = fmt_date(doc_time.get('value', '')) if doc_time is not None else ''

    # MPID tag from filename (e.g. BRONX-MPID-000003)
    base = os.path.basename(path)
    mpid_tag = base.split('_')[0] if '_' in base else base

    # ---- sections ----
    problems = []
    if 'Problems' in SEC:
        for act in SEC['Problems'].findall('.//v3:entry/v3:act', ns):
            obs = act.find('.//v3:observation', ns)
            if obs is None:
                continue
            name = code_name(obs.find('v3:value', ns)) or deref(obs.find('v3:text', ns))
            low, high = eff_low_high(obs)
            if not low:
                low, high = eff_low_high(act)
            problems.append({'name': name, 'onset': fmt_date(low),
                             'resolved': fmt_date(high),
                             'status': 'Resolved' if high else 'Active'})

    meds = []
    if 'Medications' in SEC:
        for sa in SEC['Medications'].findall('.//v3:entry/v3:substanceAdministration', ns):
            mat = sa.find('.//v3:manufacturedMaterial', ns)
            name = ''
            if mat is not None:
                name = code_name(mat.find('v3:code', ns)) or mat.findtext('v3:name', default='', namespaces=ns)
            low, high = eff_low_high(sa)
            meds.append({'name': name, 'start': fmt_date(low), 'stop': fmt_date(high)})

    labs = []
    if 'Diagnostic Results' in SEC:
        for org in SEC['Diagnostic Results'].findall('.//v3:entry/v3:organizer', ns):
            pname = code_name(org.find('v3:code', ns))
            plow, _ = eff_low_high(org)
            comps = []
            for obs in org.findall('v3:component/v3:observation', ns):
                vel = obs.find('v3:value', ns)
                value = unit = ''
                if vel is not None:
                    value = vel.get('value', '') or ''.join(vel.itertext()).strip()
                    unit = vel.get('unit', '')
                interp = obs.find('v3:interpretationCode', ns)
                flag = ''
                if interp is not None:
                    flag = {'N': 'Normal', 'L': 'Low', 'H': 'High', 'A': 'Abnormal',
                            'HH': 'Critical High', 'LL': 'Critical Low'}.get(
                        interp.get('code', ''), interp.get('code', ''))
                rr = ''
                rr_el = obs.find('.//v3:referenceRange//v3:text', ns)
                if rr_el is not None:
                    rr = ' '.join(''.join(rr_el.itertext()).split())
                olow, _ = eff_low_high(obs)
                ccode = obs.find('v3:code', ns)
                comps.append({'test': code_name(ccode), 'value': value,
                              'unit': unit, 'flag': flag, 'range': rr,
                              'date': fmt_date(olow or plow),
                              'loinc': ccode.get('code', '') if ccode is not None else '',
                              'source': 'CCD', 'superseded': False})
            labs.append({'panel': pname, 'date': fmt_date(plow), 'comps': comps})

    imms = []
    if 'Immunizations' in SEC:
        for sa in SEC['Immunizations'].findall('.//v3:entry/v3:substanceAdministration', ns):
            mat = sa.find('.//v3:manufacturedMaterial', ns)
            name = ''
            if mat is not None:
                name = code_name(mat.find('v3:code', ns)) or mat.findtext('v3:name', default='', namespaces=ns)
            low, _ = eff_low_high(sa)
            imms.append({'name': name, 'date': fmt_date(low)})
        imms.sort(key=lambda r: r['date'], reverse=True)

    vitals = []
    if 'Vital Signs' in SEC:
        for org in SEC['Vital Signs'].findall('.//v3:entry/v3:organizer', ns):
            olow, _ = eff_low_high(org)
            for obs in org.findall('v3:component/v3:observation', ns):
                vel = obs.find('v3:value', ns)
                value = unit = ''
                if vel is not None:
                    value = vel.get('value', '') or ''.join(vel.itertext()).strip()
                    unit = vel.get('unit', '')
                vlow, _ = eff_low_high(obs)
                vitals.append({'test': code_name(obs.find('v3:code', ns)), 'value': value,
                               'unit': unit, 'date': fmt_date(vlow or olow)})

    procs = []
    procsec = SEC.get('Surgeries')
    if procsec is None:
        procsec = SEC.get('Procedures')
    if procsec is not None:
        for proc in procsec.findall('.//v3:entry/v3:procedure', ns):
            name = code_name(proc.find('v3:code', ns)) or deref(proc.find('v3:text', ns))
            low, _ = eff_low_high(proc)
            procs.append({'name': name, 'date': fmt_date(low)})
        procs.sort(key=lambda r: r['date'], reverse=True)

    encs = []
    if 'Encounters' in SEC:
        for enc in SEC['Encounters'].findall('.//v3:entry/v3:encounter', ns):
            name = code_name(enc.find('v3:code', ns)) or deref(enc.find('v3:text', ns))
            low, high = eff_low_high(enc)
            encs.append({'name': name, 'start': fmt_date(low), 'stop': fmt_date(high)})
        encs.sort(key=lambda r: r['start'], reverse=True)

    allergies = []
    if 'Allergies' in SEC:
        for obs in SEC['Allergies'].findall('.//v3:entry//v3:observation', ns):
            name = code_name(obs.find('v3:value', ns))
            if name:
                allergies.append({'name': name})

    has = {
        'Conditions': len(problems), 'Allergies': len(allergies), 'Medications': len(meds),
        'Immunizations': len(imms), 'Vital Signs': len(vitals),
        'Lab Results': sum(len(p['comps']) for p in labs), 'Procedures': len(procs),
        'Encounters': len(encs),
    }

    return dict(given=given, family=family, gender=gender, dob=dob, age=age, addr=addr,
                mrn=mrn, mrn_aa=mrn_aa, mpiid=mpiid, race=race, eth=eth, lang=lang,
                doc_date=doc_date, mpid_tag=mpid_tag, problems=problems, meds=meds,
                labs=labs, imms=imms, vitals=vitals, procs=procs, encs=encs,
                allergies=allergies, has=has)


# ---------- HTML rendering ----------
def panel(title, body, count=None):
    cnt = f' <span class="cnt">{count}</span>' if count is not None else ''
    return f"""
    <section class="card">
      <div class="card-accent"></div>
      <div class="card-head">
        <span class="chev">&#9662;</span>
        <span class="card-title">{E(title)} Table{cnt}</span>
        <span class="card-tools">
          <span class="search"><input placeholder="Search" disabled><span class="mag">&#128269;</span></span>
          <span class="filter" title="Sort &amp; filter">&#9776;</span>
        </span>
      </div>
      <div class="card-body">{body}</div>
    </section>"""


def th(cols):
    return ''.join(f'<th>{E(c)} <span class="sort">&#8645;</span></th>' for c in cols)


def render_tables(P):
    # Conditions
    rows = ''
    for r in sorted(P['problems'], key=lambda x: x['status'] != 'Active'):
        stcls = 'active' if r['status'] == 'Active' else 'resolved'
        rows += (f'<tr><td class="lnk">{E(r["name"])}</td><td>{E(r["onset"])}</td>'
                 f'<td>{E(r["resolved"]) or "&mdash;"}</td>'
                 f'<td><span class="status {stcls}">{E(r["status"])}</span></td></tr>')
    conditions_tbl = f'<table><thead><tr>{th(["Condition", "Onset Date", "Resolved", "Status"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Allergies
    if P['allergies']:
        rows = ''.join(f'<tr><td class="lnk">{E(a["name"])}</td></tr>' for a in P['allergies'])
        allergies_tbl = f'<table><thead><tr>{th(["Allergen"])}</tr></thead><tbody>{rows}</tbody></table>'
    else:
        allergies_tbl = '<div class="empty">No known allergies recorded.</div>'

    # Medications
    rows = ''
    for m in P['meds']:
        active = not m['stop']
        rows += (f'<tr{extra_attr(med_extra(m))}><td class="lnk">{E(m["name"])}</td><td>{E(m["start"])}</td>'
                 f'<td>{E(m["stop"]) or "&mdash;"}</td>'
                 f'<td><span class="status {"active" if active else "resolved"}">'
                 f'{"Active" if active else "Completed"}</span></td></tr>')
    meds_tbl = f'<table><thead><tr>{th(["Medication", "Start Date", "Stop Date", "Status"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Labs
    ccd_badge = '<span class="src ccd" title="Source: C-CDA document">&#128196; CCD</span>'
    oru_badge = '<span class="src oru" title="Source: ORU lab feed (Health Information Exchange)">&#128300; ORU</span>'
    rows = ''

    # Prominent ORU feed group first
    if P.get('oru'):
        rows += (f'<tr class="grouphdr oru-hdr"><td colspan="6">ORU &ndash; Laboratory Feed '
                 f'(Health Information Exchange)<span class="gdate">{len(P["oru"])} results</span></td></tr>')
        for o in sorted(P['oru'], key=lambda x: x['test']):
            note = ('<span class="dupnote">preferred &middot; duplicate of CCD</span>'
                    if o['dup'] else '<span class="newnote">new result</span>')
            oflag = o.get('flag', '')
            oabn = oflag in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            rows += (f'<tr class="oru-row"{extra_attr(oru_extra(o))}>'
                     f'<td class="flagcell">{oru_badge} <span class="lnk strong">{E(o["test"])}</span> {note}</td>'
                     f'<td class="strong {"abnval" if oabn else ""}">{E(str(o["value"]))}</td>'
                     f'<td>{E(o["unit"])}</td><td>{E(oflag) or "&mdash;"}</td>'
                     f'<td>{E(o.get("range", "")) or "&mdash;"}</td><td>{E(o["date"])}</td></tr>')

    # CCD panels
    for p in P['labs']:
        rows += (f'<tr class="grouphdr"><td colspan="6">{E(p["panel"])}'
                 f'<span class="gdate">{E(p["date"])}</span></td></tr>')
        for c in p['comps']:
            abn = c['flag'] in ('Low', 'High', 'Abnormal', 'Critical High', 'Critical Low')
            sup = c.get('superseded')
            cls = ' '.join(x for x in [('abn' if abn else ''), ('superseded' if sup else '')] if x)
            supnote = '<span class="supnote">superseded by ORU</span>' if sup else ''
            rows += (f'<tr class="{cls}"{extra_attr(lab_extra(c))}>'
                     f'<td class="flagcell">{"<span class=bar></span>" if abn else ""}'
                     f'{ccd_badge} <span class="lnk">{E(c["test"])}</span> {supnote}</td>'
                     f'<td class="{"abnval" if abn else ""}">{E(c["value"])}</td>'
                     f'<td>{E(c["unit"])}</td><td>{E(c["flag"]) or "&mdash;"}</td>'
                     f'<td>{E(c["range"]) or "&mdash;"}</td><td>{E(c["date"])}</td></tr>')

    legend = ('<div class="lab-legend">'
              f'{ccd_badge} C-CDA document &nbsp;&nbsp; {oru_badge} ORU lab feed (HIE) '
              '&nbsp;&nbsp; <span class="superseded"><span class="lnk">strikethrough</span></span> = '
              'CCD result superseded by a duplicate ORU result</div>') if P.get('oru') else ''
    labs_tbl = legend + f'<table class="labs"><thead><tr>{th(["Lab Test", "Result", "Units", "Flag", "Reference Range", "Collection Date"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Vitals
    rows = ''.join(f'<tr><td class="lnk">{E(v["test"])}</td><td>{E(v["value"])}</td>'
                   f'<td>{E(v["unit"])}</td><td>{E(v["date"])}</td></tr>' for v in P['vitals'])
    vitals_tbl = f'<table><thead><tr>{th(["Vital", "Value", "Units", "Date"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Immunizations
    rows = ''.join(f'<tr><td class="lnk">{E(i["name"])}</td><td>{E(i["date"])}</td>'
                   f'<td><span class="status active">Completed</span></td></tr>' for i in P['imms'])
    imm_tbl = f'<table><thead><tr>{th(["Immunization", "Date Administered", "Status"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Procedures
    rows = ''.join(f'<tr><td class="lnk">{E(p["name"])}</td><td>{E(p["date"])}</td></tr>' for p in P['procs'])
    proc_tbl = f'<table><thead><tr>{th(["Procedure", "Date"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Encounters
    def _ex(e):
        p = [[k, v] for k, v in (
            ('Facility', e.get('facility', '')), ('Attending', e.get('attending', '')),
            ('PCP', e.get('pcp', '')), ('Discharge disposition', e.get('disposition', '')),
            ('Reason for visit', e.get('reason', '')), ('Encounter type', e.get('etype', ''))) if v]
        return f' data-extra="{E(json.dumps(p))}"' if p else ''
    rows = ''.join(f'<tr{_ex(e)}><td class="lnk">{E(e["name"])}</td><td>{E(e["start"])}</td>'
                   f'<td>{E(e["stop"]) or "&mdash;"}</td></tr>' for e in P['encs'])
    enc_tbl = f'<table><thead><tr>{th(["Encounter", "Start Date", "End Date"])}</tr></thead><tbody>{rows}</tbody></table>'

    # Demographics
    demo_rows = [
        ('Name', f'{P["family"].upper()}, {P["given"]}'),
        ('Date of Birth', P['dob']), ('Age', f'{P["age"]}y'), ('Gender', P['gender']),
        ('Address', P['addr']), ('Race', P['race']), ('Ethnicity', P['eth']),
        ('Language', P['lang']),
        ('Medical Record #', f'{P["mrn"]}' + (f'  ({P["mrn_aa"]})' if P['mrn_aa'] else '')),
        ('MPIID', P['mpiid']),
    ]
    demo_tbl = '<table class="demo">' + ''.join(
        f'<tr><th>{E(k)}</th><td>{E(str(v))}</td></tr>' for k, v in demo_rows if v) + '</table>'

    return dict(conditions=conditions_tbl, allergies=allergies_tbl, medications=meds_tbl,
                labs=labs_tbl, vitals=vitals_tbl, imm=imm_tbl, proc=proc_tbl,
                enc=enc_tbl, demo=demo_tbl)


def render_patient(P, idx):
    T = render_tables(P)
    has = P['has']

    nav_items = [
        ('Clinical Summary', True, True), ('Conditions', has['Conditions'] > 0, False),
        ('Allergies', True, False), ('Medications', has['Medications'] > 0, False),
        ('Documents', False, False), ('Immunizations', has['Immunizations'] > 0, False),
        ('Vital Signs', has['Vital Signs'] > 0, False), ('Lab Results', has['Lab Results'] > 0, False),
        ('Diagnostic Studies', False, False), ('Procedures', has['Procedures'] > 0, False),
        ('Histories', True, False), ('Encounters', has['Encounters'] > 0, False),
        ('Appointments', False, False), ('Care Team', False, False), ('Cohorts', False, False),
        ('Claims', False, False), ('Demographics', True, False), ('Insurance', False, False),
        ('Reports', False, False),
    ]
    label_target = {
        'Clinical Summary': 'summary', 'Conditions': 'conditions', 'Allergies': 'allergies',
        'Medications': 'medications', 'Immunizations': 'immunizations', 'Vital Signs': 'vital-signs',
        'Lab Results': 'lab-results', 'Procedures': 'procedures', 'Encounters': 'encounters',
        'Demographics': 'demographics',
    }
    nav_html = ''
    for label, data, sel in nav_items:
        cls = 'nav-item' + (' sel' if sel else '') + (' hasdata' if data else '')
        tgt = label_target.get(label, '')
        if tgt:
            nav_html += f'<a class="{cls}" data-target="{tgt}">{E(label)}</a>'
        else:
            nav_html += f'<a class="{cls} disabled">{E(label)}</a>'

    # chart flags
    flags = []
    if has['Allergies'] == 0:
        flags.append(('NKA', 'No Known Allergies', 'gray'))
    else:
        flags.append(('ALG', f'{has["Allergies"]} Allergies', 'red'))
    flags += [('Rx', f'{has["Medications"]} Medications', 'teal'),
              ('Dx', f'{has["Conditions"]} Conditions', 'teal'),
              ('Lab', f'{has["Lab Results"]} Lab Results', 'teal'),
              ('Imm', f'{has["Immunizations"]} Immunizations', 'teal')]
    flag_html = ''.join(f'<span class="flag {c}" title="{E(t)}">{E(code)}</span>'
                        for code, t, c in flags)

    def sec(key, inner):
        return f'<div class="secwrap" data-sec="{key}">{inner}</div>'

    content = '\n'.join([
        sec('conditions', panel('Conditions', T['conditions'], has['Conditions'])),
        sec('allergies', panel('Allergies', T['allergies'], has['Allergies'])),
        sec('medications', panel('Medications', T['medications'], has['Medications'])),
        sec('lab-results', panel('Lab Results', T['labs'], has['Lab Results'])),
        sec('vital-signs', panel('Vital Signs', T['vitals'], has['Vital Signs'])),
        sec('immunizations', panel('Immunizations', T['imm'], has['Immunizations'])),
        sec('procedures', panel('Procedures', T['proc'], has['Procedures'])),
        sec('encounters', panel('Encounters', T['enc'], has['Encounters'])),
        sec('demographics', panel('Demographics', T['demo'])),
    ])

    initials = (P['given'][:1] + P['family'][:1]).upper()
    style = '' if idx == 0 else ' style="display:none"'
    _aa = P.get('mrn_aa') or ''
    _qe = _aa.split('|')[0] if _aa else ''
    _src = _aa.split('|')[1] if '|' in _aa else ''
    _mrns = ';'.join(f"{m['qe']}|{m['source']}:{m['mrn']}" for m in P.get('mrn_list', []))
    return f"""
    <div class="patient" data-idx="{idx}" data-first="{E(P['given'])}" data-last="{E(P['family'])}" data-dob="{E(P['dob'])}" data-qe="{E(_qe)}" data-source="{E(_src)}" data-mrn="{E(P['mrn'])}" data-mrns="{E(_mrns)}"{style}>
      <div class="banner">
        <h1>{E(P['family'].upper())}, {E(P['given'])}</h1>
        <div class="sub"><b>{E(P['gender'])}</b> &nbsp; {P['age']}y &nbsp; {E(P['dob'])}
          &nbsp; MPIID: {E(P['mpiid'][:16])}&hellip; &nbsp; <span class="muted">{E(P['mpid_tag'])}</span></div>
      </div>
      <div class="divider"></div>
      <div class="flagbar"><span class="lbl">Chart Flags</span>{flag_html}</div>
      <div class="cols">
        <nav class="chartbook"><div class="cb-head">Chartbook</div>{nav_html}</nav>
        <div class="content">
          <h2 class="viewTitle">Clinical Summary</h2>
          {content}
          <div class="footer">
            Patient chart summary generated from C-CDA R2.1. Document date: {E(P['doc_date'])}.
            Source: synthetic C-CDA (demonstration data only).
            Styled after the HEALTHeLINK Fusion clinical viewer.
          </div>
        </div>
      </div>
    </div>"""


def load_oru(patients):
    """Load ORU (FHIR Observation NDJSON) labs, attach to the matching patient
    by MPID, and flag CCD labs that the ORU feed duplicates."""
    import json
    by_mpid = {}
    for fn in glob.glob('*oru*.ndjson'):
        with open(fn, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                if o.get('resourceType') != 'Observation':
                    continue
                mpid = ''
                for idn in o.get('subject', {}).get('identifier', []):
                    if idn.get('system', '').endswith(':mpid'):
                        mpid = idn.get('value', '')
                if not mpid:
                    continue
                cod = o.get('code', {})
                coding = (cod.get('coding') or [{}])[0]
                loinc = coding.get('code', '')
                disp = coding.get('display', '') or cod.get('text', '')
                vq = o.get('valueQuantity', {})
                eff = o.get('effectiveDateTime', '')[:10]  # YYYY-MM-DD
                d = ''
                if len(eff) == 10:
                    d = f'{eff[5:7]}/{eff[8:10]}/{eff[0:4]}'
                by_mpid.setdefault(mpid, []).append({
                    'test': disp, 'loinc': loinc, 'value': vq.get('value', ''),
                    'unit': vq.get('unit', ''), 'date': d, 'dup': False})

    for P in patients:
        oru = by_mpid.get(P['mpid_tag'], [])
        P['oru'] = oru
        # CCD (loinc, date) index
        ccd_keys = set()
        for panel in P['labs']:
            for c in panel['comps']:
                ccd_keys.add((c['loinc'], c['date']))
        oru_keys = set((o['loinc'], o['date']) for o in oru)
        for o in oru:
            o['dup'] = (o['loinc'], o['date']) in ccd_keys
        for panel in P['labs']:
            for c in panel['comps']:
                if (c['loinc'], c['date']) in oru_keys:
                    c['superseded'] = True


# ---------- build ----------
# Use the shared parser/loaders as the single source of truth (this rebinds the
# names over the inline copies above, so both views behave identically).
from ccda_parse import parse_ccd, load_oru, load_oru_hl7, merge_by_person  # noqa: E402

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
    label = f'{P["family"].upper()}, {P["given"]}  ({P["gender"]} {P["age"]}y, DOB {P["dob"]})'
    options += f'<option value="{i}">{E(label)}</option>'

blocks = '\n'.join(render_patient(P, i) for i, P in enumerate(patients))
now_str = datetime.now().strftime('%m/%d/%Y %I:%M %p')

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Patient Chart Viewer</title>
<style>
  :root {{
    --teal:#00838f; --teal-d:#006974; --teal-l:#b2dfdb; --teal-sel:#d7ecec;
    --indigo:#3f51b5; --ink:#263238; --muted:#607d8b; --line:#e0e4e7;
    --bg:#eceff1; --red:#c62828;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Segoe UI",Roboto,Arial,sans-serif; color:var(--ink);
    background:var(--bg); font-size:13px; }}
  a {{ color:inherit; text-decoration:none; }}
  .muted {{ color:var(--muted); }}

  .appbar {{ display:flex; align-items:center; background:#fff; border-bottom:1px solid var(--line);
    height:46px; padding:0 12px; gap:12px; }}
  .logo {{ width:26px; height:26px; border-radius:4px; background:var(--teal); color:#fff;
    font-weight:700; display:flex; align-items:center; justify-content:center; font-style:italic; }}
  .appbar .nav-label {{ color:var(--muted); font-size:13px; }}
  .appbar .spacer {{ flex:1; }}
  .patient-pick {{ display:flex; align-items:center; gap:8px; }}
  .patient-pick label {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.5px; }}
  .patient-pick select {{ font-size:13px; padding:5px 10px; border:1px solid #cfd8dc; border-radius:4px;
    background:#fff; color:#263238; min-width:320px; }}
  .appbar .psel {{ border-left:1px solid var(--line); padding:0 16px; height:100%;
    display:flex; align-items:center; font-weight:600; color:#37474f; }}

  .shell {{ display:flex; }}
  .rail {{ width:46px; background:#37474f; min-height:calc(100vh - 46px);
    display:flex; flex-direction:column; align-items:center; padding-top:10px; gap:18px; color:#b0bec5; }}
  .rail span {{ font-size:16px; opacity:.85; }}
  .main {{ flex:1; min-width:0; }}

  .banner {{ background:#f5f6f7; padding:12px 20px 10px; }}
  .banner h1 {{ margin:0; font-size:18px; letter-spacing:.3px; text-transform:uppercase; color:#1f2d33; }}
  .banner .sub {{ color:var(--muted); font-size:12.5px; margin-top:3px; }}
  .banner .sub b {{ color:#37474f; }}
  .divider {{ height:4px; background:linear-gradient(to bottom,var(--teal-l),var(--teal)); }}

  .flagbar {{ display:flex; gap:8px; align-items:center; padding:8px 20px; background:#fff;
    border-bottom:1px solid var(--line); }}
  .flagbar .lbl {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.5px; margin-right:4px; }}
  .flag {{ font-size:11px; font-weight:700; padding:3px 8px; border-radius:12px; border:1px solid; }}
  .flag.teal {{ color:var(--teal-d); border-color:var(--teal-l); background:#e0f2f1; }}
  .flag.red {{ color:var(--red); border-color:#ef9a9a; background:#ffebee; }}
  .flag.gray {{ color:var(--muted); border-color:#cfd8dc; background:#eceff1; }}

  .cols {{ display:flex; }}
  .chartbook {{ width:200px; background:#fff; border-right:1px solid var(--line); flex:none; }}
  .chartbook .cb-head {{ font-weight:600; padding:10px 14px; color:#37474f; border-bottom:1px solid var(--line); }}
  .nav-item {{ display:block; padding:7px 14px; font-size:13px; color:#546e7a;
    border-left:3px solid transparent; cursor:pointer; }}
  .nav-item.hasdata {{ color:#263238; border-left-color:var(--teal-l); }}
  .nav-item:hover {{ background:#f2f7f7; }}
  .nav-item.sel {{ background:var(--teal-sel); border-left-color:var(--teal); color:#00474f; font-weight:600; }}
  .nav-item.disabled {{ color:#b0bec5; cursor:default; }}
  .nav-item.disabled:hover {{ background:none; }}

  .content {{ flex:1; min-width:0; padding:16px 20px 60px; }}
  .content > h2 {{ margin:2px 0 14px; font-size:16px; color:#1f2d33; }}

  .card {{ background:#fff; border:1px solid var(--line); border-radius:3px; margin-bottom:16px; overflow:hidden; }}
  .card-accent {{ height:4px; background:var(--teal-l); }}
  .card-head {{ display:flex; align-items:center; gap:8px; background:#f7f8f9;
    border-bottom:1px solid var(--line); padding:7px 12px; }}
  .chev {{ color:var(--muted); }}
  .card-title {{ font-weight:600; color:#37474f; }}
  .card-title .cnt {{ display:inline-block; min-width:18px; text-align:center; background:#eceff1;
    color:var(--muted); border-radius:10px; font-size:11px; padding:0 6px; margin-left:4px; font-weight:600; }}
  .card-tools {{ margin-left:auto; display:flex; align-items:center; gap:10px; }}
  .search {{ position:relative; }}
  .search input {{ width:150px; padding:4px 24px 4px 8px; border:1px solid #cfd8dc; border-radius:3px;
    font-size:12px; background:#fff; }}
  .search .mag {{ position:absolute; right:6px; top:3px; color:var(--muted); font-size:12px; }}
  .filter {{ color:var(--indigo); font-size:16px; cursor:default; }}
  .card-body {{ overflow-x:auto; }}

  table {{ width:100%; border-collapse:collapse; }}
  thead th {{ text-align:left; font-size:11.5px; color:#546e7a; font-weight:600;
    padding:8px 12px; border-bottom:1px solid var(--line); white-space:nowrap; background:#fff; }}
  thead th .sort {{ color:#b0bec5; font-size:11px; }}
  tbody td {{ padding:8px 12px; border-bottom:1px solid #eef1f2; vertical-align:top; }}
  tbody tr:hover {{ background:#fafcfc; }}
  .lnk {{ color:var(--teal-d); }}
  .lnk:hover {{ text-decoration:underline; }}

  .status {{ font-size:11px; font-weight:600; padding:2px 8px; border-radius:10px; }}
  .status.active {{ background:#e0f2f1; color:var(--teal-d); }}
  .status.resolved {{ background:#eceff1; color:var(--muted); }}

  .labs .grouphdr td {{ background:#f2f7f7; font-weight:600; color:#37474f; }}
  .labs .grouphdr .gdate {{ float:right; color:var(--muted); font-weight:500; }}
  tr.abn td {{ background:#fff6f6; }}
  .flagcell {{ position:relative; padding-left:16px !important; }}
  .bar {{ position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--red); }}
  .abnval {{ color:var(--red); font-weight:700; }}

  /* source badges */
  .src {{ display:inline-block; font-size:10px; font-weight:700; letter-spacing:.3px;
    padding:1px 6px; border-radius:10px; border:1px solid; margin-right:6px; vertical-align:middle; }}
  .src.ccd {{ color:var(--muted); border-color:#cfd8dc; background:#eceff1; }}
  .src.oru {{ color:#1565c0; border-color:#90caf9; background:#e3f2fd; }}

  /* prominent ORU feed group */
  .labs .oru-hdr td {{ background:#e3f2fd; color:#0d47a1; border-top:2px solid #1565c0; }}
  .labs .oru-hdr .gdate {{ color:#1565c0; }}
  tr.oru-row td {{ background:#f3f9ff; }}
  tr.oru-row .strong {{ font-weight:700; color:#0d47a1; }}
  .dupnote {{ font-size:10.5px; color:#1565c0; background:#e3f2fd; border:1px solid #90caf9;
    padding:0 6px; border-radius:8px; margin-left:6px; }}
  .newnote {{ font-size:10.5px; color:var(--teal-d); background:#e0f2f1; border:1px solid var(--teal-l);
    padding:0 6px; border-radius:8px; margin-left:6px; }}

  /* superseded CCD rows */
  tr.superseded td {{ background:#fafafa; }}
  tr.superseded .lnk, tr.superseded td:nth-child(2) {{ text-decoration:line-through; color:#9aa7ad; }}
  .supnote {{ font-size:10.5px; color:#b0431f; background:#fdecea; border:1px solid #f3c0b6;
    padding:0 6px; border-radius:8px; margin-left:6px; text-decoration:none; }}

  .lab-legend {{ font-size:11.5px; color:var(--muted); padding:10px 12px; background:#fafbfc;
    border-bottom:1px solid var(--line); }}
  .lab-legend .superseded .lnk {{ text-decoration:line-through; color:#9aa7ad; }}

  .demo th {{ text-align:left; width:180px; color:var(--muted); font-weight:600; padding:8px 12px;
    border-bottom:1px solid #eef1f2; vertical-align:top; }}
  .demo td {{ border-bottom:1px solid #eef1f2; }}
  .empty {{ padding:16px; color:var(--muted); font-style:italic; }}
  .footer {{ color:var(--muted); font-size:11px; padding:14px 20px; }}
</style>
</head>
<body data-view-qe="{E(VIEW_QE)}">

  <div class="appbar">
    <div class="logo">f</div>
    <div class="nav-label">Navigation &nbsp;|&nbsp; Viewer: <b style="color:#37474f">Clinical Summary</b></div>
    <div class="spacer"></div>
    <div class="patient-pick">
      <label for="patientSel">Patient</label>
      <select id="patientSel">{options}</select>
    </div>
    <div class="psel">Patient Selection</div>
  </div>

  <div class="shell">
    <div class="rail">
      <span title="Patients">&#128100;</span><span title="Documents">&#128196;</span>
      <span title="Messages">&#9993;</span><span title="Alerts">&#128276;</span>
      <span title="Settings">&#9881;</span>
    </div>
    <div class="main">
      {blocks}
    </div>
  </div>

<script>
(function() {{
  function setSection(pat, target, label) {{
    pat.querySelectorAll('.secwrap').forEach(function(s) {{
      s.style.display = (target === 'summary' || s.getAttribute('data-sec') === target) ? '' : 'none';
    }});
    pat.querySelectorAll('.nav-item[data-target]').forEach(function(n) {{
      n.classList.toggle('sel', n.getAttribute('data-target') === target);
    }});
    var vt = pat.querySelector('.viewTitle');
    if (vt) vt.textContent = label;
    window.scrollTo(0, 0);
  }}

  document.querySelectorAll('.patient').forEach(function(pat) {{
    pat.querySelectorAll('.nav-item[data-target]').forEach(function(n) {{
      n.addEventListener('click', function() {{
        setSection(pat, n.getAttribute('data-target'), n.textContent.trim());
      }});
    }});
    setSection(pat, 'summary', 'Clinical Summary');
  }});

  var sel = document.getElementById('patientSel');
  sel.addEventListener('change', function() {{
    document.querySelectorAll('.patient').forEach(function(pat) {{
      pat.style.display = (pat.getAttribute('data-idx') === sel.value) ? '' : 'none';
    }});
    window.scrollTo(0, 0);
  }});
}})();
</script>
</body>
</html>"""

HTML = inject_bug(HTML)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Wrote {OUT} with {len(patients)} patients")
for i, P in enumerate(patients):
    print(f"  {i}: {P['family'].upper()}, {P['given']}  {P['gender']} {P['age']}y  "
          f"Dx={P['has']['Conditions']} Rx={P['has']['Medications']} Lab={P['has']['Lab Results']}")
