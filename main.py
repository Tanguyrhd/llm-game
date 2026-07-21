import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from llm import OllamaError, stream_llm
from mission import MISSIONS, Mission, detect_secret_leak, stream_explain_success

app = FastAPI()


class MissionBriefing(BaseModel):
    id: str
    title: str
    story: str
    objective: str
    hints: list[str]
    answer_example: str


def _briefing(mission: Mission) -> MissionBriefing:
    return MissionBriefing(
        id=mission.id,
        title=mission.title,
        story=mission.story,
        objective=mission.objective,
        hints=mission.hints,
        answer_example=mission.answer_example,
    )


def _get_mission_or_404(mission_id: str) -> Mission:
    mission = MISSIONS.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.get("/api/missions")
def list_missions() -> list[MissionBriefing]:
    return [_briefing(m) for m in MISSIONS.values()]


@app.get("/api/mission/{mission_id}")
def get_mission(mission_id: str) -> MissionBriefing:
    return _briefing(_get_mission_or_404(mission_id))


class DifficultyBriefing(MissionBriefing):
    difficulty: str | None


class MissionGroup(BaseModel):
    id: str
    title: str
    difficulties: list[DifficultyBriefing]


@app.get("/api/mission-groups")
def list_mission_groups() -> list[MissionGroup]:
    groups: dict[str, list[Mission]] = {}
    for mission in MISSIONS.values():
        groups.setdefault(mission.group, []).append(mission)

    return [
        MissionGroup(
            id=group_id,
            title=members[0].group_title,
            difficulties=[
                DifficultyBriefing(
                    **_briefing(m).model_dump(), difficulty=m.difficulty
                )
                for m in members
            ],
        )
        for group_id, members in groups.items()
    ]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    history: list[ChatMessage] = []
    message: str = Field(..., min_length=1, max_length=2000)


@app.post("/api/chat/{mission_id}")
def post_chat(mission_id: str, req: ChatRequest) -> StreamingResponse:
    mission = _get_mission_or_404(mission_id)
    messages = (
        [{"role": "system", "content": mission.system_prompt}]
        + [m.model_dump() for m in req.history]
        + [{"role": "user", "content": req.message}]
    )

    def event_stream():
        reply_parts: list[str] = []
        try:
            for chunk in stream_llm(messages):
                reply_parts.append(chunk)
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
        except OllamaError as e:
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"
            return

        success = detect_secret_leak("".join(reply_parts), mission.secret)
        yield json.dumps({"type": "done", "success": success}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


class ExplainRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


@app.post("/api/explain/{mission_id}")
def post_explain(mission_id: str, req: ExplainRequest) -> StreamingResponse:
    mission = _get_mission_or_404(mission_id)

    def event_stream():
        for chunk in stream_explain_success(mission, req.message):
            yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
