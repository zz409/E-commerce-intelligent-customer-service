import sqlite3
from uuid import uuid4

from pathlib import Path

SQLITE_PATH=Path(__file__).parents[2]/"data"/"sqlite.sqlite"

def create_conversation(user_id,conversation_id):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            conn.execute(
                """
                INSERT INTO conversation (
                    user_id,
                    conversation_id
                )
                VALUES (?,?)
                """,
                (
                    user_id,
                    conversation_id,
                ),
            )
    finally:
        conn.close()    

def insert_message(conversation_id,role,content):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    id,
                    conversation_id,
                    role,
                    content
                )
                VALUES (?,?,?,?)
                """,
                (
                    uuid4().hex,
                    conversation_id,
                    role,
                    content
                ),
            )
    finally:
        conn.close()

def get_conversations(user_id):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            rows=conn.execute(
                """
                SELECT conversation_id
                FROM conversation
                WHERE user_id = ?
                ORDER BY rowid
                """,
                (user_id,),
            ).fetchall()

            return [row[0] for row in rows]
    finally:
        conn.close()

def get_conversaiton(conversation_id):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            return conn.execute(
                """
                SELECT role,content 
                FROM conversations
                WHERE conversation_id = ?
                ORDER BY rowid
                """,
                (conversation_id,),
            ).fetchall()
    finally:
        conn.close()

def delete_conversaion(conversation_id):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            conn.execute(
                """
                DELETE FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )

            conn.execute("DELETE FROM conversation WHERE conversation_id=?",
                (conversation_id,),
            )
        
    finally:
        conn.close()
