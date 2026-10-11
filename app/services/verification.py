import asyncio
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.provisioning import ManagedServiceRequest, ProjectStatus
from app.database import AsyncSessionLocal

import uuid

async def verify_widget_installation(project_id: str, max_retries: int = 3):
    """
    Background task to verify that the customer has installed the MeterMind widget.
    It scrapes the registered domain and checks for <script src="...widget.js" data-widget-key="...">.
    """
    try:
        project_uuid = uuid.UUID(str(project_id)) if not isinstance(project_id, uuid.UUID) else project_id
    except ValueError:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ManagedServiceRequest).where(ManagedServiceRequest.id == project_uuid))
        project = result.scalar_one_or_none()
        
        if not project or project.status != ProjectStatus.PENDING_VERIFICATION:
            return

        domain = project.registered_domain
        widget_key = project.public_widget_key
        
        # Build candidate URLs to check (supporting Docker-to-host networking)
        urls_to_try = []
        if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
            urls_to_try.append(f"http://{domain}")
            port = domain.split(":")[-1] if ":" in domain else ""
            urls_to_try.append(f"http://host.docker.internal:{port}" if port else "http://host.docker.internal")
        else:
            urls_to_try.append(f"https://{domain}" if not domain.startswith("http") else domain)

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            for attempt in range(max_retries):
                for url in urls_to_try:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
                            scripts = soup.find_all("script")
                            
                            is_verified = any(
                                "widget.js" in script.get("src", "") and script.get("data-widget-key", "") == widget_key
                                for script in scripts
                            )
                            
                            if is_verified:
                                project.domain_verified = True
                                project.status = ProjectStatus.LIVE
                                await db.commit()
                                print(f"[Verification] Success: Widget verified on {domain}")
                                return
                    except Exception as e:
                        pass
                
                print(f"[Verification] Attempt {attempt+1}: Widget not found or domain unreachable on {domain}")
                await asyncio.sleep(2)
            
            # If we reach here, verification failed.
            print(f"[Verification] Failed: Could not verify widget on {domain} after {max_retries} attempts.")
            # Depending on business logic, we could leave it as PENDING_VERIFICATION or set to SUSPENDED.

