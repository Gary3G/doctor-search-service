# Phase 1.6 Contextual Slot Extraction

This phase populates the selected Phase 1.5 contextual query schema using deterministic rules.

## Output

- Enriched queries: `/Users/hol/Documents/Task/doctor-search-service/data/processed/queries_with_contextual_slots.csv`
- Extraction summary: `/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_summary.csv`
- Extraction examples: `/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_examples.csv`
- QA review sample: `/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_quality_review.csv`

## Populated Slot Coverage

| column                       | populated_rows | population_pct | top_values                       |
| ---------------------------- | -------------- | -------------- | -------------------------------- |
| age_group                    | 25             | 0.05           | elderly=13; pediatric=12         |
| pregnancy_status             | 37             | 0.074          | pregnant=30; pregnancy_related=7 |
| year                         | 29             | 0.058          | 2023=9; 2025=7; 2022=7; 2024=6   |
| recency_flag                 | 49             | 0.098          | true                             |
| dose_context_flag            | 93             | 0.186          | true                             |
| route                        | 3              | 0.006          | topical=2; inhaled=1             |
| renal_function_group         | 22             | 0.044          | renal_impairment=22              |
| hepatic_impairment_flag      | 21             | 0.042          | true                             |
| comparison_flag              | 23             | 0.046          | true                             |
| negation_flag                | 10             | 0.02           | true                             |
| prior_treatment_failure_flag | 24             | 0.048          | true                             |

Queries with at least one extracted contextual slot: 242

## Example Extractions

| column           | query_id | query_text                                                                            | extracted_value   |
| ---------------- | -------- | ------------------------------------------------------------------------------------- | ----------------- |
| age_group        | Q012     | Artemether-lumefantrine pada pasien elderly Typhoid Fever apa perlu adjustment        | elderly           |
| age_group        | Q014     | Malaria pediatric dosing Tenofovir disoproxil                                         | pediatric         |
| age_group        | Q036     | Atrial Fibrillation pediatric dosing Empagliflozin                                    | pediatric         |
| age_group        | Q063     | Malaria pada anak dosis Tenofovir disoproxil                                          | pediatric         |
| age_group        | Q091     | Liraglutide pada pasien elderly Obesity apa perlu adjustment                          | elderly           |
| age_group        | Q097     | Iron Deficiency Anaemia pada anak dosis Ferrous sulphate                              | pediatric         |
| age_group        | Q116     | Osteoporosis dengan elderly patients pilihan drug terbaik                             | elderly           |
| age_group        | Q122     | Tenofovir+Lamivudine pada pasien elderly Urinary Tract Infection apa perlu adjustment | elderly           |
| pregnancy_status | Q005     | Penicillins in pregnancy and HIV/AIDS                                                 | pregnant          |
| pregnancy_status | Q010     | renal dose adjustment Magnesium sulphate in Preeclampsia                              | pregnancy_related |
| pregnancy_status | Q022     | resistensi Methyldopa pada Hypertension in Pregnancy alternatif Methyldopa            | pregnant          |
| pregnancy_status | Q026     | kontraindikasi Labetalol pada Hypertension in Pregnancy dengan atrial fibrillation    | pregnant          |
| pregnancy_status | Q037     | SSRIs in pregnancy and ADHD                                                           | pregnant          |
| pregnancy_status | Q044     | Malaria with pregnancy first line drug                                                | pregnant          |
| pregnancy_status | Q064     | monitoring parameters Methyldopa in Hypertension in Pregnancy                         | pregnant          |
| pregnancy_status | Q068     | Labetalol resistance in Hypertension in Pregnancy alternative therapy                 | pregnant          |
| year             | Q020     | latest Malaria management guidelines 2025                                             | 2025              |
| year             | Q025     | Acute Coronary Syndrome guideline update 2023 summary                                 | 2023              |
| year             | Q067     | kapan start Atorvastatin di Acute Coronary Syndrome evidence terbaru 2025             | 2025              |
| year             | Q094     | kapan start Azithromycin di Asthma evidence terbaru 2022                              | 2022              |
| year             | Q098     | ARBs terbaru untuk Hypertension 2022                                                  | 2022              |
| year             | Q105     | tatalaksana Breast Cancer HER2-positive panduan terbaru 2025                          | 2025              |
| year             | Q113     | latest Obesity management guidelines 2025                                             | 2025              |
| year             | Q128     | kapan start Alendronate di Osteoporosis evidence terbaru 2022                         | 2022              |
| recency_flag     | Q020     | latest Malaria management guidelines 2025                                             | True              |
| recency_flag     | Q023     | indikasi Sitagliptin pada Type 2 Diabetes Mellitus guideline terbaru                  | True              |
| recency_flag     | Q025     | Acute Coronary Syndrome guideline update 2023 summary                                 | True              |
| recency_flag     | Q038     | Integrase inhibitors terbaru untuk Malaria terbaru                                    | True              |
| recency_flag     | Q062     | latest COPD management guidelines terbaru                                             | True              |
| recency_flag     | Q067     | kapan start Atorvastatin di Acute Coronary Syndrome evidence terbaru 2025             | True              |

## Quality Audit

- QA sample rows prepared for manual review: 60
- QA sample rows with at least one extracted slot: 45
- Precision/recall are not claimed as final metrics yet because no independent gold slot labels exist.
- The QA CSV includes blank review fields so sampled rows can be manually marked as correct, false positive, false negative, or partial.
- Likely error types to watch: negation scope, route abbreviations, pregnancy-related disease vs pregnancy status, and renal disease entity vs renal-context constraint.

## Limitations

- Entity-level negation is not extracted; only a query-level negation flag is populated.
- Numeric dose, duration, sex, severity, lab values, and explicit eGFR are intentionally deferred based on Phase 1.5 evidence.
- Boolean context flags should be used as interpretable ranking features, not as final relevance labels.
