# Hixny – QE-specific requirements

Status: **Live in demo** (`HixnyEmulator.html`, built by `build_smart.py`).
Region: Capital Region (and into Vermont). Site: https://hixny.org. Accent `#0e7490`.
QE code in data and tickets: `HIXNY`. Sources in sample data: `HIXNY|SPLPCPRIME`, `HIXNY|ALBMC`.
Common rules (processing, drill-in, Missing data) are in docs 02 and 03. This file lists only what is specific to Hixny.

## Positioning (from hixny.org, paraphrased)

- Workflow-first: the viewer launches **inside the EHR at the point of care, in one click**.
- Parses clinical document data and surfaces insights, instead of showing CCDs as PDFs.
- Strong data quality and security messaging.

UI design tokens, colors, shared widget behavior and screenshots: [05-ui-design.md](../05-ui-design.md).
## Look and structure [Demo]

Card dashboard with tabs, and a FHIR-flavored vocabulary.

| Element | Requirement |
|---------|-------------|
| Header | Title "SHIN-NY Community Health Record" (configurable). Patient context banner always visible. |
| Tabs | Summary, Conditions, Medications, Lab Results, Vitals, Immunizations, Procedures, Encounters, Demographics. One tab at a time. |
| Summary cards | Allergies, Active Problems, Medications, Recent Lab Results, Vital Signs, Immunizations. Each card shows a count, the top few items (`ul.mini`), and a small **FHIR resource tag** (`AllergyIntolerance`, `Condition`, `MedicationRequest`, `Observation`, `Immunization`). |
| Provenance chips | Labs show **CCD** and **ORU** badges; ORU duplicates show "preferred", new ones "new", CCD copies "superseded by ORU" (strikethrough). |
| Status chips | Medications show **Active** (green) or **Completed** (gray). |
| Active filter | Summary medications list only active medications when any exist, else all. |

### Columns

| Tab | Columns |
|-----|---------|
| Conditions | Condition, Onset, Resolved, Status |
| Medications | Medication, Start, Stop, Status |
| Lab Results | Test, Result, Units, Flag, Reference Range, Date |
| Vitals | Vital, Value, Units, Date |
| Immunizations | Immunization, Date |
| Procedures | Procedure, Date |
| Encounters | Encounter, Start, End |
| Allergies | Allergen / Substance |

Drill-in extras per doc 02, section 9. For Encounters the table shows only type and dates, so facility, attending, PCP, disposition and reason appear **only in the drill-in**.

## Hixny-specific needs

1. **EHR launch.** **[Prod]** Support a SMART-on-FHIR-style launch from an EHR with patient context passed in, so the user lands on this patient's Summary with no search step. Confirm the launch standard with Hixny (SMART App Launch, or Hixny's existing method).
2. **Copy Data ID from summary cards.** Summary-card list items (not only table rows) **must** have the copy affordance, so a user can report "PDR has it, Hixny does not" from the Summary tab. [Demo]
3. **FHIR resource tags.** Keep the resource-type tags on cards. They signal to technical users what the data maps to. If the portal exposes FHIR APIs, the tags **must** match real resource types.
4. **Insight, not documents.** Never present CCDs as an attachment list on the main path. Parsed, merged data is the default view. **[Prod]** A "source documents" view may sit behind it.
5. **Missing data default.** On this view the QE field auto-fills `HIXNY`, Source and MRN default to the person's Hixny identifier (the first `HIXNY` entry in the MRN array).

## Open questions for Hixny

- Which EHR launch mechanism and which EHRs?
- Does Hixny require its own banner wording, consent acknowledgement or login flow?
- Which sections does Hixny's real viewer expose that the demo omits (for example Care Team, Documents)?
- Are there Hixny-specific alerts or notifications to show on the Summary?

## Materials still needed

Actual Hixny provider-portal screenshots or user guide (not yet collected). See `QE-Example-Materials/Hixny/NOTES.md`.

## Acceptance

- [ ] Summary shows six cards with counts and resource tags.
- [ ] All nine tabs work and show the same merged data as the other QEs.
- [ ] Copy-Data-ID icon works on both table rows and summary-card items.
- [ ] Missing data form defaults QE to `HIXNY`.
- [ ] **[Prod]** EHR launch lands on the right patient with context.
