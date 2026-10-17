import logging

from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field,field_validator
from fastapi.responses import StreamingResponse

from app.modules.conversations.service import ConversationNotFoundError,create_conversation,send_message

logger=logging.getLogger(__name__)

router=APIRouter(
    prefix="/conversations",
    tags=["对话管理"],
)

class MessageRequest(BaseModel):
    content:str=Field(min_length=1,max_length=10000)

    @field_validator("content")
    @classmethod
    def validate_content(cls,value:str)->str:
        value=value.strip()
        if not value:
            raise ValueError("消息不能为空")
        return value

class ConversationResponse(BaseModel):
    conversation_id:str

class MessageResponse(BaseModel):
    conversation_id:str
    reply:str

@router.post("",status_code=201,response_model=ConversationResponse)
def create():
    return {
        "conversation_id":create_conversation()
    }

@router.post("/{conversation_id}/messages")
def send(
    conversation_id:str,
    body:MessageRequest
):
    try:
        events=send_message(
            conversation_id,
            body.content
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="会话不存在",
        )
    except Exception:
        logger.exception("发送消息失败")
        raise HTTPException(
            status_code=502,
            detail="消息处理失败，请稍后重试",
        )

    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control":"no-cache",
            "X-Accel-Buffering":"no",
        },
    )
