import sqlite3

query_embeddings_cache_db_name = "/home/joshua/extrafiles/projects/WhisperingAssistant/whispering_assistant/assets/docs/query_embeddings_cache.db"


def create_embedding_database():
    conn = sqlite3.connect(query_embeddings_cache_db_name)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS embeddings
    (input_text TEXT NOT NULL,
    embedding_instruction TEXT NOT NULL,
    embedding BLOB,
    PRIMARY KEY (input_text, embedding_instruction))
    """)
    conn.commit()
    conn.close()


create_embedding_database()

