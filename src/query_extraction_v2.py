"""Versioned, audit-driven slot repairs; legacy extractor remains reproducible."""
from dataclasses import replace
import re
from src.query_extraction import extract_slots as extract_legacy, normalize_text, NEGATION_PATTERN

COMPARISON_V2 = re.compile(r'\b(?:perbandingan|membandingkan|dibandingkan)\b', re.I)
COORDINATED_RENAL = re.compile(r'\brenal\s+and\s+hepatic\s+impairment\b', re.I)
SAFETY_QUESTION = re.compile(r'\baman\s+(?:atau\s+)?tidak\b', re.I)


def extract_slots(text):
    """Add demonstrated cues; remove only interrogative negation spans.

    Other negation in the same sentence is preserved. Comparison detection does
    not assert distinct drugs or clinical validity of a self-comparison.
    """
    text = normalize_text(text)
    slots = extract_legacy(text)
    return replace(slots,
        comparison_flag=slots.comparison_flag or bool(COMPARISON_V2.search(text)),
        renal_function_group=slots.renal_function_group or ('renal_impairment' if COORDINATED_RENAL.search(text) else None),
        negation_flag=bool(NEGATION_PATTERN.search(SAFETY_QUESTION.sub('', text))))
