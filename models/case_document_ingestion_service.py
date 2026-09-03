# -*- coding: utf-8 -*-
import json
from ..services.embedding_service import EmbeddingService


def split_into_chunks(text, chunk_size=4000, overlap=500):
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def chunk_and_embed_document(env, document):
    if not document.ocr_text:
        return

    env['law.case.document.chunk'].search([('document_id', '=', document.id)]).unlink()

    chunks = split_into_chunks(document.ocr_text)
    model_option = EmbeddingService.get_active_model(env)
    active_model = model_option.model_string
    for i, chunk_text in enumerate(chunks):
        try:
            embedding_vector = EmbeddingService.embed(env, chunk_text)
        except Exception as e:
            env['ir.logging'].sudo().create({
                'name': 'law_case_review',
                'type': 'server',
                'level': 'ERROR',
                'message': 'Embedding failed for chunk %d of document %d: %s' % (i, document.id, str(e)),
                'path': 'law_case_review.case_document_ingestion',
                'func': 'chunk_and_embed_document',
                'line': '0',
            })
            continue
        new_chunk = env['law.case.document.chunk'].create({
            'document_id': document.id,
            'chunk_text': chunk_text,
            'chunk_index': i,
            'embedding_model': active_model,
        })
        EmbeddingService.sync_embedding_vector(env, 'law_case_document_chunk', new_chunk.id, embedding_vector, model_option.dimension)