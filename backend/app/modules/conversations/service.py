import os
import sqlite3
import json
import logging

from contextlib import closing
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_mcp_adapters.client import MultiServerMCPClient

logger=logging.getLogger(__name__)

BACKEND_DIR=Path(__file__).resolve().parents[3]

DATA_DIR=BACKEND_DIR/"data"
DATA_DIR.mkdir(parents=True,exist_ok=True)

DATABASE_PATH=DATA_DIR/"checkpoints.sqlite"

load_dotenv()

class ConversationNotFoundError(Exception):
    pass

def initialize_database()->None:
    with closing(sqlite3.connect(DATABASE_PATH)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations(
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_conversation()->str:
    initialize_database()
    conversation_id=str(uuid4())
    with closing(sqlite3.connect(DATABASE_PATH)) as conn, conn:
        conn.execute(
            "INSERT INTO conversations (id) VALUES (?)",
            (conversation_id,),
        )

    return conversation_id

def send_message(conversation_id:str,content:str):
    initialize_database()
    with closing(sqlite3.connect(DATABASE_PATH)) as conn, conn:
        exists=conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

    if not exists:
        raise ConversationNotFoundError()

    model=init_chat_model(
        model="qwen3.8-max",
        model_provider="openai",
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    )

    def generate():
        try:
            with SqliteSaver.from_conn_string(
                str(DATABASE_PATH)
            ) as checkpointer:
                agent=create_agent(
                    model=model,
                    tools=[],
                    system_prompt=(
                        "你是电商客服助手，请使用中文回答。"
                        "尚未接入真实业务接口，不要编造订单或商品数据。"
                    ),
                    checkpointer=checkpointer,
                )

                for chunk,metadata in agent.stream(
                    {
                        "messages":[
                            {"role":"user","content":content}
                        ]
                    },
                    config={
                        "configurable":{
                            "thread_id":conversation_id
                        }
                    },
                    stream_mode="messages"
                ):
                    if metadata.get("langgraph_node") != "model":
                        continue

                    for block in chunk.content_blocks:
                        if block.get("type")=="text":
                            text=block.get("text","")
                            if text:
                                data=json.dumps(
                                    {"text":text},
                                    ensure_ascii=False,
                                )
                                yield f"event:delta\ndata:{data}\n\n"

            yield 'event:done\ndata: {}\n\n'

        except Exception:
            logger.exception("流式消息处理失败")
            data=json.dumps(
                {"message":"消息处理失败，请稍后重试"},
                ensure_ascii=False
            )
            yield f"event: error\ndata: {data}\n\n"

    return generate()
