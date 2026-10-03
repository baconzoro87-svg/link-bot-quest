import os
import aiosqlite
from crypto import encrypt_token, decrypt_token

DB_PATH = "linked_accounts.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS linked_accounts (
                user_id     INTEGER PRIMARY KEY,
                token_enc   TEXT NOT NULL,
                user_tag    TEXT,
                linked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    try:
        os.chmod(DB_PATH, 0o600)
    except Exception:
        pass


async def save_token(user_id: int, token_plaintext: str, user_tag: str = ""):
    enc = encrypt_token(token_plaintext)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO linked_accounts "
            "(user_id, token_enc, user_tag) VALUES (?, ?, ?)",
            (user_id, enc, user_tag),
        )
        await db.commit()


async def get_token(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT token_enc FROM linked_accounts WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return decrypt_token(row[0]) if row else None


async def get_display_tag(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_tag FROM linked_accounts WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def delete_token(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM linked_accounts WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def list_linked_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, user_tag, linked_at FROM linked_accounts"
        ) as cursor:
            return await cursor.fetchall()
