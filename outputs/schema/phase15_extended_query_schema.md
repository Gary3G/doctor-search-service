# Phase 1.5 Extended Query Schema

This phase defines the contextual clinical slots to carry into Phase 1.6 extraction.
It intentionally keeps supplied NER, contextual slots, and intent labels separate.

## Selection Criteria

A slot is selected when it occurs repeatedly, can materially affect relevance, can be extracted reliably, and can be matched against content text or metadata.

## Selected Schema

| column                       | dtype    | allowed_values                                                    | extraction_strategy                                                           | content_matchability                                                                         | priority |
| ---------------------------- | -------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------- |
| age_group                    | category | pediatric; adolescent; adult; elderly                             | Rule-based lexical cues; derive from explicit age only if later present.      | Textual title/content matching for pediatric, child, elderly, geriatric.                     | high     |
| pregnancy_status             | category | pregnant; pregnancy_related                                       | Regex over pregnancy, pregnant, hamil, preeclampsia variants.                 | Textual match against title/content pregnancy terms.                                         | high     |
| year                         | integer  | 2020-2039 observed pattern                                        | Regex for four-digit years.                                                   | Direct match to content.publication_year metadata.                                           | high     |
| recency_flag                 | boolean  | true; false                                                       | Detect latest, terbaru, guideline update without requiring a numeric year.    | Can boost newer publication_year when no exact year is supplied.                             | high     |
| dose_context_flag            | boolean  | true; false                                                       | Detect dose, dosing, dosis, titrasi, adjustment, penyesuaian.                 | Textual match to dosing/reference content and drug_profile content_type.                     | high     |
| route                        | category | oral; iv; im; subcutaneous; inhaled; topical                      | Normalize route synonyms such as PO->oral, intravenous->iv, SC->subcutaneous. | Textual match against route mentions in titles/content.                                      | medium   |
| renal_function_group         | category | renal_impairment; severe_impairment if CKD stage/eGFR supports it | Detect renal impairment, renal dose/adjustment, CKD stage, eGFR/CrCl.         | Textual match against renal impairment/dose content; numeric matching if eGFR appears later. | high     |
| hepatic_impairment_flag      | boolean  | true; false                                                       | Detect hepatic impairment, liver disease, cirrhosis, hepatik.                 | Textual match against hepatic/liver content.                                                 | medium   |
| comparison_flag              | boolean  | true; false                                                       | Detect vs, versus, compare, comparison, dibanding.                            | Textual match to versus/comparison/meta-analysis titles; useful for reranking.               | high     |
| negation_flag                | boolean  | true; false                                                       | Detect no, without, bukan, tidak.                                             | Mostly query-side guardrail; do not use as positive content match.                           | medium   |
| prior_treatment_failure_flag | boolean  | true; false                                                       | Detect failure, gagal, resistant, resistance, refractory, resistensi.         | Textual match to resistant/resistance/refractory/case-report content.                        | medium   |

## Candidate Slot Profile

| slot                    | status               | selected_columns             | query_matches | query_pct | content_title_matches | content_title_pct |
| ----------------------- | -------------------- | ---------------------------- | ------------- | --------- | --------------------- | ----------------- |
| age                     | defer                | none                         | 0             | 0.0       | 0                     | 0.0               |
| age_group               | selected             | age_group                    | 25            | 0.05      | 3                     | 0.0087            |
| sex                     | defer                | none                         | 0             | 0.0       | 0                     | 0.0               |
| pregnancy               | selected             | pregnancy_status             | 37            | 0.074     | 24                    | 0.0696            |
| year_or_recency         | selected             | year; recency_flag           | 52            | 0.104     | 45                    | 0.1304            |
| dose_context            | selected_partial     | dose_context_flag            | 93            | 0.186     | 33                    | 0.0957            |
| dose_value              | defer                | none                         | 0             | 0.0       | 0                     | 0.0               |
| route                   | selected_low_support | route                        | 3             | 0.006     | 6                     | 0.0174            |
| duration                | defer                | none                         | 0             | 0.0       | 0                     | 0.0               |
| renal_function          | selected_partial     | renal_function_group         | 22            | 0.044     | 11                    | 0.0319            |
| hepatic_function        | selected             | hepatic_impairment_flag      | 21            | 0.042     | 11                    | 0.0319            |
| lab_values              | defer                | none                         | 14            | 0.028     | 11                    | 0.0319            |
| severity                | defer                | none                         | 0             | 0.0       | 6                     | 0.0174            |
| comparison              | selected             | comparison_flag              | 23            | 0.046     | 5                     | 0.0145            |
| negation                | selected_flag_only   | negation_flag                | 10            | 0.02      | 0                     | 0.0               |
| prior_treatment_failure | selected             | prior_treatment_failure_flag | 24            | 0.048     | 15                    | 0.0435            |

## Selected Slot Rationale

| slot                    | selected_columns             | rationale                                                                                                      |
| ----------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| age_group               | age_group                    | Pediatric and elderly constraints recur and materially change clinical relevance.                              |
| pregnancy               | pregnancy_status             | Pregnancy-related context is frequent and strongly affects medication safety and management relevance.         |
| year_or_recency         | year; recency_flag           | Year and latest/terbaru constraints recur and can match content.publication_year.                              |
| dose_context            | dose_context_flag            | Dosing information need is common, but explicit dose values/units are absent in query text.                    |
| route                   | route                        | Route is sparse but deterministic and clinically meaningful when present.                                      |
| renal_function          | renal_function_group         | Renal dose/impairment context recurs, while broad CKD disease mentions remain covered by supplied disease NER. |
| hepatic_function        | hepatic_impairment_flag      | Hepatic impairment is not in the initial candidate list but recurs and affects medication safety/dosing.       |
| comparison              | comparison_flag              | Comparison requests recur and imply different content preferences.                                             |
| negation                | negation_flag                | Negation appears repeatedly; entity-level negation is deferred because it requires safer parsing.              |
| prior_treatment_failure | prior_treatment_failure_flag | Prior failure/resistance changes relevance toward add-on, alternative, or refractory-case content.             |

## Deferred Slot Rationale

| slot       | candidate_columns             | rationale                                                                                            |
| ---------- | ----------------------------- | ---------------------------------------------------------------------------------------------------- |
| age        | age                           | No explicit numeric ages appear in the 500 supplied queries; keep age_group instead.                 |
| sex        | sex                           | No sex-specific query constraints were observed.                                                     |
| dose_value | dose_value; dose_unit         | No explicit numeric dose values are observed; extracting empty columns would add noise.              |
| duration   | duration_value; duration_unit | No explicit duration constraints are observed.                                                       |
| lab_values | lab_name; lab_value; lab_unit | Observed terms are mostly diagnoses/entities such as anaemia, not extractable lab value constraints. |
| severity   | severity                      | No clear severity constraints are observed in query text.                                            |

## Conceptual Separation

- Existing NER columns answer what medical concepts are mentioned: disease, molecule, drug class, therapeutic area.
- Contextual slots answer under what clinical constraints the information is requested: pregnancy, renal function, recency, dosing context, comparison.
- Intent classification answers what the doctor wants to know and is handled in later phases.

## Phase 1.6 Contract

Phase 1.6 should populate the selected schema columns for all 500 queries and preserve the original raw query columns.
Deferred fields should not be added unless later manual review finds enough reliable evidence.
