# SHIN-NY Community Health Record (PDR) – Developer Specification

Audience: the developer building this inside the secure portal.
Source of truth for behavior: the working demo (below) plus these documents.
All demo data is 100% synthetic.

## Start here

1. Read [00-start-here.md](00-start-here.md) for what exists, what was decided, and the build order.
2. Everything else is reference. Feed all the `.md` files to the model or developer; use `fixtures/` as test data and `images/` as visual reference.

## Data assumption

The viewer is built on data returned by **PDR**. These documents **assume PDR returns person data shaped like the demo's merged record** ([04-pdr-data-model.md](04-pdr-data-model.md)). They do **not** describe how to call PDR. The team already knows that. The demo itself read static files; none of that file handling is part of the new build.

## Reading order

| # | File | What it covers |
|---|------|----------------|
| 6 | [00-start-here.md](00-start-here.md) | Purpose, decisions made, status, gaps, build order, a starter prompt |
| 1 | [01-home-page.md](01-home-page.md) | Home page, one card per Qualified Entity (QE) |
| 2 | [02-data-processing.md](02-data-processing.md) | Rules for **every** QE: identity, merge, de-duplication, lab reconciliation, drill-in |
| 3 | [03-missing-data-logging.md](03-missing-data-logging.md) | "Missing data" tickets and MRN Array (full build spec) |
| 4 | [04-pdr-data-model.md](04-pdr-data-model.md) | The assumed shape of the data the viewer receives, with an example |
| 5 | [05-ui-design.md](05-ui-design.md) | Visual design of each view and the shared widgets, with screenshots |
| - | [qe/](qe/) | One file per QE with QE-specific needs |
| - | `fixtures/` | `marcus_evans.json` (full), `marcus_evans.sample.json` (short) |
| - | `images/` | Screenshots of every view and widget |

QE files: [Hixny](qe/hixny.md) · [HEALTHeLINK](qe/healthelink.md) · [Bronx RHIO](qe/bronx-rhio.md) ·
[Healthix](qe/healthix.md) · [HealtheConnections](qe/healtheconnections.md) · [Rochester RHIO](qe/rochester-rhio.md)

## Terms

| Term | Meaning |
|------|---------|
| PDR | The portal being built (the record viewer that merges data for a person). |
| QE | Qualified Entity: a regional SHIN-NY health information exchange (Hixny, HEALTHeLINK, Bronx RHIO, ...). |
| Source | A contributing organization inside a QE (hospital, practice). Identified as `QE\|Source`. |
| MRN | Medical record number assigned by a source. One person has many MRNs. |
| MPID | Cross-QE person key shared by all of a person's records (demo: `MARCUS-GOLDEN-0001`). |
| EID | A QE's own enterprise ID for the person. |
| CCD / C-CDA | XML clinical document (problems, meds, labs, encounters, ...). |
| ORU | HL7 v2.5.1 `ORU^R01` lab result message. |
| ADT | Admit / Discharge / Transfer events (shown as Encounters). |
| Virtual record | The single merged view of one person built from every source. |

## Requirement language

"**Must**" = required. "**Should**" = expected unless there is a reason not to.
Each requirement is tagged where it matters:

- **[Demo]** behavior already implemented and visible in the demo.
- **[Prod]** requirement for the secure portal that the demo does not implement (for example authentication, consent, audit). These are listed so they are not missed. Confirm detail with the product owner and each QE.

## The demo (reference implementation)

- Live: https://main.d3pz3oj6iuj9t4.amplifyapp.com
- Code: https://github.com/rsxmjb234/Portal40-SideBySideV0
- 10 synthetic patients, led by **Marcus Evans** (DOB 06/01/1950, M), each with clinically coherent conditions, labs, and encounters. Marcus appears in 10 sources across 5 QEs, rendered in five QE styles from the same merged data.

The demo is static HTML generated at build time. The secure portal is dynamic. Treat the demo as the behavioral reference and these documents as the requirements. File map: [00-start-here.md](00-start-here.md), section 6.
