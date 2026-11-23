# Bronx RHIO (IMAT Solutions) – QE-specific requirements

Status: **Live in demo** (`BronxEmulator.html`, built by `build_bronx.py`).
Region: The Bronx. Site: https://bronxrhio.org. Accent `#b91c1c`.
QE code in data and tickets: `BRONX`. Source in sample data: `BRONX|BXLEB`.
Technology partner: **IMAT Solutions**. The product is a browser-based **Provider Clinical Viewer** that assembles local, statewide and other sources into a **Virtual Health Record**.
Reference: `QE-Example-Materials/BronxRHIO/` (two IMAT screenshots: ADT page and Labs page). The demo view was built from those two images, so other screens are extrapolated. Confirm them against the real IMAT viewer.
Common rules (processing, drill-in, Missing data) are in docs 02 and 03.

UI design tokens, colors, shared widget behavior and screenshots: [05-ui-design.md](../05-ui-design.md).
## Look and structure [Demo]

| Element | Requirement |
|---------|-------------|
| Layout | Left navigation pane plus a content pane. Blue IMAT-style header. |
| Tables | Zebra-striped, with a **leading magnifier column** on every row. The magnifier signals "click to see detail". The whole row is clickable. |
| Drill-in | Detail panel with a blue header (`#2196f3`). Demo name: "{Section} – detail". |
| Legend | Labs show a legend: CCD badge, ORU badge, strikethrough = superseded. |
| Patient Info | First pane. Key/value block of demographics: MPID, Name, Date of Birth and related identity fields. |

### Left navigation (order matters)

| Item | State in demo |
|------|---------------|
| Patient Info | Active |
| Advance Directives | Inactive (no data) |
| Summary | Active |
| Admits/Discharges/Registrations | Active |
| Labs | Active |
| Observations/Vitals | Active |
| Transcribed Reports | Inactive |
| Radiology | Inactive |
| Medications – Administered | Inactive |
| Medications – Prescribed | Active |
| Problems | Active |
| Immunizations | Active |
| Procedures | Active |
| eHealth Exchange2 | Inactive |
| Links | Inactive |
| All | Inactive |

Inactive items are present, visibly disabled, and not clickable.

### Columns

| Section | Columns |
|---------|---------|
| Admits/Discharges/Registrations | ADT / Encounter, Facility, Admit Date, Discharge Date, **Attending**, **PCP** |
| Labs | Observation, Value, Units, Reference Range, Abnormal, Date |
| Problems | Problem, Onset, Resolved, Status |
| Medications – Prescribed | Medication, Start, Stop, Status |
| Observations/Vitals | Observation, Value, Units, Date |
| Immunizations | Immunization, Date, Status |
| Procedures | Procedure, Date |

ADT drill-in extras: discharge disposition, reason for visit, encounter type.

## Bronx RHIO-specific needs

1. **ADT is a first-class section.** Admits, discharges and registrations are central to this viewer. Each row **must** carry facility, attending and PCP, and drill into disposition and reason. If a registration has no discharge date, the Discharge Date shows a dash.
2. **Facility fallback.** When an encounter has no facility, the demo shows "Bronx RHIO". **[Prod]** Replace with a blank or "Unknown" value. Do not invent a facility.
3. **Medications – Administered vs Prescribed.** The demo only has prescribed data. **[Prod]** Administered (for example inpatient MAR) is a separate, currently empty section. Confirm the feed.
4. **Transcribed Reports, Radiology, Advance Directives, eHealth Exchange, Links** are navigation placeholders. Confirm which are in scope and what feeds them.
5. **Missing data default.** QE auto-fills `BRONX`; Source and MRN default to the person's Bronx RHIO identifier (`BRONX|BXLEB`).
6. **Virtual Health Record wording.** The viewer presents the merged record under that name. Consider matching the term in labels.

## Open questions for Bronx RHIO / IMAT

- Real IMAT screens for Summary, Patient Info, Problems, Medications, Immunizations (only ADT and Labs were provided).
- Is the leading magnifier a link to a separate detail page or an inline expansion?
- Are ADT events real-time (HL7 ADT feed) or from CCDs? The demo derives them from the encounter list in the person data.
- Statewide and "other sources" panels: shown separately or merged?
- Authentication and consent handled by IMAT or by the new portal?

## Materials still needed

Provider Clinical Viewer screenshots (full chart and summary), user guide, sample document layouts. See `QE-Example-Materials/BronxRHIO/NOTES.md`.

## Acceptance

- [ ] Left nav matches the order above; inactive items are disabled.
- [ ] Every data row has the magnifier and opens the detail panel.
- [ ] ADT table shows the six columns; drill-in adds disposition, reason and type.
- [ ] CCD/ORU de-duplication and legend as in doc 02, section 4.
- [ ] Missing data defaults QE to `BRONX`.
