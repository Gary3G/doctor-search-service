# Phase 2 Completion Checklist

`deferred_by_plan` is used only for workflow steps that the project plan assigns to later phases; it does not mean a Phase 2 deliverable was skipped.

| Section | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 8.1 | Literature seed taxonomy | complete | `phase2_seed_taxonomy.csv` |
| 8.2 | Semantic definitions, inclusion and exclusion signals for every seed | complete | `phase2_seed_taxonomy.csv` |
| 8.3A | Delexicalized word unigram/bigram TF-IDF | complete | `data/cache/phase2_tfidf_matrix.npz; data/cache/phase2_tfidf_vocabulary.json` |
| 8.3B | Frozen multilingual sentence embeddings computed once and cached | complete | `data/cache/phase2_query_embeddings.npz; data/cache/phase2_prototype_embeddings.npz; data/cache/phase2_candidate_intent_embeddings.npz` |
| 8.3C | Thirteen structured NER/context features | complete | `phase2_structured_query_features.csv` |
| 8.3D | Explicit Liang three-branch model, attention fusion, soft-centroid refinement, and diagnostics | complete | `phase2_liang_methodology.json; phase2_liang_branch_metrics.csv; phase2_liang_training_history.csv` |
| 8.4 | Provisional query-to-prototype cosine similarities | complete | `phase2_prototype_assignments.csv` |
| 8.5 | Top-two seed-prototype margin, Liang model margin, and review prioritization | complete | `phase2_prototype_assignments.csv; phase2_liang_hybrid_assignments.csv; phase2_low_margin_review.csv` |
| 8.6 | Independent agglomerative clustering selected at k=15; KMeans comparison | complete | `phase2_cluster_model_comparison.csv` |
| 8.7 | Clusters compared with seed prototypes, lexical evidence, features, and representatives | complete | `phase2_nlp_taxonomy_analysis.csv` |
| 8.8 | Separate top unigrams, top bigrams, and representative queries for every cluster/class | complete | `phase2_tfidf_explanations.csv` |
| 8.9 | Structured feature analysis by cluster and final class | complete | `phase2_structured_feature_profiles.csv` |
| 8.10 | Explicit keep/split/merge/rename/new/manual-review decisions | complete | `phase2_taxonomy_decisions.csv; phase2_seed_to_final_derivation.csv` |
| 8.11 | Liang-model support estimates and complete proposed class distribution | complete | `phase2_final_taxonomy.csv; phase2_seed_to_final_derivation.csv; phase2_manifest.json` |
| 8.12 | Representative, low-margin, and nearest cross-class one-analyst review | complete | `phase2_manual_clinical_review.csv; phase2_low_margin_review.csv; phase2_cross_class_neighbors.csv` |
| 8.13.1-11 | Workflow through freezing the final taxonomy | complete | `phase2_final_taxonomy.csv; phase2_taxonomy_report.md` |
| 8.13.12-14 | Annotation guideline, gold labeling, classifier training | deferred_by_plan | `Phases 3 and 4; intentionally not represented as Phase 2 gold labels` |
| 8.14A | Required seed taxonomy table | complete | `phase2_seed_taxonomy.csv` |
| 8.14B | Required NLP taxonomy analysis table | complete | `phase2_nlp_taxonomy_analysis.csv` |
| 8.14C | Required final taxonomy with definitions, examples, preferences, and counts | complete | `phase2_final_taxonomy.csv; notebook.ipynb; write_up/phase2_taxonomy_summary.md` |
