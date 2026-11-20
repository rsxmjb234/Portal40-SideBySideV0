# IN-3737 update text (paste into Jira)

## Summary (rename to)

Build set of reports letting QE's understand volume of data in PDR by Assigning Authority

## Description

**Goal:** Give each QE a set of reports that show how much data it sends to PDR, by assigning
authority (AA), so the QE can see who is sending, who is not, and who is not yet registered.

**Prototype (working example):** [https://main.d3pz3oj6iuj9t4.amplifyapp.com](https://main.d3pz3oj6iuj9t4.amplifyapp.com) , see the "Understand Volume" section.
**Source and specs:** [https://github.com/rsxmjb234/NyecPortal2](https://github.com/rsxmjb234/NyecPortal2) , start at
[`docs/reports/README.md`](https://github.com/rsxmjb234/NyecPortal2/blob/main/docs/reports/README.md).

### Reports

1. **Volume by QE, highest level.** CCD, TRN and LAB per QE over the last 28 days, Verato-matched
   sources only.
   [Spec](https://github.com/rsxmjb234/NyecPortal2/blob/main/docs/reports/01-volume-by-qe.md) |
   [Prototype](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#volume-reports) |
   [SQL](https://github.com/rsxmjb234/NyecPortal2/blob/main/SQLExamples/DailyVolumeByQE-28Day-SingleSnapshot-ExcludeOrphans.sql)
2. **Hospital volume by AA.** Starts from the Salesforce hospital list, so hospitals with no data
   in PDR still appear. QE filter on top, CCD and TRN for the last 10 days. Hospitals that share
   an AA are grouped under the AA heading, and the list is sorted by AA total.
   [Spec](https://github.com/rsxmjb234/NyecPortal2/blob/main/docs/reports/02-hospital-volume.md) |
   [Prototype](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#hosp-report) |
   [SQL](https://github.com/rsxmjb234/NyecPortal2/blob/main/SQLExamples/reportonhospitals.sql)
3. **Non-hospital sources.** Starts from all data in PDR (hospitals excluded) and looks up the
   name and type in Salesforce. AAs missing from Salesforce are tagged "Not in SFDC". QE filter on
   top, CCD and TRN for the last 10 days.
   [Spec](https://github.com/rsxmjb234/NyecPortal2/blob/main/docs/reports/03-non-hospital-sources.md) |
   [Prototype](https://main.d3pz3oj6iuj9t4.amplifyapp.com/#nonhosp-report) |
   [SQL](https://github.com/rsxmjb234/NyecPortal2/blob/main/SQLExamples/reportonnonhospitals.sql)

### Rules that apply to every report

- Dates come from the submission date in the S3 key path, not last-modified date.
- One inventory snapshot (5 days ago); the window ends the day before it so every day is complete.
- Backload and processed/error prefixes are excluded.
- HEALTHeLINK is the techbd (TechByDesign) bucket.
- Hixny CCDs are stored under `<AA>DOC`; strip the suffix so they match the AA.

### Acceptance criteria

- [ ] Each report loads from a service that runs the SQL, not from saved results.
- [ ] Date ranges shown on the page are computed from the snapshot used.
- [ ] Report 2 and Report 3 together cover every AA with data in PDR exactly once.
- [ ] Report 2 lists every Salesforce hospital, including hospitals with no data.
- [ ] Report 3 tags AAs that are not in Salesforce.
- [ ] A QE filter is available on Reports 2 and 3.

### Open questions

- Add LAB (ORU) as a document type in Reports 2 and 3?
- Should the number of days be selectable?
- Who owns registering the "Not in SFDC" sources?
- Should the Not in SFDC sources get their own filter?

### Out of scope

Security, authentication and hosting. Developers will decide these.
