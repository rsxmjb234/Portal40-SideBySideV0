/*
Expected cost/run: near zero (small lookup table)
Expected runtime: seconds

Goal:
- Export the ADT snapshot (lookup_adt_counts) summed across all available months,
  grouped by QE + assigning authority + facility.
- QE names normalised to match the other reports (PDR bucket names).
- This is a separate data source from the S3 inventory — ADT messages are
  counted from a different pipeline and loaded as a static snapshot.
- Covers Aug–Oct 2026 (3 months).
*/

SELECT
    CASE originating_qe
        WHEN 'TXD'     THEN 'healthelink'
        WHEN 'HECDCS'  THEN 'healtheconnections'
        WHEN 'HEALTHIX' THEN 'healthix'
        WHEN 'HIXNY'   THEN 'hixny'
        WHEN 'BRONX'   THEN 'bronx'
        WHEN 'GRRHIO'  THEN 'rochester'
        ELSE lower(originating_qe)
    END AS qe,
    assigning_authority,
    nys_permanent_facility_id AS facility_id,
    facility_name,
    sum(CAST(message_count AS bigint)) AS adt_count
FROM pdr_inventory.lookup_adt_counts
GROUP BY 1, 2, 3, 4
ORDER BY adt_count DESC;
