# ⚡ MeterMind Enterprise Engine

**MeterMind** is an enterprise-grade, production-ready **Managed AI Agent-as-a-Service (MaaS)** platform built with **FastAPI**, **PostgreSQL + pgvector**, and modern web frontends. 

Unlike traditional SaaS platforms that charge hefty flat fees per seat, MeterMind operates on a **100% Pay-As-You-Go** micro-metering architecture. It delivers autonomous AI agents with full **FinOps budget circuit breakers**, **RAG knowledge grounding**, **hosted chat portals**, **embeddable web widgets**, and a **developer API hub**.

---

## 📑 Table of Contents
1. [Core Product Suite](#-core-product-suite)
2. [Key Architecture & Capabilities](#-key-architecture--capabilities)
3. [Landing Page & Interactive Discovery Tour](#-landing-page--interactive-discovery-tour)
4. [Security & Origin Protection](#-security--origin-protection)
5. [FinOps & Micro-Dollar Metering](#-finops--micro-dollar-metering)
6. [System Architecture Diagram](#-system-architecture-diagram)
7. [Directory Structure](#-directory-structure)
8. [API Endpoints Reference](#-api-endpoints-reference)
9. [Quickstart & Deployment](#-quickstart--deployment)
10. [Environment Variables](#-environment-variables)

---

## 📦 Core Product Suite

MeterMind delivers four production-ready deliverables directly to end users:

### 1. 🧠 pgvector Knowledge Base Engine (RAG Grounding)
* **Semantic Document Ingestion**: Upload company policies, FAQs, product manuals, or API documentation (`.txt`, `.md`, `.json`, `.csv`) or paste raw text.
* **Vector Embeddings**: Text is chunked with paragraph/sentence overlap and vectorized into **1536-dimensional embeddings** using OpenAI's `text-embedding-3-small` (with deterministic local fallback).
* **HNSW Index Retrieval**: PostgreSQL `pgvector` with HNSW indexing calculates sub-millisecond cosine similarity (`<=>`) to ground answers in verified company data, preventing hallucinations.

### 2. 🌐 Hosted Standalone Chat Portals (`/chat/{agent_id}`)
* **Zero-Setup Shareable Links**: Every agent automatically receives a dedicated public or internal chat link (`/chat/<agent_id>`).
* **Responsive Dark/Light UI**: Mobile-ready, branded interface showing the agent's name, department, status, and model.
* **Integrated Lead Capture**: Visitors can tap "Contact Support" to leave contact details and messages directly within the chat interface.

### 3. 🧩 Isolated Web Embed Widget (`widget.js`)
* **One-Line Integration**: Embed any agent into Shopify, WordPress, Webflow, or custom React/Next.js sites using:
  ```html
  <script src="https://yourdomain.com/static/widget.js" data-widget-key="af_pub_..."></script>
  ```
* **Shadow DOM Isolation**: The widget renders in an isolated Shadow DOM, guaranteeing that the host website's CSS styles never conflict with the chat bubble.
* **Automated Installation Verifier**: An async background worker periodically scrapes the target domain to confirm script installation before promoting the deployment to `LIVE` status.

### 4. ⚡ Developer API Hub & Programmatic Access
* **Bearer Token Authentication**: Each agent can be programmatically invoked via `POST /api/v1/agents/{agent_id}/execute` using an `af_live_...` API key.
* **Code Snippets Ready to Copy**: The Studio provides copy-paste integration examples in **cURL**, **Python (`requests`)**, and **JavaScript (`fetch`)**.
* **Key Regeneration**: 1-click rotation of agent API keys with immediate invalidation of old credentials.

### 5. 📥 Live Lead Capture & Customer Inquiry Inbox
* **Lead Generation Pipeline**: Customer inquiries collected through widgets or hosted portals are recorded into the database under category `LEAD`.
* **Studio Leads Inbox**: The Tenant Studio displays incoming leads in real time, complete with visitor names, email addresses, phone numbers, and timestamps.

---

## 🎯 Landing Page & Interactive Discovery Tour

The public landing page (`/`) features an **Interactive 10-Prompt Discovery Tour** that actively educates potential customers about MeterMind's architectural advantages:

1. **Live Discovery Telemetry Bar**: Live counter tracking `Prompt X of 10` with a percentage progress bar and cumulative micro-dollar spend counter (`$0.000000`).
2. **One-Tap Suggested Exploration Chips**: Users can click chips to instantly send curated prompts covering 10 core concepts:
   * `#1 💸 Pay-as-you-go vs SaaS`: Micro-metering vs wasteful flat $30/month seat fees.
   * `#2 ⚡ Autonomous Circuit Breakers`: Pre-flight spending cap checks.
   * `#3 🛡️ PII & Secret Redaction`: In-memory regex DLP sanitization.
   * `#4 🌐 Origin-Locked Widgets`: Cryptographic protection against token scraping.
   * `#5 🤖 Model Rate Catalog`: Transparent wholesale rates across GPT-4o, GPT-4o-mini, Claude, and Llama.
   * `#6 🧠 Vector Knowledge (RAG)`: PostgreSQL + `pgvector` semantic retrieval.
   * `#7 🏢 Department Chargeback`: Cross-team cost-center attribution.
   * `#8 📦 30-Second Web Embed`: Isolated Shadow DOM widget setup.
   * `#9 🔍 Automated Site Verifier`: Async background crawlers validating script tags.
   * `#10 🚀 Deploying to Production`: Production readiness celebration and magic link signup.
3. **Architecture Insight Badges**: Each response in the first 10 prompts displays a highlighted card detailing that prompt's architectural mechanism and exact token cost.

---

## 🛡️ Security & Origin Protection

* **Dynamic Domain Origin Locking**: Public widget keys (`af_pub_...`) are cryptographically bound to the client's verified domain. Ingress middleware evaluates HTTP `Origin` and `Referer` headers, immediately rejecting calls from unauthorized domains.
* **Enterprise DLP & PII Shield**: An in-memory regex pipeline automatically sanitizes credit card numbers, Social Security Numbers (SSNs), emails, and API keys (`sk-...`) into `[REDACTED_SECRET]` tokens before requests reach external LLMs.
* **Passwordless Magic Links**: Authentication operates via secure email verification links expiring in 15 minutes, issuing `HttpOnly`, `SameSite=Lax` JWT cookies upon confirmation.
* **Role-Based Access Control (RBAC)**: Distinct authorization tiers for `ADMIN` (Full control), `CREATOR` (Deploy and configure agents), and `CONSUMER` (Chat and execute).

---

## 💰 FinOps & Micro-Dollar Metering

* **Precision Cost Engine**: Incurs costs down to 6 decimal places (`$0.000001`) based on exact input and completion tokens.
  * **GPT-4o-mini**: \$0.15 / 1M input &bull; \$0.60 / 1M output
  * **GPT-4o**: \$2.50 / 1M input &bull; \$10.00 / 1M output
  * **Claude 3.5 Sonnet**: \$3.00 / 1M input &bull; \$15.00 / 1M output
  * **Llama 3.3 70B**: \$0.40 / 1M input &bull; \$0.80 / 1M output
* **Autonomous Circuit Breakers**: Administrators set monthly budget caps (e.g., \$50.00). If an agent breaches its cap, it transitions to `CIRCUIT_BROKEN` and rejects subsequent calls with `HTTP 402 Payment Required`, preventing runaway bills.
* **Department Cost-Center Attribution**: Every request logs an immutable `UsageRecord` tagged with the agent's department, enabling finance teams to generate itemized chargeback reports.

---

## 📐 System Architecture Diagram

```
                       ┌────────────────────────────────────────────────────────┐
                       │                   CLIENT TOUCHPOINTS                   │
                       │  1. Tenant Admin Web Studio (/studio)                  │
                       │  2. Customer Web Embed Widget (<script widget.js>)    │
                       │  3. Hosted Standalone Chat Portals (/chat/{agent_id})  │
                       │  4. External API Consumers (Bearer af_live_...)        │
                       └───────────────────────────┬────────────────────────────┘
                                                   │ HTTPS / JSON
                                                   ▼
                       ┌────────────────────────────────────────────────────────┐
                       │          EDGE ROUTING & INGRESS CONTROL LAYER          │
                       │  • Origin & Referer Whitelisting (af_pub_ locking)     │
                       │  • CORS & Anti-Scraping Filters                        │
                       └───────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FASTAPI APPLICATION CORE RUNTIME                                    │
│                                                                                                       │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐                   │
│  │   AUTH & IDENTITY      │  │  BILLING & FINOPS      │  │ SERVICE PROVISIONING   │                   │
│  │ • Passwordless Magic   │  │ • Micro-dollar Ledger  │  │ • Domain Origin Verify │                   │
│  │ • Scoped API Keys      │  │ • Pre-flight Breakers  │  │ • Dynamic Keys         │                   │
│  │ • JWT Cookie RBAC      │  │ • Cost Engine Catalog  │  │ • Background Crawler   │                   │
│  └───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘                   │
│              │                           │                           │                                │
│              └───────────────────────────┼───────────────────────────┘                                │
│                                          │                                                            │
│                                          ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 ISOLATED AGENT EXECUTION RUNTIME                                │  │
│  │  • Guardrail Pipeline: Regex DLP, PII/Secret Masking                                            │  │
│  │  • RAG Knowledge Retrieval: PostgreSQL + pgvector Cosine Search (1536-dim embeddings)          │  │
│  │  • Multi-LLM Provider Engine: OpenAI / Anthropic / Local Fallbacks                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
                       ┌────────────────────────────────────────────────────────┐
                       │               POSTGRESQL 16 + PGVECTOR                 │
                       │  • users (RBAC & Auth)     • agents (Configs & Budgets)│
                       │  • agent_knowledge_chunks (pgvector HNSW index)        │
                       │  • usage_records (FinOps)  • product_inquiries (Leads) │
                       │  • managed_service_requests (Domain Origin Locking)    │
                       └────────────────────────────────────────────────────────┘
```

---

## 📂 Directory Structure

```text
metermind-backend/
├── app/
│   ├── config.py                 # Pydantic Settings (.env configuration)
│   ├── database.py               # Async SQLAlchemy engine & sessionmaker
│   ├── models/                   # Database ORM models
│   │   ├── agent.py              # Agent configuration, budgets, and key hashes
│   │   ├── billing.py            # FinOps UsageRecord ledger
│   │   ├── inquiry.py            # Leads and contact submissions
│   │   ├── knowledge.py          # pgvector AgentKnowledgeChunk model
│   │   ├── provisioning.py       # ManagedServiceRequest & domain origin locks
│   │   └── user.py               # User accounts and Magic Link tokens
│   ├── routers/                  # FastAPI API route controllers
│   │   ├── agent.py              # Agent CRUD, portal endpoints, API key rotation
│   │   ├── auth.py               # Magic link generation, verification, cookies
│   │   ├── execution.py          # Agent inference execution & landing demo
│   │   ├── finops.py             # FinOps spend statistics and summaries
│   │   ├── inquiries.py          # Lead capture and inquiries inbox
│   │   ├── knowledge.py          # Document chunking, uploads, and pgvector RAG
│   │   └── managed.py            # Widget provisioning & origin-locked execution
│   ├── schemas/                  # Pydantic validation schemas
│   │   ├── agent.py              # Agent creation and response schemas
│   │   └── execution.py          # Message execution input/output schemas
│   ├── services/                 # Core business and execution logic
│   │   ├── auth.py               # Security, password hashing, and API key auth
│   │   ├── cost_engine.py        # Micro-dollar pricing calculations
│   │   ├── guardrails.py         # Regex DLP and PII sanitization
│   │   ├── knowledge.py          # Text chunking, embeddings, and vector search
│   │   ├── runtime.py            # LLM invocation runtime with RAG injection
│   │   └── verification.py       # Asynchronous website crawler for widget tags
│   └── static/                   # Frontend user interfaces
│       ├── auth.html             # Magic Link login and signup portal
│       ├── chat.html             # Standalone hosted agent chat portal
│       ├── index.html            # Public landing page with 10-prompt tour
│       ├── studio.html           # Enterprise Studio & FinOps dashboard
│       └── widget.js             # Embeddable Shadow DOM chat widget
├── .env.example                  # Environment variable configuration template
├── .github/workflows/ci.yml      # GitHub Actions CI build workflow
├── docker-compose.yaml           # Multi-container orchestration (API + pgvector)
├── Dockerfile                    # Containerization instructions
├── main.py                       # Application entrypoint & static routes
└── requirements.txt              # Python library dependencies
```

---

## 🔌 API Endpoints Reference

### Identity & Authentication
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/magic-link` | Request a 15-minute magic login link via email |
| `GET` | `/api/v1/auth/verify` | Verify token, establish session cookie, redirect to `/studio` |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile and RBAC role |
| `POST` | `/api/v1/auth/logout` | Clear session cookie and redirect to `/` |

### Agent Management & Portals
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/agents` | List all active enterprise agents |
| `POST` | `/api/v1/agents` | Provision a new agent and receive raw `af_live_...` API key |
| `GET` | `/api/v1/agents/{id}` | Retrieve agent configuration and spend details |
| `GET` | `/api/v1/agents/{id}/public` | Public metadata (name, department, model) for chat portal |
| `POST` | `/api/v1/agents/{id}/portal/execute` | Public execution endpoint for hosted chat portal |
| `POST` | `/api/v1/agents/{id}/regenerate-key` | Rotate agent API key (invalidates previous credentials) |

### Knowledge Base & RAG (`pgvector`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/agents/{id}/knowledge/text` | Ingest text or FAQ into pgvector chunks |
| `POST` | `/api/v1/agents/{id}/knowledge/upload` | Upload `.txt`, `.md`, or `.json` file for automatic chunking |
| `GET` | `/api/v1/agents/{id}/knowledge` | List indexed knowledge chunks and stats |
| `DELETE` | `/api/v1/agents/{id}/knowledge/{chunk_id}` | Remove a single knowledge chunk from the vector store |
| `DELETE` | `/api/v1/agents/{id}/knowledge` | Clear all knowledge chunks for an agent |

### Programmatic Execution & Inference
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/agents/{id}/execute` | Developer API endpoint (Requires `Bearer af_live_...`) |
| `POST` | `/api/v1/agents/demo/execute` | Public endpoint powering the 10-prompt discovery tour |

### Managed Embed Widgets & Domain Locks
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/managed/` | Provision an embed widget with domain origin locking |
| `GET` | `/api/v1/managed/` | List all provisioned website widget deployments |
| `POST` | `/api/v1/managed/widget/execute` | Widget inference execution (Origin & Referer validated) |

### Leads & Inquiries
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/inquiries` | Submit general enterprise inquiry |
| `POST` | `/api/v1/inquiries/capture` | Capture customer lead from hosted portal or embed widget |
| `GET` | `/api/v1/inquiries` | List all captured leads (Admin/Studio view) |
| `GET` | `/api/v1/inquiries/agent/{id}` | Filter captured leads by specific agent |

### FinOps & System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/finops/summary` | Global spend, monthly budget caps, and token metrics |
| `GET` | `/api/v1/finops/cost-centers` | Breakdown of token spend by department |
| `GET` | `/healthz` | Container and database liveness healthcheck |

---

## 🚀 Quickstart & Deployment

### 1. Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+ recommended)
* [Git](https://git-scm.com/)

### 2. Clone the Repository
```bash
git clone https://github.com/subhakar1999/AI-onboarding.git
cd AI-onboarding
```

### 3. Configure Environment
Copy the example environment configuration:
```bash
cp .env.example .env
```
Open `.env` and configure your API keys (optional for local mock testing):
```env
OPENAI_API_KEY="sk-your-openai-api-key"
SECRET_KEY="your-secure-random-secret-key"
```

### 4. Build & Launch Containers
```bash
docker compose up --build -d
```

### 5. Access the Platform
* **Customer Landing Page**: [http://localhost:8000/](http://localhost:8000/)
* **Enterprise Studio Dashboard**: [http://localhost:8000/studio](http://localhost:8000/studio)
* **Authentication Portal**: [http://localhost:8000/auth](http://localhost:8000/auth)
* **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Hosted Chat Portal**: `http://localhost:8000/chat/<agent_id>`

---

## ⚙️ Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `PROJECT_NAME` | `"MeterMind Enterprise Engine"` | Application brand and header name |
| `ENV` | `"production"` | Runtime mode (`production` or `development`) |
| `DEBUG` | `False` | Verbose debugging flag |
| `SECRET_KEY` | `""` | Secret key used for signing JWT cookies |
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/...` | Async PostgreSQL connection string |
| `OPENAI_API_KEY` | `"sk-mock-key-for-dev"` | OpenAI API Key (uses mock fallback if absent) |
| `SMTP_HOST` | `""` | SMTP hostname for real magic link emails (e.g. `smtp.resend.com`) |
| `SMTP_PORT` | `587` | SMTP TLS port |
| `SMTP_USER` | `""` | SMTP account username / API key |
| `SMTP_PASSWORD` | `""` | SMTP account secret / password |
| `SMTP_FROM` | `"noreply@metermind.local"` | Sender address for authentication emails |

---

## 📄 License
MeterMind is licensed under the Apache 2.0 Enterprise License. Built for autonomous AI scale.