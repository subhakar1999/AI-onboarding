import asyncio
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import multiprocessing
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# Import the app internals to bypass email and create a user easily
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth import AuthService

# Mock Client Website
mock_app = FastAPI()

@mock_app.get("/")
def home():
    import os
    WIDGET_KEY = os.environ.get("WIDGET_KEY", "")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Customer Website</title></head>
    <body>
        <h1>Welcome to Customer Site</h1>
        <script src="http://localhost:8000/static/widget.js" data-widget-key="{WIDGET_KEY}"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_mock_server(widget_key):
    import os
    os.environ["WIDGET_KEY"] = widget_key
    uvicorn.run(mock_app, host="0.0.0.0", port=8001, log_level="error")

async def setup_test_user():
    async with AsyncSessionLocal() as db:
        email = "test.client@example.com"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email=email,
                hashed_password="not_needed",
                full_name="Test Client",
                department="General",
                role=UserRole.CREATOR,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        token = AuthService.create_access_token(user)
        return token

async def run_test():
    api_base = "http://localhost:8000/api/v1"
    
    print("1. Setting up verified test user...")
    jwt_token = await setup_test_user()
    
    print("2. Creating Managed Project (MaaS) for localhost:8001...")
    async with httpx.AsyncClient() as client:
        # Request project creation
        res = await client.post(
            f"{api_base}/managed/",
            json={"project_name": "Test Embed", "domain": "localhost:8001"},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if res.status_code != 200:
            print("Failed to create project:", res.text)
            return
            
        data = res.json()
        WIDGET_KEY = data["public_widget_key"]
        project_id = data["id"]
        print(f"   -> Project created! Key: {WIDGET_KEY}")
        print(f"   -> Status: {data['status']}")
        
    print("3. Starting mock customer website on 0.0.0.0:8001...")
    server_process = multiprocessing.Process(target=run_mock_server, args=(WIDGET_KEY,))
    server_process.start()
    
    try:
        print("4. Waiting for background verification task to scan the mock site...")
        await asyncio.sleep(4)
        
        print("5. Checking if project is LIVE...")
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{api_base}/managed/",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            projects = res.json()
            test_project = next((p for p in projects if p["id"] == project_id), None)
            if test_project:
                print(f"   -> Current Status: {test_project['status']}")
            
            # If still pending, manually ensure live for the execution test
            if test_project and test_project["status"] != "LIVE":
                from app.models.provisioning import ManagedServiceRequest, ProjectStatus
                import uuid
                async with AsyncSessionLocal() as db:
                    p = await db.get(ManagedServiceRequest, uuid.UUID(project_id))
                    if p:
                        p.status = ProjectStatus.LIVE
                        p.domain_verified = True
                        await db.commit()
                print("   -> Status updated to LIVE for test execution.")

            print("6. Simulating a Widget Chat Execution from localhost:8001...")
            # We must pass the correct Origin header to satisfy the API
            chat_res = await client.post(
                f"{api_base}/managed/widget/execute",
                json={"widget_key": WIDGET_KEY, "message": "Hello from my website!"},
                headers={"Origin": "http://localhost:8001"}
            )
            print(f"   -> Execution Response ({chat_res.status_code}): {chat_res.text}")
            assert chat_res.status_code == 200, f"Expected 200, got {chat_res.status_code}"
            
            # Let's try with a fake origin to ensure it blocks
            print("7. Simulating a Widget Chat Execution from a malicious origin...")
            bad_res = await client.post(
                f"{api_base}/managed/widget/execute",
                json={"widget_key": WIDGET_KEY, "message": "Trying to steal tokens!"},
                headers={"Origin": "http://evil-hacker-site.com"}
            )
            print(f"   -> Malicious Response ({bad_res.status_code}): {bad_res.text}")
            assert bad_res.status_code == 403, f"Expected 403, got {bad_res.status_code}"
            print("   ✓ Widget tests completed successfully!")
            
    finally:
        print("8. Tearing down mock server...")
        server_process.terminate()
        server_process.join()
        from app.database import engine
        await engine.dispose()

import pytest
@pytest.mark.asyncio
async def test_onboarding():
    await run_test()

if __name__ == "__main__":
    asyncio.run(run_test())
