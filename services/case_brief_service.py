# -*- coding: utf-8 -*-
import re
import markdown
from . import ai_provider_service

def generate_case_brief(env, case):
    documents_text = ""
    for doc in case.document_ids:
        if doc.ocr_text:
            documents_text += f"\n\n--- Document: {doc.name} ({doc.document_type}) ---\n{ai_provider_service.wrap_untrusted_text(doc.ocr_text)}"

    if not documents_text:
        return "<p><em>No extracted document text available yet. Run Extract Text on the case documents first.</em></p>"

    prompt = f"""
You are preparing a case handoff brief for a lawyer who is new to this case.
Read all the source material below and write a structured brief.

CRITICAL FORMATTING RULES:
- Output ONLY raw HTML tags. Never use markdown syntax.
- Never use ** for bold - use <strong> tags instead.
- Never use * or - for bullet points - use <ul><li> tags instead.
- Never wrap your output in ```html code fences or any code fences at all.
- Do not include any text before the first <h3> tag or after the last closing tag.

Include exactly these four sections, in this order, each with an <h3> header:
<h3>Background</h3>, <h3>Key Incidents</h3>, <h3>Chronology</h3>, <h3>Current Status</h3>
Use <p> for paragraphs and <ul><li> for the chronology list.

Only use facts present in the material below. Do not invent details.

Case description: {case.description or ''}
Matter type: {case.matter_type or ''}
Outcome: {case.outcome}

Source documents:
{documents_text}
"""
    result = ai_provider_service.call_llm(env, prompt)
    result = re.sub(r'^```html\s*|^```\s*|```\s*$', '', result.strip())
    return markdown.markdown(result)