import asyncio
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.provisioning import ManagedServiceRequest, ProjectStatus
from app.database import async_session_maker

async def verify_widget_installation(project_id: str, max_retries: int = 3):
    """
    Background task to verify that the customer has installed the AgentForge widget.
    It scrapes the registered domain and checks for <script src="...widget.js" data-widget-key="...">.
    """
    async with async_session_maker() as db:
        result = await db.execute(select(ManagedServiceRequest).where(ManagedServiceRequest.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project or project.status != ProjectStatus.PENDING_VERIFICATION:
            return

        domain = project.registered_domain
        widget_key = project.public_widget_key
        # We need to construct the URL to check. We will assume https by default.
        url = f"https://{domain}" if not domain.startswith("http") else domain

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    html = response.text
                    
                    soup = BeautifulSoup(html, "html.parser")
                    scripts = soup.find_all("script")
                    
                    is_verified = False
                    for script in scripts:
                        src = script.get("src", "")
                        key = script.get("data-widget-key", "")
                        
                        if "widget.js" in src and key == widget_key:
                            is_verified = True
                            break
                    
                    if is_verified:
                        project.domain_verified = True
                        project.status = ProjectStatus.LIVE
                        await db.commit()
                        print(f"[Verification] Success: Widget installed on {domain}")
                        return
                    else:
                        print(f"[Verification] Attempt {attempt+1}: Widget not found on {domain}")
                except Exception as e:
                    print(f"[Verification] Attempt {attempt+1} failed to reach {domain}: {e}")
                
                await asyncio.sleep(5)  # wait before retry
            
            # If we reach here, verification failed.
            print(f"[Verification] Failed: Could not verify widget on {domain} after {max_retries} attempts.")
            # Depending on business logic, we could leave it as PENDING_VERIFICATION or set to SUSPENDED.
