# PDR volume reports (IN-3737)

Reports that let QEs understand the volume of data in PDR by assigning authority (AA).
This folder describes what we want, with the SQL behind each prototype report.

**Jira:** [IN-3737](https://nyec.atlassian.net/browse/IN-3737)
**Prototype site:** [https://main.d3pz3oj6iuj9t4.amplifyapp.com](https://main.d3pz3oj6iuj9t4.amplifyapp.com) (see "Understand Volume")
**Git repo:** [https://github.com/rsxmjb234/Portal40-SideBySideV0](https://github.com/rsxmjb234/Portal40-SideBySideV0)

| # | Report | Starts from | Spec | Prototype | SQL |
|---|---|---|---|---|---|
| 1 | Volume by QE, highest level | Data in PDR, QEs known to Verato | [01-volume-by-qe.md](01-volume-by-qe.md) | [link](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#volume-reports) | [SQL](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/SQLExamples/DailyVolumeByQE-28Day-SingleSnapshot-ExcludeOrphans.sql) |
| 2 | Hospital volume by AA | Salesforce hospital list | [02-hospital-volume.md](02-hospital-volume.md) | [link](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#hosp-report) | [SQL](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/SQLExamples/reportonhospitals.sql) |
| 3 | Non-hospital sources | Data in PDR, minus hospitals | [03-non-hospital-sources.md](03-non-hospital-sources.md) | [link](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#nonhosp-report) | [SQL](https://github.com/rsxmjb234/Portal40-SideBySideV0/blob/main/SQLExamples/reportonnonhospitals.sql) |

## Shared rules

- **One inventory snapshot** (5 days ago) is read, and dates come from the S3 key path
  (`<AA>/<type>/YYYY/Mon/DD/...`). Last-modified date is not used because routine S3 rewrites change it.
- The reporting window ends the day before the snapshot so every day shown is complete.
- Backload and `processed/` / `error/` prefixes are excluded.
- **HEALTHeLINK is the `techbd` (TechByDesign, `tbx`) bucket.**
- **Hixny CCDs** are stored under `<AA>DOC`; the suffix is stripped so CCD and TRN match.
- Reports 2 and 3 split the AA population cleanly: Report 2 is Salesforce hospitals, Report 3 is
  everything else that has data in PDR.

## Cost and refresh

Each query reads one snapshot and scans about 47 GB, which is roughly $0.25 at Athena list price.
The prototype's data is a saved result. To refresh it, re-run the SQL and run
`python build_reports.py`, then redeploy the site.
