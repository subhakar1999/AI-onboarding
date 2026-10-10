import math
import hashlib
from typing import List
from uuid import UUID
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.knowledge import AgentKnowledgeChunk

openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

class KnowledgeService:
    @staticmethod
    def _fallback_embedding(text: str) -> List[float]:
        """
        Deterministic pseudo-embedding generator of 1536 dimensions
        used when offline or running with mock API credentials.
        """
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(1536):
            b1 = seed[i % len(seed)]
            b2 = seed[(i * 7 + 3) % len(seed)]
            val = (b1 ^ b2) / 255.0 - 0.5
            vector.append(val)
        
        # Normalize vector to unit length
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    @classmethod
    async def create_embedding(cls, text: str) -> List[float]:
        try:
            if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-mock"):
                response = await openai_client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
        except Exception as e:
            print(f"[KnowledgeService] OpenAI embedding fallback: {e}")
        return cls._fallback_embedding(text)

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Splits text into readable coherent chunks respecting paragraph/line breaks.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            if len(current_chunk) + len(p_clean) < chunk_size:
                current_chunk += ("\n\n" + p_clean if current_chunk else p_clean)
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(p_clean) > chunk_size:
                    # Break long paragraph by sentences
                    sentences = p_clean.replace(". ", ".\n").split("\n")
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) < chunk_size:
                            sub_chunk += (" " + s if sub_chunk else s)
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = p_clean

        if current_chunk:
            chunks.append(current_chunk)

        return chunks or [text.strip()]

    @classmethod
    async def ingest_document(cls, db: AsyncSession, agent_id: UUID, text: str) -> int:
        chunks = cls.chunk_text(text)
        created_count = 0

        for chunk_text in chunks:
            if not chunk_text.strip():
                continue
            emb = await cls.create_embedding(chunk_text)
            chunk_record = AgentKnowledgeChunk(
                agent_id=agent_id,
                content=chunk_text,
                embedding=emb
            )
            db.add(chunk_record)
            created_count += 1

        await db.commit()
        return created_count

    @classmethod
    async def search_relevant_context(
        cls, db: AsyncSession, agent_id: UUID, query: str, top_k: int = 3
    ) -> List[str]:
        query_emb = await cls.create_embedding(query)
        
        # pgvector cosine distance query
        stmt = (
            select(AgentKnowledgeChunk.content)
            .where(AgentKnowledgeChunk.agent_id == agent_id)
            .order_by(AgentKnowledgeChunk.embedding.cosine_distance(query_emb))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

