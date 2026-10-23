import os
import sqlite3
import json
import logging
import sys

from contextlib import closing
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AIMessage
from app.db import conversation_db

logger=logging.getLogger(__name__)

BACKEND_DIR=Path(__file__).resolve().parents[3]

client=MultiServerMCPClient({
    "rag":{
        "transport":"stdio",
        "command":sys.executable,
        "args":["-m","app.mcp.rag_server"],
        "cwd":str(BACKEND_DIR)
    }
})

DATA_DIR=BACKEND_DIR/"data"
DATA_DIR.mkdir(parents=True,exist_ok=True)

DATABASE_PATH=DATA_DIR/"checkpoints.sqlite"

load_dotenv()


class ConversationNotFoundError(Exception):
    pass

def create_conversation(user_id:str)->str:
    conversation_id=str(uuid4())
    conversation_db.create_conversation(user_id,conversation_id)
    return conversation_id
    
def send_message(conversation_id:str,content:str):

    model=init_chat_model(
        model="qwen3.8-max",
        model_provider="openai",
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    )

    conversation_db.insert_message(
        conversation_id=conversation_id,
        content=content,
        role="user"
    )

    async def generate():
        try:
            tools=await client.get_tools()

            async with AsyncSqliteSaver.from_conn_string(
                str(DATABASE_PATH)
            ) as checkpointer:
                agent=create_agent(
                    model=model,
                    tools=tools,
                    system_prompt=(
                        "你是电商客服助手，请使用中文回答。"
                    ),
                    checkpointer=checkpointer,
                    middleware=[
                        SummarizationMiddleware(
                            model=model,
                            trigger=("tokens",60000),
                            keep=("messages",10)
                        )
                    ]
                )

                config={
                    "configurable":{
                        "thread_id":conversation_id
                    }
                }

                async for chunk,metadata in agent.astream(
                    {
                        "messages":[
                            {"role":"user","content":content}
                        ]
                    },
                    config=config,
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

                state=await agent.aget_state(config)
                final_message=next(
                    (
                        message
                        for message in reversed(state.values.get("messages",[]))
                        if isinstance(message,AIMessage)
                        and not message.tool_calls
                    ),
                    None,
                )

                final_content="".join(
                    block.get("text","")
                    for block in final_message.content_blocks
                    if block.get("type")=="text"
                )

                conversation_db.insert_message(
                    conversation_id,
                    "assistant",
                    final_content,
                )

            yield 'event:done\ndata: {}\n\n'

        except Exception:
            logger.exception("流式消息处理失败")
            data=json.dumps(
                {"message":"消息处理失败，请稍后重试"},
                ensure_ascii=False
            )
            yield f"event: error\ndata: {data}\n\n"

    return generate()

def get_conversation(conversation_id):
    return conversation_db.get_conversaiton(conversation_id)

def get_conversations(user_id):
    return conversation_db.get_conversations(user_id)

def delete_conversation(conversation_id):
    conversation_db.delete_conversaion(conversation_id)