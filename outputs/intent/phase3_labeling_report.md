# Phase 3: Intent Labeling Strategy

## Outcome

All 500 queries have a final intent label, and every original query column plus the implemented Phase 1.6 contextual fields is preserved in `queries_labeled.csv`. Each query retains three decision signals: ordered bilingual rules, query-to-intent semantic prototype similarity, and an unsupervised semantic-cluster mapping. A 60-query pilot was followed by a 180-query reviewed reference subset (the pilot is included in that total). The other 320 labels were propagated with the three-signal policy.

The term **reviewed reference subset** is intentional. Annotation was performed by a single model-assisted analyst workflow, not by independent clinicians. It is useful for this assessment but must not be described as clinical ground truth or used to claim inter-annotator reliability.

## Labeling approach

1. **Three separate signals.** The lexical rule signal uses an ordered bilingual boundary policy. The prototype signal uses cosine similarity between a frozen multilingual query embedding and all 11 complete intent definitions. The cluster signal begins with independent agglomerative query clusters and maps each anonymous cluster to the schema.
2. **Kappa-optimized cluster mapping.** Coordinate search chooses the cluster-to-intent mapping that maximizes Fleiss' kappa among rule, prototype, and cluster signals. Semantic centroid similarity breaks exact ties. Kappa increased from 0.324 to 0.357 on the available 500 signal triples.
3. **Pilot (60).** The pilot prioritizes three-way disagreement, prototype/cluster agreement against a rule, Phase 2 model disagreement, low margins, rare intents, multi-cue boundaries, languages, and length extremes.
4. **Taxonomy freeze.** The 11 Phase 2 classes remained coherent in the pilot. No class was added, removed, split, or merged. `Other / Ambiguous` remains a fallback, although no supplied query required it.
5. **Reviewed subset (180, including pilot).** Coverage was expanded across intent, language, therapeutic area, length, entity composition, contextual complexity, and Phase 2 cluster. Each supported intent has at least 12 reviewed rows.
6. **Conservative adjudication.** Unanimous and rule-plus-model agreements provide model assistance. When semantic signals disagree with an explicit rule, the auditable primary-information-need rule is retained and the row is flagged rather than being silently outvoted. If no rule exists, the semantic plurality is the fallback.
7. **Remaining 320 rows.** The same frozen consensus policy supplies labels and preserves all signals, agreement status, confidence, provenance, and review flags.

## Counts

| Final intent | All 500 | Reviewed subset |
| --- | ---: | ---: |
| Comparative Treatment Choice | 23 | 12 |
| Dosing / Administration | 96 | 14 |
| Efficacy / Outcomes | 20 | 12 |
| Guideline / Evidence Lookup | 59 | 33 |
| Interaction / Combination | 21 | 12 |
| Management / Treatment Selection | 58 | 13 |
| Mechanism / Background Knowledge | 29 | 12 |
| Monitoring / Response / Risk Assessment | 33 | 14 |
| Prophylaxis / Maintenance | 31 | 12 |
| Safety / Contraindication | 84 | 34 |
| Treatment Change / Escalation | 46 | 12 |

- Pilot: 60 queries.
- Reviewed subset: 180 queries.
- Rule-propagated remainder: 320 queries.
- `Other / Ambiguous`: 0 queries.
- Medium/low-confidence review flags: 353 queries.
- Three-signal Fleiss' kappa: 0.324 before and 0.357 after cluster-mapping optimization.
- Agreement between the Phase 2 model suggestion and the reviewed label: 87.8% on the reviewed subset and 95.4% over all queries.

The disagreement rate is a diagnostic, not inter-annotator agreement. `phase3_signal_disagreements_adjudicated.csv` records non-unanimous reviewed cases and the explicit boundary rationale.

## Quality audit

The second pass deliberately revisited low prototype margins, three-signal disagreements, multi-cue queries, rare classes, and Phase 2 disagreements. It checked the chosen primary need against each class's inclusion/exclusion criteria and retained an audit note per reviewed row. Pairwise Cohen kappas and three-rater Fleiss' kappa describe algorithmic agreement only. This review is neither time-separated nor independent; consequently, no inter-annotator statistic is claimed.

## Limitations

- The reviewed labels were created with a single model-assisted workflow and have no independent clinician adjudication.
- The prototype and cluster signals share the same frozen embedding encoder, so the three signals are operationally separate but not statistically independent.
- Maximizing kappa can make algorithms agree on the same error. The optimized value is in-sample descriptive agreement, not clinical accuracy or external validation.
- The supplied queries are strongly template-patterned. Rules perform unusually well here and may fail on natural, misspelled, implicit, code-switched, or genuinely multi-intent search traffic.
- The rule hierarchy forces one primary intent. It cannot represent equally important secondary intents.
- `label_confidence` is qualitative, not calibrated. Phase 2 probabilities and prototype margins are not annotation confidence.
- No query exercised the `Other / Ambiguous` fallback, so that boundary is unvalidated and cannot support a learnable class.
- The reviewed subset is intentionally enriched for uncertainty and is not a prevalence-estimation sample.
- Before production use, a qualified second clinical annotator should independently label the subset, disagreements should be adjudicated, and agreement should be reported by class and boundary type.
