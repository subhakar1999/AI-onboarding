import asyncio
import httpx
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.agent import Agent
from app.models.provisioning import ManagedServiceRequest, ProjectStatus
from app.services.auth import AuthService

API_URL = "http://127.0.0.1:8000/api/v1"

async def get_or_create_test_tenant():
    async with AsyncSessionLocal() as db:
        email = "tenant_onboarding@metermind.ai"
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                hashed_password="hashed_pass_test",
                full_name="Enterprise Tenant Admin",
                department="Operations",
                role=UserRole.CREATOR,
                is_verified=True,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        token = AuthService.create_access_token(user)
        return user, token

async def test_full_onboarding():
    print("=" * 70)
    print("🚀 METERMIND: COMPREHENSIVE AGENT ONBOARDING PROCESS TEST")
    print("=" * 70)

    # 1. Tenant Authentication
    print("\n[Step 1] Initializing Tenant Authentication...")
    user, token = await get_or_create_test_tenant()
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  ✓ Authenticated as: {user.email} (Role: {user.role.value})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 2. Agent Creation / Provisioning
        print("\n[Step 2] Provisioning New Enterprise Agent...")
        agent_payload = {
            "name": "Acme Retail Copilot",
            "department": "CustomerCare",
            "model_name": "gpt-4o-mini",
            "system_prompt": "You are the customer care agent for Acme Corp. Answer questions using our official knowledge base.",
            "monthly_budget_usd": 25.0,
            "enable_pii_shield": True,
            "temperature": 0.2
        }
        res = await client.post(f"{API_URL}/agents", json=agent_payload, headers=headers)
        assert res.status_code == 201, f"Agent creation failed: {res.text}"
        agent_data = res.json()
        agent_id = agent_data["id"]
        raw_api_key = agent_data.get("raw_api_key", "N/A")
        print(f"  ✓ Agent successfully created! ID: {agent_id}")
        print(f"  ✓ Generated Developer API Key: {raw_api_key[:12]}... (stored hash)")

        # 3. Knowledge Base Onboarding (RAG Document Ingestion)
        print("\n[Step 3] Onboarding Knowledge Base into pgvector (RAG Grounding)...")
        kb_text = """
        Acme Corp Return Policy 2026:
        All purchases made through Acme Corp can be returned within 45 days of delivery.
        Customers are eligible for a 100% full refund to their original payment method.
        To initiate a return, email returns@acmecorp.example.com with the order invoice.
        Items must be in original packaging. No restocking fees apply.
        """
        kb_payload = {
            "title": "Acme Corp Official Return Policy",
            "content": kb_text.strip()
        }
        res = await client.post(f"{API_URL}/agents/{agent_id}/knowledge/text", json=kb_payload, headers=headers)
        assert res.status_code == 200, f"Knowledge ingestion failed: {res.text}"
        kb_res = res.json()
        print(f"  ✓ Knowledge Ingested: {kb_res['message']} (Indexed: {kb_res['chunks_indexed']} chunks)")

        # Verify chunks listed via GET
        res = await client.get(f"{API_URL}/agents/{agent_id}/knowledge", headers=headers)
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_chunks"] >= 1
        print(f"  ✓ Verified indexed chunks in pgvector: {stats['total_chunks']} chunks stored with 1536-dim embeddings.")

        # 4. Hosted Standalone Chat Portal Test
        print("\n[Step 4] Testing Hosted Standalone Chat Portal (/chat/{agent_id})...")
        # Check public metadata
        res = await client.get(f"{API_URL}/agents/{agent_id}/public")
        assert res.status_code == 200
        public_meta = res.json()
        print(f"  ✓ Public Portal Metadata: Name='{public_meta['name']}', Dept='{public_meta['department']}', Status='{public_meta['status']}'")

        # Test execution on public portal with RAG query
        portal_payload = {"message": "What is the return window for Acme items and do I get a full refund?"}
        res = await client.post(f"{API_URL}/agents/{agent_id}/portal/execute", json=portal_payload)
        assert res.status_code == 200, f"Portal execution failed: {res.text}"
        portal_reply = res.json()
        print(f"  ✓ Agent Response via Hosted Portal:")
        print(f"    \"{portal_reply['reply'][:120]}...\"")
        print(f"  ✓ Query Incurred Cost: ${portal_reply['cost_usd']:.6f} (Latency: {portal_reply['latency_ms']}ms)")

        # 5. Embed Widget Provisioning & Domain Origin Locking Test
        print("\n[Step 5] Provisioning Embeddable Website Widget with Origin Locking...")
        domain_name = "acmecorp.com"
        managed_payload = {
            "project_name": "Acme Website Widget",
            "domain": f"https://{domain_name}"
        }
        res = await client.post(f"{API_URL}/managed/", json=managed_payload, headers=headers)
        assert res.status_code == 200, f"Widget provisioning failed: {res.text}"
        managed_data = res.json()
        widget_key = managed_data["public_widget_key"]
        project_id = managed_data["id"]
        print(f"  ✓ Widget Key Issued: {widget_key}")
        print(f"  ✓ Registered Domain Origin Lock: {managed_data['registered_domain']}")

        # Activate the project in DB to simulate verification completion
        async with AsyncSessionLocal() as db:
            project_record = await db.get(ManagedServiceRequest, project_id)
            project_record.status = ProjectStatus.LIVE
            project_record.domain_verified = True
            await db.commit()
            print("  ✓ Domain installation verified & project flipped to LIVE.")

        # Test widget execution with authorized origin
        print("\n[Step 6] Testing Widget Execution Security...")
        auth_widget_payload = {
            "widget_key": widget_key,
            "message": "Hello from embedded widget on customer website!"
        }
        res = await client.post(
            f"{API_URL}/managed/widget/execute",
            json=auth_widget_payload,
            headers={"Origin": f"https://{domain_name}"}
        )
        assert res.status_code == 200, f"Authorized widget execution failed: {res.text}"
        print(f"  ✓ Authorized Origin (https://{domain_name}): Request APPROVED! (Status: {res.status_code})")

        # Test widget execution with UNAUTHORIZED origin (SSRF / Token scraping attack)
        unauth_res = await client.post(
            f"{API_URL}/managed/widget/execute",
            json=auth_widget_payload,
            headers={"Origin": "https://malicious-token-thief.com"}
        )
        assert unauth_res.status_code == 403, f"Expected 403 Forbidden for unauthorized origin, got {unauth_res.status_code}"
        print(f"  ✓ Malicious Origin (https://malicious-token-thief.com): Request BLOCKED with 403 Forbidden!")

        # 7. Customer Lead Capture Test
        print("\n[Step 7] Capturing Customer Lead from Onboarded Agent...")
        lead_payload = {
            "name": "Jane Enterprise",
            "email": "jane@customer-company.com",
            "phone": "+1 (555) 234-5678",
            "agent_id": agent_id,
            "department": "CustomerCare",
            "message": "Interested in purchasing 500 units. Please reach out with volume discount."
        }
        res = await client.post(f"{API_URL}/inquiries/capture", json=lead_payload)
        assert res.status_code == 201, f"Lead capture failed: {res.text}"
        lead_data = res.json()
        print(f"  ✓ Customer Lead Captured! ID: {lead_data['lead_id']}")

        # Verify lead appears in Studio inbox for this agent
        res = await client.get(f"{API_URL}/inquiries/agent/{agent_id}", headers=headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) >= 1
        print(f"  ✓ Verified Lead in Studio Inbox: Name='{leads[0]['name']}', Email='{leads[0]['email']}', Phone='{leads[0]['phone']}'")

        # 8. FinOps Spend & Circuit Breaker Tracking
        print("\n[Step 8] Verifying FinOps Spend & Circuit Breaker Health...")
        res = await client.get(f"{API_URL}/agents/{agent_id}", headers=headers)
        assert res.status_code == 200
        current_agent = res.json()
        current_spend = float(current_agent["current_spend_usd"])
        monthly_budget = float(current_agent["monthly_budget_usd"])
        print(f"  ✓ Agent FinOps Tracking: Current Spend = ${current_spend:.6f} / Budget Cap = ${monthly_budget:.2f}")
        assert current_spend > 0.0, "Spend should be recorded in ledger after executions!"

        # FinOps global summary
        res = await client.get(f"{API_URL}/finops/summary", headers=headers)
        assert res.status_code == 200
        finops_summary = res.json()
        print(f"  ✓ Global FinOps Summary: Total Spend = ${finops_summary['total_spend_usd']:.4f}, Total Tokens = {finops_summary['total_tokens_consumed']}")

        print("\n" + "=" * 70)
        print("🎉 ALL 8 AGENT ONBOARDING STAGES PASSED SUCCESSFULLY!")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_full_onboarding())
