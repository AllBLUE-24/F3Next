from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Client, Project
from sqlalchemy import select

# ... (imports remain same) ...

async def process_health_check(uid: str, email: str, company: str, full_name: str, role: str, answers: dict, db: AsyncSession):
    # 1. Ensure Client
    res_c = await db.execute(select(Client).where(Client.id == uid))
    client = res_c.scalar_one_or_none()
    
    if not client:
        client = Client(
            id=uid, 
            email=email,
            full_name=full_name,
            role=role,
            company_name=company, # Save here
            status="active"
        )
        db.add(client)
        await db.flush()
    else:
        # Update missing info if needed
        if not client.company_name: client.company_name = company
        if not client.full_name: client.full_name = full_name

    # 2. Ensure Project
    res_p = await db.execute(select(Project).where(Project.client_id == uid))
    project = res_p.scalar_one_or_none()
    
    if not project:
        project = Project(
            client_id=uid, 
            company_name=company, # Save here too
            status="created"
        )
        db.add(project)
        await db.flush()

    # 3. Upsert Hook
    # ... (Rest of logic remains identical) ...