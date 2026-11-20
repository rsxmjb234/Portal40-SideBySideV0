# 01 – Home Page (one card per QE)

Screenshot: [images/home.png](images/home.png)

## Purpose

The home page is the entry point. A user chooses a **Qualified Entity (QE)**. The next screen shows the same patient record in that QE's own look, navigation and terminology. One underlying record, many QE presentations.

## Page layout [Demo]

1. **Header band** (teal gradient): logo mark, title "SHIN-NY Community Health Record", subtitle line, and a status pill. **[Demo]** The demo subtitle reads "One patient record, rendered in each Qualified Entity's own style – N live, more coming soon" and the pill reads "N synthetic patients · C-CDA + genuine HL7 ORU". Replace both with production-appropriate wording (remove synthetic/C-CDA references).
2. **Section label** "Choose a Qualified Entity (QE)".
3. **QE card grid**: responsive, minimum card width 240 px, 18 px gap. One card per QE.
4. **Explanatory note** describing that every QE renders the same record and the de-duplication rule (see doc 02).
5. **Footer disclaimer**: synthetic data only; QE names and links belong to their organizations; styled wordmarks stand in for official logos; FHIR is an HL7 trademark.

## QE card requirements (apply to every QE)

Each card **must** show:

| Element | Rule |
|---------|------|
| QE name | Styled wordmark in the QE's accent color (no official logo unless licensed). |
| Region | One line, for example "Capital Region". |
| Accent color | Top border 4 px and name text use the QE color. |
| Action | **Live** QE: link "Open the {QE} view →". **Not live**: gray "Coming soon" badge, card dimmed, not clickable. |
| QE website | Small link to the QE's public site, opens in a new tab (`rel="noopener"`), pinned to the card bottom. |

Behavior:
- Live cards lift 3 px on hover. Coming-soon cards do not.
- Cards are driven by configuration (name, region, color, site, route, live flag), not hard-coded markup, so adding a QE is a config change.
- **[Prod]** Cards **must** be filtered by the signed-in user's entitlements. A user sees (or can open) only the QEs they are authorized for. The demo shows all cards to everyone.
- **[Prod]** The home page **must** be reached only after authentication and the access acknowledgement required by each QE. See each QE file.

## Per-QE card configuration

| QE | Region | Accent | Public site | Status | View style | Detail file |
|----|--------|--------|-------------|--------|------------|-------------|
| Hixny | Capital Region | `#0e7490` | hixny.org | **Live** | Card dashboard + tabs ("SMART on FHIR"-style) | [qe/hixny.md](qe/hixny.md) |
| HEALTHeLINK | Western New York | `#1d4ed8` | wnyhealthelink.com | **Live** | Fusion clinical viewer (banner + Chartbook left nav) | [qe/healthelink.md](qe/healthelink.md) |
| Bronx RHIO | The Bronx (IMAT Solutions) | `#b91c1c` | bronxrhio.org | **Live** | IMAT Provider Clinical Viewer (left nav + zebra tables) | [qe/bronx-rhio.md](qe/bronx-rhio.md) |
| Healthix | NYC & Long Island | `#059669` | healthix.org | Coming soon | TBD | [qe/healthix.md](qe/healthix.md) |
| HealtheConnections | Central NY, North Country & more | `#ea580c` | healtheconnections.org | Coming soon | TBD | [qe/healtheconnections.md](qe/healtheconnections.md) |
| Rochester RHIO | Finger Lakes & Southern Tier | `#7c3aed` | rochesterrhio.org | Coming soon | TBD | [qe/rochester-rhio.md](qe/rochester-rhio.md) |

Card order is the order above (live first within the demo's ordering: Hixny, HEALTHeLINK, Healthix, HealtheConnections, Rochester RHIO, Bronx RHIO). Keep the order configurable.

## What every QE view must contain once opened

These are common to all QEs. QE-specific differences are in the QE files.

1. **Patient context** always visible: name, DOB, age, sex, the QE and source MRN for this view, and the MPID.
2. **Section navigation** (tabs, Chartbook or left nav, depending on the QE). Sections with no data are visibly disabled or marked, not hidden.
3. **Sections** (names vary by QE): Summary, Conditions/Problems, Allergies, Medications, Labs, Vitals/Observations, Immunizations, Procedures, Encounters/ADT, Demographics.
4. **Top-bar buttons** (orange): **MRN Array** and **Missing data**. See [03-missing-data-logging.md](03-missing-data-logging.md).
5. **Drill-in detail**: clicking any data row opens a detail panel with the full record. See doc 02, section 9.
6. **Back to home** control.
7. The view declares its QE (`data-view-qe` in the demo). The Missing data form uses it to auto-fill the QE field.

## Patient search and navigation [Prod]

The home page shows the QE choices. Once a user opens a QE view they need a patient. The demo uses a dropdown picker (a demo-only control — see [05-ui-design.md](05-ui-design.md) section 6). The production requirement is:

- A user **must** search for a patient before data is shown. There is no browse or list.
- Minimum required search fields (from HEALTHeLINK Fusion and standard HIE practice): **Last name**, **First name**, **Date of birth**. All three required.
- Search results show: Name, Age, Sex, DOB, Address, MPID. A caret or expand control shows the per-source rows (MRN, Assigning Authority / QE|Source, data types available).
- Selecting a patient opens that person's QE view.
- **[Prod]** Search results are filtered by the signed-in user's entitlements. Consent gates what is shown. No result is returned for a patient the user is not authorized to view.
- The per-source rows in search results draw from the same MRN array that feeds the MRN Array button.

Confirm the exact search flow with each QE — it may differ (HEALTHeLINK has its own flow, Hixny launches from an EHR with the patient already in context).

## Acceptance criteria

- [ ] Home lists every configured QE; live ones open, others show "Coming soon".
- [ ] Adding a QE needs only a config entry plus a view.
- [ ] Each opened view shows the same patient facts (name, DOB, conditions, meds, encounters, labs) as every other QE view for the same person.
- [ ] **[Prod]** A user cannot open a QE they are not entitled to, including by typing the URL.
