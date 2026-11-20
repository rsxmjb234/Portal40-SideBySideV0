# 04 – PDR Person Data Model (assumed shape)

## Scope of this document

The viewer is given the data for **one person** and renders it. **How the data is fetched from PDR is not part of this specification.** The team already knows how to call PDR. This document only fixes the **shape of the data the viewer works on**, so the display, merge and de-duplication rules in the other documents have something concrete to refer to.

**Assumption:** PDR returns data similar to what the demo shows. The model below is exactly what the demo's merged record looks like. If PDR's real field names or formats differ, add one mapping layer at the boundary and keep everything else on this model.

Fixtures (a complete worked example, use it as test data and as a UI development stub):
- `fixtures/marcus_evans.json`: the full merged record (about 500 KB: 840 lab results across 259 panels, 516 vitals, 120 immunizations, 1,281 procedures, 10 medications, 5 conditions, 5 encounters, 10 MRNs).
- `fixtures/marcus_evans.sample.json`: a trimmed copy for reading.

## Person object

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `given`, `family` | string | `Marcus`, `Evans` | Display as `EVANS, Marcus` or `Marcus Evans` per QE style |
| `gender` | string | `M` | `M`, `F`, other |
| `dob` | string | `06/01/1950` | `MM/DD/YYYY` in the demo. **[Prod]** Prefer ISO `YYYY-MM-DD` and format on display |
| `age` | number | `76` | Compute from DOB if not supplied |
| `addr` | string | `179 Bednar Knoll Suite 2, Bronx, NY 10467` | One line |
| `race`, `eth`, `lang` | string | `white`, `non-hispanic`, `en-US` | Shown on Demographics |
| `mpid` | string | `MARCUS-GOLDEN-0001` | Cross-source person key |
| `mrn_list` | array | see below | **The MRN array** |
| `problems`, `meds`, `labs`, `oru`, `imms`, `vitals`, `procs`, `encs`, `allergies` | arrays | see below | Any may be empty |

All dates in item lists are strings `MM/DD/YYYY`. Empty string means "not present". Omitted optional fields are the same as empty.

### `mrn_list[]`

```json
{ "qe": "BRONX", "source": "BXLEB", "mrn": "515366" }
```

`qe` is the QE code (`HIXNY`, `HEALTHELINK`, `BRONX`, `HEALTHIX`, `GRRHIO`, `HEALTHECONN`). `source` is the contributing organization code. Display as `QE|Source|MRN`.

### `problems[]` (Conditions)

| Field | Example |
|-------|---------|
| `name` | `Diabetes mellitus type 2 (disorder)` |
| `onset` | `03/01/2012` |
| `resolved` | `` (empty = active) |
| `status` | `Active` or `Resolved` |

### `meds[]` (Medications)

| Field | Example | Visible in table? |
|-------|---------|-------------------|
| `name` | `Metformin hydrochloride 500 MG Oral Tablet` | yes |
| `start`, `stop` | `04/01/2012`, `` | yes (empty `stop` = Active) |
| `status_code` | `active` / `completed` | status chip |
| `dose` | `1 tablet` | drill-in |
| `route` | `Oral` | drill-in |
| `frequency` | `twice daily` | drill-in |
| `sig` | `Take 1 tablet by mouth twice daily` | drill-in "Instructions" |
| `prescriber` | `Dr. James Okafor` | drill-in |
| `refills` | `5` | drill-in |
| `indication` | `Diabetes mellitus type 2 (disorder)` | drill-in |
| `code` | `861007` (RxNorm) | drill-in |

### `labs[]` (structured lab results from clinical summaries), grouped by panel

```json
{ "panel": "Basic metabolic panel - Blood", "date": "03/15/2025",
  "comps": [ { "test": "Glucose [Mass/volume] in Blood", "value": "81.78", "unit": "mg/dL",
               "flag": "", "range": "", "date": "03/15/2025", "loinc": "2339-0",
               "status_code": "completed", "panel": "Basic metabolic panel - Blood" } ] }
```

`flag` is one of `Normal`, `Low`, `High`, `Abnormal`, `Critical High`, `Critical Low`, or empty.

### `oru[]` (results from the lab message feed)

```json
{ "test": "Hemoglobin A1c", "loinc": "4548-4", "value": "6.1", "unit": "%",
  "date": "03/15/2025", "flag": "High", "range": "4.0-5.6" }
```

`labs` and `oru` are two different channels for the same kind of fact. The viewer reconciles them (doc 02, section 4). **Derived by the viewer, not supplied:** `dup` (ORU result duplicates a document result) and `superseded` (document result replaced by an ORU result).

### Other lists

| List | Fields |
|------|--------|
| `imms[]` | `name`, `date` |
| `vitals[]` | `test`, `value`, `unit`, `date` |
| `procs[]` | `name`, `date` |
| `allergies[]` | `name` (empty list in the sample: show "No Known Allergies") |
| `encs[]` | `name`, `etype`, `start`, `stop`, `facility`, `attending`, `pcp`, `disposition`, `reason` |

## Recommended additions for production [Prod]

The demo model does not carry these. Ask PDR for them if available.

- Per-item `source` = `{ qe, source, mrn }` and a source document or message ID, so every row can show where it came from (doc 02, section 10).
- A **stable record ID** on every item, used by "copy Data ID" and tickets.
- Per-lab `facility`, `order`, `trend` (HEALTHeLINK shows these).
- Provider role code on encounter providers.
- ISO dates with timezone.

## Condensed example

```json
{
  "given": "Marcus", "family": "Evans", "gender": "M", "dob": "06/01/1950", "age": 76,
  "addr": "179 Bednar Knoll Suite 2, Bronx, NY 10467",
  "race": "white", "eth": "non-hispanic", "lang": "en-US",
  "mpid": "MARCUS-GOLDEN-0001",
  "mrn_list": [
    { "qe": "BRONX",  "source": "BXLEB",  "mrn": "515366" },
    { "qe": "GRRHIO", "source": "RGH",    "mrn": "799628" },
    { "qe": "GRRHIO", "source": "UR1244", "mrn": "312806" }
  ],
  "problems": [
    { "name": "Diabetes mellitus type 2 (disorder)", "onset": "03/01/2012", "resolved": "", "status": "Active" }
  ],
  "meds": [
    { "name": "Metformin hydrochloride 500 MG Oral Tablet", "start": "04/01/2012", "stop": "",
      "code": "861007", "status_code": "active", "dose": "1 tablet", "route": "Oral",
      "frequency": "twice daily", "prescriber": "Dr. James Okafor", "refills": "5",
      "indication": "Diabetes mellitus type 2 (disorder)",
      "sig": "Take 1 tablet by mouth twice daily" }
  ],
  "labs": [
    { "panel": "Basic metabolic panel - Blood", "date": "03/15/2025",
      "comps": [
        { "test": "Glucose [Mass/volume] in Blood", "value": "81.78", "unit": "mg/dL", "flag": "",
          "range": "", "date": "03/15/2025", "loinc": "2339-0", "status_code": "completed",
          "panel": "Basic metabolic panel - Blood" },
        { "test": "Creatinine [Mass/volume] in Blood", "value": "1.01", "unit": "mg/dL", "flag": "",
          "range": "", "date": "03/15/2025", "loinc": "38483-4", "status_code": "completed",
          "panel": "Basic metabolic panel - Blood" }
      ] }
  ],
  "oru": [
    { "test": "Glucose", "loinc": "2339-0", "value": "81.78", "unit": "mg/dL", "date": "03/15/2025",
      "flag": "Normal", "range": "70-99" },
    { "test": "Hemoglobin A1c", "loinc": "4548-4", "value": "6.1", "unit": "%", "date": "03/15/2025",
      "flag": "High", "range": "4.0-5.6" }
  ],
  "imms": [ { "name": "Influenza, seasonal, injectable, preservative free", "date": "06/23/2024" } ],
  "vitals": [ { "test": "Body Weight", "value": "64.5", "unit": "kg", "date": "06/17/2018" } ],
  "procs": [ { "name": "Physical examination procedure (procedure)", "date": "12/29/2024" } ],
  "allergies": [],
  "encs": [
    { "name": "Emergency room admission", "etype": "Emergency room admission",
      "start": "11/02/2024", "stop": "11/03/2024",
      "facility": "Montefiore Medical Center - Emergency Department",
      "attending": "Dr. David Rosenberg", "pcp": "Dr. James Okafor",
      "disposition": "Discharged to home", "reason": "Chest pain (finding)" }
  ]
}
```

## About the sample patient

Marcus Evans is one synthetic person who appears in 10 sources across 5 QEs. Each source contributes a different subset of data, which is why the merge and de-duplication rules matter. He has five conditions (type 2 diabetes, hypertension, hyperlipidemia, CKD stage 3, osteoarthritis), a realistic ten-drug regimen, five hospital and clinic encounters, and a shared 2025-03-15 lab panel that appears both as a document result and as a lab feed result.

Known noise: the vitals, immunizations, procedures and most labs come from a random synthetic-data generator and are not clinically consistent with Marcus (for example a 150 cm height). Only the conditions, medications, encounters, MRNs and the 2025-03-15 labs are curated. Do not read clinical meaning into the rest.
