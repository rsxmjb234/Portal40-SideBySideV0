# 02 – Data Processing (requirements for ALL QEs)

Every QE view is a different presentation of the same processing pipeline. Nothing in this document is QE-specific. If a QE needs something different, it is in `qe/<name>.md`.

Reference implementation: `ccda_parse.py` (functions `merge_by_person`, `_dedup_person`, `_reconcile_oru`). In the demo that file also parsed C-CDA and HL7; that parsing is **not** part of the new build. Only the merge, de-duplication and reconciliation rules matter.

Pipeline (what the viewer does with the person data it is given):

```
 PDR person data (see 04) --> merge sources --> de-duplicate --> reconcile labs --> display + drill-in
```

How the data is obtained from PDR is outside this specification. The team already knows how to call PDR. **Assume the data arrives shaped like [04-pdr-data-model.md](04-pdr-data-model.md).**

## 1. Input

The viewer receives the data for one person, in the shape described in [04-pdr-data-model.md](04-pdr-data-model.md): demographics, the MRN array, and lists for conditions, medications, labs (grouped by panel), lab feed results (`oru`), immunizations, vitals, procedures, encounters and allergies.

Requirements:
- Missing lists or missing optional fields **must** produce an empty section ("No X on file"), never an error page.
- A bad or partial record **must not** block the rest of the person's data. Log it for operations. **[Prod]**
- Unknown or unmapped codes **must** still display the best available text (display name, then original text, then the raw code).
- Field names, value formats and flags in 04 are an **assumption** based on the demo. If PDR's real field names differ, map them once at the boundary and keep the rest of the viewer on the model in 04.

## 2. Person identity and MRNs

The person data carries an **MRN array**: every `(QE, Source, MRN)` that identifies this person, and a cross-source person key (MPID).

Rules:
1. The MRN array drives the MRN Array button and is stamped on every Missing data ticket.
2. The MRN array **must** be de-duplicated on the triple (QE, Source, MRN).
3. **Confirm with the PDR team first** (see doc 00 open questions): does PDR return one already-merged record per person, or one record per source? If PDR returns one merged record, skip the grouping step and use section 3 for display de-duplication only. If PDR returns per-source records, group by MPID (fallback `family|given|DOB`) and apply section 3 fully.
4. Lab feed results (`oru`) that carry a QE, Source and MRN **must** be matched to a source on the full triple, never on MRN alone, because two sources can issue the same MRN value. (The demo matched on MRN alone; that is a known gap.)

Requirements:
- **Must** show how many sources contributed and list them (MRN Array).
- **Should** warn when records for one MPID disagree on DOB or sex. Do not merge silently. **[Prod]**
- **[Prod]** Matching decisions **must** be auditable.

## 3. Merge and de-duplication by data type

After grouping by person, concatenate each data type across documents, then collapse duplicates using the key below. The first occurrence wins. **De-duplication hides duplicates in the merged view only. Never delete the source record.** Keep the raw documents and be able to show which sources contributed each item. **[Prod]**

| Data type | Fields | De-dup key |
|-----------|----------------------|-----------|
| Conditions | name (SNOMED display), onset, resolved, status | (name, onset) |
| Medications | name (RxNorm), start, stop, status, dose, route, frequency, prescriber, refills, indication, RxNorm code | (name, start) |
| Lab results (document) | panel, test, value, unit, flag, reference range, date, LOINC, status | panel: (panel, date); result: (LOINC, date, value) |
| Lab results (feed, `oru`) | test, value, unit, range, flag, date, LOINC | (LOINC, date, value) |
| Immunizations | name, date | (name, date) |
| Vital signs | test, value, unit, date | (test, value, date) |
| Procedures | name, date | (name, date) |
| Encounters / ADT | type, facility, admit, discharge, attending, PCP, disposition, reason | (type, admit date, facility) |
| Allergies | substance | (substance) |

Known gaps to fix in the production build:
- **Encounter key** is now `(type, admit date, facility)`. If facility is blank, two same-type, same-day encounters without a facility will still merge incorrectly — this is acceptable for the demo but should be monitored.
- **Medication key** (name, start) can merge the same drug started the same day at two doses. **Should** add dose.
- Sorting in the demo is done on the formatted `MM/DD/YYYY` string, which orders incorrectly across years. **Must** sort on real date values, newest first for encounters, immunizations and procedures.

## 4. Lab de-duplication: document results vs feed results – the core rule

The same lab can arrive twice: once inside a CCD and once as an ORU message. The viewer **must** reconcile them.

| Step | Rule |
|------|------|
| 1 | Build a set of CCD result keys `(LOINC, date)`. |
| 2 | For each ORU result, if `(LOINC, date)` is in the CCD set, mark the ORU result **duplicate = true** and display it as **preferred**. Otherwise display it as **new**. |
| 3 | For each CCD result whose `(LOINC, date)` exists in the ORU set, mark it **superseded**. Show it **crossed off (strikethrough) with a "superseded by ORU" tag. Never delete it.** |
| 4 | ORU results are shown in their own group at the top ("Laboratory Feed · ORU"), with a count. CCD results are grouped by panel and panel date below it. |
| 5 | Each lab row carries a source badge: **CCD** or **ORU**. A legend explains the badges and the strikethrough. |

Rule reasons: the ORU is the live lab-system message and is treated as authoritative. The CCD copy stays visible for audit.

Open item for product owner: the demo matches on LOINC + date only and does not compare values. **Should** flag a **conflict** when the key matches but the value or unit differs, instead of marking it a plain duplicate.

### Expected result for the demo patient (use as a test)

- CCD panel "Basic metabolic panel" dated 2025-03-15 on every document: Glucose 81.78 mg/dL, Creatinine 1.01 mg/dL, Sodium 141.78 mmol/L.
- Every ORU repeats those three plus **Hemoglobin A1c 6.1 %, flag High, ORU-only**.
- After merge: the three BMP results show as ORU **preferred** with the CCD copies **crossed off**. HbA1c shows as ORU **new**, abnormal.

## 5. Lab flags

PDR normalizes flags to one of these values: `Normal`, `Low`, `High`, `Abnormal`, `Critical High`, `Critical Low`, or empty (no flag).

`Low`, `High`, `Abnormal`, `Critical High` and `Critical Low` are **abnormal**. Abnormal results **must** be visually distinct (red value; QE styles may add a left bar or tag). See Appendix A for the raw code values the demo read.

## 6. Dates

- PDR supplies dates as `MM/DD/YYYY` strings per the model in doc 04. **[Prod]** Request ISO-8601 with timezone from PDR; store that, display per the QE convention, and sort on the stored value — not on the formatted string (see known gap in section 3).
- An open-ended medication or problem (no `stop` / `resolved` date) is **Active**. A stop or resolved date makes it **Completed** / **Resolved**.
- The raw HL7 and C-CDA timestamp formats (`YYYYMMDD`, `YYYYMMDDHHMM`, `YYYYMMDDHHMMSS`) are in Appendix A. The new build does not parse these.

## 7. Terminology

PDR will carry code-system context for structured fields. The code systems used in the data are:

| Domain | Code system |
|--------|-------------|
| Conditions, reasons, procedures | SNOMED CT |
| Medications | RxNorm |
| Labs, vitals | LOINC |
| Discharge disposition | HL7 Discharge Disposition |
| Provider role | NUCC taxonomy |
| Route of administration | NCI Thesaurus |

Display rule: if a field has a human-readable name, show it. If it is blank or unknown, show the raw code rather than nothing. OIDs and C-CDA attribute names for these code systems are in Appendix A.

## 8. Encounters / ADT fields

| Field | Meaning |
|-------|---------|
| `name` / `etype` | Encounter type (inpatient admission, ED visit, office visit, follow-up) |
| `start` / `stop` | Admit and discharge date. No `stop` means an outpatient or open encounter; show a dash |
| `facility` | Where it happened. Never invent one when it is blank |
| `attending`, `pcp` | Provider names |
| `disposition` | Discharge disposition. Only present for stays that ended with a discharge |
| `reason` | Reason for visit |

The C-CDA locations these came from are listed in Appendix A. In the new build, PDR supplies the fields directly. Use a provider role when PDR gives one; do not depend on list position to tell attending from PCP.

## 9. Drill-in detail (every QE)

Requirement from the product owner: **if more data exists than is shown in the row, the provider can click in and see it.**

- Clicking any data row **must** open a detail panel showing every field available for that record, not only the visible columns.
- Panel header shows the patient (name, DOB) and the QE|Source MRN the view represents.
- Fields with no value **must** be omitted, not shown blank.
- Group header rows and copy icons do not open the panel.
- Escape, the close button, or a click outside closes the panel.

Extra fields per type (beyond the visible columns), implemented in the demo:

| Type | Extra fields in detail |
|------|------------------------|
| Encounter / ADT | Facility, attending, PCP, discharge disposition, reason for visit, encounter type |
| Medication | Instructions (built sig), indication, dose, route, frequency, prescriber, refills, RxNorm code, record status |
| CCD lab | LOINC code, panel, result status, source document |
| ORU lab | LOINC code, source feed (HL7 v2 ORU^R01), duplicate-of-CCD yes/no |
| Others | Visible columns only (conditions, immunizations, procedures, vitals not yet enriched) |

## 10. Provenance and the Data ID

- Every displayed item **must** be traceable to its source (QE, Source, MRN, document or message ID, received date). **[Prod]** The demo tracks QE, Source and MRN only per view.
- The Missing data feature's "copy Data ID" produces `PDR|mrn=..|qe=..|src=..|<row text>`. In the demo this is built from the row text. **[Prod]** Replace it with a **stable record ID** (a persistent key per merged item), so a ticket still points at the right record after the data refreshes.

## 11. Empty and partial data

- Section with no data: the QE's own empty-state text (for example "No problems on file.").
- Navigation shows which sections have data (Fusion marks them in blue; others disable empty ones).
- A section **must** show a count when the QE style has one.

## 12. Security, privacy and audit [Prod]

The demo has none of these. All are required in the secure portal. Details come from the security team and from each QE's policy.

- Authentication and authorization, with per-user QE entitlements.
- Patient consent and consent-based visibility (HEALTHeLINK Fusion gates search results on consent).
- Break-the-glass access with a reason, and access audit logging of who viewed which patient and when.
- Encryption in transit and at rest. No PHI in logs or URLs.
- Missing data tickets stored in a dedicated secure bucket (see [03-missing-data-logging.md](03-missing-data-logging.md), section 12).

## 13. Acceptance test: Marcus Evans

Use the fixture `fixtures/marcus_evans.json` (see 04). After processing, every QE view **must** show:

| Check | Expected |
|-------|----------|
| People | 1 (Marcus Evans, DOB 06/01/1950, M) |
| MRN array | 10 entries, one per source, no duplicates |
| Conditions | 5: type 2 diabetes, hypertension, hyperlipidemia, CKD stage 3, osteoarthritis |
| Medications | 10 after merge (each source holds a 7-10 subset) |
| Encounters / ADT | 5, newest first, each with facility, attending, PCP and reason; inpatient and ED stays also have a disposition |
| Labs | 840 CCD results after de-dup, plus the ORU group |
| BMP duplicates | Glucose, creatinine, sodium: ORU preferred, CCD crossed off |
| HbA1c 6.1 % | ORU only, flagged High |
| Drill-in | Opens for encounter, medication, CCD lab and ORU lab rows with the extra fields in section 9 |

## Appendix A. Where the fields came from in the demo (informational)

The demo built its data from C-CDA XML and HL7 v2 ORU files. The new build does **not** parse these. The tables explain where each field in 04 originated, in case PDR exposes the same concepts under other names.

Identifiers in a C-CDA (`recordTarget/patientRole/id`):

| Identifier | How to recognize it | Use |
|------------|--------------------|-----|
| Source MRN | `id` with `assigningAuthorityName="QE\|Source"`; `extension` = MRN | One MRN array entry |
| MPID | `id` whose `root` ends in `.mpid` | Cross-source person key |
| EID | `id` whose `root` ends in `.eid` | QE's own ID |

Identifiers in an HL7 ORU (`PID-3`, repeating, `~` separated): `340474^^^HEALTHIX&MSSM^MR ~ HX-EID-1234^^^HEALTHIX^PI ~ MARCUS-GOLDEN-0001^^^NYEC^PI`. First repetition is the source MRN; component 4 is `QE&Source`.

Encounter fields in a C-CDA:

| Field | C-CDA location |
|-------|----------------|
| Type | `encounter/code` |
| Admit / discharge | `encounter/effectiveTime` low / high |
| Facility | `encounter/participant[@typeCode='LOC']/participantRole/playingEntity/name` |
| Attending / PCP | `encounter/performer[1]` and `[2]`, under `assignedEntity/assignedPerson/name` |
| Discharge disposition | `sdtc:dischargeDispositionCode/@displayName` |
| Reason | `encounter/entryRelationship/observation/value/@displayName` |

Medication fields: `substanceAdministration` with `effectiveTime` (IVL low/high, and a PIVL period for frequency), `routeCode`, `doseQuantity`, `repeatNumber` (refills), `author` (prescriber), `entryRelationship` (indication), and the RxNorm code under `consumable/manufacturedProduct/manufacturedMaterial/code`.

Lab results in a C-CDA: `Diagnostic Results` section, `organizer` (panel) with `component/observation` (result), `interpretationCode` (flag), `referenceRange`, LOINC `code`. In HL7: `OBX-3` code^name, `OBX-5` value, `OBX-6` unit, `OBX-7` range, `OBX-8` flag, `OBX-14` date.
