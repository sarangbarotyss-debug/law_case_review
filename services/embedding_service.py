# -*- coding: utf-8 -*-
import hashlib
import json
import requests
from odoo.exceptions import UserError


class EmbeddingService:

    MISTRAL_API_URL = "https://api.mistral.ai/v1/embeddings"
    GOOGLE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

    @staticmethod
    def get_active_model(env):
        model_id = env['ir.config_parameter'].sudo().get_param('law_case_review.embedding_model_id')
        if not model_id:
            raise UserError("No embedding model is configured. Please set one in Settings.")
        model_option = env['law.embedding.model.option'].sudo().browse(int(model_id))
        if not model_option.exists():
            raise UserError("The configured embedding model no longer exists. Please reselect one in Settings.")
        return model_option

    @staticmethod
    def embed(env, text):
        model_option = EmbeddingService.get_active_model(env)
        cache_key = hashlib.sha256(f"{model_option.model_string}:{model_option.dimension}:{text}".encode()).hexdigest()
        cached = env['law.ai.cache'].sudo().search([
            ('cache_key', '=', cache_key),
            ('cache_type', '=', 'embedding'),
        ], limit=1)
        if cached:
            return json.loads(cached.value)
        if model_option.provider == 'google':
            embedding = EmbeddingService._call_google(env, model_option.model_string, text, model_option.dimension)
        else:
            embedding = EmbeddingService._call_mistral(env, model_option.model_string, text)

        env['law.ai.cache'].sudo().create({
            'cache_key': cache_key,
            'cache_type': 'embedding',
            'value': json.dumps(embedding),
        })
        return embedding

    @staticmethod
    def _call_mistral(env, model_string, text):
        api_key = env['ir.config_parameter'].sudo().get_param('law_case_review.mistral_api_key')
        if not api_key:
            raise UserError("Mistral API key is not configured. Please set it in Settings.")
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": model_string, "input": text}
        response = requests.post(
            EmbeddingService.MISTRAL_API_URL,
            json=payload,
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    @staticmethod
    def _call_google(env, model_string, text, dimension=None):
        api_key = env['ir.config_parameter'].sudo().get_param('law_case_review.google_api_key')
        if not api_key:
            raise UserError("Google API key is not configured. Please set it in Settings.")
        url = EmbeddingService.GOOGLE_API_URL.format(model=model_string)
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": f"models/{model_string}",
            "content": {"parts": [{"text": text}]},
        }
        # Google's default output is 3072-dim; requesting a smaller size
        # (768/1536) via outputDimensionality lets it fit our other
        # prepared vector columns instead of always using the 3072 one.
        if dimension:
            payload["outputDimensionality"] = dimension
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]

    @staticmethod
    def sync_embedding_vector(env, table, record_id, embedding_vector, dimension):
        """
        Writes embedding_vector (a plain Python list of floats) into the
        dimension-specific Postgres `vector` column for one record - e.g.
        embedding_vector_1024 for a 1024-dim model. These columns aren't
        real Odoo fields (added via raw SQL), so the ORM can't set them
        directly - every place that saves an embedding must call this too,
        or that record silently won't show up in pgvector-based searches.
        """
        column = f"embedding_vector_{dimension}"
        vector_literal = '[' + ','.join(str(x) for x in embedding_vector) + ']'
        env.cr.execute(
            f"UPDATE {table} SET {column} = %s::vector WHERE id = %s",
            [vector_literal, record_id]
        )