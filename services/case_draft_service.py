# -*- coding: utf-8 -*-
import re
import markdown
from . import ai_provider_service


class CaseDraftService:

    DRAFT_TYPE_LABELS = {
        'legal_notice': 'Legal Notice',
        'reply_letter': 'Reply Letter',
    }

    @staticmethod
    def _build_prompt(draft_type, case, instructions):
        label = CaseDraftService.DRAFT_TYPE_LABELS.get(draft_type, draft_type)

        parts = [
            "You are a legal assistant helping a lawyer draft a document for a specific case.",
            f"Write a first draft of a {label}, using ONLY the case facts given below.",
            "Do not invent facts, dates, names, or events that are not present in the case material.",
            "This is a DRAFT for lawyer review only — it will never be sent anywhere automatically.",
            f"Write in formal legal document style appropriate for a {label}.",
            "",
            "CRITICAL FORMATTING RULES:",
            "- Output ONLY raw HTML tags. Never use markdown syntax.",
            "- Never use ** for bold - use <strong> tags instead.",
            "- Never use * or - for bullet points - use <ul><li> tags instead.",
            "- Never wrap your output in ```html code fences or any code fences at all.",
            "- Do not include any text before the first tag or after the last closing tag.",
            "- Use <p> for paragraphs and <h3> for section headings.",
            "",
            "Case Document Excerpts:",
        ]

        documents = case.document_ids.filtered(lambda d: d.ocr_text)
        if documents:
            for doc in documents:
                parts.append(f"--- {doc.name} ---")
                parts.append(ai_provider_service.wrap_untrusted_text(doc.ocr_text))
                parts.append("")
        else:
            parts.append("(no case documents with extracted text available)")
            parts.append("")

        if instructions:
            parts.append("Additional instructions from the lawyer:")
            parts.append(instructions)
            parts.append("")

        parts.append(f"Now write the {label}.")

        return "\n".join(parts)

    @staticmethod
    def generate(env, draft_id):
        draft = env['law.case.draft'].browse(draft_id)
        draft.ensure_one()

        prompt = CaseDraftService._build_prompt(
            draft.draft_type, draft.case_id, draft.instructions
        )
        result = ai_provider_service.call_llm(env, prompt)
        result = re.sub(r'^```html\s*|^```\s*|```\s*$', '', result.strip())
        return markdown.markdown(result)