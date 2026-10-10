from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.database import get_db
from app.models.agent import Agent
from app.models.knowledge import AgentKnowledgeChunk
from app.services.knowledge import KnowledgeService
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["Agent Knowledge Base (RAG)"])

class KnowledgeTextRequest(BaseModel):
    title: Optional[str] = "Company Document"
    content: str

class KnowledgeChunkItem(BaseModel):
    id: str
    content: str
    created_at: str

class KnowledgeStatsResponse(BaseModel):
    agent_id: str
    total_chunks: int
    chunks: List[KnowledgeChunkItem]

@router.post("/text")
async def ingest_knowledge_text(
    agent_id: UUID,
    payload: KnowledgeTextRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty")

    formatted_text = f"Title: {payload.title}\n\n{payload.content}"
    chunks_created = await KnowledgeService.ingest_document(db, agent_id, formatted_text)

    return {
        "status": "SUCCESS",
        "message": f"Successfully ingested {chunks_created} knowledge chunks into pgvector database.",
        "chunks_indexed": chunks_created
    }

@router.post("/upload")
async def upload_knowledge_file(
    agent_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file as text: {e}")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    formatted_text = f"File: {file.filename}\n\n{text_content}"
    chunks_created = await KnowledgeService.ingest_document(db, agent_id, formatted_text)

    return {
        "status": "SUCCESS",
        "filename": file.filename,
        "message": f"Ingested {chunks_created} chunks from '{file.filename}' into vector store.",
        "chunks_indexed": chunks_created
    }

@router.get("", response_model=KnowledgeStatsResponse)
async def list_agent_knowledge(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await db.execute(
        select(AgentKnowledgeChunk)
        .where(AgentKnowledgeChunk.agent_id == agent_id)
        .order_by(AgentKnowledgeChunk.created_at.desc())
    )
    records = result.scalars().all()

    items = [
        KnowledgeChunkItem(
            id=str(r.id),
            content=r.content[:200] + ("..." if len(r.content) > 200 else ""),
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M")
        )
        for r in records
    ]

    return KnowledgeStatsResponse(
        agent_id=str(agent_id),
        total_chunks=len(items),
        chunks=items
    )

@router.delete("/{chunk_id}")
async def delete_knowledge_chunk(
    agent_id: UUID,
    chunk_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    chunk = await db.get(AgentKnowledgeChunk, chunk_id)
    if not chunk or chunk.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Knowledge chunk not found")

    await db.delete(chunk)
    await db.commit()
    return {"message": "Knowledge chunk removed successfully"}

@router.delete("")
async def clear_all_agent_knowledge(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await db.execute(
        delete(AgentKnowledgeChunk).where(AgentKnowledgeChunk.agent_id == agent_id)
    )
    await db.commit()
    return {"message": "All knowledge chunks wiped for this agent"}

