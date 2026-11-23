# HEALTHeLINK – QE-specific requirements

Status: **Live in demo** (`HEALTHeLINKEmulator.html`, built by `build_chart.py`).
Region: Western New York (Buffalo area). Site: https://wnyhealthelink.com. Accent `#1d4ed8`.
QE code in data and tickets: `HEALTHELINK`. Sources in sample data: `HEALTHELINK|KINGSB`, `HEALTHELINK|ECMC`.
Product: **HEALTHeLINK Fusion** (the HealthShare clinical viewer), reached through the HEALTHeCOMMUNITY Portal.
Reference: `QE-Example-Materials/HEALTHeLINK/` (official Fusion User Training Guide v2.5, 48 screenshots, extracted text). **This is the most fully documented QE, so use the guide as the visual and workflow reference.**
Common rules (processing, drill-in, Missing data) are in docs 02 and 03.

UI design tokens, colors, shared widget behavior and screenshots: [05-ui-design.md](../05-ui-design.md).
## Look and structure [Demo]

| Element | Requirement |
|---------|-------------|
| Patient banner | Name, age, sex, DOB, MRN, MPID, plus **chart flags**: icons that show a tooltip or open on click. Demo flags: `NKA` No Known Allergies (gray), `ALG` N Allergies (red), `Rx` N Medications (teal), and other data-count flags. |
| Chartbook | Left navigation. **One section at a time.** Sections with data are marked (blue in Fusion); empty sections are visibly inactive. |
| Sections | Clinical Summary, Conditions, Allergies, Medications, Histories, Encounters, Documents, Immunizations, Vital Signs, Lab Results, Diagnostic Studies, Procedures, Appointments, Care Team, Cohorts, Claims, Demographics, Insurance, Reports. Demo implements those with data; the rest are present but inactive. |
| Tables | Dense clinical tables. Abnormal results have a red **left bar** and red value. |
| Lab columns | Lab Test, Result, Units, Flag, Reference Range, Collection Date. |

Other columns: Medications = Medication, Start Date, Stop Date, Status; Encounters = Encounter, Start Date, End Date; Vital Signs = Vital, Value, Units, Date; Immunizations = Immunization, Date Administered, Status.
Encounter facility, attending, PCP, disposition and reason appear in the drill-in.

## Fusion behaviors the production build needs [Prod]

From the training guide. Not implemented in the demo.

1. **Access path**: HEALTHeCOMMUNITY Portal badges, then the HEALTHeLINK badge, then a **Confidentiality Acknowledgement**, then **Duo two-factor**, then Fusion Gateway, then the viewer.
2. **Patient Search** (left "Search Criteria" panel): Last name, First name and DOB are **required**. The results table has Name, Age, Gender, DOB, Address, Master Patient Identifier. A caret expands **per-source rows** showing Medical Record Number, Assigning Authority and Info Types (icons).
3. **Consent gates visibility.** A patient without consent does not expose data.
4. **Lab Results full column set**: Lab Test, Result, Units, Flag, Reference Range, **Status, Trend, Order, Facility**, Collection Date, with a search box and a sort/filter control. The demo omits Status, Trend, Order, Facility. The demo model carries a result status; facility, order and trend need new data from PDR.
5. **Reports**: per-section reports (default last 30 days) to view, download and print; a "New Report" builder by data type and date range; saved named reports.
6. **Audit**: same-name access check, **break-the-glass**, patient-data-access audit.

## HEALTHeLINK-specific needs

1. **Patient Search per-source rows** map directly to the MRN array: each row is `(QE|Assigning Authority, MRN)`. Build the search result expansion from the same data that feeds MRN Array.
2. **Chart flags** are derived from the merged record (allergy count, active medications, and so on). They **must** update when the data changes.
3. **Missing data default.** QE auto-fills `HEALTHELINK`; Source and MRN default to the person's HEALTHeLINK identifier.
4. **"Info Types" icons** in search results list the data types available per source. Derive these from which sections have data in that source's documents.

## Open questions for HEALTHeLINK

- Does the portal sit behind the HEALTHeCOMMUNITY Portal and Duo, or use the new portal's own login?
- Exact consent model and how a no-consent patient is shown.
- Whether Reports (view/download/print) are in scope for the first release.
- Source of Facility, Order and Trend for labs.

## Acceptance

- [ ] Banner shows the demographics and chart flags; flags match the data counts.
- [ ] Chartbook shows one section at a time; sections with data are marked.
- [ ] Abnormal labs have the red bar and value.
- [ ] CCD/ORU de-duplication as in doc 02, section 4.
- [ ] Missing data defaults QE to `HEALTHELINK`.
- [ ] **[Prod]** Search with required Last/First/DOB; expandable per-source rows; consent enforced; break-the-glass and audit work.
