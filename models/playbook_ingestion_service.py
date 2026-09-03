# -*- coding: utf-8 -*-
import base64
import json
import requests
from ..services import ai_provider_service
from ..services.embedding_service import EmbeddingService
import re


def run_ocr(env, file_data, file_name):
    docling_url = env['ir.config_parameter'].sudo().get_param(
        'law_case_review.docling_service_url', default='http://localhost:8500'
    )
    file_content = base64.b64decode(file_data)
    response = requests.post(
        f'{docling_url}/extract-text',
        files={'file': (file_name, file_content)},
        timeout=1800
    )
    if response.status_code != 200:
        raise Exception('OCR extraction failed.')
    return response.json().get('text')


def split_into_chunks(text, max_chunk_size=4000):
    raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    heading_pattern = re.compile(r'^##\s+\d+[A-Z]?\.')
    merged_paragraphs = []
    i = 0
    while i < len(raw_paragraphs):
        para = raw_paragraphs[i]
        if heading_pattern.match(para):
            group = [para]
            j = i + 1
            while j < len(raw_paragraphs) and not heading_pattern.match(raw_paragraphs[j]):
                group.append(raw_paragraphs[j])
                j += 1
            merged_paragraphs.append('\n\n'.join(group))
            i = j
        else:
            merged_paragraphs.append(para)
            i += 1

    chunks = []
    current = ""
    for para in merged_paragraphs:
        if len(current) + len(para) + 2 > max_chunk_size and current:
            chunks.append(current)
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current:
        chunks.append(current)

    return chunks


def split_and_dispatch_chunks(env, source):
    source.write({'state': 'processing'})
    env.cr.commit()

    try:
        text = run_ocr(env, source.file, source.file_name)
        source.write({'ocr_text': text})
        env.cr.commit()
    except Exception as e:
        source.write({'state': 'error'})
        env.cr.commit()
        raise Exception('OCR step failed: %s' % str(e))

    chunks = split_into_chunks(text)

    source.write({
        'chunk_count': len(chunks),
        'chunk_done_count': 0,
    })
    env.cr.commit()

    for i, chunk in enumerate(chunks):
        source.with_delay(description="Process chunk %d of source: %s" % (i, source.name)).button_process_chunk_job(i, chunk)


def process_single_chunk(env, source, chunk_index, chunk_text):
    try:
        clauses = extract_clauses_from_chunk(env, chunk_text)
    except Exception as e:
        env['ir.logging'].sudo().create({
            'name': 'law_case_review',
            'type': 'server',
            'level': 'ERROR',
            'message': 'Chunk %d extraction failed for source %d: %s' % (chunk_index, source.id, str(e)),
            'path': 'law_case_review.playbook_ingestion',
            'func': 'process_single_chunk',
            'line': '0',
        })
        clauses = []

    existing_clauses = env['law.playbook.clause'].search([('source_id', '=', source.id)])
    seen_numbers = set(existing_clauses.mapped('clause_number'))

    for clause in clauses:
        number = clause.get('clause_number')
        if not number or number in seen_numbers:
            continue
        seen_numbers.add(number)

        clause_text = clause.get('text') or ''
        title = clause.get('title') or ''

        try:
            embedding_input = f"Article {number}: {title}. {title}. {clause_text[:200]}"
            embedding_vector = EmbeddingService.embed(env, embedding_input)
            model_option = EmbeddingService.get_active_model(env)
            embedding_model = model_option.model_string
        except Exception as e:
            env['law.playbook.clause'].create({
                'source_id': source.id,
                'clause_number': number,
                'title': title,
                'text': clause_text,
            })
            continue

        new_clause = env['law.playbook.clause'].create({
            'source_id': source.id,
            'clause_number': number,
            'title': title,
            'text': clause_text,
            'embedding_model': embedding_model,
        })
        EmbeddingService.sync_embedding_vector(env, 'law_playbook_clause', new_clause.id, embedding_vector, model_option.dimension)

    source.write({'chunk_done_count': source.chunk_done_count + 1 })
    env.cr.commit()

    if source.chunk_done_count >= source.chunk_count:
        source.write({'state': 'done'})
        env.cr.commit()


def extract_clauses_from_chunk(env, chunk_text):
    prompt = (
        "This is a piece of a legal document. Find every distinct Article or Section "
        "in this text. For each one, give me the exact number, title, and full text.\n"
        "Reply ONLY with JSON in this exact format, no explanation, no markdown:\n"
        "[{\"clause_number\": \"\", \"title\": \"\", \"text\": \"\"}]\n\n"
        "If no complete article/section is found in this text, reply with an empty list: []\n\n"
        "Text:\n" + chunk_text
    )
    answer = ai_provider_service.call_llm(env, prompt)
    return json.loads(answer)