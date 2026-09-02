# -*- coding: utf-8 -*-
from .semantic_search_service import SemanticSearchService


def find_matching_playbook_clauses(env, query_text, source_type=None, source_ids=None, top_k=5):
    if not query_text or not query_text.strip():
        return []

    results = SemanticSearchService.search(
        env,
        query_text=query_text,
        source_type=source_type,
        source_ids=source_ids,
        top_k=top_k,
    )
    return results