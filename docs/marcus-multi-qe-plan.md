# Marcus Multi-QE Plan

## Problem

Today every QE portal view (Hixny, HEALTHeLINK, Bronx) shows the **same merged record** from all 10 sources. When you demo and switch QEs, nothing changes — it's the same data in a different skin. That's wrong. Each QE should only see its own data, the way a real QE portal works.

## What we have now

| QE | Sources (AA) | CCDs | ORUs | TRNs |
|---|---|---|---|---|
| HIXNY | SPLPCPRIME, ALBMC | 2 | 2 | 0 |
| HEALTHeLINK | KINGSB, ECMC | 2 | 2 | 0 |
| HEALTHIX | MSSM, NYP | 2 | 2 | 0 |
| HEALTHECONN | UHS | 1 | 1 | 0 |
| BRONX | BXLEB | 1 | 1 | 0 |
| GRRHIO (Rochester) | UR1244, RGH | 2 | 2 | 0 |

**Problems:**
1. BRONX and HEALTHECONN only have 1 source each — need 3
2. No TRN documents exist at all
3. `merge_by_person()` merges ALL 10 sources into one record. No QE filtering happens.
4. All three build scripts load all CCDs and render all data — `VIEW_QE` is cosmetic only.

## What we want

| QE | Sources (AA) | CCDs | ORUs | TRNs |
|---|---|---|---|---|
| HIXNY | SPLPCPRIME, ALBMC, ELLS | 3 | 3 | 3 |
| HEALTHeLINK | KINGSB, ECMC, RPCI | 3 | 3 | 3 |
| HEALTHIX | MSSM, NYP, BELLEVUE | 3 | 3 | 3 |
| HEALTHECONN | UHS, SJHHC, UPSTATE | 3 | 3 | 3 |
| BRONX | BXLEB, SBH, MMC | 3 | 3 | 3 |
| Rochester | skip | — | — | — |

Each QE view filters to **only that QE's MRNs and clinical data**. When you open the Hixny view, you see Marcus with 3 CCDs, 3 ORU feeds, and 3 TRNs — all from HIXNY sources. Switch to Bronx, different data, different encounters, different labs.

## Approach: Option A — Per-QE folders (simpler, recommended)

Rather than tagging every parsed item with a source QE and filtering on render, reorganize the data into per-QE folders and point each build at the right folder. This matches how a real QE works: they only have their own data.

```
marcus_bundle/
  hixny/
    ccda/    (3 CCDs)
    oru-hl7/ (3 ORUs)
    trn/     (3 TRNs)
  healthelink/
    ccda/    oru-hl7/    trn/
  healthix/
    ccda/    oru-hl7/    trn/
  healtheconn/
    ccda/    oru-hl7/    trn/
  bronx/
    ccda/    oru-hl7/    trn/
  mpi/marcus_mpi.csv
  README.md
```

## Tasks

1. **Create missing CCDs** — get each QE to 3 sources. Remove Rochester. Use existing Synthea base CCDs from `ccds/` re-stamped with Marcus identity.
2. **Create matching ORU files** — one HL7 ORU per source, varying lab values.
3. **Create TRN documents** — minimal C-CDA discharge summaries, 3 per QE.
4. **Reorganize into per-QE folders** — move existing + new files into the structure above.
5. **Update build pipeline** — `build_home.py` points each QE build at its own folder. Add Healthix and HealtheConnections as live views.
6. **Update MPI, README, deploy script** — reflect the new 15-source structure.

## Prototype link

https://main.d3pz3oj6iuj9t4.amplifyapp.com
