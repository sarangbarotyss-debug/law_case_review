# -*- coding: utf-8 -*-
import math


class SemanticSearchService:
    MIN_SCORE = 0.65

    @staticmethod
    def cosine_similarity(vec1, vec2):
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    @staticmethod
    def _column_and_cast(dimension):
        """
        Returns (column_name, cast_type) for a given embedding dimension.
        Dimensions above 2000 can't use a plain `vector` index (pgvector's
        hnsw cap), so those columns are indexed via `halfvec` instead - the
        query needs to cast to the same type the index was built with.
        """
        column = f"embedding_vector_{dimension}"
        cast_type = f"halfvec({dimension})" if dimension > 2000 else "vector"
        return column, cast_type

    @staticmethod
    def search(env, query_text, query_embedding=None, source_type=None, source_ids=None, top_k=5):
        from . embedding_service import EmbeddingService
        if query_embedding is None:
            query_embedding = EmbeddingService.embed(env, query_text)
        model_option = EmbeddingService.get_active_model(env)
        active_model_string = model_option.model_string
        column, cast_type = SemanticSearchService._column_and_cast(model_option.dimension)

        MIN_SCORE = SemanticSearchService.MIN_SCORE
        MIN_RESULTS = 3
        CANDIDATE_LIMIT = 20  # pull extra candidates, then apply threshold/fallback logic in Python 

        vector_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

        where_clauses = [f"{column} IS NOT NULL", "embedding_model = %s"]
        params = [active_model_string]

        if source_ids:
            where_clauses.append("source_id IN %s")
            params.append(tuple(source_ids))
        elif source_type:
            where_clauses.append("source_id IN (SELECT id FROM law_playbook_source WHERE source_type = %s)")
            params.append(source_type)

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT id, 1 - ({column} <=> %s::{cast_type}) AS score
            FROM law_playbook_clause
            WHERE {where_sql}
            ORDER BY {column} <=> %s::{cast_type}
            LIMIT %s
        """
        params = [vector_literal] + params + [vector_literal, CANDIDATE_LIMIT]

        env.cr.execute(query, params)
        rows = env.cr.fetchall()  # [(id, score), ...]

        above_threshold = [(score, rid) for rid, score in rows if score >= MIN_SCORE]
        chosen = above_threshold if len(above_threshold) >= MIN_RESULTS else [(score, rid) for rid, score in rows[:MIN_RESULTS]]
        chosen = chosen[:top_k]

        clause_ids = [rid for score, rid in chosen]
        clauses_by_id = {c.id: c for c in env['law.playbook.clause'].browse(clause_ids)}

        return [{'score': score, 'clause': clauses_by_id[rid]} for score, rid in chosen if rid in clauses_by_id]

    @staticmethod
    def search_case_context(env, query_text, case_id, source_ids=None, top_k=8):
        """
        Searches both the case's own document chunks and the case's selected
        playbook clauses, scoped strictly to this case - no other case's
        documents, no unrelated playbook sources.
        Returns a combined, score-sorted list of type-tagged results:
        [{'type': 'chunk', 'score': ..., 'chunk': rec}, {'type': 'clause', 'score': ..., 'clause': rec}, ...] 
        """
        from . embedding_service import EmbeddingService
        query_embedding = EmbeddingService.embed(env, query_text)
        model_option = EmbeddingService.get_active_model(env)
        active_model_string = model_option.model_string
        column, cast_type = SemanticSearchService._column_and_cast(model_option.dimension)
        vector_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

        results = []

        # 1. Case's own document chunks
        chunk_query = f"""
            SELECT id, 1 - ({column} <=> %s::{cast_type}) AS score
            FROM law_case_document_chunk
            WHERE case_id = %s AND {column} IS NOT NULL AND embedding_model = %s
            ORDER BY {column} <=> %s::{cast_type}
            LIMIT %s
        """
        env.cr.execute(chunk_query, [vector_literal, case_id, active_model_string, vector_literal, top_k])
        chunk_rows = env.cr.fetchall()
        chunks_by_id = {c.id: c for c in env['law.case.document.chunk'].browse([rid for rid, score in chunk_rows])}
        for rid, score in chunk_rows:
            if rid in chunks_by_id:
                results.append({'type': 'chunk', 'score': score, 'chunk': chunks_by_id[rid]})

        # 2. Playbook clauses from this case's selected sources only
        if source_ids:
            clause_query = f"""
                SELECT id, 1 - ({column} <=> %s::{cast_type}) AS score
                FROM law_playbook_clause
                WHERE source_id IN %s AND {column} IS NOT NULL AND embedding_model = %s
                ORDER BY {column} <=> %s::{cast_type}
                LIMIT %s
            """
            env.cr.execute(clause_query, [vector_literal, tuple(source_ids), active_model_string, vector_literal, top_k])
            clause_rows = env.cr.fetchall()
            clauses_by_id = {c.id: c for c in env['law.playbook.clause'].browse([rid for rid, score in clause_rows])}
            for rid, score in clause_rows:
                if rid in clauses_by_id:
                    results.append({'type': 'clause', 'score': score, 'clause': clauses_by_id[rid]})

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]