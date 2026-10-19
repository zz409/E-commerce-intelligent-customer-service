import sqlite3
import ladybug
import sqlite_vec

from pathlib import Path

SQLITE_PATH=Path(__file__).parents[2]/"data"/"sqlite.sqlite"
LDBD_PATH=Path(__file__).parents[2]/"data"/"lbdb.lbdb"

def insert_document(document_id,filename):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        with conn:
            conn.execute(
                """
                    INSERT INTO documents(
                        document_id,
                        filename
                    )
                    VALUES(?,?)
                """,
                (
                    document_id,
                    filename
                ),
            )

    finally:
        conn.close()
    

def insert_chunks(chunk_id,embedding,document_id,chunk_index,page,content):
    conn=sqlite3.connect(SQLITE_PATH)

    try:
        conn.enable_load_extension(True)

        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)

        with conn:
            conn.execute(
                """
                    INSERT INTO chunks(
                        chunk_id,
                        embedding,
                        document_id,
                        chunk_index,
                        page,
                        content
                    )
                    VALUES(?,?,?,?,?,?)
                """,
                (
                    chunk_id,
                    sqlite_vec.serialize_float32(embedding),
                    document_id,
                    chunk_index,
                    page,
                    content
                ),
            )
    
    finally:
        conn.close()

def insert_triples(document_id,chunk_id,page,triples):
    db=ladybug.Database(str(LDBD_PATH))

    try:
        conn=ladybug.Connection(db)

        try:
            for triple in triples:
                for node_id,name in [
                    (triple["subject_id"],triple["subject"]),
                    (triple["object_id"],triple["object"]),
                ]:
                    conn.execute(
                        """
                        MERGE(e:Entity{id:$id})
                        SET e.name=$name,
                            e.document_id=$document_id
                        """,
                        {
                            "id":node_id,
                            "name":name,
                            "document_id":document_id,
                        },
                    )

                conn.execute(
                    """
                    MATCH (a:Entity {id:$subject_id}),
                          (b:Entity {id:$object_id})
                    CREATE (a)-[:Fact{
                        predicate:$predicate,
                        document_id:$document_id,
                        chunk_id:$chunk_id,
                        page:$page,
                        evidence:$evidence
                    }]->(b)
                    """,
                    {
                        "subject_id":triple["subject_id"],
                        "object_id":triple["object_id"],
                        "predicate":triple["predicate"],
                        "document_id":document_id,
                        "chunk_id":chunk_id,
                        "page":page,
                        "evidence":triple["evidence"],
                    },
                )
        finally:
            conn.close()
    finally:
        db.close()


def list_documents():
    conn=sqlite3.connect(SQLITE_PATH)
    try:
        return conn.execute(
            "SELECT document_id,filename FROM documents"
        ).fetchall()
    finally:
        conn.close()
    
def delete_document(document_id):
    conn=sqlite3.connect(SQLITE_PATH)
    try:
        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)

        with conn:
            conn.execute(
                "DELETE FROM chunks WHERE document_id=?",
                (document_id,),
            )

            conn.execute(
                "DELETE FROM documents WHERE document_id=?",
                (document_id,),
            )
    finally:
        conn.close()

    db=ladybug.Database(str(LDBD_PATH))

    try:
        conn=ladybug.Connection(db)

        try:
            conn.execute(
                """
                MATCH (e:Entity)
                WHERE e.document_id=$document_id
                DETACH DELETE e
                """,
                {"document_id":document_id},
            )

        finally:conn.close()

    finally:
        db.close()