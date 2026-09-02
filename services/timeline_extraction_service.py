# -*- coding: utf-8 -*-

import json
from odoo.exceptions import UserError
from . import ai_provider_service


def extract_timeline_events(env, document):
    """
    document: a law.case.document record with ocr_text populated.
    Returns: list of dicts ready to create law.case.timeline.event records.
    Does NOT create records itself - caller decides what to do with results.
    """
    if not document.ocr_text:
        return []

    prompt = """
Read the following legal document text and extract every distinct dated event
mentioned in it. Return ONLY a raw JSON array, no markdown, no explanation,
no code fences. Each item must have exactly these keys:

{
  "event_date": "YYYY-MM-DD or empty string if not a clean/parseable date",
  "event_date_text": "the date exactly as written in the document",
  "title": "short title, under 10 words",
  "description": "one or two sentence description of what happened",
  "event_type": "one of: filing, hearing, notice, agreement, incident, correspondence, other",
  "source_snippet": "the exact sentence(s) from the document text that mention this event, under 250 characters"
}

If the document contains no dated events, return an empty array: []
Do not invent dates or events that are not explicitly present in the text.

Document text:
""" + document.ocr_text

    try:
        ai_response = ai_provider_service.call_llm(env, prompt)
        events = json.loads(ai_response)
    except (json.JSONDecodeError, ValueError) as e:
        env['ir.logging'].sudo().create({
            'name': 'law_case_review',
            'type': 'server',
            'level': 'ERROR',
            'message': 'Timeline extraction JSON parse failed for document %s: %s' % (document.id, str(e)),
            'path': 'law_case_review.timeline_extraction_service',
            'func': 'extract_timeline_events',
            'line': '0',
        })
        return []

    if not isinstance(events, list):
        return []

    results = []
    for item in events:
        if not isinstance(item, dict) or not item.get('title'):
            continue
        results.append({
            'event_date': item.get('event_date') or False,
            'event_date_text': item.get('event_date_text', ''),
            'title': item.get('title', '')[:250],
            'description': item.get('description', ''),
            'event_type': item.get('event_type') if item.get('event_type') in
                ('filing', 'hearing', 'notice', 'agreement', 'incident', 'correspondence', 'other')
                else 'other',
            'source_snippet': item.get('source_snippet', '')[:500],
        })
    return results