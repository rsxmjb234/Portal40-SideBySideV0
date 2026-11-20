# Report 2: Hospital volume by assigning authority

**Prototype:** [https://main.d3pz3oj6iuj9t4.amplifyapp.com/#hosp-report](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#hosp-report)
**SQL file:** [`SQLExamples/reportonhospitals.sql`](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/SQLExamples/reportonhospitals.sql)
**Part of:** [IN-3737](https://nyec.atlassian.net/browse/IN-3737), reports that let QEs understand the volume of data in PDR by assigning authority.

## What we want

For hospitals, start from Salesforce (SFDC) and look into PDR. Salesforce is the full list
of hospitals, so every hospital appears whether or not it sent anything. A hospital that
Salesforce knows about and PDR shows no data for is the point of the report: it tells a QE
which hospitals to follow up on.

- A **QE filter** at the top, one button per QE.
- Under the filter, the volume each hospital sent in the last 10 days, split by document
  type (CCD and TRN).
- **Hospitals only.** Other organization types are in Report 3.
- **Sorted by assigning authority (AA) total**, highest first, not by hospital total.
- **One hospital on an AA:** a single plain row (hospital, AA code, CCD, TRN, total).
- **Two or more hospitals on one AA:** show the AA as a heading row carrying the counts, with
  each hospital listed beneath it. The counts belong to the AA, because PDR only knows the AA.
- **Hospitals with no data are shown in normal text, not grayed out**, with dashes for the
  counts. They stay at the bottom of the list.
- A badge shows how many assigning authorities are submitting, for example
  "19 of 31 assigning authorities submitting".

## Definitions and rules

| Item | Rule |
|---|---|
| Hospital | A Salesforce record with `record_type = 'Assigning Authority'` and `organization_type = 'Article 28 - Hospital'`. |
| QE | `qe_name` from the Salesforce lookup (`lookup_hospital_assigning_authorities`). |
| Period | The last 10 complete days, ending the day before the inventory snapshot (snapshot is 5 days ago). |
| Document types | CCD and TRN. |
| Match | Salesforce `code` matched to the AA in the S3 key (first path segment), upper-cased and trimmed, regardless of which QE bucket the data landed in. |
| Submission date | Parsed from the S3 key path, not last-modified date. |
| Excluded | Backload, `processed/` and `error/` prefixes, and anything before 2026-03-11 (header-only data). |
| Hixny CCDs | Hixny writes CCDs under `<AA>DOC` (for example `AMHSAMCHDOC`) while TRN and ORU use `<AA>`. The SQL strips the `DOC` suffix for Hixny CCD keys so both land on the same AA. |

## Output columns (SQL)

`qe_name`, `organization_name`, `assigning_authority`, `nys_facility_id`, `ccd_count`,
`trn_count`, `total_docs`. One row per hospital. When several hospitals share an AA, each
of those rows repeats the AA's counts, and the page groups them under one AA heading.

## Open items for requirements

- Add LAB (ORU) as a document type, which the first report already counts.
- Let the user choose the number of days (10 days is fixed in the prototype).
- Decide whether AA-level and hospital-level counts should be split when hospitals share an AA, if PDR ever carries a facility identifier.
- Link each hospital to its Salesforce record using `nys_facility_id`.

## SQL

```sql
/*
Expected cost/run: ~$0.60 (single snapshot partition, ~120 GB)
Expected runtime: ~1-2 minutes

Goal:
- Report ONLY on hospitals (Article 28 - Hospital) for the last 10 complete
  days, counting CCD and TRN per assigning authority.
- ALL hospital AAs in the SFDC lookup are shown, including those with zero
  submissions (shown as 0).
- QE is sourced from lookup_hospital_assigning_authorities.qe_name (SFDC).
- Excludes backload and processed/error prefixes.

Single-snapshot approach:
- Reads ONE recent inventory partition (5 days ago) and filters by submission
  date parsed from the S3 key path. last_modified_date is NOT used for the
  date window because it is re-stamped by routine S3 rewrites (see rules.md).
- 10-day window = [snapshot_day - 10, snapshot_day) — the partial snapshot-
  edge day is excluded so every reported day is complete.
*/

WITH params AS (
    SELECT
        date_add('day', -5, current_date)   AS snapshot_day,     -- window end (exclusive)
        date_add('day', -15, current_date)  AS window_start,     -- 10 days before snapshot
        date_format(
            date_add('day', -5, current_date),
            '%Y-%m-%d-01-00'
        )                                   AS dt_partition
),

-- Full hospital AA list from SFDC lookup.
-- One row per hospital; multiple rows per AA when hospitals share the same code.
hospitals AS (
    SELECT
        upper(trim(code))              AS aa_key,
        trim(code)                     AS assigning_authority,
        trim(organization_name)        AS organization_name,
        trim(qe_name)                  AS qe_name,
        trim(nys_facility_id)          AS nys_facility_id
    FROM pdr_inventory.lookup_hospital_assigning_authorities
    WHERE record_type      = 'Assigning Authority'
      AND organization_type = 'Article 28 - Hospital'
      AND code IS NOT NULL
      AND trim(code) <> ''
),

-- Count CCD and TRN from a single snapshot, using submission date from key path.
-- HIXNY normalisation: CCD keys use <AA>DOC as the first path segment; strip the
-- DOC suffix so HIXNY CCD counts join correctly to the hospital AA lookup.
actual AS (
    SELECT
        CASE
            WHEN lower(i.bucket) LIKE '%hixny%'
             AND regexp_like(lower(i.key), '(^|/)ccd(/|$)')
             AND upper(trim(split_part(i.key, '/', 1))) LIKE '%DOC'
            THEN regexp_replace(upper(trim(split_part(i.key, '/', 1))), 'DOC$', '')
            ELSE upper(trim(split_part(i.key, '/', 1)))
        END AS aa_key,
        count_if(regexp_like(lower(i.key), '(^|/)ccd(/|$)')) AS ccd_count,
        count_if(regexp_like(lower(i.key), '(^|/)trn(/|$)')) AS trn_count
    FROM pdr_inventory.pdr_inventory_prod_data_all i
    CROSS JOIN params p
    WHERE
        i.dt = p.dt_partition
        AND i.bucket LIKE 'nyec-pdr-prod-%'
        AND i.is_latest = true
        AND coalesce(i.is_delete_marker, false) = false
        -- Scan reducer; real floor is applied on submission_date in the WHERE below
        AND i.last_modified_date >= timestamp '2026-03-11 00:00:00'
        -- GLOBAL RULE: exclude processed/ and error/ workflow-prefix objects
        AND NOT regexp_like(lower(i.key), '^(processed|error)/')
        -- Exclude backload
        AND NOT regexp_like(lower(i.key), '(^|/)backload(/|$)')
        AND (
            regexp_like(lower(i.key), '(^|/)ccd(/|$)')
            OR regexp_like(lower(i.key), '(^|/)trn(/|$)')
        )
        -- Submission date window (from key path, never changes on rewrite)
        AND TRY(date_parse(
                regexp_extract(i.key, '(?i)(?:ccd|trn)/(\d{4}/[A-Za-z]{3}/\d{2})/', 1),
                '%Y/%b/%d'
            )) >= p.window_start
        AND TRY(date_parse(
                regexp_extract(i.key, '(?i)(?:ccd|trn)/(\d{4}/[A-Za-z]{3}/\d{2})/', 1),
                '%Y/%b/%d'
            )) < p.snapshot_day
    GROUP BY 1
)

SELECT
    h.qe_name,
    h.organization_name,
    h.assigning_authority,
    h.nys_facility_id,
    coalesce(a.ccd_count, 0)                                     AS ccd_count,
    coalesce(a.trn_count, 0)                                     AS trn_count,
    coalesce(a.ccd_count, 0) + coalesce(a.trn_count, 0)         AS total_docs
FROM hospitals h
LEFT JOIN actual a ON h.aa_key = a.aa_key
ORDER BY total_docs DESC, h.assigning_authority ASC, h.organization_name ASC;
```

## Prototype notes

- The prototype is a static page. Results were produced by running the SQL above in Athena
  and saving the output; there is no Lambda yet. In production the page should call a
  service (for example a Lambda) that runs the same SQL and returns the rows.
- The date range text on the page is typed in by hand in the prototype. In production it
  must be computed from the snapshot date the query used.
- Security, authentication and hosting are out of scope here. Developers will decide those.
- All report SQL lives in [`SQLExamples/`](https://github.com/rsxmjb234/Portal40-SideBySideV0/tree/main/SQLExamples). Page code is
  [`build_home.py`](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/build_home.py); data loaders are
  [`build_reports.py`](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/build_reports.py).
