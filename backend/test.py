from uuid import uuid4

from app.db.rag_db import (
    insert_document,
    insert_chunks,
    insert_triples,
    list_documents,
)


def main():
    # 每次测试生成不同 ID，避免主键冲突
    prefix = uuid4().hex

    document_id_1 = f"{prefix}_doc1"
    document_id_2 = f"{prefix}_doc2"

    chunk_id_1 = f"{document_id_1}:0"
    chunk_id_2 = f"{document_id_2}:0"

    # 1. 插入两条文档记录
    insert_document(document_id_1, "商品A说明书.pdf")
    insert_document(document_id_2, "商品B说明书.pdf")

    # 2. 插入两个文本块及向量
    # 仅用于验证存储，不是真实模型生成的语义向量
    embedding_1 = [1.0] + [0.0] * 1023
    embedding_2 = [0.0, 1.0] + [0.0] * 1022

    insert_chunks(
        chunk_id=chunk_id_1,
        embedding=embedding_1,
        document_id=document_id_1,
        chunk_index=0,
        page=1,
        content="商品A的保修期限为一年。",
    )

    insert_chunks(
        chunk_id=chunk_id_2,
        embedding=embedding_2,
        document_id=document_id_2,
        chunk_index=0,
        page=2,
        content="商品B的生产商是公司B。",
    )

    # 3. 插入两条关系，同时创建对应实体节点
    insert_triples(
        document_id=document_id_1,
        chunk_id=chunk_id_1,
        page=1,
        triples=[
            {
                "subject_id": f"{document_id_1}:商品A",
                "subject": "商品A",
                "object_id": f"{document_id_1}:一年",
                "object": "一年",
                "predicate": "保修期限",
                "evidence": "商品A的保修期限为一年。",
            }
        ],
    )

    insert_triples(
        document_id=document_id_2,
        chunk_id=chunk_id_2,
        page=2,
        triples=[
            {
                "subject_id": f"{document_id_2}:商品B",
                "subject": "商品B",
                "object_id": f"{document_id_2}:公司B",
                "object": "公司B",
                "predicate": "生产商",
                "evidence": "商品B的生产商是公司B。",
            }
        ],
    )

    print("插入完成，本次文档 ID：")
    print(document_id_1)
    print(document_id_2)

    print("\n全部文档：")
    for row in list_documents():
        print(row)


if __name__ == "__main__":
    main()