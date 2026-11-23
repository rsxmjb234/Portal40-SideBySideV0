# Sample Patients — Synthetic Cross-Source Test Data

10 synthetic patients, each spanning multiple SHIN-NY QE
sources for MPI linkage, de-duplication, and per-QE filtering demos.

All data is 100% synthetic. Demonstration only.

## Patients

### Marcus Evans (`marcus_evans`)
  DOB: 1950-06-01  Sex: M  MPID: MARCUS-GOLDEN-0001
  5 QEs, 15 sources
  Conditions: Diabetes mellitus type 2, Essential hypertension, Hyperlipidemia, Chronic kidney disease stage 3, Osteoarthritis

### Gloria Washington (`gloria_washington`)
  DOB: 1948-12-15  Sex: F  MPID: GLORIA-GOLDEN-0002
  4 QEs, 8 sources
  Conditions: Congestive heart failure, Atrial fibrillation, Coronary arteriosclerosis, Essential hypertension

### Robert Chen (`robert_chen`)
  DOB: 1955-10-30  Sex: M  MPID: ROBERT-GOLDEN-0003
  3 QEs, 6 sources
  Conditions: Chronic obstructive lung disease, Asthma, Pulmonary hypertension, Essential hypertension

### Dolores Ramirez (`dolores_ramirez`)
  DOB: 1962-04-14  Sex: F  MPID: DOLORES-GOLDEN-0004
  4 QEs, 8 sources
  Conditions: Chronic kidney disease stage 4, Diabetes mellitus type 2, Essential hypertension, Anemia, Hyperlipidemia

### James Thompson (`james_thompson`)
  DOB: 1958-07-22  Sex: M  MPID: JAMES-GOLDEN-0005
  3 QEs, 6 sources
  Conditions: Cerebrovascular accident, Epilepsy, Essential hypertension, Hyperlipidemia

### Sonia Petrova (`sonia_petrova`)
  DOB: 1970-11-08  Sex: F  MPID: SONIA-GOLDEN-0006
  3 QEs, 6 sources
  Conditions: Crohn's disease, Cirrhosis of liver, Portal hypertension, Anemia

### Angela Mitchell (`angela_mitchell`)
  DOB: 1975-03-25  Sex: F  MPID: ANGELA-GOLDEN-0007
  4 QEs, 8 sources
  Conditions: Rheumatoid arthritis, Systemic lupus erythematosus, Chronic kidney disease stage 2, Essential hypertension

### David Park (`david_park`)
  DOB: 1983-09-17  Sex: M  MPID: DAVID-GOLDEN-0008
  3 QEs, 6 sources
  Conditions: Diabetes mellitus type 1, Hypothyroidism, Obesity, Hyperlipidemia

### William Harris (`william_harris`)
  DOB: 1945-06-03  Sex: M  MPID: WILLIAM-GOLDEN-0009
  4 QEs, 8 sources
  Conditions: Malignant neoplasm of colon, Anemia, Deep venous thrombosis, Essential hypertension

### Evelyn Rodriguez (`evelyn_rodriguez`)
  DOB: 1940-02-18  Sex: F  MPID: EVELYN-GOLDEN-0010
  5 QEs, 11 sources
  Conditions: Congestive heart failure, Chronic obstructive lung disease, Diabetes mellitus type 2, Chronic kidney disease stage 3, Atrial fibrillation, Osteoporosis

## Folder Structure

```
sample_patients/
  {patient_id}/
    {qe_lower}/
      ccda/       C-CDA Continuity of Care Documents
      oru-hl7/    HL7 v2.5.1 ORU^R01 lab messages
      trn/        C-CDA Discharge Summary (TRN) documents
    mpi/
      {patient_id}_mpi.csv   MPI anchor rows
```

## Generation

```
python generate_patients.py                           # all patients
python generate_patients.py --patient marcus_evans    # one patient
```
