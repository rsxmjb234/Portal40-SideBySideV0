# Marcus Evans — golden cross-source test person (synthetic)

One synthetic person who intentionally spans 5 SHIN-NY QE sources (3 facilities
each, 15 total) so he can be linked in the MPI and used to demo cross-source
matching, de-duplication, and per-QE filtering.

## Identity
  name: Marcus Evans   DOB: 1950-06-01   sex: M
  shared MPID: MARCUS-GOLDEN-0001
  address: 179 Bednar Knoll Suite 2, New York, NY, 11367

## Source identities (15 total, no Rochester/GRRHIO)
  HIXNY         | SPLPCPRIME | mrn=956304 eid=HI-EID-5976 | base=BRONX-MPID-000032_Dwain139_Hartmann983_e...
  HIXNY         | ALBMC      | mrn=945947 eid=HI-EID-5392 | base=BRONX-MPID-000053_Deshawn686_Wilkinson79...
  HIXNY         | ELLS       | mrn=671234 eid=HI-EID-6012 | base=BRONX-MPID-000068_Shenita872_Osinski784_...
  HEALTHELINK   | KINGSB     | mrn=832368 eid=HE-EID-9965 | base=BRONX-MPID-000024_Peter292_Olson653_1dea...
  HEALTHELINK   | ECMC       | mrn=881691 eid=HE-EID-9109 | base=BRONX-MPID-000031_Millard193_Beahan375_a...
  HEALTHELINK   | RPCI       | mrn=748293 eid=HE-EID-7541 | base=BRONX-MPID-000092_Janeth814_Loree183_Sch...
  HEALTHIX      | MSSM       | mrn=340474 eid=HE-EID-8304 | base=BRONX-MPID-000003_Lessie363_Cartwright18...
  HEALTHIX      | NYP        | mrn=811058 eid=HE-EID-6843 | base=BRONX-MPID-000005_Cary869_Mante251_94f83...
  HEALTHIX      | BELLEVUE   | mrn=529417 eid=HE-EID-4218 | base=BRONX-MPID-000094_Haydee844_Elna874_Beah...
  HEALTHECONN   | UHS        | mrn=826608 eid=HE-EID-2717 | base=BRONX-MPID-000101_Carly657_Sparkle906_Bi...
  HEALTHECONN   | SJHHC      | mrn=413856 eid=HE-EID-3298 | base=BRONX-MPID-000003_Lessie363_Cartwright18...
  HEALTHECONN   | UPSTATE    | mrn=697215 eid=HE-EID-5107 | base=BRONX-MPID-000031_Millard193_Beahan375_a...
  BRONX         | BXLEB      | mrn=515366 eid=BR-EID-1665 | base=BRONX-MPID-000094_Haydee844_Elna874_Beah...
  BRONX         | SBH        | mrn=284731 eid=BR-EID-2194 | base=BRONX-MPID-000024_Peter292_Olson653_1dea...
  BRONX         | MMC        | mrn=362948 eid=BR-EID-3017 | base=BRONX-MPID-000053_Deshawn686_Wilkinson79...

## Folder structure
  marcus_bundle/
    {qe_lower}/
      ccda/       3 C-CDA Continuity of Care Documents per QE
      oru-hl7/    3 HL7 v2.5.1 ORU^R01 lab messages per QE
      trn/        3 C-CDA Discharge Summary (TRN) documents per QE
    mpi/
      marcus_mpi.csv   MPI anchor rows (15 rows + header)

## QE subfolders
  - hixny/       — SPLPCPRIME, ALBMC, ELLS
  - healthelink/ — KINGSB, ECMC, RPCI
  - healthix/    — MSSM, NYP, BELLEVUE
  - healtheconn/ — UHS, SJHHC, UPSTATE
  - bronx/       — BXLEB, SBH, MMC

## File types
  CCD (.xml)  — Full clinical document with conditions, meds, labs, vitals,
                immunizations, procedures, encounters from the Synthea base.
                Each uses a *different* base CCD for clinical variety.
  ORU (.hl7)  — Basic Metabolic Panel with Glucose, Creatinine, Sodium, HbA1c.
                Values vary per source; HbA1c always flagged High (diabetes).
  TRN (.xml)  — Discharge summary with one encounter and Marcus's 5 shared
                conditions (DM2, HTN, Hyperlipidemia, CKD3, Osteoarthritis).

## De-duplication
  When all 3 CCDs from one QE are loaded together, merge_by_person() groups them
  by MPID into one virtual record. Each QE's view should show only that QE's 3
  source identities, not data from other QEs.

All data is 100% synthetic. Demonstration only.
