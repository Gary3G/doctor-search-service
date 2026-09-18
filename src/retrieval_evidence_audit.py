"""Audit existing extraction evidence without modifying features or rankings."""
from __future__ import annotations
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import OUTPUT_DIR, PROCESSED_DATA_DIR
from src.query_extraction import extract_slots
from src.topic_boost_retrieval import table

OUTPUT=OUTPUT_DIR/'audits'/'retrieval_evidence'
QUERIES=PROCESSED_DATA_DIR/'queries_with_contextual_slots.csv'
CONTENT=PROCESSED_DATA_DIR/'content_with_contextual_slots.csv'
NOTES=PROCESSED_DATA_DIR/'retrieval_evidence_review.csv'
ENTITY_FIELDS=('disease_entity','molecule_entity','drug_class_entity','therapeutic_area')
SLOTS=tuple(extract_slots('').__dict__)


def normalize(text):
    return re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',str(text)).casefold()).strip()


def literal_span(text,term):
    """Case/punctuation-insensitive whole-phrase evidence, not semantic validation."""
    words=re.findall(r'\w+',term,flags=re.UNICODE)
    if not words:return ''
    pattern=r'(?<!\w)'+r'[^\w]*'.join(re.escape(w) for w in words)+r'(?!\w)'
    match=re.search(pattern,text,flags=re.I)
    return match.group() if match else ''


def active(value):
    return pd.notna(value) and value is not False and str(value).lower() not in ('false','0','')


def build():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    q=pd.read_csv(QUERIES);c=pd.read_csv(CONTENT)
    entities=[];records=[];contexts=[]
    # Use current extractor as provenance, not as independent correctness ground truth.
    for side,frame,id_col,text_col in [('query',q,'query_id','query_text'),('content',c,'content_id','title')]:
        for _,row in frame.iterrows():
            rid=row[id_col];text=row[text_col];extracted=extract_slots(text).__dict__
            duplicate_count=0;unsupported_molecules=0
            for field in ENTITY_FIELDS:
                values=[] if pd.isna(row[field]) else [t.strip() for t in str(row[field]).split(';') if t.strip()]
                seen=set()
                for term in values:
                    key=normalize(term); duplicate=key in seen;seen.add(key);duplicate_count+=duplicate
                    span=literal_span(text,term)
                    unsupported_molecules += int(field=='molecule_entity' and not span and not duplicate)
                    entities.append(dict(side=side,record_id=rid,field=field,value=term,duplicate=duplicate,
                        evidence_source='text_and_metadata' if span else 'metadata_without_literal_text_support',evidence_span=span))
            persisted={s:row[s if side=='query' else 'title_'+s] for s in SLOTS}
            for s,v in extracted.items():
                if active(v):
                    contexts.append(dict(side=side,record_id=rid,field=s,value=v,evidence_source='text_rule',evidence_text=text))
            heuristic=[]
            if side=='content':
                if bool(row.content_dose_context) and not bool(row.title_dose_context_flag): heuristic.append('dose_from_drug_profile')
                if bool(row.content_comparison_context) and not bool(row.title_comparison_flag):heuristic.append('comparison_from_review')
                for h in heuristic:contexts.append(dict(side=side,record_id=rid,field=h,value=True,evidence_source='content_type_only',evidence_text=row.content_type))
                contexts.append(dict(side=side,record_id=rid,field='publication_year',value=row.publication_year,evidence_source='publication_metadata',evidence_text=str(row.publication_year)))
            title_year_disagrees=side=='content' and active(extracted['year']) and extracted['year']!=row.publication_year
            # Sampling risk flags do not assert errors.
            risks=[]
            if unsupported_molecules:risks.append('molecule_without_literal_support')
            if heuristic:risks.append('context_type_proxy')
            if title_year_disagrees:risks.append('title_vs_publication_year')
            if extracted['negation_flag']:risks.append('negation')
            if extracted['comparison_flag']:risks.append('comparison')
            if extracted['route']:risks.append('route')
            if re.search(r'\b(renal|kidney|immunocompromised|obesity|pregnan|hamil|elderly|anak|lansia)',text,re.I):risks.append('population_or_comorbidity')
            if duplicate_count:risks.append('duplicate_metadata')
            if any(str(persisted[s])!=str(v) and not (pd.isna(persisted[s]) and v is None) and not (s=='year' and pd.notna(persisted[s]) and v is not None and float(persisted[s])==v) for s,v in extracted.items()):
                raise ValueError(f'Current extractor differs from saved slots: {rid}')
            records.append(dict(side=side,record_id=rid,language=row.language,text=text,
                entities=json.dumps({f:row[f] for f in ENTITY_FIELDS}),
                extracted_context=json.dumps({k:v for k,v in extracted.items() if active(v)}),
                proxies=';'.join(heuristic),publication_year=row.publication_year if side=='content' else '',
                risk_flags=';'.join(risks),duplicate_terms=duplicate_count,unsupported_molecule_count=unsupported_molecules,
                title_year_disagrees=title_year_disagrees))
    records=pd.DataFrame(records);ent=pd.DataFrame(entities);ctx=pd.DataFrame(contexts)
    ent.to_csv(OUTPUT/'entity_evidence.csv',index=False);ctx.to_csv(OUTPUT/'context_evidence.csv',index=False)
    records.to_csv(OUTPUT/'all_records.csv',index=False)
    selections=[]
    for side,frame in records.groupby('side',sort=True):
        selected=[]
        for lang,g in frame.groupby('language',sort=True):
            chosen=g.sort_values('record_id').sample(n=min(6,len(g)),random_state=42)
            for rid in chosen.record_id:selected.append((rid,'language_stratified_random',lang))
        used={x[0] for x in selected}
        # Round-robin risk coverage, deterministic sorted IDs, 12 extra records.
        risks=['negation','title_vs_publication_year','context_type_proxy','comparison','route','population_or_comorbidity','duplicate_metadata','molecule_without_literal_support']
        while len(selected)<30:
            before=len(selected)
            for risk in risks:
                candidates=frame[frame.risk_flags.str.contains(risk,regex=False)&~frame.record_id.isin(used)].sort_values('record_id')
                if len(candidates):
                    rid=candidates.iloc[0].record_id;selected.append((rid,'targeted_risk',risk));used.add(rid)
                if len(selected)==30:break
            if len(selected)==before:break
        selections.extend(dict(side=side,record_id=rid,sample_group=group,selection_reason=reason) for rid,group,reason in selected)
    sample=pd.DataFrame(selections).merge(records,on=['side','record_id'],validate='one_to_one')
    sample.to_csv(OUTPUT/'review_sample.csv',index=False)
    unique=ent[~ent.duplicate]
    summary=unique.assign(literal_support=unique.evidence_source.eq('text_and_metadata')).groupby(['side','field']).agg(unique_terms=('value','size'),literal_supported=('literal_support','sum')).reset_index()
    summary['literal_support_fraction']=summary.literal_supported/summary.unique_terms
    summary.to_csv(OUTPUT/'entity_support_summary.csv',index=False)
    context_summary=ctx.groupby(['side','field','evidence_source']).size().reset_index(name='records')
    context_summary.to_csv(OUTPUT/'context_source_summary.csv',index=False)
    manifest=dict(sample='30 queries and 30 titles: 6 random per language per side plus 12 targeted-risk per side',seed=42,
        selection_uses_relevance=False,ranking_modified=False,
        literal_support='surface-form evidence only; unsupported does not mean incorrect; codes and ontology validity not independently verified',
        manual_review='LLM-assisted semantic review of sampled text, not independent clinician annotation',
        sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [QUERIES,CONTENT,Path(__file__),Path('src/query_extraction.py'),Path('src/structured_compatibility.py')]})
    if NOTES.exists():
        notes=pd.read_csv(NOTES).fillna('')
        reviewed=sample.merge(notes,on=['side','record_id'],validate='one_to_one',how='left')
        if len(notes)!=len(sample) or reviewed.review_notes.isna().any():raise ValueError('Review must cover exactly the sample')
        reviewed.to_csv(OUTPUT/'reviewed_sample.csv',index=False)
        tags=reviewed.assign(finding=reviewed.findings.str.split(';')).explode('finding')
        counts=tags[tags.finding.ne('')].groupby(['side','sample_group','finding']).size().reset_index(name='records')
        counts.to_csv(OUTPUT/'review_findings.csv',index=False)
        diagnostics=followup_diagnostics(q,c)
        write_report(summary,context_summary,records,reviewed,counts,diagnostics)
        manifest['sha256'][str(NOTES)]=hashlib.sha256(NOTES.read_bytes()).hexdigest()
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return sample


def followup_diagnostics(q,c):
    findings=[]
    for name,side,frame,text_col,pattern,slot in [
        ('comparison_word_missed','content',c,'title',r'\bperbandingan\b','title_comparison_flag'),
        ('coordinated_renal_phrase_missed','content',c,'title',r'\brenal and hepatic impairment\b','title_renal_function_group'),
        ('safety_question_negation','query',q,'query_text',r'\baman(?:\s+atau)?\s+tidak\b','negation_flag')]:
        for _,r in frame[frame[text_col].str.contains(pattern,case=False,regex=True)].iterrows():
            findings.append(dict(check=name,side=side,record_id=r.query_id if side=='query' else r.content_id,text=r[text_col],saved_value=r[slot]))
    # Surface lexicon from supplied molecule names; candidate recall is bounded by
    # this lexicon. Prefer longest spans to avoid double counting nested names.
    terms=set()
    for frame in (q,c):
        for value in frame.molecule_entity.dropna():terms.update(t.strip() for t in value.split(';') if t.strip())
    for side,frame,id_col,text_col in [('query',q,'query_id','query_text'),('content',c,'content_id','title')]:
        for _,r in frame.iterrows():
            found=[];text=r[text_col]
            for term in sorted(terms,key=lambda s:(-len(s),s)):
                span=literal_span(text,term)
                if span and not any(normalize(term) in normalize(existing) for existing in found):found.append(term)
            supplied={normalize(t.strip()) for t in str(r.molecule_entity).split(';')}
            for term in found:
                if normalize(term) not in supplied:
                    findings.append(dict(check='literal_molecule_missing_from_metadata_candidate',side=side,record_id=r[id_col],text=text,saved_value=term))
    diagnostics=pd.DataFrame(findings)
    diagnostics.to_csv(OUTPUT/'followup_diagnostics.csv',index=False)
    return diagnostics


def write_report(summary,context_summary,records,reviewed,counts,diagnostics):
    checks=diagnostics.groupby(['side','check']).size().reset_index(name='records_or_candidates')
    random_counts=counts[counts.sample_group.eq('language_stratified_random')]
    report='\n\n'.join([
        '# Retrieval entity and context evidence audit',
        'Run `.venv/bin/python -m src.retrieval_evidence_audit`. Audit only: no retrieval weights, labels, extraction outputs, or model rankings were changed. All 500 query texts and 345 content titles received deterministic evidence-source profiling. An LLM-assisted review then covered 60 selected records: 30 queries and 30 titles. Each side has 18 language-stratified random records (6 EN, 6 ID, 6 MIXED; seed42) and 12 deterministic targeted-risk records. Sampling uses no behavioral grades or retrieval failures.',
        '## Recommendation',
        'The strongest next step is a small extraction and provenance repair: recover the missed bilingual comparison and coordinated renal expressions, distinguish safety questions from asserted negation, and separate explicit title context from content-type proxies. Keep supplied entity metadata, but preserve whether each specific concept is explicit in query/title text or only supplied. Do not make every metadata molecule a mandatory query constraint. Then evaluate explicit-only context and evidence-source-aware entity coverage as separate ablations against frozen hybrid.',
        '## Full-corpus evidence profile',
        'Counts below are unique normalized annotations per record and field. Literal support uses case/punctuation-insensitive whole-phrase matching. This is evidence visibility, not entity accuracy: synonyms, class members and valid body-only concepts can lack literal support. ICD/ATC mappings and clinical appropriateness were not independently adjudicated.',
        table(summary.round(4)),
        f"{int(records[(records.side=='query')].unsupported_molecule_count.gt(0).sum())}/500 queries and {int(records[(records.side=='content')].unsupported_molecule_count.gt(0).sum())}/345 content items contain at least one supplied molecule with no literal surface support. Query titles that name a drug class can legitimately have related molecules in metadata, but using those molecules as explicit query restrictions adds specificity the text did not request.",
        'Only 128/399 unique content molecule annotations are literally visible, versus 381/539 query molecule annotations. Drug-class and therapeutic-area metadata often represent inferred taxonomy, not literal text; their lack of literal support is expected and not automatically erroneous. Duplicate metadata is present in 43 queries and 67 content records; current set matching already collapses duplicates, so deduplication alone is unlikely to improve ranking.',
        '## Context sources',table(context_summary),
        'There are 33 titles with explicit dosing cues, plus 27 documents receiving dosing evidence only from drug_profile type (45% of 60 dosing-positive documents). Comparison has 5 explicit title-rule positives, plus 12 review-type-only positives (about 71% of 17 comparison-positive documents). These proxies do not establish that a requested dose or two-drug comparison is covered. In the seven Perbandingan titles, an explicit comparison can be missed even while unrelated review types receive credit.',
        '## Confirmed recurring patterns and candidate entity omissions',table(checks),
        'The 7 Perbandingan titles all have comparison_flag=False. The 10 Renal and Hepatic Impairment titles all lack renal_function_group despite clear coordinated wording. All 10 flagged query negations contain aman [atau] tidak, a safety question, not an asserted negated clinical condition. These are narrow pattern findings, not global precision/recall estimates. Negation is not currently used in the Phase 11 ranking score, so repairing it improves query understanding but has no direct effect on that ranker.',
        'Literal molecule omission candidates come from a vocabulary of supplied molecule names, scanning text with longest-name preference. They are leads for review, not newly accepted entity labels. C025 is manually confirmed at the text level: its title names Metoprolol versus Empagliflozin, but its metadata lists only Metoprolol. A supplemental inspection also confirms C315 names Hydrocortisone and Piperacillin-tazobactam, while metadata lists only Hydrocortisone. Six of seven Perbandingan titles repeat the same comparator, so recovering comparison wording alone will not create six useful distinct-drug comparisons. The sample also shows Magnesium versus Magnesium sulphate specificity, which requires controlled alias review rather than automatic equivalence.',
        '## Findings in the random portion',
        'These counts refer to only 18 queries and 18 titles, equally stratified by language. They are not population prevalence estimates; targeted-risk findings are reported separately in review_findings.csv. Categories overlap. Every sampled record has a saved reviewer note and evidence excerpt.',table(random_counts),
        '## Representative evidence',
        table(reviewed[reviewed.record_id.isin(['Q180','Q242','Q262','Q001','C025','C084','C291','C265','C263','C005'])][['record_id','text','findings','review_notes']]),
        '## Prioritized follow-up',
        '1. Repair the three demonstrated extraction patterns with bilingual positive/negative cases. For comparison, retain distinct comparator entities and flag self-comparisons; a comparison cue alone does not imply a meaningful pair.\n2. Split explicit context from type-only proxies and preserve entity provenance (literal, controlled alias, metadata-only, hierarchy-derived). Evaluate each source separately. Keep unsupported evidence unknown rather than declaring it wrong.\n3. Recover text-explicit molecules missing from metadata, starting with reviewed comparator titles; use per-entity coverage for distinct requested drugs. Do not silently add every lexicon hit without checking ambiguity.\n4. Consider immunocompromised population, care setting, comorbidity and severity only after measuring query frequency AND document-side support. The sample shows these gaps but does not yet justify a broad new schema.\n5. Obtain independent relevance judgments for pooled results before claiming clinical ranking gains. Additional body/abstract text would help establish applicability, but is not available in this corpus.',
        '## Audit boundaries',
        'The semantic review was LLM-assisted; it is not an independent clinician audit and does not establish medical correctness. Corpus-wide literal checks are reproducible; semantic judgments are saved annotations replayed by the script, not independently regenerated. No global extraction precision/recall is claimed because no exhaustive independent gold annotation was created. Body content, ontology/code correctness, and medication/disease appropriateness are outside this audit. Current and saved title/query extractor outputs were checked for consistency.',
        'Files: reviewed_sample.csv (all 60 notes), entity_evidence.csv (individual annotations and matched spans), context_evidence.csv (field/source/text), entity_support_summary.csv, context_source_summary.csv, followup_diagnostics.csv, review_findings.csv, all_records.csv and manifest.json. Authored notes are in data/processed/retrieval_evidence_review.csv.'
    ])+'\n'
    # Narrative findings are consolidated in write_up/phase11_summary.md.


if __name__=='__main__':
    sample=build()
    print(sample[['side','record_id','sample_group','text','entities','extracted_context','proxies','publication_year']].to_json(orient='records',indent=2))
