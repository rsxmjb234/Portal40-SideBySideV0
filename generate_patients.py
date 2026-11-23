"""
Generic multi-patient synthetic data generator.
Reads patient_profiles.json and outputs clinically coherent CCDs, ORU labs,
and TRN discharge summaries to sample_patients/{patient_id}/{qe}/{type}/.

Usage:
    python generate_patients.py                           # all patients
    python generate_patients.py --patient marcus_evans    # one patient
"""
import os
import sys
import json
import shutil
import random
import argparse
import xml.etree.ElementTree as ET
from datetime import date, timedelta

V3 = 'urn:hl7-org:v3'
ns = {'v3': V3}
CCDS_DIR = os.environ.get('SYNTHEA_CCDS_DIR', 'ccds')
OUT = os.environ.get('SAMPLE_PATIENTS_DIR', 'sample_patients')

ET.register_namespace('', V3)
ET.register_namespace('sdtc', 'urn:hl7-org:sdtc')
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

ENC_CODES = {'Inpatient': '99223', 'Emergency': '99285', 'Observation': '99220'}

# ---- Condition-driven abnormal value rules ----
# Maps SNOMED code -> [(loinc, flag_direction, abnormal_low, abnormal_high)]
ABNORMAL_RULES = {
    '44054006': [   # DM2
        ('2339-0', 'H', 110, 220),
        ('4548-4', 'H', 6.5, 9.5),
    ],
    '46635009': [   # DM1
        ('2339-0', 'H', 120, 280),
        ('4548-4', 'H', 7.0, 10.0),
    ],
    '431855005': [  # CKD3
        ('38483-4', 'H', 1.5, 3.0),
        ('33914-3', 'L', 30, 55),
        ('3094-0', 'H', 25, 45),
        ('14959-1', 'H', 50, 200),
    ],
    '431857002': [  # CKD4
        ('38483-4', 'H', 2.5, 5.0),
        ('33914-3', 'L', 15, 29),
        ('3094-0', 'H', 35, 65),
        ('14959-1', 'H', 100, 300),
        ('6298-4', 'H', 5.1, 6.0),
    ],
    '709044004': [  # CKD2
        ('38483-4', 'H', 1.3, 1.8),
        ('33914-3', 'L', 60, 85),
        ('14959-1', 'H', 30, 80),
    ],
    '42343007': [   # CHF
        ('30934-4', 'H', 150, 800),
        ('6598-7', 'H', 0.04, 0.15),
    ],
    '53741008': [   # CAD
        ('2093-3', 'H', 200, 280),
        ('13457-7', 'H', 130, 190),
        ('6598-7', 'H', 0.03, 0.10),
    ],
    '49436004': [   # A-fib
        ('30934-4', 'H', 100, 400),
    ],
    '55822004': [   # Hyperlipidemia
        ('2093-3', 'H', 210, 300),
        ('2571-8', 'H', 160, 350),
        ('2085-9', 'L', 25, 38),
        ('13457-7', 'H', 130, 200),
    ],
    '13645005': [   # COPD
        ('2744-1', 'L', 7.30, 7.34),
        ('2019-8', 'H', 48, 60),
        ('2703-7', 'L', 60, 78),
    ],
    '195967001': [  # Asthma
        ('2703-7', 'L', 65, 78),
    ],
    '70995007': [   # Pulmonary HTN
        ('30934-4', 'H', 100, 500),
    ],
    '271737000': [  # Anemia
        ('718-7', 'L', 7.0, 11.5),
        ('4544-3', 'L', 22, 35),
        ('2498-4', 'L', 20, 55),
        ('2276-4', 'L', 5, 11),
        ('17849-1', 'H', 1.8, 3.5),
    ],
    '19943007': [   # Cirrhosis
        ('1920-8', 'H', 50, 120),
        ('1742-6', 'H', 60, 150),
        ('1975-2', 'H', 1.5, 5.0),
        ('2885-2', 'L', 2.0, 3.3),
        ('6301-6', 'H', 1.3, 2.5),
    ],
    '34000006': [   # Crohn's
        ('2885-2', 'L', 2.5, 3.4),
        ('1988-5', 'H', 5.0, 30.0),
    ],
    '34742003': [   # Portal HTN
        ('777-3', 'L', 80, 140),
    ],
    '69896004': [   # RA
        ('30341-2', 'H', 25, 60),
        ('1988-5', 'H', 5.0, 25.0),
    ],
    '55464009': [   # Lupus
        ('8061-4', 'H', 160, 1280),
        ('30341-2', 'H', 30, 80),
        ('718-7', 'L', 9.0, 11.5),
    ],
    '40930008': [   # Hypothyroid
        ('3016-3', 'H', 5.0, 15.0),
        ('3024-7', 'L', 0.4, 0.7),
    ],
    '363406005': [  # Colon cancer
        ('2039-6', 'H', 5.0, 50.0),
        ('718-7', 'L', 8.0, 11.5),
    ],
    '128053003': [  # DVT
        ('6301-6', 'H', 1.2, 2.0),
    ],
    '230690007': [  # Stroke
        ('2093-3', 'H', 200, 260),
    ],
}


def q(t):
    return f'{{{V3}}}{t}'


def hl7(fields):
    return '|'.join(str(f) for f in fields)


def load_profiles(path='patient_profiles.json'):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---- CCD generation (parameterized from generate_patients.py) ----

def make_ccd(patient, src):
    """Clone a Synthea base CCD, re-stamping identity for the patient at this source."""
    base_path = os.path.join(CCDS_DIR, src['base_ccd'])
    tree = ET.parse(base_path)
    root = tree.getroot()

    # document-level effective time
    de = root.find('v3:effectiveTime', ns)
    if de is not None:
        de.set('value', '20250315120000')

    pr = root.find('.//v3:recordTarget/v3:patientRole', ns)

    # rewrite source <id>: QE|Source + MRN
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
    mpid_el.set('extension', patient['mpid'])
    # move ids right after existing ids
    for e in (eid_el, mpid_el):
        pr.remove(e)
    insert_at = list(pr).index(ids[-1]) + 1 if ids else 0
    pr.insert(insert_at, mpid_el)
    pr.insert(insert_at, eid_el)

    # address
    addr_el = pr.find('v3:addr', ns)
    if addr_el is not None:
        addr = patient['addr']
        for tag, val in zip(('streetAddressLine', 'city', 'state', 'postalCode'), addr):
            el = addr_el.find(f'v3:{tag}', ns)
            if el is None:
                el = ET.SubElement(addr_el, q(tag))
            el.text = val

    # name / gender / dob
    pat = pr.find('v3:patient', ns)
    nm = pat.find('v3:name', ns)
    givens = nm.findall('v3:given', ns)
    for extra in givens[1:]:
        nm.remove(extra)
    if givens:
        givens[0].text = patient['first_name']
    else:
        ET.SubElement(nm, q('given')).text = patient['first_name']
    fam = nm.find('v3:family', ns)
    if fam is None:
        fam = ET.SubElement(nm, q('family'))
    fam.text = patient['last_name']
    g = pat.find('v3:administrativeGenderCode', ns)
    if g is not None:
        g.set('code', patient['gender'])
    bt = pat.find('v3:birthTime', ns)
    if bt is not None:
        bt.set('value', patient['dob'])

    return ET.tostring(root, encoding='unicode')


# ---- HL7 v2.5.1 ORU^R01 generation ----

def oru_message(patient, src, msgid, collected, obx_rows, order_dt=None):
    """Build a genuine HL7 v2.5.1 ORU^R01 message string (CR-separated segments)."""
    order_dt = order_dt or collected
    qe, fac, mrn = src['qe'], src['source'], src['mrn']
    addr = patient['addr']
    first, last = patient['first_name'], patient['last_name']
    dob, gender, mpid = patient['dob'], patient['gender'], patient['mpid']

    seg = []
    seg.append(hl7(['MSH', '^~\\&', f'LAB_{qe}', fac, 'SHINNY', 'NYS',
                     collected, '', 'ORU^R01^ORU_R01', msgid, 'P', '2.5.1']))
    pid3 = f'{mrn}^^^{qe}&{fac}^MR~{src["eid"]}^^^{qe}^PI~{mpid}^^^NYEC^PI'
    addr_str = f'{addr[0]}^^{addr[1]}^{addr[2]}^{addr[3]}'
    seg.append(hl7(['PID', '1', '', pid3, '', f'{last}^{first}', '', dob, gender,
                     '', '', addr_str]))
    seg.append(hl7(['PV1', '1', 'O', fac]))
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


# ---- TRN (discharge summary) generation ----

def make_trn(patient, src):
    """Build a minimal C-CDA R2.1 discharge summary for parse_ccd() compatibility."""
    admit_date = src['trn_admit_date']
    enc_type = src['trn_enc_type']
    enc_code = ENC_CODES.get(enc_type, '99223')
    facility = src['facility_name']

    admit_y = int(admit_date[:4])
    admit_m = int(admit_date[4:6])
    admit_d = int(admit_date[6:8])
    discharge = date(admit_y, admit_m, admit_d) + timedelta(days=3)
    discharge_str = discharge.strftime('%Y%m%d')

    qe_source = f"{src['qe']}|{src['source']}"
    first = patient['first_name']
    last = patient['last_name']
    dob = patient['dob']
    gender = patient['gender']
    mpid = patient['mpid']
    addr = patient['addr']
    conditions = patient['conditions']

    # Encounter entry XML
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

    # Problems entries XML
    prob_entries = ''
    for i, cond in enumerate(conditions):
        snomed = cond['snomed_code']
        display = cond['display_name']
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

    # Problems table rows for narrative
    prob_rows = ''.join(
        f'\n                <tr><td>{c["display_name"]}</td><td>Active</td></tr>'
        for c in conditions)

    xml = f'''<?xml version='1.0' encoding='UTF-8'?>
<ClinicalDocument xmlns="urn:hl7-org:v3" xmlns:sdtc="urn:hl7-org:sdtc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:hl7-org:v3 http://xreg2.nist.gov:8080/hitspValidation/schema/cdar2c32/infrastructure/cda/C32_CDA.xsd">
  <realmCode code="US"/>
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.1" extension="2015-08-01"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.8" extension="2015-08-01"/>
  <id root="2.16.840.1.113883.19.5" extension="TRN-{src['qe']}-{src['source']}-001" assigningAuthorityName="{qe_source}"/>
  <code code="18842-5" displayName="Discharge summary" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
  <title>Discharge Summary: {first} {last} — {facility}</title>
  <effectiveTime value="{discharge_str}120000"/>
  <confidentialityCode code="N"/>
  <languageCode code="en-US"/>
  <recordTarget>
    <patientRole>
      <id extension="{src['mrn']}" assigningAuthorityName="{qe_source}" root="94f24417-94dd-5693-a38c-b610acf36d41"/>
      <id root="2.16.840.1.113883.3.9999.eid" extension="{src['eid']}" assigningAuthorityName="{src['qe']}"/>
      <id root="2.16.840.1.113883.3.9999.mpid" extension="{mpid}"/>
      <addr use="HP">
        <streetAddressLine>{addr[0]}</streetAddressLine>
        <city>{addr[1]}</city>
        <state>{addr[2]}</state>
        <postalCode>{addr[3]}</postalCode>
      </addr>
      <telecom nullFlavor="NI"/>
      <patient>
        <name>
          <given>{first}</given>
          <family>{last}</family>
        </name>
        <administrativeGenderCode code="{gender}" codeSystem="2.16.840.1.113883.5.1" codeSystemName="HL7 AdministrativeGender"/>
        <birthTime value="{dob}"/>
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
        <softwareName>generate_patients.py</softwareName>
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
              <tbody>{prob_rows}
              </tbody>
            </table>
          </text>{prob_entries}
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>'''
    return xml


# ---- Condition-driven lab panel logic ----

def get_patient_panels(patient, profiles):
    """Return the unique set of lab panel names for this patient, based on conditions."""
    cond_map = profiles['condition_lab_map']
    panels = set()
    for cond in patient['conditions']:
        for p in cond_map.get(cond['snomed_code'], []):
            panels.add(p)
    # Always include BMP as a baseline panel
    panels.add('bmp')
    return sorted(panels)


def generate_lab_value(test_def, patient_conditions, rng):
    """Generate a single lab value. Conditions may push values into abnormal ranges."""
    loinc = test_def['loinc']
    normal_low = test_def['normal_low']
    normal_high = test_def['normal_high']

    # Check if any condition causes this test to be abnormal
    for cond in patient_conditions:
        rules = ABNORMAL_RULES.get(cond['snomed_code'], [])
        for rule_loinc, direction, abn_low, abn_high in rules:
            if rule_loinc == loinc:
                val = round(rng.uniform(abn_low, abn_high), 4)
                flag = 'H' if direction == 'H' else 'L'
                return val, flag

    # Normal value
    val = round(rng.uniform(normal_low, normal_high), 4)
    return val, 'N'


def fmt_val(val, precision):
    """Format a numeric value to the specified decimal precision."""
    if precision == 0:
        return str(int(round(val)))
    return f'{val:.{precision}f}'


def generate_obx_rows(patient, profiles, seed_key):
    """Generate all OBX rows for a patient at one source, driven by conditions."""
    panels = get_patient_panels(patient, profiles)
    panel_defs = profiles['lab_panel_defs']
    rng = random.Random(seed_key)

    # Deduplicate tests (a test can appear in multiple panels)
    seen_loincs = set()
    obx_rows = []
    for panel_name in panels:
        for test_def in panel_defs.get(panel_name, []):
            if test_def['loinc'] in seen_loincs:
                continue
            seen_loincs.add(test_def['loinc'])
            val, flag = generate_lab_value(test_def, patient['conditions'], rng)
            val_str = fmt_val(val, test_def['precision'])
            obx_rows.append((
                test_def['loinc'],
                test_def['test_name'],
                val_str,
                test_def['unit'],
                test_def['ref_range'],
                flag,
            ))
    return obx_rows


def collection_date_for_source(patient_id, source_index):
    """Deterministic collection date spread over 2024-09 to 2025-03."""
    rng = random.Random(f'{patient_id}_{source_index}')
    base = date(2024, 9, 1)
    days = rng.randint(1, 190)
    hour = rng.randint(7, 15)
    minute = rng.choice([0, 15, 30, 45])
    dt = base + timedelta(days=days)
    return f'{dt.year:04d}{dt.month:02d}{dt.day:02d}{hour:02d}{minute:02d}00'


# ---- Patient generation orchestrator ----

def flatten_sources(patient):
    """Flatten qe_assignments into a list of source dicts with 'qe' key added."""
    all_sources = []
    for qa in patient['qe_assignments']:
        qe = qa['qe']
        for src in qa['sources']:
            all_sources.append({**src, 'qe': qe})
    return all_sources


def generate_patient_match_json(patient, all_sources):
    """Generate one Patient Match JSON per QE|SOURCE|MRN, for loading into Verato/MPI.

    Each file is a self-contained POST body for the Patient Match identity API.
    Files land in sample_patients/{patient_id}/mpi/{QE}_{SOURCE}_{MRN}.json
    """
    patient_id = patient['id']
    first = patient['first_name']
    last = patient['last_name']
    dob = patient['dob']
    gender = 'MALE' if patient['gender'] == 'M' else 'FEMALE'
    addr = patient.get('addr', ['', '', '', ''])
    mpid = patient['mpid']

    mpi_dir = os.path.join(OUT, patient_id, 'mpi')
    os.makedirs(mpi_dir, exist_ok=True)
    count = 0

    for src in all_sources:
        qe = src['qe']
        source = src['source']
        mrn = src['mrn']
        eid = src.get('eid', '')
        facility = src.get('facility_name', '')

        doc = {
            "content": {
                "identity": {
                    "addresses": [
                        {
                            "country": "US",
                            "city": addr[1] if len(addr) > 1 else "",
                            "postalCode": addr[3] if len(addr) > 3 else "",
                            "state": addr[2] if len(addr) > 2 else "",
                            "type": "home",
                            "line2": "",
                            "line1": addr[0] if len(addr) > 0 else ""
                        }
                    ],
                    "sources": [
                        {
                            "date": "",
                            "metadata": {
                                "transactionType": "A04",
                                "sourceLoginName": "",
                                "sourceUserName": "",
                                "location": facility
                            },
                            "name": f"{qe}|{source}",
                            "id": mrn
                        }
                    ],
                    "genders": [
                        gender
                    ],
                    "guarantor": [
                        {
                            "zip": "",
                            "lastName": "",
                            "city": "",
                            "suffix": "",
                            "ssn": "",
                            "firstName": "",
                            "phone": "",
                            "dob": "",
                            "addressLine1": "",
                            "middleName": "",
                            "addressLine2": "",
                            "state": "",
                            "relationship": ""
                        }
                    ],
                    "datesOfBirth": [
                        dob
                    ],
                    "phoneNumbers": [
                        {
                            "number": "",
                            "areaCode": "",
                            "extension": "",
                            "countryCode": "",
                            "type": ""
                        }
                    ],
                    "deathDetails": [
                        {
                            "country": "",
                            "deceased": "",
                            "dateOfDeath": "",
                            "city": "",
                            "county": "",
                            "state": ""
                        }
                    ],
                    "custom.attributes": [
                        {
                            "race": "",
                            "ethnicity": "",
                            "maritalstatus": "",
                            "source.hie": qe
                        }
                    ],
                    "emails": [],
                    "names": [
                        {
                            "middle": "",
                            "last": last,
                            "suffix": "",
                            "first": first
                        }
                    ],
                    "ssns": [],
                    "alternateIdentifiers": [
                        {
                            "endDate": "",
                            "type": "QE MPIID",
                            "value": mpid,
                            "issuer": qe,
                            "startDate": ""
                        },
                        {
                            "endDate": "",
                            "type": "ENCOUNTER ID",
                            "value": eid,
                            "issuer": f"{qe}|{source}",
                            "startDate": ""
                        }
                    ],
                    "multipleBirthIndicator": [
                        {
                            "multipleBirthIndicator": ""
                        }
                    ],
                    "healthInsuranceCoverage": [
                        {
                            "sequenceNumber": "",
                            "planType": "",
                            "endDate": "",
                            "payerName": "",
                            "subscriberId": "",
                            "idNumber": "",
                            "groupNumber": "",
                            "effectiveDate": ""
                        }
                    ]
                }
            },
            "trackingId": f"{patient_id}_{qe}_{source}_{mrn}"
        }

        filename = f"{qe}_{source}_{mrn}.json"
        filepath = os.path.join(mpi_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2)
        count += 1

    return count


def generate_patient(patient, profiles):
    """Generate all data (CCD, ORU, TRN, MPI) for one patient."""
    patient_id = patient['id']
    first = patient['first_name']
    last = patient['last_name']
    pat_upper = patient_id.upper()

    patient_dir = os.path.join(OUT, patient_id)
    all_sources = flatten_sources(patient)

    # Create per-QE subfolders
    qe_names = sorted(set(s['qe'].lower() for s in all_sources))
    for qe_lower in qe_names:
        for sub in ('ccda', 'oru-hl7', 'trn'):
            os.makedirs(os.path.join(patient_dir, qe_lower, sub), exist_ok=True)
    os.makedirs(os.path.join(patient_dir, 'mpi'), exist_ok=True)

    ccd_count = oru_count = trn_count = 0

    for idx, src in enumerate(all_sources):
        qe_lower = src['qe'].lower()

        # ---- CCD ----
        xml = make_ccd(patient, src)
        fn = f"{pat_upper}_{src['qe']}_{src['source']}_{src['mrn']}.xml"
        path = os.path.join(patient_dir, qe_lower, 'ccda', fn)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("<?xml version='1.0' encoding='UTF-8'?>\n" + xml)
        ccd_count += 1

        # ---- ORU ----
        collected = collection_date_for_source(patient_id, idx)
        msgid = f'MSG_{src["qe"]}_{src["source"]}_{idx+1:03d}'
        seed_key = f'{patient_id}_{src["qe"]}_{src["source"]}_{idx}'
        obx_rows = generate_obx_rows(patient, profiles, seed_key)
        msg = oru_message(patient, src, msgid, collected, obx_rows)
        oru_fn = f"{pat_upper}_{src['qe']}_{src['source']}_{src['mrn']}_ORU.hl7"
        oru_path = os.path.join(patient_dir, qe_lower, 'oru-hl7', oru_fn)
        with open(oru_path, 'w', encoding='utf-8', newline='') as f:
            f.write(msg)
        oru_count += 1

        # ---- TRN ----
        trn_xml = make_trn(patient, src)
        trn_fn = f"{pat_upper}_{src['qe']}_{src['source']}_{src['mrn']}_TRN.xml"
        trn_path = os.path.join(patient_dir, qe_lower, 'trn', trn_fn)
        with open(trn_path, 'w', encoding='utf-8') as f:
            f.write(trn_xml)
        trn_count += 1

    # ---- MPI CSV ----
    mpi_path = os.path.join(patient_dir, 'mpi', f'{patient_id}_mpi.csv')
    with open(mpi_path, 'w', encoding='utf-8', newline='') as f:
        f.write('qe,source,mrn,eid,mpid,first_name,last_name,dob,gender\n')
        for s in all_sources:
            f.write(f"{s['qe']},{s['source']},{s['mrn']},{s['eid']},{patient['mpid']},"
                    f"{first},{last},{patient['dob']},{patient['gender']}\n")

    # ---- Patient Match JSON (one per QE|SOURCE|MRN) ----
    pm_count = generate_patient_match_json(patient, all_sources)

    return {
        'patient_id': patient_id,
        'ccds': ccd_count,
        'orus': oru_count,
        'trns': trn_count,
        'patient_match': pm_count,
        'qes': qe_names,
        'sources': len(all_sources),
    }


def write_readme(profiles):
    """Generate sample_patients/README.md documenting all patients."""
    lines = [
        '# Sample Patients — Synthetic Cross-Source Test Data\n',
        f'{len(profiles["patients"])} synthetic patients, each spanning multiple SHIN-NY QE',
        'sources for MPI linkage, de-duplication, and per-QE filtering demos.\n',
        'All data is 100% synthetic. Demonstration only.\n',
        '## Patients\n',
    ]

    for p in profiles['patients']:
        total_sources = sum(len(qa['sources']) for qa in p['qe_assignments'])
        qe_count = len(p['qe_assignments'])
        conditions = ', '.join(c['display_name'] for c in p['conditions'])
        dob = p['dob']
        lines.append(f'### {p["first_name"]} {p["last_name"]} (`{p["id"]}`)')
        lines.append(f'  DOB: {dob[:4]}-{dob[4:6]}-{dob[6:]}  Sex: {p["gender"]}  MPID: {p["mpid"]}')
        lines.append(f'  {qe_count} QEs, {total_sources} sources')
        lines.append(f'  Conditions: {conditions}\n')

    lines += [
        '## Folder Structure\n',
        '```',
        'sample_patients/',
        '  {patient_id}/',
        '    {qe_lower}/',
        '      ccda/       C-CDA Continuity of Care Documents',
        '      oru-hl7/    HL7 v2.5.1 ORU^R01 lab messages',
        '      trn/        C-CDA Discharge Summary (TRN) documents',
        '    mpi/',
        '      {patient_id}_mpi.csv           MPI anchor rows (CSV)',
        '      {QE}_{SOURCE}_{MRN}.json       Patient Match API POST body (one per MRN)',
        '```\n',
        '## Generation\n',
        '```',
        'python generate_patients.py                           # all patients',
        'python generate_patients.py --patient marcus_evans    # one patient',
        '```\n',
    ]

    readme_path = os.path.join(OUT, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---- main ----

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic multi-patient data')
    parser.add_argument('--patient', help='Generate just one patient by id (e.g. marcus_evans)')
    args = parser.parse_args()

    profiles = load_profiles()
    patients = profiles['patients']

    if args.patient:
        patients = [p for p in patients if p['id'] == args.patient]
        if not patients:
            print(f'Error: patient "{args.patient}" not found in patient_profiles.json')
            sys.exit(1)

    # Clean output dirs for selected patients
    for p in patients:
        patient_dir = os.path.join(OUT, p['id'])
        if os.path.isdir(patient_dir):
            try:
                shutil.rmtree(patient_dir)
            except PermissionError:
                print(f'  Warning: could not remove {patient_dir} (locked?) - skipping cleanup')

    results = []
    for p in patients:
        result = generate_patient(p, profiles)
        results.append(result)
        print(f'  {result["patient_id"]}: {result["ccds"]} CCDs, {result["orus"]} ORUs, '
              f'{result["trns"]} TRNs, {result["patient_match"]} Patient Match JSONs '
              f'across {len(result["qes"])} QEs ({result["sources"]} sources)')

    write_readme(profiles)

    print(f'\nGenerated {len(results)} patient(s) under ./{OUT}/')
    total_ccds = sum(r['ccds'] for r in results)
    total_orus = sum(r['orus'] for r in results)
    total_trns = sum(r['trns'] for r in results)
    total_pm = sum(r['patient_match'] for r in results)
    print(f'  Total: {total_ccds} CCDs, {total_orus} ORUs, {total_trns} TRNs, {total_pm} Patient Match JSONs')


if __name__ == '__main__':
    main()
