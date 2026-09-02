# -*- coding: utf-8 -*-
import json
import re
from . import ai_provider_service
from .semantic_search_service import SemanticSearchService


class CaseQAService:

    FALLBACK_ANSWER = "The case documents and selected playbook sources do not contain information to answer this question."

    @staticmethod
    def _build_prompt(question, results):
        chunks = [r for r in results if r['type'] == 'chunk']
        clauses = [r for r in results if r['type'] == 'clause']

        parts = [
            "You are a legal assistant helping a lawyer with a specific case.",
            "Answer ONLY using the information given below. Do not use outside knowledge.",
            "Always respond in English, regardless of the language of the source text.",
            "If the information given does not answer the question, respond with exactly: \"" + CaseQAService.FALLBACK_ANSWER + "\"",
            "Cite the sources you used, using the exact labels shown between the --- markers.",
            "",
            "Respond ONLY as JSON, no markdown, no explanation outside the JSON:",
            "{\"answer\": \"<plain english answer>\", \"cited_labels\": [\"<label1>\", \"<label2>\"]}",
            "",
            "Question: " + question,
            "",
            "Case Document Excerpts:",
        ]

        if chunks:
            for r in chunks:
                chunk = r['chunk']
                label = f"{chunk.document_id.name} :: chunk {chunk.chunk_index}"
                parts.append(f"--- {label} ---")
                parts.append(chunk.chunk_text)
                parts.append("")
        else:
            parts.append("(none found)")
            parts.append("")

        parts.append("Playbook Clauses:")
        if clauses:
            for r in clauses:
                clause = r['clause']
                label = f"Article {clause.clause_number} :: {clause.title}"
                parts.append(f"--- {label} ---")
                parts.append(clause.text or '')
                parts.append("")
        else:
            parts.append("(none found)")
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def ask(env, case_id, question, top_k=8):
        case = env['law.case'].browse(case_id)
        case.ensure_one()

        cached = env['law.case.qa.log'].search([
            ('case_id', '=', case_id),
            ('question', '=', question),
            ('source_write_date', '=', case.qa_last_content_update),
        ], limit=1)
        if cached:
            return {
                'answer': cached.answer,
                'cited_chunks': cached.cited_chunk_ids,
                'cited_clauses': cached.cited_clause_ids,
                'from_cache': True,
            }

        source_ids = case.playbook_source_ids.ids
        results = SemanticSearchService.search_case_context(
            env, question, case_id=case_id, source_ids=source_ids, top_k=top_k
        )

        if not results:
            answer_text = CaseQAService.FALLBACK_ANSWER
            cited_chunks = env['law.case.document.chunk']
            cited_clauses = env['law.playbook.clause']
        else:
            prompt = CaseQAService._build_prompt(question, results)
            from odoo.exceptions import UserError
            try:
                answer = ai_provider_service.call_llm(env, prompt)
            except Exception as e:
                raise UserError(str(e))
            cleaned = re.sub(r'^```json\s*|\s*```$', '', answer.strip())

            try:
                parsed = json.loads(cleaned)
                answer_text = parsed.get('answer', CaseQAService.FALLBACK_ANSWER)
                cited_labels = parsed.get('cited_labels', [])
            except (json.JSONDecodeError, ValueError):
                answer_text = CaseQAService.FALLBACK_ANSWER
                cited_labels = []

            if answer_text.strip() == CaseQAService.FALLBACK_ANSWER:
                cited_labels = []

            candidate_chunks = [r['chunk'] for r in results if r['type'] == 'chunk']
            candidate_clauses = [r['clause'] for r in results if r['type'] == 'clause']

            cited_chunks = env['law.case.document.chunk'].browse([
                c.id for c in candidate_chunks
                if f"{c.document_id.name} :: chunk {c.chunk_index}" in cited_labels
            ])
            cited_clauses = env['law.playbook.clause'].browse([
                c.id for c in candidate_clauses
                if f"Article {c.clause_number} :: {c.title}" in cited_labels
            ])

        env['law.case.qa.log'].create({
            'case_id': case_id,
            'question': question,
            'answer': answer_text,
            'source_write_date': case.qa_last_content_update,
            'cited_chunk_ids': [(6, 0, cited_chunks.ids)],
            'cited_clause_ids': [(6, 0, cited_clauses.ids)],
            'hidden_from_chat': False,
        })

        return {
            'answer': answer_text,
            'cited_chunks': cited_chunks,
            'cited_clauses': cited_clauses,
            'from_cache': False,
        }