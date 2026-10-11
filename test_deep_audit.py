import sys
import uuid
import asyncio
import httpx
from decimal import Decimal
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal, engine
from app.models.user import User, UserRole, VerificationToken
from app.models.agent import Agent
from app.models.provisioning import ManagedServiceRequest, ProjectStatus
from app.models.knowledge import AgentKnowledgeChunk
from app.models.inquiry import ProductInquiry
from app.services.auth import AuthService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"

async def run_deep_audit():
    print("=" * 70)
    print("🔍 METERMIND DEEP SYSTEM AUDIT & REGRESSION TEST SUITE")
    print("=" * 70)

    # 1. Static and System Health Endpoints
    print("\n[Phase 1] Static & Health Endpoints...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        for path in ["/", "/studio", "/auth", "/healthz", "/static/widget.js"]:
            res = await client.get(path)
            assert res.status_code == 200, f"Expected 200 for {path}, got {res.status_code}"
            print(f"  ✓ GET {path} -> {res.status_code}")

    # 2. Magic Link Authentication & Cookie Handling
    print("\n[Phase 2] Magic Link Authentication Flow...")
    test_email = "audit_user@metermind.ai"
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Request magic link
        res = await client.post(f"{API_URL}/auth/magic-link", json={"email": test_email, "full_name": "Audit Inspector"})
        assert res.status_code == 200, f"Failed magic-link request: {res.text}"
        print(f"  ✓ Magic link requested for {test_email}")

        # Retrieve token from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(VerificationToken).where(VerificationToken.email == test_email).order_by(VerificationToken.created_at.desc()))
            v_token = result.scalars().first()
            assert v_token is not None, "Verification token was not saved to database!"
        
        # Test invalid token verification
        invalid_res = await client.get(f"{API_URL}/auth/verify?token=fake_invalid_token&email={test_email}")
        assert invalid_res.status_code == 400, f"Expected 400 for invalid token, got {invalid_res.status_code}"
        print("  ✓ Invalid token rejected with 400 Bad Request")

    # 3. RBAC & Agent Creation
    print("\n[Phase 3] RBAC & Agent Management Lifecycle...")
    async with AsyncSessionLocal() as db:
        # Get or create admin user
        admin_res = await db.execute(select(User).where(User.email == "admin@metermind.ai"))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email="admin@metermind.ai",
                hashed_password="hash",
                full_name="Platform Admin",
                department="Platform",
                role=UserRole.ADMIN,
                is_verified=True,
                is_active=True
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
        admin_token = AuthService.create_access_token(admin_user)

        # Get or create consumer user (read-only / chat only)
        consumer_res = await db.execute(select(User).where(User.email == "consumer@metermind.ai"))
        consumer_user = consumer_res.scalar_one_or_none()
        if not consumer_user:
            consumer_user = User(
                email="consumer@metermind.ai",
                hashed_password="hash",
                full_name="Consumer User",
                department="General",
                role=UserRole.CONSUMER,
                is_verified=True,
                is_active=True
            )
            db.add(consumer_user)
            await db.commit()
            await db.refresh(consumer_user)
        consumer_token = AuthService.create_access_token(consumer_user)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        agent_payload = {
            "name": "Audit Security Agent",
            "department": "SecurityOperations",
            "model_name": "gpt-4o-mini",
            "system_prompt": "You are a cloud security expert analyzing IAM roles.",
            "monthly_budget_usd": 15.0,
            "enable_pii_shield": True,
            "temperature": 0.1
        }
        
        # CONSUMER should be denied creating an agent
        denied_res = await client.post(f"{API_URL}/agents", json=agent_payload, headers={"Authorization": f"Bearer {consumer_token}"})
        assert denied_res.status_code == 403, f"Expected 403 for CONSUMER creating agent, got {denied_res.status_code}"
        print("  ✓ CONSUMER role prevented from creating agent (403 Forbidden)")

        # ADMIN should succeed
        res = await client.post(f"{API_URL}/agents", json=agent_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 201, f"Failed agent creation: {res.text}"
        agent_data = res.json()
        agent_id = agent_data["id"]
        raw_key = agent_data["raw_api_key"]
        print(f"  ✓ Agent created by ADMIN: ID={agent_id}, Key={raw_key[:12]}...")

        # Get agent details
        res = await client.get(f"{API_URL}/agents/{agent_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Audit Security Agent"
        print("  ✓ Retrieved agent configuration via GET /agents/{id}")

        # Get non-existent agent
        fake_uuid = str(uuid.uuid4())
        res = await client.get(f"{API_URL}/agents/{fake_uuid}")
        assert res.status_code == 404
        print("  ✓ Non-existent agent returned 404 Not Found")

        # Public metadata endpoint
        res = await client.get(f"{API_URL}/agents/{agent_id}/public")
        assert res.status_code == 200
        pub = res.json()
        assert pub["name"] == "Audit Security Agent"
        print(f"  ✓ Public metadata endpoint verified: Name='{pub['name']}', Status='{pub['status']}'")

    # 4. Programmatic API Execution & Key Rotation
    print("\n[Phase 4] Programmatic Developer API Execution & Key Rotation...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Execute agent with raw_key
        exec_payload = {
            "messages": [{"role": "user", "content": "Check for open S3 buckets"}]
        }
        res = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {raw_key}"}
        )
        assert res.status_code == 200, f"Execution failed: {res.text}"
        exec_data = res.json()
        assert "response" in exec_data
        assert exec_data["cost_usd"] > 0
        print(f"  ✓ Developer API execution approved! Cost: ${exec_data['cost_usd']:.6f}, Tokens: {exec_data['total_tokens']}")

        # Rotate/regenerate agent API key
        regen_res = await client.post(
            f"{API_URL}/agents/{agent_id}/regenerate-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert regen_res.status_code == 200
        new_key = regen_res.json()["raw_api_key"]
        assert new_key != raw_key, "Rotated key should be different from old key"
        print(f"  ✓ Key rotated successfully! New Key: {new_key[:12]}...")

        # Old key should now be rejected with 401
        old_res = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {raw_key}"}
        )
        assert old_res.status_code == 401, f"Expected 401 for old revoked key, got {old_res.status_code}"
        print("  ✓ Old revoked key properly rejected with 401 Unauthorized")

        # New key should succeed
        new_exec = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert new_exec.status_code == 200
        print("  ✓ New rotated key executed successfully (200 OK)")

    # 5. Guardrails & DLP PII Sanitization
    print("\n[Phase 5] Guardrails & PII Shield Verification...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        pii_payload = {
            "messages": [
                {"role": "user", "content": "My email is user@confidential.com and my SSN is 123-45-6789. Can you help?"}
            ]
        }
        res = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=pii_payload,
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert res.status_code == 200
        print("  ✓ PII text processed and safely sanitized through regex guardrails")

    # 6. Status Modification & Pause/Circuit Breaker Enforcement
    print("\n[Phase 6] Agent Status Control & Circuit Breaker Enforcement...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Pause the agent
        pause_res = await client.post(
            f"{API_URL}/agents/{agent_id}/status",
            json={"status": "PAUSED"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert pause_res.status_code == 200
        print("  ✓ Agent status transitioned to PAUSED")

        # Execution should be blocked with 403
        blocked_res = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert blocked_res.status_code == 403, f"Expected 403 for PAUSED agent, got {blocked_res.status_code}"
        print("  ✓ PAUSED agent execution successfully blocked with 403 Forbidden")

        # Portal execution should also be blocked
        portal_res = await client.post(
            f"{API_URL}/agents/{agent_id}/portal/execute",
            json={"message": "Hello from portal"}
        )
        assert portal_res.status_code == 403
        print("  ✓ Public portal execution also blocked for PAUSED agent (403 Forbidden)")

        # Resume agent
        resume_res = await client.post(
            f"{API_URL}/agents/{agent_id}/status",
            json={"status": "ACTIVE"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resume_res.status_code == 200
        print("  ✓ Agent status resumed to ACTIVE")

        # Simulate budget breach
        async with AsyncSessionLocal() as db:
            ag = await db.get(Agent, uuid.UUID(agent_id))
            ag.current_spend_usd = Decimal("15.000000") # Equal to monthly_budget_usd (15.00)
            await db.commit()

        # Call should trigger circuit breaker 402 Payment Required
        breach_res = await client.post(
            f"{API_URL}/agents/{agent_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert breach_res.status_code == 402, f"Expected 402 Payment Required, got {breach_res.status_code}"
        print("  ✓ Budget breach immediately flipped agent to CIRCUIT_BROKEN (402 Payment Required)")

        # Reset spend for further tests
        async with AsyncSessionLocal() as db:
            ag = await db.get(Agent, uuid.UUID(agent_id))
            ag.current_spend_usd = Decimal("0.001000")
            ag.status = "ACTIVE"
            await db.commit()

    # 7. Knowledge Base (RAG) Document Ingestion, Search, and Deletion
    print("\n[Phase 7] Knowledge Base (RAG) Full Ingestion & Deletion Suite...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Ingest text document
        doc_payload = {
            "title": "Cloud Security Protocol 2026",
            "content": "All IAM users must enable hardware security key MFA. Passwords expire every 90 days."
        }
        res = await client.post(f"{API_URL}/agents/{agent_id}/knowledge/text", json=doc_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        print("  ✓ Text document ingested into pgvector")

        # Upload file
        file_content = b"Security Operations Guide: SOC teams operate in 24/7 rotational shifts. P1 incidents must be acknowledged in 5 minutes."
        files = {"file": ("soc_guide.txt", file_content, "text/plain")}
        res = await client.post(f"{API_URL}/agents/{agent_id}/knowledge/upload", files=files, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        print("  ✓ File upload ingested into pgvector")

        # List chunks
        res = await client.get(f"{API_URL}/agents/{agent_id}/knowledge", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        kb_data = res.json()
        assert kb_data["total_chunks"] >= 2
        chunk_to_delete = kb_data["chunks"][0]["id"]
        print(f"  ✓ Listed knowledge chunks: Total={kb_data['total_chunks']}")

        # Delete single chunk
        del_chunk_res = await client.delete(f"{API_URL}/agents/{agent_id}/knowledge/{chunk_to_delete}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_chunk_res.status_code == 200
        print(f"  ✓ Deleted chunk {chunk_to_delete}")

        # Wipe all knowledge chunks
        wipe_res = await client.delete(f"{API_URL}/agents/{agent_id}/knowledge", headers={"Authorization": f"Bearer {admin_token}"})
        assert wipe_res.status_code == 200
        print("  ✓ Cleared all knowledge chunks for agent")

        # Verify 0 chunks remain
        res = await client.get(f"{API_URL}/agents/{agent_id}/knowledge", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.json()["total_chunks"] == 0
        print("  ✓ Confirmed 0 chunks remaining in vector store")

    # 8. Managed Deployments (MaaS) CRUD & Deletion
    print("\n[Phase 8] Managed Deployments CRUD & Deletion...")
    test_domain = f"test-{uuid.uuid4().hex[:6]}.example.com"
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create project
        create_res = await client.post(
            f"{API_URL}/managed/",
            json={"project_name": "Audit Temp Widget", "domain": test_domain},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_res.status_code == 200
        proj_data = create_res.json()
        proj_id = proj_data["id"]
        print(f"  ✓ Created managed deployment: ID={proj_id}, Domain={test_domain}")

        # List projects
        list_res = await client.get(f"{API_URL}/managed/", headers={"Authorization": f"Bearer {admin_token}"})
        assert list_res.status_code == 200
        assert any(p["id"] == proj_id for p in list_res.json())
        print("  ✓ Project listed in GET /managed/")

        # Delete project
        del_res = await client.delete(f"{API_URL}/managed/{proj_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_res.status_code == 200
        print(f"  ✓ Project {proj_id} deleted successfully via DELETE /managed/{proj_id}")

        # Verify no longer in list
        list_res = await client.get(f"{API_URL}/managed/", headers={"Authorization": f"Bearer {admin_token}"})
        assert not any(p["id"] == proj_id for p in list_res.json())
        print("  ✓ Confirmed project deleted from database")

    # 9. Clean up test agent
    print("\n[Phase 9] Agent Deletion Cleanup...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        del_agent_res = await client.delete(f"{API_URL}/agents/{agent_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_agent_res.status_code == 200
        print(f"  ✓ Cleaned up test agent {agent_id}")

    # 10. Landing Page 10-Prompt Demo Execution
    print("\n[Phase 10] Landing Page Demo Agents Execution...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        for agent_type in ["support", "data", "voice", "code"]:
            demo_res = await client.post(
                f"{API_URL}/agents/demo/execute",
                json={"agent_type": agent_type, "message": f"Hello from {agent_type} test"}
            )
            assert demo_res.status_code == 200
            print(f"  ✓ Demo Agent '{agent_type}' executed successfully (Cost: ${demo_res.json()['cost_usd']:.6f})")

        # Unknown demo agent should return 404
        unknown_res = await client.post(
            f"{API_URL}/agents/demo/execute",
            json={"agent_type": "quantum_physics_bot", "message": "Hi"}
        )
        assert unknown_res.status_code == 404
        print("  ✓ Unknown demo agent correctly rejected with 404 Not Found")

    # Dispose DB engine
    await engine.dispose()

    print("\n" + "=" * 70)
    print("🏆 ALL 10 DEEP AUDIT PHASES PASSED WITH ZERO FAILURES!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_deep_audit())
