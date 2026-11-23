# Portal 4.0 — QE PDR Viewer

Five Qualified Entity portal views rendering synthetic patients in each QE's own style, plus volume reports showing real PDR data by assigning authority. 10 patient archetypes available, led by Marcus Evans.

## Live site

**https://main.d3pz3oj6iuj9t4.amplifyapp.com**

## What's here

### QE Portal Views (5 live)
| QE | Style | Renderer |
|---|---|---|
| Hixny | SMART on FHIR | `build_smart.py` |
| HEALTHeLINK | Fusion | `build_chart.py` |
| Healthix | SMART on FHIR | `build_smart.py` (reload) |
| HealtheConnections | HEC Portal | `build_healtheconn.py` |
| Bronx RHIO | IMAT Solutions | `build_bronx.py` |

Each QE view shows **only that QE's data** — different MRNs, encounters, labs, and medications. The same patient identity and shared conditions appear in every view, but the clinical data is partitioned per QE, just like a real portal.

### Volume Reports (4 live)
1. **Volume by QE** — CCD + TRN + LAB + ADT per QE (28-day + ADT snapshot)
2. **Hospital Volume** — Salesforce hospitals with all 4 doc types, AA grouping, chain names
3. **Non-Hospital Sources** — PDR-first view with "Not in SFDC" tags
4. **ADT Volume by Facility** — from `lookup_adt_counts` snapshot

### Synthetic Patient Data
10 patient archetypes defined in `patient_profiles.json`, each with clinically coherent conditions, labs, and encounters. Patient data is generated into `sample_patients/{patient_id}/{qe}/{ccda,oru-hl7,trn}/` by `generate_patients.py`. Marcus Evans is patient #1 (default) with 5 QEs × 3 sources each.

## Build

```powershell
# Generate patient data (10 patients into sample_patients/)
python.exe generate_patients.py

# Generate report data files (hosp_data.js, nonhosp_data.js, adt_data.js)
python.exe build_reports.py

# Build all 5 QE views + index.html (default patient: marcus_evans)
python.exe build_home.py

# Build for a different patient
python.exe build_home.py cardiac_patient
```

## Deploy

Requires the `304507007699_AWSPowerUserAccess` sandbox profile:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy_amplify.ps1
```

## Refresh Athena reports

Requires the `220065406231_pdr-nyec-program-team-PROD` profile:

```powershell
# Run the SQL, save results to SQLExamples/*.json
python.exe athena_hello_world.py --check   # verify login
# Then re-run each query and rebuild:
python.exe build_reports.py
python.exe build_home.py
```

## Jira

- **IN-3633** — PDR Data Validation Portal (master ticket)
- **IN-3737** — Volume reports by AA

## Structure

```
build_home.py              Orchestrator — builds 5 QE views + index.html
build_smart.py             Hixny / Healthix renderer (SMART on FHIR)
build_chart.py             HEALTHeLINK renderer (Fusion)
build_bronx.py             Bronx RHIO renderer (IMAT)
build_healtheconn.py       HealtheConnections renderer (HEC Portal)
ccda_parse.py              Shared C-CDA + ORU parser, merge, dedup
bug_widget.py              Missing-data logging widget
generate_patients.py       Generates synthetic patient data for all 10 patients
patient_profiles.json      Defines 10 patient archetypes (conditions, QE assignments)
build_reports.py           Generates JS data from Athena JSON
athena_hello_world.py      Athena query runner
deploy_amplify.ps1         Zip + upload to AWS Amplify
ccds/                      10 Synthea base CCD templates
sample_patients/           Per-patient, per-QE data (10 patients × 3-5 QEs × 3 sources)
SQLExamples/               4 SQL queries + saved JSON results
docs/                      Report specs, plans
```
