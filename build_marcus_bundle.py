"""
Mint one self-consistent synthetic test person, "Marcus Evans", who exists
across 5 real SHIN-NY QE sources (3 facilities each, 15 total) so he can be
linked in the MPI, plus genuine HL7 v2.5.1 ORU^R01 lab messages and TRN
discharge summaries.

Outputs a self-contained bundle under ./marcus_bundle with per-QE subfolders.

Identity model (matches the MPI-linkage notebook + Julie's note):
  - a source identity is (qe, source, mrn); assigning authority in the CCD is "QE|Source".
  - the cross-source keys are eid (per qe) and a shared mpid.
Each source uses a different Synthea base CCD for clinical variety; the script
rewrites name / DOB / gender and the source <id>, keeping the base CCD's real
conditions and labs so the portal has real clinical data to display.
"""
import os
import shutil
import copy
import xml.etree.ElementTree as ET

V3 = 'urn:hl7-org:v3'
ns = {'v3': V3}
CCDS_DIR = os.environ.get('SYNTHEA_CCDS_DIR', 'ccds')
OUT = 'marcus_bundle'

ET.register_namespace('', V3)
ET.register_namespace('sdtc', 'urn:hl7-org:sdtc')
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

# ---- Marcus golden identity ----
FIRST, LAST = 'Marcus', 'Evans'
DOB = '19500601'          # 1950-06-01
GENDER = 'M'
MPID = 'MARCUS-GOLDEN-0001'
ADDR = ('179 Bednar Knoll Suite 2', 'New York', 'NY', '11367')

# 15 sources: 5 QEs x 3 facilities each. Each uses a different base CCD.
# No GRRHIO/Rochester.
SOURCES = [
    # HIXNY
    {'qe': 'HIXNY',       'source': 'SPLPCPRIME', 'mrn': '956304', 'eid': 'HI-EID-5976',
     'base': 'BRONX-MPID-000032_Dwain139_Hartmann983_e6b63232-7089-e00b-b09c-7fec1e30a1e6.xml'},
    {'qe': 'HIXNY',       'source': 'ALBMC',      'mrn': '945947', 'eid': 'HI-EID-5392',
     'base': 'BRONX-MPID-000053_Deshawn686_Wilkinson796_6357b2bc-ccf3-bd9d-36a1-21e38ba7b8e5.xml'},
    {'qe': 'HIXNY',       'source': 'ELLS',       'mrn': '671234', 'eid': 'HI-EID-6012',
     'base': 'BRONX-MPID-000068_Shenita872_Osinski784_eb4a5007-18fc-ba60-2811-54dd5820fde0.xml'},
    # HEALTHELINK
    {'qe': 'HEALTHELINK', 'source': 'KINGSB',     'mrn': '832368', 'eid': 'HE-EID-9965',
     'base': 'BRONX-MPID-000024_Peter292_Olson653_1dea7120-75ab-3049-0e6c-42721886f034.xml'},
    {'qe': 'HEALTHELINK', 'source': 'ECMC',       'mrn': '881691', 'eid': 'HE-EID-9109',
     'base': 'BRONX-MPID-000031_Millard193_Beahan375_ab53fbf2-df39-cfce-bd37-05c891d6114e.xml'},
    {'qe': 'HEALTHELINK', 'source': 'RPCI',       'mrn': '748293', 'eid': 'HE-EID-7541',
     'base': 'BRONX-MPID-000092_Janeth814_Loree183_Schmitt836_4dcf8aea-5afd-c06f-1518-52dfa8ccf531.xml'},
    # HEALTHIX
    {'qe': 'HEALTHIX',    'source': 'MSSM',       'mrn': '340474', 'eid': 'HE-EID-8304',
     'base': 'BRONX-MPID-000003_Lessie363_Cartwright189_3d8cfae0-76e6-8b05-3421-f81320276a38.xml'},
    {'qe': 'HEALTHIX',    'source': 'NYP',        'mrn': '811058', 'eid': 'HE-EID-6843',
     'base': 'BRONX-MPID-000005_Cary869_Mante251_94f83860-c645-ca9d-ba62-ec22edb1cc5b.xml'},
    {'qe': 'HEALTHIX',    'source': 'BELLEVUE',   'mrn': '529417', 'eid': 'HE-EID-4218',
     'base': 'BRONX-MPID-000094_Haydee844_Elna874_Beahan375_0c7cfb67-ad2f-4381-ff1b-c7e334dc0c85.xml'},
    # HEALTHECONN
    {'qe': 'HEALTHECONN', 'source': 'UHS',        'mrn': '826608', 'eid': 'HE-EID-2717',
     'base': 'BRONX-MPID-000101_Carly657_Sparkle906_Bins636_880bba7a-b046-c5b7-4995-579eee711aa5.xml'},
    {'qe': 'HEALTHECONN', 'source': 'SJHHC',      'mrn': '413856', 'eid': 'HE-EID-3298',
     'base': 'BRONX-MPID-000003_Lessie363_Cartwright189_3d8cfae0-76e6-8b05-3421-f81320276a38.xml'},
    {'qe': 'HEALTHECONN', 'source': 'UPSTATE',    'mrn': '697215', 'eid': 'HE-EID-5107',
     'base': 'BRONX-MPID-000031_Millard193_Beahan375_ab53fbf2-df39-cfce-bd37-05c891d6114e.xml'},
    # BRONX
    {'qe': 'BRONX',       'source': 'BXLEB',      'mrn': '515366', 'eid': 'BR-EID-1665',
     'base': 'BRONX-MPID-000094_Haydee844_Elna874_Beahan375_0c7cfb67-ad2f-4381-ff1b-c7e334dc0c85.xml'},
    {'qe': 'BRONX',       'source': 'SBH',        'mrn': '284731', 'eid': 'BR-EID-2194',
     'base': 'BRONX-MPID-000024_Peter292_Olson653_1dea7120-75ab-3049-0e6c-42721886f034.xml'},
    {'qe': 'BRONX',       'source': 'MMC',        'mrn': '362948', 'eid': 'BR-EID-3017',
     'base': 'BRONX-MPID-000053_Deshawn686_Wilkinson796_6357b2bc-ccf3-bd9d-36a1-21e38ba7b8e5.xml'},
]

# 15 sets of lab values for ORU variety (Glucose, Creatinine, Sodium, HbA1c)
LAB_VALUES = [
    (81, 0.91, 140, 6.1),   # HIXNY SPLPCPRIME
    (88, 1.05, 138, 6.0),   # HIXNY ALBMC
    (78, 0.87, 143, 5.9),   # HIXNY ELLS
    (92, 1.12, 137, 6.3),   # HEALTHELINK KINGSB
    (85, 0.95, 141, 6.2),   # HEALTHELINK ECMC
    (90, 1.20, 139, 6.5),   # HEALTHELINK RPCI
    (83, 0.89, 144, 5.8),   # HEALTHIX MSSM
    (95, 1.10, 138, 6.4),   # HEALTHIX NYP
    (79, 0.99, 142, 6.0),   # HEALTHIX BELLEVUE
    (86, 1.25, 140, 6.1),   # HEALTHECONN UHS
    (91, 0.93, 137, 6.3),   # HEALTHECONN SJHHC
    (84, 1.02, 143, 5.9),   # HEALTHECONN UPSTATE
    (87, 0.85, 141, 6.2),   # BRONX BXLEB
    (93, 1.15, 139, 6.0),   # BRONX SBH
    (80, 0.97, 144, 6.4),   # BRONX MMC
]

# Collection dates spread over 20250314-20250316 for variety
COLLECT_DATES = [
    '20250314083000', '20250314101500', '20250314143000',
    '20250315080000', '20250315094500', '20250315120000',
    '20250315083000', '20250315110000', '20250315141500',
    '20250316080000', '20250316093000', '20250316114500',
    '20250314090000', '20250315100000', '20250316130000',
]

# TRN encounter configuration per source
TRN_CONFIG = [
    # (admit_date, enc_type, enc_code, facility_name)
    ('20250110', 'Inpatient',   '99223', 'SPLPC Primary Care'),
    ('20241205', 'Emergency',   '99285', 'Albany Medical Center'),
    ('20250218', 'Observation', '99220', 'Ellis Hospital'),
    ('20241115', 'Inpatient',   '99223', 'Kingsbrook Jewish Medical Center'),
    ('20250301', 'Emergency',   '99285', 'Erie County Medical Center'),
    ('20240920', 'Inpatient',   '99223', 'Roswell Park Comprehensive Cancer'),
    ('20250105', 'Observation', '99220', 'Mount Sinai Hospital'),
    ('20241010', 'Emergency',   '99285', 'NewYork-Presbyterian Hospital'),
    ('20250220', 'Inpatient',   '99223', 'Bellevue Hospital Center'),
    ('20241201', 'Observation', '99220', 'UHS Wilson Medical Center'),
    ('20250115', 'Emergency',   '99285', 'St. Joseph Hospital Health Center'),
    ('20240825', 'Inpatient',   '99223', 'SUNY Upstate Medical University'),
    ('20250305', 'Emergency',   '99285', 'Bronx-Lebanon Hospital'),
    ('20241020', 'Inpatient',   '99223', 'St. Barnabas Hospital'),
    ('20250125', 'Observation', '99220', 'Montefiore Medical Center'),
]

# Marcus's 5 shared conditions
MARCUS_CONDITIONS = [
    ('44054006',  'Diabetes mellitus type 2'),
    ('59621000',  'Essential hypertension'),
    ('55822004',  'Hyperlipidemia'),
    ('431855005', 'Chronic kidney disease stage 3'),
    ('396275006', 'Osteoarthritis'),
]


def q(t):
    return f'{{{V3}}}{t}'


def make_ccd(src):
    """Clone a Synthea base CCD, re-stamping identity for Marcus at this source."""
    base_path = os.path.join(CCDS_DIR, src['base'])
    tree = ET.parse(base_path)
    root = tree.getroot()

    # document-level authored time -> common recent date
    de = root.find('v3:effectiveTime', ns)
    if de is not None:
        de.set('value', '20250315120000')

    pr = root.find('.//v3:recordTarget/v3:patientRole', ns)

    # rewrite the source <id>: QE|Source + MRN
    ids = pr.findall('v3:id', ns)
    if ids:
        ids[0].set('extension', src['mrn'])
        ids[0].set('assigningAuthorityName', f"{src['qe']}|{src['source']}")
    # add EID (per-QE enterprise id) and shared MPID
    eid_el = ET.SubElement(pr, q('id'))
    eid_el.set('root', '2.16.840.1.113883.3.9999.eid')
    eid_el.set('extension', src['eid'])
    eid_el.set('assigningAuthorityName', src['qe'])
    mpid_el = ET.SubElement(pr, q('id'))
    mpid_el.set('root', '2.16.840.1.113883.3.9999.mpid')
    mpid_el.set('extension', MPID)
    # move the two new ids right after existing ids
    for e in (eid_el, mpid_el):
        pr.remove(e)
    insert_at = list(pr).index(ids[-1]) + 1 if ids else 0
    pr.insert(insert_at, mpid_el)
    pr.insert(insert_at, eid_el)

    # address
    addr = pr.find('v3:addr', ns)
    if addr is not None:
        for tag, val in zip(('streetAddressLine', 'city', 'state', 'postalCode'), ADDR):
            el = addr.find(f'v3:{tag}', ns)
            if el is None:
                el = ET.SubElement(addr, q(tag))
            el.text = val

    # name / gender / dob
    pat = pr.find('v3:patient', ns)
    nm = pat.find('v3:name', ns)
    givens = nm.findall('v3:given', ns)
    for extra in givens[1:]:
        nm.remove(extra)
    if givens:
        givens[0].text = FIRST
    else:
        ET.SubElement(nm, q('given')).text = FIRST
    fam = nm.find('v3:family', ns)
    if fam is None:
        fam = ET.SubElement(nm, q('family'))
    fam.text = LAST
    g = pat.find('v3:administrativeGenderCode', ns)
    if g is not None:
        g.set('code', GENDER)
    bt = pat.find('v3:birthTime', ns)
    if bt is not None:
        bt.set('value', DOB)

    return ET.tostring(root, encoding='unicode')


# ---------- HL7 v2.5.1 ORU^R01 ----------
def hl7(fields):
    return '|'.join(fields)


def oru_message(src, msgid, collected, obx_rows, order_dt=None):
    """Build a genuine HL7 v2.5.1 ORU^R01 message string (CR-separated segments)."""
    order_dt = order_dt or collected
    qe, fac, mrn = src['qe'], src['source'], src['mrn']
    seg = []
    seg.append(hl7(['MSH', '^~\\&', f'LAB_{qe}', fac, 'SHINNY', 'NYS',
                    collected, '', 'ORU^R01^ORU_R01', msgid, 'P', '2.5.1']))
    pid3 = f'{mrn}^^^{qe}&{fac}^MR~{src["eid"]}^^^{qe}^PI~{MPID}^^^NYEC^PI'
    addr = f'{ADDR[0]}^^{ADDR[1]}^{ADDR[2]}^{ADDR[3]}'
    seg.append(hl7(['PID', '1', '', pid3, '', f'{LAST}^{FIRST}', '', DOB, GENDER,
                    '', '', addr]))
    seg.append(hl7(['PV1', '1', 'O', f'{fac}']))
    seg.append(hl7(['ORC', 'RE', f'ORD{msgid}', f'FIL{msgid}', '', '', '', '', '',
                    order_dt]))
    seg.append(hl7(['OBR', '1', f'ORD{msgid}', f'FIL{msgid}',
                    '51990-0^Basic metabolic panel^LN', '', order_dt, collected,
                    '', '', '', '', '', '', '', '', '', '', '', '', '', 'F']))
    for i, r in enumerate(obx_rows, 1):
        code, name, val, unit, rng, flag = r
        seg.append(hl7(['OBX', str(i), 'NM', f'{code}^{name}^LN', '', str(val),
                        unit, rng, flag, '', '', 'F', '', '', collected]))
    return '\r'.join(seg) + '\r'


# ---------- TRN (discharge summary) ----------
def make_trn(src, trn_cfg):
    """Build a minimal C-CDA R2.1 discharge summary for parse_ccd() compatibility."""
    admit_date, enc_type, enc_code, facility = trn_cfg

    # Discharge = admit + 3 days
    admit_y, admit_m, admit_d = int(admit_date[:4]), int(admit_date[4:6]), int(admit_date[6:8])
    from datetime import date as _date, timedelta
    discharge = _date(admit_y, admit_m, admit_d) + timedelta(days=3)
    discharge_str = discharge.strftime('%Y%m%d')

    qe_source = f"{src['qe']}|{src['source']}"

    # Build encounter entry XML
    enc_entry = f'''<entry typeCode="DRIV">
          <encounter classCode="ENC" moodCode="EVN">
            <templateId root="2.16.840.1.113883.10.20.22.4.49" extension="2015-08-01"/>
            <id root="2.16.840.1.113883.19.5" extension="ENC-{src['qe']}-{src['source']}-001"/>
            <code code="{enc_code}" displayName="{enc_type}" codeSystem="2.16.840.1.113883.6.12" codeSystemName="CPT"/>
            <effectiveTime>
              <low value="{admit_date}"/>
              <high value="{discharge_str}"/>
            </effectiveTime>
            <participant typeCode="LOC">
              <participantRole classCode="SDLOC">
                <playingEntity classCode="PLC">
                  <name>{facility}</name>
                </playingEntity>
              </participantRole>
            </participant>
          </encounter>
        </entry>'''

    # Build problems entries
    prob_entries = ''
    for i, (snomed, display) in enumerate(MARCUS_CONDITIONS):
        prob_entries += f'''
        <entry typeCode="DRIV">
          <act classCode="ACT" moodCode="EVN">
            <templateId root="2.16.840.1.113883.10.20.22.4.3" extension="2015-08-01"/>
            <id root="2.16.840.1.113883.19.5" extension="PROB-{src['qe']}-{src['source']}-{i+1:03d}"/>
            <code code="CONC" codeSystem="2.16.840.1.113883.5.6"/>
            <statusCode code="active"/>
            <effectiveTime>
              <low value="20200101"/>
            </effectiveTime>
            <entryRelationship typeCode="SUBJ">
              <observation classCode="OBS" moodCode="EVN">
                <templateId root="2.16.840.1.113883.10.20.22.4.4" extension="2015-08-01"/>
                <id root="2.16.840.1.113883.19.5" extension="OBS-{src['qe']}-{src['source']}-{i+1:03d}"/>
                <code code="64572001" displayName="Condition" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
                <statusCode code="completed"/>
                <effectiveTime>
                  <low value="20200101"/>
                </effectiveTime>
                <value xsi:type="CD" code="{snomed}" displayName="{display}" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
              </observation>
            </entryRelationship>
          </act>
        </entry>'''

    xml = f'''<?xml version='1.0' encoding='UTF-8'?>
<ClinicalDocument xmlns="urn:hl7-org:v3" xmlns:sdtc="urn:hl7-org:sdtc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:hl7-org:v3 http://xreg2.nist.gov:8080/hitspValidation/schema/cdar2c32/infrastructure/cda/C32_CDA.xsd">
  <realmCode code="US"/>
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.1" extension="2015-08-01"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.8" extension="2015-08-01"/>
  <id root="2.16.840.1.113883.19.5" extension="TRN-{src['qe']}-{src['source']}-001" assigningAuthorityName="{qe_source}"/>
  <code code="18842-5" displayName="Discharge summary" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
  <title>Discharge Summary: {FIRST} {LAST} — {facility}</title>
  <effectiveTime value="{discharge_str}120000"/>
  <confidentialityCode code="N"/>
  <languageCode code="en-US"/>
  <recordTarget>
    <patientRole>
      <id extension="{src['mrn']}" assigningAuthorityName="{qe_source}" root="94f24417-94dd-5693-a38c-b610acf36d41"/>
      <id root="2.16.840.1.113883.3.9999.eid" extension="{src['eid']}" assigningAuthorityName="{src['qe']}"/>
      <id root="2.16.840.1.113883.3.9999.mpid" extension="{MPID}"/>
      <addr use="HP">
        <streetAddressLine>{ADDR[0]}</streetAddressLine>
        <city>{ADDR[1]}</city>
        <state>{ADDR[2]}</state>
        <postalCode>{ADDR[3]}</postalCode>
      </addr>
      <telecom nullFlavor="NI"/>
      <patient>
        <name>
          <given>{FIRST}</given>
          <family>{LAST}</family>
        </name>
        <administrativeGenderCode code="{GENDER}" codeSystem="2.16.840.1.113883.5.1" codeSystemName="HL7 AdministrativeGender"/>
        <birthTime value="{DOB}"/>
        <raceCode code="2106-3" displayName="white" codeSystemName="CDC Race and Ethnicity" codeSystem="2.16.840.1.113883.6.238"/>
        <ethnicGroupCode code="2186-5" displayName="non-hispanic" codeSystemName="CDC Race and Ethnicity" codeSystem="2.16.840.1.113883.6.238"/>
        <languageCommunication>
          <languageCode code="en-US"/>
        </languageCommunication>
      </patient>
    </patientRole>
  </recordTarget>
  <author>
    <time value="{discharge_str}120000"/>
    <assignedAuthor>
      <id nullFlavor="NA"/>
      <addr nullFlavor="NA"/>
      <telecom nullFlavor="NA"/>
      <assignedAuthoringDevice>
        <manufacturerModelName>SHIN-NY Synthetic Data Generator</manufacturerModelName>
        <softwareName>build_marcus_bundle.py</softwareName>
      </assignedAuthoringDevice>
      <representedOrganization>
        <id nullFlavor="NA"/>
        <name>{facility}</name>
        <telecom nullFlavor="NA"/>
        <addr nullFlavor="NA"/>
      </representedOrganization>
    </assignedAuthor>
  </author>
  <custodian>
    <assignedCustodian>
      <representedCustodianOrganization>
        <id nullFlavor="NA"/>
        <name>{facility}</name>
        <telecom nullFlavor="NA"/>
        <addr nullFlavor="NA"/>
      </representedCustodianOrganization>
    </assignedCustodian>
  </custodian>
  <documentationOf>
    <serviceEvent classCode="PCPR">
      <effectiveTime>
        <low value="{admit_date}"/>
        <high value="{discharge_str}"/>
      </effectiveTime>
    </serviceEvent>
  </documentationOf>
  <component>
    <structuredBody>
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.22.1" extension="2015-08-01"/>
          <code code="46240-8" displayName="History of encounters" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
          <title>Encounters</title>
          <text>
            <table border="1" width="100%">
              <thead><tr><th>Encounter</th><th>Date</th><th>Facility</th></tr></thead>
              <tbody><tr><td>{enc_type}</td><td>{admit_date[:4]}-{admit_date[4:6]}-{admit_date[6:8]}</td><td>{facility}</td></tr></tbody>
            </table>
          </text>
          {enc_entry}
        </section>
      </component>
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.5.1" extension="2015-08-01"/>
          <code code="11450-4" displayName="Problem list" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
          <title>Problems</title>
          <text>
            <table border="1" width="100%">
              <thead><tr><th>Condition</th><th>Status</th></tr></thead>
              <tbody>''' + ''.join(
        f'''
                <tr><td>{display}</td><td>Active</td></tr>'''
        for _, display in MARCUS_CONDITIONS) + '''
              </tbody>
            </table>
          </text>''' + prob_entries + '''
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>'''
    return xml


# ---------- build ----------
def main():
    # Clean up any old flat structure
    for old_dir in ('ccda', 'oru-hl7'):
        old_path = os.path.join(OUT, old_dir)
        if os.path.isdir(old_path):
            try:
                shutil.rmtree(old_path)
                print(f'  Removed old flat directory: {old_path}')
            except PermissionError:
                print(f'  Warning: could not remove {old_path} (locked by OneDrive?) - skipping')

    # Create per-QE subfolders
    qe_names = sorted(set(s['qe'].lower() for s in SOURCES))
    for qe_lower in qe_names:
        for sub in ('ccda', 'oru-hl7', 'trn'):
            os.makedirs(os.path.join(OUT, qe_lower, sub), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'mpi'), exist_ok=True)

    ccd_files = []
    oru_files = []
    trn_files = []

    for idx, src in enumerate(SOURCES):
        qe_lower = src['qe'].lower()

        # ---- CCD ----
        xml = make_ccd(src)
        fn = f"MARCUS_{src['qe']}_{src['source']}_{src['mrn']}.xml"
        path = os.path.join(OUT, qe_lower, 'ccda', fn)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("<?xml version='1.0' encoding='UTF-8'?>\n" + xml)
        ccd_files.append(os.path.join(qe_lower, 'ccda', fn))

        # ---- ORU ----
        glucose, creatinine, sodium, hba1c = LAB_VALUES[idx]
        collected = COLLECT_DATES[idx]
        msgid = f'MSG_{src["qe"]}_{src["source"]}_001'
        obx = [
            ('2339-0', 'Glucose', glucose, 'mg/dL', '70-99', 'N'),
            ('38483-4', 'Creatinine', creatinine, 'mg/dL', '0.70-1.30', 'N'),
            ('2947-0', 'Sodium', sodium, 'mmol/L', '136-145', 'N'),
            ('4548-4', 'Hemoglobin A1c', hba1c, '%', '4.0-5.6', 'H'),
        ]
        msg = oru_message(src, msgid, collected, obx)
        oru_fn = f"MARCUS_{src['qe']}_{src['source']}_{src['mrn']}_ORU.hl7"
        oru_path = os.path.join(OUT, qe_lower, 'oru-hl7', oru_fn)
        with open(oru_path, 'w', encoding='utf-8', newline='') as f:
            f.write(msg)
        oru_files.append(os.path.join(qe_lower, 'oru-hl7', oru_fn))

        # ---- TRN ----
        trn_xml = make_trn(src, TRN_CONFIG[idx])
        trn_fn = f"MARCUS_{src['qe']}_{src['source']}_{src['mrn']}_TRN.xml"
        trn_path = os.path.join(OUT, qe_lower, 'trn', trn_fn)
        with open(trn_path, 'w', encoding='utf-8') as f:
            f.write(trn_xml)
        trn_files.append(os.path.join(qe_lower, 'trn', trn_fn))

    # ---- MPI CSV ----
    mpi_path = os.path.join(OUT, 'mpi', 'marcus_mpi.csv')
    with open(mpi_path, 'w', encoding='utf-8', newline='') as f:
        f.write('qe,source,mrn,eid,mpid,first_name,last_name,dob,gender\n')
        for s in SOURCES:
            f.write(f"{s['qe']},{s['source']},{s['mrn']},{s['eid']},{MPID},"
                    f"{FIRST},{LAST},{DOB},{GENDER}\n")

    # ---- README ----
    src_table = '\n'.join(
        f"  {s['qe']:13s} | {s['source']:10s} | mrn={s['mrn']} eid={s['eid']} | base={s['base'][:40]}..."
        for s in SOURCES)
    readme = f"""# Marcus Evans — golden cross-source test person (synthetic)

One synthetic person who intentionally spans 5 SHIN-NY QE sources (3 facilities
each, 15 total) so he can be linked in the MPI and used to demo cross-source
matching, de-duplication, and per-QE filtering.

## Identity
  name: {FIRST} {LAST}   DOB: {DOB[:4]}-{DOB[4:6]}-{DOB[6:]}   sex: {GENDER}
  shared MPID: {MPID}
  address: {', '.join(ADDR)}

## Source identities (15 total, no Rochester/GRRHIO)
{src_table}

## Folder structure
  marcus_bundle/
    {{qe_lower}}/
      ccda/       3 C-CDA Continuity of Care Documents per QE
      oru-hl7/    3 HL7 v2.5.1 ORU^R01 lab messages per QE
      trn/        3 C-CDA Discharge Summary (TRN) documents per QE
    mpi/
      marcus_mpi.csv   MPI anchor rows (15 rows + header)

## QE subfolders
  - hixny/       — SPLPCPRIME, ALBMC, ELLS
  - healthelink/ — KINGSB, ECMC, RPCI
  - healthix/    — MSSM, NYP, BELLEVUE
  - healtheconn/ — UHS, SJHHC, UPSTATE
  - bronx/       — BXLEB, SBH, MMC

## File types
  CCD (.xml)  — Full clinical document with conditions, meds, labs, vitals,
                immunizations, procedures, encounters from the Synthea base.
                Each uses a *different* base CCD for clinical variety.
  ORU (.hl7)  — Basic Metabolic Panel with Glucose, Creatinine, Sodium, HbA1c.
                Values vary per source; HbA1c always flagged High (diabetes).
  TRN (.xml)  — Discharge summary with one encounter and Marcus's 5 shared
                conditions (DM2, HTN, Hyperlipidemia, CKD3, Osteoarthritis).

## De-duplication
  When all 3 CCDs from one QE are loaded together, merge_by_person() groups them
  by MPID into one virtual record. Each QE's view should show only that QE's 3
  source identities, not data from other QEs.

All data is 100% synthetic. Demonstration only.
"""
    with open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)

    # ---- Summary ----
    print(f'Bundle written to ./{OUT}')
    print(f'  CCDs: {len(ccd_files)} files across {len(qe_names)} QE folders')
    print(f'  ORUs: {len(oru_files)} files')
    print(f'  TRNs: {len(trn_files)} files')
    print(f'  MPI:  {mpi_path} ({len(SOURCES)} rows)')
    print(f'  QE folders: {", ".join(qe_names)}')
    for fn in ccd_files:
        print(f'    CCD: {fn}')
    for fn in oru_files:
        print(f'    ORU: {fn}')
    for fn in trn_files:
        print(f'    TRN: {fn}')


if __name__ == '__main__':
    main()
