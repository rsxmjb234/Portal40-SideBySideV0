#!/usr/bin/env python3
"""Lambda vs local comparison tests for Marcus Evans.

Parses all Marcus Evans CCD, TRN, and ORU files using:
  1. The local ccda_parse.py pipeline (same orchestration as build_smart.py)
  2. The deployed pdr-ccd-parser-dev Lambda (invoked via AWS CLI per QE,
     then merged — per-QE batching avoids the 6 MB sync payload limit)

Compares outputs field by field and reports PASS/FAIL per section.
Exit code 0 if all sections pass, 1 if any fail.
"""
import sys
import os
import glob
import json
import base64
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Setup — add repo root to sys.path so 'import ccda_parse' works
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import ccda_parse

MARCUS_DIR = os.path.join(REPO_ROOT, 'sample_patients', 'marcus_evans')
QES = ['bronx', 'healtheconn', 'healthelink', 'healthix', 'hixny']

LAMBDA_FUNCTION = 'pdr-ccd-parser-dev'
AWS_PROFILE = '304507007699_AWSPowerUserAccess'
AWS_REGION = 'us-east-1'


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_files():
    """Collect all CCD, TRN, and ORU file paths for Marcus Evans across 5 QEs."""
    ccds, trns, orus = [], [], []
    for qe in QES:
        qe_dir = os.path.join(MARCUS_DIR, qe)
        ccds.extend(sorted(glob.glob(os.path.join(qe_dir, 'ccda', '*.xml'))))
        trns.extend(sorted(glob.glob(os.path.join(qe_dir, 'trn', '*.xml'))))
        orus.extend(sorted(glob.glob(os.path.join(qe_dir, 'oru-hl7', '*.hl7'))))
    return ccds, trns, orus


def files_for_qe(qe, ccd_files, trn_files, oru_files):
    """Filter file lists to those belonging to a given QE."""
    qe_dir = os.path.join(MARCUS_DIR, qe)
    return (
        [f for f in ccd_files if f.startswith(qe_dir)],
        [f for f in trn_files if f.startswith(qe_dir)],
        [f for f in oru_files if f.startswith(qe_dir)],
    )


# ---------------------------------------------------------------------------
# Local parse — same orchestration as build_smart.py
# ---------------------------------------------------------------------------

def local_parse(ccd_files, trn_files, oru_files):
    """Run the local parsing pipeline: parse_ccd each CCD and TRN file,
    init oru=[] on each, call load_oru_hl7, call merge_by_person."""
    all_files = ccd_files + trn_files
    patients = [ccda_parse.parse_ccd(f) for f in all_files]

    # init oru=[] on each parsed record (matches build_smart.py)
    for P in patients:
        P['oru'] = []

    # load ORU HL7 messages per QE directory
    for qe in QES:
        oru_pattern = os.path.join(MARCUS_DIR, qe, 'oru-hl7', '*.hl7')
        ccda_parse.load_oru_hl7(patients, oru_pattern)

    merged = ccda_parse.merge_by_person(patients)
    return merged[0] if merged else {}


# ---------------------------------------------------------------------------
# Lambda invocation helpers
# ---------------------------------------------------------------------------

def invoke_lambda_for_qe(ccd_files, trn_files, oru_files, qe_label):
    """Invoke the Lambda with one QE's documents and return the parsed dict."""

    def encode_file(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('ascii')

    event = {
        'documents': {
            'ccds': [encode_file(f) for f in ccd_files],
            'orus': [encode_file(f) for f in oru_files],
            'trns': [encode_file(f) for f in trn_files],
        }
    }

    payload_path = os.path.join(tempfile.gettempdir(), f'lambda_payload_{qe_label}.json')
    output_path = os.path.join(tempfile.gettempdir(), f'lambda_output_{qe_label}.json')

    with open(payload_path, 'w', encoding='utf-8') as f:
        json.dump(event, f)

    payload_mb = os.path.getsize(payload_path) / (1024 * 1024)
    print(f"    {qe_label}: {len(ccd_files)} CCDs + {len(trn_files)} TRNs + "
          f"{len(oru_files)} ORUs, payload {payload_mb:.2f} MB")

    try:
        cmd = [
            'aws', 'lambda', 'invoke',
            '--function-name', LAMBDA_FUNCTION,
            '--cli-binary-format', 'raw-in-base64-out',
            '--payload', f'fileb://{payload_path}',
            '--profile', AWS_PROFILE,
            '--region', AWS_REGION,
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"    Lambda invoke FAILED for {qe_label} (exit code {result.returncode})")
            print(f"    stderr: {result.stderr}")
            sys.exit(1)

        # Check for FunctionError (timeout, OOM, etc.)
        cli_out = result.stdout.strip()
        if cli_out:
            cli_meta = json.loads(cli_out)
            if 'FunctionError' in cli_meta:
                print(f"    Lambda FunctionError for {qe_label}: {cli_meta['FunctionError']}")
                with open(output_path, 'r', encoding='utf-8') as f:
                    print(f"    Response: {f.read()[:500]}")
                sys.exit(1)

        with open(output_path, 'r', encoding='utf-8') as f:
            response = json.load(f)

        if response.get('statusCode') != 200:
            print(f"    Lambda returned statusCode {response.get('statusCode')} for {qe_label}")
            err = response.get('body', {})
            if isinstance(err, dict):
                print(f"    Error: {err.get('error', 'unknown')}")
            sys.exit(1)

        return response['body']

    finally:
        for p in (payload_path, output_path):
            if os.path.exists(p):
                os.unlink(p)


def lambda_parse(ccd_files, trn_files, oru_files):
    """Invoke the Lambda per QE (to stay under the 6 MB sync payload limit),
    then merge the per-QE results using merge_by_person — identical to how
    the local pipeline merges across QEs."""
    per_qe_results = []

    for qe in QES:
        qe_ccds, qe_trns, qe_orus = files_for_qe(qe, ccd_files, trn_files, oru_files)
        result = invoke_lambda_for_qe(qe_ccds, qe_trns, qe_orus, qe)
        per_qe_results.append(result)

    # Merge the 5 per-QE Lambda results the same way the local pipeline
    # merges documents: merge_by_person groups by person_key, concatenates
    # lists, de-duplicates, and reconciles ORU vs CCD labs.
    merged = ccda_parse.merge_by_person(per_qe_results)
    return merged[0] if merged else {}


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(local, lam):
    """Compare local and Lambda outputs field by field.
    Returns list of (section, passed, details)."""
    results = []

    # --- demographics ---
    demo_fields = ['given', 'family', 'gender', 'dob', 'age']
    demo_pass = True
    demo_details = []
    for field in demo_fields:
        lv = str(local.get(field, ''))
        rv = str(lam.get(field, ''))
        if lv != rv:
            demo_pass = False
            demo_details.append(f"    {field}: local={lv!r} vs lambda={rv!r}")
    results.append(('demographics', demo_pass, demo_details))

    # --- mrn_list (count + sorted contents) ---
    def mrn_key(m):
        return (m.get('qe', ''), m.get('source', ''), m.get('mrn', ''))

    local_mrns = sorted(local.get('mrn_list', []), key=mrn_key)
    lam_mrns = sorted(lam.get('mrn_list', []), key=mrn_key)
    mrn_pass = (len(local_mrns) == len(lam_mrns)
                and all(mrn_key(a) == mrn_key(b)
                        for a, b in zip(local_mrns, lam_mrns)))
    mrn_details = []
    if not mrn_pass:
        mrn_details.append(f"    count: local={len(local_mrns)} vs lambda={len(lam_mrns)}")
        local_set = {mrn_key(m) for m in local_mrns}
        lam_set = {mrn_key(m) for m in lam_mrns}
        for x in sorted(local_set - lam_set):
            mrn_details.append(f"    only in local: {x}")
        for x in sorted(lam_set - local_set):
            mrn_details.append(f"    only in lambda: {x}")
    results.append(('mrn_list', mrn_pass, mrn_details))

    # --- problems (count + sorted names) ---
    local_probs = sorted(p['name'] for p in local.get('problems', []))
    lam_probs = sorted(p['name'] for p in lam.get('problems', []))
    prob_pass = local_probs == lam_probs
    prob_details = []
    if not prob_pass:
        prob_details.append(f"    count: local={len(local_probs)} vs lambda={len(lam_probs)}")
        for x in sorted(set(local_probs) - set(lam_probs)):
            prob_details.append(f"    only in local: {x}")
        for x in sorted(set(lam_probs) - set(local_probs)):
            prob_details.append(f"    only in lambda: {x}")
    results.append(('problems', prob_pass, prob_details))

    # --- meds (count + sorted names) ---
    local_meds = sorted(m['name'] for m in local.get('meds', []))
    lam_meds = sorted(m['name'] for m in lam.get('meds', []))
    med_pass = local_meds == lam_meds
    med_details = []
    if not med_pass:
        med_details.append(f"    count: local={len(local_meds)} vs lambda={len(lam_meds)}")
        for x in sorted(set(local_meds) - set(lam_meds)):
            med_details.append(f"    only in local: {x}")
        for x in sorted(set(lam_meds) - set(local_meds)):
            med_details.append(f"    only in lambda: {x}")
    results.append(('meds', med_pass, med_details))

    # --- labs (panel count + total component count) ---
    local_panels = len(local.get('labs', []))
    lam_panels = len(lam.get('labs', []))
    local_comps = sum(len(p['comps']) for p in local.get('labs', []))
    lam_comps = sum(len(p['comps']) for p in lam.get('labs', []))
    lab_pass = local_panels == lam_panels and local_comps == lam_comps
    lab_details = []
    if not lab_pass:
        lab_details.append(f"    panels: local={local_panels} vs lambda={lam_panels}")
        lab_details.append(f"    total components: local={local_comps} vs lambda={lam_comps}")
    results.append(('labs', lab_pass, lab_details))

    # --- oru (count + sorted test names) ---
    local_oru = sorted(o['test'] for o in local.get('oru', []))
    lam_oru = sorted(o['test'] for o in lam.get('oru', []))
    oru_pass = local_oru == lam_oru
    oru_details = []
    if not oru_pass:
        oru_details.append(f"    count: local={len(local_oru)} vs lambda={len(lam_oru)}")
        for x in sorted(set(local_oru) - set(lam_oru)):
            oru_details.append(f"    only in local: {x}")
        for x in sorted(set(lam_oru) - set(local_oru)):
            oru_details.append(f"    only in lambda: {x}")
    results.append(('oru', oru_pass, oru_details))

    # --- simple counts: vitals, imms, procs, encs, allergies ---
    for section in ('vitals', 'imms', 'procs', 'encs', 'allergies'):
        lc = len(local.get(section, []))
        rc = len(lam.get(section, []))
        passed = lc == rc
        details = []
        if not passed:
            details.append(f"    count: local={lc} vs lambda={rc}")
        results.append((section, passed, details))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('=' * 60)
    print('Lambda vs Local Comparison Test - Marcus Evans')
    print('=' * 60)

    # Collect files
    ccds, trns, orus = collect_files()
    print(f'\nFiles found: {len(ccds)} CCDs, {len(trns)} TRNs, {len(orus)} ORUs')

    if not ccds:
        print('ERROR: No CCD files found under', MARCUS_DIR)
        sys.exit(1)

    # --- Local parse ---
    print('\n--- Running local parse ---')
    local_result = local_parse(ccds, trns, orus)
    print(f"  {local_result['given']} {local_result['family']}: "
          f"{len(local_result.get('problems', []))} problems, "
          f"{len(local_result.get('meds', []))} meds, "
          f"{len(local_result.get('mrn_list', []))} MRNs, "
          f"{len(local_result.get('oru', []))} ORU results")

    # --- Lambda parse (per QE, then merge) ---
    print('\n--- Invoking Lambda (per QE to fit 6 MB sync limit) ---')
    lambda_result = lambda_parse(ccds, trns, orus)
    print(f"\n  Merged Lambda result: "
          f"{lambda_result.get('given', '')} {lambda_result.get('family', '')}: "
          f"{len(lambda_result.get('problems', []))} problems, "
          f"{len(lambda_result.get('meds', []))} meds, "
          f"{len(lambda_result.get('mrn_list', []))} MRNs, "
          f"{len(lambda_result.get('oru', []))} ORU results")

    # --- Comparison ---
    print('\n--- Comparison Results ---\n')
    results = compare(local_result, lambda_result)

    all_pass = True
    for section, passed, details in results:
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f'  [{status}] {section}')
        for d in details:
            print(d)

    print('\n' + '=' * 60)
    if all_pass:
        print('RESULT: ALL SECTIONS PASS - Lambda and local produce identical results')
    else:
        print('RESULT: SOME SECTIONS FAILED - see details above')
    print('=' * 60)

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
