# AgentForge Enterprise Engine

AgentForge Enterprise Engine is a robust, production-ready FastAPI backend and web platform for creating, managing, and executing AI Agents. It provides a complete end-to-end ecosystem from a beautiful public-facing landing page to an internal Agent Studio with enterprise-grade financial and security guardrails.

## ✨ Key Functionalities & Features

### 🖥️ Frontend & UI
* **Modern Landing Zone (`/`)**: A sleek, conversion-optimized public website inspired by top AI platforms, highlighting the **100% Pay-As-You-Go** pricing model, zero subscriptions, and micro-dollar metering.
* **Authentication Portal (`/auth`)**: A secure authentication flow using **Magic Links (Email Verification)**. Users sign up/login by entering their email, receiving a secure link, and entering without needing passwords.
* **Agent Studio (`/studio`)**: A comprehensive internal dashboard for interacting with AI Agents.
  * **Example Agent Templates**: Browse pre-built enterprise agents (e.g., Customer Support, Code Reviewer) with transparent estimated costs per run.
  * **Agent Fleet Management**: View all deployed agents grouped by department and model.
  * **Interactive Playground**: Chat with any agent in real-time, observing latency, token usage, and micro-dollar costs per message.
  * **FinOps Dashboard**: Live gauges for Monthly Spend, Allocated Budget, and total tokens processed across the fleet.

### 🛡️ Security & Access Control
* **Email Verification & Magic Links**: Robust `HttpOnly` JWT cookie sessions established only after email verification via token.
* **Role-Based Access Control (RBAC)**: Distinct permissions for `ADMIN` (Full control), `CREATOR` (Deploy agents), and `CONSUMER` (Chat only).
* **Enterprise Guardrails**: Automatic PII redaction (SSNs, Emails, Credit Cards, API Keys) before prompts are ever sent to the LLM. Keeps enterprise data secure and compliant.
* **API Key Management**: Secure hashing and management of raw API keys for programmatic agent consumption.

### 💰 FinOps & Chargeback
* **Micro-dollar Metering**: Tracks token usage on every LLM request and calculates highly accurate micro-dollar costs based on the specific underlying model (e.g., GPT-4o, Claude 3.5 Sonnet, Llama 3).
* **Cost-Center Attribution**: Attributes every query's cost to specific business departments or cost-centers.
* **Budget Circuit Breakers**: Administrators can set hard monthly budgets per agent. The engine automatically trips the circuit breaker and pauses execution if an agent breaches its allocated spend limit.

### 🤖 LLM Runtime & Backend Engine
* **FastAPI Backend**: High-performance asynchronous API for agent execution, streaming, and management.
* **PostgreSQL + pgvector**: Scalable relational database for storing users, agents, billing ledgers, and (optionally) vector embeddings.
* **OpenAI / Multi-Model Integration**: Centralized LLM inference engine supporting configurable temperatures, system prompts, and tool dispatching.

---

## 📂 Directory Structure

```text
agentforge-backend/
├── app/
│   ├── main.py                   # FastAPI entrypoint, lifespan, CORS, healthz
│   ├── config.py                 # Pydantic v2 settings & environment variables
│   ├── database.py               # Async engine, sessionmaker, base model
│   ├── models/                   # SQLAlchemy ORM models (user, agent, billing)
│   ├── schemas/                  # Pydantic validation schemas
│   ├── services/                 # Business logic (FinOps, Guardrails, Auth)
│   ├── routers/                  # API endpoints (agents, execution, auth, finops)
│   └── static/                   # Tailwind HTML Frontends (index, auth, studio)
├── Dockerfile                    # Containerization instructions
├── docker-compose.yaml           # Multi-container orchestration (API + Postgres)
└── requirements.txt              # Python dependencies
```

---

## 🚀 Quickstart

1. **Configure Environment:** Create a `.env` file in the root directory and add your `OPENAI_API_KEY`:
   ```bash
   OPENAI_API_KEY=sk-your-openai-api-key
   ```
2. **Build and Launch:** Spin up the PostgreSQL database and FastAPI backend using Docker:
   ```bash
   docker compose up --build -d
   ```
3. **Visit the Application:**
   - **Customer Landing Page:** [http://localhost:8000/](http://localhost:8000/)
   - **Authentication Portal:** [http://localhost:8000/auth](http://localhost:8000/auth)
   - **Agent Studio UI:** [http://localhost:8000/studio](http://localhost:8000/studio)
   - **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)