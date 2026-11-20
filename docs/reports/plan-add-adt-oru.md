# Plan: Add ADT and ORU (LAB) to all volume reports

## Current state

| Report | CCD | TRN | LAB/ORU | ADT |
|---|---|---|---|---|
| 1. Volume by QE (28-day) | ✅ | ✅ | ✅ | ❌ |
| 2. Hospital Volume (10-day) | ✅ | ✅ | ❌ | ❌ |
| 3. Non-Hospital Sources (10-day) | ✅ | ✅ | ❌ | ❌ |

Report 1 already counts LAB. Reports 2 and 3 only count CCD + TRN.

None of the reports count ADT.

## Target state

| Report | CCD | TRN | LAB/ORU | ADT |
|---|---|---|---|---|
| 1. Volume by QE (28-day) | ✅ | ✅ | ✅ | ✅ |
| 2. Hospital Volume (10-day) | ✅ | ✅ | ✅ | ✅ |
| 3. Non-Hospital Sources (10-day) | ✅ | ✅ | ✅ | ✅ |

## Document types in PDR S3 keys

The S3 key path structure is `<AA>/<type>/YYYY/Mon/DD/...` where `<type>` is one of:
- `ccd` — C-CDA clinical documents
- `trn` — transaction/discharge summaries
- `lab` (also `oru`) — laboratory results (HL7 ORU feeds)
- `adt` — admit/discharge/transfer messages

## What needs to change

### 1. SQL: Add LAB and ADT columns to Reports 2 and 3

**reportonhospitals.sql** changes:
- In the `actual` CTE WHERE clause, expand the filter to also match `lab|oru` and `adt` paths
- Add `count_if` columns: `lab_count` (matching `lab` or `oru` paths) and `adt_count`
- Update the submission date regex to include `lab|oru|adt` pattern
- Update the SELECT to include `lab_count`, `adt_count`, and revise `total_docs`
- Apply the same HIXNY DOC-suffix normalisation for LAB and ADT keys if applicable

**reportonnonhospitals.sql** — same changes as above.

**DailyVolumeByQE-28Day-SingleSnapshot-ExcludeOrphans.sql** changes:
- Add `adt` to the data_type CASE expression (currently only handles ccd, trn, lab)
- Add `adt_in_pdr` to the output SELECT
- The submission date regex already matches `ccd|trn|lab|oru` — add `adt`

### 2. ADT: Use static placeholder for now

There's already an ADT page loaded to Amplify. For now, the ADT column in reports will show real counts from the SQL (ADT data exists in PDR S3), but any drill-down or detail view can link to the static ADT page as a placeholder until a dynamic ADT viewer is built.

If ADT data in PDR turns out to be minimal or zero for some QEs, that's fine — the column shows 0 just like hospitals with no CCD data.

### 3. Re-run queries and regenerate data files

After updating SQL:
1. EXPLAIN each query (free) to validate syntax
2. Run each query (estimated ~47 GB per query, ~$0.25 each)
3. Save results to `SQLExamples/*.json`
4. Run `python.exe build_reports.py` to regenerate `hosp_data.js` and `nonhosp_data.js`

### 4. Update build_reports.py

- `hosp_data.js`: add `lab` and `adt` fields to each row (currently only `ccd` and `trn`)
- `nonhosp_data.js`: same — add `lab` and `adt`

### 5. Update build_home.py — HTML and render scripts

**Report 1 (Volume by QE bar chart):**
- Add an ADT bar segment (new color) to the stacked bar
- Add ADT to the legend
- Update the hardcoded data array with ADT counts (or re-run the query)

**Report 2 (Hospital Volume table):**
- Add `LAB` and `ADT` columns to the table header
- Update the JS render function to display 4 doc-type columns instead of 2
- Update the total calculation: `ccd + trn + lab + adt`
- Update the AA-group heading to span the extra columns

**Report 3 (Non-Hospital Sources table):**
- Same as Report 2: add LAB and ADT columns, update totals

**Subtitle text:**
- Change "CCD + TRN" → "CCD + TRN + LAB + ADT" in the report subtitles

### 6. Update specs and Jira

- Update `docs/reports/01-volume-by-qe.md`, `02-hospital-volume.md`, `03-non-hospital-sources.md`
- Update IN-3737 description to reflect the 4 document types

### 7. Deploy

- `python.exe build_home.py` to regenerate all pages
- `deploy_amplify.ps1` to push to Amplify

## Estimated cost

- 3 Athena queries × ~47 GB each = ~141 GB total ≈ $0.75

## Risk

- ADT data in PDR may be sparse or concentrated in certain QEs. The counts will be what they are — zeros are fine and informative.
- The HIXNY DOC-suffix issue may or may not apply to LAB and ADT keys. Need to check with a quick query or just apply the normalisation broadly.

## Order of work

1. Update the 3 SQL files
2. EXPLAIN all 3 (free)
3. Run all 3, save JSON
4. Update `build_reports.py` to include lab + adt fields
5. Update `build_home.py` — HTML cards, table headers, render JS
6. `python.exe build_reports.py` → `python.exe build_home.py` → verify locally
7. `git add + commit + push`
8. Deploy to Amplify
9. Update specs and Jira
