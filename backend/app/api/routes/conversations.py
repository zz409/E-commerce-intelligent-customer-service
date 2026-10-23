import logging

from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field,field_validator
from fastapi.responses import StreamingResponse

from app.modules.conversations import service

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

class CreateConversationRequest(BaseModel):
    user_id:str

@router.post("",status_code=201,response_model=ConversationResponse)
def create(
    body:CreateConversationRequest
):
    return {
        "conversation_id":service.create_conversation(
            user_id=body.user_id,
        )
    }

@router.post("/{conversation_id}/messages")
def send(
    conversation_id:str,
    body:MessageRequest
):
    try:
        events=service.send_message(
            conversation_id,
            body.content
        )
    except service.ConversationNotFoundError:
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


@router.get("/{conversation_id}/messages")
def get_conversation(
    conversation_id:str
):
    return service.get_conversation(conversation_id)

@router.get("",response_model=list[str])
def get_conversation(
    user_id:str
)->list[str]:
    return service.get_conversations(user_id)

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id:str
):
    service.delete_conversation(conversation_id)