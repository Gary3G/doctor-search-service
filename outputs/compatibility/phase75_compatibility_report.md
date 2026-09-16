# Phase 7.5: CLEAR-Inspired Structured Compatibility

## How and why CLEAR is used

CLEAR (Lopez et al., npj Digital Medicine, 2025) is used as a methodological pattern, not copied as a model. The original task retrieves entity-relevant context from long clinical notes for downstream extraction. This project ranks independent medical content for doctor queries. The transferable idea is that extracted clinical entities should be selected, normalized/augmented, and actively matched—not left as descriptive metadata.

| clear_stage | project_adaptation | why_used | boundary |
| --- | --- | --- | --- |
| Clinical entity extraction | Use supplied disease/molecule/class/area labels plus Phase 1.6 contextual slots. | Preserves clinically meaningful query structure instead of treating the query as undifferentiated text. | No new neural NER is trained. |
| Entity relevance selection | Separate exact entities, hierarchy, context, intent prior, and conflicts. | Not every extracted field should have equal semantic meaning or become a hard filter. | Selection is transparent and rule-based. |
| Entity augmentation | Normalize names; use ICD parent and ATC molecule-to-class relations. | Recovers clinically related content when exact surface forms or molecule identity differ. | No external synonym ontology; hierarchy is limited to supplied codes. |
| Target matching | Compute exact overlap, coverage, hierarchy, context match, and conflict features for every pair. | Makes NER operational as ranking evidence rather than descriptive metadata. | Missing title evidence is unknown, not a negative. |
| Relevant context retrieval | Expose an equal-weight structured score for later BM25/hybrid reranking. | Provides a CPU-friendly signal that can be ablated in later retrieval experiments. | Phase 7.5 does not tune weights or evaluate a ranker. |
| Component evaluation | Audit extraction separately and retain feature groups for later ablation. | Distinguishes extraction quality from downstream retrieval contribution. | Existing slot QA is limited without independent clinician gold labels. |

The adaptation is CPU-first. Supplied disease, molecule, drug-class, and therapeutic-area labels are normalized; ICD parent and ATC class relationships provide bounded hierarchy expansion; Phase 1.6 constraints are matched against content metadata and title-derived evidence. No neural NER, external ontology expansion, encoder fine-tuning, or CLEAR model reproduction is claimed.

## Pairwise feature contract

The matrix contains all 172,500 combinations of 500 queries and 345 content items. It contains no relevance grade, behavior, doctor, session, rank, popularity, or exposure feature. This prevents label leakage before evaluation splitting.

Exact entity matches, hierarchy matches, and conflicts are separate. Missing title context is treated as unknown rather than conflicting. This distinction preserves recall and avoids unsafe hard filtering.

## Initial structured score

`entity_score` is augmented entity coverage. `context_score` is coverage of active query constraints. When context exists, `structured_score` is their equal mean; otherwise it equals entity score. `structured_conflict_rate` is retained separately rather than applying an arbitrary penalty. Intent-to-content-type compatibility is also separate and is not included in the score. No weight was selected using behavior.

Mean structured score is 0.056; 12,354 pairs have an augmented entity match and 14,278 have a context match.

## Descriptive construct check

| relevance_grade | rows | mean_entity_coverage | mean_entity_augmented_coverage | mean_entity_conflict_rate | mean_context_coverage | mean_context_conflict_rate | mean_structured_score | mean_structured_conflict_rate | mean_intent_content_type_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 5547 | 0.0299 | 0.0312 | 0.9701 | 0.0658 | 0.0565 | 0.057 | 0.7714 | 0.4657 |
| 1 | 438 | 0.0303 | 0.0308 | 0.9697 | 0.0582 | 0.0616 | 0.0542 | 0.7606 | 0.4863 |
| 2 | 707 | 0.0343 | 0.0357 | 0.9657 | 0.0582 | 0.0686 | 0.0586 | 0.7772 | 0.4569 |
| 3 | 345 | 0.0399 | 0.0413 | 0.9601 | 0.0594 | 0.0638 | 0.0587 | 0.7504 | 0.458 |

Across exposed pairs, Spearman correlation between structured score and Phase 7 weak grade is -0.005. This is descriptive only: exposures and behavior come from an existing ranker, so the association neither tunes the score nor establishes causal value.

## Feature prevalence

| feature | nonzero_pairs | nonzero_share | mean | median | maximum |
| --- | --- | --- | --- | --- | --- |
| structured_conflict_rate | 170834 | 0.9903 | 0.7716 | 1.0 | 1.0 |
| entity_conflict_rate | 170709 | 0.9896 | 0.9695 | 1.0 | 1.0 |
| molecule_conflict | 169800 | 0.9843 | 0.9843 | 1.0 | 1.0 |
| disease_conflict | 169345 | 0.9817 | 0.9817 | 1.0 | 1.0 |
| drug_class_conflict | 168816 | 0.9786 | 0.9786 | 1.0 | 1.0 |
| therapeutic_area_conflict | 161000 | 0.9333 | 0.9333 | 1.0 | 1.0 |
| intent_content_type_match | 81929 | 0.475 | 0.475 | 0.0 | 1.0 |
| structured_score | 25300 | 0.1467 | 0.0561 | 0.0 | 1.0 |
| context_coverage | 14278 | 0.0828 | 0.0633 | 0.0 | 1.0 |
| context_conflict_rate | 12676 | 0.0735 | 0.0617 | 0.0 | 1.0 |
| entity_augmented_coverage | 12354 | 0.0716 | 0.0321 | 0.0 | 1.0 |
| entity_coverage | 12354 | 0.0716 | 0.0305 | 0.0 | 1.0 |
| therapeutic_area_match | 11500 | 0.0667 | 0.0667 | 0.0 | 1.0 |
| recency_conflict | 8477 | 0.0491 | 0.0491 | 0.0 | 1.0 |
| year_conflict | 8365 | 0.0485 | 0.0485 | 0.0 | 1.0 |
| recency_match | 6125 | 0.0355 | 0.0355 | 0.0 | 1.0 |
| dose_context_match | 5580 | 0.0323 | 0.0323 | 0.0 | 1.0 |
| drug_class_match | 3684 | 0.0214 | 0.0214 | 0.0 | 1.0 |
| atc_class_match | 3548 | 0.0206 | 0.0206 | 0.0 | 1.0 |
| drug_class_name_match | 3466 | 0.0201 | 0.0201 | 0.0 | 1.0 |
| icd10_parent_match | 3280 | 0.019 | 0.019 | 0.0 | 1.0 |
| disease_match | 3155 | 0.0183 | 0.0183 | 0.0 | 1.0 |
| disease_name_match | 3155 | 0.0183 | 0.0183 | 0.0 | 1.0 |
| icd10_exact_match | 3155 | 0.0183 | 0.0183 | 0.0 | 1.0 |
| atc_code_exact_match | 2700 | 0.0157 | 0.0157 | 0.0 | 1.0 |
| molecule_match | 2700 | 0.0157 | 0.0157 | 0.0 | 1.0 |
| molecule_name_match | 2700 | 0.0157 | 0.0157 | 0.0 | 1.0 |
| year_match | 1640 | 0.0095 | 0.0095 | 0.0 | 1.0 |
| molecule_hierarchical_match | 984 | 0.0057 | 0.0057 | 0.0 | 1.0 |
| pregnancy_match | 888 | 0.0051 | 0.0051 | 0.0 | 1.0 |

## Boundaries and next evaluation

- Content context is title-derived because body text and dedicated context fields are unavailable.
- ICD/ATC expansion is bounded to supplied codes and deterministic parent/class derivation.
- Negation is carried as a query guardrail but not converted into positive matching.
- The intent prior is expert-rule-based and remains separate for ablation.
- Extraction quality and retrieval contribution are separate questions, following CLEAR's component-evaluation principle.
- Retrieval weights, temporal/query splits, BM25 integration, and ranking metrics belong to later phases.
