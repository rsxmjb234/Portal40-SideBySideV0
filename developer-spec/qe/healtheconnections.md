# HealtheConnections – QE-specific requirements

Status: **Not built. "Coming soon" card on the home page.** No view exists yet.
Region: Central NY (Syracuse), North Country, Southern Tier, Mohawk Valley, Mid-Hudson. Site: https://www.healtheconnections.org. Accent `#ea580c`.
QE code in data and tickets: `HEALTHECONN`. Source in sample data: `HEALTHECONN|UHS`.

## What is known (from the QE's public site)

- Serves 1,600+ health and care organizations.
- Awarded the SHIN-NY **statewide encounter alerts (ADT)** service, in partnership with PointClickCare. This makes the **ADT / Encounters section a priority** for this QE.
- **Rochester RHIO is migrating its HIE services into HealtheConnections** (data-feed migration into early 2027). See [rochester-rhio.md](rochester-rhio.md).
- A public HIE user guide PDF exists on their site and has not yet been collected.

## Needed before building

HIE portal screenshots and the user guide. See `QE-Example-Materials/HealtheConnections/NOTES.md`. View style, navigation and columns are unknown.

## What the HealtheConnections view must do regardless

- Apply every rule in [02-data-processing.md](../02-data-processing.md), including the ADT field set (facility, admit/discharge, attending, PCP, disposition, reason) in section 8.
- Include **MRN Array** and **Missing data**, auto-filling QE with `HEALTHECONN`.
- Support absorbing Rochester RHIO sources later. The model already treats sources as `QE|Source`, so migrated Rochester sources become additional `HEALTHECONN|<Source>` entries (or stay `GRRHIO|<Source>` during transition). **Decide which, before data is migrated**, because the MRN array and tickets key on this value.
- **[Prod]** Statewide encounter alerts: define whether alerts (real-time ADT notifications) appear in the viewer, on the home page, or both.


## Acceptance criteria (minimum before marking live)

- [ ] Home page card shows "Coming soon" and switches to live by a config change only.
- [ ] All rules in [02-data-processing.md](../02-data-processing.md) apply once built (merge, de-dup, lab reconciliation, drill-in).
- [ ] MRN Array and Missing data buttons present, QE field auto-fills to this QE's code.
- [ ] Reference materials (screenshots, user guide) collected and QE-specific requirements confirmed with the QE before building the view.

## Open questions

- Viewer look and navigation (collect the user guide first).
- ADT alert presentation and the PointClickCare feed format.
- Migration timeline and identifier handling for Rochester RHIO sources.
- Authentication, consent and break-the-glass rules.
