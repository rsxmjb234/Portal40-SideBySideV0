# Rochester RHIO – QE-specific requirements

Status: **Not built. "Coming soon" card on the home page.** No view exists yet.
Region: Finger Lakes and Southern Tier (14 counties, about 1.5 million residents). Sites: https://rochesterrhio.org and https://grrhio.org (provider portal). Accent `#7c3aed`.
QE code in data and tickets: `GRRHIO`. Sources in sample data: `GRRHIO|UR1244`, `GRRHIO|RGH`.

## Key point: this QE may not stay a separate view

Rochester RHIO is **transitioning its HIE services to HealtheConnections** (data-feed migration into early 2027). After that, services are delivered through HealtheConnections. See [healtheconnections.md](healtheconnections.md).

**Do not build a Rochester RHIO view until the product owner confirms** whether it will be:
1. a separate view for the transition period, or
2. folded into HealtheConnections (the home card is retired and `GRRHIO` sources appear under HealtheConnections).

## What is needed regardless

- `GRRHIO|<Source>` identifiers **must** continue to be recognized in the MRN array and in tickets, because historical tickets and merged records reference them.
- If the view is built, it follows the same rules as every QE: [02-data-processing.md](../02-data-processing.md), **MRN Array**, **Missing data** with the QE field auto-filled to `GRRHIO`.
- The home page card is configuration only (live flag, route). Retiring it must not break existing links or tickets.

## Needed before building

Provider portal screenshots and guide, or confirmation that the portal is superseded. See `QE-Example-Materials/RochesterRHIO/NOTES.md`.


## Acceptance criteria (minimum before marking live)

- [ ] Home page card shows "Coming soon" and switches to live by a config change only.
- [ ] All rules in [02-data-processing.md](../02-data-processing.md) apply once built (merge, de-dup, lab reconciliation, drill-in).
- [ ] MRN Array and Missing data buttons present, QE field auto-fills to this QE's code.
- [ ] Reference materials (screenshots, user guide) collected and QE-specific requirements confirmed with the QE before building the view.

## Open questions

- Separate view, or fold into HealtheConnections? Until when?
- How are `GRRHIO` MRNs and assigning authorities re-labelled after migration?
- Viewer look and navigation if a separate view is needed.
