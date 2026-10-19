import shutil
import os
import re

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer
from app.db import rag_db
from pathlib import Path
from pypdf import PdfReader
from uuid import uuid4

load_dotenv()

PDF_DIR=Path(__file__).resolve().parents[3]/"data"/"pdfs"

def insert_document(file,filename):

    transformer_model=init_chat_model(
        model_provider="openai",
        model="qwen3.8-max",
        api_key=os.getenv("QWEN_API_KEY"),
        base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    )

    transformer=LLMGraphTransformer(
        llm=transformer_model,
    )

    embedding_model=init_embeddings(
        "openai:qwen3.7-text-embedding",
        api_key=os.getenv("EMBEDDING_MODEL_API_KEY"),
        base_url=os.getenv("EMBEDDING_MODEL_BASE_URL"),
        check_embedding_ctx_length=False,
    )
    document_id=uuid4().hex
    target_path=PDF_DIR/f"{document_id}.pdf"


    with target_path.open("wb") as target:
        shutil.copyfileobj(file,target)

    rag_db.insert_document(document_id,filename)

    chunks=[]

    reader=PdfReader(target_path)

    for page_number,page in enumerate(reader.pages,start=1):
        text=page.extract_text() or ""

        text=text.replace("\r\n","\n").replace("\r","\n")
        text=text.replace("\u00a0"," ")
        text=text.replace("\u200b","")
        text=text.replace("\x00","")

        text=re.sub(r"[ \t]+", " ", text)
        text=re.sub(r" *\n *", "\n", text)
        text=re.sub(r"\n{3,}", "\n\n", text)

        text=text.strip()

        texts=RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n","\n","。","！","？","；"," ",""],
        ).split_text(text)

        for content in texts:
            chunks.append({
                "page":page_number,
                "content":content,
                "vector":[],
            })

    if chunks:
        vectors=embedding_model.embed_documents(
            [chunk["content"] for chunk in chunks]
        )
        for chunk_index,(chunk,embedding) in enumerate(zip(chunks,vectors)):

            chunk_id=uuid4().hex

            rag_db.insert_chunks(
                chunk_id=chunk_id,
                embedding=embedding,
                document_id=document_id,
                chunk_index=chunk_index,
                page=chunk["page"],
                content=chunk["content"],
            )

            graphs=transformer.convert_to_graph_documents([
                Document(
                    page_content=chunk["content"],
                    metadata={
                        "document_id":document_id,
                        "chunk_id":chunk_id,
                        "page":chunk["page"],
                    },
                )
            ])

            triples=[]

            for graph in graphs:
                for relation in graph.relationships:
                    triples.append({
                        "subject_id":uuid4().hex,
                        "subject":str(relation.source.id),
                        "predicate":relation.type,
                        "object_id":uuid4().hex,
                        "object":str(relation.target.id),
                        "evidence":chunk["content"],
                    })

            if triples:
                rag_db.insert_triples(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    page=chunk["page"],
                    triples=triples,
                )
    
def list_document():
    return rag_db.list_documents()
    
def delete_document(document_id):
    rag_db.delete_document(document_id=document_id)
    path=PDF_DIR/f"{document_id}.pdf"
    path.unlink()