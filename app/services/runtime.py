import time
from decimal import Decimal
from openai import AsyncOpenAI
from app.config import settings
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.guardrails import GuardrailsService
from app.services.cost_engine import cost_engine
from app.services.knowledge import KnowledgeService

openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

class AgentExecutionRuntime:
    @staticmethod
    async def run(agent, user_messages: list, db: Optional[AsyncSession] = None) -> dict:
        start_time = time.perf_counter()
        
        # 1. Input Guardrails & Query extraction
        processed_messages = []
        latest_user_query = ""
        for msg in user_messages:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            role = msg.get("role", "user") if isinstance(msg, dict) else getattr(msg, "role", "user")
            if agent.enable_pii_shield and content:
                content, _ = GuardrailsService.sanitize_input(content)
            if role == "user":
                latest_user_query = content
            processed_messages.append({"role": role, "content": content})

        # 2. Semantic RAG Knowledge Retrieval (pgvector)
        rag_context = ""
        rag_snippets = []
        if db and getattr(agent, "id", None) and latest_user_query:
            try:
                rag_snippets = await KnowledgeService.search_relevant_context(
                    db=db, agent_id=agent.id, query=latest_user_query, top_k=3
                )
                if rag_snippets:
                    rag_context = "\n\n--- RELEVANT COMPANY KNOWLEDGE BASE ---\n" + "\n---\n".join(rag_snippets) + "\n----------------------------------------\n"
            except Exception as e:
                print(f"[RAG Warning] Failed to query knowledge chunks: {e}")

        # Construct full system prompt with grounded context
        system_content = agent.system_prompt
        if rag_context:
            system_content += rag_context + "\nInstruction: Prioritize the verified company knowledge provided above when answering the user query."

        # Prepend System Prompt
        full_conversation = [{"role": "system", "content": system_content}] + processed_messages

        # 2. Invoke LLM with fallback safe-handling
        try:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith(("sk-mock", "sk-dummy", "sk-your")):
                raise ValueError("Offline/Mock mode active")
            response = await openai_client.chat.completions.create(
                model=agent.model_name,
                messages=full_conversation,
                temperature=float(agent.temperature),
            )
            
            output_text = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
        except Exception:
            # Fallback simulator when testing locally without external API credits
            if rag_snippets:
                output_text = f"[Agent: {agent.name}] Operational. Based on verified company knowledge: {rag_snippets[0].strip()}"
            else:
                output_text = f"[Agent: {agent.name}] Operational. Query processed under policy {agent.department}."
            prompt_tokens = max(10, sum(len(m['content'].split()) for m in full_conversation) * 2)
            completion_tokens = max(10, len(output_text.split()) * 2)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # 3. Calculate Micro-Dollar Incurred Cost
        cost_usd = cost_engine.calculate_cost(
            model_name=agent.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        return {
            "output_text": output_text,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd
        }