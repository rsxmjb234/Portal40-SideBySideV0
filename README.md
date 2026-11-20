# Portal 4.0 — QE PDR Viewer

Five Qualified Entity portal views rendering the same synthetic patient (Marcus Evans) in each QE's own style, plus volume reports showing real PDR data by assigning authority.

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
Marcus Evans — 5 QEs × 3 sources each = 15 CCDs + 15 ORUs + 15 TRNs (45 files). Generated from 10 Synthea base records, re-stamped with Marcus's identity.

## Build

```powershell
# Generate Marcus data (45 files into marcus_bundle/)
python.exe build_marcus_bundle.py

# Generate report data files (hosp_data.js, nonhosp_data.js, adt_data.js)
python.exe build_reports.py

# Build all 5 QE views + index.html
python.exe build_home.py
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
build_marcus_bundle.py     Generates 45 synthetic data files
build_reports.py           Generates JS data from Athena JSON
athena_hello_world.py      Athena query runner
deploy_amplify.ps1         Zip + upload to AWS Amplify
ccds/                      10 Synthea base CCD templates
marcus_bundle/             Per-QE patient data (5 QEs × 3 sources)
SQLExamples/               4 SQL queries + saved JSON results
docs/                      Report specs, plans
```
