# Phase 1 Data Audit

This audit profiles the four supplied raw datasets before label construction or modeling.

## Dataset Inventory

| dataset                | rows | missing_values |
| ---------------------- | ---- | -------------- |
| queries.csv            | 500  | 0              |
| content.csv            | 345  | 0              |
| behavioral_signals.csv | 1500 | 0              |
| impressions.csv        | 7190 | 0              |

## Queries

- Rows: 500
- Unique query IDs: 500
- Duplicate query IDs: 0
- Missing values: 0
- Median query length: 7.0 words
- Queries without recognized disease/molecule/drug-class entities: 0 (0.0%)
- Near-duplicate/paraphrase candidate pairs at threshold: 30
- Manual review sample rows: 120

Language distribution:

| language | count |
| -------- | ----- |
| EN       | 222   |
| MIXED    | 173   |
| ID       | 105   |

Language examples from supplied labels:

| language | query_id | query_text                                                                     |
| -------- | -------- | ------------------------------------------------------------------------------ |
| EN       | Q001     | is Diazepam safe in Febrile Seizure with immunocompromised                     |
| EN       | Q002     | SGLT2 inhibitors adverse effects monitoring in Atrial Fibrillation             |
| EN       | Q005     | Penicillins in pregnancy and HIV/AIDS                                          |
| EN       | Q007     | Hydroxychloroquine hepatic impairment dose in Rheumatoid Arthritis             |
| EN       | Q008     | Short-acting beta2-agonists adverse effects monitoring in Asthma               |
| ID       | Q003     | interaksi obat Nivolumab dan Nivolumab pada Colorectal Cancer                  |
| ID       | Q018     | interaksi obat Losartan dan Empagliflozin pada Chronic Kidney Disease          |
| ID       | Q022     | resistensi Methyldopa pada Hypertension in Pregnancy alternatif Methyldopa     |
| ID       | Q032     | interaksi obat Ramipril dan Spironolactone pada Heart Failure                  |
| ID       | Q035     | algoritma terapi HIV/AIDS step up                                              |
| MIXED    | Q004     | Apixaban efficacy pada Deep Vein Thrombosis clinical outcome data              |
| MIXED    | Q006     | kombinasi Metoprolol dan Metoprolol pada Heart Failure aman atau tidak         |
| MIXED    | Q011     | Psoriasis dengan renal impairment penyesuaian dosis Tacrolimus topical         |
| MIXED    | Q012     | Artemether-lumefantrine pada pasien elderly Typhoid Fever apa perlu adjustment |
| MIXED    | Q013     | kontraindikasi Bedaquiline pada Tuberculosis dengan anaemia                    |

Top therapeutic areas:

| therapeutic_area   | count |
| ------------------ | ----- |
| Pulmonology        | 73    |
| Cardiology         | 61    |
| Infectious Disease | 60    |
| Endocrinology      | 48    |
| Rheumatology       | 43    |
| Psychiatry         | 41    |
| Neurology          | 33    |
| Oncology           | 32    |
| Critical Care      | 18    |
| Pediatrics         | 17    |

## Content

- Rows: 345
- Unique content IDs: 345
- Duplicate content IDs: 0
- Missing values: 0
- Median word count: 1068.0
- Near-duplicate title candidate pairs at threshold: 23

Content-type distribution:

| content_type     | count |
| ---------------- | ----- |
| article          | 109   |
| clinical_summary | 90    |
| case_report      | 50    |
| guideline        | 47    |
| drug_profile     | 35    |
| review           | 14    |

Content-side dimensions that can support matching are saved in `tables/content/matchable_dimensions.csv`.

## Behavioral Signals

- Events: 1500
- Unique sessions/doctors/queries/content: 663 / 117 / 350 / 175
- Duplicate events on session-doctor-query-content-event-timestamp key: 0
- Median dwell seconds: 23.0
- Max dwell seconds: 353
- Zero-dwell events: 66
- Repeated doctor-query-content engagement rows: 0
- Suspicious pattern rows written: 79

Event-type distribution:

| event_type    | count |
| ------------- | ----- |
| click         | 944   |
| scroll_deep   | 436   |
| save_bookmark | 91    |
| return_visit  | 29    |

## Impressions

- Impressions: 7190
- Unique sessions/queries/content: 813 / 500 / 345
- Duplicate impression IDs: 0
- Engaged impressions: 1500 (20.9%)
- Unengaged impressions: 5690 (79.1%)
- No explicit rank/position column is present; rank-like position is inferred by timestamp within each session-query group for exploratory bias checks.

Important label caveat: an unengaged impression should not be treated as automatically irrelevant because position bias, examination bias, answer satisfaction without click, competing relevant results, and limited session time can all produce non-engagement.

## Phase 1 Takeaways

- The raw files are complete by missing-value checks and have unique primary IDs.
- Query and content both expose disease, molecule, drug class, therapeutic area, and language, so structured matching is feasible.
- Query text contains contextual constraints such as age/pediatric, pregnancy, year, renal/hepatic function, dosing, comparisons, and prior treatment failure that are not represented in the supplied NER columns.
- Behavioral labels should use graded evidence from event type and dwell time rather than binary clicked/not-clicked labels.
- Impression order can support bias-aware analysis, but only via inferred rank from serving timestamps.

## Artifacts

- Metrics JSON: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_metrics.json`
- Manual query review sample: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_query_manual_review.csv`
- Query near duplicates: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_query_near_duplicates.csv`
- Content near duplicates: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_content_near_duplicates.csv`
- Suspicious behavioral rows: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_suspicious_behavior.csv`
- Detailed tables: `/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables`
