from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from llm import OllamaError, ask_llm
from mission import SECRET_KEEPER, detect_secret_leak, explain_success

app = FastAPI()


class MissionBriefing(BaseModel):
    id: str
    title: str
    story: str
    objective: str
    hints: list[str]
    answer_example: str


@app.get("/api/mission")
def get_mission() -> MissionBriefing:
    return MissionBriefing(
        id=SECRET_KEEPER.id,
        title=SECRET_KEEPER.title,
        story=SECRET_KEEPER.story,
        objective=SECRET_KEEPER.objective,
        hints=SECRET_KEEPER.hints,
        answer_example=SECRET_KEEPER.answer_example,
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    history: list[ChatMessage] = []
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    success: bool
    explanation: str | None = None


@app.post("/api/chat")
def post_chat(req: ChatRequest) -> ChatResponse:
    messages = (
        [{"role": "system", "content": SECRET_KEEPER.system_prompt}]
        + [m.model_dump() for m in req.history]
        + [{"role": "user", "content": req.message}]
    )

    try:
        reply = ask_llm(messages)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    success = detect_secret_leak(reply, SECRET_KEEPER.secret)
    return ChatResponse(
        reply=reply,
        success=success,
        explanation=SECRET_KEEPER.success_explanation if success else None,
    )


class ExplainRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ExplainResponse(BaseModel):
    explanation: str


@app.post("/api/explain")
def post_explain(req: ExplainRequest) -> ExplainResponse:
    return ExplainResponse(explanation=explain_success(req.message))


app.mount("/", StaticFiles(directory="static", html=True), name="static")
