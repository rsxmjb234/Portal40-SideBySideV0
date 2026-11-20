# 00 – Start Here: Project Context, Status and Build Plan

Read this first if you are a model or developer joining cold. It explains what exists, why it looks the way it does, and what remains.

## 1. What this is

A proof-of-concept viewer for the **Public Health / SHIN-NY Community Health Record**. It answers one question: can the same person's merged record be shown inside each Qualified Entity's (QE) own look and workflow, with the same underlying data and the same rules?

The demo shows one synthetic patient, **Marcus Evans**, in three QE styles (Hixny, HEALTHeLINK, Bronx RHIO / IMAT). Three more QEs (Healthix, HealtheConnections, Rochester RHIO) are placeholders on the home page.

The new build is a **secure portal**. It gets its data from PDR. The demo does not: it read static files. This documentation set assumes PDR supplies person data shaped like [04-pdr-data-model.md](04-pdr-data-model.md), and does not describe how to fetch it.

## 2. Features that exist in the demo

| Feature | Where specified |
|---------|-----------------|
| Home page with a card per QE (live / coming soon) | 01 |
| Three QE-styled views over one record | 05, qe/ |
| Merge of many sources into one virtual record, with de-duplication per data type | 02 section 3 |
| Lab reconciliation: lab-feed (ORU) result preferred, document (CCD) copy crossed off, never deleted | 02 section 4 |
| Abnormal flags, CCD/ORU provenance badges | 02 section 5, 05 |
| **MRN Array** button: lists every `QE\|Source\|MRN` for the person | 03 |
| **Missing data** ticket: two directions ("QE has it, PDR does not" / "PDR has it, QE does not"), QE auto-filled to the view's QE, copy-a-Data-ID from any row, stored as single-line JSON for Athena | 03 |
| **Drill-in detail**: click any row to see every field, including fields not shown as columns | 02 section 9, 05 |
| Realistic encounter/ADT fields (facility, attending, PCP, disposition, reason) | 02 section 8, 04 |
| Realistic medication fields (dose, route, frequency, prescriber, refills, indication, RxNorm) | 04 |

## 3. Decisions already made (do not reopen without the product owner)

1. **One person across many sources.** Marcus has 10 MRNs in 10 sources across 5 QEs. The first attempt used five different people and was rejected, because the point is one person with many MRNs.
2. **Distinct documents, one condition list.** The 10 source documents differ in labs, vitals and so on (real variety), but share one identity and one five-condition list. Identical clones were rejected.
3. **Each QE gets its own look.** Not one shared theme. Imitate the real product (see `QE-Example-Materials/` for the references we have).
4. **Missing data, direction A** ("QE has it, PDR does not") auto-fills QE to the view's QE. **Direction B** ("PDR has it, QE does not") pre-fills QE, Source and MRN read-only and takes a pasted Data ID.
5. **Never delete, only supersede.** De-duplication hides and crosses off. The source record stays.
6. **Drill-in is shared.** One widget, injected into every view, not three separate implementations.
7. **Tickets** are one line of JSON each, in a dedicated secure bucket, partitioned by date (doc 03 section 12).
8. **CRISP** (Maryland HIE) was studied only as a design reference. It is not a NY QE.

## 4. What the demo does NOT do

- No login, consent, break-the-glass or audit (doc 02 section 12).
- No real EHR launch.
- No patient search. A dropdown selects the patient.
- Tickets are shown on screen, not stored. The storage design exists in doc 03 but is not implemented.
- Only encounters and medications have enriched drill-in fields. Conditions, immunizations, procedures and vitals show only their table columns.
- Lab detail is thin: no ordering provider, performing lab, facility or trend.
- Section placeholders (Documents, Appointments, Claims, Radiology, Transcribed Reports and others) are visibly inactive and have no data.
- Healthix, HealtheConnections and Rochester RHIO views are not built, and their reference material has not been collected.

## 5. Known defects and gaps in the demo logic

Listed in doc 02 so the new build does not copy them. Summary:
- ORU matched to a source on MRN alone.
- Encounter de-duplication key was updated to `(type, admit date, facility)` in doc 02. Medication key `(name, start)` is still too loose — same drug at two doses started the same day will merge incorrectly.
- Dates sorted as text.
- "Data ID" built from row text instead of a stable ID.
- CCD/ORU duplicate test ignores the value, so conflicts are not flagged.
- Provider roles inferred from list position.
- Facility falls back to the QE name in the Bronx view when blank.
- The sample patient's vitals, immunizations and procedures are random generator output, not curated.

## 6. Reference implementation map

Repo: https://github.com/rsxmjb234/Portal40-SideBySideV0. Live demo: https://main.d3pz3oj6iuj9t4.amplifyapp.com.

| File | Role |
|------|------|
| `ccda_parse.py` | Parse, merge, de-duplicate, reconcile. **Rules to port.** Parsing itself is not needed in the new build. |
| `build_smart.py` | Hixny view |
| `build_chart.py` | HEALTHeLINK (Fusion) view |
| `build_bronx.py` | Bronx RHIO (IMAT) view |
| `bug_widget.py` | MRN Array, Missing data, copy icon and drill-in widget (HTML, CSS and JS in one file) |
| `build_home.py` | Home page and build orchestration |
| `make_person.py` | Generates the Marcus test data. Not needed in the new build |
| `export_fixture.py` | Exports `fixtures/marcus_evans.json` |

The demo builds static HTML pages from Python. The new build is a dynamic secure app. Port behavior, not architecture.

## 7. Suggested build order

1. **Data layer.** Implement the person model from 04 and a boundary mapper from the real PDR response to it. Test with `fixtures/marcus_evans.json`.
2. **Processing.** MRN array de-dup, merge, per-type de-dup, lab reconciliation (doc 02). Unit-test against the Marcus acceptance table (doc 02 section 13).
3. **Shared widgets.** Buttons, MRN Array, Missing data (both directions), copy icon, drill-in modal (doc 03, doc 05 section 5).
4. **One QE view end to end.** Start with HEALTHeLINK: it has the best reference material (`QE-Example-Materials/HEALTHeLINK/`).
5. **Second and third views.** Hixny, then Bronx RHIO.
6. **Home page** with configuration-driven cards and entitlements.
7. **Ticket storage** to the secure bucket (doc 03 section 12).
8. **Security and audit** (doc 02 section 12), which touches every step. Plan it from step 1.
9. **Remaining QEs** once their reference material is collected.

## 8. Open questions for the product owner

- Exact PDR response shape and whether PDR returns a merged person or one record per source.
- Authentication, consent and break-the-glass rules per QE.
- Which sections are in scope for first release (Reports, Documents, Care Team, Medications Administered, ...).
- Rochester RHIO: separate view or folded into HealtheConnections, and when.
- Where tickets are stored and who triages them.
- Per-QE branding and logo permissions (the demo uses styled wordmarks, not official logos).

## 9. Prompt for a model

If you give these documents to a model, a prompt like this works:

> You are building the PDR Community Health Record viewer described in these documents. Data comes from the PDR API, shaped as in 04-pdr-data-model.md. Do not design the API call. Use `fixtures/marcus_evans.json` as a stub. Implement the rules in 02, the widgets in 03 and 05, the Hixny, HEALTHeLINK and Bronx RHIO views in qe/, and the home page in 01. Follow 00 section 7 for order. Flag any requirement that conflicts or is missing instead of guessing.
