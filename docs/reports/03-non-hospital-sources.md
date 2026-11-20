# Report 3: Non-hospital sources in PDR

**Prototype:** [https://main.d3pz3oj6iuj9t4.amplifyapp.com/#nonhosp-report](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#nonhosp-report)
**SQL file:** [`SQLExamples/reportonnonhospitals.sql`](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/SQLExamples/reportonnonhospitals.sql)
**Part of:** [IN-3737](https://nyec.atlassian.net/browse/IN-3737), reports that let QEs understand the volume of data in PDR by assigning authority.

## What we want

This is the inverse of the hospital report. For hospitals we start from the Salesforce list.
For everything else we start from **all data in PDR** and look into Salesforce for a name and
type. The report answers: which non-hospital sources are sending data, how much, and do we
know who they are?

- A **QE filter** at the top, one button per QE.
- One row per assigning authority with data in the last 10 days, showing source name, AA code,
  organization type, CCD, TRN and total, sorted by total.
- **Name and type come from Salesforce when the AA is there.** When it is not, the row shows a
  **"Not in SFDC"** tag. These are sources sending data that Salesforce does not know about.
- **Hospitals are excluded.** Any AA that Salesforce lists as `Article 28 - Hospital` is in Report 2.
- Only AAs with data appear. There is no "all of Salesforce" list on this side.
- A badge shows the number of sources and how many are not in Salesforce, for example
  "475 sources with data, 383 not in SFDC".
- If one AA maps to several Salesforce organizations, show the first name and "+N more".

## Definitions and rules

| Item | Rule |
|---|---|
| Population | Every AA with CCD or TRN in PDR in the period, per QE bucket, except hospital AAs. |
| Hospital AA | Salesforce `organization_type = 'Article 28 - Hospital'`. Excluded here. |
| Name and type | From `lookup_hospital_assigning_authorities` for any organization type. Several types on one AA are joined with " / ". |
| QE | From the S3 bucket name (`nyec-pdr-prod-<qe>`). The `techbd` and `tbx` buckets are HEALTHeLINK and are reported as `healthelink`. |
| Period | The last 10 complete days, ending the day before the inventory snapshot (snapshot is 5 days ago). |
| Document types | CCD and TRN. |
| Excluded | Backload, `processed/` and `error/` prefixes, and anything before 2026-03-11. |
| Hixny CCDs | The `DOC` suffix is stripped from Hixny CCD keys, as in Report 2. |

## Output columns (SQL)

`qe`, `assigning_authority`, `sfdc_status` ("In SFDC" or "Not in SFDC"), `organization_type`,
`organization_name`, `sfdc_org_count`, `ccd_count`, `trn_count`, `total_docs`.

## Open items for requirements

- Many sources are not in Salesforce (2,875 of 3,276 rows in the prototype run). Decide who owns
  getting them registered, and whether this report should offer a "Not in SFDC only" filter.
- Add a column or filter for organization type (nursing home, diagnostic and treatment center, hospice, and so on).
- Add LAB (ORU) as a document type.
- Decide how to treat an AA that appears in more than one QE bucket (it is one row per bucket today).

## SQL

```sql
/*
Expected cost/run: ~$0.25 (single snapshot partition, ~47 GB)
Expected runtime: ~1-2 minutes

Goal:
- Report on every NON-hospital source in PDR for the last 10 complete days,
  counting CCD and TRN per assigning authority (AA) per QE bucket.
- This is the inverse of reportonhospitals.sql. Hospitals start from the
  Salesforce (SFDC) list and look right into PDR. This report starts from
  PDR ("all data that landed") and looks LEFT into SFDC for a name/type.
- An AA that has data in PDR but is not in SFDC is still shown, labeled
  'Not in SFDC'.
- Any AA that SFDC lists as 'Article 28 - Hospital' is excluded (those are
  covered by reportonhospitals.sql).
- Only AAs with data appear (there is no "all of SFDC" list on this side).
- QE comes from the S3 bucket name (nyec-pdr-prod-<qe>), since AAs that are
  not in SFDC have no SFDC QE. HEALTHeLINK = the TechByDesign bucket
  (techbd / tbx), so that bucket is reported as 'healthelink'.
- Excludes backload and processed/error prefixes.

Single-snapshot approach (same as reportonhospitals.sql):
- Reads ONE recent inventory partition (5 days ago) and filters by submission
  date parsed from the S3 key path, not last_modified_date (re-stamped by
  routine S3 rewrites).
- 10-day window = [snapshot_day - 10, snapshot_day) so every reported day is
  complete.

HIXNY: CCD keys use <AA>DOC as the first path segment; the DOC suffix is
stripped so Hixny CCD and TRN counts land on the same AA.
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

-- AAs SFDC says are hospitals. These are excluded from this report.
hospital_aas AS (
    SELECT DISTINCT upper(trim(code)) AS aa_key
    FROM pdr_inventory.lookup_hospital_assigning_authorities
    WHERE record_type       = 'Assigning Authority'
      AND organization_type = 'Article 28 - Hospital'
      AND code IS NOT NULL
      AND trim(code) <> ''
),

-- SFDC name/type per AA (any organization type). One row per AA.
sfdc AS (
    SELECT
        upper(trim(code))                                                   AS aa_key,
        array_join(array_sort(array_distinct(array_agg(trim(organization_type)))), ' / ')
                                                                            AS organization_type,
        min(trim(organization_name))                                        AS organization_name,
        count(DISTINCT trim(organization_name))                             AS org_count
    FROM pdr_inventory.lookup_hospital_assigning_authorities
    WHERE record_type = 'Assigning Authority'
      AND code IS NOT NULL
      AND trim(code) <> ''
    GROUP BY upper(trim(code))
),

-- ALL data in PDR for the window, per QE bucket + AA.
actual AS (
    SELECT
        -- HEALTHeLINK data lands in the TechByDesign bucket (techbd / tbx).
        CASE
            WHEN regexp_replace(regexp_replace(i.bucket, '^nyec-pdr-prod-', ''), '-part2$', '') IN ('techbd', 'tbx')
            THEN 'healthelink'
            ELSE regexp_replace(regexp_replace(i.bucket, '^nyec-pdr-prod-', ''), '-part2$', '')
        END AS qe,
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
        -- Scan reducer; real floor is applied on submission_date below
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
    GROUP BY 1, 2
)

SELECT
    a.qe,
    a.aa_key                                              AS assigning_authority,
    CASE WHEN s.aa_key IS NULL THEN 'Not in SFDC' ELSE 'In SFDC' END AS sfdc_status,
    coalesce(s.organization_type, 'Not in SFDC')          AS organization_type,
    coalesce(s.organization_name, 'Not in SFDC')          AS organization_name,
    coalesce(s.org_count, 0)                              AS sfdc_org_count,
    a.ccd_count,
    a.trn_count,
    a.ccd_count + a.trn_count                             AS total_docs
FROM actual a
LEFT JOIN sfdc s         ON a.aa_key = s.aa_key
LEFT JOIN hospital_aas h ON a.aa_key = h.aa_key
WHERE h.aa_key IS NULL
ORDER BY total_docs DESC, a.qe ASC, a.aa_key ASC;
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
