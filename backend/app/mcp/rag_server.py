import os
from dotenv import load_dotenv

from openai import OpenAI
from mcp.server.fastmcp import FastMCP
from app.db import rag_db
from langchain.embeddings import init_embeddings
from langchain_neo4j import LLMGraphTransformer
from langchain.chat_models import init_chat_model
from langchain_core.documents import Document

load_dotenv()

mcp=FastMCP("知识库检索服务")

@mcp.tool()
def rag(text)->list[dict]:
    """RAG检索，返回相关片段"""

    results=[]

    client = OpenAI(
        api_key=os.environ["RERANK_MODEL_API_KEY"],
        base_url=os.environ["RERANK_MODEL_BASE_URL"],
    )

    embedding_model=init_embeddings(
        "openai:qwen3.7-text-embedding",
        api_key=os.getenv("EMBEDDING_MODEL_API_KEY"),
        base_url=os.getenv("EMBEDDING_MODEL_BASE_URL"),
        check_embedding_ctx_length=False,
    )

    transformer_model=init_chat_model(
        model_provider="openai",
        model="qwen3.8-max",
        api_key=os.getenv("QWEN_API_KEY"),
        base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    )

    transformer=LLMGraphTransformer(
        llm=transformer_model,
    )

    vector=embedding_model.embed_query(text=text)

    graphs=transformer.convert_to_graph_documents([
        Document(
            page_content=text,
        )
    ])

    entity_names=list({
        str(node.id)
        for graph in graphs
        for node in graph.nodes
    })

    vector_results = rag_db.search_chunk(vector)

    response=client.post(
        "/reranks",
        body={
            "model":"qwen3-rerank",
            "query":text,
            "documents":[
                row["content"]
                for row in vector_results
            ],
            "top_n":5,
        },
        cast_to=object,
    )

    for result in response["results"]:
        chunk=vector_results[result["index"]]

        results.append({
            "content":chunk["content"],
            "document_id":chunk["document_id"],
            "page":chunk["page"],
        })

    graph_results = rag_db.search_graph(entity_names=entity_names)

    for graph_result in graph_results:
        for relationship in graph_result["relationships"]:
            results.append({
                "content":relationship["evidence"],
                "document_id":relationship["document_id"],
                "page":relationship["page"],
            })
        
    return results

if __name__=="__main__":
    mcp.run(transport="stdio")