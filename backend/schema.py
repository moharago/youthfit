# Pydantic 데이터 모델 (요청/응답 정의)from pydantic import BaseModel

from typing import Optional

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "guest"

class ChatResponse(BaseModel):
    answer: str