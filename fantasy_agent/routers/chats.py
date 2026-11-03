"""Chat sessions and their messages: create/list/rename/delete a chat, and
append messages to one by running the shared agent graph."""
import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from fantasy_agent.auth import get_current_user
from fantasy_agent.clients.espn_fantasy_client import current_league_id, current_team_context
from fantasy_agent.db import Chat, Message, SessionLocal, User
from fantasy_agent.logging.trace import emit


class CreateChatRequest(BaseModel):
    title: str = "New Chat"


class RenameChatRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    message: str


def _get_owned_chat(db, chat_id: int, user: User) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


def create_router(graph) -> APIRouter:
    """Build the chats router around the already-compiled, shared graph singleton."""
    router = APIRouter()

    @router.post("/api/chats")
    async def create_chat(req: CreateChatRequest, user: User = Depends(get_current_user)):
        db = SessionLocal()
        try:
            chat = Chat(user_id=user.id, title=req.title)
            db.add(chat)
            db.commit()
            return {"id": chat.id, "title": chat.title}
        finally:
            db.close()

    @router.get("/api/chats")
    async def list_chats(user: User = Depends(get_current_user)):
        db = SessionLocal()
        try:
            chats = (
                db.query(Chat)
                .filter(Chat.user_id == user.id)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return {"chats": [{"id": c.id, "title": c.title, "updated_at": c.updated_at} for c in chats]}
        finally:
            db.close()

    @router.patch("/api/chats/{chat_id}")
    async def rename_chat(chat_id: int, req: RenameChatRequest, user: User = Depends(get_current_user)):
        db = SessionLocal()
        try:
            chat = _get_owned_chat(db, chat_id, user)
            chat.title = req.title
            db.commit()
            return {"id": chat.id, "title": chat.title}
        finally:
            db.close()

    @router.delete("/api/chats/{chat_id}")
    async def delete_chat(chat_id: int, user: User = Depends(get_current_user)):
        db = SessionLocal()
        try:
            chat = _get_owned_chat(db, chat_id, user)
            db.delete(chat)
            db.commit()
            return {"status": "ok"}
        finally:
            db.close()

    @router.get("/api/chats/{chat_id}/messages")
    async def list_messages(chat_id: int, user: User = Depends(get_current_user)):
        db = SessionLocal()
        try:
            _get_owned_chat(db, chat_id, user)
            msgs = (
                db.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
                .all()
            )
            return {"messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs]}
        finally:
            db.close()

    @router.post("/api/chats/{chat_id}/messages")
    async def add_message(chat_id: int, req: AddMessageRequest, user: User = Depends(get_current_user)):
        if user.league_id is None:
            raise HTTPException(status_code=400, detail="no league linked to this account")

        db = SessionLocal()
        try:
            chat = _get_owned_chat(db, chat_id, user)
            db.add(Message(chat_id=chat.id, role="user", content=req.message))
            db.commit()
        finally:
            db.close()

        current_league_id.set(user.league_id)
        current_team_context.set(user.team_name)

        t0 = time.monotonic()
        try:
            # to_thread copies contextvars, so current_league_id reaches the worker thread.
            result = await asyncio.to_thread(graph.invoke, {"messages": [HumanMessage(content=req.message)]})
        except Exception as err:
            emit("error", route="chats", error=str(err))
            raise HTTPException(status_code=500, detail="internal server error")
        finally:
            emit("graph_end", graph="chat", duration_ms=int((time.monotonic() - t0) * 1000))

        reply = result["messages"][-1].text

        db = SessionLocal()
        try:
            chat = _get_owned_chat(db, chat_id, user)
            db.add(Message(chat_id=chat.id, role="assistant", content=reply))
            chat.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

        return {"reply": reply}

    return router
