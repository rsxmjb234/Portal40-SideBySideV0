# Healthix – QE-specific requirements

Status: **Not built. "Coming soon" card on the home page.** No view exists yet.
Region: New York City and Long Island. Site: https://healthix.org. Accent `#059669`.
QE code in data and tickets: `HEALTHIX`. Sources in sample data: `HEALTHIX|MSSM`, `HEALTHIX|NYP`.

## What is known

- Largest public HIE in the nation, with data on roughly 20 million or more patients from thousands of organizations (from the Healthix site).
- Its volume means the viewer must handle **large merged records**. The demo's Marcus record (about 840 lab results) is small by comparison.

## Needed before building

Healthix clinical viewer screenshots, user guide and sample document layouts have **not been collected**. See `QE-Example-Materials/Healthix/NOTES.md`. The view style, navigation, section names and columns are all unknown.

## What the Healthix view must do regardless

- Apply every rule in [02-data-processing.md](../02-data-processing.md) (merge, de-duplication, CCD/ORU reconciliation, drill-in).
- Show the home page card per [01-home-page.md](../01-home-page.md) and switch it to "live" by configuration.
- Include the **MRN Array** and **Missing data** buttons, auto-filling the QE field with `HEALTHIX`.
- **[Prod]** Large-record behavior: paging or virtualized tables, server-side sort and filter, and a response-time target agreed with Healthix.


## Acceptance criteria (minimum before marking live)

- [ ] Home page card shows "Coming soon" and switches to live by a config change only.
- [ ] All rules in [02-data-processing.md](../02-data-processing.md) apply once built (merge, de-dup, lab reconciliation, drill-in).
- [ ] MRN Array and Missing data buttons present, QE field auto-fills to this QE's code.
- [ ] Reference materials (screenshots, user guide) collected and QE-specific requirements confirmed with the QE before building the view.

## Open questions

- Viewer look and navigation (collect screenshots first).
- Authentication, consent and break-the-glass rules.
- Which data types Healthix exposes (ADT alerts, documents, images).
- Expected record sizes and performance targets.
