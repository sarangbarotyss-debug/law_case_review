# -*- coding: utf-8 -*-

import json
import re
from . import ai_provider_service
from . playbook_retrieval_service import find_matching_playbook_clauses

def _build_case_text(case):
    parts = []
    if case.description:
        parts.append(case.description)
    for doc in case.document_ids:
        if doc.state == 'confirmed' and doc.ocr_text:
            parts.append(doc.ocr_text)
    return "\n\n".join(parts)

def _classify_match(env, case_text, clause):
    prompt = (
        "You are a legal assistant helping a lawyer prepare a case.\n"
        "Below is a summary of the client's case, followed by one provision "
        "from a legal reference document (e.g. a constitutional article or statute).\n\n"
        "Decide ONE of the following for this specific provision, based only on the case text given:\n"
        "- \"violation\": the case facts describe a possible violation of this provision "
        "(something was done that this provision prohibits or that breaches a right it grants)\n"
        "- \"defense\": this provision could support the client's position or be used in their defense\n"
        "- \"related\": this provision is topically related but doesn't clearly support either of the above\n\n"
        "Respond ONLY as JSON, no markdown, no explanation outside the JSON:\n"
        "{\"match_type\": \"violation|defense|related\", \"explanation\": \"<2-3 sentence reasoning>\"}\n\n"
        "Case summary:\n" + case_text + "\n\n"
        "Provision (Article/Section " + (clause.clause_number or '') + " - " + (clause.title or '') + "):\n"
        + (clause.text or '')
    )
    answer = ai_provider_service.call_llm(env, prompt)
    cleaned = re.sub(r'^```json\s*|\s*```$', '', answer.strip())
    return json.loads(cleaned)


def run_case_playbook_comparison(env, case):
    case_text = _build_case_text(case)
    if not case_text.strip():
        raise Exception("This case has no description or confirmed document text to compare.")

    if not case.playbook_source_ids:
        raise Exception("Please select at least one playbook source before running Find.")

    source_ids = case.playbook_source_ids.ids

    matches = find_matching_playbook_clauses(
        env, query_text=case_text, source_ids=source_ids, top_k=10
    )
    env['law.case.playbook.match'].search([('case_id', '=', case.id)]).unlink()

    # Confidence is relative to this specific search's own top score, not a
    # fixed global number - because absolute score meaning varies per case.
    CONFIDENCE_MARGIN = 0.02
    top_score = max((m['score'] for m in matches), default=0.0)

    for m in matches:
        clause = m['clause']
        try:
            classification = _classify_match(env, case_text, clause)
        except Exception:
            # Classification failed for this one clause - skip it rather than
            # abort the whole comparison. The match was found by search, we just
            # couldn't get an LLM verdict on it this time.
            continue
        confidence = 'strong' if (top_score - m['score']) <= CONFIDENCE_MARGIN else 'possible'
        env['law.case.playbook.match'].create({
            'case_id': case.id,
            'clause_id': clause.id,
            'match_type': classification.get('match_type', 'related'),
            'explanation': classification.get('explanation', ''),
            'score': m['score'],
            'confidence': confidence,
        })