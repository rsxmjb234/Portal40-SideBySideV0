/*
Expected cost/run: ~$0.25 (single snapshot partition, ~47 GB)
Expected runtime: ~1-2 minutes

Goal:
- Report on every NON-hospital source in PDR for the last 10 complete days,
  counting CCD, TRN, LAB (ORU), and ADT per assigning authority (AA) per QE bucket.
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
        count_if(regexp_like(lower(i.key), '(^|/)trn(/|$)')) AS trn_count,
        count_if(regexp_like(lower(i.key), '(^|/)(lab|oru)(/|$)')) AS lab_count,
        count_if(regexp_like(lower(i.key), '(^|/)adt(/|$)')) AS adt_count
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
            OR regexp_like(lower(i.key), '(^|/)(lab|oru)(/|$)')
            OR regexp_like(lower(i.key), '(^|/)adt(/|$)')
        )
        -- Submission date window (from key path, never changes on rewrite)
        AND TRY(date_parse(
                regexp_extract(i.key, '(?i)(?:ccd|trn|lab|oru|adt)/(\d{4}/[A-Za-z]{3}/\d{2})/', 1),
                '%Y/%b/%d'
            )) >= p.window_start
        AND TRY(date_parse(
                regexp_extract(i.key, '(?i)(?:ccd|trn|lab|oru|adt)/(\d{4}/[A-Za-z]{3}/\d{2})/', 1),
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
    a.lab_count,
    a.adt_count,
    a.ccd_count + a.trn_count + a.lab_count + a.adt_count AS total_docs
FROM actual a
LEFT JOIN sfdc s         ON a.aa_key = s.aa_key
LEFT JOIN hospital_aas h ON a.aa_key = h.aa_key
WHERE h.aa_key IS NULL
ORDER BY total_docs DESC, a.qe ASC, a.aa_key ASC;
