import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    psycopg_url = os.getenv("PSYCOPG_URL")
    return psycopg.connect(psycopg_url, autocommit=False)

async def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            bio TEXT,
            website TEXT,
            linkedin_url TEXT,
            qr_token CHAR(6) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dance_card_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scanner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT now(),
            UNIQUE(owner_id, scanner_id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
