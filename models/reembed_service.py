# -*- coding: utf-8 -*-
from .. services.embedding_service import EmbeddingService


def _find_missing_ids(env, model_name, dimension, model_string, limit=None):
    table = 'law_playbook_clause' if model_name == 'law.playbook.clause' else 'law_case_document_chunk'
    column = f"embedding_vector_{dimension}"
    query = f"SELECT id FROM {table} WHERE {column} IS NULL OR embedding_model != %s"
    params = [model_string]
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    env.cr.execute(query, params)
    return [row[0] for row in env.cr.fetchall()]


def count_missing_for_model(env, new_model):
    dimension = new_model.dimension
    clause_ids = _find_missing_ids(env, 'law.playbook.clause', dimension, new_model.model_string)
    chunk_ids = _find_missing_ids(env, 'law.case.document.chunk', dimension, new_model.model_string)
    return len(clause_ids) + len(chunk_ids)


def _reembed_clause(env, clause, new_model, dimension):
    embedding_input = f"Article {clause.clause_number}: {clause.title or ''}. {clause.title or ''}. {(clause.text or '')[:200]}"
    embedding_vector = EmbeddingService.embed(env, embedding_input)
    clause.write({'embedding_model': new_model.model_string})
    EmbeddingService.sync_embedding_vector(env, 'law_playbook_clause', clause.id, embedding_vector, dimension)


def _reembed_chunk(env, chunk, new_model, dimension):
    embedding_vector = EmbeddingService.embed(env, chunk.chunk_text)
    chunk.write({'embedding_model': new_model.model_string})
    EmbeddingService.sync_embedding_vector(env, 'law_case_document_chunk', chunk.id, embedding_vector, dimension)


def process_batch_for_model(env, new_model, batch_size=5):
    """
    Processes up to batch_size records still needing re-embedding for
    new_model, mixing clauses and chunks in one pass. Returns counts for
    this batch only - caller (the wizard) accumulates totals across calls.
    """
    dimension = new_model.dimension
    processed = 0
    errors = 0

    clause_ids = _find_missing_ids(env, 'law.playbook.clause', dimension, new_model.model_string, limit=batch_size)
    for clause in env['law.playbook.clause'].browse(clause_ids):
        try:
            with env.cr.savepoint():
                _reembed_clause(env, clause, new_model, dimension)
            processed += 1
        except Exception as e:
            errors += 1
            env['ir.logging'].sudo().create({
                'name': 'law_case_review',
                'type': 'server',
                'level': 'ERROR',
                'message': 'Re-embed failed for clause %d: %s' % (clause.id, str(e)),
                'path': 'law_case_review.reembed_service',
                'func': 'process_batch_for_model',
                'line': '0',
            })
        env.cr.commit()

    remaining_slots = batch_size - processed - errors
    if remaining_slots > 0:
        chunk_ids = _find_missing_ids(env, 'law.case.document.chunk', dimension, new_model.model_string, limit=remaining_slots)
        for chunk in env['law.case.document.chunk'].browse(chunk_ids):
            try:
                with env.cr.savepoint():
                    _reembed_chunk(env, chunk, new_model, dimension)
                processed += 1
            except Exception as e:
                errors += 1
                env['ir.logging'].sudo().create({
                    'name': 'law_case_review',
                    'type': 'server',
                    'level': 'ERROR',
                    'message': 'Re-embed failed for chunk %d: %s' % (chunk.id, str(e)),
                    'path': 'law_case_review.reembed_service',
                    'func': 'process_batch_for_model',
                    'line': '0',
                })
            env.cr.commit()

    return processed, errors