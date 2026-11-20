/*
Expected cost/run: ~$0.60 (single snapshot partition, ~47 GB)
Expected runtime: ~1-2 minutes

Goal:
- Report ONLY on hospitals (Article 28 - Hospital) for the last 10 complete
  days, counting CCD, TRN, LAB (ORU), and ADT per assigning authority.
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
    SELECT DISTINCT
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
        -- Scan reducer; real floor is applied on submission_date in the WHERE below
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
    GROUP BY 1
)

SELECT
    h.qe_name,
    h.organization_name,
    h.assigning_authority,
    h.nys_facility_id,
    coalesce(a.ccd_count, 0)                                     AS ccd_count,
    coalesce(a.trn_count, 0)                                     AS trn_count,
    coalesce(a.lab_count, 0)                                     AS lab_count,
    coalesce(a.adt_count, 0)                                     AS adt_count,
    coalesce(a.ccd_count, 0) + coalesce(a.trn_count, 0)
        + coalesce(a.lab_count, 0) + coalesce(a.adt_count, 0)   AS total_docs
FROM hospitals h
LEFT JOIN actual a ON h.aa_key = a.aa_key
ORDER BY total_docs DESC, h.assigning_authority ASC, h.organization_name ASC;
