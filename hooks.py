# -*- coding: utf-8 -*-

SUPPORTED_DIMENSIONS = [768, 1024, 1536, 3072]


def post_init_hook(env):
    """
    Sets up pgvector for semantic search: enables the extension, adds one
    vector column per supported embedding dimension (see SUPPORTED_DIMENSIONS),
    and builds a similarity-search index on each. Safe to re-run (all
    statements use IF NOT EXISTS), so this also works cleanly on module
    upgrade.

    Why multiple columns: a Postgres `vector` column has one fixed
    dimension. Different embedding models (Mistral, OpenAI, Google, etc.)
    output different dimensions. Rather than lock the system to one
    dimension permanently, we prepare a column for each realistic size in
    advance, so switching the active embedding model never requires a live
    schema migration - it just uses a different, already-existing column.
    """
    cr = env.cr

    cr.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    for table in ('law_playbook_clause', 'law_case_document_chunk'):
        for dim in SUPPORTED_DIMENSIONS:
            column = f"embedding_vector_{dim}"
            index_name = f"{table}_{column}_hnsw_idx"

            cr.execute(f"""
                ALTER TABLE {table}
                ADD COLUMN IF NOT EXISTS {column} vector({dim});
            """)

            cr.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = %s AND indexname = %s;
            """, [table, index_name])
            if not cr.fetchone():
                if dim > 2000:
                    # HNSW indexes cap at 2000 dims natively; halfvec (half
                    # precision) raises that ceiling to 4000, at the cost of
                    # minor precision loss - acceptable for similarity search.
                    cr.execute(f"""
                        CREATE INDEX {index_name}
                        ON {table} USING hnsw (({column}::halfvec({dim})) halfvec_cosine_ops);
                    """)
                else:
                    cr.execute(f"""
                        CREATE INDEX {index_name}
                        ON {table} USING hnsw ({column} vector_cosine_ops);
                    """)